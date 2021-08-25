from datetime import datetime, timedelta
from http import HTTPStatus
import logging
import queue
import threading
import warnings

from bs4 import BeautifulSoup
import requests

from .article_searcher import ArticleSearcher


logger = logging.getLogger(f"general_logger.{__name__}")


class ArchiveSearcher(ArticleSearcher):
    timeout = 15

    HEADERS = {
        'accept': 'text/html,application/xhtml+xml,application/xml,application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                      ' AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/90.0.4430.85 Safari/537.36',
    }

    def __init__(self, search_term: str, minimum_duration_minutes=None, lenient=True, max_threads=2):
        super().__init__(search_term)
        self.minimum_duration_minutes = minimum_duration_minutes
        self.lenient = lenient
        self.max_threads = max_threads
        self._query_date = datetime.today().date()

    def get_next_batches(self, num_batches=1):
        def download_urls():
            while not dates.empty():
                date = dates.get_nowait()
                urls_list = self._get_articles_for_day(
                    self.search_term, date, self.minimum_duration_minutes, self.lenient
                )
                for url in urls_list:
                    urls.put(url)

        num_download_threads = min(num_batches, self.max_threads)

        dates = queue.Queue()
        for i in range(1, num_batches + 1):
            dates.put_nowait(self._query_date - timedelta(days=i))
        self._query_date -= timedelta(days=num_batches)

        urls = queue.Queue()
        download_threads = []
        for _ in range(num_download_threads):
            thread = threading.Thread(target=download_urls, daemon=True, args=())
            thread.start()
            download_threads.append(thread)

        for thread in download_threads:
            thread.join()

        return list(urls.queue)

    @classmethod
    def _get_articles_for_day(cls, tag: str, day: datetime.date, minimum_duration_minutes=None, lenient=True):
        logger.info(f"Get urls from day: {day}")
        try:
            response = cls._download_tag_day_page(tag=tag, day=day)
        except requests.exceptions.Timeout:
            warnings.warn(f"Timeout when getting articles for the day {day}")
            return []

        if response.status_code != HTTPStatus.OK:
            warnings.warn(f"HTTP status was {response.status_code}")
            return []

        return cls._get_article_urls_from_tag_day_page(response.text, minimum_duration_minutes, lenient)

    @classmethod
    def _download_tag_day_page(cls, tag: str, day: datetime.date):
        return requests.get(f"https://medium.com/tag/{tag}/archive/{day.strftime('%Y/%m/%d')}", timeout=cls.timeout)

    @classmethod
    def _get_article_urls_from_tag_day_page(cls, tag_day_page: str, minimum_duration_minutes=None, lenient=True):
        soup = BeautifulSoup(tag_day_page, "html.parser")

        article_list = soup.find("div", attrs={"class": "js-postStream"})
        articles = article_list.find_all("div", attrs={"class": "streamItem"})

        if minimum_duration_minutes is not None:
            articles_filtered = []
            for article in articles:
                duration_minutes = cls._get_duration_minutes_from_article_soup(article)

                if duration_minutes is None:
                    if lenient:
                        articles_filtered.append(article)
                elif duration_minutes >= minimum_duration_minutes:
                    articles_filtered.append(article)

            articles = articles_filtered

        read_more_elements = [article.find("div", attrs={"class": ""}) for article in articles]

        return [cls.remove_query_parameters(element.find("a")["href"]) for element in read_more_elements]

    @staticmethod
    def _get_duration_minutes_from_article_soup(article_soup):
        reading_time_span = article_soup.find("span", attrs={"class": "readingTime"})
        if not reading_time_span:
            return None

        return int(reading_time_span["title"].split(" ")[0])

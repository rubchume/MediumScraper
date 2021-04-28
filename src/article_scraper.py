from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
import logging
import multiprocessing
import re
import time
from typing import Optional, Tuple
import warnings

from bs4 import BeautifulSoup
import requests

from src.article import Article
from src.article_searcher.archive_searcher import ArchiveSearcher
from src.article_storage import ArticleStorage
from src.map_reduce import MapReduce

logger = logging.getLogger(f"general_logger.{__name__}")


class ErrorCodes(Enum):
    MISSING_SCHEMA = 1
    CONNECTION_ERROR = 2
    TIMEOUT = 3
    DECODING_ERROR = 4
    TOO_SHORT = 5
    OK = HTTPStatus.OK.value
    NOT_FOUND = HTTPStatus.NOT_FOUND.value
    FORBIDDEN = HTTPStatus.FORBIDDEN.value
    UNKNOWN_ERROR = -1


@dataclass
class Page:
    response: Optional[requests.Response]
    error_code: ErrorCodes


ErrorCodeNames = [code.name for code in ErrorCodes]


class ArticleScraper(object):
    HEADERS = {
        'accept': 'text/html,application/xhtml+xml,application/xml,application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                      ' AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/90.0.4430.85 Safari/537.36',
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "x-xsrf-token": "1",
    }

    def __init__(self, minimum_duration_minutes=2):
        self.minimum_duration_minutes = minimum_duration_minutes

    def compile_articles(self, search_term: str, num_articles: int, directory="articles"):
        logger.info("Start article compilation")

        searcher = ArchiveSearcher(search_term=search_term)

        storage = ArticleStorage()
        storage.create(directory, force=True)

        num_download_threads = 10
        queues_max_size = 100
        num_parse_processes = multiprocessing.cpu_count()

        keep_going = multiprocessing.Value("i", 1)
        num_active_searchers = multiprocessing.Value("i", 1)
        num_active_downloaders = multiprocessing.Value("i", num_download_threads)
        num_active_parsers = multiprocessing.Value("i", num_parse_processes)

        urls: multiprocessing.Queue = multiprocessing.Queue(maxsize=queues_max_size)
        pages: multiprocessing.Queue = multiprocessing.Queue(maxsize=queues_max_size)
        articles: multiprocessing.Queue = multiprocessing.Queue(maxsize=queues_max_size)

        logger.info("Create searching results job")

        def get_next_batches():
            urls_list = searcher.get_next_batches(num_batches=2)
            return urls_list, False

        get_urls_job = MapReduce(
            function=get_next_batches,
            num_workers=1,
            output_queue=urls,
            external_workers_to_wait_for=keep_going,
            num_active_workers=num_active_searchers,
            name="Search Articles Job"
        )
        get_urls_job.start()

        download_article_pages_job = MapReduce(
            function=self._download_article_page,
            num_workers=num_download_threads,
            input_queue=urls,
            output_queue=pages,
            external_workers_to_wait_for=num_active_searchers,
            num_active_workers=num_active_downloaders,
            name="Download article pages job"
        )
        download_article_pages_job.start()

        parse_articles_job = MapReduce(
            function=self._page_to_article,
            num_workers=num_parse_processes,
            input_queue=pages,
            output_queue=articles,
            external_workers_to_wait_for=num_active_downloaders,
            num_active_workers=num_active_parsers,
            name="Download article pages job",
            concurrent=True
        )
        parse_articles_job.start()

        def save_article(article):
            article_object, error_code = article

            if error_code != ErrorCodes.OK:
                return

            storage.add(article_object)

        save_articles_job = MapReduce(
            function=save_article,
            num_workers=1,
            input_queue=articles,
            external_workers_to_wait_for=num_active_parsers,
            num_active_workers=multiprocessing.Value("i", 1),
            name="Save articles job"
        )
        save_articles_job.start()

        while num_active_parsers.value > 0:
            if storage.num_articles >= num_articles:
                logger.info("Objective number of articles reached. Stop retrieving URLs")
                with keep_going.get_lock():
                    keep_going.value = 0
                break

            logger.info(f"Number of articles saved: {storage.num_articles}")
            time.sleep(5)

        logger.info("Downloading remaining URLs")
        get_urls_job.join()
        download_article_pages_job.join()
        parse_articles_job.join()
        save_articles_job.join()

        storage.close()

        logger.info("Compilation finished")
        logger.info(f"{storage.num_articles} articles saved in folder {directory}")

    @classmethod
    def _download_article_page(cls, url) -> Page:
        try:
            response = requests.get(f"{url}", cls.HEADERS, timeout=15)

            http_status_name = HTTPStatus(response.status_code).name
            if http_status_name in ErrorCodeNames:
                error_code = ErrorCodes[http_status_name]
            else:
                error_code = ErrorCodes.UNKNOWN_ERROR

            return Page(response, error_code)

        except requests.exceptions.Timeout:
            warnings.warn(f"Timeout for url {url}")
            return Page(None, ErrorCodes.TIMEOUT)

        except requests.exceptions.ConnectionError:
            return Page(None, ErrorCodes.CONNECTION_ERROR)

        except requests.exceptions.MissingSchema:
            return Page(None, ErrorCodes.MISSING_SCHEMA)

    def _page_to_article(self, page) -> Tuple[Optional[Article], ErrorCodes]:
        if page.error_code != ErrorCodes.OK:
            return None, page.error_code

        try:
            article_id, title, author, paragraphs, duration_minutes = self._parse_article_page(page.response.text)
        except TypeError as e:
            print(f"TypeError: {e}")
            return None, ErrorCodes.DECODING_ERROR
        except TooShortError:
            print("Article is too short. Discard.")
            return None, ErrorCodes.TOO_SHORT

        return Article(
            id=article_id,
            url=page.response.url,
            author=author,
            title=title,
            paragraphs=paragraphs,
            duration_minutes=duration_minutes,
        ), ErrorCodes.OK

    def _parse_article_page(self, page_html):
        def get_id():
            parsely_post_id = soup.find("meta", attrs={"name": "parsely-post-id"})
            if parsely_post_id:
                return parsely_post_id["content"]

            url = soup.find("meta", attrs={"property": "og:url"})["content"]
            return url.split("-")[-1]

        def get_duration_in_minutes():
            min_read = soup.find(text=re.compile("min read"))
            return int(re.findall(r"(\d+) min read", min_read.parent.text)[0])

        soup = BeautifulSoup(page_html, "html.parser")

        duration_minutes = get_duration_in_minutes()
        if duration_minutes < self.minimum_duration_minutes:
            raise TooShortError

        article_id = get_id()
        title = soup.find("meta", attrs={"name": "title"})["content"]
        author = soup.find("meta", attrs={"name": "author"})["content"]
        paragraphs = [
            "".join(element.find_all(text=True))
            for element in soup.find("article").find_all(["p", "li", "h1", "h2", "h3", "h4"])
        ]

        return article_id, title, author, paragraphs, duration_minutes


class TooShortError(RuntimeError):
    pass

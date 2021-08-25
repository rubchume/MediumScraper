from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
import logging
import multiprocessing
import re
import time
from typing import Optional, Tuple
from urllib.parse import urlparse
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
    OK = HTTPStatus.OK.value
    NOT_FOUND = HTTPStatus.NOT_FOUND.value
    FORBIDDEN = HTTPStatus.FORBIDDEN.value
    UNKNOWN_ERROR = -1


ErrorCodeNames = [code.name for code in ErrorCodes]


@dataclass
class Page:
    response: Optional[requests.Response]
    error_code: ErrorCodes


num_cpus = multiprocessing.cpu_count()


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

    @classmethod
    def compile_articles(
            cls,
            search_term: str,
            num_articles: int,
            directory="articles",
            minimum_duration_minutes=5,
            lenient=False,
            num_days_searched_in_parallel=5,
            num_download_threads=20,
            num_parse_processes=num_cpus,
            queues_max_size=100,
    ):
        logger.info("Start article compilation")

        searcher = ArchiveSearcher(
            search_term=search_term,
            max_threads=num_days_searched_in_parallel,
            minimum_duration_minutes=minimum_duration_minutes,
            lenient=lenient
        )

        storage = ArticleStorage()
        storage.create(directory, force=True)

        keep_going = multiprocessing.Value("i", 1)
        num_active_searchers = multiprocessing.Value("i", 1)
        num_active_downloaders = multiprocessing.Value("i", num_download_threads)
        num_active_parsers = multiprocessing.Value("i", num_parse_processes)

        urls: multiprocessing.Queue = multiprocessing.Queue(maxsize=queues_max_size)
        pages: multiprocessing.Queue = multiprocessing.Queue(maxsize=queues_max_size)
        articles: multiprocessing.Queue = multiprocessing.Queue(maxsize=queues_max_size)

        logger.info("Create searching results job")

        def get_next_batches():
            urls_list = searcher.get_next_batches(num_batches=num_days_searched_in_parallel)
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

        logger.info("Create download articles job")

        download_article_pages_job = MapReduce(
            function=cls._download_article_page,
            num_workers=num_download_threads,
            input_queue=urls,
            output_queue=pages,
            external_workers_to_wait_for=num_active_searchers,
            num_active_workers=num_active_downloaders,
            name="Download article pages job"
        )
        download_article_pages_job.start()

        logger.info("Create parse articles job")

        parse_articles_job = MapReduce(
            function=cls._page_to_article,
            num_workers=num_parse_processes,
            input_queue=pages,
            output_queue=articles,
            external_workers_to_wait_for=num_active_downloaders,
            num_active_workers=num_active_parsers,
            name="Parse article pages job",
            concurrent=True
        )
        parse_articles_job.start()

        logger.info("Create save articles job")

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
            time.sleep(20)

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

    @classmethod
    def _page_to_article(cls, page) -> Tuple[Optional[Article], ErrorCodes]:
        if page.error_code != ErrorCodes.OK:
            return None, page.error_code

        try:
            article_id, title, author, paragraphs, duration_minutes = cls._parse_article_page(page.response.text)
        except TypeError as e:
            logger.info(f"TypeError: {e}")
            return None, ErrorCodes.DECODING_ERROR

        return Article(
            id=article_id,
            url=cls._remove_query_parameters(page.response.url),
            author=author,
            title=title,
            paragraphs=paragraphs,
            duration_minutes=duration_minutes,
        ), ErrorCodes.OK

    @staticmethod
    def _remove_query_parameters(url):
        url_components = urlparse(url)
        return f"{url_components.scheme}://{url_components.netloc}{url_components.path}"

    @staticmethod
    def _parse_article_page(page_html):
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
        article_id = get_id()
        title = soup.find("meta", attrs={"name": "title"})["content"]
        author = soup.find("meta", attrs={"name": "author"})["content"]
        paragraphs = [
            "".join(element.find_all(text=True))
            for element in soup.find("article").find_all(["p", "li", "h1", "h2", "h3", "h4"])
        ]

        return article_id, title, author, paragraphs, duration_minutes

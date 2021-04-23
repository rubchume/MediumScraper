from enum import Enum
from http import HTTPStatus
from typing import Optional, Tuple

from bs4 import BeautifulSoup
import requests

from src.article import Article


class ErrorCodes(Enum):
    OK = 0
    MISSING_SCHEMA = 1
    CONNECTION_ERROR = 2
    NOT_FOUND = 3


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
    def scrape(cls, url) -> Tuple[Optional[Article], ErrorCodes]:

        response, error_code = cls._download_article(url)

        if error_code != ErrorCodes.OK:
            return None, error_code

        article_id, title, author, paragraphs = cls._scrape_medium_article_in_html_format(response.text)

        return Article(
            id=article_id,
            url=url,
            author=author,
            title=title,
            paragraphs=paragraphs
        ), ErrorCodes.OK

    @classmethod
    def _download_article(cls, url):
        try:
            response = requests.get(f"{url}", cls.HEADERS)

            http_status_name = HTTPStatus(response.status_code).name
            error_code = ErrorCodes[http_status_name]

            return response, error_code

        except requests.exceptions.ConnectionError:
            return None, ErrorCodes.CONNECTION_ERROR

        except requests.exceptions.MissingSchema:
            return None, ErrorCodes.MISSING_SCHEMA

    @staticmethod
    def _scrape_medium_article_in_html_format(page_html):
        page = BeautifulSoup(page_html, "html.parser")

        article_id = page.find("meta", attrs={"name": "parsely-post-id"})["content"]
        title = page.find("meta", attrs={"name": "title"})["content"]
        author = page.find("meta", attrs={"name": "author"})["content"]
        paragraphs = [
            "".join(element.find_all(text=True))
            for element in page.find("article").find_all(["p", "li", "h1", "h2", "h3", "h4"])
        ]

        return article_id, title, author, paragraphs

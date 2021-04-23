from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
import json
from json import JSONDecodeError
import re
from typing import List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests


class ErrorCodes(Enum):
    OK = 0
    MISSING_SCHEMA = 1
    CONNECTION_ERROR = 2
    NOT_FOUND = 3
    DECODING_ERROR = 4


@dataclass
class Article:
    url: str
    path: str
    title: Optional[str] = None
    author: Optional[str] = None
    paragraphs: Optional[List[str]] = None
    error_code: ErrorCodes = ErrorCodes.OK

    @property
    def metadata(self):
        return {
            "url": self.url,
            "path": self.path,
            "title": self.title,
            "author": self.author,
        }


class MediumScraper(object):
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
    def scrape_medium_article(cls, url) -> Article:
        url_parsed = urlparse(url)

        try:
            response = requests.get(f"{url}?format=json", cls.HEADERS)
        except requests.exceptions.ConnectionError:
            return Article(url=url_parsed.netloc, path=url_parsed.path, error_code=ErrorCodes.CONNECTION_ERROR)
        except requests.exceptions.MissingSchema:
            return Article(url=url_parsed.netloc, path=url_parsed.path, error_code=ErrorCodes.MISSING_SCHEMA)

        if response.status_code == HTTPStatus.NOT_FOUND:
            return Article(url=url_parsed.netloc, path=url_parsed.path, error_code=ErrorCodes.NOT_FOUND)

        page_json = response.text[re.search(r"{", response.text).start():]

        try:
            page = json.loads(page_json)
            title, author, paragraphs = cls.scrape_medium_article_in_json_format(page)
        except JSONDecodeError:
            title, author, paragraphs = cls.scrape_medium_article_in_html_format(response.text)
        except Exception:
            return Article(url=url_parsed.netloc, path=url_parsed.path, error_code=ErrorCodes.DECODING_ERROR)

        return Article(
            url=url_parsed.netloc,
            path=url_parsed.path,
            author=author,
            title=title,
            paragraphs=paragraphs
        )

    @staticmethod
    def scrape_medium_article_in_json_format(page):
        title = page["payload"]["value"]["title"]
        creator_id = page["payload"]["value"]["creatorId"]
        author = page["payload"]["references"]["User"][creator_id]["name"]
        paragraphs = [
            paragraph["text"]
            for paragraph in page["payload"]["value"]["content"]["bodyModel"]["paragraphs"]
            if paragraph["type"]
        ]

        return title, author, paragraphs

    @staticmethod
    def scrape_medium_article_in_html_format(page_html):
        page = BeautifulSoup(page_html, "html.parser")
        title = page.find("meta", attrs={"name": "title"})["content"]
        author = page.find("meta", attrs={"name": "author"})["content"]
        paragraphs = [
            "".join(element.find_all(text=True))
            for element in page.find("article").find_all(["p", "li", "h1", "h2", "h3", "h4"])
        ]

        return title, author, paragraphs

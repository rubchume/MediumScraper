import json
import re
from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
from json import JSONDecodeError
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import numpy as np
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
    title: str = None
    author: str = None
    paragraphs: List[str] = None
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
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36',
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

    @classmethod
    def search_articles(cls, search_term: str, num_articles=10):
        def get_article_id(url):
            return url.split("-")[-1]

        headers = cls.HEADERS.copy()

        session = requests.session()

        base_url = f"https://medium.com/search/posts?q={search_term}"

        urls = []
        article_ids = []
        article_ids_batch = None
        num_batches = int(np.ceil(num_articles / 10))
        for i in range(1, num_batches + 1):
            print(f"Batch {i} of {num_batches}", end="\r")
            if i == 1:
                response = session.get(f"https://medium.com/search?q={search_term}", headers=headers)
            elif i == 2:
                ignore_query_parameters = "&".join([f"ignore={article_id}" for article_id in article_ids])
                response = session.get(
                    f"{base_url}&count=10&{ignore_query_parameters}",
                    headers=headers
                )
            elif i == 3:
                response = session.post(
                    base_url,
                    headers=headers,
                    data={
                        "ignoredIds": article_ids,
                        "page": 3,
                        "pageSize": 10
                    }
                )
            else:
                response = session.post(
                    base_url,
                    headers=headers,
                    data={
                        "ignoredIds": article_ids_batch,
                        "page": i,
                        "pageSize": 10
                    }
                )

            if response.status_code != HTTPStatus.OK:
                raise RuntimeError(f"Search returned an HTTP status code {response.status_code}")

            headers['cookie'] = '; '.join([x.name + '=' + x.value for x in response.cookies])

            urls_batch = cls.get_article_urls(response.text)
            article_ids_batch = [get_article_id(url) for url in urls_batch]

            urls += urls_batch
            article_ids += article_ids_batch

        return urls, article_ids

    @staticmethod
    def get_article_urls(search_result: str):
        def remove_query_parameters(url):
            url_components = urlparse(url)
            return f"{url_components.scheme}://{url_components.netloc}{url_components.path}"

        search_result = BeautifulSoup(search_result, "html.parser")
        article_list = search_result.find("div", attrs={"class": "js-postListHandle"})
        articles = article_list.find_all("div", attrs={"class": "postArticle-content"})

        return [remove_query_parameters(article.find("a")["href"]) for article in articles]

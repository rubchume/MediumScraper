import json
import re
from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
from json import JSONDecodeError
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests


class ErrorCodes(Enum):
    OK = 0
    MISSING_SCHEMA = 1
    CONNECTION_ERROR = 2
    DECODING_ERROR = 3


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


HEADERS = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
}


def scrape_medium_article(url) -> Article:
    global HEADERS

    url_parsed = urlparse(url)

    try:
        response = requests.get(f"{url}?format=json", HEADERS)
    except requests.exceptions.ConnectionError:
        return Article(url=url_parsed.netloc, path=url_parsed.path, error_code=ErrorCodes.CONNECTION_ERROR)
    except requests.exceptions.MissingSchema:
        return Article(url=url_parsed.netloc, path=url_parsed.path, error_code=ErrorCodes.MISSING_SCHEMA)

    page_json = response.text[re.search(r"{", response.text).start():]

    try:
        page = json.loads(page_json)
    except JSONDecodeError:
        return Article(url=url_parsed.netloc, path=url_parsed.path, error_code=ErrorCodes.DECODING_ERROR)

    title, author, paragraphs = scrape_medium_article_in_json_format(page)

    return Article(
        url=url_parsed.netloc,
        path=url_parsed.path,
        author=author,
        title=title,
        paragraphs=paragraphs
    )


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


def search_articles(search_term: str):
    response = requests.get(f"https://medium.com/search?q={search_term}")
    if response.status_code != HTTPStatus.OK:
        raise RuntimeError(f"Search returned an HTTP status code {response.status_code}")

    return get_article_urls(response.text)


def get_article_urls(search_result: str):
    def remove_query_parameters(url):
        url_components = urlparse(url)
        return f"{url_components.scheme}://{url_components.netloc}{url_components.path}"

    search_result = BeautifulSoup(search_result, "html.parser")
    article_list = search_result.find("div", attrs={"class": "js-postListHandle"})
    articles = article_list.find_all("div", attrs={"class": "postArticle-content"})

    return [remove_query_parameters(article.find("a")["href"]) for article in articles]

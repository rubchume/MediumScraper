from http import HTTPStatus
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import numpy as np
import requests


class ArticleSearcher(object):
    HEADERS = {
        'accept': 'text/html,application/xhtml+xml,application/xml,application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                      ' AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/90.0.4430.85 Safari/537.36',
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "x-xsrf-token": "1",
    }

    def __init__(self):
        self.search_term = None
        self._session = None
        self._headers = None
        self._batch_count = None
        self._base_url = None
        self._article_ids_to_ignore = None

    def start(self, search_term: str):
        self.search_term = search_term
        self._session = requests.session()
        self._headers = self.HEADERS.copy()
        self._batch_count = 0
        self._base_url = f"https://medium.com/search/posts?q={self.search_term}"

    def get_next_article_urls(self, num_articles=10):
        print(f"ArticleSearcher. Getting next {num_articles} article URLs.")

        urls = []
        num_batches = int(np.ceil(num_articles / 10))
        for _ in range(1, num_batches + 1):
            print(f" Downloading batch number {self._batch_count + 1}")
            urls += self.get_next_batch_of_10_articles()

        return urls

    def get_next_batch_of_10_articles(self):
        def get_article_id(url):
            return url.split("-")[-1]

        self._batch_count += 1

        if self._batch_count == 1:
            response = self._session.get(f"https://medium.com/search?q={self.search_term}", headers=self._headers)
        elif self._batch_count == 2:
            ignore_query_parameters = "&".join([f"ignore={article_id}" for article_id in self._article_ids_to_ignore])
            response = self._session.get(
                f"{self._base_url}&count=10&{ignore_query_parameters}",
                headers=self._headers
            )
        else:
            response = self._session.post(
                self._base_url,
                headers=self._headers,
                json={
                    "ignoredIds": self._article_ids_to_ignore,
                    "page": self._batch_count,
                    "pageSize": 10
                }
            )

        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Search returned an HTTP status code {response.status_code}")

        self._headers['cookie'] = '; '.join([x.name + '=' + x.value for x in response.cookies])

        urls_batch = self.get_article_urls(response.text)

        if self._batch_count == 2:
            self._article_ids_to_ignore = self._article_ids_to_ignore + [get_article_id(url) for url in urls_batch]
        else:
            self._article_ids_to_ignore = [get_article_id(url) for url in urls_batch]

        return urls_batch

    @staticmethod
    def get_article_urls(search_result: str):
        def remove_query_parameters(url):
            url_components = urlparse(url)
            return f"{url_components.scheme}://{url_components.netloc}{url_components.path}"

        search_result = BeautifulSoup(search_result, "html.parser")
        article_list = search_result.find("div", attrs={"class": "js-postListHandle"})
        articles = article_list.find_all("div", attrs={"class": "postArticle-content"})

        return [remove_query_parameters(article.find("a")["href"]) for article in articles]

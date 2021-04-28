from http import HTTPStatus
import unittest
from unittest import mock

import requests
import requests_mock

from src.article_scraper import ArticleScraper, ErrorCodes


class ArticleScrapperTests(unittest.TestCase):
    @mock.patch("requests.get")
    def test_wrong_url_returns_article_with_error_code(self, get_mock):
        # Given
        get_mock.side_effect = requests.exceptions.ConnectionError
        url = "http://WrongUrl.asdf"
        # When
        article, error_code = ArticleScraper.scrape(url)
        # Then
        self.assertEqual(ErrorCodes.CONNECTION_ERROR, error_code)

    @requests_mock.Mocker()
    def test_not_found_page_returns_article_with_error_code(self, mock):
        # Given
        url = "http://not_found.com"
        mock.get("http://not_found.com", status_code=404)
        # When
        article, error_code = ArticleScraper.scrape(url)
        # Then
        self.assertEqual(ErrorCodes.NOT_FOUND, error_code)

    @mock.patch("requests.get")
    def test_url_with_missing_schema_returns_article_with_error_code(self, get_mock):
        # Given
        get_mock.side_effect = requests.exceptions.MissingSchema
        url = "google.com"
        # When
        article, error_code = ArticleScraper.scrape(url)
        # Then
        self.assertEqual(ErrorCodes.MISSING_SCHEMA, error_code)

    @requests_mock.Mocker()
    def test_find_medium_article_title(self, mock):
        # Given
        with open("tests/helpers/example_article_1.html", "r", encoding="utf-8") as file:
            article_html = file.read()
        mock.get("http://some_article.com", text=article_html)
        # When
        article, error_code = ArticleScraper.scrape("http://some_article.com")
        # Then
        self.assertEqual(200, error_code.value)
        self.assertEqual(
            "SEO Secrets: Reverse-Engineering Google’s Algorithm | by benjamin bannister | freeCodeCamp.org | Medium",
            article.title
        )

    @requests_mock.Mocker()
    def test_find_medium_article_id(self, mock):
        # Given
        with open("tests/helpers/example_article_1.html", "r", encoding="utf-8") as file:
            article_html = file.read()
        mock.get("http://some_article.com", text=article_html)
        # When
        article, error_code = ArticleScraper.scrape("http://some_article.com")
        # Then
        self.assertEqual(200, error_code.value)
        self.assertEqual(
            "92fad4f5a39",
            article.id
        )

    @requests_mock.Mocker()
    def test_find_medium_article_author(self, mock):
        # Given
        with open("tests/helpers/example_article_1.html", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get(
            "https://medium.com/free-code-camp/"
            "seo-secrets-reverse-engineering-googles-algorithm-92fad4f5a39",
            text=article_json
        )
        # When
        article, error_code = ArticleScraper.scrape(
            "https://medium.com/free-code-camp/seo-secrets-reverse-engineering-googles-algorithm-92fad4f5a39"
        )
        # Then
        self.assertEqual("benjamin bannister", article.author)

    @requests_mock.Mocker()
    def test_get_article_body(self, mock):
        # Given
        with open("tests/helpers/example_article_1.html", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get("http://some_article.com/some_path/article", text=article_json)
        # When
        article, error_code = ArticleScraper.scrape("http://some_article.com/some_path/article")
        # Then
        self.assertEqual("SEO Secrets: Reverse-Engineering Google’s Algorithm", article.paragraphs[0])
        self.assertEqual(
            "What have I learned from creating content for the internet? One thing is crystal clear:"
            " if you want people to discover your work, you need search engine optimization (SEO).",
            article.paragraphs[1]
        )

    @requests_mock.Mocker()
    def test_assign_unkown_error_code_when_http_status_code_is_not_included_in_custom_error_codes(self, mock):
        # Given
        with open("tests/helpers/example_article_1.html", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get(
            "http://some_article.com/some_path/article", text=article_json, status_code=HTTPStatus.INSUFFICIENT_STORAGE
        )
        # When
        article, error_code = ArticleScraper.scrape("http://some_article.com/some_path/article")
        # Then
        self.assertEqual(ErrorCodes.UNKNOWN_ERROR, error_code)

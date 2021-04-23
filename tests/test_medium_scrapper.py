import unittest
from unittest import mock

import requests
import requests_mock

from src.medium_scraper import ErrorCodes, MediumScraper


class MediumScrapperTests(unittest.TestCase):
    @mock.patch("requests.get")
    def test_wrong_url_returns_article_with_error_code(self, get_mock):
        # Given
        get_mock.side_effect = requests.exceptions.ConnectionError
        url = "http://WrongUrl.asdf"
        # When
        article = MediumScraper.scrape_medium_article(url)
        # Then
        self.assertEqual(ErrorCodes.CONNECTION_ERROR, article.error_code)

    @requests_mock.Mocker()
    def test_not_found_page_returns_article_with_error_code(self, mock):
        # Given
        url = "http://not_found.com"
        mock.get("http://not_found.com?format=json", status_code=404)
        # When
        article = MediumScraper.scrape_medium_article(url)
        # Then
        self.assertEqual(ErrorCodes.NOT_FOUND, article.error_code)

    @mock.patch("requests.get")
    def test_url_with_missing_schema_returns_article_with_error_code(self, get_mock):
        # Given
        get_mock.side_effect = requests.exceptions.MissingSchema
        url = "google.com"
        # When
        article = MediumScraper.scrape_medium_article(url)
        # Then
        self.assertEqual(ErrorCodes.MISSING_SCHEMA, article.error_code)

    @requests_mock.Mocker()
    def test_separate_url_and_path(self, mock):
        # Given
        with open("tests/helpers/example_article_1.json", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get("http://some_article.com/some_path/article?format=json", text=article_json)
        # When
        article = MediumScraper.scrape_medium_article("http://some_article.com/some_path/article")
        # Then
        self.assertEqual("some_article.com", article.url)
        self.assertEqual("/some_path/article", article.path)

    @requests_mock.Mocker()
    def test_find_medium_article_title_when_returned_page_is_json(self, mock):
        # Given
        with open("tests/helpers/example_article_1.json", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get("http://some_article.com?format=json", text=article_json)
        # When
        article = MediumScraper.scrape_medium_article("http://some_article.com")
        # Then
        self.assertEqual("SEO Secrets: Reverse-Engineering Google’s Algorithm", article.title)

    @requests_mock.Mocker()
    def test_find_medium_article_title_when_returned_page_is_html(self, mock):
        # Given
        with open("tests/helpers/example_article_1.html", "r", encoding="utf-8") as file:
            article_html = file.read()
        mock.get("http://some_article.com?format=json", text=article_html)
        # When
        article = MediumScraper.scrape_medium_article("http://some_article.com")
        # Then
        self.assertEqual(
            "SEO Secrets: Reverse-Engineering Google’s Algorithm | by benjamin bannister | freeCodeCamp.org | Medium",
            article.title
        )

    @requests_mock.Mocker()
    def test_find_medium_article_author_when_returned_page_is_json(self, mock):
        # Given
        with open("tests/helpers/example_article_1.json", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get(
            "https://medium.com/free-code-camp/"
            "seo-secrets-reverse-engineering-googles-algorithm-92fad4f5a39?format=json",
            text=article_json
        )
        # When
        article = MediumScraper.scrape_medium_article(
            "https://medium.com/free-code-camp/seo-secrets-reverse-engineering-googles-algorithm-92fad4f5a39"
        )
        # Then
        self.assertEqual("benjamin bannister", article.author)

    @requests_mock.Mocker()
    def test_find_medium_article_author_when_returned_page_is_html(self, mock):
        # Given
        with open("tests/helpers/example_article_1.html", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get(
            "https://medium.com/free-code-camp/"
            "seo-secrets-reverse-engineering-googles-algorithm-92fad4f5a39?format=json",
            text=article_json
        )
        # When
        article = MediumScraper.scrape_medium_article(
            "https://medium.com/free-code-camp/seo-secrets-reverse-engineering-googles-algorithm-92fad4f5a39"
        )
        # Then
        self.assertEqual("benjamin bannister", article.author)

    @requests_mock.Mocker()
    def test_get_article_body_when_returned_page_is_json(self, mock):
        # Given
        with open("tests/helpers/example_article_1.json", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get("http://some_article.com/some_path/article?format=json", text=article_json)
        # When
        article = MediumScraper.scrape_medium_article("http://some_article.com/some_path/article")
        # Then
        self.assertEqual("SEO Secrets: Reverse-Engineering Google’s Algorithm", article.paragraphs[0])
        self.assertEqual(
            "SEO. Three letters to know if you want your content found. Image: benjamin bannister",
            article.paragraphs[1]
        )
        self.assertEqual(
            "What have I learned from creating content for the internet? One thing is crystal clear:"
            " if you want people to discover your work, you need search engine optimization (SEO).",
            article.paragraphs[2]
        )

    @requests_mock.Mocker()
    def test_get_article_body_when_returned_page_is_html(self, mock):
        # Given
        with open("tests/helpers/example_article_1.html", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get("http://some_article.com/some_path/article?format=json", text=article_json)
        # When
        article = MediumScraper.scrape_medium_article("http://some_article.com/some_path/article")
        # Then
        self.assertEqual("SEO Secrets: Reverse-Engineering Google’s Algorithm", article.paragraphs[0])
        self.assertEqual(
            "What have I learned from creating content for the internet? One thing is crystal clear:"
            " if you want people to discover your work, you need search engine optimization (SEO).",
            article.paragraphs[1]
        )

import unittest
from unittest import mock

import requests
import requests_mock

from src.medium_scraper import ErrorCodes, scrape_medium_article, get_article_urls, search_articles


class MediumScrapperTests(unittest.TestCase):
    @mock.patch("requests.get")
    def test_wrong_url_returns_article_with_error_code(self, get_mock):
        # Given
        get_mock.side_effect = requests.exceptions.ConnectionError
        url = "http://WrongUrl.asdf"
        # When
        article = scrape_medium_article(url)
        # Then
        self.assertEqual(ErrorCodes.CONNECTION_ERROR, article.error_code)

    @mock.patch("requests.get")
    def test_url_with_missing_schema_returns_article_with_error_code(self, get_mock):
        # Given
        get_mock.side_effect = requests.exceptions.MissingSchema
        url = "google.com"
        # When
        article = scrape_medium_article(url)
        # Then
        self.assertEqual(ErrorCodes.MISSING_SCHEMA, article.error_code)

    @requests_mock.Mocker()
    def test_return_decoding_error_when_json_decode_error_is_raised_because_returned_page_was_html_and_not_json(self, mock):
        # Given
        with open("tests/helpers/example_article_1.html", "r", encoding="utf-8") as file:
            html = file.read()
        mock.get("http://some_article.com?format=json", text=html)
        url = "http://some_article.com"
        # When
        article = scrape_medium_article(url)
        # Then
        self.assertEqual(ErrorCodes.DECODING_ERROR, article.error_code)

    @requests_mock.Mocker()
    def test_find_medium_article_title(self, mock):
        # Given
        with open("tests/helpers/example_article_1.json", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get("http://some_article.com?format=json", text=article_json)
        # When
        article = scrape_medium_article("http://some_article.com")
        # Then
        self.assertEqual("SEO Secrets: Reverse-Engineering Google’s Algorithm", article.title)

    @requests_mock.Mocker()
    def test_find_medium_article_author(self, mock):
        # Given
        with open("tests/helpers/example_article_1.json", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get("https://medium.com/free-code-camp/seo-secrets-reverse-engineering-googles-algorithm-92fad4f5a39?format=json", text=article_json)
        # When
        article = scrape_medium_article("https://medium.com/free-code-camp/seo-secrets-reverse-engineering-googles-algorithm-92fad4f5a39")
        # Then
        self.assertEqual("benjamin bannister", article.author)

    @requests_mock.Mocker()
    def test_separate_url_and_path(self, mock):
        # Given
        with open("tests/helpers/example_article_1.json", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get("http://some_article.com/some_path/article?format=json", text=article_json)
        # When
        article = scrape_medium_article("http://some_article.com/some_path/article")
        # Then
        self.assertEqual("some_article.com", article.url)
        self.assertEqual("/some_path/article", article.path)

    @requests_mock.Mocker()
    def test_get_article_body(self, mock):
        # Given
        with open("tests/helpers/example_article_1.json", "r", encoding="utf-8") as file:
            article_json = file.read()
        mock.get("http://some_article.com/some_path/article?format=json", text=article_json)
        # When
        article = scrape_medium_article("http://some_article.com/some_path/article")
        # Then
        self.assertEqual("SEO Secrets: Reverse-Engineering Google’s Algorithm", article.paragraphs[0])
        self.assertEqual("SEO. Three letters to know if you want your content found. Image: benjamin bannister", article.paragraphs[1])
        self.assertEqual(
            "What have I learned from creating content for the internet? One thing is crystal clear:"
            " if you want people to discover your work, you need search engine optimization (SEO).",
            article.paragraphs[2]
        )

    def test_get_urls_from_search_results(self):
        # Given
        with open("tests/helpers/example_search_result_1.html", "r", encoding="utf-8") as file:
            search_result = file.read()
        # When
        urls = get_article_urls(search_result)
        # Then
        self.assertEqual(
            [
                'https://medium.com/airbnb-engineering/experimentation-measurement-for-search-engine-optimization-b64136629760',
                'https://medium.com/blogging-guide/medium-article-search-engine-optimization-medium-seo-9249f18e8e76',
                'https://medium.com/cool-code-pal/introducing-web-components-and-what-it-means-for-search-engine-optimization-and-privacy-b21bfc1f63c7',
                'https://medium.com/the-logician/seo-guide-d534b69ce1c7',
                'https://medium.com/@myxys/seo-101-complete-search-engine-optimization-guide-checklist-97153741cfe6',
                'https://medium.com/write-to-blog/how-to-learn-search-engine-optimization-for-beginning-bloggers-765fe895d2d3',
                'https://medium.com/swlh/why-i-suck-at-search-engine-optimization-7777e6d0441f',
                'https://medium.com/age-of-awareness/search-engine-optimization-seo-for-new-writers-what-it-is-and-why-you-should-care-d36b8a1d000d',
                'https://medium.datadriveninvestor.com/why-seo-is-more-than-just-search-engine-optimization-285f75337702',
                'https://medium.com/@tyohan/progressive-web-app-search-engine-optimization-in-shuvayatra-app-a7c111671338'
            ],
            urls
        )

    @requests_mock.Mocker()
    def test_get_urls_from_search_term(self, mock):
        with open("tests/helpers/example_search_result_1.html", "r", encoding="utf-8") as file:
            search_result = file.read()
        mock.get("https://medium.com/search?q=mySearchTerm", text=search_result)
        # When
        urls = search_articles("mySearchTerm")
        # Then
        self.assertEqual(1, mock.call_count)
        self.assertEqual("https://medium.com/search?q=mySearchTerm", mock.request_history[0].url)
        self.assertEqual(
            [
                'https://medium.com/airbnb-engineering/experimentation-measurement-for-search-engine-optimization-b64136629760',
                'https://medium.com/blogging-guide/medium-article-search-engine-optimization-medium-seo-9249f18e8e76',
                'https://medium.com/cool-code-pal/introducing-web-components-and-what-it-means-for-search-engine-optimization-and-privacy-b21bfc1f63c7',
                'https://medium.com/the-logician/seo-guide-d534b69ce1c7',
                'https://medium.com/@myxys/seo-101-complete-search-engine-optimization-guide-checklist-97153741cfe6',
                'https://medium.com/write-to-blog/how-to-learn-search-engine-optimization-for-beginning-bloggers-765fe895d2d3',
                'https://medium.com/swlh/why-i-suck-at-search-engine-optimization-7777e6d0441f',
                'https://medium.com/age-of-awareness/search-engine-optimization-seo-for-new-writers-what-it-is-and-why-you-should-care-d36b8a1d000d',
                'https://medium.datadriveninvestor.com/why-seo-is-more-than-just-search-engine-optimization-285f75337702',
                'https://medium.com/@tyohan/progressive-web-app-search-engine-optimization-in-shuvayatra-app-a7c111671338'
            ],
            urls
        )

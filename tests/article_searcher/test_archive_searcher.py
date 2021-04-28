from datetime import date, datetime
import unittest
from unittest import mock

import requests
import requests_mock

from src.article_searcher.archive_searcher import ArchiveSearcher


class ArchiveSearcherTests(unittest.TestCase):
    def test_archive_searcher_initializes_last_query_date_to_today(self):
        # When
        searcher = ArchiveSearcher(search_term="something")
        # Then
        self.assertEqual(datetime.today().date(), searcher._query_date)

    @mock.patch.object(ArchiveSearcher, "_get_articles_for_day")
    def test_get_next_batches(self, get_articles_for_day_mock):
        # Given
        searcher = ArchiveSearcher(search_term="something")
        searcher._query_date = date(2021, 4, 4)
        get_articles_for_day_mock.side_effect = [
            [
                "dogs.com",
                "cats.com",
            ],
            [
                "salsa.com",
                "bachata.com",
            ],
            [
                "Paella amb bajoqueta"
            ]
        ]
        # Then
        urls_list = searcher.get_next_batches(num_batches=3)
        # Then
        self.assertEqual(
            {"dogs.com", "cats.com", "salsa.com", "bachata.com", "Paella amb bajoqueta"},
            set(urls_list)
        )
        self.assertEqual(3, get_articles_for_day_mock.call_count)
        get_articles_for_day_mock.assert_has_calls(
            [
                mock.call("something", date(2021, 4, 3)),
                mock.call("something", date(2021, 4, 2)),
                mock.call("something", date(2021, 4, 1))
            ]
        )

    @requests_mock.Mocker()
    def test_get_articles_for_date(self, m):
        # Given
        expected_archive_url = "https://medium.com/tag/arros_al_forn/archive/2021/04/03"
        with open("tests/helpers/archive_results_for_day.html", "r", encoding="utf-8") as file:
            m.get(expected_archive_url, text=file.read(), status_code=200)

        expected_urls = [
            'https://medium.com/@karen-shasha/kitchen-improvisation-a-birthday-dinner-50c75c731b47',
            'https://medium.com/@russcarlton/i-wanted-to-figure-him-out-7a92a27acde4',
            'https://medium.com/@reihoo/%E5%A6%82%E4%BD%95%E5%9C%A8%E5%AE%B6%E5%81%9A'
            '%E8%A5%BF%E7%8F%AD%E7%89%99%E6%B5%B7%E9%AE%AE%E9%A3%AF-paella-6ffe441cfc95',
            'https://medium.com/@miggyperez/7-delicious-paella-recipes-3a6d1ce1e86a'
        ]
        # When
        urls = ArchiveSearcher._get_articles_for_day(tag="arros_al_forn", day=date(2021, 4, 3))
        # Then
        self.assertEqual(expected_archive_url, m.request_history[0].url)
        self.assertEqual(
            expected_urls,
            urls
        )

    @requests_mock.Mocker()
    def test_get_articles_for_date_returns_empty_list_when_timeout_is_triggered(self, m):
        # Given
        expected_archive_url = "https://medium.com/tag/arros_al_forn/archive/2021/04/03"
        m.get(expected_archive_url, exc=requests.exceptions.Timeout)
        # When
        urls = ArchiveSearcher._get_articles_for_day(tag="arros_al_forn", day=date(2021, 4, 3))
        # Then
        self.assertEqual(expected_archive_url, m.request_history[0].url)
        self.assertEqual([], urls)

    @requests_mock.Mocker()
    def test_get_articles_for_date_returns_empty_list_when_response_status_code_is_not_200(self, m):
        # Given
        expected_archive_url = "https://medium.com/tag/arros_al_forn/archive/2021/04/03"
        m.get(expected_archive_url, status_code=404)
        # When
        urls = ArchiveSearcher._get_articles_for_day(tag="arros_al_forn", day=date(2021, 4, 3))
        # Then
        self.assertEqual(expected_archive_url, m.request_history[0].url)
        self.assertEqual([], urls)

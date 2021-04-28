import unittest

from src.article_searcher.article_searcher import ArticleSearcher


class ArticleSearcherTests(unittest.TestCase):
    def test_raise_not_implemented_error_when_calling_get_batch_method_in_abstract_class(self):
        self.assertRaises(
            NotImplementedError,
            ArticleSearcher(search_term="asdf").get_next_batches
        )

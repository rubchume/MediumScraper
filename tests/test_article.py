import unittest

from src.article import Article


class ArticleTests(unittest.TestCase):
    def test_get_number_of_words(self):
        # Given
        article = Article(
            id="id",
            url="url",
            title="title",
            author="someone",
            paragraphs=["Hello I am your friend", "Do you want to be my friend?"]
        )
        # Then
        self.assertEqual(12, article.num_words)

    def test_number_of_words_of_article_with_no_paragraphs_is_0(self):
        article = Article(
            id="id",
            url="url",
            title="title",
            author="someone",
        )
        # Then
        self.assertEqual(0, article.num_words)

import os
import unittest

from src.article_manager import ArticleManager
from src.medium_scraper import Article


class ArticleManagerTests(unittest.TestCase):
    def test_write_article_to_text_file(self):
        # Given
        article_manager = ArticleManager(articles_directory="tests/helpers")
        article = Article(
            url="somepage.com",
            path="/path/to/article",
            author="Cervantes",
            title="Don Quijote New Version",
            paragraphs=[
                "En un lugar de la mancha de cuyo nombre no quiero acordarme...",
                "no hace mucho que vivía un hidalgo de los de lanza en astillero, adarga antigua, rocín flaco y galgo corredor."
            ]
        )
        # When
        article_manager.article_to_text_file(article, index=3)
        # Then
        with open("tests/helpers/3.txt", "r", encoding="utf-8") as file:
            text = file.read()

        self.assertEqual(
            "En un lugar de la mancha de cuyo nombre no quiero acordarme...\n"
            "no hace mucho que vivía un hidalgo de los de lanza en astillero,"
            " adarga antigua, rocín flaco y galgo corredor.",
            text
        )
        # Finally
        os.remove("tests/helpers/3.txt")

    def test_save_article(self):
        # Given
        article_manager = ArticleManager(articles_directory="tests/helpers")
        article = Article(
            url="somepage.com",
            path="/path/to/article",
            author="Cervantes",
            title="Don Quijote New Version",
            paragraphs=[
                "En un lugar de la mancha de cuyo nombre no quiero acordarme...",
                "no hace mucho que vivía un hidalgo de los de lanza en astillero, adarga antigua, rocín flaco y galgo corredor."
            ]
        )
        article_manager.num_articles = 10
        # When
        article_manager.save_article(article)
        # Then
        self.assertEqual(
            dict(
                url="somepage.com",
                path="/path/to/article",
                author="Cervantes",
                title="Don Quijote New Version",
            ),
            article_manager.articles_metadata[11]
        )

        with open("tests/helpers/11.txt", "r", encoding="utf-8") as file:
            text = file.read()

        self.assertEqual(
            "En un lugar de la mancha de cuyo nombre no quiero acordarme...\n"
            "no hace mucho que vivía un hidalgo de los de lanza en astillero,"
            " adarga antigua, rocín flaco y galgo corredor.",
            text
        )
        # Finally
        os.remove("tests/helpers/11.txt")

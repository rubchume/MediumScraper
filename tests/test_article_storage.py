import os
from os import listdir
from os.path import isdir, isfile, join
import shutil
import unittest

import pandas as pd
from pandas._testing import assert_frame_equal

from src.article import Article
from src.article_storage import ArticleStorage


class ArticleStorageTests(unittest.TestCase):
    def tearDown(self) -> None:
        if isdir("tests/helpers/new_storage"):
            shutil.rmtree("tests/helpers/new_storage")

    def test_create_storage_in_a_non_empty_folder_returns_error(self):
        # Given
        article_storage = ArticleStorage()
        # Then
        self.assertRaises(
            ValueError,
            article_storage.create,
            directory="tests/helpers"
        )

    def test_create_storage_in_an_empty_directory_does_not_fail(self):
        # Given
        article_storage = ArticleStorage()
        os.mkdir("tests/helpers/new_storage")
        # When
        article_storage.create("tests/helpers/new_storage")
        article_storage.close()
        # Then
        files_in_directory = [
            file for file in listdir("tests/helpers/new_storage")
            if isfile(join("tests/helpers/new_storage", file))
        ]
        self.assertEqual(1, len(files_in_directory))
        self.assertEqual("index.txt", files_in_directory[0])

    def test_create_and_close_storage_creates_an_index_file(self):
        # Given
        article_storage = ArticleStorage()
        # When
        article_storage.create("tests/helpers/new_storage")
        article_storage.close()
        # Then
        files_in_directory = [
            file for file in listdir("tests/helpers/new_storage")
            if isfile(join("tests/helpers/new_storage", file))
        ]
        self.assertEqual(1, len(files_in_directory))
        self.assertEqual("index.txt", files_in_directory[0])
        assert_frame_equal(
            pd.DataFrame(
                [],
                columns=["Id", "URL", "Author", "Title"]
            ),
            pd.read_csv("tests/helpers/new_storage/index.txt")
        )

    def test_add_article(self):
        # Given
        article_storage = ArticleStorage()
        article_storage.create(directory="tests/helpers/new_storage")
        article = Article(
            id="234",
            url="somepage.com/path/to/article",
            author="Cervantes",
            title="Don Quijote New Version",
            paragraphs=[
                "En un lugar de la mancha de cuyo nombre no quiero acordarme...",
                "no hace mucho que vivía un hidalgo de los de lanza en astillero, adarga antigua, rocín flaco y galgo corredor."
            ]
        )
        # When
        article_storage.add(article)
        article_storage.close()
        # Then
        with open("tests/helpers/new_storage/234.txt", "r", encoding="utf-8") as file:
            text = file.read()

        self.assertEqual(
            "En un lugar de la mancha de cuyo nombre no quiero acordarme...\n"
            "no hace mucho que vivía un hidalgo de los de lanza en astillero,"
            " adarga antigua, rocín flaco y galgo corredor.",
            text
        )

        assert_frame_equal(
            pd.DataFrame(
                {
                    "Id": ["234"],
                    "URL": ["somepage.com/path/to/article"],
                    "Author": ["Cervantes"],
                    "Title": ["Don Quijote New Version"]
                },
            ),
            pd.read_csv("tests/helpers/new_storage/index.txt").astype("str")
        )

    def test_add_many_articles(self):
        # Given
        article_storage = ArticleStorage()
        article_storage.create(directory="tests/helpers/new_storage")
        article1 = Article(
            id="234",
            url="somepage.com/path/to/article",
            author="Cervantes",
            title="Don Quijote New Version",
            paragraphs=[
                "En un lugar de la mancha de cuyo nombre no quiero acordarme...",
                "no hace mucho que vivía un hidalgo de los de lanza en astillero, adarga antigua, rocín flaco y galgo corredor."
            ]
        )
        article2 = Article(
            id="asdf4",
            url="somepage.com/path/to/other_article",
            author="Lope de Vega",
            title="Sonetos y más sonetos",
            paragraphs=[
                "Un soneto me ha mandado hacer Violante,",
                "en mi vida me he visto en tal aprieto,"
            ]
        )
        # When
        article_storage.add(article1)
        article_storage.add(article2)
        article_storage.close()
        # Then
        with open("tests/helpers/new_storage/234.txt", "r", encoding="utf-8") as file:
            self.assertEqual(
                "En un lugar de la mancha de cuyo nombre no quiero acordarme...\n"
                "no hace mucho que vivía un hidalgo de los de lanza en astillero,"
                " adarga antigua, rocín flaco y galgo corredor.",
                file.read()
            )
        with open("tests/helpers/new_storage/asdf4.txt", "r", encoding="utf-8") as file:
            self.assertEqual(
                "Un soneto me ha mandado hacer Violante,\n"
                "en mi vida me he visto en tal aprieto,",
                file.read()
            )
        assert_frame_equal(
            pd.DataFrame(
                {
                    "Id": ["234", "asdf4"],
                    "URL": ["somepage.com/path/to/article", "somepage.com/path/to/other_article"],
                    "Author": ["Cervantes", "Lope de Vega"],
                    "Title": ["Don Quijote New Version", "Sonetos y más sonetos"]
                },
            ),
            pd.read_csv("tests/helpers/new_storage/index.txt").astype("str")
        )

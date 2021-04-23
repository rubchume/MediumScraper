import os
from os import listdir
from os import path

import pandas as pd

from src.article import Article


class ArticleStorage(object):
    ID = "Id"
    URL = "URL"
    AUTHOR = "Author"
    TITLE = "Title"
    FIELDS = [ID, URL, AUTHOR, TITLE]

    def __init__(self):
        self.directory = None
        self._metadata = None

    @property
    def num_articles(self):
        return len(self._metadata)

    def create(self, directory):
        def directory_is_not_empty():
            if not path.isdir(directory):
                return False

            return any([path.isfile(path.join(directory, f)) for f in listdir(directory)])

        if directory_is_not_empty():
            raise ValueError("New storage must be set in an empty or not-existent directory")

        if not path.isdir(directory):
            os.mkdir(directory)

        self.directory = directory
        self._metadata = []

    def close(self):
        pd.DataFrame(
            self._metadata,
            columns=self.FIELDS
        ).to_csv(f"{self.directory}/index.txt", index=False, header=True)

    def add(self, article):
        self._metadata.append(self._get_metadata(article))
        self._article_to_text_file(article)

    @classmethod
    def _get_metadata(cls, article: Article):
        return {
            cls.ID: article.id,
            cls.URL: article.url,
            cls.AUTHOR: article.author,
            cls.TITLE: article.title,
        }

    def _article_to_text_file(self, article):
        with open(f"{self.directory}/{article.id}.txt", "w", encoding="utf-8") as file:
            file.write("\n".join(article.paragraphs))

import os
from os import listdir
from os import path
from pathlib import Path
import shutil

import pandas as pd

from .article import Article


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
    def num_articles(self) -> int:
        return len(self._metadata)

    def create(self, directory, force=False):
        def directory_is_not_empty():
            return any([path.isfile(path.join(directory, f)) for f in listdir(directory)])

        def directory_exists():
            return path.isdir(directory)

        if directory_exists():
            if directory_is_not_empty():
                if force:
                    shutil.rmtree(directory)
                    os.mkdir(directory)
                else:
                    raise ValueError("New storage must be set in an empty or not-existent directory")
        else:
            Path(directory).mkdir(parents=True, exist_ok=True)

        self.directory = directory
        self._metadata = []

    def close(self):
        pd.DataFrame(
            self._metadata,
            columns=self.FIELDS
        ).to_csv(f"{self.directory}/index.csv", index=False, header=True)

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

from abc import abstractmethod
from urllib.parse import urlparse


class ArticleSearcher(object):
    def __init__(self, search_term: str):
        self.search_term = search_term

    @abstractmethod
    def get_next_batches(self, num_batches=1):
        raise NotImplementedError

    @staticmethod
    def remove_query_parameters(url):
        url_components = urlparse(url)
        return f"{url_components.scheme}://{url_components.netloc}{url_components.path}"

class ArticleManager(object):
    def __init__(self, articles_directory="articles"):
        self.num_articles = 0
        self.articles_directory = articles_directory
        self.articles_metadata = {}

    def save_article(self, article):
        self.num_articles += 1
        index = self.num_articles

        self.articles_metadata[index] = article.metadata
        self.article_to_text_file(article, index)

    def article_to_text_file(self, article, index):
        with open(f"{self.articles_directory}/{index}.txt", "w", encoding="utf-8") as file:
            file.write("\n".join(article.paragraphs))

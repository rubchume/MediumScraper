import logging
from pathlib import Path

import boto3

from src.article import Article
from src.article_storage import ArticleStorage

logger = logging.getLogger()
logger.setLevel(logging.INFO)


s3 = boto3.client("s3")


def lambda_handler(event, context):
    logger.info("Scrape Medium articles")
    logger.info(f'Search term: {event["search_term"]}')
    logger.info(f'Number of articles: {event["num_articles"]}')
    logger.info(f'Search unique identifier: {event["search_id"]}')

    bucket = "medium-scraper-bucket"
    logger.info(f"Use bucket {bucket}")

    results_directory = Path("results")

    file_name = results_directory / f"{event['search_id']}.txt"
    logger.info(f"File name: {file_name}")

    s3.put_object(Bucket=bucket, Key=str(file_name), Body="Content of file".encode("utf-8"))

    storage = ArticleStorage()

    articles_directory = Path("/tmp") / event["search_id"]
    storage.create(str(articles_directory), force=True)

    article1 = Article(
        id="article_id",
        url="article_url",
        title="This is the title",
        paragraphs=[
            "This is the first paragraph",
            "This is the second paragraph"
        ]
    )
    storage.add(article1)

    for local_path in Path(articles_directory).glob("*.txt"):
        s3_path = str(Path("results") / local_path.relative_to("/tmp"))
        with open(local_path, "r", encoding="utf-8") as article:
            s3.put_object(Bucket=bucket, Key=s3_path, Body=article.read())

    logger.info("Operation completed")

    return event

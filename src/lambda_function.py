import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Scrape Medium articles")
    logger.info(f'Search term: {event["search_term"]}')
    logger.info(f'Number of articles: {event["num_articles"]}')
    logger.info(f'Search unique identifier: {event["search_id"]}')
    return event

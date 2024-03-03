from config import config
from scraper import OptionsScraper


def scrape_ticker_job(ticker, timestamp):
    mongo_client = config.mongo_client()
    OptionsScraper(ticker, None, timestamp, mongo_client).scrape()
    mongo_client.close()

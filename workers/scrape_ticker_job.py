from config import config
from scraper import IvScraper


def scrape_ticker_job(ticker, timestamp):
    mongo_client = config.mongo_client()
    iv_scraper = IvScraper(ticker, None, timestamp, mongo_client)
    iv_scraper.scrape()
    mongo_client.close()

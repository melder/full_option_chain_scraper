from config import config
from scraper import IvScraper


def scrape_ticker_job(ticker, timestamp):
    IvScraper(ticker, None, timestamp, config.mongo_client()).scrape()

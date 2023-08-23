from config import config
from scraper import IvScraper
from models.blacklist import Blacklist


def scrape_ticker_job(ticker, timestamp):
    iv_scraper = IvScraper(ticker, None, timestamp, config.mongo_client())
    iv_scraper.scrape()
    Blacklist(iv_scraper).exec()

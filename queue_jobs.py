from datetime import datetime
from rq import Retry, Queue

from config import config

import scraper
from models.blacklist import Blacklist
from workers import scrape_ticker_job


def queue_scraping():
    queue = Queue(connection=config.redis_client(decode_responses=False))
    timestamp = str(round(datetime.timestamp(datetime.utcnow())))
    blacklist = Blacklist.blacklisted_tickers()
    for ticker in scraper.get_all_options():
        if ticker in blacklist:
            continue
        queue.enqueue(
            scrape_ticker_job.scrape_ticker_job,
            args=(ticker, timestamp),
            result_ttl=0,
            retry=Retry(max=2),
        )


if __name__ == "__main__":
    queue_scraping()

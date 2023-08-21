from datetime import datetime
from rq import Queue
from scraper import (
    get_all_options,
    blacklisted_tickers,
    IvScraper,
    ExpirationDateMapper,
    config,
)
from jobs.scrape_job import scrape_ticker_job

queue = Queue(connection=config.redis_worker)

timestamp = str(round(datetime.timestamp(datetime.utcnow())))
for _ticker in get_all_options():
    if _ticker in blacklisted_tickers:
        continue
    iv_scraper = IvScraper(_ticker, ExpirationDateMapper(_ticker).get_expr())
    queue.enqueue(
        scrape_ticker_job,
        args=(iv_scraper, timestamp),
        result_ttl=0,
    )

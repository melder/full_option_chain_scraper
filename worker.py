from datetime import datetime
from rq import Connection, Queue, Worker, Retry

from config import config
from jobs.scrape_jobs import scrape_ticker_job
from scraper import (
    get_all_options,
    blacklisted_tickers,
    IvScraper,
    ExpirationDateMapper,
)

redis_conn = config.redis_worker
queue = Queue(connection=redis_conn)

# Enqueue a job
timestamp = str(round(datetime.timestamp(datetime.utcnow())))
exprs = ExpirationDateMapper.get_all_exprs()
for ticker in get_all_options():
    if ticker in blacklisted_tickers:
        continue
    expr = exprs.get(ticker)
    iv_scraper = IvScraper(ticker, expr)
    queue.enqueue(
        scrape_ticker_job,
        args=(iv_scraper, timestamp),
        retry=Retry(max=3, interval=120),
        result_ttl=0,
    )


# Create a worker
with Connection(redis_conn):
    worker = Worker([queue])

    # Start the worker to process jobs indefinitely
    worker.work()

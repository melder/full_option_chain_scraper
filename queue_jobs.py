from datetime import datetime, timezone
from rq import Retry, Queue

from config import config

from workers import scrape_ticker_job


def queue_scraping():
    queue = Queue(
        config.namespace, connection=config.redis_client(decode_responses=False)
    )
    timestamp = str(round(datetime.timestamp(datetime.now(timezone.utc))))
    for ticker in config.crypto_tickers:
        queue.enqueue(
            scrape_ticker_job.scrape_ticker_job,
            args=(ticker, timestamp),
            result_ttl=0,
            retry=Retry(max=2),
        )


if __name__ == "__main__":
    queue_scraping()

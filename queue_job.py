from datetime import datetime
from rq import Queue
from scraper import (
    get_all_options,
    blacklisted_tickers,
    IvScraper,
    ExpirationDateMapper,
    config,
)
from jobs import scrape_job


def main():
    queue = Queue(
        connection=config.redis_worker,
    )
    timestamp = str(round(datetime.timestamp(datetime.utcnow())))
    for _ticker in get_all_options():
        if _ticker in blacklisted_tickers:
            continue
        if not (expr := ExpirationDateMapper(_ticker).get_expr()):
            continue

        iv_scraper = IvScraper(_ticker, expr, timestamp)
        queue.enqueue(
            scrape_job.scrape_ticker_job,
            args=(iv_scraper,),
            result_ttl=0,
        )


if __name__ == "__main__":
    main()

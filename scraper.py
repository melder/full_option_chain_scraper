from config import config  # pylint: disable=wrong-import-order

import csv
import os
import sys
import time
from datetime import datetime, date
from pprint import pprint  # pylint: disable=unused-import

import helpers.date_helpers as dh
import helpers.hood_helpers as hood

from models.expiration_date_cache import ExpirationDateCache
from models.option import Option


def read_csv(file_path, delimiter="\t"):
    with open(file_path, "r", encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=delimiter)
        return list(csv_reader)


# deprecated, but keeping on hand for potential future export to csv functions
def write_to_csv(file_path, data, delimiter="\t"):
    with open(file_path, "a", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=delimiter)
        csv_writer.writerow(data)


class OptionsScraper:
    """
    1. Scrapes implied volatility of options closest to
    at the money (minimum 4). E.g. for stock at $99.5
    with $1 strikes it will look at: 99C, 100C, 99P, 100P

    2. Persist option API json in datastore (mongodb in this case)
    """

    # scrape attempts assuming network/rate limit/etc errors
    retry_count = 8
    retry_sleep = 10.1

    # blocking scrape not utilizing background workers
    @classmethod
    def exec_blocking(cls):
        exprs = ExpirationDateCache.get_all_exprs()
        timestamp = str(round(datetime.timestamp(datetime.utcnow())))
        db = config.mongo_client()

        for ticker in config.crypto_tickers:
            try:
                scraper = cls(ticker, exprs.get(ticker), timestamp, db)
                scraper.scrape()
            except Exception:  # pylint: disable=broad-exception-caught
                # TODO: add some logging
                pass

    def __init__(
        self,
        ticker,
        expr,
        scrape_start_timestamp=None,
        client=None,
    ):
        self.ticker = ticker
        self.expr = expr or ExpirationDateCache(ticker).get_expr()

        self.price = 0

        self.scrape_start_timestamp = scrape_start_timestamp

        self.option_collection = (
            Option(client[config.conf.mongo.database]) if client else None
        )

    def scrape(self):
        if not (self.ticker and self.expr):
            return None

        for _ in range(self.retry_count):
            if not (res := hood.get_option_chain(self.ticker, self.expr)):
                time.sleep(self.retry_sleep)
                continue
            if not (sorted_chain := self.process_chain(res)):
                time.sleep(self.retry_sleep)
                continue
            if self.option_collection:
                self.insert_options_to_db(sorted_chain)
            return True

        return None

    def process_chain(self, chain):
        if not (price := hood.get_price(self.ticker)):
            return None

        self.price = float(price)
        return sorted(chain, key=lambda x: abs(self.price - float(x["strike_price"])))

    # v2 TODO:
    # 1. move to model
    # 2. prune properties
    # 3. batch insert or move to low priority background worker
    def insert_options_to_db(self, chain):
        """
        v1: Currently shoving entire option JS returned by hood API,
        of which there are 4 (or 4 * depth), into single document which
        represents the state of a singular ticker scraped.
        In other words, scraping 4000 tickers for option data will generate
        4000 documents with 16000 (4 * 4000) embedded option objects.

        Document properties:

        - scraper_timestamp (int)
        - ticker (str)
        - expiration (ISO8601 date str)
        - price (float)
        - expires_at (datetime)
        - absolute_seconds_remaining (int)
        - market_seconds_remaining (int)
        - created_at (datetime)
        - options (array of dict JSON responses HOOD API returns)
        """

        if self.scrape_start_timestamp and self.option_collection:
            document = {
                "scraper_timestamp": self.scrape_start_timestamp,
                "scraper_iso_date": date.fromtimestamp(
                    int(self.scrape_start_timestamp)
                ).isoformat(),
                "ticker": self.ticker,
                "expiration": self.expr,
                "price": float(self.price),
                "expires_at": dh.market_closes_at(self.expr),
                "absolute_seconds_remaining": dh.absolute_seconds_until_expr(self.expr),
                "market_seconds_remaining": dh.market_seconds_until_expr(self.expr),
                "created_at": datetime.utcnow(),
                "options": chain,
            }
            self.option_collection.create(document)


if __name__ == "__main__":
    COMMANDS = [
        "scrape",
        "scrape-force",
        "populate-exprs",
        "purge-exprs",
    ]
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python scraper.py <{' / '.join(COMMANDS)}>")
        sys.exit(0)

    if sys.argv[1] in ["scrape", "scrape-force"]:
        if not dh.is_market_open_now() and sys.argv[1] == "scrape":
            print("Market is closed")
            sys.exit(0)

        os.system("python queue_jobs.py")
        if sys.platform != "darwin":
            os.system(
                f"rq worker-pool -b {config.namespace} -n {config.conf.workers} -u redis://:{config.conf.redis.password}@{config.conf.redis.host}:{config.conf.redis.port}/0"
            )
        else:
            os.system(
                f"OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES rq worker-pool -b {config.namespace} -n {config.conf.workers}"
            )
        sys.exit(0)

    if sys.argv[1] == "populate-exprs":
        ExpirationDateCache.populate(config.crypto_tickers)
        sys.exit(0)

    if sys.argv[1] == "purge-exprs":
        ExpirationDateCache.purge()
        sys.exit(0)

from config import config  # pylint: disable=wrong-import-order

import csv
import os
import sys
import time
from datetime import datetime
from pprint import pprint  # pylint: disable=unused-import
from statistics import mean, median

import date_helpers as dh
import redis_helper as redh
import hood

_OUTPUT_FOLDER = config.conf.output_csv_path
_OPTIONS_CSV_FILE = config.conf.options_symbols_csv_path


def read_csv(file_path, delimiter="\t"):
    with open(file_path, "r", encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=delimiter)
        return list(csv_reader)


def write_to_csv(file_path, data, delimiter="\t"):
    with open(file_path, "a", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=delimiter)
        csv_writer.writerow(data)


def get_all_options():
    return [tokens[0] for tokens in read_csv(_OPTIONS_CSV_FILE)]


class IvScraper:
    """
    1. Scrapes implied volatility of options closest to
    at the money (minimum 4). E.g. for stock at $99.5
    with $1 strikes it will look at: 99C, 100C, 99P, 100P

    2. CSV structure (no header):
    SYMBOL, EXPR, PRICE, AVG IV, MEDIAN IV, STRIKES, TIMESTAMP

    Example:
    SPY, 2023-07-11, 438.71, 0.0920215, 0.0916695, 438C 439C 438P 439P, 1688891462

    3. Dynamically generates blacklist assuming options not
    available on designated platform (robinhood in this case).
    """

    # scrape attempts assuming network/rate limit/etc errors
    retry_count = 3
    retry_sleep = 1

    # failures are stored in redis. if number of failures exceeds this value
    # the symbol is blacklisted. blacklist will be periodically purged
    __blacklist = []
    blacklist_threshold = retry_count * 5

    @classmethod
    def exec(cls):
        csv_path = os.path.join(
            _OUTPUT_FOLDER, str(round(datetime.timestamp(datetime.utcnow()))) + ".csv"
        )

        exprs = ExpirationDateMapper.get_all_exprs()
        for ticker in get_all_options():
            scraper = cls(ticker, exprs.get(ticker))
            scraper.scrape()
            if line := scraper.format_line():
                write_to_csv(csv_path, line)

    def __init__(self, ticker, expr):
        self.ticker = ticker
        self.expr = expr or ExpirationDateMapper(ticker).get_set_expr()

        self.price = -1
        self.strikes = []
        self.ivs = []
        self.timestamp = -1

        # initialize blacklist once via class variable
        # if blacklist isn't initialized, insert a dummy symbol
        # to guarantee single fetch per runtime
        if not IvScraper.__blacklist:
            IvScraper.__blacklist = self.blacklisted_tickers() or ["1X2Y3Z4"]

    def scrape(self):
        if self.ticker in self.__blacklist:
            return None

        res = []
        fail_count = 0
        for _ in range(self.retry_count):
            if not (res := hood.condensed_option_chain(self.ticker, self.expr)):
                fail_count += 1
                time.sleep(self.retry_sleep)
                continue

            self.process_chain(res)
            break

        if fail_count > 0:
            redh.blacklist_append(self.ticker, fail_count)

        return None

    def process_chain(self, chain, depth=1):
        self.price = hood.get_price(self.ticker)
        if self.price:
            sorted_chain = sorted(
                chain, key=lambda x: abs(float(self.price) - float(x["strike_price"]))
            )
            for i, o in enumerate(sorted_chain):
                if (strike := o.get("strike_price")) and (o_type := o.get("type")):
                    postfix = "C" if o_type.lower() == "call" else "P"
                    self.strikes.append(f"{round(float(strike),2)}{postfix}")
                if (iv := o.get("implied_volatility")) and i < 4 * depth:
                    self.ivs.append(float(iv))

    # SYMBOL, EXPR, PRICE, AVG IV, MEDIAN IV, STRIKES, TIMESTAMP
    def format_line(self):
        if not self.ivs:
            return []

        return [
            self.ticker,
            self.expr,
            self.price,
            str(mean(self.ivs)),
            str(median(self.ivs)),
            " ".join(self.strikes),
            str(dh.absolute_seconds_until_expr(self.expr)),
        ]

    def blacklisted_tickers(self):
        d = redh.blacklist_all_failure_counts()
        return [k for k, v in d.items() if int(v) >= self.blacklist_threshold]


class ExpirationDateMapper:
    """
    1. Designates which expiration date to look at
    for each symbol:

    a. Monthlies
    b. Weeklies
    c. Semi-weeklies
    d. Dailies

    2. Scraper is intended to fetch IV relative to
    the closest expiration date except on the
    expiration date itself. I.e if it's a friday
    when weeklies generally expire, the scraper
    will collect next friday's data.

    Since semi-weeklies / dailies comprise only a
    handful of symbols (ETFs mostly) they will
    remain hardcoded for the time being.

    3. The mapper should be purged / initialized
    weekly as securities occassionaly drift between
    weekly <-> monthly buckets. Generally best done
    on Sunday because symbols CSVs are processed on
    Saturdays and uploaded to git by Saturday evening:

    https://github.com/melder/symbols_options_csvs

    Semi-weeklies + dailies expirations should be
    updated end of day after market close.
    """

    # scrape attempts assuming network/rate limit/etc errors
    retry_count = 5
    retry_sleep = 15

    # some duplication from IvScraper class
    # TODO: add blacklist class?
    __blacklist = []
    blacklist_threshold = IvScraper.blacklist_threshold

    semi_weeklies = ["IWM"]
    dailies = ["SPY", "QQQ"]

    @classmethod
    def populate(cls):
        for ticker in get_all_options():
            cls(ticker).get_set_expr()

    # TODO: purge weeklies / monthlies separately
    @classmethod
    def purge(cls):
        redh.purge_expr_dates()

    @classmethod
    def get_all_exprs(cls):
        return redh.get_all_expr_dates()

    def __init__(self, ticker):
        self.ticker = ticker

        if not ExpirationDateMapper.__blacklist:
            ExpirationDateMapper.__blacklist = self.blacklisted_tickers() or ["1X2Y3Z4"]

    # TODO: clean this shit up
    def get_set_expr(self):
        if self.ticker not in self.__blacklist:
            for _ in range(self.retry_count):
                if res := dh.next_expr_for_ticker(self.ticker):
                    if self.ticker not in (self.semi_weeklies + self.dailies):
                        redh.set_expr_date(self.ticker, res)
                    return res
                time.sleep(self.retry_sleep)

    def blacklisted_tickers(self):
        d = redh.blacklist_all_failure_counts()
        return [k for k, v in d.items() if int(v) >= self.blacklist_threshold]


if __name__ == "__main__":
    COMMANDS = ["scrape", "scrape-force", "purge-exprs"]
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python scraper.py <{' / '.join(COMMANDS)}>")
        sys.exit(0)

    if sys.argv[1] in ["scrape", "scrape-force"]:
        if not dh.is_market_open_now() and sys.argv[1] == "scrape":
            print("Market is closed")
            sys.exit(0)
        IvScraper.exec()
        sys.exit(0)

    if sys.argv[1] == "purge-exprs":
        exprs = [v for _, v in redh.get_all_expr_dates().items()]
        if datetime.now().date().isoformat() in exprs:
            ExpirationDateMapper.purge()
        sys.exit(0)

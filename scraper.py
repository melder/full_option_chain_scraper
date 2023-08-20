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


class Blacklist:
    """
    Filter out symbols that violate blacklist rules:

    1. Brokerage did not return options for SYMBOL
    2. Price of SYMBOL is less than $2.50 or greater than $1k

    More rules to come for sure

    Also has "audit" method to de-blacklist symbols that no
    longer violate rules
    """

    threshold = 15
    rule_1_scrape_fail_score = 3
    rule_2_bad_price_score = 1

    # in cents
    price_min = 500
    price_max = 100000
    price_range = range(price_min, price_max + 1)

    # Blacklist from blacklist
    blacklist_exempt = ["SPCE", "SNDL", "FCEL", "TLRY", "AMC", "BB", "NOK"]

    @classmethod
    def audit(cls):
        """
        remove symbols that no longer violate blacklist rules
        """

        global ignore_backlist  # pylint: disable=global-statement
        ignore_backlist = True

        for ticker in [k for k, _ in blacklist.items()]:
            scraper = IvScraper(ticker, expr=None)
            scraper.scrape()

            # blacklisted from blacklist
            if ticker in cls.blacklist_exempt:
                redh.blacklist_remove_ticker(ticker)
                continue

            # rule 1
            if not scraper.ivs:
                continue

            # rule 2
            if round(scraper.price * 100) not in cls.price_range:
                continue

            redh.blacklist_remove_ticker(ticker)

    def __init__(self, scraper_obj):
        """
        ticker data is a hash comprising of scraped data
        """
        self.scraper_obj = scraper_obj
        self.ticker = scraper_obj.ticker
        self.score = 0

    def exec(self):
        # TODO: this hurts my eyes to look at
        if not ignore_backlist and self.ticker not in self.blacklist_exempt:
            self.scrape_fail()
            if self.score == 0:  # failed scrape won't have price data
                self.extreme_price()
            if self.score > 0:
                self.add_to_blacklist()

    def add_to_blacklist(self):
        """
        score is value on how aggressively a symbol should
        be blacklisted. For example failure to retrieve symbol
        data could imply a network error rather than there
        are simply no options available for it. A score is
        associated and incremented to each symbol and once
        it breaches a threshold it is no longer scraped
        """
        redh.blacklist_append(self.ticker, self.score)

    # rule 1
    def scrape_fail(self):
        if not self.scraper_obj.ivs:
            self.score += self.rule_1_scrape_fail_score

    # rule 2
    def extreme_price(self):
        if round(self.scraper_obj.price * 100) not in self.price_range:
            self.score += self.rule_2_bad_price_score


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

    @classmethod
    def exec(cls):
        csv_path = os.path.join(
            _OUTPUT_FOLDER, str(round(datetime.timestamp(datetime.utcnow()))) + ".csv"
        )

        exprs = ExpirationDateMapper.get_all_exprs()
        for ticker in get_all_options():
            if not ignore_backlist and ticker in blacklisted_tickers:
                continue
            # try:
            scraper = cls(ticker, exprs.get(ticker))
            scraper.scrape()
            if line := scraper.format_line():
                write_to_csv(csv_path, line)
            Blacklist(scraper).exec()
            # except Exception:  # pylint: disable=broad-exception-caught
            #     # TODO: add some logging
            #     pass

    def __init__(self, ticker, expr):
        self.ticker = ticker
        self.expr = expr or ExpirationDateMapper(ticker).get_set_expr()

        self.price = -1
        self.strikes = []
        self.ivs = []
        self.timestamp = -1

    def scrape(self):
        if not (self.ticker and self.expr):
            return None

        res = []
        # for _ in range(self.retry_count):
        if not (res := hood.condensed_option_chain(self.ticker, self.expr)):
            # time.sleep(self.retry_sleep)
            raise Exception("Error fetching option chain")

        self.process_chain(res)
        return True

        return None

    def process_chain(self, chain, depth=1):
        if price := hood.get_price(self.ticker):
            self.price = float(price)
            sorted_chain = sorted(
                chain, key=lambda x: abs(self.price - float(x["strike_price"]))
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
            str(self.price),
            str(mean(self.ivs)),
            str(median(self.ivs)),
            " ".join(self.strikes),
            str(dh.absolute_seconds_until_expr(self.expr)),
        ]

    def scrape_and_write(self, timestamp):
        csv_path = os.path.join(_OUTPUT_FOLDER, str(timestamp) + ".csv")
        self.scrape()
        if line := self.format_line():
            write_to_csv(csv_path, line)


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

    # special cases
    semi_weeklies = ["IWM"]
    dailies = ["SPY", "QQQ"]

    # scrape attempts assuming network/rate limit/etc errors
    retry_count = 3
    retry_sleep = 1

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

    @classmethod
    def get_all_exprs_dates(cls, compress=False):
        res = [v for _, v in cls.get_all_exprs().items()]
        return res if not compress else list(set(res))

    def __init__(self, ticker):
        self.ticker = ticker
        if ignore_backlist:
            self.retry_sleep = 1
            self.retry_count = 3

    def get_set_expr(self):
        if not ignore_backlist and self.ticker in blacklisted_tickers:
            return None

        for _ in range(self.retry_count):
            if res := dh.next_expr_for_ticker(self.ticker):
                if self.ticker not in (self.semi_weeklies + self.dailies):
                    redh.set_expr_date(self.ticker, res)
                return res
            time.sleep(self.retry_sleep)

        return None


blacklist = redh.blacklist_all_failure_counts()
blacklisted_tickers = [k for k, v in blacklist.items() if int(v) >= Blacklist.threshold]

# TODO: gut feeling that this is poor design. rethink this
ignore_backlist = False  # pylint: disable=invalid-name

if __name__ == "__main__":
    COMMANDS = ["scrape", "scrape-force", "purge-exprs", "audit-blacklist"]
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
        TODAY_DATE_ISO = datetime.now().date().isoformat()
        if TODAY_DATE_ISO in ExpirationDateMapper.get_all_exprs_dates():
            ExpirationDateMapper.purge()
        sys.exit(0)

    if sys.argv[1] == "audit-blacklist":
        Blacklist.audit()
        sys.exit(0)

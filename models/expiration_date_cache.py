import time
from helpers import redis_helpers as redh
from helpers import date_helpers as dh
from models.blacklist import Blacklist


class ExpirationDateCache:
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
    retry_count = 15
    retry_sleep = 10.1

    @classmethod
    def populate(cls, tickers):
        for ticker in tickers:
            print(ticker)
            cls(ticker).get_expr()

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

    def __init__(self, ticker, ignore_blacklist=False):
        self.ticker = ticker
        self.ignore_blacklist = ignore_blacklist

    def get_expr(self):
        if not self.ignore_blacklist and self.ticker in Blacklist.blacklisted_tickers():
            return None
        return redh.get_expr_date(self.ticker) or self.get_set_expr()

    def get_set_expr(self):
        if not self.ignore_blacklist and self.ticker in Blacklist.blacklisted_tickers():
            return None

        for _ in range(self.retry_count):
            if res := dh.next_expr_for_ticker(self.ticker):
                if self.ticker not in (self.semi_weeklies + self.dailies):
                    redh.set_expr_date(self.ticker, res)
                return res
            time.sleep(self.retry_sleep)

        return None

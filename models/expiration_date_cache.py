import time
from helpers import redis_helpers as redh
from helpers import date_helpers as dh


class ExpirationDateCache:
    """
    1. Designates which expiration date to look at
    for each symbol

    2. Scraper is intended to fetch IV relative to
    the closest expiration date except on the
    expiration date itself. I.e if it's a friday
    when weeklies generally expire, the scraper
    will collect next friday's data

    3. The mapper should be purged / initialized
    weekly as securities occassionaly drift between
    weekly <-> monthly buckets. Generally best done
    on Sunday because symbols CSVs are processed on
    Saturdays and uploaded to git by Saturday evening:

    https://github.com/melder/symbols_options_csvs
    """

    # scrape attempts assuming network/rate limit/etc errors
    retry_count = 10
    retry_sleep = 10.1

    @classmethod
    def populate(cls, tickers):
        for ticker in tickers:
            print(ticker)
            cls(ticker).get_expr()

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

    def get_expr(self):
        return redh.get_expr_date(self.ticker) or self.get_set_expr()

    def get_set_expr(self):
        for _ in range(self.retry_count):
            if res := dh.next_expr_for_ticker(self.ticker):
                redh.set_expr_date(self.ticker, res)
                return res
            time.sleep(self.retry_sleep)

        return None

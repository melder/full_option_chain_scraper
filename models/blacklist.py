from helpers import redis_helpers as redh


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
    price_min = 250
    price_max = 100000
    price_range = range(price_min, price_max + 1)

    # Blacklist from blacklist
    blacklist_exempt = ["SPCE", "SNDL", "FCEL", "TLRY", "AMC", "BB", "NOK"]

    @classmethod
    def blacklisted_tickers(cls):
        res = redh.blacklist_all_failure_counts()
        return [k for k, v in res.items() if int(v) >= Blacklist.threshold]

    @classmethod
    def audit(cls):
        """
        remove symbols that no longer violate blacklist rules
        """

        # TODO: circular dependencyish, need to rethink
        from scraper import IvScraper

        for ticker in redh.blacklisted_tickers():
            print(ticker)
            # blacklisted from blacklist
            if ticker in cls.blacklist_exempt:
                redh.blacklist_remove_ticker(ticker)
                continue

            scraper = IvScraper(
                ticker,
                expr=None,
            )

            # rule 1
            if not scraper.scrape():
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
        self.score = 0

    def exec(self):
        if self.scraper_obj.ticker in self.blacklist_exempt:
            return 0

        self.scrape_fail()
        self.extreme_price()

        if self.score > 0:
            self.add_to_blacklist()

        return self.score

    def add_to_blacklist(self):
        """
        score is value on how aggressively a symbol should
        be blacklisted. For example failure to retrieve symbol
        data could imply a network error rather than there
        are simply no options available for it. A score is
        associated and incremented to each symbol and once
        it breaches a threshold it is no longer scraped
        """
        redh.blacklist_append(self.scraper_obj.ticker, self.score)

    # rule 1
    def scrape_fail(self):
        if not self.scraper_obj.scraped:
            self.score += self.rule_1_scrape_fail_score

    # rule 2
    def extreme_price(self):
        if (
            self.scraper_obj.price
            and round(self.scraper_obj.price * 100) not in self.price_range
        ):
            self.score += self.rule_2_bad_price_score

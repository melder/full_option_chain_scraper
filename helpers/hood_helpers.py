import robin_stocks.robinhood as rh
from helpers import auth

auth.hood()

_MIC = "XNYS"  # NYSE market code


def get_market_hours(iso_date):
    return rh.get_market_hours(_MIC, iso_date)


def get_price(ticker):
    return rh.stocks.get_latest_price(ticker)[0]


def get_tradable_options(ticker, expr, option_type=None):
    return rh.find_tradable_options(ticker, expr, optionType=option_type)


def get_chains(ticker):
    return rh.options.get_chains(ticker)


def get_option_chain(ticker, expr, option_type=None):
    if option_type is None or option_type not in ["call", "put"]:
        return rh.options.find_options_by_expiration(ticker, expr)

    return rh.options.find_options_by_expiration(ticker, expr, optionType=option_type)


def get_option_chain_by_strike(ticker, expr, strike):
    try:
        return rh.options.find_options_by_expiration_and_strike(ticker, expr, strike)
    except AttributeError as err:
        print(f"Unexpected {err=}, {type(err)=}")
        print(f"Failed to get option chain data for {ticker}")
        return []
    except TypeError as err:
        print(f"Unexpected {err=}, {type(err)=}")
        print(f"Failed to get option chain data for {ticker}")
        return []


def condensed_option_chain(ticker, expr):
    try:
        strike1, strike2 = closest_strikes_to_price(ticker, expr)
        if not (strike1 and strike2):
            return []
        res = get_option_chain_by_strike(ticker, expr, strike1)
        res += get_option_chain_by_strike(ticker, expr, strike2)
        return res if len(res) == 4 else []
    except (ValueError, ConnectionError):
        return []


def closest_strikes_to_price(ticker, expr):
    try:
        price = float(get_price(ticker))
        options = get_tradable_options(ticker, expr, option_type="call")
        if list(filter(None, options)):
            return list(
                map(
                    lambda x: x["strike_price"],
                    sorted(
                        options, key=lambda o: abs(price - float(o["strike_price"]))
                    ),
                )
            )[:2]
    except TypeError as err:
        print(f"Unexpected {err=}, {type(err)=}")
        print(f"Failed to get option chain data for {ticker}")
    return [None, None]

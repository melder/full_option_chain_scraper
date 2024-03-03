from config import config  # pylint: disable=wrong-import-order
from helpers.general_helpers import key_join

r = config.redis_client()


_NAMESPACE = config.namespace


###########################
# OPTION EXPIRATION DATES #
###########################

_EXPIRATION_DATE_KEY = key_join(_NAMESPACE, "expr")


def get_all_expr_dates():
    return r.hgetall(_EXPIRATION_DATE_KEY)


def get_expr_date(ticker):
    return r.hget(_EXPIRATION_DATE_KEY, ticker)


def set_expr_date(ticker, expr):
    return r.hset(_EXPIRATION_DATE_KEY, ticker, expr)


def purge_expr_dates():
    r.delete(_EXPIRATION_DATE_KEY)


#####################
# AUXILIARY HELPERS #
#####################


def purge_glob(glob):
    for k in r.keys(glob):
        r.delete(k)

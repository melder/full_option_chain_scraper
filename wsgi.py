from collections import defaultdict
from flask import Flask, jsonify, request
from models.option import Option

app = Flask(__name__)


@app.route("/")
def hello_world():
    data = {"results": "test"}
    return jsonify(data)


@app.route("/option_chains")
def option_chains():
    expr = request.args.get("expr") or request.args.get("expiration")
    ticker = request.args.get("ticker")
    timestamp = request.args.get("timestamp")

    if not (expr and ticker):
        return jsonify("Missing required parameters 'expr' and/or 'ticker'"), 400

    _filter = {"ticker": ticker, "expiration": expr}
    if timestamp:
        _filter["scraper_timestamp"] = timestamp

    query = list(
        Option()
        .collection.find(
            _filter,
            {
                "_id": 0,
                "scraper_timestamp": 1,
                "price": 1,
                "options.type": 1,
                "options.strike_price": 1,
                "options.volume": 1,
                "options.open_interest": 1,
            },
        )
        .sort("scraper_timestamp", 1)
    )

    data = {}
    for doc in query:
        scraper_timestamp = doc.get("scraper_timestamp")
        if not scraper_timestamp:
            continue

        data[scraper_timestamp] = {}
        data[scraper_timestamp]["price"] = doc.get("price", 0)
        data[scraper_timestamp]["strikes"] = defaultdict(dict)

        for option in doc["options"]:
            if not (strike := option.get("strike_price")):
                continue

            data[scraper_timestamp]["strikes"][float(strike)] |= {
                option["type"]: {
                    "volume": option.get("volume", 0),
                    "open_interest": option.get("open_interest", 0),
                }
            }

    res = {}
    res["ticker"] = ticker
    res["expiration"] = expr
    res["data"] = data
    res["count"] = len(query)
    res["status"] = 200

    return res


@app.route("/expirations")
def expirations():
    query = Option().collection.distinct("expiration")

    res = {}
    res["data"] = sorted(query)
    res["count"] = len(query)
    res["status"] = 200

    return res


@app.route("/timestamps")
def timestamps():
    expr = request.args.get("expr") or request.args.get("expiration")
    if not expr:
        return jsonify("Missing required parameters 'expr'"), 400

    query = Option().collection.find({"expiration": expr}).distinct("scraper_timestamp")

    res = {}
    res["expiration"] = expr
    res["data"] = sorted(list(map(int, query)))
    res["count"] = len(query)
    res["status"] = 200

    return res


## Uncomment if testing locally
# @app.after_request
# def add_header(response):
#     response.headers["Access-Control-Allow-Origin"] = "*"
#     return response

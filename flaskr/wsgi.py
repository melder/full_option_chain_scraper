from flask import Flask, jsonify, request
from models import option

app = Flask(__name__, instance_relative_config=True)


@app.route("/")
def hello_world():
    data = {"results": "test"}
    return jsonify(data)


@app.route("/option_chains")
def option_chains():
    expr = request.args.get("expr")
    ticker = request.args.get("ticker")

    if not (expr and ticker):
        return "Missing required parameters 'expr' and/or 'ticker'", 400

    return list(
        option.Option().collection.find(
            {"ticker": ticker, "expiration": expr},
            {
                "ticker": 1,
                "expiration": 1,
                "options.volume": 1,
                "options.open_interest": 1,
            },
        )
    )

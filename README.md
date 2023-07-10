# IV Scraper

Iterates through all available options and scrapes implied volatility values of the 4 options closest to the spot price (calls + puts above/below spot). Outputs average and median value to a CSV file. Default expiration date is the earliest one. So for a weekly it's generally friday. For a daily (SPY, QQQ) it will be the next market day. Scraper will collect IV data up to the day of expiration. On expiration day it will roll over to next expiration date. Using weeklies as an example: if run on Friday (the day the option expires) the scraper will instead scrape the option chain expiring on the next Friday.

**Note** that this is in prototype phase and has some circular design issues + poor optimization

## Motivation

The only unquantifiable variable in the price of an option (or premium) is its volatility. The premium - what people are willing to pay - is essentially mass speculation of the future price movement of an option's underlying security. In essence the volatility is quantified by the premium itself, hence "implied" volatility. This can potentially be exploited since periods of unusually high or low _realized_ volatility tends to regress to the mean.

Simply put:

1. During periods of unusually low volatility it is better to go long (or buy) options since they are _relatively_ cheap
2. Likewise when volatility is unusually high it is better to go short (or sell) options since they are _relatively_ expensive

Delta neutral option strategies for each:

1. Long: straddle, strangle
2. Short: iron condor / butterfly

A nice feature of these strategies is they don't require much equity. A few hundred dollars is enough to experiment for a while assuming good discipline and average luck.

Hopefully the motivation is more clear now: to construct a granular history of implied volatility data with the objective of better identifying periods of high and low volatility. And since the data intends to be very comprehensive (tracks every stock that offers options), it will hopefully enable all sorts of creative analysis.

## Requirements

1. Python 3.11.4
2. pipenv
3. redis7 server
4. robinhood account with options enabled
5. Optional: AWS east instance. API requests are about 2-3x faster than running local

## Installation

TBD

## Configurations:

### settings.yml

```
version: 0.0.1
options_symbols_csv_path: "./csv/options.csv"
output_csv_path: "./out"
```

### vendors.yml

```
hood:
  login: melder@example.com
  password: password
  my2fa: ABCD
  pickle_name: rick

redis:
  host: localhost
  port: 6379
```

### crontab

TBD
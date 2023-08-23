# IV Scraper

* Iterates through all available options and scrapes implied volatility values of the 4 options closest to the spot price (calls + puts above/below spot). 
* For those options stores their data in mongodb (IV, greeks, expiration, volume, open interest, bids / asks + prices, and much more ...)
* Default expiration date is set to nearest one. So for a weekly it's generally friday. For a daily (SPY, QQQ) it will be the next market day. Scraper will collect IV data up to the day of expiration. On expiration day it will roll over to next expiration date. Using weeklies as an example: if run on Friday (the day the option expires) the scraper will instead scrape the option chain expiring on the next Friday.
* Scraper uses multiprocessing for higher throughput. Set workers to > 1 in settings.yml


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
2. pyenv + pipenv
3. redis7 server
4. mongodb7 (feel free to fork if you prefer implementing a different DB)
5. robinhood account with options enabled
6. Optional: server with high # of CPU cores for fast scraping (6 core server throughput of 2k options / minute)


## Installation

1. Install pyenv / python 3.11.4 / pipenv
2. Clone, init environment, init submodules:

```
git clone git@github.com:melder/iv_scraper.git
cd iv_scraper
git submodule update --init --recursive
pipenv install
```

3. In the config directory create settings.yml / vendors.yml and set them up with the appropriate values
4. To test

```
$ pipenv shell
$ python scraper.py scrape
```

## Commands

* scrape - self explanitory
* scrape-force - scrapes regardless of market open status
* populate-exprs - retrieving expirations is API heavy so cache is utilized. This is intended to prepopulate before scraping to avoid rate limit slowdowns
* purge-exprs - Deletes expiration date cache on weekly / monthly expiration days
* audit-blacklist - iterates through blacklisted items to see if any should be rotated out

## Configuration

### settings.yml

```
options_symbols_csv_path: "./csv/options.csv"
workers: 6
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

mongo:
  host: localhost
  port: 27017
  database: scraper
```

### crontab example

```
# FYI some distros don't support CRON_TZ

CRON_TZ=America/New_York

45 9-15 * * 1-5 ec2-user cd ~/iv_scraper; pipenv run python scraper.py scrape
*  1    * * 1-5 ec2-user cd ~/iv_scraper; pipenv run python scraper.py purge-exprs
1  2    * * 1-5 ec2-user cd ~/iv_scraper; pipenv run python scraper.py populate-exprs
0  20   * * 0   ec2-user cd ~/iv_scraper; pipenv run python scraper.py audit-blacklist
```

Notes:

1. Scraper will only scrape when market is open (unless using scrape-force command)
2. Expiration dates cache will only be purged on the day of expiration. Since it is a very lightweight operation, it is set to run every minute for an hour to greatly reduce odds that cache persists and messes things up.

## Background Jobs

**Note:** scrape command performs all the queueing and then launching the workers (in sequence). But if you have personal preference on how to run the job processor scrape can be substituted with the following:

```
# queuing: 
python queue_jobs.py

# run workers
# X = number of parallel workers
rq worker-pool -b -n X
```

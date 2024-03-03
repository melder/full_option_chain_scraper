# Full option chain scraper

* Iterates through specified tickers and scrapes entire option chain for those tickers
* Store option chain data in MDB
* Currently only works on weeklies
* Scraper uses multiprocessing for higher throughput. Set workers to > 1 in settings.yml

## Motivation

This is a fork of https://github.com/melder/iv_scraper but it scrapes entire option chain of a small set of stocks (instead of scraping 4 option chains closest to current stock price for all stocks that offers options).

The idea is to construct a series of volume / open interest over time to attempt to isolate "smart" money plays. In this case I'm trying to look into cryptocurrency related stocks / option chains because crypto is ripe and legal for manipulation. However this can be configured to track any collection of stocks.

**Since option chains can be very large it isn't recommended to track more than a couple dozen at a time**

## Requirements

1. Python 3.12.2
2. pyenv + pipenv
3. redis7 server
4. mongodb7 (feel free to fork if you prefer implementing a different DB)
5. robinhood account with options enabled
6. Optional: server with high # of CPU cores for fast scraping (6 core server throughput of 2k options / minute)


## Installation

1. Install pyenv / python 3.12.2 / pipenv
2. Clone, init environment, init submodules:

```
git clone git@github.com:melder/full_option_chain_scraper.git
cd full_option_chain_scraper
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

## Configuration

### settings.yml

```
namespace: option_chain_scraper
workers: 3
crypto_tickers:
  - MSTR
  - COIN
  - BITO
  - MARA
  - CLSK
  - RIOT
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
  password: pass # optional

mongo:
  host: localhost
  port: 27017
  database: production
  username: user        # optional
  password: pass        # optional
  auth_source: auth_db  # optional
```

### crontab example

```
# FYI some distros don't support CRON_TZ

CRON_TZ=America/New_York

*/2  9-16    * * 1-5 ec2-user cd ~/full_option_chain_scraper; pipenv run python scraper.py scrape
2    16      * * 1-5 ec2-user cd ~/full_option_chain_scraper; pipenv run python scraper.py scrape-force
*    1       * * 1-5 ec2-user cd ~/full_option_chain_scraper; pipenv run python scraper.py purge-exprs
1    2       * * 1-5 ec2-user cd ~/full_option_chain_scraper; pipenv run python scraper.py populate-exprs
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

rq worker-pool -b <namespace> -n X

# osx:

OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES rq worker-pool -b <namespace> -n 5
```

# pylint: skip-file
# TODO: migrate constants to config
import os
import yaml


def parse_yaml_vendors():
    with open("config/vendors.yml", "r") as f:
        return yaml.safe_load(f)


def parse_yaml_settings():
    with open("config/settings.yml", "r") as f:
        return yaml.safe_load(f)


class DictAsMember(dict):
    """
    Converts yml to attribute for cleaner access
    """

    def __getattr__(self, name):
        value = self[name]
        if isinstance(value, dict):
            value = DictAsMember(value)
        return value


conf = DictAsMember(parse_yaml_settings() | parse_yaml_vendors())

namespace = conf.namespace
crypto_tickers = conf.crypto_tickers

if conf.get("redis"):
    import redis as r

    redis_host = conf.redis.host
    redis_port = conf.redis.port
    redis_password = conf.redis.get("password")

    if redis_password:
        redis_cli = r.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True,
        )
        redis_worker = r.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=False,
        )
    else:
        redis_cli = r.Redis(host=redis_host, port=redis_port, decode_responses=True)
        redis_worker = r.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=False,
        )


def redis_client(decode_responses=True):
    if not conf.get("redis"):
        return None

    if decode_responses:
        return redis_cli

    return redis_worker


def mongo_client():
    if not conf.get("mongo"):
        return None

    import pymongo

    mongo_username = conf.mongo.get("username")
    mongo_password = conf.mongo.get("password")
    mongo_authsource = conf.mongo.get("authsource")

    if mongo_username and mongo_password and mongo_authsource:
        mongo_cli = pymongo.MongoClient(
            conf.mongo.host,
            conf.mongo.port,
            username=conf.mongo.username,
            password=conf.mongo.password,
            authSource=conf.mongo.auth_source,
        )
    else:
        mongo_cli = pymongo.MongoClient(
            conf.mongo.host,
            conf.mongo.port,
        )

    return mongo_cli


def mongo_db():
    if not conf.get("mongo"):
        return None
    return mongo_client()[conf.mongo.database]

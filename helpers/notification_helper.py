from config import config  # pylint: disable=wrong-import-order

import json
import random
import time
from datetime import datetime
from urllib import request
from pytz import timezone


_WEBHOOK_HEADERS = {
    "User-Agent": "PostmanRuntime/7.28.4",
    "Content-Type": "application/json",
}


class DiscordNotifier:
    """
    Notifications to Discord via webhooks
    """

    retry_count = 5

    @classmethod
    def anomaly_notifier(cls, config_key="anomaly"):
        webhook = config.discord_webhooks().get(config_key)
        if not webhook:
            raise DiscordNotifierException(f"{config_key} webhook not set!")

        return cls(webhook)

    def __init__(self, webhook, test_mode=False):
        self.webhook = webhook
        self.test_mode = test_mode

    def debug(self, msg):
        self.send_notification(f"DEBUG - {msg}")

    def info(self, msg):
        self.send_notification(f"INFO  - {msg}")

    def warn(self, msg):
        self.send_notification(f"WARN  - {msg}")

    def error(self, msg):
        self.send_notification(f"ERROR - {msg}")

    def fatal(self, msg):
        self.send_notification(f"FATAL - {msg}")

    def send_notification(self, msg):
        if self.test_mode:
            print(msg)
            return None

        t = datetime.now(timezone("US/Eastern")).isoformat(sep=" ")[:24]
        d = {"content": f"```({config.version}) [{t}] {msg}```"}
        data = str(json.dumps(d)).encode("utf-8")

        for _ in range(self.retry_count):
            try:
                req = request.Request(self.webhook, headers=_WEBHOOK_HEADERS, data=data)
                request.urlopen(req)
                break
            except Exception:
                time.sleep(random.randint(1, 5))

        return None


class DiscordNotifierException(Exception):
    def __init__(self, message):
        self.message = message

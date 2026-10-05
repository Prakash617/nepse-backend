"""Long-polling daemon for the NEPSE Telegram bot."""

import logging
import time

import requests
from django.core.management.base import BaseCommand

from apps.notifications.telegram import (
    TELEGRAM_API_BASE,
    get_telegram_token,
    process_telegram_update,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the Telegram Bot long-polling daemon to handle user links and commands."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Poll once for pending updates and exit.",
        )

    def handle(self, *args, **options):
        token = get_telegram_token()
        if not token:
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN is not configured."))
            return

        once = options["once"]
        self.stdout.write(self.style.SUCCESS("Starting Telegram Bot polling daemon..."))

        offset = 0
        while True:
            try:
                url = f"{TELEGRAM_API_BASE}{token}/getUpdates"
                params = {"offset": offset, "timeout": 20}
                res = requests.get(url, params=params, timeout=25)

                if res.status_code == 200:
                    data = res.json()
                    results = data.get("result", [])
                    for update in results:
                        update_id = update.get("update_id", 0)
                        offset = max(offset, update_id + 1)
                        result = process_telegram_update(update)
                        self.stdout.write(f"Processed update {update_id}: {result}")
                else:
                    self.stderr.write(f"Telegram API getUpdates returned status {res.status_code}")
                    time.sleep(3)

            except Exception as e:
                self.stderr.write(f"Error in Telegram polling loop: {e}")
                time.sleep(3)

            if once:
                break

"""Management command to sync daily prices from NEPSE."""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.prices.services import sync_daily_prices
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize daily prices from the NEPSE upstream API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--business-date",
            type=str,
            default=None,
            help="Business date in YYYY-MM-DD format (defaults to latest available).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and validate data without committing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        business_date = options.get("business_date")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be committed."))

        self.stdout.write("Fetching daily prices from NEPSE...")

        try:
            client = NepseClient()
            prices_data = client.get_today_prices(business_date=business_date)
        except NepseError as e:
            raise CommandError(f"Failed to fetch prices from NEPSE: {e}") from e

        self.stdout.write(f"Fetched {len(prices_data)} price records.")

        if dry_run:
            for p in prices_data[:5]:
                self.stdout.write(
                    f"  {p.get('symbol')}: LTP={p.get('ltp')}, "
                    f"Date={p.get('business_date')}"
                )
            if len(prices_data) > 5:
                self.stdout.write(f"  ... and {len(prices_data) - 5} more")
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes made."))
            return

        result = sync_daily_prices(prices_data)

        self.stdout.write(self.style.SUCCESS(
            f"Daily Prices:\n"
            f"  Created: {result.created}\n"
            f"  Updated: {result.updated}\n"
            f"  Skipped: {result.skipped}\n"
            f"  Failed: {result.failed}"
        ))

        if result.errors:
            for error in result.errors[:10]:
                self.stdout.write(self.style.WARNING(f"  Warning: {error}"))
            if len(result.errors) > 10:
                self.stdout.write(self.style.WARNING(
                    f"  ... and {len(result.errors) - 10} more warnings"
                ))

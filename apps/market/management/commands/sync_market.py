"""Management command to sync market snapshot from NEPSE."""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.market.services import sync_market_snapshot
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize market snapshot from the NEPSE upstream API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and validate data without committing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be committed."))

        self.stdout.write("Fetching market summary from NEPSE...")

        try:
            client = NepseClient()
            summary_data = client.get_market_summary()
        except NepseError as e:
            raise CommandError(f"Failed to fetch market summary from NEPSE: {e}") from e

        self.stdout.write(f"Market summary: volume={summary_data.get('total_traded_volume')}, "
                          f"value={summary_data.get('total_traded_value')}")

        if dry_run:
            for key, value in summary_data.items():
                self.stdout.write(f"  {key}: {value}")
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes made."))
            return

        result = sync_market_snapshot(summary_data)

        self.stdout.write(self.style.SUCCESS(
            f"Market Snapshot:\n"
            f"  Created: {result.created}\n"
            f"  Updated: {result.updated}\n"
            f"  Skipped: {result.skipped}\n"
            f"  Failed: {result.failed}"
        ))

        if result.errors:
            for error in result.errors:
                self.stdout.write(self.style.WARNING(f"  Warning: {error}"))

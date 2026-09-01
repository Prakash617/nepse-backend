"""Management command to sync market snapshot from NEPSE."""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.market.services import sync_market_snapshot, sync_market_snapshot_from_indices
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

        self.stdout.write("Fetching market data from NEPSE...")

        try:
            client = NepseClient()

            # Primary: use index history + summary history (reliable)
            result = sync_market_snapshot_from_indices(client)

            # If indices sync had no data, fall back to market summary
            if result.skipped and not result.created and not result.updated:
                self.stdout.write("Indices sync had no data, trying market summary...")
                summary_data = client.get_market_summary()
                self.stdout.write(
                    f"Market summary: volume={summary_data.get('total_traded_volume')}, "
                    f"value={summary_data.get('total_traded_value')}"
                )
                if not dry_run:
                    result = sync_market_snapshot(summary_data)
        except NepseError as e:
            raise CommandError(f"Failed to fetch market data from NEPSE: {e}") from e

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes made."))
            return

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

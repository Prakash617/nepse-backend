"""Management command to sync market indices from NEPSE."""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.indices.services import sync_indices
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize market indices from the NEPSE upstream API."

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

        self.stdout.write("Fetching indices from NEPSE...")

        try:
            client = NepseClient()
            # Fetch both NEPSE indices and sector indices
            nepse_indices = client.get_indices()
            sector_indices = client.get_sector_indices()
            all_indices = nepse_indices + sector_indices
        except NepseError as e:
            raise CommandError(f"Failed to fetch indices from NEPSE: {e}") from e

        self.stdout.write(f"Fetched {len(all_indices)} indices ({len(nepse_indices)} NEPSE + {len(sector_indices)} sector).")

        if dry_run:
            for idx in all_indices:
                self.stdout.write(f"  {idx.get('id')}: {idx.get('name')}")
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes made."))
            return

        result = sync_indices(all_indices)

        self.stdout.write(self.style.SUCCESS(
            f"Indices:\n"
            f"  Created: {result.created}\n"
            f"  Updated: {result.updated}\n"
            f"  Skipped: {result.skipped}\n"
            f"  Failed: {result.failed}"
        ))

        if result.errors:
            for error in result.errors:
                self.stdout.write(self.style.WARNING(f"  Warning: {error}"))

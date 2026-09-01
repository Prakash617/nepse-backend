"""Management command to sync sectors from NEPSE."""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.sectors.services import sync_sectors
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize sectors from the NEPSE upstream API."

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

        self.stdout.write("Fetching sectors from NEPSE...")

        try:
            client = NepseClient()
            sectors_data = client.get_sectors()
        except NepseError as e:
            raise CommandError(f"Failed to fetch sectors from NEPSE: {e}") from e

        self.stdout.write(f"Fetched {len(sectors_data)} sectors.")

        if dry_run:
            for s in sectors_data:
                self.stdout.write(f"  {s.get('id')}: {s.get('name')}")
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes made."))
            return

        result = sync_sectors(sectors_data)

        self.stdout.write(self.style.SUCCESS(
            f"Sectors:\n"
            f"  Created: {result.created}\n"
            f"  Updated: {result.updated}\n"
            f"  Skipped: {result.skipped}\n"
            f"  Failed: {result.failed}"
        ))

        if result.errors:
            for error in result.errors:
                self.stdout.write(self.style.WARNING(f"  Warning: {error}"))

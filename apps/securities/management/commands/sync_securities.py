"""Management command to sync securities from NEPSE."""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.securities.services import sync_securities
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize securities from the NEPSE upstream API."

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

        self.stdout.write("Fetching securities from NEPSE...")

        try:
            client = NepseClient()
            securities_data = client.get_securities()
        except NepseError as e:
            raise CommandError(f"Failed to fetch securities from NEPSE: {e}") from e

        self.stdout.write(f"Fetched {len(securities_data)} securities.")

        if dry_run:
            for s in securities_data[:10]:
                self.stdout.write(f"  {s.get('id')}: {s.get('symbol')} - {s.get('company_name')}")
            if len(securities_data) > 10:
                self.stdout.write(f"  ... and {len(securities_data) - 10} more")
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes made."))
            return

        result = sync_securities(securities_data)

        self.stdout.write(self.style.SUCCESS(
            f"Securities:\n"
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

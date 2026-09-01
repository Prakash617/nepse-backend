"""Management command to sync company profiles from NEPSE."""

import logging
import time

from django.core.management.base import BaseCommand, CommandError

from apps.fundamentals.services import sync_company_profiles
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize company profiles from the NEPSE upstream API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and validate data without committing to the database.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.1,
            help="Delay in seconds between requests to avoid rate limiting (default: 0.1).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        delay = options["delay"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be committed."))

        self.stdout.write("Fetching securities list from NEPSE...")

        try:
            client = NepseClient()
            securities = client.get_securities_simple()
        except NepseError as e:
            raise CommandError(f"Failed to fetch securities from NEPSE: {e}") from e

        self.stdout.write(f"Fetched {len(securities)} securities. Fetching profiles...")

        profiles_data = []
        failed_count = 0
        for i, sec in enumerate(securities):
            nepse_id = sec.get("id")
            if nepse_id is None:
                continue
            try:
                profile = client.get_company_profile(nepse_id)
                if isinstance(profile, dict):
                    profile["nepse_id"] = nepse_id
                    profiles_data.append(profile)
            except NepseError as e:
                failed_count += 1
                if failed_count <= 5:
                    self.stdout.write(self.style.WARNING(f"  Skipping {sec.get('symbol')}: {e}"))
                continue

            if (i + 1) % 50 == 0:
                self.stdout.write(f"  Processed {i + 1}/{len(securities)} ({len(profiles_data)} profiles)...")

            if delay > 0:
                time.sleep(delay)

        self.stdout.write(f"Fetched {len(profiles_data)} profiles ({failed_count} failed).")

        if dry_run:
            for p in profiles_data[:10]:
                self.stdout.write(f"  {p.get('nepse_id')}: {p.get('companyName', 'N/A')}")
            if len(profiles_data) > 10:
                self.stdout.write(f"  ... and {len(profiles_data) - 10} more")
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes made."))
            return

        result = sync_company_profiles(profiles_data)

        self.stdout.write(self.style.SUCCESS(
            f"Company Profiles:\n"
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

"""Management command to sync financial reports from NEPSE."""

import logging
import time

from django.core.management.base import BaseCommand, CommandError

from apps.fundamentals.services import sync_financial_reports
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize financial reports from the NEPSE upstream API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and validate data without committing to the database.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.15,
            help="Delay in seconds between requests (default: 0.15).",
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

        self.stdout.write(f"Fetched {len(securities)} securities. Fetching financials...")

        reports_data = []
        failed_count = 0
        for i, sec in enumerate(securities):
            nepse_id = sec.get("id")
            if nepse_id is None:
                continue
            try:
                financials = client.get_company_financials(nepse_id)
                for report in financials:
                    report["nepse_id"] = nepse_id
                    reports_data.append(report)
            except NepseError as e:
                failed_count += 1
                if failed_count <= 5:
                    self.stdout.write(self.style.WARNING(f"  Skipping {sec.get('symbol')}: {e}"))
                continue

            if (i + 1) % 50 == 0:
                self.stdout.write(f"  Processed {i + 1}/{len(securities)} ({len(reports_data)} reports)...")

            if delay > 0:
                time.sleep(delay)

        self.stdout.write(f"Fetched {len(reports_data)} financial reports ({failed_count} failed).")

        if dry_run:
            for r in reports_data[:10]:
                self.stdout.write(f"  {r.get('nepse_id')}: {r.get('fiscal_year')} ({r.get('report_type')})")
            if len(reports_data) > 10:
                self.stdout.write(f"  ... and {len(reports_data) - 10} more")
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes made."))
            return

        result = sync_financial_reports(reports_data)

        self.stdout.write(self.style.SUCCESS(
            f"Financial Reports:\n"
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

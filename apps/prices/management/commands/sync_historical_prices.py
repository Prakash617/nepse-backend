"""Management command to sync historical daily prices from NEPSE."""

import logging
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.prices.services import sync_historical_prices
from apps.securities.models import Security

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize historical daily prices from NEPSE for a date range."

    def add_arguments(self, parser):
        parser.add_argument(
            "--start",
            type=str,
            required=True,
            help="Start date in YYYY-MM-DD format.",
        )
        parser.add_argument(
            "--end",
            type=str,
            required=True,
            help="End date in YYYY-MM-DD format.",
        )
        parser.add_argument(
            "--symbols",
            type=str,
            nargs="*",
            default=None,
            help="Specific symbols to sync (e.g., NABIL NHPC). Defaults to all securities.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate inputs without fetching or persisting data.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        start_str = options["start"]
        end_str = options["end"]
        symbols_arg = options.get("symbols")

        # Validate dates
        try:
            start_date = date.fromisoformat(start_str)
        except ValueError as e:
            raise CommandError(
                f"Invalid start date: '{start_str}'. Use YYYY-MM-DD format."
            ) from e

        try:
            end_date = date.fromisoformat(end_str)
        except ValueError as e:
            raise CommandError(
                f"Invalid end date: '{end_str}'. Use YYYY-MM-DD format."
            ) from e

        if start_date > end_date:
            raise CommandError(
                f"Start date ({start_date}) must be before or equal to end date ({end_date})."
            )

        if start_date > date.today():
            raise CommandError(f"Start date ({start_date}) is in the future.")

        # Determine symbols
        if symbols_arg:
            symbols = [s.upper() for s in symbols_arg]
        else:
            symbols = list(
                Security.objects.order_by("symbol").values_list("symbol", flat=True)
            )

        if not symbols:
            raise CommandError("No securities found. Sync securities first.")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be committed."))
            self._print_summary(start_date, end_date, symbols)
            return

        self._print_summary(start_date, end_date, symbols)
        self.stdout.write("Fetching historical prices from NEPSE...")

        try:
            result = sync_historical_prices(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as e:
            raise CommandError(f"Historical sync failed: {e}") from e

        self.stdout.write(self.style.SUCCESS(
            f"Historical Prices:\n"
            f"  Created: {result.created}\n"
            f"  Updated: {result.updated}\n"
            f"  Skipped: {result.skipped}\n"
            f"  Failed: {result.failed}"
        ))

        if result.errors:
            for error in result.errors[:20]:
                self.stdout.write(self.style.WARNING(f"  Warning: {error}"))
            if len(result.errors) > 20:
                self.stdout.write(self.style.WARNING(
                    f"  ... and {len(result.errors) - 20} more warnings"
                ))

    def _print_summary(self, start_date: date, end_date: date, symbols: list[str]):
        self.stdout.write(
            f"\nHistorical Price Synchronization\n"
            f"  Date range: {start_date} → {end_date}\n"
            f"  Securities: {len(symbols)}\n"
        )
        if len(symbols) <= 10:
            for s in symbols:
                self.stdout.write(f"    - {s}")
        else:
            for s in symbols[:5]:
                self.stdout.write(f"    - {s}")
            self.stdout.write(f"    ... and {len(symbols) - 5} more")
        self.stdout.write("")

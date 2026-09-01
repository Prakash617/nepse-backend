"""Management command to check daily price data integrity."""

import logging

from django.core.management.base import BaseCommand
from django.db.models import Count, F, Max, Min, Q

from apps.prices.models import DailyPrice
from apps.securities.models import Security

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check daily price data for integrity issues."

    def handle(self, *args, **options):
        self.stdout.write("Checking daily price data integrity...\n")

        total_records = DailyPrice.objects.count()
        total_securities = DailyPrice.objects.values("security").distinct().count()

        if total_records == 0:
            self.stdout.write(self.style.WARNING("No daily price records found."))
            return

        # Date range
        stats = DailyPrice.objects.aggregate(
            earliest=Min("trading_date"),
            latest=Max("trading_date"),
        )
        earliest = stats["earliest"]
        latest = stats["latest"]

        self.stdout.write(f"Total records: {total_records}")
        self.stdout.write(f"Securities with history: {total_securities}")
        self.stdout.write(f"Date range: {earliest} → {latest}")
        self.stdout.write("")

        issues: list[str] = []

        # Check 1: Duplicate records (should be impossible due to constraint, but verify)
        duplicates = (
            DailyPrice.objects.values("security", "trading_date")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
        )
        dup_count = duplicates.count()
        if dup_count > 0:
            issues.append(f"DUPLICATE records found: {dup_count} duplicate pairs")
        else:
            self.stdout.write(self.style.SUCCESS("No duplicate records."))

        # Check 2: Prices without valid security
        orphan_count = DailyPrice.objects.filter(security__isnull=True).count()
        if orphan_count > 0:
            issues.append(f"Orphan records (no security): {orphan_count}")
        else:
            self.stdout.write(self.style.SUCCESS("All records have valid securities."))

        # Check 3: OHLC consistency (high >= low where both exist)
        bad_ohlc = DailyPrice.objects.filter(
            Q(high__isnull=False) & Q(low__isnull=False) & Q(high__lt=F("low"))
        ).count()
        if bad_ohlc > 0:
            issues.append(f"Records where high < low: {bad_ohlc}")
        else:
            self.stdout.write(self.style.SUCCESS("OHLC consistency: high >= low for all records."))

        # Check 4: Negative volume
        negative_volume = DailyPrice.objects.filter(
            Q(volume__isnull=False) & Q(volume__lt=0)
        ).count()
        if negative_volume > 0:
            issues.append(f"Records with negative volume: {negative_volume}")
        else:
            self.stdout.write(self.style.SUCCESS("No negative volume records."))

        # Check 5: Securities with no price history
        securities_without_history = Security.objects.exclude(
            id__in=DailyPrice.objects.values("security")
        ).count()
        if securities_without_history > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"Securities without price history: {securities_without_history}"
                )
            )

        # Check 6: Records with all null price fields
        all_null = DailyPrice.objects.filter(
            open__isnull=True,
            high__isnull=True,
            low__isnull=True,
            close__isnull=True,
            ltp__isnull=True,
        ).count()
        if all_null > 0:
            issues.append(f"Records with all null OHLC+LTP: {all_null}")
        else:
            self.stdout.write(self.style.SUCCESS("No records with all null prices."))

        # Summary
        self.stdout.write("")
        if issues:
            self.stdout.write(self.style.WARNING(f"Found {len(issues)} issue(s):"))
            for issue in issues:
                self.stdout.write(self.style.WARNING(f"  - {issue}"))
        else:
            self.stdout.write(self.style.SUCCESS("All integrity checks passed."))

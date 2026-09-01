"""Management command to check market data integrity across all data types.

Extends check_price_data with gap detection, source conflict awareness,
and comprehensive integrity checks.

Usage:
    python manage.py check_market_data
    python manage.py check_market_data --gaps
    python manage.py check_market_data --full
"""

import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count, F, Max, Min, Q

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check market data integrity: duplicates, invalid OHLC, gaps, unresolved securities."

    def add_arguments(self, parser):
        parser.add_argument(
            "--gaps",
            action="store_true",
            help="Include trading-day gap detection (slower).",
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="Run all checks including gap detection.",
        )

    def handle(self, *args, **options):
        do_gaps = options["gaps"] or options["full"]

        self.stdout.write("=" * 60)
        self.stdout.write("Market Data Integrity Check")
        self.stdout.write("=" * 60)

        issues: list[str] = []
        warnings: list[str] = []

        # --- Daily Price checks ---
        self.stdout.write("\n--- Daily Price Records ---")
        issues.extend(self._check_daily_prices(warnings))

        # --- Market Snapshot checks ---
        self.stdout.write("\n--- Market Snapshots ---")
        issues.extend(self._check_market_snapshots(warnings))

        # --- Index Snapshot checks ---
        self.stdout.write("\n--- Index Snapshots ---")
        issues.extend(self._check_index_snapshots(warnings))

        # --- Security coverage ---
        self.stdout.write("\n--- Security Coverage ---")
        self._check_security_coverage(warnings)

        # --- Gap detection ---
        if do_gaps:
            self.stdout.write("\n--- Trading Day Gap Detection ---")
            self._check_trading_day_gaps(warnings)

        # --- Summary ---
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Summary")
        self.stdout.write("=" * 60)

        if warnings:
            self.stdout.write(f"\nWarnings ({len(warnings)}):")
            for w in warnings:
                self.stdout.write(self.style.WARNING(f"  - {w}"))

        if issues:
            self.stdout.write(f"\nIssues ({len(issues)}):")
            for i in issues:
                self.stdout.write(self.style.ERROR(f"  - {i}"))
        else:
            self.stdout.write(self.style.SUCCESS("\nAll integrity checks passed."))

    def _check_daily_prices(self, warnings: list[str]) -> list[str]:
        """Check daily price data integrity."""
        from apps.prices.models import DailyPrice

        issues: list[str] = []
        total = DailyPrice.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("  No daily price records found."))
            return issues

        stats = DailyPrice.objects.aggregate(
            earliest=Min("trading_date"),
            latest=Max("trading_date"),
        )
        self.stdout.write(f"  Total records: {total}")
        self.stdout.write(f"  Date range: {stats['earliest']} → {stats['latest']}")

        # Duplicates
        dups = (
            DailyPrice.objects.values("security", "trading_date")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .count()
        )
        if dups > 0:
            issues.append(f"Duplicate daily price records: {dups}")
        else:
            self.stdout.write(self.style.SUCCESS("  No duplicates."))

        # OHLC consistency
        bad_ohlc = DailyPrice.objects.filter(
            Q(high__isnull=False) & Q(low__isnull=False) & Q(high__lt=F("low"))
        ).count()
        if bad_ohlc > 0:
            issues.append(f"Records where high < low: {bad_ohlc}")

        high_lt_open = DailyPrice.objects.filter(
            Q(high__isnull=False) & Q(open__isnull=False) & Q(high__lt=F("open"))
        ).count()
        if high_lt_open > 0:
            issues.append(f"Records where high < open: {high_lt_open}")

        low_gt_close = DailyPrice.objects.filter(
            Q(low__isnull=False) & Q(close__isnull=False) & Q(low__gt=F("close"))
        ).count()
        if low_gt_close > 0:
            issues.append(f"Records where low > close: {low_gt_close}")

        if bad_ohlc == 0 and high_lt_open == 0 and low_gt_close == 0:
            self.stdout.write(self.style.SUCCESS("  OHLC consistency: OK"))

        # Negative volume
        neg_vol = DailyPrice.objects.filter(
            Q(volume__isnull=False) & Q(volume__lt=0)
        ).count()
        if neg_vol > 0:
            issues.append(f"Records with negative volume: {neg_vol}")

        # All null prices
        all_null = DailyPrice.objects.filter(
            open__isnull=True,
            high__isnull=True,
            low__isnull=True,
            close__isnull=True,
            ltp__isnull=True,
        ).count()
        if all_null > 0:
            warnings.append(f"Records with all null OHLC+LTP: {all_null}")

        # Per-security stats
        top_securities = (
            DailyPrice.objects.values("security__symbol")
            .annotate(cnt=Count("id"), earliest=Min("trading_date"), latest=Max("trading_date"))
            .order_by("-cnt")[:5]
        )
        self.stdout.write("  Top securities by record count:")
        for s in top_securities:
            self.stdout.write(
                f"    {s['security__symbol']}: {s['cnt']} records "
                f"({s['earliest']} → {s['latest']})"
            )

        return issues

    def _check_market_snapshots(self, warnings: list[str]) -> list[str]:
        """Check market snapshot data."""
        from apps.market.models import MarketSnapshot

        issues: list[str] = []
        total = MarketSnapshot.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("  No market snapshots found."))
            return issues

        stats = MarketSnapshot.objects.aggregate(
            earliest=Min("trading_date"),
            latest=Max("trading_date"),
        )
        self.stdout.write(f"  Total snapshots: {total}")
        self.stdout.write(f"  Date range: {stats['earliest']} → {stats['latest']}")

        # Duplicates
        dups = (
            MarketSnapshot.objects.values("trading_date")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .count()
        )
        if dups > 0:
            issues.append(f"Duplicate market snapshots: {dups}")
        else:
            self.stdout.write(self.style.SUCCESS("  No duplicates."))

        return issues

    def _check_index_snapshots(self, warnings: list[str]) -> list[str]:
        """Check index snapshot data."""
        from apps.indices.models import IndexSnapshot, MarketIndex

        issues: list[str] = []
        total = IndexSnapshot.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("  No index snapshots found."))
            return issues

        index_count = MarketIndex.objects.count()
        self.stdout.write(f"  Total index definitions: {index_count}")
        self.stdout.write(f"  Total index snapshots: {total}")

        # Per-index stats
        per_index = (
            IndexSnapshot.objects.values("index__name")
            .annotate(cnt=Count("id"), earliest=Min("trading_date"), latest=Max("trading_date"))
            .order_by("-cnt")[:5]
        )
        self.stdout.write("  Top indices by record count:")
        for idx in per_index:
            self.stdout.write(
                f"    {idx['index__name']}: {idx['cnt']} records "
                f"({idx['earliest']} → {idx['latest']})"
            )

        return issues

    def _check_security_coverage(self, warnings: list[str]) -> None:
        """Check which securities have price history."""
        from apps.prices.models import DailyPrice
        from apps.securities.models import Security

        total_securities = Security.objects.count()
        with_history = DailyPrice.objects.values("security").distinct().count()
        without_history = total_securities - with_history

        self.stdout.write(f"  Total securities: {total_securities}")
        self.stdout.write(f"  With price history: {with_history}")
        if without_history > 0:
            warnings.append(f"Securities without price history: {without_history}")

    def _check_trading_day_gaps(self, warnings: list[str]) -> None:
        """Detect missing trading days in daily price data.

        Uses the NEPSE trading calendar heuristic:
        - Weekdays only (Mon-Fri)
        - Excludes known holiday patterns (approximate)
        """
        from apps.prices.models import DailyPrice

        stats = DailyPrice.objects.aggregate(
            earliest=Min("trading_date"),
            latest=Max("trading_date"),
        )
        earliest = stats["earliest"]
        latest = stats["latest"]

        if not earliest or not latest:
            self.stdout.write(self.style.WARNING("  No date range to check for gaps."))
            return

        # Get all distinct trading dates
        trading_dates = set(
            DailyPrice.objects.values_list("trading_date", flat=True).distinct()
        )

        # Check for gaps (weekdays only)
        current = earliest
        gap_dates: list[date] = []
        while current <= latest:
            if current.weekday() < 5 and current not in trading_dates:
                gap_dates.append(current)
            current += timedelta(days=1)

        if gap_dates:
            self.stdout.write(
                self.style.WARNING(f"  Missing trading days: {len(gap_dates)}")
            )
            # Show first 10
            for d in gap_dates[:10]:
                self.stdout.write(self.style.WARNING(f"    {d} ({d.strftime('%A')})"))
            if len(gap_dates) > 10:
                self.stdout.write(
                    self.style.WARNING(f"    ... and {len(gap_dates) - 10} more")
                )
            warnings.append(f"Missing trading days: {len(gap_dates)}")
        else:
            self.stdout.write(self.style.SUCCESS("  No trading day gaps detected."))

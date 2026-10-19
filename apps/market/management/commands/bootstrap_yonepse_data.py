"""Management command to bootstrap historical data from YONEPSE.

Fetches static JSON datasets from YONEPSE GitHub Pages and populates
the database using existing domain sync services.

Usage:
    python manage.py bootstrap_yonepse_data
    python manage.py bootstrap_yonepse_data --dry-run
    python manage.py bootstrap_yonepse_data --start 2012-01-01 --end 2026-08-30
    python manage.py bootstrap_yonepse_data --prices
    python manage.py bootstrap_yonepse_data --indices
    python manage.py bootstrap_yonepse_data --market
    python manage.py bootstrap_yonepse_data --securities
"""

import logging
from datetime import date
from typing import Any

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Bootstrap historical market data from YONEPSE static datasets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report without persisting data.",
        )
        parser.add_argument(
            "--start",
            type=str,
            default=None,
            help="Start date for LTP price import (YYYY-MM-DD). Defaults to earliest available.",
        )
        parser.add_argument(
            "--end",
            type=str,
            default=None,
            help="End date for LTP price import (YYYY-MM-DD). Defaults to latest available.",
        )
        parser.add_argument(
            "--securities",
            action="store_true",
            help="Bootstrap sectors and securities from YONEPSE.",
        )
        parser.add_argument(
            "--indices",
            action="store_true",
            help="Bootstrap market index definitions from YONEPSE.",
        )
        parser.add_argument(
            "--index-history",
            action="store_true",
            help="Bootstrap historical index snapshots from YONEPSE.",
        )
        parser.add_argument(
            "--market",
            action="store_true",
            help="Bootstrap market history from YONEPSE.",
        )
        parser.add_argument(
            "--prices",
            action="store_true",
            help="Bootstrap historical LTP/daily prices from YONEPSE.",
        )
        parser.add_argument(
            "--dividends",
            action="store_true",
            help="Bootstrap dividend and bonus-share history from YONEPSE.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Bootstrap all available datasets.",
        )

    def handle(self, *args, **options):
        from integrations.yonepse import YonepseClient

        dry_run = options["dry_run"]
        start_str = options.get("start")
        end_str = options.get("end")
        do_securities = options["securities"]
        do_indices = options["indices"]
        do_index_history = options["index_history"]
        do_market = options["market"]
        do_prices = options["prices"]
        do_dividends = options["dividends"]
        do_all = options["all"]

        # Default to all if nothing specified
        if not (
            do_securities
            or do_indices
            or do_index_history
            or do_market
            or do_prices
            or do_dividends
            or do_all
        ):
            do_all = True

        if do_all:
            do_securities = True
            do_indices = True
            do_index_history = True
            do_market = True
            do_prices = True
            do_dividends = True

        # Parse date range
        start_date = date.fromisoformat(start_str) if start_str else None
        end_date = date.fromisoformat(end_str) if end_str else None

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be committed."))

        report: dict[str, Any] = {
            "sectors": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
            "securities": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
            "indices": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
            "index_snapshots": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
            "market_history": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
            "daily_prices": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
            "dividends": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
            "bonus_shares": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
            "errors": [],
            "earliest_date": None,
            "latest_date": None,
        }

        client = YonepseClient()

        try:
            if do_securities:
                self._bootstrap_securities(client, report, dry_run)

            if do_indices:
                self._bootstrap_indices(client, report, dry_run)

            if do_index_history:
                self._bootstrap_index_history(
                    client, report, dry_run, start_date, end_date
                )

            if do_market:
                self._bootstrap_market_history(client, report, dry_run)

            if do_prices:
                self._bootstrap_ltp_prices(
                    client, report, dry_run, start_date, end_date
                )

            if do_dividends:
                self._bootstrap_dividends(client, report, dry_run)
        finally:
            client.close()

        self._print_report(report)

    def _bootstrap_securities(
        self,
        client: Any,
        report: dict,
        dry_run: bool,
    ) -> None:
        """Bootstrap sectors and securities."""
        from apps.sectors.services import sync_sectors
        from apps.securities.services import sync_securities
        from integrations.yonepse.parsers import (
            parse_sectors_from_securities,
            parse_securities_list,
        )

        self.stdout.write("Bootstrapping sectors and securities...")

        raw_securities = client.get_all_securities()
        sector_data = parse_sectors_from_securities(raw_securities)
        security_data = parse_securities_list(raw_securities)

        if dry_run:
            report["sectors"]["created"] = len(sector_data)
            report["securities"]["created"] = len(security_data)
            self.stdout.write(
                f"  Would create {len(sector_data)} sectors, "
                f"{len(security_data)} securities"
            )
            return

        # Sync sectors first
        sector_result = sync_sectors(sector_data)
        report["sectors"]["created"] = sector_result.created
        report["sectors"]["updated"] = sector_result.updated
        report["sectors"]["skipped"] = sector_result.skipped
        report["sectors"]["failed"] = sector_result.failed
        report["errors"].extend(sector_result.errors)

        # Sync securities
        sec_result = sync_securities(security_data)
        report["securities"]["created"] = sec_result.created
        report["securities"]["updated"] = sec_result.updated
        report["securities"]["skipped"] = sec_result.skipped
        report["securities"]["failed"] = sec_result.failed
        report["errors"].extend(sec_result.errors)

        self.stdout.write(
            f"  Sectors: created={sector_result.created}, updated={sector_result.updated}"
        )
        self.stdout.write(
            f"  Securities: created={sec_result.created}, updated={sec_result.updated}"
        )

    def _bootstrap_indices(
        self,
        client: Any,
        report: dict,
        dry_run: bool,
    ) -> None:
        """Bootstrap market indices."""
        from apps.indices.services import sync_indices
        from integrations.yonepse.parsers import parse_indices, parse_sector_indices

        self.stdout.write("Bootstrapping indices...")

        raw_indices = client.get_indices()
        raw_sector_indices = client.get_sector_indices()

        index_data = parse_indices(raw_indices) + parse_sector_indices(raw_sector_indices)

        if dry_run:
            report["indices"]["created"] = len(index_data)
            self.stdout.write(f"  Would create {len(index_data)} indices")
            return

        result = sync_indices(index_data)
        report["indices"]["created"] = result.created
        report["indices"]["updated"] = result.updated
        report["indices"]["skipped"] = result.skipped
        report["indices"]["failed"] = result.failed
        report["errors"].extend(result.errors)

        self.stdout.write(
            f"  Indices: created={result.created}, updated={result.updated}"
        )

    def _bootstrap_market_history(
        self,
        client: Any,
        report: dict,
        dry_run: bool,
    ) -> None:
        """Bootstrap market history snapshots."""
        from datetime import date as date_cls

        from apps.market.services import sync_market_snapshot
        from integrations.yonepse.parsers import parse_market_history

        self.stdout.write("Bootstrapping market history...")

        raw_history = client.get_market_history()
        history_data = parse_market_history(raw_history)

        if dry_run:
            report["market_history"]["created"] = len(history_data)
            self.stdout.write(f"  Would create {len(history_data)} market snapshots")
            return

        created = 0
        updated = 0
        skipped = 0
        for item in history_data:
            business_date_str = item.get("business_date")
            if not business_date_str:
                skipped += 1
                continue
            try:
                trading_date = date_cls.fromisoformat(business_date_str)
            except (ValueError, TypeError):
                skipped += 1
                continue

            result = sync_market_snapshot(item, trading_date=trading_date)
            created += result.created
            updated += result.updated
            skipped += result.skipped

            # Track date range
            if report["earliest_date"] is None or trading_date < report["earliest_date"]:
                report["earliest_date"] = trading_date
            if report["latest_date"] is None or trading_date > report["latest_date"]:
                report["latest_date"] = trading_date

        report["market_history"]["created"] = created
        report["market_history"]["updated"] = updated
        report["market_history"]["skipped"] = skipped

        self.stdout.write(
            f"  Market history: created={created}, updated={updated}, skipped={skipped}"
        )

    def _bootstrap_index_history(
        self,
        client: Any,
        report: dict,
        dry_run: bool,
        start_date: date | None,
        end_date: date | None,
    ) -> None:
        """Bootstrap historical index snapshots from YONEPSE monthly shards."""
        from apps.indices.services import sync_index_snapshots
        from integrations.yonepse.parsers import (
            parse_index_monthly,
            parse_sector_indices,
        )

        self.stdout.write("Bootstrapping index history...")

        # Build index code -> nepse_id map (index shards are keyed by index code).
        try:
            raw_sector_indices = client.get_sector_indices()
        except Exception as exc:
            report["errors"].append(f"Failed to fetch sector indices: {exc}")
            self.stdout.write(self.style.WARNING(f"  Failed to fetch indices: {exc}"))
            return

        code_to_nepse_id: dict[str, int] = {}
        for item in parse_sector_indices(raw_sector_indices):
            code = item.get("code")
            if code and item.get("id") is not None:
                code_to_nepse_id[str(code)] = int(item["id"])

        if not code_to_nepse_id:
            self.stdout.write(self.style.WARNING("  No index code mapping available"))
            return

        manifest = client.get_index_manifest()
        available_months = manifest.get("availableMonths", [])
        if not available_months:
            self.stdout.write(self.style.WARNING("  No index months available in manifest"))
            return

        filtered_months: list[str] = []
        for month_str in available_months:
            try:
                month_date = date.fromisoformat(f"{month_str}-01")
            except (ValueError, TypeError):
                continue
            if start_date and month_date < start_date.replace(day=1):
                continue
            if end_date and month_date > end_date.replace(day=1):
                continue
            filtered_months.append(month_str)

        if not filtered_months:
            self.stdout.write(self.style.WARNING("  No index months in specified date range"))
            return

        self.stdout.write(
            f"  Processing {len(filtered_months)} months of index history..."
        )

        # Accumulate per-index records so we make one sync call per index.
        # Keyed by (index_code, business_date) to deduplicate overlapping shards.
        grouped: dict[str, dict[str, dict]] = {code: {} for code in code_to_nepse_id}
        unmapped_codes: set[str] = set()
        failed_total = 0

        for i, month_str in enumerate(filtered_months):
            try:
                monthly_data = client.get_index_monthly(month_str)
            except Exception as exc:
                failed_total += 1
                report["errors"].append(f"Failed to fetch index history {month_str}: {exc}")
                continue

            for record in parse_index_monthly(monthly_data):
                code = record.get("index_code")
                business_date = record.get("business_date")
                if code in grouped and business_date:
                    grouped[code][business_date] = record
                elif code is not None:
                    unmapped_codes.add(str(code))

            if (i + 1) % 24 == 0:
                self.stdout.write(
                    f"  Fetched {i + 1}/{len(filtered_months)} months"
                )

        if dry_run:
            total_records = sum(len(recs) for recs in grouped.values())
            report["index_snapshots"]["created"] = total_records
            self.stdout.write(f"  Would create/update {total_records} index snapshots")
            return

        created_total = 0
        updated_total = 0
        skipped_total = 0
        for code, by_date in grouped.items():
            records = list(by_date.values())
            if not records:
                continue
            result = sync_index_snapshots(code_to_nepse_id[code], records)
            created_total += result.created
            updated_total += result.updated
            skipped_total += result.skipped
            failed_total += result.failed
            report["errors"].extend(result.errors)

        report["index_snapshots"]["created"] = created_total
        report["index_snapshots"]["updated"] = updated_total
        report["index_snapshots"]["skipped"] = skipped_total
        report["index_snapshots"]["failed"] = failed_total

        if unmapped_codes:
            report["errors"].append(
                f"Unmapped index codes: {', '.join(sorted(unmapped_codes))}"
            )

        self.stdout.write(
            f"  Index snapshots: created={created_total}, updated={updated_total}, "
            f"skipped={skipped_total}, failed={failed_total}"
        )

    def _bootstrap_dividends(
        self,
        client: Any,
        report: dict,
        dry_run: bool,
    ) -> None:
        """Bootstrap dividend and bonus-share history from YONEPSE."""
        from apps.corporate_actions.services import sync_bonus_shares, sync_dividends
        from apps.securities.models import Security
        from integrations.yonepse.parsers import parse_dividends_history

        self.stdout.write("Bootstrapping dividends and bonus shares...")

        raw = client.get_dividend_history()
        records = parse_dividends_history(raw)

        if not records:
            self.stdout.write(self.style.WARNING("  No dividend records available"))
            return

        # Deduplicate by (symbol, fiscal_year); upstream may list multiple
        # announcements for the same fiscal year. Keep the last occurrence.
        deduped: dict[tuple[str, str], dict] = {}
        for rec in records:
            fiscal_year = rec.get("fiscal_year")
            symbol = rec.get("symbol")
            if not symbol or not fiscal_year:
                continue
            deduped[(symbol, fiscal_year)] = rec

        symbols = {sym for sym, _ in deduped}
        symbol_to_security = {
            s.symbol: s
            for s in Security.objects.filter(symbol__in=symbols)
        }

        dividend_payload: list[dict[str, Any]] = []
        bonus_payload: list[dict[str, Any]] = []
        skipped = 0
        for (symbol, fiscal_year), rec in deduped.items():
            security = symbol_to_security.get(symbol)
            if security is None:
                skipped += 1
                report["errors"].append(f"No security for dividend symbol {symbol}")
                continue
            announce = rec.get("announcement_date")
            cash = rec.get("cash")
            bonus = rec.get("bonus")

            if cash is not None or bonus is not None:
                dividend_payload.append({
                    "nepse_id": security.nepse_id,
                    "fiscal_year": fiscal_year,
                    "dividend_per_share": cash,
                    "bonus_shares": bonus,
                    "announcement_date": announce,
                })

            if bonus is not None:
                bonus_payload.append({
                    "nepse_id": security.nepse_id,
                    "fiscal_year": fiscal_year,
                    "bonus_ratio": str(bonus),
                    "announcement_date": announce,
                })

        if dry_run:
            report["dividends"]["created"] = len(dividend_payload)
            report["bonus_shares"]["created"] = len(bonus_payload)
            self.stdout.write(
                f"  Would create/update {len(dividend_payload)} dividends, "
                f"{len(bonus_payload)} bonus shares"
            )
            return

        div_result = sync_dividends(dividend_payload)
        report["dividends"]["created"] = div_result.created
        report["dividends"]["updated"] = div_result.updated
        report["dividends"]["skipped"] = div_result.skipped
        report["dividends"]["failed"] = div_result.failed
        report["errors"].extend(div_result.errors)

        bonus_result = sync_bonus_shares(bonus_payload)
        report["bonus_shares"]["created"] = bonus_result.created
        report["bonus_shares"]["updated"] = bonus_result.updated
        report["bonus_shares"]["skipped"] = bonus_result.skipped
        report["bonus_shares"]["failed"] = bonus_result.failed
        report["errors"].extend(bonus_result.errors)

        self.stdout.write(
            f"  Dividends: created={div_result.created}, updated={div_result.updated}, "
            f"skipped={div_result.skipped}, failed={div_result.failed}"
        )
        self.stdout.write(
            f"  Bonus shares: created={bonus_result.created}, "
            f"updated={bonus_result.updated}, skipped={bonus_result.skipped}, "
            f"failed={bonus_result.failed}"
        )

    def _bootstrap_ltp_prices(
        self,
        client: Any,
        report: dict,
        dry_run: bool,
        start_date: date | None,
        end_date: date | None,
    ) -> None:
        """Bootstrap historical LTP/daily prices from YONEPSE monthly shards."""
        from apps.prices.services import sync_daily_prices
        from integrations.yonepse.parsers import parse_ltp_monthly

        self.stdout.write("Bootstrapping LTP prices...")

        manifest = client.get_ltp_manifest()
        available_months = manifest.get("availableMonths", [])

        if not available_months:
            self.stdout.write(self.style.WARNING("  No LTP months available in manifest"))
            return

        # Filter by date range if specified
        filtered_months = []
        for month_str in available_months:
            # month_str is "YYYY-MM"
            try:
                month_date = date.fromisoformat(f"{month_str}-01")
            except (ValueError, TypeError):
                continue
            if start_date and month_date < start_date.replace(day=1):
                continue
            if end_date and month_date > end_date.replace(day=1):
                continue
            filtered_months.append(month_str)

        if not filtered_months:
            self.stdout.write(self.style.WARNING("  No months in specified date range"))
            return

        self.stdout.write(f"  Processing {len(filtered_months)} months of LTP data...")

        created_total = 0
        updated_total = 0
        skipped_total = 0
        failed_total = 0

        for i, month_str in enumerate(filtered_months):
            try:
                monthly_data = client.get_ltp_monthly(month_str)
            except Exception as exc:
                failed_total += 1
                report["errors"].append(f"Failed to fetch LTP {month_str}: {exc}")
                self.stdout.write(self.style.WARNING(f"  Failed: {month_str}: {exc}"))
                continue

            price_records = parse_ltp_monthly(monthly_data)

            if dry_run:
                created_total += len(price_records)
                if (i + 1) % 12 == 0:
                    self.stdout.write(f"  [DRY RUN] Processed {i + 1}/{len(filtered_months)} months")
                continue

            result = sync_daily_prices(price_records)
            created_total += result.created
            updated_total += result.updated
            skipped_total += result.skipped
            failed_total += result.failed
            report["errors"].extend(result.errors)

            # Track date range from the series dates
            dates = monthly_data.get("dates", [])
            if dates:
                try:
                    earliest = date.fromisoformat(dates[0])
                    if (
                        report["earliest_date"] is None
                        or earliest < report["earliest_date"]
                    ):
                        report["earliest_date"] = earliest
                except (ValueError, TypeError):
                    pass
                try:
                    latest = date.fromisoformat(dates[-1])
                    if report["latest_date"] is None or latest > report["latest_date"]:
                        report["latest_date"] = latest
                except (ValueError, TypeError):
                    pass

            if (i + 1) % 12 == 0:
                self.stdout.write(
                    f"  Processed {i + 1}/{len(filtered_months)} months "
                    f"(created={created_total}, skipped={skipped_total})"
                )

        report["daily_prices"]["created"] = created_total
        report["daily_prices"]["updated"] = updated_total
        report["daily_prices"]["skipped"] = skipped_total
        report["daily_prices"]["failed"] = failed_total

        self.stdout.write(
            f"  LTP prices: created={created_total}, updated={updated_total}, "
            f"skipped={skipped_total}, failed={failed_total}"
        )

    def _print_report(self, report: dict) -> None:
        """Print the bootstrap summary report."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("YONEPSE Bootstrap Report")
        self.stdout.write("=" * 60)

        for section in [
            "sectors",
            "securities",
            "indices",
            "index_snapshots",
            "market_history",
            "daily_prices",
            "dividends",
            "bonus_shares",
        ]:
            stats = report[section]
            self.stdout.write(f"\n{section.replace('_', ' ').title()}:")
            for key, val in stats.items():
                self.stdout.write(f"  {key}: {val}")

        if report["earliest_date"]:
            self.stdout.write("\nHistorical Range:")
            self.stdout.write(f"  Earliest: {report['earliest_date']}")
            self.stdout.write(f"  Latest:   {report['latest_date']}")

        if report["errors"]:
            self.stdout.write(f"\nErrors ({len(report['errors'])}):")
            for error in report["errors"][:20]:
                self.stdout.write(f"  - {error}")
            if len(report["errors"]) > 20:
                self.stdout.write(f"  ... and {len(report['errors']) - 20} more")

        self.stdout.write("")

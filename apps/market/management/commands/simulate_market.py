"""Market Simulation Command for Live Testing.

Simulates live NEPSE trading sessions, price ticks, intraday records,
indices movements, and alert evaluation triggers for testing the platform
without requiring external NEPSE API access.
"""

import math
import random
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.alerts.engine import AlertEngine
from apps.alerts.models import Alert
from apps.indices.models import IndexSnapshot, MarketIndex
from apps.market.models import MarketSnapshot
from apps.market.services import get_current_market_status
from apps.prices.models import DailyPrice, IntradayPrice
from apps.securities.models import Security
from apps.users.models import User
from apps.watchlist.models import Watchlist, WatchlistItem


DEFAULT_SIMULATED_SYMBOLS = [
    "NABIL",
    "CHCL",
    "SHIVM",
    "NICA",
    "HDL",
    "GBIME",
    "CIT",
    "UPPER",
    "SCB",
    "NMB",
]


class Command(BaseCommand):
    help = "Simulate live NEPSE trading ticks, market status, intraday prices, and alert triggers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--open-market",
            action="store_true",
            help="Set simulated market status to LIVE (continuous trading session).",
        )
        parser.add_argument(
            "--close-market",
            action="store_true",
            help="Set simulated market status to CLOSED / clear simulation status.",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="Print current market status and simulation state.",
        )
        parser.add_argument(
            "--seed-intraday",
            action="store_true",
            help="Generate 1-minute intraday tick series for today for simulated stocks.",
        )
        parser.add_argument(
            "--demo-alerts",
            action="store_true",
            help="Create demo alerts for the 'demo' user near current market prices.",
        )
        parser.add_argument(
            "--trigger-alert",
            action="store_true",
            help="Force-trigger a demo alert immediately for live notification and Web Push testing.",
        )
        parser.add_argument(
            "--ticks",
            type=int,
            default=5,
            help="Number of simulated ticks to execute (default: 5). Ignored if --loop is set.",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=2.0,
            help="Interval in seconds between ticks (default: 2.0).",
        )
        parser.add_argument(
            "--loop",
            action="store_true",
            help="Run simulation continuously until stopped with Ctrl+C.",
        )
        parser.add_argument(
            "--volatility",
            type=float,
            default=0.006,
            help="Maximum relative price change per tick (default: 0.006, i.e. ~0.6%%).",
        )
        parser.add_argument(
            "--symbols",
            type=str,
            default="",
            help="Comma-separated symbols to simulate (defaults to top stocks + user watchlists).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        # 1. Market Status commands
        if options["open_market"]:
            cache.set("nepse_simulation_market_open", True, timeout=None)
            self.stdout.write(self.style.SUCCESS("🟢 Simulated market status set to LIVE (Continuous Trading)."))
            if not any([options["seed_intraday"], options["demo_alerts"], options["trigger_alert"], options["loop"]]):
                self._print_status()
                return

        if options["close_market"]:
            cache.delete("nepse_simulation_market_open")
            self.stdout.write(self.style.WARNING("🔴 Simulated market status reset / CLOSED."))
            if not any([options["seed_intraday"], options["demo_alerts"], options["trigger_alert"]]):
                self._print_status()
                return

        if options["status"]:
            self._print_status()
            return

        # 2. Setup Symbols
        symbols = self._get_target_symbols(options.get("symbols", ""))

        # 3. Seed demo alerts if requested
        if options["demo_alerts"]:
            self._seed_demo_alerts(symbols)

        # 4. Trigger alert if requested
        if options["trigger_alert"]:
            self._trigger_demo_alert(symbols)

        # 5. Seed intraday history if requested
        if options["seed_intraday"]:
            self._seed_intraday_history(symbols)

        # 6. Check if we should run ticks
        is_loop = options["loop"]
        ticks = options["ticks"]

        # If user only specified a flag like --demo-alerts or --seed-intraday without loop or explicit tick count override
        if not is_loop and not options["open_market"] and (options["demo_alerts"] or options["trigger_alert"] or options["seed_intraday"]):
            self.stdout.write(self.style.SUCCESS("✓ Setup tasks completed. Run with `--loop` or `--ticks N` to simulate live trading ticks."))
            return

        # Automatically open simulated market during tick run
        cache.set("nepse_simulation_market_open", True, timeout=None)
        self.stdout.write(self.style.SUCCESS("🟢 Market is LIVE for simulation session."))

        interval = options["interval"]
        volatility = options["volatility"]

        self.stdout.write(self.style.NOTICE(f"Starting simulation on {len(symbols)} stocks: {', '.join(symbols)}"))
        self.stdout.write(self.style.NOTICE(f"Interval: {interval}s | Volatility: {volatility * 100:.2f}% | Mode: {'Infinite Loop' if is_loop else f'{ticks} ticks'}"))
        self.stdout.write("-" * 75)

        tick_count = 0
        try:
            while is_loop or tick_count < ticks:
                tick_count += 1
                self._execute_tick(symbols, tick_count, volatility)
                if is_loop or tick_count < ticks:
                    time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n\n⏹ Simulation paused by user."))

        self.stdout.write("-" * 75)
        self.stdout.write(self.style.SUCCESS(f"Completed {tick_count} simulation ticks."))
        self._print_status()

    def _get_target_symbols(self, symbols_arg: str) -> list[str]:
        if symbols_arg:
            syms = [s.strip().upper() for s in symbols_arg.split(",") if s.strip()]
            existing = list(Security.objects.filter(symbol__in=syms).values_list("symbol", flat=True))
            if existing:
                return existing

        # Default to watchlist symbols for demo user + default top stocks
        demo_user = User.objects.filter(username="demo").first()
        watchlist_syms: list[str] = []
        if demo_user:
            watchlist_syms = list(
                WatchlistItem.objects.filter(watchlist__user=demo_user)
                .values_list("security__symbol", flat=True)
            )

        all_syms = list(dict.fromkeys(watchlist_syms + DEFAULT_SIMULATED_SYMBOLS))
        existing = list(Security.objects.filter(symbol__in=all_syms).values_list("symbol", flat=True))
        return existing or ["NABIL", "CHCL", "SHIVM", "NICA", "HDL"]

    def _print_status(self) -> None:
        cache.delete("nepse_market_status")  # Clear API status cache to reflect immediately
        status = get_current_market_status()
        self.stdout.write(self.style.HTTP_INFO("\n--- Current Market Status ---"))
        self.stdout.write(f" Status:       {status['status']} (is_open={status['is_open']})")
        self.stdout.write(f" Message:      {status['message']}")
        self.stdout.write(f" Detail:       {status['detail']}")
        self.stdout.write(f" Source:       {status['source']}")
        self.stdout.write(f" Trading Date: {status['trading_date']}")
        self.stdout.write("-----------------------------\n")

    def _seed_demo_alerts(self, symbols: list[str]) -> None:
        """Create active alerts for the demo user close to current market prices."""
        demo_user = User.objects.filter(username="demo").first()
        if not demo_user:
            self.stdout.write(self.style.WARNING("Demo user not found; skipping demo alerts."))
            return

        today = timezone.localdate()
        created_count = 0

        for sym in symbols[:4]:
            sec = Security.objects.filter(symbol=sym).first()
            if not sec:
                continue

            latest_dp = DailyPrice.objects.filter(security=sec, trading_date=today).first()
            if not latest_dp:
                latest_dp = DailyPrice.objects.filter(security=sec).order_by("-trading_date").first()

            current_ltp = float(latest_dp.ltp) if latest_dp and latest_dp.ltp else 500.0

            # Target slightly above (+0.5%) for price cross above
            target_above = Decimal(str(round(current_ltp * 1.005, 2)))
            # Target slightly below (-0.5%) for price cross below
            target_below = Decimal(str(round(current_ltp * 0.995, 2)))

            # Alert 1: Price Cross Above
            _, created = Alert.objects.get_or_create(
                user=demo_user,
                security=sec,
                condition=Alert.ConditionType.PRICE_CROSS_ABOVE,
                defaults={
                    "threshold": target_above,
                    "frequency": Alert.FrequencyType.RECURRING,
                    "is_active": True,
                    "notify_in_app": True,
                    "notify_browser_push": True,
                },
            )
            if created:
                created_count += 1

            # Alert 2: Gain Percent Above (>= 1.0%)
            _, created2 = Alert.objects.get_or_create(
                user=demo_user,
                security=sec,
                condition=Alert.ConditionType.PERCENT_CHANGE_UP,
                defaults={
                    "threshold": Decimal("1.00"),
                    "frequency": Alert.FrequencyType.RECURRING,
                    "is_active": True,
                    "notify_in_app": True,
                    "notify_browser_push": True,
                },
            )
            if created2:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"✓ Configured {created_count} demo alerts for user '{demo_user.username}'."))

    def _trigger_demo_alert(self, symbols: list[str]) -> None:
        """Force trigger an alert for user demo to test Web Push and real-time popups."""
        demo_user = User.objects.filter(username="demo").first()
        if not demo_user:
            self.stdout.write(self.style.ERROR("Demo user not found."))
            return

        today = timezone.localdate()
        target_sym = symbols[0] if symbols else "NABIL"
        sec = Security.objects.filter(symbol=target_sym).first()
        if not sec:
            self.stdout.write(self.style.ERROR(f"Security {target_sym} not found."))
            return

        dp = DailyPrice.objects.filter(security=sec, trading_date=today).first()
        if not dp:
            dp = DailyPrice.objects.filter(security=sec).order_by("-trading_date").first()

        ltp = dp.ltp if dp and dp.ltp else Decimal("580.00")
        threshold = round(ltp * Decimal("0.98"), 2)

        alert, _ = Alert.objects.get_or_create(
            user=demo_user,
            security=sec,
            condition=Alert.ConditionType.PRICE_ABOVE,
            defaults={
                "threshold": threshold,
                "frequency": Alert.FrequencyType.RECURRING,
                "is_active": True,
                "notify_in_app": True,
                "notify_browser_push": True,
            },
        )
        alert.is_active = True
        alert.threshold = threshold
        alert.save()

        # Trigger alert via AlertEngine
        AlertEngine.trigger_alert(
            alert=alert,
            current_price=dp,
            triggered_val=ltp,
            message=f"{sec.symbol} surged to Rs. {ltp}! (Threshold: Rs. {threshold})",
        )
        self.stdout.write(self.style.SUCCESS(f"🚀 Triggered live test alert for {sec.symbol} -> In-app toast + Web Push dispatched!"))

    def _seed_intraday_history(self, symbols: list[str]) -> None:
        """Seed 1-minute historical intraday ticks for today so charts display rich series."""
        today = timezone.localdate()
        now = timezone.now()
        start_time = now.replace(hour=11, minute=0, second=0, microsecond=0)
        if start_time > now:
            start_time = now - timedelta(hours=3)

        total_minutes = int((now - start_time).total_seconds() // 60)
        total_minutes = max(30, min(total_minutes, 240))  # Between 30 and 240 ticks

        self.stdout.write(f"Generating {total_minutes} intraday minute ticks for {len(symbols)} securities...")

        created_intraday = 0
        for sym in symbols:
            sec = Security.objects.filter(symbol=sym).first()
            if not sec:
                continue

            latest_dp = DailyPrice.objects.filter(security=sec, trading_date=today).first()
            if not latest_dp:
                latest_dp = DailyPrice.objects.filter(security=sec).order_by("-trading_date").first()

            base_price = float(latest_dp.open or latest_dp.ltp or 500.0) if latest_dp else 500.0
            price = base_price
            intraday_records: list[IntradayPrice] = []

            for m in range(total_minutes):
                tick_time = start_time + timedelta(minutes=m)
                # Brownian motion with slight mean reversion
                pct = (random.random() - 0.49) * 0.005
                price = max(1.0, round(price * (1 + pct), 2))
                vol = random.randint(20, 800)
                turnover = Decimal(str(round(price * vol, 2)))

                intraday_records.append(
                    IntradayPrice(
                        security=sec,
                        timestamp=tick_time,
                        ltp=Decimal(str(price)),
                        volume=vol,
                        turnover=turnover,
                    )
                )

            IntradayPrice.objects.bulk_create(intraday_records, ignore_conflicts=True)
            created_intraday += len(intraday_records)

        self.stdout.write(self.style.SUCCESS(f"✓ Created {created_intraday} intraday tick records for charts."))

    def _execute_tick(self, symbols: list[str], tick_number: int, volatility: float) -> None:
        """Simulate one live trading tick across target securities."""
        today = timezone.localdate()
        now = timezone.now()
        tick_summary: list[str] = []
        triggered_alerts_total = 0

        with transaction.atomic():
            for sym in symbols:
                sec = Security.objects.filter(symbol=sym).first()
                if not sec:
                    continue

                dp = DailyPrice.objects.filter(security=sec, trading_date=today).first()
                if not dp:
                    # Create today's baseline from previous close
                    prev = DailyPrice.objects.filter(security=sec).order_by("-trading_date").first()
                    base = prev.ltp if prev and prev.ltp else Decimal("500.00")
                    dp = DailyPrice.objects.create(
                        security=sec,
                        trading_date=today,
                        open=base,
                        high=base,
                        low=base,
                        close=base,
                        ltp=base,
                        previous_close=base,
                        point_change=Decimal("0.00"),
                        percentage_change=Decimal("0.0000"),
                        volume=0,
                    )

                prev_close = float(dp.previous_close or dp.open or dp.ltp or 100.0)
                current_ltp = float(dp.ltp or prev_close)

                # Simulated price delta: random walk with slight upward or downward drift
                delta_pct = (random.random() * 2 - 0.98) * volatility
                new_ltp_float = max(1.0, round(current_ltp * (1 + delta_pct), 2))
                new_ltp = Decimal(str(new_ltp_float))

                tick_vol = random.randint(50, 1200)
                new_vol = (dp.volume or 0) + tick_vol
                new_high = max(dp.high or new_ltp, new_ltp)
                new_low = min(dp.low or new_ltp, new_ltp)
                pt_change = round(new_ltp - Decimal(str(prev_close)), 2)
                pct_change = round((pt_change / Decimal(str(prev_close))) * Decimal("100"), 4)

                dp.ltp = new_ltp
                dp.close = new_ltp
                dp.high = new_high
                dp.low = new_low
                dp.volume = new_vol
                dp.point_change = pt_change
                dp.percentage_change = pct_change
                dp.save()

                # Add Intraday Price record
                IntradayPrice.objects.create(
                    security=sec,
                    timestamp=now,
                    ltp=new_ltp,
                    volume=tick_vol,
                    turnover=Decimal(str(round(new_ltp_float * tick_vol, 2))),
                )

                # Check & trigger user alerts for this security
                active_alerts = Alert.objects.filter(security=sec, is_active=True)
                for alert in active_alerts:
                    if AlertEngine.evaluate_single_alert(alert, dp):
                        triggered_alerts_total += 1

                # Format tick text
                sign = "+" if pt_change >= 0 else ""
                color_func = self.style.SUCCESS if pt_change >= 0 else self.style.ERROR
                change_str = color_func(f"{sign}{pt_change:.2f} ({sign}{pct_change:.2f}%)")
                tick_summary.append(f"{sym}: Rs.{new_ltp} [{change_str}]")

            # Update Market Snapshot total turnover & volume
            snapshot = MarketSnapshot.objects.filter(trading_date=today).first()
            if snapshot:
                snapshot.total_volume = (snapshot.total_volume or 0) + random.randint(500, 3000)
                snapshot.transactions = (snapshot.transactions or 0) + random.randint(5, 25)
                snapshot.save()

        # Print live ticker line
        alerts_info = f" | {self.style.WARNING(f'⚡ Alerts Fired: {triggered_alerts_total}')}" if triggered_alerts_total else ""
        self.stdout.write(f"[{now.strftime('%H:%M:%S')} Tick #{tick_number:02d}] " + " | ".join(tick_summary[:4]) + alerts_info)

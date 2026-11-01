"""Integration tests for Signal Generation, Lifecycle Tracking, and Celery Tasks."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from apps.prices.models import DailyPrice
from apps.securities.models import Security
from apps.technical_analysis.models import (
    TradingSignal,
)
from apps.technical_analysis.signals import (
    generate_daily_trading_signals,
    update_trading_signals_lifecycle,
)
from apps.technical_analysis.tasks import (
    generate_signals_task,
    update_signal_lifecycle_task,
)


@pytest.fixture
def mock_stock_with_prices(db) -> tuple[Security, list[DailyPrice]]:
    sec = Security.objects.create(
        symbol="NABIL",
        company_name="Nabil Bank Limited",
        nepse_id=101,
    )
    start_date = datetime.date(2026, 8, 1)
    prices = []
    curr = 500.0

    for i in range(55):
        d = start_date + datetime.timedelta(days=i)
        drift = 0.5
        osc = 2.0 if i % 2 == 0 else -1.5
        curr = max(100.0, curr + drift + osc)
        o = curr - 1.0
        c = curr
        h = c + 3.0
        low_val = o - 2.0
        v = 15000.0 + (i * 100.0)
        p = DailyPrice.objects.create(
            security=sec,
            trading_date=d,
            open=Decimal(str(round(o, 2))),
            high=Decimal(str(round(h, 2))),
            low=Decimal(str(round(low_val, 2))),
            close=Decimal(str(round(c, 2))),
            volume=Decimal(str(round(v, 2))),
            turnover=Decimal(str(round(v * c, 2))),
        )
        prices.append(p)

    # Add strong breakout bar on last day
    last_d = start_date + datetime.timedelta(days=55)
    last_p = prices[-1]
    breakout_p = DailyPrice.objects.create(
        security=sec,
        trading_date=last_d,
        open=last_p.close,
        high=Decimal(str(round(float(last_p.close) + 15.0, 2))),
        low=Decimal(str(round(float(last_p.close) - 1.0, 2))),
        close=Decimal(str(round(float(last_p.close) + 12.0, 2))),
        volume=Decimal("45000.00"),
        turnover=Decimal("25000000.00"),
    )
    prices.append(breakout_p)

    return sec, prices


@pytest.mark.django_db
class TestSignalGenerationAndLifecycle:
    """Tests for signal generation and progression pipeline."""

    def test_generate_daily_trading_signals(
        self, mock_stock_with_prices: tuple[Security, list[DailyPrice]]
    ) -> None:
        sec, prices = mock_stock_with_prices
        as_of_date = prices[-1].trading_date

        res = generate_daily_trading_signals(
            as_of_date=as_of_date,
            short_term_min_score=50.0,
            swing_min_score=50.0,
        )

        assert res["status"] == "success"
        assert res["total_signals"] >= 1

        signals = TradingSignal.objects.filter(security=sec, signal_date=as_of_date)
        assert signals.exists()
        sig = signals.first()
        assert sig.status == TradingSignal.STATUS_PENDING
        assert sig.suggested_entry > 0
        assert sig.stop_loss < sig.suggested_entry

    def test_update_trading_signals_lifecycle_fills_pending(
        self, mock_stock_with_prices: tuple[Security, list[DailyPrice]]
    ) -> None:
        sec, prices = mock_stock_with_prices
        signal_date = prices[-1].trading_date

        # Emitted signal on signal_date
        signal = TradingSignal.objects.create(
            security=sec,
            strategy_type=TradingSignal.STRATEGY_SHORT_TERM,
            setup_type=TradingSignal.SETUP_BREAKOUT,
            status=TradingSignal.STATUS_PENDING,
            signal_date=signal_date,
            suggested_entry=Decimal("550.00"),
            entry_zone_low=Decimal("545.00"),
            entry_zone_high=Decimal("555.00"),
            stop_loss=Decimal("520.00"),
            target_1=Decimal("595.00"),
            target_2=Decimal("610.00"),
            risk_per_share=Decimal("30.00"),
            risk_reward_ratio=Decimal("1.50"),
            composite_score=Decimal("75.0"),
            max_holding_period=10,
            rationale="Setup A",
        )

        # Day T+1 candle
        next_day = signal_date + datetime.timedelta(days=1)
        DailyPrice.objects.create(
            security=sec,
            trading_date=next_day,
            open=Decimal("548.00"),
            high=Decimal("560.00"),
            low=Decimal("546.00"),
            close=Decimal("558.00"),
            volume=Decimal("20000.00"),
            turnover=Decimal("11000000.00"),
        )

        res = update_trading_signals_lifecycle(current_date=next_day)
        assert res["filled"] == 1

        signal.refresh_from_db()
        assert signal.status == TradingSignal.STATUS_ACTIVE
        assert signal.entry_date == next_day
        assert signal.actual_entry_price == Decimal("548.00")
        assert signal.holding_period_days == 1
        assert signal.tracking_history.count() == 1

    def test_update_trading_signals_lifecycle_triggers_stop_loss(
        self, mock_stock_with_prices: tuple[Security, list[DailyPrice]]
    ) -> None:
        sec, prices = mock_stock_with_prices
        entry_date = prices[-1].trading_date

        signal = TradingSignal.objects.create(
            security=sec,
            strategy_type=TradingSignal.STRATEGY_SHORT_TERM,
            setup_type=TradingSignal.SETUP_BREAKOUT,
            status=TradingSignal.STATUS_ACTIVE,
            signal_date=entry_date - datetime.timedelta(days=1),
            entry_date=entry_date,
            suggested_entry=Decimal("550.00"),
            actual_entry_price=Decimal("550.00"),
            stop_loss=Decimal("530.00"),
            target_1=Decimal("580.00"),
            target_2=Decimal("600.00"),
            risk_per_share=Decimal("20.00"),
            risk_reward_ratio=Decimal("1.50"),
            composite_score=Decimal("75.0"),
            holding_period_days=2,
            max_holding_period=10,
            rationale="Active trade",
        )

        # Day T+2 candle low plunges through stop loss (530.00)
        session_date = entry_date + datetime.timedelta(days=1)
        DailyPrice.objects.create(
            security=sec,
            trading_date=session_date,
            open=Decimal("540.00"),
            high=Decimal("542.00"),
            low=Decimal("525.00"),  # pierced 530
            close=Decimal("528.00"),
            volume=Decimal("15000.00"),
            turnover=Decimal("8000000.00"),
        )

        res = update_trading_signals_lifecycle(current_date=session_date)
        assert res["closed"] == 1

        signal.refresh_from_db()
        assert signal.status == TradingSignal.STATUS_STOPPED_OUT
        assert signal.exit_date == session_date
        assert signal.actual_exit_price == Decimal("530.00")
        assert signal.return_pct is not None and signal.return_pct < Decimal("0.00")

    def test_celery_signal_tasks(
        self, mock_stock_with_prices: tuple[Security, list[DailyPrice]]
    ) -> None:
        sec, prices = mock_stock_with_prices
        latest_date = prices[-1].trading_date.isoformat()

        gen_res = generate_signals_task.apply(kwargs={"as_of_date": latest_date}).get()
        assert gen_res["status"] == "success"

        lc_res = update_signal_lifecycle_task.apply(kwargs={"current_date": latest_date}).get()
        assert lc_res["status"] == "success"

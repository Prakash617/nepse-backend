"""Unit tests for TradingSignal, TradingSignalTracking, and BacktestRunRecord models."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.securities.models import Security
from apps.technical_analysis.models import (
    BacktestRunRecord,
    TradingSignal,
    TradingSignalTracking,
)


@pytest.fixture
def sample_security(db) -> Security:
    """Fixture providing a test Security."""
    return Security.objects.create(
        symbol="NABIL",
        company_name="Nabil Bank Limited",
        nepse_id=101,
    )


@pytest.mark.django_db
class TestTradingSignalModels:
    """Tests for TradingSignal and TradingSignalTracking data models."""

    def test_create_short_term_trading_signal(self, sample_security: Security) -> None:
        signal = TradingSignal.objects.create(
            security=sample_security,
            strategy_type=TradingSignal.STRATEGY_SHORT_TERM,
            setup_type=TradingSignal.SETUP_BREAKOUT,
            status=TradingSignal.STATUS_PENDING,
            signal_date=datetime.date(2026, 10, 1),
            suggested_entry=Decimal("520.00"),
            entry_zone_low=Decimal("515.00"),
            entry_zone_high=Decimal("525.00"),
            stop_loss=Decimal("495.00"),
            target_1=Decimal("557.50"),
            target_2=Decimal("570.00"),
            risk_per_share=Decimal("25.00"),
            risk_reward_ratio=Decimal("1.50"),
            composite_score=Decimal("78.5"),
            max_holding_period=10,
            rationale="Breakout above 20-day high with volume spike and rising EMA 20.",
            metadata={"rsi_14": 62.4, "adx_14": 28.1, "rel_volume": 1.6},
        )

        assert signal.id is not None
        assert signal.strategy_type == "short_term"
        assert signal.status == "pending"
        assert signal.risk_per_share == Decimal("25.00")
        assert "NABIL" in str(signal)
        assert "SHORT_TERM" in str(signal)

    def test_unique_constraint_prevents_duplicate_signal_on_same_date(
        self, sample_security: Security
    ) -> None:
        TradingSignal.objects.create(
            security=sample_security,
            strategy_type=TradingSignal.STRATEGY_SHORT_TERM,
            setup_type=TradingSignal.SETUP_BREAKOUT,
            signal_date=datetime.date(2026, 10, 1),
            suggested_entry=Decimal("500.00"),
            stop_loss=Decimal("480.00"),
            target_1=Decimal("530.00"),
            risk_per_share=Decimal("20.00"),
            risk_reward_ratio=Decimal("1.50"),
            composite_score=Decimal("75.0"),
            rationale="Setup A",
        )

        with pytest.raises(IntegrityError):
            TradingSignal.objects.create(
                security=sample_security,
                strategy_type=TradingSignal.STRATEGY_SHORT_TERM,
                setup_type=TradingSignal.SETUP_PULLBACK,
                signal_date=datetime.date(2026, 10, 1),
                suggested_entry=Decimal("505.00"),
                stop_loss=Decimal("485.00"),
                target_1=Decimal("535.00"),
                risk_per_share=Decimal("20.00"),
                risk_reward_ratio=Decimal("1.50"),
                composite_score=Decimal("80.0"),
                rationale="Duplicate signal",
            )

    def test_create_signal_tracking(self, sample_security: Security) -> None:
        signal = TradingSignal.objects.create(
            security=sample_security,
            strategy_type=TradingSignal.STRATEGY_SWING,
            setup_type=TradingSignal.SETUP_TREND_CONTINUATION,
            status=TradingSignal.STATUS_ACTIVE,
            signal_date=datetime.date(2026, 10, 1),
            suggested_entry=Decimal("500.00"),
            actual_entry_price=Decimal("502.00"),
            stop_loss=Decimal("470.00"),
            target_1=Decimal("566.00"),
            target_2=Decimal("598.00"),
            risk_per_share=Decimal("32.00"),
            risk_reward_ratio=Decimal("2.00"),
            composite_score=Decimal("82.0"),
            max_holding_period=40,
            rationale="Swing trend continuation above EMA 20 and EMA 50.",
        )

        tracking = TradingSignalTracking.objects.create(
            signal=signal,
            trading_date=datetime.date(2026, 10, 2),
            close_price=Decimal("512.00"),
            high_price=Decimal("515.00"),
            low_price=Decimal("501.00"),
            unrealized_return_pct=Decimal("1.99"),
            trailing_stop_level=Decimal("470.00"),
            day_in_trade=1,
            notes="Strong first session close near highs.",
        )

        assert tracking.id is not None
        assert tracking.day_in_trade == 1
        assert "Day 1" in str(tracking)
        assert signal.tracking_history.count() == 1

    def test_create_backtest_run_record(self) -> None:
        record = BacktestRunRecord.objects.create(
            strategy_type="short_term",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 6, 30),
            initial_capital=Decimal("1000000.00"),
            final_equity=Decimal("1185000.00"),
            total_return_pct=Decimal("18.50"),
            benchmark_return_pct=Decimal("6.20"),
            total_trades=42,
            winning_trades=27,
            losing_trades=15,
            win_rate_pct=Decimal("64.29"),
            profit_factor=Decimal("1.85"),
            max_drawdown_pct=Decimal("5.40"),
            sharpe_ratio=Decimal("1.72"),
            parameters={"min_score": 65.0, "atr_multiplier": 1.5},
            summary_metrics={"avg_holding_days": 5.4, "profit_factor": 1.85},
            equity_curve=[{"date": "2026-01-01", "equity": 1000000.0}],
        )

        assert record.id is not None
        assert record.total_trades == 42
        assert record.win_rate_pct == Decimal("64.29")
        assert "18.50%" in str(record)

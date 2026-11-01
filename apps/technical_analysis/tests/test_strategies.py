"""Unit tests for Short-Term and Swing Trading strategies."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from apps.securities.models import Security
from apps.technical_analysis.indicators import calculate_all_indicators
from apps.technical_analysis.indicators.types import Candle
from apps.technical_analysis.strategies.short_term import ShortTermTradingStrategy
from apps.technical_analysis.strategies.swing import SwingTradingStrategy


def generate_synthetic_candles(
    n: int = 60,
    base_price: float = 500.0,
) -> list[Candle]:
    """Generate realistic oscillating price candles for testing."""
    start_date = datetime.date(2026, 1, 1)
    candles = []
    curr = base_price

    for i in range(n):
        c_date = start_date + datetime.timedelta(days=i)
        # Moderate oscillation around an upward trend
        drift = 0.4
        oscillation = 2.0 if i % 2 == 0 else -1.5
        curr = max(100.0, curr + drift + oscillation)
        o = curr - 1.0
        c = curr
        h = c + 2.0
        low = o - 2.0
        v = 10000.0 + (i * 50.0)
        candles.append(
            Candle(
                trading_date=c_date,
                open=round(o, 2),
                high=round(h, 2),
                low=round(low, 2),
                close=round(c, 2),
                volume=round(v, 2),
            )
        )
    return candles


@pytest.fixture
def mock_security(db) -> Security:
    return Security.objects.create(
        symbol="TESTSEC",
        company_name="Test Security Limited",
        nepse_id=999,
    )


@pytest.mark.django_db
class TestShortTermStrategy:
    """Tests for ShortTermTradingStrategy."""

    def test_short_term_generates_candidate_on_strong_trend(
        self, mock_security: Security
    ) -> None:
        candles = generate_synthetic_candles(n=50, base_price=500.0)
        # Add a breakout expansion candle at the end with high volume
        last = candles[-1]
        candles.append(
            Candle(
                trading_date=last.trading_date + datetime.timedelta(days=1),
                open=last.close,
                high=last.close + 12.0,
                low=last.close - 1.0,
                close=last.close + 10.0,
                volume=last.volume * 2.5,
            )
        )

        indicators = calculate_all_indicators(candles)
        strategy = ShortTermTradingStrategy(min_composite_score=50.0)

        candidate = strategy.evaluate_security(
            security=mock_security,
            candles=candles,
            indicators=indicators,
        )

        assert candidate is not None
        assert candidate.strategy_type == "short_term"
        assert candidate.stop_loss < candidate.suggested_entry
        assert candidate.target_1 > candidate.suggested_entry
        assert candidate.risk_reward_ratio >= Decimal("1.50")
        assert candidate.max_holding_period == 10

    def test_short_term_exit_rules(self) -> None:
        strategy = ShortTermTradingStrategy()
        candle = Candle(
            trading_date=datetime.date(2026, 3, 1),
            open=510.0,
            high=535.0,
            low=475.0,
            close=520.0,
            volume=5000.0,
        )

        # 1. Stop loss hit
        exit_res = strategy.check_exit_conditions(
            current_candle=candle,
            entry_price=Decimal("500.00"),
            stop_loss=Decimal("480.00"),  # candle low is 475.0 <= 480.0
            target_1=Decimal("530.00"),
            target_2=Decimal("550.00"),
            trailing_stop=None,
            days_in_trade=2,
        )
        assert exit_res.should_exit is True
        assert exit_res.exit_type == "stopped_out"
        assert exit_res.is_stop_loss is True

        # 2. Target 2 reached
        candle_target = Candle(
            trading_date=datetime.date(2026, 3, 2),
            open=520.0,
            high=555.0,  # exceeds target 2 of 550
            low=515.0,
            close=552.0,
            volume=5000.0,
        )
        exit_target = strategy.check_exit_conditions(
            current_candle=candle_target,
            entry_price=Decimal("500.00"),
            stop_loss=Decimal("480.00"),
            target_1=Decimal("530.00"),
            target_2=Decimal("550.00"),
            trailing_stop=None,
            days_in_trade=4,
        )
        assert exit_target.should_exit is True
        assert exit_target.exit_type == "target_2_hit"

        # 3. Time-based max holding exit
        candle_neutral = Candle(
            trading_date=datetime.date(2026, 3, 15),
            open=505.0,
            high=510.0,
            low=502.0,
            close=508.0,
            volume=5000.0,
        )
        exit_time = strategy.check_exit_conditions(
            current_candle=candle_neutral,
            entry_price=Decimal("500.00"),
            stop_loss=Decimal("480.00"),
            target_1=Decimal("530.00"),
            target_2=Decimal("550.00"),
            trailing_stop=None,
            days_in_trade=10,  # 10th session
        )
        assert exit_time.should_exit is True
        assert exit_time.exit_type == "expired"
        assert exit_time.is_time_exit is True


@pytest.mark.django_db
class TestSwingStrategy:
    """Tests for SwingTradingStrategy."""

    def test_swing_generates_candidate_on_mature_uptrend(
        self, mock_security: Security
    ) -> None:
        candles = generate_synthetic_candles(n=70, base_price=400.0)
        # Add a continuation candle
        last = candles[-1]
        candles.append(
            Candle(
                trading_date=last.trading_date + datetime.timedelta(days=1),
                open=last.close,
                high=last.close + 10.0,
                low=last.close - 1.0,
                close=last.close + 8.0,
                volume=last.volume * 2.0,
            )
        )

        indicators = calculate_all_indicators(candles)
        strategy = SwingTradingStrategy(min_composite_score=50.0)

        candidate = strategy.evaluate_security(
            security=mock_security,
            candles=candles,
            indicators=indicators,
            market_context={"benchmark_change_pct": 1.0},
        )

        assert candidate is not None
        assert candidate.strategy_type == "swing"
        assert candidate.risk_reward_ratio >= Decimal("2.00")
        assert candidate.max_holding_period == 40
        assert candidate.target_2 is not None

    def test_swing_trailing_stop_updates_on_target_1(self) -> None:
        strategy = SwingTradingStrategy()
        candle = Candle(
            trading_date=datetime.date(2026, 3, 5),
            open=520.0,
            high=545.0,  # touched target 1 (540.0)
            low=518.0,
            close=542.0,
            volume=10000.0,
        )

        exit_res = strategy.check_exit_conditions(
            current_candle=candle,
            entry_price=Decimal("500.00"),
            stop_loss=Decimal("460.00"),
            target_1=Decimal("540.00"),
            target_2=Decimal("580.00"),
            trailing_stop=None,
            days_in_trade=6,
        )

        assert exit_res.should_exit is False
        # Trailing stop moved to entry price (breakeven)
        assert exit_res.updated_trailing_stop == Decimal("500.00")


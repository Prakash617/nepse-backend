"""Unit tests for risk reward and position sizing modules."""

from __future__ import annotations

from decimal import Decimal

from apps.technical_analysis.risk.position_sizing import calculate_position_size
from apps.technical_analysis.risk.risk_reward import evaluate_risk_reward


class TestRiskRewardEvaluation:
    """Tests for risk-reward ratio and trade filter logic."""

    def test_valid_short_term_risk_reward(self) -> None:
        result = evaluate_risk_reward(
            entry_price=500.0,
            stop_loss=480.0,  # 20 risk (4%)
            target_1=530.0,  # 30 reward (1.5 R:R)
            target_2=540.0,  # 40 reward (2.0 R:R)
            min_rr_ratio=1.5,
            max_risk_pct=8.0,
        )
        assert result.is_valid is True
        assert result.risk_per_share == Decimal("20.00")
        assert result.risk_pct == Decimal("4.00")
        assert result.risk_reward_ratio == Decimal("1.50")

    def test_invalid_stop_above_entry(self) -> None:
        result = evaluate_risk_reward(
            entry_price=500.0,
            stop_loss=510.0,
            target_1=550.0,
        )
        assert result.is_valid is False
        assert "below entry price" in (result.rejection_reason or "")

    def test_invalid_low_rr_ratio(self) -> None:
        result = evaluate_risk_reward(
            entry_price=500.0,
            stop_loss=480.0,  # 20 risk
            target_1=520.0,  # 20 reward (1.0 R:R)
            min_rr_ratio=1.5,
        )
        assert result.is_valid is False
        assert "below required minimum" in (result.rejection_reason or "")

    def test_stop_loss_too_wide(self) -> None:
        result = evaluate_risk_reward(
            entry_price=500.0,
            stop_loss=450.0,  # 10% risk
            target_1=600.0,
            max_risk_pct=8.0,
        )
        assert result.is_valid is False
        assert "exceeds maximum permitted threshold" in (result.rejection_reason or "")

    def test_overhead_resistance_blocking_target(self) -> None:
        result = evaluate_risk_reward(
            entry_price=500.0,
            stop_loss=480.0,
            target_1=540.0,
            overhead_resistance=520.0,  # Blocks target 1
        )
        assert result.is_valid is False
        assert "Overhead resistance" in (result.rejection_reason or "")


class TestPositionSizing:
    """Tests for NEPSE board lot position sizing calculations."""

    def test_standard_board_lot_sizing(self) -> None:
        # Rs. 1,000,000 capital, 1% risk = Rs. 10,000
        # Entry = 500, Stop = 480 -> Risk = 20
        # Raw shares = 10,000 / 20 = 500 shares (50 board lots)
        # Max allocation 30% allows up to Rs. 300,000 outlay (600 shares)
        result = calculate_position_size(
            portfolio_capital=1000000.0,
            entry_price=500.0,
            stop_loss=480.0,
            risk_percentage=1.0,
            max_portfolio_allocation_pct=30.0,
            board_lot_size=10,
        )
        assert result.is_valid is True
        assert result.suggested_shares == 500
        assert result.total_outlay == Decimal("250000.00")
        assert result.portfolio_allocation_pct == Decimal("25.00")

    def test_allocation_cap_applied(self) -> None:
        # Rs. 1,000,000 capital, max allocation 15% = Rs. 150,000
        # Entry = 500 -> max shares by allocation = 150,000 / 500 = 300 shares
        # Risk = 5 per share (stop 495) -> raw shares by risk = 10,000 / 5 = 2000 shares
        # Expected capped to 300 shares
        result = calculate_position_size(
            portfolio_capital=1000000.0,
            entry_price=500.0,
            stop_loss=495.0,
            risk_percentage=1.0,
            max_portfolio_allocation_pct=15.0,
            board_lot_size=10,
        )
        assert result.is_valid is True
        assert result.suggested_shares == 300
        assert result.total_outlay == Decimal("150000.00")

    def test_insufficient_capital_for_single_board_lot(self) -> None:
        # Rs. 10,000 capital, 1% risk = Rs. 100
        # Entry = 1000, Stop = 900 -> Risk = 100 -> 1 share allowed, but min lot is 10
        result = calculate_position_size(
            portfolio_capital=10000.0,
            entry_price=1000.0,
            stop_loss=900.0,
            risk_percentage=1.0,
            board_lot_size=10,
        )
        assert result.is_valid is False
        assert "less than minimum NEPSE board lot" in (result.rejection_reason or "")

"""API tests for Daily Trading Signal Engine endpoints."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.securities.models import Security
from apps.technical_analysis.models import (
    TradingSignal,
    TradingSignalTracking,
)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def sample_trading_signals(db) -> tuple[Security, TradingSignal, TradingSignal]:
    sec = Security.objects.create(
        symbol="NABIL",
        company_name="Nabil Bank Limited",
        nepse_id=101,
    )
    today = datetime.date(2026, 10, 15)

    sig1 = TradingSignal.objects.create(
        security=sec,
        strategy_type=TradingSignal.STRATEGY_SHORT_TERM,
        setup_type=TradingSignal.SETUP_BREAKOUT,
        status=TradingSignal.STATUS_ACTIVE,
        signal_date=today - datetime.timedelta(days=2),
        entry_date=today - datetime.timedelta(days=1),
        suggested_entry=Decimal("520.00"),
        actual_entry_price=Decimal("520.00"),
        stop_loss=Decimal("495.00"),
        target_1=Decimal("557.50"),
        target_2=Decimal("570.00"),
        risk_per_share=Decimal("25.00"),
        risk_reward_ratio=Decimal("1.50"),
        composite_score=Decimal("82.0"),
        holding_period_days=2,
        max_holding_period=10,
        rationale="Strong breakout setup with rising volume.",
        metadata={"rsi_14": 61.5, "rel_volume": 1.7},
    )

    TradingSignalTracking.objects.create(
        signal=sig1,
        trading_date=today - datetime.timedelta(days=1),
        close_price=Decimal("525.00"),
        high_price=Decimal("528.00"),
        low_price=Decimal("518.00"),
        unrealized_return_pct=Decimal("0.96"),
        trailing_stop_level=Decimal("495.00"),
        day_in_trade=1,
        notes="Day 1 close",
    )

    sig2 = TradingSignal.objects.create(
        security=sec,
        strategy_type=TradingSignal.STRATEGY_SWING,
        setup_type=TradingSignal.SETUP_TREND_CONTINUATION,
        status=TradingSignal.STATUS_TARGET_1_HIT,
        signal_date=today - datetime.timedelta(days=10),
        entry_date=today - datetime.timedelta(days=9),
        exit_date=today - datetime.timedelta(days=2),
        suggested_entry=Decimal("480.00"),
        actual_entry_price=Decimal("480.00"),
        actual_exit_price=Decimal("540.00"),
        stop_loss=Decimal("450.00"),
        target_1=Decimal("540.00"),
        target_2=Decimal("570.00"),
        risk_per_share=Decimal("30.00"),
        risk_reward_ratio=Decimal("2.00"),
        composite_score=Decimal("88.0"),
        return_pct=Decimal("12.50"),
        holding_period_days=7,
        max_holding_period=40,
        rationale="Swing trend continuation.",
        metadata={"rsi_14": 58.0},
    )

    return sec, sig1, sig2


@pytest.mark.django_db
class TestTradingSignalAPI:
    """Test suite for /api/v1/technical/signals/ and /strategies/ endpoints."""

    def test_list_all_signals(
        self, api_client: APIClient, sample_trading_signals: tuple[Security, TradingSignal, TradingSignal]
    ) -> None:
        url = "/api/v1/technical/signals/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # In paginated or list view
        items = data["results"] if "results" in data else data
        assert len(items) == 2

    def test_filter_signals_by_strategy(
        self, api_client: APIClient, sample_trading_signals: tuple[Security, TradingSignal, TradingSignal]
    ) -> None:
        url = "/api/v1/technical/signals/?strategy=short_term"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        items = data["results"] if "results" in data else data
        assert len(items) == 1
        assert items[0]["strategy_type"] == "short_term"
        assert items[0]["symbol"] == "NABIL"

    def test_list_active_signals(
        self, api_client: APIClient, sample_trading_signals: tuple[Security, TradingSignal, TradingSignal]
    ) -> None:
        url = "/api/v1/technical/signals/active/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        items = data["results"] if "results" in data else data
        assert len(items) == 1
        assert items[0]["status"] == "active"

    def test_retrieve_signal_detail_with_tracking(
        self, api_client: APIClient, sample_trading_signals: tuple[Security, TradingSignal, TradingSignal]
    ) -> None:
        _, sig1, _ = sample_trading_signals
        url = f"/api/v1/technical/signals/{sig1.id}/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sig1.id
        assert "tracking_history" in data
        assert len(data["tracking_history"]) == 1
        assert data["tracking_history"][0]["day_in_trade"] == 1

    def test_get_signal_performance_history(
        self, api_client: APIClient, sample_trading_signals: tuple[Security, TradingSignal, TradingSignal]
    ) -> None:
        url = "/api/v1/technical/signals/history/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        swing_stats = next((item for item in data if item["strategy_type"] == "swing"), None)
        assert swing_stats is not None
        assert swing_stats["closed_signals"] == 1
        assert swing_stats["winning_signals"] == 1
        assert swing_stats["win_rate_pct"] == 100.0

    def test_get_trading_strategies_meta(self, api_client: APIClient) -> None:
        url = "/api/v1/technical/strategies/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        strat_types = {item["strategy_type"] for item in data}
        assert "short_term" in strat_types
        assert "swing" in strat_types

"""Integration tests for Technical Analysis REST API endpoints."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.prices.models import DailyPrice
from apps.sectors.models import Sector
from apps.securities.models import Security
from apps.technical_analysis.services.analysis_service import (
    persist_technical_analysis_run,
    run_full_technical_pipeline,
)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def seeded_market_data(db) -> tuple[Security, Sector, datetime.date]:
    """Seed minimal market, sector, and security price records and run pipeline."""
    sec = Sector.objects.create(nepse_id=101, name="Commercial Banks")
    stock = Security.objects.create(
        nepse_id=2001,
        symbol="NABIL",
        company_name="Nabil Bank Limited",
        sector=sec,
    )
    stock2 = Security.objects.create(
        nepse_id=2002,
        symbol="GBIME",
        company_name="Global IME Bank",
        sector=sec,
    )
    nepse = MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")

    start_date = datetime.date(2026, 1, 1)
    target_date = start_date + datetime.timedelta(days=29)

    for i in range(30):
        d = start_date + datetime.timedelta(days=i)
        DailyPrice.objects.create(
            security=stock,
            trading_date=d,
            open=Decimal("400.0"),
            high=Decimal("415.0"),
            low=Decimal("395.0"),
            close=Decimal(str(400 + i * 2)),
            percentage_change=Decimal("0.5"),
            volume=10000 + i * 500,
        )
        DailyPrice.objects.create(
            security=stock2,
            trading_date=d,
            open=Decimal("200.0"),
            high=Decimal("205.0"),
            low=Decimal("195.0"),
            close=Decimal(str(200 + i)),
            percentage_change=Decimal("0.3"),
            volume=5000 + i * 200,
        )
        IndexSnapshot.objects.create(
            index=nepse,
            trading_date=d,
            open=Decimal("2500.0"),
            high=Decimal("2530.0"),
            low=Decimal("2490.0"),
            close=Decimal(str(2500 + i * 3)),
            volume=100000,
        )

    report = run_full_technical_pipeline(target_date)
    persist_technical_analysis_run(report)
    return stock, sec, target_date


@pytest.mark.django_db
class TestTechnicalAnalysisAPI:
    """Test suite covering all /api/v1/technical/ endpoints."""

    def test_market_overview(self, api_client: APIClient, seeded_market_data) -> None:
        _, _, target_date = seeded_market_data
        url = f"/api/v1/technical/market-overview/?date={target_date.isoformat()}"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "condition" in data
        assert "breadth" in data
        assert "daily_return_pct" in data
        assert "as_of_date" in data

    def test_market_overview_invalid_date(self, api_client: APIClient) -> None:
        url = "/api/v1/technical/market-overview/?date=invalid-date"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_sector_list(self, api_client: APIClient, seeded_market_data) -> None:
        _, _, target_date = seeded_market_data
        url = f"/api/v1/technical/sectors/?trading_date={target_date.isoformat()}"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert len(data) >= 1
        sec_snapshot = data[0]
        assert "sector_score" in sec_snapshot
        assert "classification" in sec_snapshot
        assert "sector_name" in sec_snapshot

    def test_trending_sectors(self, api_client: APIClient, seeded_market_data) -> None:
        _, _, target_date = seeded_market_data
        url = f"/api/v1/technical/sectors/trending/?trading_date={target_date.isoformat()}"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert len(data) <= 3
        if data:
            assert "top_candidates" in data[0]

    def test_sector_detail(self, api_client: APIClient, seeded_market_data) -> None:
        _, sector, target_date = seeded_market_data
        url = f"/api/v1/technical/sectors/{sector.id}/?trading_date={target_date.isoformat()}"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["sector"] == sector.id
        assert "sector_score" in data

    def test_sector_detail_not_found(self, api_client: APIClient) -> None:
        url = "/api/v1/technical/sectors/999999/"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_sector_stocks(self, api_client: APIClient, seeded_market_data) -> None:
        _, sector, target_date = seeded_market_data
        url = f"/api/v1/technical/sectors/{sector.id}/stocks/?trading_date={target_date.isoformat()}"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        results = data.get("results", data)
        assert len(results) >= 2
        assert all(s["sector"] == sector.id for s in results)

    def test_sector_top_stocks(self, api_client: APIClient, seeded_market_data) -> None:
        _, sector, target_date = seeded_market_data
        url = f"/api/v1/technical/sectors/{sector.id}/top-stocks/?limit=1&trading_date={target_date.isoformat()}"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert len(data) == 1
        assert data[0]["rank"] == 1

    def test_stock_rankings(self, api_client: APIClient, seeded_market_data) -> None:
        _, _, target_date = seeded_market_data
        url = f"/api/v1/technical/stocks/rankings/?trading_date={target_date.isoformat()}&search=NABIL"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        results = data.get("results", data)
        assert len(results) == 1
        assert results[0]["symbol"] == "NABIL"
        assert "total_score" in results[0]

    def test_stock_rankings_filters(self, api_client: APIClient, seeded_market_data) -> None:
        _, _, target_date = seeded_market_data
        url = f"/api/v1/technical/stocks/rankings/?trading_date={target_date.isoformat()}&min_score=95"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK

    def test_stock_recommendations(self, api_client: APIClient, seeded_market_data) -> None:
        _, _, target_date = seeded_market_data
        url = f"/api/v1/technical/stocks/recommendations/?trading_date={target_date.isoformat()}"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "results" in data or isinstance(data, list)

    def test_stock_detail(self, api_client: APIClient, seeded_market_data) -> None:
        stock, _, target_date = seeded_market_data
        url = f"/api/v1/technical/stocks/{stock.symbol}/?trading_date={target_date.isoformat()}"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["symbol"] == stock.symbol
        assert "trend_score" in data
        assert "momentum_score" in data
        assert "explanation" in data

    def test_stock_detail_not_found(self, api_client: APIClient) -> None:
        url = "/api/v1/technical/stocks/NONEXISTENT/"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_stock_indicators(self, api_client: APIClient, seeded_market_data) -> None:
        stock, _, target_date = seeded_market_data
        url = f"/api/v1/technical/stocks/{stock.symbol}/indicators/?trading_date={target_date.isoformat()}"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["symbol"] == stock.symbol
        assert "rsi_14" in data
        assert "ema_20" in data
        assert "adx_14" in data
        assert "bollinger_upper" in data

    def test_stock_signals(self, api_client: APIClient, seeded_market_data) -> None:
        stock, _, target_date = seeded_market_data
        url = f"/api/v1/technical/stocks/{stock.symbol}/signals/?trading_date={target_date.isoformat()}"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert isinstance(data, list)

    def test_stock_history(self, api_client: APIClient, seeded_market_data) -> None:
        stock, _, _ = seeded_market_data
        url = f"/api/v1/technical/stocks/{stock.symbol}/history/?limit=10"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "total_score" in data[0]

    def test_backtesting_run_post(self, api_client: APIClient, seeded_market_data) -> None:
        _, _, target_date = seeded_market_data
        start_date = target_date - datetime.timedelta(days=25)
        payload = {
            "start_date": start_date.isoformat(),
            "end_date": target_date.isoformat(),
            "min_technical_score": 20.0,
            "horizons": [5, 10],
            "rebalance_frequency_days": 5,
        }
        res = api_client.post("/api/v1/technical/backtesting/run/", data=payload, format="json")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "total_signals" in data
        assert "overall_performance" in data
        assert "portfolio_simulation" in data

    def test_backtesting_get(self, api_client: APIClient, seeded_market_data) -> None:
        _, _, target_date = seeded_market_data
        start_date = target_date - datetime.timedelta(days=25)
        url = f"/api/v1/technical/backtesting/results/?start_date={start_date.isoformat()}&end_date={target_date.isoformat()}&min_technical_score=20.0"
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "overall_performance" in data

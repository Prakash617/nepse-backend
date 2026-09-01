"""Tests for check_market_data management command."""

from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestCheckMarketDataEmpty:
    def test_no_data(self) -> None:
        out = StringIO()
        call_command("check_market_data", stdout=out)
        output = out.getvalue()
        assert "Market Data Integrity Check" in output
        assert "No daily price records found" in output


@pytest.mark.django_db
class TestCheckMarketDataWithData:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        from datetime import date
        from decimal import Decimal

        from apps.market.models import MarketSnapshot
        from apps.prices.models import DailyPrice
        from apps.sectors.models import Sector
        from apps.securities.models import Security

        sector = Sector.objects.create(nepse_id=1, name="Banks")
        sec = Security.objects.create(
            nepse_id=131, symbol="NABIL", company_name="Nabil Bank", sector=sector
        )
        DailyPrice.objects.create(
            security=sec,
            trading_date=date(2026, 8, 27),
            open=Decimal("1000"),
            high=Decimal("1050"),
            low=Decimal("980"),
            close=Decimal("1020"),
            ltp=Decimal("1020"),
            volume=50000,
            turnover=Decimal("51000000"),
        )
        MarketSnapshot.objects.create(
            trading_date=date(2026, 8, 27),
            total_volume=1000000,
            total_turnover=Decimal("5000000000"),
            transactions=50000,
        )

    def test_with_data(self) -> None:
        out = StringIO()
        call_command("check_market_data", stdout=out)
        output = out.getvalue()
        assert "Daily Price Records" in output
        assert "Market Snapshots" in output
        assert "All integrity checks passed" in output

    def test_with_gaps(self) -> None:
        out = StringIO()
        call_command("check_market_data", "--gaps", stdout=out)
        output = out.getvalue()
        assert "Gap Detection" in output

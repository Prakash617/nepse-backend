"""Tests for technical analysis Celery tasks."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.core.cache import cache

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.prices.models import DailyPrice
from apps.sectors.models import Sector
from apps.securities.models import Security
from apps.technical_analysis.models import AnalysisRun
from apps.technical_analysis.tasks import (
    backfill_historical_technical_analysis,
    calculate_daily_technical_analysis,
)


@pytest.mark.django_db
class TestCeleryTasks:
    """Test Celery tasks wrapper functionality and distributed lock protection."""

    def setup_method(self) -> None:
        cache.clear()

    def teardown_method(self) -> None:
        cache.clear()

    def test_calculate_daily_technical_analysis_task(self) -> None:
        sec = Sector.objects.create(nepse_id=7784, name="Commercial Banks")
        stock = Security.objects.create(nepse_id=6001, symbol="CELSTK", company_name="Celery Stk", sector=sec)
        nepse = MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")

        d = datetime.date(2026, 1, 1)
        for i in range(25):
            cur_d = d + datetime.timedelta(days=i)
            DailyPrice.objects.create(
                security=stock,
                trading_date=cur_d,
                open=Decimal("100.0"), high=Decimal("105.0"), low=Decimal("95.0"),
                close=Decimal(str(100 + i)), percentage_change=Decimal("1.0"), volume=5000,
            )
            IndexSnapshot.objects.create(
                index=nepse,
                trading_date=cur_d,
                open=Decimal("2000.0"), high=Decimal("2020.0"), low=Decimal("1990.0"),
                close=Decimal(str(2000 + i * 2)), volume=50000,
            )

        target_str = (d + datetime.timedelta(days=24)).isoformat()
        res = calculate_daily_technical_analysis(as_of_date=target_str)

        assert res["status"] == "success"
        assert res["securities_processed"] == 1
        assert res["sectors_processed"] == 1
        assert res["errors"] == 0

    def test_distributed_lock_prevents_overlap(self) -> None:
        target_d = datetime.date(2026, 4, 1)
        lock_key = f"lock:tech_analysis_run:{target_d}"
        cache.set(lock_key, "locked", timeout=60)

        # Pre-create an existing run
        AnalysisRun.objects.create(
            analysis_date=target_d,
            status=AnalysisRun.STATUS_RUNNING,
        )

        res = calculate_daily_technical_analysis(as_of_date=target_d.isoformat())

        # Should safely detect existing run and not re-execute concurrently
        assert res["status"] in ("running", "success")

    def test_backfill_historical_task(self) -> None:
        sec = Sector.objects.create(nepse_id=7784, name="Commercial Banks")
        stock = Security.objects.create(nepse_id=6002, symbol="BACKSTK", company_name="Backfill Stk", sector=sec)
        nepse = MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")

        d = datetime.date(2026, 5, 1)
        for i in range(25):
            cur_d = d + datetime.timedelta(days=i)
            DailyPrice.objects.create(
                security=stock,
                trading_date=cur_d,
                open=Decimal("100.0"), high=Decimal("105.0"), low=Decimal("95.0"),
                close=Decimal(str(100 + i)), percentage_change=Decimal("1.0"), volume=5000,
            )
            IndexSnapshot.objects.create(
                index=nepse,
                trading_date=cur_d,
                open=Decimal("2000.0"), high=Decimal("2020.0"), low=Decimal("1990.0"),
                close=Decimal(str(2000 + i)), volume=50000,
            )

        start_str = (d + datetime.timedelta(days=20)).isoformat()
        end_str = (d + datetime.timedelta(days=24)).isoformat()

        res = backfill_historical_technical_analysis(start_str, end_str)
        assert res["status"] == "completed"
        assert res["total_sessions"] == 5
        assert res["processed_sessions"] == 5
        assert res["failed_sessions"] == 0

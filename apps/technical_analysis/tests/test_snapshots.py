"""Tests for technical analysis snapshot models and persistence service."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.prices.models import DailyPrice
from apps.sectors.models import Sector
from apps.securities.models import Security
from apps.technical_analysis.models import (
    AnalysisRun,
    SectorAnalysisSnapshot,
    SectorStockRanking,
    TechnicalIndicatorSnapshot,
    TechnicalScoreSnapshot,
)
from apps.technical_analysis.services.analysis_service import (
    persist_technical_analysis_run,
    run_full_technical_pipeline,
)


@pytest.mark.django_db
class TestSnapshotsPersistence:
    """Test database snapshot creation, uniqueness, and idempotency."""

    def test_persist_pipeline_creates_snapshots(self) -> None:
        sec = Sector.objects.create(nepse_id=7784, name="Commercial Banks")
        stock = Security.objects.create(nepse_id=5001, symbol="TESTBANK", company_name="Test Bank", sector=sec)
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

        target = d + datetime.timedelta(days=24)
        report = run_full_technical_pipeline(target)
        run_record = persist_technical_analysis_run(report)

        assert run_record.status == AnalysisRun.STATUS_SUCCESS
        assert run_record.securities_processed == 1
        assert run_record.sectors_processed == 1

        # Verify indicator snapshot exists
        ind_snap = TechnicalIndicatorSnapshot.objects.filter(security=stock, trading_date=target).first()
        assert ind_snap is not None
        assert ind_snap.ema_20 is not None

        # Verify score snapshot exists
        score_snap = TechnicalScoreSnapshot.objects.filter(security=stock, trading_date=target).first()
        assert score_snap is not None
        assert score_snap.total_score > 0

        # Verify sector snapshot exists
        sec_snap = SectorAnalysisSnapshot.objects.filter(sector=sec, trading_date=target).first()
        assert sec_snap is not None
        assert sec_snap.sector_score > 0

        # Verify ranking snapshot exists
        rank_snap = SectorStockRanking.objects.filter(security=stock, trading_date=target).first()
        assert rank_snap is not None
        assert rank_snap.rank == 1

    def test_idempotent_recalculation_does_not_duplicate(self) -> None:
        sec = Sector.objects.create(nepse_id=7784, name="Commercial Banks")
        stock = Security.objects.create(nepse_id=5002, symbol="IDEMP", company_name="Idemp Bank", sector=sec)
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

        target = d + datetime.timedelta(days=24)
        report = run_full_technical_pipeline(target)

        # Run 1
        persist_technical_analysis_run(report)
        count_ind_1 = TechnicalIndicatorSnapshot.objects.filter(trading_date=target).count()
        count_score_1 = TechnicalScoreSnapshot.objects.filter(trading_date=target).count()

        # Run 2 (recalculation for same date)
        persist_technical_analysis_run(report)
        count_ind_2 = TechnicalIndicatorSnapshot.objects.filter(trading_date=target).count()
        count_score_2 = TechnicalScoreSnapshot.objects.filter(trading_date=target).count()

        # Counts must remain identical (updated in-place, not duplicated)
        assert count_ind_1 == count_ind_2 == 1
        assert count_score_1 == count_score_2 == 1

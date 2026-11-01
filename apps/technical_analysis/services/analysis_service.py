"""Technical Analysis Orchestration and Persistence Service.

Coordinates complete end-of-day market, sector, and stock technical analysis runs,
and provides transactional bulk persistence of historical snapshots.
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from decimal import Decimal

from django.core.cache import cache
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.prices.models import DailyPrice
from apps.technical_analysis.engines.market_engine import (
    MarketAnalysisResult,
    run_market_analysis,
)
from apps.technical_analysis.engines.sector_engine import (
    SectorIntelligenceResult,
    run_sector_intelligence,
)
from apps.technical_analysis.engines.stock_engine import (
    run_all_stocks_analysis,
)
from apps.technical_analysis.models import (
    DEFAULT_CALCULATION_VERSION,
    AnalysisRun,
    RecommendationSnapshot,
    SectorAnalysisSnapshot,
    SectorStockRanking,
    TechnicalIndicatorSnapshot,
    TechnicalScoreSnapshot,
    TechnicalSignal,
)
from apps.technical_analysis.scoring.ranking import (
    ConsolidatedStockRankings,
    build_stock_rankings,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FullMarketIntelligenceReport:
    """Master end-of-day report combining market, sector, and stock rankings."""

    as_of_date: datetime.date
    market_overview: MarketAnalysisResult
    sector_intelligence: SectorIntelligenceResult
    stock_rankings: ConsolidatedStockRankings


def run_full_technical_pipeline(
    as_of_date: datetime.date | None = None,
) -> FullMarketIntelligenceReport:
    """Execute complete analysis pipeline across all eligible NEPSE securities."""
    if as_of_date is None:
        latest_d = DailyPrice.objects.aggregate(max_d=Max("trading_date"))["max_d"]
        if not latest_d:
            latest_d = datetime.date.today()
        as_of_date = latest_d

    logger.info("Executing technical analysis pipeline for session: %s", as_of_date)

    # 1. Market Analysis
    market_res = run_market_analysis(as_of_date)

    # 2. Sector Intelligence
    sector_res = run_sector_intelligence(as_of_date)
    sector_strength_map = {
        s.sector_id: s.score.total_score for s in sector_res.all_sector_rankings
    }

    # 3. Stock Technical Analysis
    stocks_analyzed = run_all_stocks_analysis(
        as_of_date,
        sector_strength_map=sector_strength_map,
    )

    # 4. Consolidated Rankings
    stock_rankings = build_stock_rankings(
        stocks_analyzed,
        sector_res.all_sector_rankings,
        as_of_date,
    )

    logger.info(
        "Technical analysis pipeline complete: %d stocks, %d sectors analyzed.",
        len(stocks_analyzed),
        sector_res.total_sectors,
    )

    return FullMarketIntelligenceReport(
        as_of_date=as_of_date,
        market_overview=market_res,
        sector_intelligence=sector_res,
        stock_rankings=stock_rankings,
    )


def _to_dec(val: float | None, places: int = 2) -> Decimal | None:
    if val is None:
        return None
    return Decimal(str(round(val, places)))


def persist_technical_analysis_run(
    report: FullMarketIntelligenceReport,
    run_type: str = AnalysisRun.RUN_TYPE_SCHEDULED,
    calculation_version: str = DEFAULT_CALCULATION_VERSION,
) -> AnalysisRun:
    """Transactionally save full pipeline results to PostgreSQL snapshot tables."""
    as_of_date = report.as_of_date
    run_record = AnalysisRun.objects.create(
        analysis_date=as_of_date,
        run_type=run_type,
        status=AnalysisRun.STATUS_RUNNING,
        calculation_version=calculation_version,
    )

    try:
        with transaction.atomic():
            # 1. Persist Sector Snapshots
            sector_objs: list[SectorAnalysisSnapshot] = []
            for s in report.sector_intelligence.all_sector_rankings:
                sector_objs.append(
                    SectorAnalysisSnapshot(
                        sector_id=s.sector_id,
                        trading_date=as_of_date,
                        sector_score=_to_dec(s.score.total_score, 1) or Decimal("0.0"),
                        classification=s.score.classification,
                        rotation_stage=s.score.rotation_stage,
                        daily_return_pct=_to_dec(s.daily_return_pct, 2),
                        weekly_return_pct=_to_dec(s.weekly_return_pct, 2),
                        monthly_return_pct=_to_dec(s.monthly_return_pct, 2),
                        relative_strength_vs_nepse_20=_to_dec(s.relative_strength.rs_20.excess_return_pct, 2),
                        relative_strength_vs_nepse_60=_to_dec(s.relative_strength.rs_60.excess_return_pct, 2),
                        constituent_count=s.breadth.constituent_count,
                        advancing_count=s.breadth.advancing_count,
                        declining_count=s.breadth.declining_count,
                        unchanged_count=s.breadth.unchanged_count,
                        pct_above_ema_20=_to_dec(s.breadth.pct_above_ema_20, 1),
                        pct_above_ema_50=_to_dec(s.breadth.pct_above_ema_50, 1),
                        data_source=s.data_source,
                        component_scores=s.score.component_details,
                        explanation=s.score.explanation,
                        calculation_version=calculation_version,
                    )
                )

            SectorAnalysisSnapshot.objects.bulk_create(
                sector_objs,
                update_conflicts=True,
                update_fields=[
                    "sector_score", "classification", "rotation_stage",
                    "daily_return_pct", "weekly_return_pct", "monthly_return_pct",
                    "relative_strength_vs_nepse_20", "relative_strength_vs_nepse_60",
                    "constituent_count", "advancing_count", "declining_count",
                    "unchanged_count", "pct_above_ema_20", "pct_above_ema_50",
                    "data_source", "component_scores", "explanation",
                ],
                unique_fields=["sector", "trading_date", "calculation_version"],
            )

            # 2. Persist Stock Indicators & Scores
            indicator_objs: list[TechnicalIndicatorSnapshot] = []
            score_objs: list[TechnicalScoreSnapshot] = []
            signal_objs: list[TechnicalSignal] = []

            for st in report.stock_rankings.overall_rankings:
                inds = st.indicators
                ma = inds.moving_averages
                mom = inds.momentum
                tr = inds.trend
                volat = inds.volatility
                vol = inds.volume
                struct = inds.price_structure

                indicator_objs.append(
                    TechnicalIndicatorSnapshot(
                        security_id=st.security_id,
                        trading_date=as_of_date,
                        sma_20=_to_dec(ma.sma_20),
                        sma_50=_to_dec(ma.sma_50),
                        sma_200=_to_dec(ma.sma_200),
                        ema_20=_to_dec(ma.ema_20),
                        ema_50=_to_dec(ma.ema_50),
                        ema_200=_to_dec(ma.ema_200),
                        rsi_14=_to_dec(mom.rsi.value),
                        macd_line=_to_dec(mom.macd.macd_line, 4),
                        macd_signal=_to_dec(mom.macd.signal_line, 4),
                        macd_histogram=_to_dec(mom.macd.histogram, 4),
                        adx_14=_to_dec(tr.adx),
                        plus_di_14=_to_dec(tr.plus_di),
                        minus_di_14=_to_dec(tr.minus_di),
                        bollinger_upper=_to_dec(volat.bollinger.upper_band),
                        bollinger_middle=_to_dec(volat.bollinger.middle_band),
                        bollinger_lower=_to_dec(volat.bollinger.lower_band),
                        bandwidth=_to_dec(volat.bollinger.bandwidth, 4),
                        percent_b=_to_dec(volat.bollinger.percent_b, 4),
                        atr_14=_to_dec(volat.atr.atr),
                        atr_pct=_to_dec(volat.atr.atr_percentage),
                        volume=_to_dec(st.volume) or Decimal("0.0"),
                        avg_volume_20=_to_dec(vol.avg_volume_20),
                        avg_volume_50=_to_dec(vol.avg_volume_50),
                        relative_volume=_to_dec(vol.relative_volume),
                        high_20=_to_dec(struct.high_20),
                        low_20=_to_dec(struct.low_20),
                        high_52w=_to_dec(struct.high_52w),
                        low_52w=_to_dec(struct.low_52w),
                        calculation_version=calculation_version,
                    )
                )

                score_objs.append(
                    TechnicalScoreSnapshot(
                        security_id=st.security_id,
                        trading_date=as_of_date,
                        total_score=_to_dec(st.score.total_score, 1) or Decimal("0.0"),
                        trend_score=_to_dec(st.score.trend_score, 1) or Decimal("0.0"),
                        momentum_score=_to_dec(st.score.momentum_score, 1) or Decimal("0.0"),
                        volume_score=_to_dec(st.score.volume_score, 1) or Decimal("0.0"),
                        relative_strength_score=_to_dec(st.score.relative_strength_score, 1) or Decimal("0.0"),
                        breakout_score=_to_dec(st.score.breakout_score, 1) or Decimal("0.0"),
                        risk_score=_to_dec(st.score.risk_score, 1) or Decimal("0.0"),
                        classification=st.score.classification,
                        explanation=st.explanation,
                        bullish_signals=st.score.bullish_signals,
                        bearish_signals=st.score.bearish_signals,
                        warnings=st.score.warnings,
                        component_details=st.score.component_details,
                        calculation_version=calculation_version,
                    )
                )

                # Persist significant individual signals
                for b_sig in st.score.bullish_signals[:2]:
                    signal_objs.append(
                        TechnicalSignal(
                            security_id=st.security_id,
                            trading_date=as_of_date,
                            signal_type=b_sig[:80],
                            category=TechnicalSignal.CATEGORY_BULLISH,
                            explanation=b_sig,
                            is_confirmed=True,
                        )
                    )
                for w_sig in st.score.warnings[:2]:
                    signal_objs.append(
                        TechnicalSignal(
                            security_id=st.security_id,
                            trading_date=as_of_date,
                            signal_type=w_sig[:80],
                            category=TechnicalSignal.CATEGORY_WARNING,
                            explanation=w_sig,
                            is_confirmed=True,
                        )
                    )

            TechnicalIndicatorSnapshot.objects.bulk_create(
                indicator_objs,
                update_conflicts=True,
                update_fields=[
                    "sma_20", "sma_50", "sma_200", "ema_20", "ema_50", "ema_200",
                    "rsi_14", "macd_line", "macd_signal", "macd_histogram",
                    "adx_14", "plus_di_14", "minus_di_14", "bollinger_upper",
                    "bollinger_middle", "bollinger_lower", "bandwidth", "percent_b",
                    "atr_14", "atr_pct", "volume", "avg_volume_20", "avg_volume_50",
                    "relative_volume", "high_20", "low_20", "high_52w", "low_52w",
                ],
                unique_fields=["security", "trading_date", "calculation_version"],
            )

            TechnicalScoreSnapshot.objects.bulk_create(
                score_objs,
                update_conflicts=True,
                update_fields=[
                    "total_score", "trend_score", "momentum_score", "volume_score",
                    "relative_strength_score", "breakout_score", "risk_score",
                    "classification", "explanation", "bullish_signals",
                    "bearish_signals", "warnings", "component_details",
                ],
                unique_fields=["security", "trading_date", "calculation_version"],
            )

            if signal_objs:
                TechnicalSignal.objects.bulk_create(signal_objs, ignore_conflicts=True)

            # 3. Persist Sector Stock Rankings
            ranking_objs: list[SectorStockRanking] = []
            for s_id, constituent_list in report.stock_rankings.sector_rankings.items():
                tot = len(constituent_list)
                for rk_idx, stock in enumerate(constituent_list, 1):
                    excess_s = stock.relative_strength_sector.rs_20.excess_return_pct
                    ranking_objs.append(
                        SectorStockRanking(
                            sector_id=s_id,
                            security_id=stock.security_id,
                            trading_date=as_of_date,
                            rank=rk_idx,
                            total_constituents=tot,
                            technical_score=_to_dec(stock.score.total_score, 1) or Decimal("0.0"),
                            relative_strength_vs_sector=_to_dec(excess_s, 2),
                            calculation_version=calculation_version,
                        )
                    )

            SectorStockRanking.objects.bulk_create(
                ranking_objs,
                update_conflicts=True,
                update_fields=["rank", "total_constituents", "technical_score", "relative_strength_vs_sector"],
                unique_fields=["sector", "security", "trading_date", "calculation_version"],
            )

            # 4. Persist Candidate Recommendations
            recom_objs: list[RecommendationSnapshot] = []

            # A. Top picks in trending sectors
            for trec in report.stock_rankings.trending_sector_recommendations:
                for idx, cand in enumerate(trec.top_candidates, 1):
                    recom_objs.append(
                        RecommendationSnapshot(
                            security_id=cand.security_id,
                            sector_id=cand.sector_id,
                            trading_date=as_of_date,
                            category=RecommendationSnapshot.CATEGORY_TRENDING_SECTOR_TOP,
                            technical_score=_to_dec(cand.score.total_score, 1) or Decimal("0.0"),
                            sector_score=_to_dec(trec.sector_strength_score, 1),
                            rank_in_sector=idx,
                            reason=f"Top candidate in leading sector {trec.sector_name}",
                            calculation_version=calculation_version,
                        )
                    )

            # B. Idiosyncratic standouts
            for cand in report.stock_rankings.idiosyncratic_standouts:
                recom_objs.append(
                    RecommendationSnapshot(
                        security_id=cand.security_id,
                        sector_id=cand.sector_id,
                        trading_date=as_of_date,
                        category=RecommendationSnapshot.CATEGORY_IDIOSYNCRATIC,
                        technical_score=_to_dec(cand.score.total_score, 1) or Decimal("0.0"),
                        reason="Demonstrates independent bullish momentum despite weak sector",
                        calculation_version=calculation_version,
                    )
                )

            # C. Strong bullish candidates
            for cand in report.stock_rankings.strong_bullish_candidates:
                recom_objs.append(
                    RecommendationSnapshot(
                        security_id=cand.security_id,
                        sector_id=cand.sector_id,
                        trading_date=as_of_date,
                        category=RecommendationSnapshot.CATEGORY_STRONG_BULLISH,
                        technical_score=_to_dec(cand.score.total_score, 1) or Decimal("0.0"),
                        reason="Exceptional alignment across trend, momentum, volume, and relative strength",
                        calculation_version=calculation_version,
                    )
                )

            if recom_objs:
                RecommendationSnapshot.objects.bulk_create(
                    recom_objs,
                    update_conflicts=True,
                    update_fields=["technical_score", "sector_score", "rank_overall", "rank_in_sector", "reason"],
                    unique_fields=["security", "trading_date", "category", "calculation_version"],
                )

            # Mark run as success
            run_record.status = AnalysisRun.STATUS_SUCCESS
            run_record.finished_at = timezone.now()
            run_record.securities_processed = len(report.stock_rankings.overall_rankings)
            run_record.sectors_processed = report.sector_intelligence.total_sectors
            run_record.save(update_fields=["status", "finished_at", "securities_processed", "sectors_processed"])

            logger.info("Successfully persisted technical analysis run %d for %s", run_record.id, as_of_date)

    except Exception as exc:
        logger.exception("Failed to persist technical analysis run for %s: %s", as_of_date, exc)
        run_record.status = AnalysisRun.STATUS_FAILED
        run_record.finished_at = timezone.now()
        run_record.error_count += 1
        run_record.error_details = [{"error": str(exc), "timestamp": timezone.now().isoformat()}]
        run_record.save(update_fields=["status", "finished_at", "error_count", "error_details"])
        raise

    return run_record


def execute_daily_analysis_pipeline(
    as_of_date: datetime.date | None = None,
    run_type: str = AnalysisRun.RUN_TYPE_SCHEDULED,
) -> AnalysisRun:
    """Entry point for Celery tasks and administrative triggers.

    Uses a Redis distributed lock to avoid concurrent duplicate runs for the same date.
    """
    if as_of_date is None:
        latest_d = DailyPrice.objects.aggregate(max_d=Max("trading_date"))["max_d"]
        if not latest_d:
            latest_d = datetime.date.today()
        as_of_date = latest_d

    lock_key = f"lock:tech_analysis_run:{as_of_date}"
    acquired = cache.add(lock_key, "locked", timeout=900)  # 15 minutes timeout
    if not acquired:
        logger.warning("Another technical analysis run is already in progress for %s. Skipping.", as_of_date)
        existing = AnalysisRun.objects.filter(analysis_date=as_of_date).order_by("-started_at").first()
        if existing:
            return existing
        raise RuntimeError(f"Concurrent technical analysis lock active for {as_of_date}")

    try:
        report = run_full_technical_pipeline(as_of_date)
        run_record = persist_technical_analysis_run(report, run_type=run_type)

        # Update lifecycle of active signals and generate daily trading signals
        try:
            from apps.technical_analysis.signals import (
                generate_daily_trading_signals,
                update_trading_signals_lifecycle,
            )
            update_trading_signals_lifecycle(as_of_date)
            generate_daily_trading_signals(as_of_date)
        except Exception as sig_exc:
            logger.exception("Error executing signal generation/lifecycle on %s: %s", as_of_date, sig_exc)

        return run_record
    finally:
        cache.delete(lock_key)

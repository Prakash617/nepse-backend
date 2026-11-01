"""Signal Generation Engine: Evaluates Short-Term and Swing strategies across active NEPSE stocks."""

from __future__ import annotations

import datetime
import logging
from typing import Any

from django.db.models import Max

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.prices.models import DailyPrice
from apps.securities.models import Security
from apps.technical_analysis.indicators import calculate_all_indicators
from apps.technical_analysis.indicators.types import candles_from_records
from apps.technical_analysis.models import (
    DEFAULT_CALCULATION_VERSION,
    SectorAnalysisSnapshot,
    TradingSignal,
)
from apps.technical_analysis.strategies.short_term import (
    ShortTermTradingStrategy,
)
from apps.technical_analysis.strategies.swing import (
    SwingTradingStrategy,
)

logger = logging.getLogger(__name__)


def generate_daily_trading_signals(
    as_of_date: datetime.date | None = None,
    calculation_version: str = DEFAULT_CALCULATION_VERSION,
    *,
    short_term_min_score: float = 65.0,
    swing_min_score: float = 68.0,
) -> dict[str, Any]:
    """Scan all active NEPSE securities on the completed daily candle and emit trading signals.

    Args:
        as_of_date: Date of completed trading session. Defaults to latest available in DB.
        calculation_version: Version tag for reproducibility.
        short_term_min_score: Minimum quantitative setup score for Short-Term signals.
        swing_min_score: Minimum quantitative setup score for Swing signals.

    Returns:
        Summary dict containing signal counts and metadata.
    """
    if as_of_date is None:
        latest_d = DailyPrice.objects.aggregate(max_d=Max("trading_date"))["max_d"]
        if not latest_d:
            logger.warning("No daily prices found in database. Cannot generate signals.")
            return {"status": "no_data", "signals_count": 0}
        as_of_date = latest_d

    logger.info("Generating daily trading signals for date: %s", as_of_date)

    # 1. Market Context (NEPSE Index nepse_id=58)
    market_context: dict[str, Any] = {}
    nepse_index = MarketIndex.objects.filter(nepse_id=58).first()
    if nepse_index:
        recent_snaps = list(
            IndexSnapshot.objects.filter(
                index=nepse_index,
                trading_date__lte=as_of_date,
            )
            .order_by("-trading_date")[:21]
        )
        if len(recent_snaps) >= 20 and recent_snaps[0].close and recent_snaps[-1].close:
            c0 = float(recent_snaps[0].close)
            cN = float(recent_snaps[-1].close)
            market_context["benchmark_change_pct"] = ((c0 - cN) / cN) * 100.0

    # 2. Sector Context
    sector_map: dict[int, dict[str, Any]] = {}
    sector_snaps = SectorAnalysisSnapshot.objects.filter(
        trading_date=as_of_date,
        calculation_version=calculation_version,
    )
    for s_snap in sector_snaps:
        sector_map[s_snap.sector_id] = {
            "score": float(s_snap.sector_score),
            "rotation_stage": s_snap.rotation_stage,
            "classification": s_snap.classification,
        }

    # 3. Active Securities trading on as_of_date
    active_sec_ids = list(
        DailyPrice.objects.filter(trading_date=as_of_date)
        .values_list("security_id", flat=True)
        .distinct()
    )

    if not active_sec_ids:
        logger.info("No active securities found trading on %s", as_of_date)
        return {"status": "success", "as_of_date": as_of_date.isoformat(), "signals_count": 0}

    securities = list(Security.objects.filter(id__in=active_sec_ids).select_related("sector"))

    short_term_strategy = ShortTermTradingStrategy(min_composite_score=short_term_min_score)
    swing_strategy = SwingTradingStrategy(min_composite_score=swing_min_score)

    signals_to_upsert: list[TradingSignal] = []
    short_term_count = 0
    swing_count = 0

    # Fetch historical daily prices for active securities in bulk
    # Look back 90 calendar days to guarantee 50-60 trading sessions
    lookback_start = as_of_date - datetime.timedelta(days=120)
    all_prices = list(
        DailyPrice.objects.filter(
            security_id__in=active_sec_ids,
            trading_date__gte=lookback_start,
            trading_date__lte=as_of_date,
        )
        .order_by("security_id", "trading_date")
        .values("security_id", "trading_date", "open", "high", "low", "close", "volume", "turnover")
    )

    prices_by_sec: dict[int, list[dict[str, Any]]] = {}
    for p in all_prices:
        sec_id = p["security_id"]
        if sec_id not in prices_by_sec:
            prices_by_sec[sec_id] = []
        prices_by_sec[sec_id].append(p)

    for sec in securities:
        sec_records = prices_by_sec.get(sec.id, [])
        if len(sec_records) < 20:
            continue

        candles = candles_from_records(sec_records)
        if not candles or candles[-1].trading_date != as_of_date:
            continue

        try:
            indicators = calculate_all_indicators(candles)
        except Exception as exc:
            logger.debug("Failed indicator calculation for %s: %s", sec.symbol, exc)
            continue

        s_context = sector_map.get(sec.sector_id) if sec.sector_id else None

        # A. Short-Term Strategy Evaluation
        cand_st = short_term_strategy.evaluate_security(
            security=sec,
            candles=candles,
            indicators=indicators,
            market_context=market_context,
            sector_context=s_context,
        )
        if cand_st is not None:
            signals_to_upsert.append(
                TradingSignal(
                    security=sec,
                    strategy_type=TradingSignal.STRATEGY_SHORT_TERM,
                    setup_type=cand_st.setup_type,
                    status=TradingSignal.STATUS_PENDING,
                    signal_date=as_of_date,
                    suggested_entry=cand_st.suggested_entry,
                    entry_zone_low=cand_st.entry_zone_low,
                    entry_zone_high=cand_st.entry_zone_high,
                    stop_loss=cand_st.stop_loss,
                    target_1=cand_st.target_1,
                    target_2=cand_st.target_2,
                    risk_per_share=cand_st.risk_per_share,
                    risk_reward_ratio=cand_st.risk_reward_ratio,
                    composite_score=cand_st.composite_score,
                    max_holding_period=cand_st.max_holding_period,
                    rationale=cand_st.rationale,
                    metadata=cand_st.metadata,
                    calculation_version=calculation_version,
                )
            )
            short_term_count += 1

        # B. Swing Strategy Evaluation
        cand_sw = swing_strategy.evaluate_security(
            security=sec,
            candles=candles,
            indicators=indicators,
            market_context=market_context,
            sector_context=s_context,
        )
        if cand_sw is not None:
            signals_to_upsert.append(
                TradingSignal(
                    security=sec,
                    strategy_type=TradingSignal.STRATEGY_SWING,
                    setup_type=cand_sw.setup_type,
                    status=TradingSignal.STATUS_PENDING,
                    signal_date=as_of_date,
                    suggested_entry=cand_sw.suggested_entry,
                    entry_zone_low=cand_sw.entry_zone_low,
                    entry_zone_high=cand_sw.entry_zone_high,
                    stop_loss=cand_sw.stop_loss,
                    target_1=cand_sw.target_1,
                    target_2=cand_sw.target_2,
                    risk_per_share=cand_sw.risk_per_share,
                    risk_reward_ratio=cand_sw.risk_reward_ratio,
                    composite_score=cand_sw.composite_score,
                    max_holding_period=cand_sw.max_holding_period,
                    rationale=cand_sw.rationale,
                    metadata=cand_sw.metadata,
                    calculation_version=calculation_version,
                )
            )
            swing_count += 1

    # Bulk create / update idempotent signals
    if signals_to_upsert:
        TradingSignal.objects.bulk_create(
            signals_to_upsert,
            update_conflicts=True,
            update_fields=[
                "suggested_entry",
                "entry_zone_low",
                "entry_zone_high",
                "stop_loss",
                "target_1",
                "target_2",
                "risk_per_share",
                "risk_reward_ratio",
                "composite_score",
                "rationale",
                "metadata",
            ],
            unique_fields=["security", "signal_date", "strategy_type", "calculation_version"],
        )

    logger.info(
        "Emitted %d trading signals (%d Short-Term, %d Swing) for %s",
        len(signals_to_upsert),
        short_term_count,
        swing_count,
        as_of_date,
    )

    return {
        "status": "success",
        "as_of_date": as_of_date.isoformat(),
        "total_signals": len(signals_to_upsert),
        "short_term_signals": short_term_count,
        "swing_signals": swing_count,
    }

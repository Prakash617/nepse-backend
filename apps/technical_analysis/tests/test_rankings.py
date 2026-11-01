"""Unit tests for stock rankings and idiosyncratic standouts."""

from __future__ import annotations

import datetime

from apps.technical_analysis.engines.sector_engine import SectorBreadth, SingleSectorAnalysis
from apps.technical_analysis.engines.stock_engine import SingleStockAnalysis
from apps.technical_analysis.indicators import calculate_all_indicators
from apps.technical_analysis.scoring.ranking import build_stock_rankings
from apps.technical_analysis.scoring.relative_strength import (
    RelativeStrengthAnalysis,
    RelativeStrengthMetric,
)
from apps.technical_analysis.scoring.sector_scoring import SectorStrengthScore
from apps.technical_analysis.scoring.stock_scoring import StockTechnicalScore


def _make_dummy_stock(
    sec_id: int,
    symbol: str,
    sector_id: int,
    total_score: float,
    classification: str = "Bullish Candidate",
) -> SingleStockAnalysis:
    score = StockTechnicalScore(
        total_score=total_score,
        classification=classification,
        trend_score=20.0,
        momentum_score=15.0,
        volume_score=10.0,
        relative_strength_score=10.0,
        breakout_score=5.0,
        risk_score=5.0,
        bullish_signals=["Uptrend confirmed"],
        bearish_signals=[],
        warnings=[],
        component_details={},
    )
    empty_m = RelativeStrengthMetric(0, None, None, 0.0, False)
    rs = RelativeStrengthAnalysis(empty_m, empty_m, empty_m, "neutral", [])
    inds = calculate_all_indicators([])

    return SingleStockAnalysis(
        security_id=sec_id,
        nepse_id=sec_id,
        symbol=symbol,
        company_name=f"Company {symbol}",
        sector_id=sector_id,
        sector_name=f"Sector {sector_id}",
        as_of_date=datetime.date(2026, 1, 1),
        latest_close=100.0,
        point_change=1.0,
        daily_return_pct=1.0,
        volume=1000,
        indicators=inds,
        relative_strength_market=rs,
        relative_strength_sector=rs,
        score=score,
        explanation="Test explanation",
    )


def _make_dummy_sector(
    sec_id: int,
    name: str,
    total_score: float,
    classification: str = "Neutral",
) -> SingleSectorAnalysis:
    score = SectorStrengthScore(
        total_score=total_score,
        classification=classification,
        rotation_stage="improving",
        price_momentum_score=10.0,
        ema_trend_score=10.0,
        relative_strength_score=10.0,
        volume_score=10.0,
        rsi_score=5.0,
        adx_score=5.0,
        explanation="Test sector",
        component_details={},
    )
    empty_m = RelativeStrengthMetric(0, None, None, 0.0, False)
    rs = RelativeStrengthAnalysis(empty_m, empty_m, empty_m, "neutral", [])
    inds = calculate_all_indicators([])
    breadth = SectorBreadth(10, 8, 5, 2, 1, 5, 62.5, 4, 50.0)

    return SingleSectorAnalysis(
        sector_id=sec_id,
        sector_nepse_id=sec_id,
        sector_name=name,
        display_name=name,
        as_of_date=datetime.date(2026, 1, 1),
        latest_close=1000.0,
        point_change=5.0,
        daily_return_pct=0.5,
        weekly_return_pct=1.5,
        monthly_return_pct=3.0,
        volume=50000,
        data_source="official_index",
        indicators=inds,
        relative_strength=rs,
        breadth=breadth,
        score=score,
    )


class TestStockRankings:
    """Test 3 ranking views and idiosyncratic stock detection."""

    def test_overall_and_sector_rankings_and_idiosyncratic_standout(self) -> None:
        # Sectors: Sector 1 (Strong: 85), Sector 2 (Moderate: 60), Sector 3 (Weak: 25)
        sec1 = _make_dummy_sector(1, "Banking", 85.0, "Strong Trending")
        sec2 = _make_dummy_sector(2, "Hydro", 60.0, "Neutral")
        sec3 = _make_dummy_sector(3, "Finance", 25.0, "Bearish")
        sector_analyses = [sec1, sec2, sec3]

        # Stocks:
        # Stock A in Banking: score 90
        # Stock B in Banking: score 70
        # Stock C in Hydro: score 65
        # Stock D in Finance (Weak Sector): score 82 -> IDIOSYNCRATIC STANDOUT!
        # Stock E in Finance: score 20
        stk_a = _make_dummy_stock(101, "STK_A", 1, 90.0)
        stk_b = _make_dummy_stock(102, "STK_B", 1, 70.0)
        stk_c = _make_dummy_stock(103, "STK_C", 2, 65.0)
        stk_d = _make_dummy_stock(104, "STK_D", 3, 82.0)
        stk_e = _make_dummy_stock(105, "STK_E", 3, 20.0)

        stocks = [stk_e, stk_b, stk_a, stk_c, stk_d]
        d = datetime.date(2026, 1, 1)

        rankings = build_stock_rankings(stocks, sector_analyses, d)

        # 1. Overall ranking: STK_A (90), STK_D (82), STK_B (70), STK_C (65), STK_E (20)
        assert rankings.overall_rankings[0].symbol == "STK_A"
        assert rankings.overall_rankings[1].symbol == "STK_D"
        assert rankings.overall_rankings[-1].symbol == "STK_E"

        # 2. Sector-wise rankings
        assert len(rankings.sector_rankings[1]) == 2
        assert rankings.sector_rankings[1][0].symbol == "STK_A"
        assert len(rankings.sector_rankings[3]) == 2
        assert rankings.sector_rankings[3][0].symbol == "STK_D"

        # 3. Trending sector recommendations has top picks from Banking
        assert len(rankings.trending_sector_recommendations) == 3
        top_sec_rec = rankings.trending_sector_recommendations[0]
        assert top_sec_rec.sector_name == "Banking"
        assert top_sec_rec.top_candidates[0].symbol == "STK_A"

        # 4. Idiosyncratic standouts: STK_D belongs to Finance (score 25) but has score 82!
        assert len(rankings.idiosyncratic_standouts) == 1
        assert rankings.idiosyncratic_standouts[0].symbol == "STK_D"

"""Stock ranking and recommendation generation.

Produces the 3 required ranking views:
1. Overall NEPSE Stock Ranking (across all sectors)
2. Sector-wise Stock Ranking (within each sector)
3. Trending Sector Stock Recommendations (top 3 trending sectors highlights)

Also identifies idiosyncratic standouts (strong stocks in weak sectors)
and enforces neutrality safeguards.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from apps.technical_analysis.engines.sector_engine import SingleSectorAnalysis
from apps.technical_analysis.engines.stock_engine import SingleStockAnalysis


@dataclass(frozen=True)
class TrendingSectorRecommendation:
    """Recommendations and candidate highlights for a top trending sector."""

    sector_id: int
    sector_name: str
    sector_strength_score: float
    sector_classification: str
    rotation_stage: str
    top_candidates: list[SingleStockAnalysis]


@dataclass(frozen=True)
class ConsolidatedStockRankings:
    """Master ranking views covering market-wide, sector-wise, and trending candidates."""

    as_of_date: datetime.date
    total_evaluated: int

    # View 1: Overall NEPSE market ranking
    overall_rankings: list[SingleStockAnalysis]

    # View 2: Sector-wise rankings (sector_id -> constituent stocks ranked by score)
    sector_rankings: dict[int, list[SingleStockAnalysis]]

    # View 3: Top 3 Trending Sectors with top candidate recommendations
    trending_sector_recommendations: list[TrendingSectorRecommendation]

    # Special view: Strong stocks in weak sectors (idiosyncratic standouts)
    idiosyncratic_standouts: list[SingleStockAnalysis]

    # Candidate lists grouped by classification
    strong_bullish_candidates: list[SingleStockAnalysis]
    bullish_candidates: list[SingleStockAnalysis]
    emerging_candidates: list[SingleStockAnalysis]
    breakout_candidates: list[SingleStockAnalysis]


def build_stock_rankings(
    analyzed_stocks: list[SingleStockAnalysis],
    sector_analyses: list[SingleSectorAnalysis],
    as_of_date: datetime.date,
    *,
    trending_sector_limit: int = 5,
) -> ConsolidatedStockRankings:
    """Construct all 3 required ranking perspectives from analyzed securities."""
    # 1. Overall NEPSE Market Ranking (sorted by total_score descending)
    overall_sorted = sorted(analyzed_stocks, key=lambda s: s.score.total_score, reverse=True)

    # 2. Sector-wise Rankings
    sector_grouped: dict[int, list[SingleStockAnalysis]] = {}
    for stock in analyzed_stocks:
        if stock.sector_id is not None:
            if stock.sector_id not in sector_grouped:
                sector_grouped[stock.sector_id] = []
            sector_grouped[stock.sector_id].append(stock)

    # Sort constituents within each sector
    for s_id in sector_grouped:
        sector_grouped[s_id].sort(key=lambda s: s.score.total_score, reverse=True)

    # 3. Trending Sector Recommendations (Top 3 trending sectors)
    top_sectors = sorted(sector_analyses, key=lambda s: s.score.total_score, reverse=True)[:3]
    trending_recs: list[TrendingSectorRecommendation] = []

    for top_sec in top_sectors:
        constituents = sector_grouped.get(top_sec.sector_id, [])
        top_picks = constituents[:trending_sector_limit]

        trending_recs.append(
            TrendingSectorRecommendation(
                sector_id=top_sec.sector_id,
                sector_name=top_sec.sector_name,
                sector_strength_score=top_sec.score.total_score,
                sector_classification=top_sec.score.classification,
                rotation_stage=top_sec.score.rotation_stage,
                top_candidates=top_picks,
            )
        )

    # 4. Idiosyncratic Standouts (Strong stocks score >= 65 in weak sectors score < 45)
    weak_sector_ids = {
        sec.sector_id for sec in sector_analyses if sec.score.total_score < 45.0
    }
    idiosyncratic = [
        s for s in overall_sorted
        if s.sector_id in weak_sector_ids and s.score.total_score >= 65.0
    ]

    # Candidate Groupings
    strong_bullish = [s for s in overall_sorted if s.score.total_score >= 80.0]
    bullish = [s for s in overall_sorted if 65.0 <= s.score.total_score < 80.0]
    emerging = [s for s in overall_sorted if s.score.classification == "Emerging Candidate"]
    breakouts = [
        s for s in overall_sorted
        if s.indicators.price_structure.is_breakout_20 or s.indicators.volume.is_volume_breakout
    ]

    return ConsolidatedStockRankings(
        as_of_date=as_of_date,
        total_evaluated=len(analyzed_stocks),
        overall_rankings=overall_sorted,
        sector_rankings=sector_grouped,
        trending_sector_recommendations=trending_recs,
        idiosyncratic_standouts=idiosyncratic,
        strong_bullish_candidates=strong_bullish,
        bullish_candidates=bullish,
        emerging_candidates=emerging,
        breakout_candidates=breakouts,
    )

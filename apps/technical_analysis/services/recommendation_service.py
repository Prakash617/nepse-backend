"""Recommendation and candidate generation service."""

from __future__ import annotations

from apps.technical_analysis.engines.stock_engine import SingleStockAnalysis
from apps.technical_analysis.scoring.ranking import ConsolidatedStockRankings


def get_candidates_by_category(
    rankings: ConsolidatedStockRankings,
    category: str = "all",
) -> list[SingleStockAnalysis]:
    """Retrieve algorithmic candidates categorized by research label."""
    cat = category.lower().strip()

    if cat in ("strong_bullish", "strong"):
        return rankings.strong_bullish_candidates
    elif cat in ("bullish",):
        return rankings.bullish_candidates
    elif cat in ("emerging",):
        return rankings.emerging_candidates
    elif cat in ("breakout",):
        return rankings.breakout_candidates
    elif cat in ("idiosyncratic", "standouts"):
        return rankings.idiosyncratic_standouts

    # Default: return top candidates from strong + bullish + emerging
    return (
        rankings.strong_bullish_candidates
        + rankings.bullish_candidates
        + rankings.emerging_candidates
    )

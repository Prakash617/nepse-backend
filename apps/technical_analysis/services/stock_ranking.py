"""Stock ranking querying and filtering service."""

from __future__ import annotations

from apps.technical_analysis.engines.stock_engine import SingleStockAnalysis


def filter_stock_rankings(
    rankings: list[SingleStockAnalysis],
    *,
    sector_id: int | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    min_rvol: float | None = None,
    classification: str | None = None,
    search: str | None = None,
) -> list[SingleStockAnalysis]:
    """Apply filters and criteria to a list of analyzed stock objects."""
    filtered = rankings

    if sector_id is not None:
        filtered = [s for s in filtered if s.sector_id == sector_id]

    if min_score is not None:
        filtered = [s for s in filtered if s.score.total_score >= min_score]

    if max_score is not None:
        filtered = [s for s in filtered if s.score.total_score <= max_score]

    if min_rvol is not None:
        filtered = [
            s for s in filtered
            if s.indicators.volume.relative_volume is not None
            and s.indicators.volume.relative_volume >= min_rvol
        ]

    if classification:
        filtered = [
            s for s in filtered
            if s.score.classification.lower() == classification.lower()
        ]

    if search:
        q = search.lower().strip()
        filtered = [
            s for s in filtered
            if q in s.symbol.lower() or q in s.company_name.lower()
        ]

    return filtered

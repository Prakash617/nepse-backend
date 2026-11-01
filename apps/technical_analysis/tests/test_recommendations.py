"""Unit tests for recommendation categorization and filtering."""

from __future__ import annotations

import datetime

from apps.technical_analysis.scoring.ranking import build_stock_rankings
from apps.technical_analysis.services.recommendation_service import get_candidates_by_category
from apps.technical_analysis.services.stock_ranking import filter_stock_rankings
from apps.technical_analysis.tests.test_rankings import _make_dummy_sector, _make_dummy_stock


class TestRecommendationService:
    """Test candidate filtering and research categories."""

    def test_filter_stock_rankings(self) -> None:
        stk1 = _make_dummy_stock(1, "NABIL", 1, 85.0, "Strong Technical Candidate")
        stk2 = _make_dummy_stock(2, "GBIME", 1, 70.0, "Bullish Candidate")
        stk3 = _make_dummy_stock(3, "SHIVM", 2, 45.0, "Weakening")
        stocks = [stk1, stk2, stk3]

        # Filter by sector
        f_sec1 = filter_stock_rankings(stocks, sector_id=1)
        assert len(f_sec1) == 2

        # Filter by min_score
        f_score = filter_stock_rankings(stocks, min_score=80.0)
        assert len(f_score) == 1
        assert f_score[0].symbol == "NABIL"

        # Filter by search
        f_search = filter_stock_rankings(stocks, search="gb")
        assert len(f_search) == 1
        assert f_search[0].symbol == "GBIME"

    def test_get_candidates_by_category(self) -> None:
        stk1 = _make_dummy_stock(1, "STK1", 1, 85.0)
        stk2 = _make_dummy_stock(2, "STK2", 1, 72.0)
        stk3 = _make_dummy_stock(3, "STK3", 2, 55.0, "Emerging Candidate")
        stocks = [stk1, stk2, stk3]
        sec1 = _make_dummy_sector(1, "Sec1", 80.0)
        sec2 = _make_dummy_sector(2, "Sec2", 70.0)

        rankings = build_stock_rankings(stocks, [sec1, sec2], datetime.date(2026, 1, 1))

        strong_cands = get_candidates_by_category(rankings, "strong_bullish")
        assert len(strong_cands) == 1
        assert strong_cands[0].symbol == "STK1"

        emerging_cands = get_candidates_by_category(rankings, "emerging")
        assert len(emerging_cands) == 1
        assert emerging_cands[0].symbol == "STK3"

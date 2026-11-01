"""FilterSets for technical analysis endpoints."""

from __future__ import annotations

import django_filters
from django.db.models import Q

from apps.technical_analysis.models import (
    RecommendationSnapshot,
    SectorAnalysisSnapshot,
    TechnicalScoreSnapshot,
    TradingSignal,
)


class StockRankingFilter(django_filters.FilterSet):
    """Filter for stock technical scores and screeners."""

    sector = django_filters.CharFilter(field_name="security__sector__name", lookup_expr="iexact")
    sector_id = django_filters.NumberFilter(field_name="security__sector__id")
    classification = django_filters.CharFilter(lookup_expr="iexact")
    min_score = django_filters.NumberFilter(field_name="total_score", lookup_expr="gte")
    max_score = django_filters.NumberFilter(field_name="total_score", lookup_expr="lte")
    trading_date = django_filters.DateFilter()
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = TechnicalScoreSnapshot
        fields = [
            "sector",
            "sector_id",
            "classification",
            "min_score",
            "max_score",
            "trading_date",
        ]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(security__symbol__icontains=value) | Q(security__company_name__icontains=value)
        )


class SectorSnapshotFilter(django_filters.FilterSet):
    """Filter for sector analysis snapshots."""

    classification = django_filters.CharFilter(lookup_expr="iexact")
    rotation_stage = django_filters.CharFilter(lookup_expr="iexact")
    trading_date = django_filters.DateFilter()
    min_score = django_filters.NumberFilter(field_name="sector_score", lookup_expr="gte")

    class Meta:
        model = SectorAnalysisSnapshot
        fields = [
            "classification",
            "rotation_stage",
            "trading_date",
            "min_score",
        ]


class RecommendationFilter(django_filters.FilterSet):
    """Filter for algorithmic candidate recommendations."""

    category = django_filters.CharFilter(lookup_expr="iexact")
    sector_id = django_filters.NumberFilter()
    trading_date = django_filters.DateFilter()
    min_score = django_filters.NumberFilter(field_name="technical_score", lookup_expr="gte")

    class Meta:
        model = RecommendationSnapshot
        fields = ["category", "sector_id", "trading_date", "min_score"]


class TradingSignalFilter(django_filters.FilterSet):
    """Filter for daily and historical trading signals."""

    strategy = django_filters.CharFilter(field_name="strategy_type", lookup_expr="iexact")
    strategy_type = django_filters.CharFilter(lookup_expr="iexact")
    setup_type = django_filters.CharFilter(lookup_expr="iexact")
    status = django_filters.CharFilter(lookup_expr="iexact")
    symbol = django_filters.CharFilter(field_name="security__symbol", lookup_expr="iexact")
    sector = django_filters.CharFilter(field_name="security__sector__name", lookup_expr="iexact")
    signal_date = django_filters.DateFilter()
    date_from = django_filters.DateFilter(field_name="signal_date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="signal_date", lookup_expr="lte")
    min_score = django_filters.NumberFilter(field_name="composite_score", lookup_expr="gte")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = TradingSignal
        fields = [
            "strategy",
            "strategy_type",
            "setup_type",
            "status",
            "symbol",
            "sector",
            "signal_date",
            "date_from",
            "date_to",
            "min_score",
        ]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(security__symbol__icontains=value)
            | Q(security__company_name__icontains=value)
            | Q(rationale__icontains=value)
        )


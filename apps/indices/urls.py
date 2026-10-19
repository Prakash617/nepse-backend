"""Index API URL patterns."""

from django.urls import path

from apps.indices.views import (
    IndexHistoryView,
    IndexIntradayView,
    MarketIndexDetailView,
    MarketIndexListView,
)

urlpatterns = [
    path("", MarketIndexListView.as_view(), name="index-list"),
    path("intraday/", IndexIntradayView.as_view(), name="index-intraday-default"),
    path("<int:nepse_id>/", MarketIndexDetailView.as_view(), name="index-detail"),
    path("<int:nepse_id>/intraday/", IndexIntradayView.as_view(), name="index-intraday"),
    path("<int:nepse_id>/history/", IndexHistoryView.as_view(), name="index-history"),
]

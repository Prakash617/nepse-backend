"""Market API URL patterns."""

from django.urls import path

from apps.market.views import (
    MarketGainersView,
    MarketLosersView,
    MarketStatusView,
    MarketSummaryView,
    MarketTurnoverView,
    MarketVolumeView,
)

urlpatterns = [
    path("status/", MarketStatusView.as_view(), name="market-status"),
    path("summary/", MarketSummaryView.as_view(), name="market-summary"),
    path("gainers/", MarketGainersView.as_view(), name="market-gainers"),
    path("losers/", MarketLosersView.as_view(), name="market-losers"),
    path("turnover/", MarketTurnoverView.as_view(), name="market-turnover"),
    path("volume/", MarketVolumeView.as_view(), name="market-volume"),
]

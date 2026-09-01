"""Index API URL patterns."""

from django.urls import path

from apps.indices.views import IndexHistoryView, MarketIndexDetailView, MarketIndexListView

urlpatterns = [
    path("", MarketIndexListView.as_view(), name="index-list"),
    path("<int:nepse_id>/", MarketIndexDetailView.as_view(), name="index-detail"),
    path("<int:nepse_id>/history/", IndexHistoryView.as_view(), name="index-history"),
]

"""Security API URL patterns."""

from django.urls import path

from apps.securities.views import (
    SecurityDetailView,
    SecurityHistoryView,
    SecurityIntradayView,
    SecurityListView,
)

urlpatterns = [
    path("", SecurityListView.as_view(), name="security-list"),
    path("<str:symbol>/", SecurityDetailView.as_view(), name="security-detail"),
    path("<str:symbol>/history/", SecurityHistoryView.as_view(), name="security-history"),
    path("<str:symbol>/intraday/", SecurityIntradayView.as_view(), name="security-intraday"),
]

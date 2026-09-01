"""Sector API URL patterns."""

from django.urls import path

from apps.sectors.views import SectorListView

urlpatterns = [
    path("", SectorListView.as_view(), name="sector-list"),
]

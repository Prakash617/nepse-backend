"""Watchlist API URL patterns."""

from django.urls import path

from apps.watchlist.views import (
    WatchlistDetailView,
    WatchlistItemCreateView,
    WatchlistItemDeleteView,
    WatchlistListCreateView,
)

urlpatterns = [
    path("", WatchlistListCreateView.as_view(), name="watchlist-list"),
    path("<int:pk>/", WatchlistDetailView.as_view(), name="watchlist-detail"),
    path("<int:pk>/items/", WatchlistItemCreateView.as_view(), name="watchlist-item-create"),
    path("<int:pk>/items/<int:item_pk>/", WatchlistItemDeleteView.as_view(), name="watchlist-item-delete"),
]

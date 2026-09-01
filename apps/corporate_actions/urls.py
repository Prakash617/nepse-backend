"""Corporate Actions API URL patterns."""

from django.urls import path

from apps.corporate_actions.views import (
    BonusShareDetailView,
    BonusShareListView,
    DividendDetailView,
    DividendListView,
)

urlpatterns = [
    path("dividends/", DividendListView.as_view(), name="dividend-list"),
    path("dividends/<int:pk>/", DividendDetailView.as_view(), name="dividend-detail"),
    path("bonus-shares/", BonusShareListView.as_view(), name="bonus-share-list"),
    path("bonus-shares/<int:pk>/", BonusShareDetailView.as_view(), name="bonus-share-detail"),
]

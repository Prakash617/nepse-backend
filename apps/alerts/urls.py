"""Alert URL routing."""

from django.urls import path
from apps.alerts.views import (
    AlertListCreateView,
    AlertDetailView,
    AlertPauseView,
    AlertResumeView,
    AlertHistoryListView,
)

app_name = "alerts"

urlpatterns = [
    path("", AlertListCreateView.as_view(), name="alert-list-create"),
    path("history/", AlertHistoryListView.as_view(), name="alert-history-all"),
    path("<int:pk>/", AlertDetailView.as_view(), name="alert-detail"),
    path("<int:pk>/pause/", AlertPauseView.as_view(), name="alert-pause"),
    path("<int:pk>/resume/", AlertResumeView.as_view(), name="alert-resume"),
    path("<int:pk>/history/", AlertHistoryListView.as_view(), name="alert-history"),
]

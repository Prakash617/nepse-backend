"""System specifications and telemetry URL patterns."""

from django.urls import path

from apps.market.system_views import (
    HealthCheckView,
    SystemSpecsView,
    SystemSyncHistoryView,
    SystemSyncTriggerView,
)

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="system-health"),
    path("specs/", SystemSpecsView.as_view(), name="system-specs"),
    path("sync/", SystemSyncTriggerView.as_view(), name="system-sync-trigger"),
    path("sync/history/", SystemSyncHistoryView.as_view(), name="system-sync-history"),
]

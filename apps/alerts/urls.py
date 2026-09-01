"""Alert API URL patterns."""

from django.urls import path

from apps.alerts.views import AlertDetailView, AlertListCreateView

urlpatterns = [
    path("", AlertListCreateView.as_view(), name="alert-list"),
    path("<int:pk>/", AlertDetailView.as_view(), name="alert-detail"),
]

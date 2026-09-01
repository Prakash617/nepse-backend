"""Fundamentals API URL patterns."""

from django.urls import path

from apps.fundamentals.views import (
    CompanyProfileDetailView,
    CompanyProfileListView,
    FinancialReportDetailView,
    FinancialReportListView,
)

urlpatterns = [
    path("profiles/", CompanyProfileListView.as_view(), name="company-profile-list"),
    path("profiles/<int:nepse_id>/", CompanyProfileDetailView.as_view(), name="company-profile-detail"),
    path("reports/", FinancialReportListView.as_view(), name="financial-report-list"),
    path("reports/<int:pk>/", FinancialReportDetailView.as_view(), name="financial-report-detail"),
]

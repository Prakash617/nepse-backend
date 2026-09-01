"""Fundamentals API views."""

from django.db.models import QuerySet
from rest_framework import generics

from apps.fundamentals.models import CompanyProfile, FinancialReport
from apps.fundamentals.serializers import CompanyProfileSerializer, FinancialReportSerializer


class CompanyProfileListView(generics.ListAPIView):
    queryset = CompanyProfile.objects.select_related("security").all()
    serializer_class = CompanyProfileSerializer

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()

        symbol = self.request.query_params.get("security__symbol")
        if symbol:
            qs = qs.filter(security__symbol__iexact=symbol)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)

        return qs.order_by("security__symbol")


class CompanyProfileDetailView(generics.RetrieveAPIView):
    queryset = CompanyProfile.objects.select_related("security").all()
    serializer_class = CompanyProfileSerializer
    lookup_field = "nepse_id"
    lookup_url_kwarg = "nepse_id"


class FinancialReportListView(generics.ListAPIView):
    queryset = FinancialReport.objects.select_related("security").all()
    serializer_class = FinancialReportSerializer

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()

        symbol = self.request.query_params.get("security__symbol")
        if symbol:
            qs = qs.filter(security__symbol__iexact=symbol)

        fiscal_year = self.request.query_params.get("fiscal_year")
        if fiscal_year:
            qs = qs.filter(fiscal_year=fiscal_year)

        report_type = self.request.query_params.get("report_type")
        if report_type:
            qs = qs.filter(report_type__icontains=report_type)

        return qs.order_by("-fiscal_year", "security__symbol")


class FinancialReportDetailView(generics.RetrieveAPIView):
    queryset = FinancialReport.objects.select_related("security").all()
    serializer_class = FinancialReportSerializer

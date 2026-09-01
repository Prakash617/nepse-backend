"""Tests for fundamentals API endpoints."""

import pytest
from rest_framework.test import APIClient

from apps.fundamentals.models import CompanyProfile, FinancialReport
from apps.securities.models import Security


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def security():
    return Security.objects.create(
        nepse_id=100,
        symbol="TEST",
        company_name="Test Company",
    )


@pytest.mark.django_db
class TestCompanyProfileAPI:
    def test_list_profiles(self, api_client, security):
        CompanyProfile.objects.create(
            security=security, nepse_id=100, name="Test Company"
        )
        response = api_client.get("/api/v1/fundamentals/profiles/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_retrieve_profile(self, api_client, security):
        CompanyProfile.objects.create(
            security=security, nepse_id=100, name="Test Company"
        )
        response = api_client.get("/api/v1/fundamentals/profiles/100/")
        assert response.status_code == 200
        assert response.data["name"] == "Test Company"

    def test_filter_by_symbol(self, api_client):
        security1 = Security.objects.create(
            nepse_id=100, symbol="TEST1", company_name="Company 1"
        )
        security2 = Security.objects.create(
            nepse_id=101, symbol="TEST2", company_name="Company 2"
        )
        CompanyProfile.objects.create(security=security1, nepse_id=100, name="Company 1")
        CompanyProfile.objects.create(security=security2, nepse_id=101, name="Company 2")
        response = api_client.get("/api/v1/fundamentals/profiles/", {"security__symbol": "TEST1"})
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_search_by_name(self, api_client, security):
        CompanyProfile.objects.create(security=security, nepse_id=100, name="Test Company")
        response = api_client.get("/api/v1/fundamentals/profiles/", {"search": "Test"})
        assert response.status_code == 200
        assert len(response.data["results"]) == 1


@pytest.mark.django_db
class TestFinancialReportAPI:
    def test_list_reports(self, api_client, security):
        FinancialReport.objects.create(
            security=security, fiscal_year="2081/82", report_type="Annual Report"
        )
        response = api_client.get("/api/v1/fundamentals/reports/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filter_by_fiscal_year(self, api_client, security):
        FinancialReport.objects.create(
            security=security, fiscal_year="2081/82", report_type="Annual Report"
        )
        FinancialReport.objects.create(
            security=security, fiscal_year="2080/81", report_type="Annual Report"
        )
        response = api_client.get("/api/v1/fundamentals/reports/", {"fiscal_year": "2081/82"})
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filter_by_report_type(self, api_client, security):
        FinancialReport.objects.create(
            security=security, fiscal_year="2081/82", report_type="Annual Report"
        )
        FinancialReport.objects.create(
            security=security, fiscal_year="2081/82", report_type="Quarterly Report"
        )
        response = api_client.get("/api/v1/fundamentals/reports/", {"report_type": "Annual"})
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

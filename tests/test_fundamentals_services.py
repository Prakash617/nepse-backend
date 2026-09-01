"""Tests for fundamentals sync services."""

import pytest

from apps.fundamentals.models import CompanyProfile, FinancialReport
from apps.fundamentals.services import sync_company_profiles, sync_financial_reports
from apps.securities.models import Security


@pytest.fixture
def security():
    return Security.objects.create(
        nepse_id=100,
        symbol="TEST",
        company_name="Test Company",
    )


@pytest.mark.django_db
class TestSyncCompanyProfiles:
    def test_creates_new_profiles(self, security):
        profiles_data = [
            {"nepse_id": 100, "name": "Test Company", "address": "Kathmandu"}
        ]
        result = sync_company_profiles(profiles_data)
        assert result.created == 1
        assert CompanyProfile.objects.filter(nepse_id=100).exists()

    def test_updates_existing_profiles(self, security):
        CompanyProfile.objects.create(
            security=security, nepse_id=100, name="Old Name"
        )
        profiles_data = [
            {"nepse_id": 100, "name": "New Name", "address": "Updated"}
        ]
        result = sync_company_profiles(profiles_data)
        assert result.updated == 1
        profile = CompanyProfile.objects.get(nepse_id=100)
        assert profile.name == "New Name"

    def test_skips_unchanged_profiles(self, security):
        CompanyProfile.objects.create(
            security=security, nepse_id=100, name="Test Company"
        )
        profiles_data = [
            {"nepse_id": 100, "name": "Test Company"}
        ]
        result = sync_company_profiles(profiles_data)
        assert result.skipped == 1

    def test_skips_invalid_data(self):
        profiles_data = [{"name": "No ID"}]
        result = sync_company_profiles(profiles_data)
        assert result.skipped == 1
        assert len(result.errors) == 1

    def test_skips_missing_security(self):
        profiles_data = [{"nepse_id": 999, "name": "No Security"}]
        result = sync_company_profiles(profiles_data)
        assert result.skipped == 1

    def test_idempotent(self, security):
        profiles_data = [{"nepse_id": 100, "name": "Test"}]
        result1 = sync_company_profiles(profiles_data)
        result2 = sync_company_profiles(profiles_data)
        assert result1.created == 1
        assert result2.skipped == 1


@pytest.mark.django_db
class TestSyncFinancialReports:
    def test_creates_new_reports(self, security):
        reports_data = [
            {
                "nepse_id": 100,
                "fiscal_year": "2081/82",
                "report_type": "Annual Report",
                "file_url": "https://example.com/report.pdf",
            }
        ]
        result = sync_financial_reports(reports_data)
        assert result.created == 1
        assert FinancialReport.objects.filter(
            security__nepse_id=100, fiscal_year="2081/82"
        ).exists()

    def test_updates_existing_reports(self, security):
        FinancialReport.objects.create(
            security=security,
            fiscal_year="2081/82",
            report_type="Annual Report",
            file_url="https://example.com/old.pdf",
        )
        reports_data = [
            {
                "nepse_id": 100,
                "fiscal_year": "2081/82",
                "report_type": "Annual Report",
                "file_url": "https://example.com/new.pdf",
            }
        ]
        result = sync_financial_reports(reports_data)
        assert result.updated == 1
        report = FinancialReport.objects.get(
            security__nepse_id=100, fiscal_year="2081/82"
        )
        assert report.file_url == "https://example.com/new.pdf"

    def test_skips_unchanged_reports(self, security):
        FinancialReport.objects.create(
            security=security,
            fiscal_year="2081/82",
            report_type="Annual Report",
            file_url="https://example.com/report.pdf",
        )
        reports_data = [
            {
                "nepse_id": 100,
                "fiscal_year": "2081/82",
                "report_type": "Annual Report",
                "file_url": "https://example.com/report.pdf",
            }
        ]
        result = sync_financial_reports(reports_data)
        assert result.skipped == 1

    def test_skips_invalid_data(self):
        reports_data = [{"nepse_id": 100}]
        result = sync_financial_reports(reports_data)
        assert result.skipped == 1

    def test_idempotent(self, security):
        reports_data = [
            {
                "nepse_id": 100,
                "fiscal_year": "2081/82",
                "report_type": "Annual Report",
                "file_url": "https://example.com/report.pdf",
            }
        ]
        result1 = sync_financial_reports(reports_data)
        result2 = sync_financial_reports(reports_data)
        assert result1.created == 1
        assert result2.skipped == 1

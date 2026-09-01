"""Tests for fundamentals models."""

import pytest
from django.db import IntegrityError

from apps.fundamentals.models import CompanyProfile, FinancialReport
from apps.securities.models import Security


@pytest.fixture
def security():
    return Security.objects.create(
        nepse_id=100,
        symbol="TEST",
        company_name="Test Company",
    )


@pytest.mark.django_db
class TestCompanyProfile:
    def test_create_profile(self, security):
        profile = CompanyProfile.objects.create(
            security=security,
            nepse_id=security.nepse_id,
            name="Test Company",
            address="Kathmandu, Nepal",
            contact_number="+977-1-1234567",
            website="https://example.com",
            email="info@example.com",
            description="A test company.",
        )
        assert profile.pk is not None
        assert profile.name == "Test Company"
        assert str(profile) == "Profile: Test Company"

    def test_unique_nepse_id(self, security):
        security2 = Security.objects.create(
            nepse_id=101, symbol="TEST2", company_name="Test 2"
        )
        CompanyProfile.objects.create(
            security=security, nepse_id=1, name="Company 1"
        )
        with pytest.raises(IntegrityError):
            CompanyProfile.objects.create(
                security=security2, nepse_id=1, name="Company 2"
            )

    def test_one_to_one_relationship(self, security):
        CompanyProfile.objects.create(
            security=security, nepse_id=security.nepse_id, name="Test"
        )
        with pytest.raises(IntegrityError):
            CompanyProfile.objects.create(
                security=security, nepse_id=security.nepse_id + 1, name="Test 2"
            )


@pytest.mark.django_db
class TestFinancialReport:
    def test_create_report(self, security):
        report = FinancialReport.objects.create(
            security=security,
            fiscal_year="2081/82",
            report_type="Annual Report",
            file_url="https://example.com/report.pdf",
        )
        assert report.pk is not None
        assert report.fiscal_year == "2081/82"
        expected = f"{security.symbol} - 2081/82 (Annual Report)"
        assert str(report) == expected

    def test_unique_together_constraint(self, security):
        FinancialReport.objects.create(
            security=security,
            fiscal_year="2081/82",
            report_type="Annual Report",
        )
        with pytest.raises(IntegrityError):
            FinancialReport.objects.create(
                security=security,
                fiscal_year="2081/82",
                report_type="Annual Report",
            )

    def test_different_report_types_same_year(self, security):
        FinancialReport.objects.create(
            security=security,
            fiscal_year="2081/82",
            report_type="Annual Report",
        )
        report2 = FinancialReport.objects.create(
            security=security,
            fiscal_year="2081/82",
            report_type="Quarterly Report",
        )
        assert report2.pk is not None

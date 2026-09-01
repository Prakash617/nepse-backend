"""Tests for corporate actions API endpoints."""

import pytest
from rest_framework.test import APIClient

from apps.corporate_actions.models import BonusShare, Dividend
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
class TestDividendAPI:
    def test_list_dividends(self, api_client, security):
        Dividend.objects.create(
            security=security, fiscal_year="2081/82", dividend_per_share=10.00
        )
        response = api_client.get("/api/v1/corporate-actions/dividends/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filter_by_symbol(self, api_client):
        security1 = Security.objects.create(
            nepse_id=100, symbol="TEST1", company_name="Company 1"
        )
        security2 = Security.objects.create(
            nepse_id=101, symbol="TEST2", company_name="Company 2"
        )
        Dividend.objects.create(
            security=security1, fiscal_year="2081/82", dividend_per_share=10.00
        )
        Dividend.objects.create(
            security=security2, fiscal_year="2081/82", dividend_per_share=5.00
        )
        response = api_client.get("/api/v1/corporate-actions/dividends/", {"security__symbol": "TEST1"})
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filter_by_fiscal_year(self, api_client, security):
        Dividend.objects.create(
            security=security, fiscal_year="2081/82", dividend_per_share=10.00
        )
        Dividend.objects.create(
            security=security, fiscal_year="2080/81", dividend_per_share=5.00
        )
        response = api_client.get("/api/v1/corporate-actions/dividends/", {"fiscal_year": "2081/82"})
        assert response.status_code == 200
        assert len(response.data["results"]) == 1


@pytest.mark.django_db
class TestBonusShareAPI:
    def test_list_bonuses(self, api_client, security):
        BonusShare.objects.create(
            security=security, fiscal_year="2081/82", bonus_ratio="1:1"
        )
        response = api_client.get("/api/v1/corporate-actions/bonus-shares/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filter_by_fiscal_year(self, api_client, security):
        BonusShare.objects.create(
            security=security, fiscal_year="2081/82", bonus_ratio="1:1"
        )
        BonusShare.objects.create(
            security=security, fiscal_year="2080/81", bonus_ratio="1:2"
        )
        response = api_client.get("/api/v1/corporate-actions/bonus-shares/", {"fiscal_year": "2081/82"})
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filter_by_symbol(self, api_client):
        security1 = Security.objects.create(
            nepse_id=100, symbol="TEST1", company_name="Company 1"
        )
        security2 = Security.objects.create(
            nepse_id=101, symbol="TEST2", company_name="Company 2"
        )
        BonusShare.objects.create(
            security=security1, fiscal_year="2081/82", bonus_ratio="1:1"
        )
        BonusShare.objects.create(
            security=security2, fiscal_year="2081/82", bonus_ratio="1:2"
        )
        response = api_client.get("/api/v1/corporate-actions/bonus-shares/", {"security__symbol": "TEST1"})
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

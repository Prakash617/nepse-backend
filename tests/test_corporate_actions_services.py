"""Tests for corporate actions sync services."""

import pytest

from apps.corporate_actions.models import BonusShare, Dividend
from apps.corporate_actions.services import sync_bonus_shares, sync_dividends
from apps.securities.models import Security


@pytest.fixture
def security():
    return Security.objects.create(
        nepse_id=100,
        symbol="TEST",
        company_name="Test Company",
    )


@pytest.mark.django_db
class TestSyncDividends:
    def test_creates_new_dividends(self, security):
        dividends_data = [
            {
                "nepse_id": 100,
                "fiscal_year": "2081/82",
                "dividend_per_share": 10.00,
                "bonus_shares": 1.00,
            }
        ]
        result = sync_dividends(dividends_data)
        assert result.created == 1
        assert Dividend.objects.filter(security__nepse_id=100).exists()

    def test_updates_existing_dividends(self, security):
        Dividend.objects.create(
            security=security,
            fiscal_year="2081/82",
            dividend_per_share=5.00,
        )
        dividends_data = [
            {
                "nepse_id": 100,
                "fiscal_year": "2081/82",
                "dividend_per_share": 10.00,
            }
        ]
        result = sync_dividends(dividends_data)
        assert result.updated == 1
        dividend = Dividend.objects.get(security__nepse_id=100)
        assert dividend.dividend_per_share == 10.00

    def test_skips_unchanged_dividends(self, security):
        Dividend.objects.create(
            security=security,
            fiscal_year="2081/82",
            dividend_per_share=10.00,
        )
        dividends_data = [
            {
                "nepse_id": 100,
                "fiscal_year": "2081/82",
                "dividend_per_share": 10.00,
            }
        ]
        result = sync_dividends(dividends_data)
        assert result.skipped == 1

    def test_skips_invalid_data(self):
        dividends_data = [{"nepse_id": 100}]
        result = sync_dividends(dividends_data)
        assert result.skipped == 1

    def test_idempotent(self, security):
        dividends_data = [
            {"nepse_id": 100, "fiscal_year": "2081/82", "dividend_per_share": 10.00}
        ]
        result1 = sync_dividends(dividends_data)
        result2 = sync_dividends(dividends_data)
        assert result1.created == 1
        assert result2.skipped == 1


@pytest.mark.django_db
class TestSyncBonusShares:
    def test_creates_new_bonuses(self, security):
        bonus_data = [
            {"nepse_id": 100, "fiscal_year": "2081/82", "bonus_ratio": "1:1"}
        ]
        result = sync_bonus_shares(bonus_data)
        assert result.created == 1
        assert BonusShare.objects.filter(security__nepse_id=100).exists()

    def test_updates_existing_bonuses(self, security):
        BonusShare.objects.create(
            security=security,
            fiscal_year="2081/82",
            bonus_ratio="1:2",
        )
        bonus_data = [
            {"nepse_id": 100, "fiscal_year": "2081/82", "bonus_ratio": "1:1"}
        ]
        result = sync_bonus_shares(bonus_data)
        assert result.updated == 1
        bonus = BonusShare.objects.get(security__nepse_id=100)
        assert bonus.bonus_ratio == "1:1"

    def test_skips_unchanged_bonuses(self, security):
        BonusShare.objects.create(
            security=security,
            fiscal_year="2081/82",
            bonus_ratio="1:1",
        )
        bonus_data = [
            {"nepse_id": 100, "fiscal_year": "2081/82", "bonus_ratio": "1:1"}
        ]
        result = sync_bonus_shares(bonus_data)
        assert result.skipped == 1

    def test_skips_invalid_data(self):
        bonus_data = [{"nepse_id": 100}]
        result = sync_bonus_shares(bonus_data)
        assert result.skipped == 1

    def test_idempotent(self, security):
        bonus_data = [
            {"nepse_id": 100, "fiscal_year": "2081/82", "bonus_ratio": "1:1"}
        ]
        result1 = sync_bonus_shares(bonus_data)
        result2 = sync_bonus_shares(bonus_data)
        assert result1.created == 1
        assert result2.skipped == 1

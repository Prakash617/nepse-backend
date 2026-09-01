"""Tests for corporate actions models."""

import pytest

from apps.corporate_actions.models import BonusShare, Dividend
from apps.securities.models import Security


@pytest.fixture
def security():
    return Security.objects.create(
        nepse_id=100,
        symbol="TEST",
        company_name="Test Company",
    )


@pytest.mark.django_db
class TestDividend:
    def test_create_dividend(self, security):
        dividend = Dividend.objects.create(
            security=security,
            fiscal_year="2081/82",
            dividend_per_share=10.00,
            bonus_shares=1.00,
        )
        assert dividend.pk is not None
        assert dividend.fiscal_year == "2081/82"
        expected = f"{security.symbol} - 2081/82"
        assert str(dividend) == expected

    def test_nullable_fields(self, security):
        dividend = Dividend.objects.create(
            security=security,
            fiscal_year="2081/82",
        )
        assert dividend.dividend_per_share is None
        assert dividend.bonus_shares is None
        assert dividend.announcement_date is None


@pytest.mark.django_db
class TestBonusShare:
    def test_create_bonus_share(self, security):
        bonus = BonusShare.objects.create(
            security=security,
            fiscal_year="2081/82",
            bonus_ratio="1:1",
        )
        assert bonus.pk is not None
        assert bonus.bonus_ratio == "1:1"
        expected = f"{security.symbol} - 2081/82 (1:1)"
        assert str(bonus) == expected

    def test_default_ratio_empty(self, security):
        bonus = BonusShare.objects.create(
            security=security,
            fiscal_year="2081/82",
        )
        assert bonus.bonus_ratio == ""

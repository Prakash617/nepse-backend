"""Tests for alert evaluation service."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.alerts.models import Alert
from apps.notifications.models import Notification
from apps.notifications.services import (
    _evaluate_condition,
    _get_latest_price,
    evaluate_alerts,
)
from apps.prices.models import DailyPrice
from apps.securities.models import Security

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def security():
    return Security.objects.create(
        nepse_id=100, symbol="TEST", company_name="Test Company"
    )


@pytest.mark.django_db
class TestGetLatestPrice:
    def test_returns_latest_price(self, security):
        DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("1000.00")
        )
        DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 16), ltp=Decimal("1050.00")
        )
        latest = _get_latest_price(security.pk)
        assert latest is not None
        assert latest.ltp == Decimal("1050.00")
        assert latest.trading_date == date(2026, 1, 16)

    def test_returns_none_when_no_prices(self, security):
        assert _get_latest_price(security.pk) is None


@pytest.mark.django_db
class TestEvaluateCondition:
    def test_price_above_triggered(self, security):
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("1100.00")
        )
        alert = Alert(
            user=None, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=Decimal("1000.00"),
        )
        assert _evaluate_condition(alert, price) is True

    def test_price_above_not_triggered(self, security):
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("900.00")
        )
        alert = Alert(
            user=None, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=Decimal("1000.00"),
        )
        assert _evaluate_condition(alert, price) is False

    def test_price_below_triggered(self, security):
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("900.00")
        )
        alert = Alert(
            user=None, security=security,
            condition=Alert.ConditionType.PRICE_BELOW, threshold=Decimal("1000.00"),
        )
        assert _evaluate_condition(alert, price) is True

    def test_price_below_not_triggered(self, security):
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("1100.00")
        )
        alert = Alert(
            user=None, security=security,
            condition=Alert.ConditionType.PRICE_BELOW, threshold=Decimal("1000.00"),
        )
        assert _evaluate_condition(alert, price) is False

    def test_percent_change_up_triggered(self, security):
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15),
            ltp=Decimal("1050.00"), percentage_change=Decimal("5.50"),
        )
        alert = Alert(
            user=None, security=security,
            condition=Alert.ConditionType.PERCENT_CHANGE_UP, threshold=Decimal("5.00"),
        )
        assert _evaluate_condition(alert, price) is True

    def test_percent_change_up_not_triggered(self, security):
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15),
            ltp=Decimal("1020.00"), percentage_change=Decimal("2.00"),
        )
        alert = Alert(
            user=None, security=security,
            condition=Alert.ConditionType.PERCENT_CHANGE_UP, threshold=Decimal("5.00"),
        )
        assert _evaluate_condition(alert, price) is False

    def test_percent_change_down_triggered(self, security):
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15),
            ltp=Decimal("950.00"), percentage_change=Decimal("-6.00"),
        )
        alert = Alert(
            user=None, security=security,
            condition=Alert.ConditionType.PERCENT_CHANGE_DOWN, threshold=Decimal("5.00"),
        )
        assert _evaluate_condition(alert, price) is True

    def test_percent_change_down_not_triggered(self, security):
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15),
            ltp=Decimal("980.00"), percentage_change=Decimal("-2.00"),
        )
        alert = Alert(
            user=None, security=security,
            condition=Alert.ConditionType.PERCENT_CHANGE_DOWN, threshold=Decimal("5.00"),
        )
        assert _evaluate_condition(alert, price) is False

    def test_null_ltp_returns_false(self, security):
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=None
        )
        alert = Alert(
            user=None, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=Decimal("1000.00"),
        )
        assert _evaluate_condition(alert, price) is False

    def test_null_percentage_change_returns_false(self, security):
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15),
            ltp=Decimal("1050.00"), percentage_change=None,
        )
        alert = Alert(
            user=None, security=security,
            condition=Alert.ConditionType.PERCENT_CHANGE_UP, threshold=Decimal("5.00"),
        )
        assert _evaluate_condition(alert, price) is False


@pytest.mark.django_db
class TestEvaluateAlerts:
    def test_creates_notification_when_triggered(self, user, security):
        DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("1100.00")
        )
        Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=Decimal("1000.00"),
        )
        result = evaluate_alerts()
        assert result["triggered"] == 1
        assert Notification.objects.count() == 1
        notif = Notification.objects.first()
        assert notif.user == user
        assert "TEST" in notif.title

    def test_no_notification_when_not_triggered(self, user, security):
        DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("900.00")
        )
        Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=Decimal("1000.00"),
        )
        result = evaluate_alerts()
        assert result["triggered"] == 0
        assert Notification.objects.count() == 0

    def test_skips_inactive_alerts(self, user, security):
        DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("1100.00")
        )
        Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=Decimal("1000.00"),
            is_active=False,
        )
        result = evaluate_alerts()
        assert result["evaluated"] == 0
        assert result["triggered"] == 0
        assert Notification.objects.count() == 0

    def test_skips_alerts_with_no_price_data(self, user, security):
        Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=Decimal("1000.00"),
        )
        result = evaluate_alerts()
        assert result["triggered"] == 0
        assert result["skipped"] == 1

    def test_updates_last_triggered_at(self, user, security):
        DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("1100.00")
        )
        alert = Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=Decimal("1000.00"),
        )
        assert alert.last_triggered_at is None
        evaluate_alerts()
        alert.refresh_from_db()
        assert alert.last_triggered_at is not None

    def test_idempotent_same_day(self, user, security):
        DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("1100.00")
        )
        Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=Decimal("1000.00"),
        )
        result1 = evaluate_alerts()
        result2 = evaluate_alerts()
        assert result1["triggered"] == 1
        assert result2["triggered"] == 0
        assert Notification.objects.count() == 1

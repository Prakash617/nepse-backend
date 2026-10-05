"""Tests for alert models and state transitions."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.alerts.models import Alert, AlertHistory
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
class TestAlert:
    def test_create_alert(self, user, security):
        alert = Alert.objects.create(
            user=user,
            security=security,
            condition=Alert.ConditionType.PRICE_ABOVE,
            threshold=Decimal("1000.00"),
            frequency=Alert.FrequencyType.RECURRING,
            notify_browser_push=True,
            notify_in_app=True,
            cooldown_minutes=15,
        )
        assert alert.pk is not None
        assert alert.is_active is True
        assert alert.status == Alert.AlertStatus.ACTIVE
        assert alert.last_triggered_at is None
        assert alert.notify_browser_push is True
        assert alert.cooldown_minutes == 15
        assert "TEST" in str(alert)

    def test_pause_and_resume(self, user, security):
        alert = Alert.objects.create(
            user=user,
            security=security,
            condition=Alert.ConditionType.PRICE_BELOW,
            threshold=Decimal("500.00"),
        )
        assert alert.status == Alert.AlertStatus.ACTIVE
        assert alert.is_active is True

        alert.pause()
        assert alert.status == Alert.AlertStatus.PAUSED
        assert alert.is_active is False

        alert.resume()
        assert alert.status == Alert.AlertStatus.ACTIVE
        assert alert.is_active is True

    def test_alert_history_logging(self, user, security):
        alert = Alert.objects.create(
            user=user,
            security=security,
            condition=Alert.ConditionType.PRICE_ABOVE,
            threshold=Decimal("1000.00"),
        )
        history = AlertHistory.objects.create(
            alert=alert,
            user=user,
            security=security,
            triggered_value=Decimal("1050.00"),
            threshold=Decimal("1000.00"),
            condition=alert.condition,
            message="TEST reached 1050.00",
            push_sent=True,
            in_app_sent=True,
        )
        assert history.pk is not None
        assert history.triggered_value == Decimal("1050.00")
        assert history.push_sent is True
        assert str(history).startswith("TEST triggered at")

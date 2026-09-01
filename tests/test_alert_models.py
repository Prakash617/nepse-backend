"""Tests for alert models."""

import pytest
from django.contrib.auth import get_user_model

from apps.alerts.models import Alert
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
            threshold=1000.00,
        )
        assert alert.pk is not None
        assert alert.is_active is True
        assert alert.last_triggered_at is None
        expected = f"testuser - TEST Price Above {alert.threshold}"
        assert str(alert) == expected

    def test_default_is_active(self, user, security):
        alert = Alert.objects.create(
            user=user,
            security=security,
            condition=Alert.ConditionType.PRICE_BELOW,
            threshold=500.00,
        )
        assert alert.is_active is True

    def test_condition_choices(self):
        assert Alert.ConditionType.PRICE_ABOVE == "price_above"
        assert Alert.ConditionType.PRICE_BELOW == "price_below"
        assert Alert.ConditionType.PERCENT_CHANGE_UP == "percent_change_up"
        assert Alert.ConditionType.PERCENT_CHANGE_DOWN == "percent_change_down"

    def test_ordering(self, user, security):
        alert1 = Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=1000,
        )
        alert2 = Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_BELOW, threshold=500,
        )
        alerts = list(Alert.objects.filter(user=user))
        assert alerts[0] == alert2
        assert alerts[1] == alert1

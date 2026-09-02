"""Tests for AlertEngine evaluation, crossing logic, cooldowns, and multi-channel dispatch."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.alerts.engine import AlertEngine
from apps.alerts.models import Alert, AlertHistory
from apps.notifications.models import Notification
from apps.prices.models import DailyPrice
from apps.securities.models import Security

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(username="engineuser", password="testpass123")


@pytest.fixture
def security():
    return Security.objects.create(nepse_id=201, symbol="NABIL", company_name="Nabil Bank Limited")


@pytest.mark.django_db
class TestAlertEngineConditions:
    def test_price_cross_above(self, user, security):
        alert = Alert.objects.create(
            user=user,
            security=security,
            condition=Alert.ConditionType.PRICE_CROSS_ABOVE,
            threshold=Decimal("500.00"),
        )
        prev_price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 14), ltp=Decimal("495.00")
        )
        curr_price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("505.00")
        )

        triggered, val, msg = AlertEngine.evaluate_condition(alert, curr_price, prev_price)
        assert triggered is True
        assert val == Decimal("505.00")
        assert "crossed above" in msg

        # If previous price was already above, cross above should NOT trigger
        prev_above = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 16), ltp=Decimal("502.00")
        )
        curr_above = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 17), ltp=Decimal("508.00")
        )
        trig2, _, _ = AlertEngine.evaluate_condition(alert, curr_above, prev_above)
        assert trig2 is False

    def test_volume_above(self, user, security):
        alert = Alert.objects.create(
            user=user,
            security=security,
            condition=Alert.ConditionType.VOLUME_ABOVE,
            threshold=Decimal("50000"),
        )
        price_low = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 14), volume=20000
        )
        price_high = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), volume=65000
        )

        trig1, _, _ = AlertEngine.evaluate_condition(alert, price_low)
        assert trig1 is False

        trig2, val, msg = AlertEngine.evaluate_condition(alert, price_high)
        assert trig2 is True
        assert val == Decimal("65000")
        assert "traded volume reached" in msg


@pytest.mark.django_db
class TestAlertEngineLifecycle:
    @patch("apps.notifications.tasks.send_push_notification_task.delay")
    def test_one_time_alert_deactivates_on_trigger(self, mock_push_task, user, security):
        alert = Alert.objects.create(
            user=user,
            security=security,
            condition=Alert.ConditionType.PRICE_ABOVE,
            threshold=Decimal("500.00"),
            frequency=Alert.FrequencyType.ONCE,
            notify_in_app=True,
            notify_browser_push=True,
        )
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("520.00")
        )

        fired = AlertEngine.evaluate_single_alert(alert, price)
        assert fired is True

        alert.refresh_from_db()
        assert alert.status == Alert.AlertStatus.TRIGGERED
        assert alert.is_active is False
        assert alert.trigger_count == 1
        assert alert.triggered_price == Decimal("520.00")

        # Verify In-App Notification created
        assert Notification.objects.filter(user=user, alert=alert).count() == 1
        # Verify AlertHistory created
        assert AlertHistory.objects.filter(alert=alert).count() == 1
        # Verify Push task called
        assert mock_push_task.called

    def test_recurring_alert_reset_cycle(self, user, security):
        alert = Alert.objects.create(
            user=user,
            security=security,
            condition=Alert.ConditionType.PRICE_ABOVE,
            threshold=Decimal("500.00"),
            frequency=Alert.FrequencyType.RECURRING,
        )

        price1 = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("510.00")
        )
        fired1 = AlertEngine.evaluate_single_alert(alert, price1)
        assert fired1 is True
        alert.refresh_from_db()
        assert alert.status == Alert.AlertStatus.TRIGGERED

        # Price stays above -> duplicate trigger prevented
        price2 = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 16), ltp=Decimal("515.00")
        )
        fired2 = AlertEngine.evaluate_single_alert(alert, price2)
        assert fired2 is False

        # Price drops below -> reset boundary satisfied
        price3 = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 17), ltp=Decimal("490.00")
        )
        AlertEngine.check_and_update_reset_state(alert, price3)
        alert.refresh_from_db()
        assert alert.status == Alert.AlertStatus.ACTIVE

        # Price climbs back above -> triggers again!
        price4 = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 18), ltp=Decimal("505.00")
        )
        # Set last_triggered_at to past so cooldown/date check allows re-trigger
        alert.last_triggered_at = timezone.now() - timedelta(days=1)
        alert.save()

        fired3 = AlertEngine.evaluate_single_alert(alert, price4)
        assert fired3 is True
        alert.refresh_from_db()
        assert alert.trigger_count == 2

    def test_cooldown_protection(self, user, security):
        alert = Alert.objects.create(
            user=user,
            security=security,
            condition=Alert.ConditionType.PRICE_ABOVE,
            threshold=Decimal("500.00"),
            cooldown_minutes=30,
            last_triggered_at=timezone.now() - timedelta(minutes=10),
            status=Alert.AlertStatus.ACTIVE,
        )
        price = DailyPrice.objects.create(
            security=security, trading_date=date(2026, 1, 15), ltp=Decimal("510.00")
        )

        # 10 mins elapsed < 30 mins cooldown -> skipped
        fired = AlertEngine.evaluate_single_alert(alert, price)
        assert fired is False

        # Fast forward time past 30 mins
        alert.last_triggered_at = timezone.now() - timedelta(minutes=35)
        alert.save()

        fired2 = AlertEngine.evaluate_single_alert(alert, price)
        assert fired2 is True

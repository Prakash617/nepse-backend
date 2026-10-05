"""Tests for Telegram Bot notification integration, model, APIs, and dispatch."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.alerts.engine import AlertEngine
from apps.alerts.models import Alert
from apps.notifications.models import TelegramSubscription
from apps.notifications.telegram import (
    process_telegram_update,
    send_telegram_alert,
    send_telegram_raw_message,
)
from apps.prices.models import DailyPrice
from apps.securities.models import Security

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", email="test@example.com", password="password123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otheruser", email="other@example.com", password="password123")


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def security(db):
    return Security.objects.create(nepse_id=101, symbol="NABIL", company_name="Nabil Bank Limited")


@pytest.mark.django_db
class TestTelegramSubscriptionModel:
    def test_create_subscription(self, user):
        sub = TelegramSubscription.objects.create(
            user=user,
            chat_id="12345678",
            username="prakash",
            first_name="Prakash",
            is_active=True,
        )
        assert sub.pk is not None
        assert sub.chat_id == "12345678"
        assert sub.is_active is True
        assert str(user.username) in str(sub)


@pytest.mark.django_db
class TestTelegramServices:
    @patch("requests.post")
    def test_send_telegram_raw_message_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"ok": True})
        ok = send_telegram_raw_message("12345678", "Hello World")
        assert ok is True
        assert mock_post.called

    @patch("requests.post")
    def test_send_telegram_raw_message_bot_blocked_deactivates(self, mock_post, user):
        sub = TelegramSubscription.objects.create(
            user=user,
            chat_id="12345678",
            is_active=True,
        )
        mock_post.return_value = MagicMock(status_code=403, text="Forbidden: bot was blocked by the user")
        ok = send_telegram_raw_message("12345678", "Hello World")
        assert ok is False
        sub.refresh_from_db()
        assert sub.is_active is False

    @patch("requests.post")
    def test_send_telegram_alert(self, mock_post, user):
        TelegramSubscription.objects.create(
            user=user,
            chat_id="12345678",
            is_active=True,
        )
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"ok": True})
        delivered = send_telegram_alert(
            user=user,
            title="NABIL Reached Target",
            body="Price reached Rs. 600",
            data={"symbol": "NABIL", "price": "600", "threshold": "550"},
        )
        assert delivered == 1

    def test_process_start_command_with_code(self, user):
        sub = TelegramSubscription.objects.create(
            user=user,
            chat_id="",
            verification_code="TEST1234",
            is_active=False,
        )

        with patch("apps.notifications.telegram.send_telegram_raw_message", return_value=True):
            update = {
                "message": {
                    "chat": {"id": 987654321},
                    "from": {"username": "testtelegram", "first_name": "Test"},
                    "text": "/start TEST1234",
                }
            }
            res = process_telegram_update(update)
            assert res["status"] == "connected"
            sub.refresh_from_db()
            assert sub.is_active is True
            assert sub.chat_id == "987654321"
            assert sub.username == "testtelegram"

    def test_process_multiple_different_users_connect(self, user, other_user):
        sub_user1 = TelegramSubscription.objects.create(
            user=user,
            chat_id="",
            verification_code="USER1CODE",
            is_active=False,
        )
        sub_user2 = TelegramSubscription.objects.create(
            user=other_user,
            chat_id="",
            verification_code="USER2CODE",
            is_active=False,
        )

        with patch("apps.notifications.telegram.send_telegram_raw_message", return_value=True):
            # User 1 connects from Chat 111
            res1 = process_telegram_update({
                "message": {
                    "chat": {"id": 111},
                    "from": {"username": "user1_tg", "first_name": "User 1"},
                    "text": "/start USER1CODE",
                }
            })
            assert res1["status"] == "connected"
            assert res1["user"] == user.username

            # User 2 connects from Chat 222
            res2 = process_telegram_update({
                "message": {
                    "chat": {"id": 222},
                    "from": {"username": "user2_tg", "first_name": "User 2"},
                    "text": "/start USER2CODE",
                }
            })
            assert res2["status"] == "connected"
            assert res2["user"] == other_user.username

            sub_user1.refresh_from_db()
            sub_user2.refresh_from_db()

            assert sub_user1.chat_id == "111"
            assert sub_user1.is_active is True
            assert sub_user2.chat_id == "222"
            assert sub_user2.is_active is True


@pytest.mark.django_db
class TestTelegramAPI:
    def test_telegram_status_endpoint(self, api_client, user):
        res = api_client.get("/api/v1/notifications/telegram/status/")
        assert res.status_code == 200
        assert "is_connected" in res.data
        assert "connect_url" in res.data
        assert res.data["bot_username"] == "stock_napal_bot"

    def test_telegram_connect_endpoint(self, api_client, user):
        res = api_client.post("/api/v1/notifications/telegram/connect/")
        assert res.status_code == 200
        assert "verification_code" in res.data
        assert "start=" in res.data["connect_url"]

    def test_telegram_disconnect_endpoint(self, api_client, user):
        TelegramSubscription.objects.create(
            user=user,
            chat_id="123456",
            is_active=True,
        )
        res = api_client.post("/api/v1/notifications/telegram/disconnect/")
        assert res.status_code == 200
        assert res.data["success"] is True
        assert TelegramSubscription.objects.filter(user=user, is_active=True).count() == 0

    @patch("apps.notifications.views.send_test_telegram", return_value=True)
    def test_telegram_test_endpoint(self, mock_test, api_client, user):
        res = api_client.post("/api/v1/notifications/telegram/test/")
        assert res.status_code == 200
        assert res.data["success"] is True


@pytest.mark.django_db
class TestAlertEngineTelegramDispatch:
    @patch("apps.notifications.tasks.send_telegram_notification_task.delay")
    def test_alert_engine_dispatches_telegram(self, mock_task, user, security):
        Alert.objects.create(
            user=user,
            security=security,
            condition="price_above",
            threshold=Decimal("500.00"),
            is_active=True,
            notify_telegram=True,
        )
        DailyPrice.objects.create(
            security=security,
            trading_date="2026-09-02",
            ltp=Decimal("550.00"),
            close=Decimal("550.00"),
        )

        res = AlertEngine.evaluate_securities([security.id])
        assert res["triggered"] == 1
        assert mock_task.called

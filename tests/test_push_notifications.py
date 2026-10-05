"""Tests for Web Push subscriptions and notification delivery."""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from pywebpush import WebPushException
from rest_framework import status
from rest_framework.test import APIClient

from apps.notifications.models import PushSubscription
from apps.notifications.tasks import send_push_notification_task
from apps.notifications.webpush import PushNotificationService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(username="pushuser", password="testpass123")


@pytest.fixture
def other_user():
    return User.objects.create_user(username="otherpushuser", password="testpass123")


@pytest.fixture
def sample_subscription(user):
    return PushSubscription.objects.create(
        user=user,
        endpoint="https://updates.push.services.mozilla.com/wpush/v2/test1",
        p256dh="BNIPVKVp5gEyHkwpZZjDhGb84zlDuJjGu2YulvS74E2SuO15eifJXx2-nBcDJLU7ulWBShoZ_ZlOuGGdYbIw1Cs",
        auth="q5gl-g5G4mSbnRKK4Kbj6-3BQEjS9dFpApK9K4sI0kk",
        user_agent="Mozilla/5.0 Chrome/120.0",
        is_active=True,
    )


@pytest.mark.django_db
class TestPushSubscriptionModel:
    def test_create_subscription(self, user):
        sub = PushSubscription.objects.create(
            user=user,
            endpoint="https://fcm.googleapis.com/fcm/send/endpoint123",
            p256dh="test_p256dh_key",
            auth="test_auth_secret",
            user_agent="Firefox Desktop",
        )
        assert sub.pk is not None
        assert sub.is_active is True
        assert str(sub) == f"{user.username} - PushSubscription (active)"

    def test_unique_user_endpoint_constraint(self, user):
        PushSubscription.objects.create(
            user=user,
            endpoint="https://fcm.googleapis.com/fcm/send/dup",
            p256dh="key1",
            auth="auth1",
        )
        with pytest.raises(IntegrityError):
            PushSubscription.objects.create(
                user=user,
                endpoint="https://fcm.googleapis.com/fcm/send/dup",
                p256dh="key2",
                auth="auth2",
            )

    def test_multiple_devices_for_same_user(self, user):
        PushSubscription.objects.create(
            user=user,
            endpoint="https://fcm.googleapis.com/fcm/send/device1",
            p256dh="key1",
            auth="auth1",
        )
        PushSubscription.objects.create(
            user=user,
            endpoint="https://fcm.googleapis.com/fcm/send/device2",
            p256dh="key2",
            auth="auth2",
        )
        assert PushSubscription.objects.filter(user=user).count() == 2


@pytest.mark.django_db
class TestPushSubscriptionAPI:
    def test_subscribe_requires_auth(self, api_client):
        res = api_client.post(
            "/api/v1/notifications/push/subscribe/",
            data={"endpoint": "https://test.com", "keys": {"p256dh": "k", "auth": "a"}},
            format="json",
        )
        assert res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_subscribe_creates_subscription(self, api_client, user):
        api_client.force_authenticate(user=user)
        payload = {
            "endpoint": "https://updates.push.services.mozilla.com/wpush/v2/new_sub",
            "keys": {
                "p256dh": "mock_p256dh",
                "auth": "mock_auth",
            },
            "user_agent": "TestBrowser 1.0",
        }
        res = api_client.post("/api/v1/notifications/push/subscribe/", data=payload, format="json")
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["is_subscribed"] is True

        sub = PushSubscription.objects.get(user=user, endpoint=payload["endpoint"])
        assert sub.p256dh == "mock_p256dh"
        assert sub.auth == "mock_auth"
        assert sub.user_agent == "TestBrowser 1.0"
        assert sub.is_active is True

    def test_subscribe_updates_existing_subscription(self, api_client, user, sample_subscription):
        api_client.force_authenticate(user=user)
        sample_subscription.is_active = False
        sample_subscription.save()

        payload = {
            "endpoint": sample_subscription.endpoint,
            "keys": {
                "p256dh": "updated_p256dh",
                "auth": "updated_auth",
            },
        }
        res = api_client.post("/api/v1/notifications/push/subscribe/", data=payload, format="json")
        assert res.status_code == status.HTTP_200_OK

        sample_subscription.refresh_from_db()
        assert sample_subscription.p256dh == "updated_p256dh"
        assert sample_subscription.is_active is True

    def test_unsubscribe(self, api_client, user, sample_subscription):
        api_client.force_authenticate(user=user)
        res = api_client.post(
            "/api/v1/notifications/push/unsubscribe/",
            data={"endpoint": sample_subscription.endpoint},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["updated_count"] == 1

        sample_subscription.refresh_from_db()
        assert sample_subscription.is_active is False

    def test_unsubscribe_user_isolation(self, api_client, other_user, sample_subscription):
        api_client.force_authenticate(user=other_user)
        res = api_client.post(
            "/api/v1/notifications/push/unsubscribe/",
            data={"endpoint": sample_subscription.endpoint},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["updated_count"] == 0

        sample_subscription.refresh_from_db()
        assert sample_subscription.is_active is True

    def test_push_status(self, api_client, user, sample_subscription):
        api_client.force_authenticate(user=user)
        res = api_client.get("/api/v1/notifications/push/status/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["is_subscribed"] is True
        assert data["subscription_count"] == 1
        assert "vapid_public_key" in data
        assert len(data["vapid_public_key"]) > 20

    def test_push_status_unsubscribed_user(self, api_client, other_user):
        api_client.force_authenticate(user=other_user)
        res = api_client.get("/api/v1/notifications/push/status/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["is_subscribed"] is False
        assert data["subscription_count"] == 0


@pytest.mark.django_db
class TestPushNotificationService:
    @patch("apps.notifications.webpush.webpush")
    def test_send_push_success(self, mock_webpush, user, sample_subscription):
        mock_webpush.return_value = MagicMock(status_code=201)

        result = PushNotificationService.send_push_to_user(
            user=user,
            title="NABIL Alert",
            body="Target 540 hit",
            data={"symbol": "NABIL"},
        )
        assert result["sent"] == 1
        assert result["failed"] == 0
        assert mock_webpush.called
        call_kwargs = mock_webpush.call_args[1]
        assert call_kwargs["subscription_info"]["endpoint"] == sample_subscription.endpoint

    @patch("apps.notifications.webpush.webpush")
    def test_deactivates_expired_410_subscription(self, mock_webpush, user, sample_subscription):
        mock_response = MagicMock()
        mock_response.status_code = 410
        mock_webpush.side_effect = WebPushException("Gone", response=mock_response)

        result = PushNotificationService.send_push_to_user(
            user=user,
            title="Expired Test",
            body="Test body",
        )
        assert result["sent"] == 0
        assert result["failed"] == 1
        assert result["deactivated"] == 1

        sample_subscription.refresh_from_db()
        assert sample_subscription.is_active is False

    @patch("apps.notifications.webpush.webpush")
    def test_send_test_push_method(self, mock_webpush, user, sample_subscription):
        mock_webpush.return_value = MagicMock(status_code=201)

        result = PushNotificationService.send_test_push(user=user)
        assert result["sent"] == 1
        assert mock_webpush.called

    @patch("apps.notifications.webpush.webpush")
    def test_celery_send_push_task(self, mock_webpush, user, sample_subscription):
        mock_webpush.return_value = MagicMock(status_code=201)

        result = send_push_notification_task(
            user_id=user.id,
            title="Celery Task Alert",
            body="Celery delivered push",
        )
        assert result["sent"] == 1
        assert mock_webpush.called

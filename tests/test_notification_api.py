"""Tests for notification REST API."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.securities.models import Security

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def other_user():
    return User.objects.create_user(username="otheruser", password="testpass123")


@pytest.fixture
def security():
    return Security.objects.create(nepse_id=101, symbol="NABIL", company_name="Nabil Bank Limited")


@pytest.fixture
def user_notifications(user, security):
    n1 = Notification.objects.create(
        user=user,
        title="Price Alert 1",
        message="NABIL is above 500",
        notification_type=Notification.NotificationType.PRICE_ALERT,
        security=security,
        data={"symbol": "NABIL", "price": "520"},
        is_read=False,
    )
    n2 = Notification.objects.create(
        user=user,
        title="System Notice",
        message="System maintenance scheduled",
        notification_type=Notification.NotificationType.SYSTEM,
        is_read=True,
    )
    n3 = Notification.objects.create(
        user=user,
        title="Price Alert 2",
        message="NABIL is above 600",
        notification_type=Notification.NotificationType.PRICE_ALERT,
        security=security,
        is_read=False,
    )
    return [n1, n2, n3]


@pytest.mark.django_db
class TestNotificationListAPI:
    def test_requires_authentication(self, api_client):
        res = api_client.get("/api/v1/notifications/")
        assert res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_list_user_notifications(self, api_client, user, user_notifications):
        api_client.force_authenticate(user=user)
        res = api_client.get("/api/v1/notifications/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["count"] == 3
        assert len(data["results"]) == 3
        # Check enriched security symbol
        first_item = data["results"][0]
        assert first_item["title"] == "Price Alert 2"
        assert first_item["security_symbol"] == "NABIL"

    def test_filter_by_is_read_false(self, api_client, user, user_notifications):
        api_client.force_authenticate(user=user)
        res = api_client.get("/api/v1/notifications/?is_read=false")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["count"] == 2
        for item in data["results"]:
            assert item["is_read"] is False

    def test_filter_by_type(self, api_client, user, user_notifications):
        api_client.force_authenticate(user=user)
        res = api_client.get("/api/v1/notifications/?type=system")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "System Notice"

    def test_user_isolation(self, api_client, other_user, user_notifications):
        api_client.force_authenticate(user=other_user)
        res = api_client.get("/api/v1/notifications/")
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["count"] == 0


@pytest.mark.django_db
class TestNotificationUnreadCountAPI:
    def test_unread_count(self, api_client, user, user_notifications):
        api_client.force_authenticate(user=user)
        res = api_client.get("/api/v1/notifications/unread-count/")
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["unread_count"] == 2

    def test_unread_count_other_user(self, api_client, other_user, user_notifications):
        api_client.force_authenticate(user=other_user)
        res = api_client.get("/api/v1/notifications/unread-count/")
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["unread_count"] == 0


@pytest.mark.django_db
class TestNotificationActionsAPI:
    def test_mark_as_read(self, api_client, user, user_notifications):
        api_client.force_authenticate(user=user)
        target = user_notifications[0]
        assert target.is_read is False

        res = api_client.post(f"/api/v1/notifications/{target.id}/read/")
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["is_read"] is True

        target.refresh_from_db()
        assert target.is_read is True

    def test_cannot_mark_other_users_notification_as_read(self, api_client, other_user, user_notifications):
        api_client.force_authenticate(user=other_user)
        target = user_notifications[0]

        res = api_client.post(f"/api/v1/notifications/{target.id}/read/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_mark_all_as_read(self, api_client, user, user_notifications):
        api_client.force_authenticate(user=user)
        res = api_client.post("/api/v1/notifications/read-all/")
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["updated_count"] == 2

        # Check DB
        assert Notification.objects.filter(user=user, is_read=False).count() == 0

    def test_delete_notification(self, api_client, user, user_notifications):
        api_client.force_authenticate(user=user)
        target = user_notifications[0]

        res = api_client.delete(f"/api/v1/notifications/{target.id}/")
        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert not Notification.objects.filter(id=target.id).exists()

    def test_cannot_delete_other_users_notification(self, api_client, other_user, user_notifications):
        api_client.force_authenticate(user=other_user)
        target = user_notifications[0]

        res = api_client.delete(f"/api/v1/notifications/{target.id}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert Notification.objects.filter(id=target.id).exists()

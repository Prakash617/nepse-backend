"""Tests for notification models."""

import pytest
from django.contrib.auth import get_user_model

from apps.notifications.models import Notification

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.mark.django_db
class TestNotification:
    def test_create_notification(self, user):
        notif = Notification.objects.create(
            user=user,
            title="Test Alert",
            message="NABIL is above 1000",
        )
        assert notif.pk is not None
        assert notif.is_read is False
        assert notif.alert is None
        assert str(notif) == "testuser - Test Alert"

    def test_default_is_read_false(self, user):
        notif = Notification.objects.create(
            user=user, title="Test", message="Test message"
        )
        assert notif.is_read is False

    def test_ordering(self, user):
        n1 = Notification.objects.create(user=user, title="First", message="msg1")
        n2 = Notification.objects.create(user=user, title="Second", message="msg2")
        notifs = list(Notification.objects.filter(user=user))
        assert notifs[0] == n2
        assert notifs[1] == n1

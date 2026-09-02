"""Tests for notification WebSocket consumer."""

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from apps.notifications.consumers import NotificationConsumer

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(username="wsuser", password="testpass123")


@pytest.mark.anyio
@pytest.mark.django_db
async def test_websocket_unauthenticated_rejected():
    communicator = WebsocketCommunicator(NotificationConsumer.as_asgi(), "/ws/notifications/")
    communicator.scope["user"] = AnonymousUser()

    connected, close_code = await communicator.connect()
    assert connected is False
    assert close_code == 4401


@pytest.mark.anyio
@pytest.mark.django_db
async def test_websocket_authenticated_success(user):
    communicator = WebsocketCommunicator(NotificationConsumer.as_asgi(), "/ws/notifications/")
    communicator.scope["user"] = user

    connected, _ = await communicator.connect()
    assert connected is True

    # Receive connection ack
    response = await communicator.receive_json_from()
    assert response["type"] == "connection_established"
    assert response["username"] == "wsuser"

    # Test ping/pong
    await communicator.send_json_to({"type": "ping"})
    pong = await communicator.receive_json_from()
    assert pong["type"] == "pong"

    await communicator.disconnect()


@pytest.mark.anyio
@pytest.mark.django_db
async def test_websocket_receives_notification(user):
    from channels.layers import get_channel_layer

    communicator = WebsocketCommunicator(NotificationConsumer.as_asgi(), "/ws/notifications/")
    communicator.scope["user"] = user

    connected, _ = await communicator.connect()
    assert connected is True
    await communicator.receive_json_from()  # connection_established

    # Dispatch notification event through channel layer
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f"user_{user.id}",
        {
            "type": "notification.message",
            "notification": {
                "id": 1,
                "title": "NABIL Alert",
                "message": "Target 500 reached",
                "notification_type": "price_alert",
            },
        },
    )

    received = await communicator.receive_json_from()
    assert received["type"] == "notification"
    assert received["data"]["title"] == "NABIL Alert"
    assert received["data"]["notification_type"] == "price_alert"

    await communicator.disconnect()

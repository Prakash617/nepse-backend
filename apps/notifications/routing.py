"""WebSocket URL routing for notifications."""

from django.urls import re_path, path
from apps.notifications.consumers import NotificationConsumer

websocket_urlpatterns = [
    path("ws/notifications/", NotificationConsumer.as_asgi()),
    re_path(r"^ws/notifications/?$", NotificationConsumer.as_asgi()),
]

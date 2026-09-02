"""Notification, Web Push, and Telegram URL routing."""

from django.urls import path
from apps.notifications.views import (
    NotificationListView,
    NotificationDetailView,
    UnreadCountView,
    MarkReadView,
    MarkAllReadView,
    PushSubscribeView,
    PushUnsubscribeView,
    PushStatusView,
    PushTestView,
    TelegramStatusView,
    TelegramConnectView,
    TelegramDisconnectView,
    TelegramTestView,
    TelegramWebhookView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", UnreadCountView.as_view(), name="notification-unread-count"),
    path("read-all/", MarkAllReadView.as_view(), name="notification-read-all"),
    path("<int:pk>/", NotificationDetailView.as_view(), name="notification-detail"),
    path("<int:pk>/read/", MarkReadView.as_view(), name="notification-mark-read"),
    # Web Push endpoints
    path("push/subscribe/", PushSubscribeView.as_view(), name="push-subscribe"),
    path("push/unsubscribe/", PushUnsubscribeView.as_view(), name="push-unsubscribe"),
    path("push/status/", PushStatusView.as_view(), name="push-status"),
    path("push/test/", PushTestView.as_view(), name="push-test"),
    # Telegram Bot endpoints
    path("telegram/status/", TelegramStatusView.as_view(), name="telegram-status"),
    path("telegram/connect/", TelegramConnectView.as_view(), name="telegram-connect"),
    path("telegram/disconnect/", TelegramDisconnectView.as_view(), name="telegram-disconnect"),
    path("telegram/test/", TelegramTestView.as_view(), name="telegram-test"),
    path("telegram/webhook/", TelegramWebhookView.as_view(), name="telegram-webhook"),
]

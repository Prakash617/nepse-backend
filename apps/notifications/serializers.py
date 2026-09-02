"""Notification and Push Subscription serializers for REST API."""

from rest_framework import serializers
from apps.notifications.models import Notification, PushSubscription


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification objects."""

    security_symbol = serializers.CharField(source="security.symbol", read_only=True, default=None)
    security_name = serializers.CharField(source="security.company_name", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "data",
            "is_read",
            "security",
            "security_symbol",
            "security_name",
            "alert",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class UnreadCountSerializer(serializers.Serializer):
    """Serializer for unread notification count response."""

    unread_count = serializers.IntegerField()


class PushSubscriptionKeysSerializer(serializers.Serializer):
    """Keys sub-object in standard PushSubscription JSON."""

    p256dh = serializers.CharField(max_length=255, required=True)
    auth = serializers.CharField(max_length=255, required=True)


class PushSubscriptionCreateSerializer(serializers.Serializer):
    """Serializer for subscribing to Web Push notifications."""

    endpoint = serializers.CharField(required=True)
    keys = PushSubscriptionKeysSerializer(required=True)
    user_agent = serializers.CharField(required=False, default="", allow_blank=True)


class PushUnsubscribeSerializer(serializers.Serializer):
    """Serializer for unsubscribing from Web Push."""

    endpoint = serializers.CharField(required=True)


class PushStatusSerializer(serializers.Serializer):
    """Serializer for browser push status response."""

    is_subscribed = serializers.BooleanField()
    subscription_count = serializers.IntegerField()
    vapid_public_key = serializers.CharField()


class PushTestResponseSerializer(serializers.Serializer):
    """Serializer for test push trigger response."""

    success = serializers.BooleanField()
    sent = serializers.IntegerField()
    failed = serializers.IntegerField()
    deactivated = serializers.IntegerField()

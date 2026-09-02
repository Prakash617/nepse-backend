"""Notification, Web Push, and Telegram API views."""

import logging
from typing import Any

from django.conf import settings
from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification, PushSubscription, TelegramSubscription
from apps.notifications.serializers import (
    NotificationSerializer,
    UnreadCountSerializer,
    PushSubscriptionCreateSerializer,
    PushUnsubscribeSerializer,
    PushStatusSerializer,
    PushTestResponseSerializer,
)
from apps.notifications.services import NotificationService
from apps.notifications.webpush import PushNotificationService
from apps.notifications.telegram import (
    get_bot_username,
    generate_verification_code,
    send_test_telegram,
    process_telegram_update,
)

logger = logging.getLogger(__name__)


class NotificationListView(generics.ListAPIView):
    """List all notifications for the authenticated user."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List user notifications",
        description="Returns a paginated list of notifications belonging exclusively to the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="is_read",
                type=bool,
                description="Filter by read status (true/false)",
                required=False,
            ),
            OpenApiParameter(
                name="type",
                type=str,
                description="Filter by notification_type",
                required=False,
            ),
        ],
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Notification.objects.none()

        qs = (
            Notification.objects.filter(user=self.request.user)
            .select_related("security", "alert")
            .order_by("-created_at")
        )

        is_read_param = self.request.query_params.get("is_read")
        if is_read_param is not None:
            if is_read_param.lower() in ("true", "1"):
                qs = qs.filter(is_read=True)
            elif is_read_param.lower() in ("false", "0"):
                qs = qs.filter(is_read=False)

        type_param = self.request.query_params.get("type")
        if type_param:
            qs = qs.filter(notification_type=type_param)

        return qs


class NotificationDetailView(generics.RetrieveDestroyAPIView):
    """Retrieve or delete a single notification."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)


class UnreadCountView(APIView):
    """Get the unread notification count for the authenticated user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get unread notification count",
        responses={200: UnreadCountSerializer},
    )
    def get(self, request: Request) -> Response:
        count = NotificationService.get_unread_count(request.user)
        return Response({"unread_count": count})


class MarkAsReadView(APIView):
    """Mark a single notification as read."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark a notification as read",
        request=None,
        responses={200: NotificationSerializer},
    )
    def post(self, request: Request, pk: int) -> Response:
        notification = NotificationService.mark_as_read(user=request.user, notification_id=pk)
        if not notification:
            return Response(
                {"detail": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = NotificationSerializer(notification)
        return Response(serializer.data)


MarkReadView = MarkAsReadView


class MarkAllAsReadView(APIView):
    """Mark all unread notifications for the authenticated user as read."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark all notifications as read",
        request=None,
        responses={200: OpenApiResponse(description="Count of updated notifications")},
    )
    def post(self, request: Request) -> Response:
        count = NotificationService.mark_all_as_read(request.user)
        return Response({"updated_count": count})


MarkAllReadView = MarkAllAsReadView


class PushSubscribeView(APIView):
    """Register or update a Web Push subscription."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Subscribe browser/device to Web Push notifications",
        request=PushSubscriptionCreateSerializer,
        responses={
            201: OpenApiResponse(description="Subscription created or updated successfully"),
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = PushSubscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        keys = serializer.validated_data.get("keys", {})
        subscription, _ = PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=serializer.validated_data["endpoint"],
            defaults={
                "p256dh": keys.get("p256dh", ""),
                "auth": keys.get("auth", ""),
                "user_agent": serializer.validated_data.get("user_agent", ""),
                "is_active": True,
            },
        )

        logger.info(
            "Push subscription %s for user %s registered successfully.",
            subscription.id,
            request.user.username,
        )
        return Response(
            {
                "success": True,
                "is_subscribed": True,
                "subscription_id": subscription.id,
                "endpoint": subscription.endpoint,
            },
            status=status.HTTP_200_OK,
        )


class PushUnsubscribeView(APIView):
    """Deactivate an existing Web Push subscription."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Unsubscribe device from Web Push notifications",
        request=PushUnsubscribeSerializer,
        responses={200: OpenApiResponse(description="Unsubscribed successfully")},
    )
    def post(self, request: Request) -> Response:
        serializer = PushUnsubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        endpoint = serializer.validated_data["endpoint"]
        updated = PushSubscription.objects.filter(
            user=request.user,
            endpoint=endpoint,
        ).update(is_active=False)

        logger.info("Deactivated %d push subscription(s) for user %s", updated, request.user.username)
        return Response({"success": True, "updated_count": updated})


class PushStatusView(APIView):
    """Retrieve Web Push status and VAPID public key for the authenticated user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get browser Web Push status and VAPID public key",
        responses={200: PushStatusSerializer},
    )
    def get(self, request: Request) -> Response:
        count = PushSubscription.objects.filter(user=request.user, is_active=True).count()
        vapid_public_key = getattr(settings, "VAPID_PUBLIC_KEY", "")

        return Response(
            {
                "is_subscribed": count > 0,
                "subscription_count": count,
                "vapid_public_key": vapid_public_key,
            }
        )


class PushTestView(APIView):
    """Trigger a real test browser Web Push notification to the authenticated user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Send a test Web Push notification to active subscriptions",
        request=None,
        responses={200: PushTestResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        result = PushNotificationService.send_test_push(request.user)
        return Response(
            {
                "success": result["sent"] > 0 or result["failed"] == 0,
                "sent": result["sent"],
                "failed": result["failed"],
                "deactivated": result["deactivated"],
            }
        )


class TelegramStatusView(APIView):
    """Get Telegram Bot connection status for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        sub = TelegramSubscription.objects.filter(user=request.user, is_active=True).first()
        bot_username = get_bot_username()

        # If not connected, get or generate pending verification code
        pending_sub = None
        if not sub:
            pending_sub = TelegramSubscription.objects.filter(user=request.user).first()
            if not pending_sub or not pending_sub.verification_code:
                code = generate_verification_code()
                if pending_sub:
                    pending_sub.verification_code = code
                    pending_sub.save()
                else:
                    pending_sub = TelegramSubscription.objects.create(
                        user=request.user,
                        chat_id="",
                        verification_code=code,
                        is_active=False,
                    )

        code = (sub.verification_code if sub else (pending_sub.verification_code if pending_sub else ""))
        connect_url = f"https://t.me/{bot_username}?start={code}" if code else f"https://t.me/{bot_username}"

        return Response({
            "is_connected": sub is not None,
            "bot_username": bot_username,
            "username": sub.username if sub else "",
            "first_name": sub.first_name if sub else "",
            "chat_id": sub.chat_id if sub else "",
            "verification_code": code,
            "connect_url": connect_url,
        })


class TelegramConnectView(APIView):
    """Generate a fresh Telegram bot deep-link connection token."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        code = generate_verification_code()
        sub, _ = TelegramSubscription.objects.get_or_create(
            user=request.user,
            defaults={"chat_id": "", "is_active": False},
        )
        sub.verification_code = code
        sub.save()

        bot_username = get_bot_username()
        connect_url = f"https://t.me/{bot_username}?start={code}"

        return Response({
            "verification_code": code,
            "bot_username": bot_username,
            "connect_url": connect_url,
        })


class TelegramDisconnectView(APIView):
    """Disconnect and deactivate Telegram bot notifications for the user."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        updated = TelegramSubscription.objects.filter(user=request.user).update(is_active=False)
        return Response({"success": True, "updated_count": updated})


class TelegramTestView(APIView):
    """Send a real test notification to the user's Telegram."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        ok = send_test_telegram(request.user)
        return Response({"success": ok})


class TelegramWebhookView(APIView):
    """Public webhook receiver for Telegram Bot updates."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        data = request.data
        result = process_telegram_update(data)
        return Response(result)

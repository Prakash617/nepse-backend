"""Alert API views.

All endpoints require authentication. Users can only access, modify, and delete their own alerts.
"""

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alerts.models import Alert, AlertHistory
from apps.alerts.serializers import (
    AlertHistorySerializer,
    AlertListSerializer,
    AlertSerializer,
)


class AlertListCreateView(generics.ListCreateAPIView):
    """List user's alerts or create a new alert."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List user alerts",
        parameters=[
            OpenApiParameter(name="security__symbol", type=str, required=False, description="Filter by stock symbol"),
            OpenApiParameter(name="condition", type=str, required=False, description="Filter by condition type"),
            OpenApiParameter(name="status", type=str, required=False, description="Filter by status (active, triggered, paused)"),
            OpenApiParameter(name="is_active", type=bool, required=False, description="Filter by active status"),
        ],
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AlertSerializer
        return AlertListSerializer

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Alert.objects.none()

        qs = Alert.objects.filter(user=self.request.user).select_related("security")

        security = self.request.query_params.get("security__symbol")
        if security:
            qs = qs.filter(security__symbol__iexact=security)

        condition = self.request.query_params.get("condition")
        if condition:
            qs = qs.filter(condition=condition)

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        return qs

    def perform_create(self, serializer: AlertSerializer) -> None:
        serializer.save(user=self.request.user)


class AlertDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an alert."""

    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Alert.objects.none()
        return Alert.objects.filter(user=self.request.user).select_related("security")


class AlertPauseView(APIView):
    """Pause an active alert."""

    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Pause alert",
        request=None,
        responses={200: AlertSerializer, 404: OpenApiResponse(description="Alert not found")},
    )
    def post(self, request: Request, pk: int) -> Response:
        try:
            alert = Alert.objects.get(user=request.user, id=pk)
            alert.pause()
            return Response(AlertSerializer(alert).data)
        except Alert.DoesNotExist:
            return Response({"error": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)


class AlertResumeView(APIView):
    """Resume a paused alert."""

    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Resume alert",
        request=None,
        responses={200: AlertSerializer, 404: OpenApiResponse(description="Alert not found")},
    )
    def post(self, request: Request, pk: int) -> Response:
        try:
            alert = Alert.objects.get(user=request.user, id=pk)
            alert.resume()
            return Response(AlertSerializer(alert).data)
        except Alert.DoesNotExist:
            return Response({"error": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)


class AlertHistoryListView(generics.ListAPIView):
    """List historical triggers for user's alerts."""

    serializer_class = AlertHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return AlertHistory.objects.none()

        qs = AlertHistory.objects.filter(user=self.request.user).select_related("security", "alert")
        alert_id = self.kwargs.get("pk")
        if alert_id:
            qs = qs.filter(alert_id=alert_id)
        return qs

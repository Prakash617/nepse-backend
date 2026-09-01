"""Alert API views.

All endpoints require authentication. Users can only access their own alerts.
"""

from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.alerts.models import Alert
from apps.alerts.serializers import AlertListSerializer, AlertSerializer


class AlertListCreateView(generics.ListCreateAPIView):
    """List user's alerts or create a new one."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AlertSerializer
        return AlertListSerializer

    def get_queryset(self) -> QuerySet:
        qs = Alert.objects.filter(user=self.request.user).select_related("security")

        security = self.request.query_params.get("security__symbol")
        if security:
            qs = qs.filter(security__symbol__iexact=security)

        condition = self.request.query_params.get("condition")
        if condition:
            qs = qs.filter(condition=condition)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AlertDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an alert."""

    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        return Alert.objects.filter(user=self.request.user).select_related("security")

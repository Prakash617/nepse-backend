"""Alert serializers."""

from rest_framework import serializers

from apps.alerts.models import Alert


class AlertSerializer(serializers.ModelSerializer):
    security_symbol = serializers.CharField(source="security.symbol", read_only=True)
    condition_display = serializers.CharField(
        source="get_condition_display", read_only=True
    )

    class Meta:
        model = Alert
        fields = [
            "id",
            "security",
            "security_symbol",
            "condition",
            "condition_display",
            "threshold",
            "is_active",
            "last_triggered_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_triggered_at", "created_at", "updated_at"]


class AlertListSerializer(serializers.ModelSerializer):
    security_symbol = serializers.CharField(source="security.symbol", read_only=True)
    condition_display = serializers.CharField(
        source="get_condition_display", read_only=True
    )

    class Meta:
        model = Alert
        fields = [
            "id",
            "security_symbol",
            "condition",
            "condition_display",
            "threshold",
            "is_active",
            "last_triggered_at",
            "created_at",
        ]
        read_only_fields = ["id", "last_triggered_at", "created_at"]

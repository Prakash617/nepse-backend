"""Alert serializers."""

from rest_framework import serializers
from apps.alerts.models import Alert, AlertHistory


class AlertSerializer(serializers.ModelSerializer):
    """Full serializer for creating, retrieving, and updating Alerts."""

    security_symbol = serializers.CharField(source="security.symbol", read_only=True)
    security_name = serializers.CharField(source="security.company_name", read_only=True)
    security_input = serializers.CharField(write_only=True, required=False)
    condition_display = serializers.CharField(source="get_condition_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id",
            "security",
            "security_symbol",
            "security_name",
            "security_input",
            "condition",
            "condition_display",
            "threshold",
            "status",
            "status_display",
            "frequency",
            "frequency_display",
            "is_active",
            "notify_browser_push",
            "notify_in_app",
            "notify_telegram",
            "cooldown_minutes",
            "last_triggered_at",
            "triggered_price",
            "trigger_count",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status_display",
            "condition_display",
            "frequency_display",
            "last_triggered_at",
            "triggered_price",
            "trigger_count",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "security": {"required": False},
        }

    def validate(self, attrs: dict) -> dict:
        from apps.securities.models import Security

        security_input = attrs.pop("security_input", None)
        if security_input:
            val = str(security_input).strip()
            try:
                if val.isdigit():
                    sec = Security.objects.get(id=int(val))
                else:
                    sec = Security.objects.get(symbol__iexact=val)
                attrs["security"] = sec
            except Security.DoesNotExist:
                raise serializers.ValidationError({"security_input": f"Security '{security_input}' not found."})

        if not self.instance and "security" not in attrs:
            raise serializers.ValidationError({"security_input": "Security is required."})

        return attrs


class AlertListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing Alerts in tables and summaries."""

    security_symbol = serializers.CharField(source="security.symbol", read_only=True)
    security_name = serializers.CharField(source="security.company_name", read_only=True)
    condition_display = serializers.CharField(source="get_condition_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id",
            "security_symbol",
            "security_name",
            "condition",
            "condition_display",
            "threshold",
            "status",
            "status_display",
            "frequency",
            "is_active",
            "notify_browser_push",
            "notify_in_app",
            "cooldown_minutes",
            "last_triggered_at",
            "triggered_price",
            "trigger_count",
            "created_at",
        ]
        read_only_fields = ["id", "last_triggered_at", "created_at"]


class AlertHistorySerializer(serializers.ModelSerializer):
    """Serializer for Alert trigger audit logs."""

    security_symbol = serializers.CharField(source="security.symbol", read_only=True)

    class Meta:
        model = AlertHistory
        fields = [
            "id",
            "alert",
            "security",
            "security_symbol",
            "triggered_at",
            "triggered_value",
            "threshold",
            "condition",
            "message",
            "push_sent",
            "in_app_sent",
        ]
        read_only_fields = fields

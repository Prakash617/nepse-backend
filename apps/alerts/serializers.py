"""Alert serializers."""

from rest_framework import serializers

from apps.alerts.models import Alert


class AlertSerializer(serializers.ModelSerializer):
    security_symbol = serializers.CharField(source="security.symbol", read_only=True)
    security_input = serializers.CharField(write_only=True, required=False)
    condition_display = serializers.CharField(
        source="get_condition_display", read_only=True
    )

    class Meta:
        model = Alert
        fields = [
            "id",
            "security",
            "security_symbol",
            "security_input",
            "condition",
            "condition_display",
            "threshold",
            "is_active",
            "last_triggered_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_triggered_at", "created_at", "updated_at"]
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

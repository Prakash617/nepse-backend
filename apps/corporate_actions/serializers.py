"""Corporate Actions serializers."""

from rest_framework import serializers

from apps.corporate_actions.models import BonusShare, Dividend


class DividendSerializer(serializers.ModelSerializer):
    security_symbol = serializers.CharField(source="security.symbol", read_only=True)

    class Meta:
        model = Dividend
        fields = [
            "id",
            "security",
            "security_symbol",
            "fiscal_year",
            "dividend_per_share",
            "bonus_shares",
            "announcement_date",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class BonusShareSerializer(serializers.ModelSerializer):
    security_symbol = serializers.CharField(source="security.symbol", read_only=True)

    class Meta:
        model = BonusShare
        fields = [
            "id",
            "security",
            "security_symbol",
            "fiscal_year",
            "bonus_ratio",
            "announcement_date",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

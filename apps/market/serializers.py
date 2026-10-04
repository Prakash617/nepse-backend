"""Market API serializers."""

from rest_framework import serializers

from apps.market.models import MarketSnapshot
from apps.prices.models import DailyPrice


class MarketSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketSnapshot
        fields = [
            "trading_date",
            "total_volume",
            "total_turnover",
            "transactions",
            "open",
            "high",
            "low",
            "close",
            "previous_close",
            "point_change",
            "percentage_change",
        ]


class MarketSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketSnapshot
        fields = [
            "trading_date",
            "open",
            "high",
            "low",
            "close",
            "previous_close",
            "point_change",
            "percentage_change",
            "total_volume",
            "total_turnover",
            "transactions",
        ]


class MarketRankingSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="security.symbol", read_only=True)

    class Meta:
        model = DailyPrice
        fields = [
            "symbol",
            "close",
            "percentage_change",
            "volume",
            "turnover",
            "trading_date",
        ]


class MarketStatusSerializer(serializers.Serializer):
    is_open = serializers.BooleanField()
    status = serializers.CharField()
    as_of = serializers.CharField()
    trading_date = serializers.CharField(allow_null=True)
    source = serializers.CharField()
    message = serializers.CharField()
    detail = serializers.CharField()
    trading_hours = serializers.CharField()


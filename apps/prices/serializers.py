"""Price API serializers."""

from rest_framework import serializers

from apps.prices.models import DailyPrice, IntradayPrice


class DailyPriceSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="security.symbol", read_only=True)

    class Meta:
        model = DailyPrice
        fields = [
            "symbol",
            "trading_date",
            "open",
            "high",
            "low",
            "close",
            "ltp",
            "previous_close",
            "volume",
            "turnover",
            "percentage_change",
            "point_change",
        ]


class IntradayPriceSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="security.symbol", read_only=True)

    class Meta:
        model = IntradayPrice
        fields = [
            "symbol",
            "timestamp",
            "ltp",
            "volume",
            "turnover",
        ]

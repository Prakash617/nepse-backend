"""Index API serializers."""

from rest_framework import serializers

from apps.indices.models import IndexSnapshot, MarketIndex


class MarketIndexSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketIndex
        fields = [
            "nepse_id",
            "name",
        ]


class IndexSnapshotSerializer(serializers.ModelSerializer):
    index_name = serializers.CharField(source="index.name", read_only=True)

    class Meta:
        model = IndexSnapshot
        fields = [
            "index_name",
            "trading_date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "turnover",
            "point_change",
            "percentage_change",
        ]

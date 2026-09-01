"""Watchlist serializers."""

from rest_framework import serializers

from apps.watchlist.models import Watchlist, WatchlistItem


class WatchlistItemSerializer(serializers.ModelSerializer):
    security_symbol = serializers.CharField(source="security.symbol", read_only=True)
    security_company = serializers.CharField(source="security.company_name", read_only=True)

    class Meta:
        model = WatchlistItem
        fields = [
            "id",
            "security",
            "security_symbol",
            "security_company",
            "note",
            "added_at",
        ]
        read_only_fields = ["id", "added_at"]


class WatchlistSerializer(serializers.ModelSerializer):
    items = WatchlistItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = Watchlist
        fields = [
            "id",
            "name",
            "description",
            "items",
            "item_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class WatchlistListSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Watchlist
        fields = [
            "id",
            "name",
            "description",
            "item_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_item_count(self, obj: Watchlist) -> int:
        return obj.items.count()

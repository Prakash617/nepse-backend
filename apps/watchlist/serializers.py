"""Watchlist serializers."""

from rest_framework import serializers

from apps.watchlist.models import Watchlist, WatchlistItem


class WatchlistItemSerializer(serializers.ModelSerializer):
    security_symbol = serializers.CharField(source="security.symbol", read_only=True)
    security_company = serializers.CharField(source="security.company_name", read_only=True)
    security_input = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = WatchlistItem
        fields = [
            "id",
            "security",
            "security_symbol",
            "security_company",
            "security_input",
            "note",
            "added_at",
        ]
        read_only_fields = ["id", "added_at"]
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
    items = WatchlistItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()

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

    def get_item_count(self, obj: Watchlist) -> int:
        return obj.items.count()

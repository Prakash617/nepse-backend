"""Watchlist serializers."""

from rest_framework import serializers

from apps.watchlist.models import Watchlist, WatchlistItem


class WatchlistItemSerializer(serializers.ModelSerializer):
    security_symbol = serializers.CharField(source="security.symbol", read_only=True)
    security_company = serializers.CharField(source="security.company_name", read_only=True)
    security_sector = serializers.CharField(source="security.sector.name", default=None, read_only=True)
    security_input = serializers.CharField(write_only=True, required=False)

    ltp = serializers.SerializerMethodField()
    close = serializers.SerializerMethodField()
    previous_close = serializers.SerializerMethodField()
    point_change = serializers.SerializerMethodField()
    percentage_change = serializers.SerializerMethodField()
    volume = serializers.SerializerMethodField()
    turnover = serializers.SerializerMethodField()
    trading_date = serializers.SerializerMethodField()

    class Meta:
        model = WatchlistItem
        fields = [
            "id",
            "security",
            "security_symbol",
            "security_company",
            "security_sector",
            "security_input",
            "note",
            "added_at",
            "ltp",
            "close",
            "previous_close",
            "point_change",
            "percentage_change",
            "volume",
            "turnover",
            "trading_date",
        ]
        read_only_fields = ["id", "added_at"]
        extra_kwargs = {
            "security": {"required": False},
        }

    def _get_price(self, obj: WatchlistItem):
        if hasattr(obj, "_latest_price"):
            return obj._latest_price
        price_map = self.context.get("price_map")
        if price_map is not None:
            price = price_map.get(obj.security_id)
            obj._latest_price = price
            return price
        from apps.prices.models import DailyPrice
        price = DailyPrice.objects.filter(security_id=obj.security_id).order_by("-trading_date").first()
        obj._latest_price = price
        return price

    def get_ltp(self, obj: WatchlistItem) -> str | None:
        p = self._get_price(obj)
        if p and (p.ltp is not None or p.close is not None):
            return str(p.ltp or p.close)
        return None

    def get_close(self, obj: WatchlistItem) -> str | None:
        p = self._get_price(obj)
        return str(p.close) if p and p.close is not None else None

    def get_previous_close(self, obj: WatchlistItem) -> str | None:
        p = self._get_price(obj)
        return str(p.previous_close) if p and p.previous_close is not None else None

    def get_point_change(self, obj: WatchlistItem) -> str | None:
        p = self._get_price(obj)
        return str(p.point_change) if p and p.point_change is not None else None

    def get_percentage_change(self, obj: WatchlistItem) -> str | None:
        p = self._get_price(obj)
        return str(p.percentage_change) if p and p.percentage_change is not None else None

    def get_volume(self, obj: WatchlistItem) -> int | None:
        p = self._get_price(obj)
        return p.volume if p else None

    def get_turnover(self, obj: WatchlistItem) -> str | None:
        p = self._get_price(obj)
        return str(p.turnover) if p and p.turnover is not None else None

    def get_trading_date(self, obj: WatchlistItem) -> str | None:
        p = self._get_price(obj)
        return p.trading_date.isoformat() if p and p.trading_date else None

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

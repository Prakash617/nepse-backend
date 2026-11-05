"""Sector API serializers."""

from rest_framework import serializers

from apps.indices.models import IndexSnapshot
from apps.sectors.models import Sector

SECTOR_INDEX_MAPPING: dict[str, int] = {
    "Commercial Banks": 51,
    "Hotels And Tourism": 52,
    "Others": 53,
    "Hydro Power": 54,
    "Development Banks": 55,
    "Manufacturing And Processing": 56,
    "Non Life Insurance": 59,
    "Finance": 60,
    "Tradings": 61,
    "Microfinance": 64,
    "Life Insurance": 65,
    "Mutual Fund": 66,
    "Investment": 67,
}


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = [
            "nepse_id",
            "name",
            "display_name",
        ]


class SectorListSerializer(serializers.ModelSerializer):
    security_count = serializers.SerializerMethodField()
    equity_count = serializers.SerializerMethodField()
    index_id = serializers.SerializerMethodField()
    index_value = serializers.SerializerMethodField()
    index_change = serializers.SerializerMethodField()
    index_percent_change = serializers.SerializerMethodField()

    class Meta:
        model = Sector
        fields = [
            "nepse_id",
            "name",
            "display_name",
            "security_count",
            "equity_count",
            "index_id",
            "index_value",
            "index_change",
            "index_percent_change",
        ]

    def get_security_count(self, obj: Sector) -> int:
        if hasattr(obj, "_security_count"):
            return obj._security_count
        return obj.securities.count()

    def get_equity_count(self, obj: Sector) -> int:
        if hasattr(obj, "_equity_count"):
            return obj._equity_count
        return obj.securities.filter(security_type__iexact="Equity").count()

    def _get_snapshot(self, obj: Sector) -> IndexSnapshot | None:
        idx_id = SECTOR_INDEX_MAPPING.get(obj.name)
        if not idx_id:
            return None
        if not hasattr(self, "_snapshots_cache"):
            self._snapshots_cache = {}
            try:
                snapshots = (
                    IndexSnapshot.objects.filter(index__nepse_id__in=SECTOR_INDEX_MAPPING.values())
                    .order_by("index__nepse_id", "-trading_date")
                    .distinct("index__nepse_id")
                )
                for snap in snapshots:
                    self._snapshots_cache[snap.index.nepse_id] = snap
            except Exception:
                pass
        return self._snapshots_cache.get(idx_id)

    def get_index_id(self, obj: Sector) -> int | None:
        return SECTOR_INDEX_MAPPING.get(obj.name)

    def get_index_value(self, obj: Sector) -> float | None:
        snap = self._get_snapshot(obj)
        return float(snap.close) if snap and snap.close is not None else None

    def get_index_change(self, obj: Sector) -> float | None:
        snap = self._get_snapshot(obj)
        return float(snap.point_change) if snap and snap.point_change is not None else None

    def get_index_percent_change(self, obj: Sector) -> float | None:
        snap = self._get_snapshot(obj)
        return float(snap.percentage_change) if snap and snap.percentage_change is not None else None

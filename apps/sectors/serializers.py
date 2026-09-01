"""Sector API serializers."""

from rest_framework import serializers

from apps.sectors.models import Sector


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

    class Meta:
        model = Sector
        fields = [
            "nepse_id",
            "name",
            "display_name",
            "security_count",
        ]

    def get_security_count(self, obj: Sector) -> int:
        if hasattr(obj, "_security_count"):
            return obj._security_count
        return obj.securities.count()

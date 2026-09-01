"""Security API serializers."""

from rest_framework import serializers

from apps.securities.models import Security


class SecurityListSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source="sector.name", default=None, read_only=True)

    class Meta:
        model = Security
        fields = [
            "symbol",
            "company_name",
            "security_type",
            "sector_name",
            "listing_date",
            "paid_up_value",
            "face_value",
        ]


class SecurityDetailSerializer(serializers.ModelSerializer):
    sector = serializers.SerializerMethodField()

    class Meta:
        model = Security
        fields = [
            "symbol",
            "company_name",
            "security_type",
            "sector",
            "listing_date",
            "paid_up_value",
            "face_value",
        ]

    def get_sector(self, obj: Security) -> dict | None:
        if obj.sector is None:
            return None
        return {
            "name": obj.sector.name,
            "display_name": obj.sector.display_name,
        }

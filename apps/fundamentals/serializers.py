"""Fundamentals serializers."""

from rest_framework import serializers

from apps.fundamentals.models import CompanyProfile, FinancialReport


class CompanyProfileSerializer(serializers.ModelSerializer):
    security_symbol = serializers.CharField(source="security.symbol", read_only=True)

    class Meta:
        model = CompanyProfile
        fields = [
            "id",
            "security",
            "security_symbol",
            "nepse_id",
            "name",
            "address",
            "contact_number",
            "website",
            "email",
            "description",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class FinancialReportSerializer(serializers.ModelSerializer):
    security_symbol = serializers.CharField(source="security.symbol", read_only=True)

    class Meta:
        model = FinancialReport
        fields = [
            "id",
            "security",
            "security_symbol",
            "fiscal_year",
            "report_type",
            "file_url",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

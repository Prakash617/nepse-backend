from django.contrib import admin

from apps.fundamentals.models import CompanyProfile, FinancialReport


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = (
        "security",
        "nepse_id",
        "name",
        "contact_number",
        "website",
    )
    search_fields = ("security__symbol", "name")
    ordering = ("security__symbol",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("security",)


@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = (
        "security",
        "fiscal_year",
        "report_type",
        "file_url",
    )
    list_filter = ("fiscal_year", "report_type")
    search_fields = ("security__symbol",)
    ordering = ("-fiscal_year", "security__symbol")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("security",)

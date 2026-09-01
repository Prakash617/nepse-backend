"""Fundamentals models.

Company profile and financial report data from NEPSE upstream.
Fields derived from get_company_profile() and get_company_financials() responses.
"""

from django.db import models


class CompanyProfile(models.Model):
    """Company profile/contact information for a listed security.

    Synced from /api/nots/security/profile/{id}.
    """

    security = models.OneToOneField(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="company_profile",
        help_text="The security this profile belongs to.",
    )
    nepse_id = models.PositiveIntegerField(
        unique=True,
        help_text="Upstream NEPSE security/company ID.",
    )
    name = models.CharField(
        max_length=300,
        blank=True,
        default="",
        help_text="Company name.",
    )
    address = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Company registered address.",
    )
    contact_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Company phone/contact number.",
    )
    website = models.URLField(
        max_length=300,
        blank=True,
        default="",
        help_text="Company website URL.",
    )
    email = models.EmailField(
        max_length=200,
        blank=True,
        default="",
        help_text="Company contact email.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Company description or business summary.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Company Profile"
        verbose_name_plural = "Company Profiles"

    def __str__(self) -> str:
        return f"Profile: {self.name}"


class FinancialReport(models.Model):
    """Financial report metadata for a listed security.

    Synced from /api/nots/application/reports/{id}.
    Stores report metadata (fiscal year, type, file URL) — not actual financial data.
    """

    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="financial_reports",
        help_text="The security this report belongs to.",
    )
    fiscal_year = models.CharField(
        max_length=20,
        help_text="Fiscal year (e.g., '2081/82').",
    )
    report_type = models.CharField(
        max_length=100,
        help_text="Type of report (e.g., 'Annual Report').",
    )
    file_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="URL to the report file.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fiscal_year", "report_type"]
        unique_together = [("security", "fiscal_year", "report_type")]
        verbose_name = "Financial Report"
        verbose_name_plural = "Financial Reports"

    def __str__(self) -> str:
        return f"{self.security.symbol} - {self.fiscal_year} ({self.report_type})"

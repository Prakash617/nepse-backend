"""YONEPSE static-data client.

Fetches JSON datasets from the YONEPSE GitHub Pages site.
These are static files refreshed by GitHub Actions on a schedule.
No authentication required.
"""

import logging
from typing import Any

import httpx

from integrations.yonepse import endpoints
from integrations.yonepse.exceptions import (
    YonepseClientError,
)

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0


class YonepseClient:
    """Client for YONEPSE static JSON datasets hosted on GitHub Pages."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = (base_url or endpoints.BASE_URL).rstrip("/")
        self.timeout = timeout
        self._http = httpx.Client(timeout=timeout, follow_redirects=True)

    # -- low-level -----------------------------------------------------------

    def _get_json(self, url: str) -> Any:
        """Fetch a JSON resource. Raises YonepseClientError on failure."""
        try:
            resp = self._http.get(url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise YonepseClientError(
                f"HTTP {exc.response.status_code} fetching {url}"
            ) from exc
        except httpx.RequestError as exc:
            raise YonepseClientError(f"Request failed for {url}: {exc}") from exc

        try:
            return resp.json()
        except Exception as exc:
            raise YonepseClientError(
                f"Invalid JSON from {url}: {exc}"
            ) from exc

    # -- reference data ------------------------------------------------------

    def get_all_securities(self) -> list[dict[str, Any]]:
        """Return the full securities list from all_securities.json."""
        data = self._get_json(endpoints.ALL_SECURITIES)
        if not isinstance(data, list):
            raise YonepseClientError(
                f"Expected list for all_securities, got {type(data).__name__}"
            )
        return data

    def get_indices(self) -> list[dict[str, Any]]:
        """Return main NEPSE index definitions."""
        data = self._get_json(endpoints.INDICES)
        if not isinstance(data, list):
            raise YonepseClientError(
                f"Expected list for indices, got {type(data).__name__}"
            )
        return data

    def get_sector_indices(self) -> list[dict[str, Any]]:
        """Return sector-wise index definitions."""
        data = self._get_json(endpoints.SECTOR_INDICES)
        if not isinstance(data, list):
            raise YonepseClientError(
                f"Expected list for sector_indices, got {type(data).__name__}"
            )
        return data

    # -- market ---------------------------------------------------------------

    def get_market_history(self) -> list[dict[str, Any]]:
        """Return historical daily market summary records."""
        data = self._get_json(endpoints.MARKET_HISTORY)
        if not isinstance(data, list):
            raise YonepseClientError(
                f"Expected list for market history, got {type(data).__name__}"
            )
        return data

    # -- LTP history ----------------------------------------------------------

    def get_ltp_manifest(self) -> dict[str, Any]:
        """Return the LTP history manifest (available months, latest date)."""
        data = self._get_json(endpoints.LTP_MANIFEST)
        if not isinstance(data, dict):
            raise YonepseClientError(
                f"Expected dict for LTP manifest, got {type(data).__name__}"
            )
        return data

    def get_ltp_monthly(self, month: str) -> dict[str, Any]:
        """Return LTP data for a specific month (YYYY-MM format).

        Returns the monthly shard dict with columns, series, dates, etc.
        """
        url = endpoints.LTP_MONTHLY_TEMPLATE.format(month=month)
        data = self._get_json(url)
        if not isinstance(data, dict):
            raise YonepseClientError(
                f"Expected dict for LTP monthly {month}, got {type(data).__name__}"
            )
        return data

    def get_ltp_daily(self, date_str: str) -> dict[str, Any]:
        """Return LTP data for a specific day (YYYY-MM-DD format).

        Returns the daily shard dict with columns, series, times, etc.
        """
        url = endpoints.LTP_DAILY_TEMPLATE.format(date=date_str)
        data = self._get_json(url)
        if not isinstance(data, dict):
            raise YonepseClientError(
                f"Expected dict for LTP daily {date_str}, got {type(data).__name__}"
            )
        return data

    # -- company / fundamentals -----------------------------------------------

    def get_company_profiles(self) -> list[dict[str, Any]]:
        """Return company profile data."""
        data = self._get_json(endpoints.COMPANY_PROFILES)
        if not isinstance(data, list):
            raise YonepseClientError(
                f"Expected list for company profiles, got {type(data).__name__}"
            )
        return data

    def get_company_financials(self) -> list[dict[str, Any]]:
        """Return company financial data."""
        data = self._get_json(endpoints.COMPANY_FINANCIALS)
        if not isinstance(data, list):
            raise YonepseClientError(
                f"Expected list for company financials, got {type(data).__name__}"
            )
        return data

    # -- IPO ------------------------------------------------------------------

    def get_ipo_old(self) -> list[dict[str, Any]]:
        """Return historical IPO data."""
        data = self._get_json(endpoints.IPO_OLD)
        if not isinstance(data, list):
            raise YonepseClientError(
                f"Expected list for old IPOs, got {type(data).__name__}"
            )
        return data

    def get_ipo_upcoming(self) -> list[dict[str, Any]]:
        """Return upcoming IPO data."""
        data = self._get_json(endpoints.IPO_UPCOMING)
        if not isinstance(data, list):
            raise YonepseClientError(
                f"Expected list for upcoming IPOs, got {type(data).__name__}"
            )
        return data

    # -- dividends ------------------------------------------------------------

    def get_proposed_dividends(self) -> list[dict[str, Any]]:
        """Return proposed dividend data (latest year)."""
        data = self._get_json(endpoints.PROPOSED_DIVIDEND_LATEST)
        if not isinstance(data, list):
            raise YonepseClientError(
                f"Expected list for proposed dividends, got {type(data).__name__}"
            )
        return data

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> "YonepseClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

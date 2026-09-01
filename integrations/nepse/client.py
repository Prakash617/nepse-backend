"""NEPSE API client.

Provides NepseClient — the primary interface for the rest of the application.
Handles authentication, HTTP communication, and response parsing.
All upstream NEPSE-specific details are hidden behind this interface.
"""

import logging
from typing import Any

import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from integrations.nepse.auth import TokenParser, calculate_payload_id
from integrations.nepse.endpoints import (
    DEFAULT_BASE_URL,
    ENDPOINTS,
    INDEX_ID_MAX,
    INDEX_ID_MIN,
    TOP_STOCK_CATEGORIES,
)
from integrations.nepse.exceptions import (
    NepseAuthenticationError,
    NepseConnectionError,
    NepseInvalidResponseError,
    NepseRateLimitError,
    NepseServerError,
    NepseSSLError,
    NepseTimeoutError,
)
from integrations.nepse.parsers import (
    parse_brokers,
    parse_company_financials,
    parse_index_history,
    parse_indices,
    parse_market_status,
    parse_market_summary,
    parse_notices,
    parse_price_history,
    parse_sector_indices,
    parse_sectors,
    parse_sectorwise_summary,
    parse_securities_list,
    parse_securities_simple,
    parse_today_prices,
    parse_top_stocks,
)

logger = logging.getLogger(__name__)


class NepseClient:
    """Production NEPSE API client.

    Hides authentication, session management, payload generation,
    and response parsing from the rest of the application.

    Usage::

        client = NepseClient(base_url="https://www.nepalstock.com")
        status = client.get_market_status()
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        verify_ssl: bool = True,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: NEPSE API base URL. Defaults to https://www.nepalstock.com.
            verify_ssl: Whether to verify SSL certificates. Default True.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for server errors.
            backoff_factor: Backoff factor between retries.
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._token_parser = TokenParser()

        # Auth state
        self._access_token: str | None = None
        self._token_details: dict[str, Any] | None = None
        self._market_open_id: int | None = None

        # HTTP session
        self._session = requests.Session()
        if verify_ssl:
            self._session.verify = certifi.where()
        else:
            self._session.verify = False
            logger.warning("SSL certificate verification is disabled. This is not recommended.")

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        self._session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Referer": f"{self._base_url}/",
            }
        )

        logger.info("NepseClient initialized.")

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token. Fetches one if needed."""
        if self._access_token is not None:
            return

        endpoint = ENDPOINTS["authenticate_api"]
        url = self._base_url + endpoint["api"]

        try:
            response = self._session.request(endpoint["method"], url, timeout=self._timeout)
            response.raise_for_status()
            token_response = response.json()

            # Convert salt strings to ints (NEPSE returns them as strings)
            for i in range(1, 6):
                key = f"salt{i}"
                token_response[key] = int(token_response[key])

            self._access_token, _ = self._token_parser.parse_token_response(token_response)
            self._token_details = token_response
            logger.info("Successfully authenticated with NEPSE API.")
        except NepseSSLError:
            raise
        except requests.exceptions.SSLError as e:
            logger.error("SSL certificate verification failed during authentication.")
            raise NepseSSLError(
                "SSL certificate verification failed. This is likely due to the NEPSE "
                "server's incomplete certificate chain. Consider verify_ssl=False."
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise NepseConnectionError(f"Failed to connect to NEPSE API: {e}") from e
        except requests.exceptions.Timeout as e:
            raise NepseTimeoutError(f"Authentication request timed out: {e}") from e
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status == 401:
                raise NepseAuthenticationError("Authentication failed: invalid credentials.") from e
            raise NepseAuthenticationError(f"Authentication failed with status {status}: {e}") from e
        except requests.exceptions.RequestException as e:
            raise NepseAuthenticationError(f"Authentication request failed: {e}") from e

    def _get_market_open_id(self) -> int:
        """Fetch and cache the market-open ID needed for payload calculation."""
        if self._market_open_id is not None:
            return self._market_open_id

        self._ensure_authenticated()
        endpoint = ENDPOINTS["marketopen_api"]
        url = self._base_url + endpoint["api"]
        headers = {"Authorization": f"Salter {self._access_token}"}

        try:
            response = self._session.get(url, headers=headers, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
            self._market_open_id = data["id"]
            return self._market_open_id
        except (requests.exceptions.RequestException, KeyError) as e:
            raise NepseConnectionError(f"Failed to fetch market-open ID: {e}") from e

    def _get_payload_id(self, payload_type: str = "default") -> int:
        """Calculate the payload ID for POST requests."""
        self._ensure_authenticated()
        market_open_id = self._get_market_open_id()
        return calculate_payload_id(
            market_open_id=market_open_id,
            token_details=self._token_details or {},
            payload_type=payload_type,
        )

    def _auth_headers(self) -> dict[str, str]:
        """Return authorization headers."""
        self._ensure_authenticated()
        return {"Authorization": f"Salter {self._access_token}"}

    def _reset_auth(self) -> None:
        """Reset auth state (used after 401 or token invalidation)."""
        self._access_token = None
        self._token_details = None
        self._market_open_id = None

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        payload_type: str | None = None,
    ) -> Any:
        """Make an authenticated HTTP request.

        Args:
            method: HTTP method ("GET" or "POST").
            path: API path (appended to base_url).
            params: Query string parameters.
            payload: JSON body for POST requests.
            payload_type: If provided, auto-generate payload ID of this type.

        Returns:
            Parsed JSON response.
        """
        url = self._base_url + path
        headers = self._auth_headers()

        if method == "GET":
            logger.debug("GET %s params=%s", path, params)
            try:
                resp = self._session.get(url, params=params, headers=headers, timeout=self._timeout)
            except requests.exceptions.ConnectionError as e:
                raise NepseConnectionError(f"Connection failed: {e}") from e
            except requests.exceptions.Timeout as e:
                raise NepseTimeoutError(f"Request timed out: {e}") from e
            except requests.exceptions.HTTPError as e:
                resp = e.response
                if resp is not None:
                    self._handle_error_response(resp)
                raise NepseConnectionError(f"HTTP error: {e}") from e
        elif method == "POST":
            if payload is None and payload_type is not None:
                payload = {"id": self._get_payload_id(payload_type)}
            logger.debug("POST %s payload_type=%s", path, payload_type)
            try:
                resp = self._session.post(
                    url, json=payload, params=params, headers=headers, timeout=self._timeout
                )
            except requests.exceptions.ConnectionError as e:
                raise NepseConnectionError(f"Connection failed: {e}") from e
            except requests.exceptions.Timeout as e:
                raise NepseTimeoutError(f"Request timed out: {e}") from e
            except requests.exceptions.HTTPError as e:
                resp = e.response
                if resp is not None:
                    self._handle_error_response(resp)
                raise NepseConnectionError(f"HTTP error: {e}") from e
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        self._handle_error_response(resp)

        try:
            return resp.json()
        except ValueError as e:
            raise NepseInvalidResponseError(f"Invalid JSON response: {e}") from e

    def _handle_error_response(self, resp: requests.Response) -> None:
        """Check response status and raise appropriate exceptions."""
        if resp.status_code == 401:
            self._reset_auth()
            raise NepseAuthenticationError("Authentication failed (HTTP 401). Token may have expired.")
        if resp.status_code == 403:
            raise NepseAuthenticationError("Access forbidden (HTTP 403).")
        if resp.status_code == 429:
            raise NepseRateLimitError("Rate limit exceeded (HTTP 429).")
        if resp.status_code >= 500:
            raise NepseServerError(f"NEPSE server error: HTTP {resp.status_code}.")

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        payload_type: str | None = None,
    ) -> Any:
        return self._request("POST", path, params=params, payload=payload, payload_type=payload_type)

    # ------------------------------------------------------------------
    # Public API methods — Market data
    # ------------------------------------------------------------------

    def get_market_status(self) -> dict[str, Any]:
        """Check if the NEPSE market is currently open.

        Returns:
            Normalized dict with 'id' (int) and 'is_open' (bool).
        """
        data = self._get(ENDPOINTS["marketopen_api"]["api"])
        return parse_market_status(data)

    def get_market_summary(self) -> dict[str, Any]:
        """Get today's market summary.

        Returns:
            Normalized market summary dict.
        """
        data = self._get(ENDPOINTS["market_summary_api"]["api"])
        return parse_market_summary(data)

    def get_today_prices(self, business_date: str | None = None) -> list[dict[str, Any]]:
        """Get today's trading prices for all securities.

        Args:
            business_date: Optional date in "YYYY-MM-DD" format.

        Returns:
            List of normalized price dicts.
        """
        params: dict[str, Any] = {"page": "0", "size": "500"}
        if business_date is not None:
            params["businessDate"] = business_date
        data = self._post(
            ENDPOINTS["today_price_api"]["api"],
            params=params,
            payload_type="default",
        )
        content = data.get("content", []) if isinstance(data, dict) else []
        return parse_today_prices(content)

    def get_live_trades(self) -> list[dict[str, Any]]:
        """Get live market trades (returns empty list if market is closed).

        Returns:
            List of normalized live trade dicts.
        """
        status = self.get_market_status()
        if not status["is_open"]:
            logger.info("Market is closed; returning empty live trades.")
            return []

        data = self._post(
            ENDPOINTS["stock_live_api"]["api"],
            payload_type="stock-live",
        )
        items = data if isinstance(data, list) else []
        return parse_today_prices(items)

    # ------------------------------------------------------------------
    # Public API methods — Securities
    # ------------------------------------------------------------------

    def get_securities(self) -> list[dict[str, Any]]:
        """Get full list of all listed securities.

        Returns:
            List of normalized security dicts.
        """
        data = self._get(ENDPOINTS["security_api"]["api"])
        return parse_securities_list(data)

    def get_securities_simple(self) -> list[dict[str, Any]]:
        """Get simplified list of all securities.

        Returns:
            List of simplified security dicts.
        """
        data = self._get(ENDPOINTS["securities_list_api"]["api"])
        return parse_securities_simple(data)

    def get_ticker_info(self, ticker: str) -> dict[str, Any]:
        """Get detailed info for a single ticker.

        Args:
            ticker: Stock symbol (e.g., "NABIL").

        Returns:
            Raw ticker info dict from the API.

        Raises:
            ValueError: If ticker is empty.
        """
        if not ticker:
            raise ValueError("Ticker is required.")
        ticker_upper = ticker.upper()

        # Build symbol->id map
        securities = self.get_securities()
        security_map = {s["symbol"]: s["id"] for s in securities if s.get("symbol") and s.get("id")}
        security_id = security_map.get(ticker_upper)
        if security_id is None:
            raise NepseInvalidResponseError(f"Ticker '{ticker_upper}' not found in NEPSE securities.")

        path = f"{ENDPOINTS['ticker_info_api']['api']}/{security_id}"
        return self._post(path, payload_type="stock-live")

    # ------------------------------------------------------------------
    # Public API methods — Indices
    # ------------------------------------------------------------------

    def get_indices(self) -> list[dict[str, Any]]:
        """Get NEPSE index and sub-indices.

        Returns:
            List of normalized index dicts.
        """
        data = self._get(ENDPOINTS["nepse_index_api"]["api"])
        return parse_indices(data)

    def get_sector_indices(self) -> list[dict[str, Any]]:
        """Get sector indices.

        Returns:
            List of normalized sector index dicts.
        """
        data = self._get(ENDPOINTS["sector_index_api"]["api"])
        return parse_sector_indices(data)

    def get_index_history(
        self, index_id: int, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Get historical data for an index.

        Args:
            index_id: Index ID (valid range: 51-67).
            start_date: Start date in "YYYY-MM-DD" format.
            end_date: End date in "YYYY-MM-DD" format.

        Returns:
            List of normalized index history dicts.
        """
        if not (INDEX_ID_MIN <= index_id <= INDEX_ID_MAX):
            raise ValueError(
                f"Index ID {index_id} is not valid. Must be between {INDEX_ID_MIN} and {INDEX_ID_MAX}."
            )
        path = f"{ENDPOINTS['head_indices_api']['api']}/{index_id}"
        params = {"startDate": start_date, "endDate": end_date}
        data = self._get(path, params=params)
        return parse_index_history(data)

    def get_live_index(self, index_id: int = 58) -> list[dict[str, Any]]:
        """Get live data for an index.

        Args:
            index_id: Index ID (valid range: 51-67). Default 58 (NEPSE Index).

        Returns:
            List of live index data points.
        """
        if not (INDEX_ID_MIN <= index_id <= INDEX_ID_MAX):
            raise ValueError(
                f"Index ID {index_id} is not valid. Must be between {INDEX_ID_MIN} and {INDEX_ID_MAX}."
            )
        path = f"{ENDPOINTS['indices_live_api']['api']}/{index_id}"
        data = self._post(path, payload_type="sector-live")
        return data if isinstance(data, list) else []

    # ------------------------------------------------------------------
    # Public API methods — Sectors
    # ------------------------------------------------------------------

    def get_sectors(self) -> list[dict[str, Any]]:
        """Get all sectors.

        Returns:
            List of normalized sector dicts.
        """
        data = self._get(ENDPOINTS["sector_api"]["api"])
        return parse_sectors(data)

    def get_sectorwise_summary(self) -> list[dict[str, Any]]:
        """Get sector-wise market summary.

        Returns:
            List of normalized sector summary dicts.
        """
        data = self._get(ENDPOINTS["sectorwise_summary_api"]["api"])
        return parse_sectorwise_summary(data)

    # ------------------------------------------------------------------
    # Public API methods — Top stocks
    # ------------------------------------------------------------------

    def get_top_stocks(
        self, category: str, show_all: bool = False
    ) -> list[dict[str, Any]]:
        """Get top stocks by category.

        Args:
            category: One of 'top_gainer', 'top_loser', 'top_turnover',
                      'top_trade', 'top_transaction'.
            show_all: If True, return all results instead of top 10.

        Returns:
            List of normalized top-stock dicts.
        """
        if category not in TOP_STOCK_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. Must be one of: {TOP_STOCK_CATEGORIES}"
            )
        params = {"all": str(show_all).lower()}
        data = self._get(ENDPOINTS[category]["api"], params=params)
        return parse_top_stocks(data)

    # ------------------------------------------------------------------
    # Public API methods — Price history
    # ------------------------------------------------------------------

    def get_price_history(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        page: int = 0,
        size: int = 500,
    ) -> list[dict[str, Any]]:
        """Get historical price data for a ticker.

        Args:
            ticker: Stock symbol.
            start_date: Start date in "YYYY-MM-DD" format.
            end_date: End date in "YYYY-MM-DD" format.
            page: Page number (0-indexed).
            size: Records per page.

        Returns:
            List of normalized price history dicts.
        """
        ticker_upper = ticker.upper()
        securities = self.get_securities()
        security_map = {s["symbol"]: s["id"] for s in securities if s.get("symbol") and s.get("id")}
        security_id = security_map.get(ticker_upper)
        if security_id is None:
            raise NepseInvalidResponseError(f"Ticker '{ticker_upper}' not found in NEPSE securities.")

        path = f"{ENDPOINTS['ticker_price_api']['api']}/{security_id}"
        params = {
            "startDate": start_date,
            "endDate": end_date,
            "page": str(page),
            "size": str(size),
        }
        data = self._get(path, params=params)
        return parse_price_history(data)

    # ------------------------------------------------------------------
    # Public API methods — Company / Fundamentals
    # ------------------------------------------------------------------

    def get_company_financials(self, company_id: int) -> list[dict[str, Any]]:
        """Get financial reports for a company.

        Args:
            company_id: The security/company ID.

        Returns:
            List of normalized financial report dicts.
        """
        path = f"{ENDPOINTS['company_financials_api']['api']}/{company_id}"
        data = self._get(path)
        return parse_company_financials(data)

    def get_company_profile(self, company_id: int) -> dict[str, Any]:
        """Get company profile/contact data.

        Args:
            company_id: The security/company ID.

        Returns:
            Raw profile dict from the API.
        """
        path = f"{ENDPOINTS['ticker_contact_api']['api']}/{company_id}"
        return self._get(path)

    # ------------------------------------------------------------------
    # Public API methods — Brokers
    # ------------------------------------------------------------------

    def get_brokers(self) -> list[dict[str, Any]]:
        """Get list of all registered brokers.

        Returns:
            List of normalized broker dicts.
        """
        params = {"page": "0", "size": "500"}
        payload = {
            "memberName": "",
            "contactPerson": "",
            "contactNumber": "",
            "memberCode": "",
            "provinceId": 0,
            "districtId": 0,
            "municipalityId": 0,
        }
        data = self._post(ENDPOINTS["broker_api"]["api"], params=params, payload=payload)
        content = data.get("content", []) if isinstance(data, dict) else []
        return parse_brokers(content)

    # ------------------------------------------------------------------
    # Public API methods — News / Notices
    # ------------------------------------------------------------------

    def get_notices(self) -> list[dict[str, Any]]:
        """Get NEPSE notices.

        Returns:
            List of normalized notice dicts.
        """
        data = self._get(ENDPOINTS["notice_api"]["api"])
        return parse_notices(data)

    def get_disclosures(self) -> dict[str, Any]:
        """Get company disclosures/announcements.

        Returns:
            Raw disclosure dict from the API.
        """
        return self._get(ENDPOINTS["disclosure"]["api"])

    # ------------------------------------------------------------------
    # Public API methods — Additional data
    # ------------------------------------------------------------------

    def get_market_cap(self) -> list[dict[str, Any]]:
        """Get market capitalization data.

        Returns:
            Raw market cap data from the API.
        """
        return self._get(ENDPOINTS["marketcap_api"]["api"])

    def get_supply_demand(self, show_all: bool = False) -> list[dict[str, Any]]:
        """Get supply and demand data.

        Args:
            show_all: If True, return all data instead of top results.

        Returns:
            Raw supply/demand data.
        """
        params = {"all": str(show_all).lower()}
        return self._get(ENDPOINTS["supply_demand_api"]["api"], params=params)

    def get_trading_average(
        self, n_days: int = 120, business_date: str | None = None
    ) -> list[dict[str, Any]]:
        """Get trading average data.

        Args:
            n_days: Number of days (1-180).
            business_date: Optional end date in "YYYY-MM-DD" format.

        Returns:
            Raw trading average data.
        """
        if not (1 <= n_days <= 180):
            raise ValueError("n_days must be between 1 and 180.")
        params: dict[str, Any] = {"nDays": str(n_days), "page": "0", "size": "500"}
        if business_date is not None:
            params["businessDate"] = business_date
        return self._get(ENDPOINTS["trading_average_api"]["api"], params=params)

    def get_market_summary_history(self) -> list[dict[str, Any]]:
        """Get market summary history.

        Returns:
            Raw market summary history data.
        """
        return self._get(ENDPOINTS["market_summary_history_api"]["api"])

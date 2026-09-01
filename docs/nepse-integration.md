# NEPSE Integration Reference

Implementation details for the NEPSE integration layer.

Upstream reference: https://github.com/Shubhamnpk/yonepse

## Architecture

```
integrations/nepse/
├── __init__.py         # Public API: NepseClient + exceptions
├── auth.py             # WASM token parsing + payload ID calculation
├── client.py           # NepseClient — primary interface
├── endpoints.py        # All verified endpoint definitions
├── exceptions.py       # Custom exception hierarchy
├── nepse.wasm          # WASM binary for token decoding (from YONEPSE)
└── parsers.py          # Response normalization
```

**Data flow:**

```
NepseClient → authentication → HTTP request → upstream response → parser → normalized dict
```

## Authentication

### Flow

1. `GET /api/authenticate/prove` → returns `{accessToken, refreshToken, salt1..salt5}`
2. WASM module (`nepse.wasm`) decodes tokens from salts via `TokenParser`
3. `Authorization: Salter {parsed_access_token}` header on all subsequent requests
4. POST endpoints require a calculated payload ID in JSON body `{id: <payload_id>}`

### Token Parsing

The NEPSE API obfuscates tokens using salts. The WASM module exports 5 functions (`cdx`, `rdx`, `bdx`, `ndx`, `mdx`) that compute character indices used to strip characters from the raw tokens.

### Payload ID Calculation

POST endpoints require a calculated payload ID. The calculation:

1. Look up `_PAYLOAD_TABLE[market_open_id]` (100-entry lookup table)
2. Add `market_open_id + 2 * today` (today = `datetime.now().day`)
3. For `stock-live`: return base payload
4. For `sector-live` or default: apply salt-based adjustment using token salts

The `market_open_id` is fetched from `GET /api/nots/nepse-data/market-open` and cached.

**Important:** Payload IDs are date-sensitive. The same request on different days produces different payloads.

## Endpoints

All 32 endpoints verified from YONEPSE `official_api/endpoints.py`:

### Market Data
| Name | Endpoint | Method | Notes |
|---|---|---|---|
| Market Open | `/api/nots/nepse-data/market-open` | GET | Returns `{id, isOpen}` |
| Today Price | `/api/nots/nepse-data/today-price` | POST | Paginated: `page`, `size`, `businessDate` |
| Market Summary | `/api/nots/market-summary` | GET | |
| Market Summary History | `/api/nots/market-summary-history` | GET | |
| Market Cap | `/api/nots/nepse-data/marcapbydate` | GET | |
| Trading Average | `/api/nots/nepse-data/trading-average` | GET | Params: `nDays`, `businessDate` |
| Supply/Demand | `/api/nots/nepse-data/supplydemand` | GET | |
| Live Trades | `/api/nots/lives-market` | POST | Requires payload |

### Securities
| Name | Endpoint | Method | Notes |
|---|---|---|---|
| Company List | `/api/nots/company/list` | GET | Full security list |
| Securities List | `/api/nots/securities` | GET | Simplified list |
| Ticker Info | `/api/nots/security/{id}` | POST | Requires payload |
| Ticker Contact | `/api/nots/security/profile/{id}` | GET | |
| Ticker Price History | `/api/nots/market/security/price/{id}` | GET | Paginated |
| Daily Trade Stat | `/api/nots/securityDailyTradeStat/{id}` | GET | |

### Indices
| Name | Endpoint | Method | Notes |
|---|---|---|---|
| NEPSE Index | `/api/nots/nepse-index` | GET | All indices |
| Sector Indices | `/api/nots/index` | GET | |
| Index History | `/api/nots/index/history/{index_id}` | GET | Params: `startDate`, `endDate` |
| Live Indices | `/api/nots/graph/index/{index_id}` | POST | Requires payload |

### Sectors
| Name | Endpoint | Method | Notes |
|---|---|---|---|
| Sectors | `/api/nots/sector` | GET | |
| Sectorwise Summary | `/api/nots/sectorwise` | GET | |

### Top Stocks
| Name | Endpoint | Method | Notes |
|---|---|---|---|
| Top Gainer | `/api/nots/top-ten/top-gainer` | GET | |
| Top Loser | `/api/nots/top-ten/top-loser` | GET | |
| Top Turnover | `/api/nots/top-ten/turnover` | GET | |
| Top Trade | `/api/nots/top-ten/trade` | GET | |
| Top Transaction | `/api/nots/top-ten/transaction` | GET | |
| Top Trade Quantity | `/api/nots/top-ten/trade-qty` | GET | |

### Company / Brokers / News
| Name | Endpoint | Method | Notes |
|---|---|---|---|
| Company Financials | `/api/nots/application/reports/{id}` | GET | |
| Broker List | `/api/nots/member` | POST | Paginated |
| Disclosures | `/api/nots/news/companies/disclosure` | GET | |
| Notices | `/api/web/notice/` | GET | |
| Info Officers | `/api/web/info-officer` | GET | |

## NepseClient Methods

| Method | Endpoint | Returns |
|---|---|---|
| `get_market_status()` | marketopen_api | `{id, is_open}` |
| `get_market_summary()` | market_summary_api | summary dict |
| `get_today_prices(business_date?)` | today_price_api | list of price dicts |
| `get_live_trades()` | stock_live_api | list of trade dicts |
| `get_securities()` | security_api | list of security dicts |
| `get_securities_simple()` | securities_list_api | list of simple dicts |
| `get_ticker_info(ticker)` | ticker_info_api | ticker dict |
| `get_indices()` | nepse_index_api | list of index dicts |
| `get_sector_indices()` | sector_index_api | list of sector index dicts |
| `get_index_history(id, start, end)` | head_indices_api | list of history dicts |
| `get_live_index(id?)` | indices_live_api | list of live data |
| `get_sectors()` | sector_api | list of sector dicts |
| `get_sectorwise_summary()` | sectorwise_summary_api | list of summary dicts |
| `get_top_stocks(category, show_all?)` | top_* | list of top stock dicts |
| `get_price_history(ticker, start, end)` | ticker_price_api | list of price dicts |
| `get_company_financials(id)` | company_financials_api | list of report dicts |
| `get_company_profile(id)` | ticker_contact_api | profile dict |
| `get_brokers()` | broker_api | list of broker dicts |
| `get_notices()` | notice_api | list of notice dicts |
| `get_disclosures()` | disclosure | raw dict |
| `get_market_cap()` | marketcap_api | raw data |
| `get_supply_demand(show_all?)` | supply_demand_api | raw data |
| `get_trading_average(n_days, date?)` | trading_average_api | raw data |
| `get_market_summary_history()` | market_summary_history_api | raw data |

## Error Handling

| Exception | When |
|---|---|
| `NepseError` | Base exception |
| `NepseAuthenticationError` | HTTP 401, 403, or auth failure |
| `NepseSSLError` | SSL certificate verification fails |
| `NepseRateLimitError` | HTTP 429 |
| `NepseConnectionError` | Connection refused/failed |
| `NepseTimeoutError` | Request timeout |
| `NepseInvalidResponseError` | Invalid JSON or missing required fields |
| `NepseServerError` | HTTP 5xx |

On HTTP 401, the client automatically resets its auth state and re-authenticates on the next request.

## Retry Behavior

- 3 retries by default (configurable via `max_retries`)
- Retries on HTTP 500, 502, 503, 504
- Backoff factor of 1.0 (configurable)
- No retries on auth errors (401, 403)

## Configuration

Environment variables (in `.env` or settings):

| Variable | Default | Description |
|---|---|---|
| `NEPSE_API_BASE_URL` | `https://www.nepalstock.com` | API base URL |
| `NEPSE_SSL_VERIFY` | `true` | Verify SSL certificates |
| `NEPSE_TIMEOUT` | `30` | Request timeout (seconds) |
| `NEPSE_MAX_RETRIES` | `3` | Max retries for server errors |
| `NEPSE_BACKOFF_FACTOR` | `1.0` | Backoff factor between retries |

## SSL Considerations

NEPSE has known certificate chain issues. The client uses `certifi` for SSL by default. If SSL verification fails:

1. First, ensure `certifi` is up to date
2. If the issue persists, set `NEPSE_SSL_VERIFY=false` (not recommended for production)
3. The client logs a warning when SSL verification is disabled

**Never disable SSL verification in production without understanding the security implications.**

## Known Upstream Limitations

1. **No token refresh:** The upstream implementation caches the token in memory and never refreshes. Our client resets auth on 401 and re-authenticates.
2. **Hardcoded root URL:** The upstream hardcodes `https://www.nepalstock.com`. Our client makes it configurable.
3. **Date-sensitive payloads:** POST payload IDs depend on `datetime.now().day`, making them non-deterministic across days.
4. **No rate limiting documentation:** Upstream does not document rate limits. We handle HTTP 429 gracefully.
5. **WASM dependency:** Token parsing requires the `wasmtime` Python package and `nepse.wasm` binary.

## Testing

All tests mock the upstream NEPSE API — no real calls are made.

```bash
# Run all NEPSE integration tests
uv run pytest tests/test_nepse_auth.py tests/test_nepse_parsers.py tests/test_nepse_client.py -v

# Run all tests
uv run pytest
```

### Test coverage

- Authentication (WASM token parsing, payload ID calculation)
- All NepseClient methods (mocked HTTP)
- All parsers (market status, securities, prices, indices, sectors, etc.)
- Error handling (401, 403, 429, 5xx, timeouts, connection errors, invalid JSON)
- Token caching and reset
- Input validation (invalid categories, invalid index IDs, missing tickers)

## Manual Verification

```python
# In Django shell:
uv run python manage.py shell

from integrations.nepse import NepseClient

client = NepseClient()

# Check market status
client.get_market_status()

# Get securities
securities = client.get_securities()
len(securities)
```

**Important:** Use minimal manual requests. Do not hammer the upstream API.

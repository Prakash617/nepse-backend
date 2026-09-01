# NEPSE Platform API Documentation

Base URL: `/api/v1/`

## Authentication

Market-data endpoints are publicly readable. No authentication required for read-only access.

## Pagination

List endpoints use page-number pagination with default page size of 20.

```json
{
    "count": 100,
    "next": "http://...?page=2",
    "previous": null,
    "results": [...]
}
```

## Securities

### List Securities

```
GET /api/v1/securities/
```

**Query Parameters:**
- `search` — Filter by symbol (case-insensitive contains)
- `sector` — Filter by sector name (case-insensitive contains)
- `security_type` — Filter by security type (exact match)
- `ordering` — Sort by field (default: `symbol`). Allowed: `symbol`, `-symbol`, `company_name`, `-company_name`, `security_type`, `-security_type`, `listing_date`, `-listing_date`

**Response:**
```json
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "symbol": "NABIL",
            "company_name": "Nabil Bank Limited",
            "security_type": "Ordinary Share",
            "sector_name": "Commercial Banks",
            "listing_date": "2002-01-01",
            "paid_up_value": "100.00",
            "face_value": "100.00"
        }
    ]
}
```

### Get Security Detail

```
GET /api/v1/securities/{symbol}/
```

Lookup is case-insensitive.

**Response:**
```json
{
    "symbol": "NABIL",
    "company_name": "Nabil Bank Limited",
    "security_type": "Ordinary Share",
    "sector": {
        "name": "Commercial Banks",
        "display_name": "Commercial Banks Sector"
    },
    "listing_date": "2002-01-01",
    "paid_up_value": "100.00",
    "face_value": "100.00"
}
```

### Get Price History

```
GET /api/v1/securities/{symbol}/history/
```

**Query Parameters:**
- `start` — Start date (YYYY-MM-DD)
- `end` — End date (YYYY-MM-DD)

**Response:**
```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "symbol": "NABIL",
            "trading_date": "2026-01-15",
            "open": "100.00",
            "high": "105.00",
            "low": "99.00",
            "close": "103.00",
            "ltp": "103.00",
            "previous_close": "100.00",
            "volume": 1000000,
            "turnover": "103000000.00",
            "percentage_change": "3.0000",
            "point_change": "3.0000"
        }
    ]
}
```

### Get Intraday Data

```
GET /api/v1/securities/{symbol}/intraday/
```

**Response:**
```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "symbol": "NABIL",
            "timestamp": "2026-01-15T10:30:00Z",
            "ltp": "103.00",
            "volume": 100,
            "turnover": "10300.00"
        }
    ]
}
```

## Sectors

### List Sectors

```
GET /api/v1/sectors/
```

Returns all sectors with security counts. No pagination.

**Response:**
```json
[
    {
        "nepse_id": 1,
        "name": "Commercial Banks",
        "display_name": "Commercial Banks Sector",
        "security_count": 15
    }
]
```

## Indices

### List Indices

```
GET /api/v1/indices/
```

Returns all market indices. No pagination.

**Response:**
```json
[
    {
        "nepse_id": 58,
        "name": "NEPSE Index"
    }
]
```

### Get Index Detail

```
GET /api/v1/indices/{nepse_id}/
```

### Get Index History

```
GET /api/v1/indices/{nepse_id}/history/
```

**Query Parameters:**
- `start` — Start date (YYYY-MM-DD)
- `end` — End date (YYYY-MM-DD)

**Response:**
```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "index_name": "NEPSE Index",
            "trading_date": "2026-01-15",
            "open": "2000.0000",
            "high": "2050.0000",
            "low": "1990.0000",
            "close": "2030.0000",
            "volume": 1000000,
            "turnover": "2030000000.00",
            "point_change": "30.0000",
            "percentage_change": "1.5000"
        }
    ]
}
```

## Market

### Market Summary

```
GET /api/v1/market/summary/
```

Returns the latest available market snapshot. Uses the latest trading date from stored DailyPrice data.

**Response:**
```json
{
    "trading_date": "2026-01-15",
    "open": "2000.0000",
    "high": "2050.0000",
    "low": "1990.0000",
    "close": "2030.0000",
    "previous_close": "2000.0000",
    "point_change": "30.0000",
    "percentage_change": "1.5000",
    "total_volume": 10000000,
    "total_turnover": "15000000000.00",
    "transactions": 50000
}
```

### Market Gainers

```
GET /api/v1/market/gainers/
```

Returns top gainers based on percentage_change from the latest trading date.

**Query Parameters:**
- `limit` — Number of results (default: 20, max: 100)

**Response:**
```json
{
    "results": [
        {
            "symbol": "NABIL",
            "close": "103.00",
            "percentage_change": "3.0000",
            "volume": 1000000,
            "turnover": "103000000.00"
        }
    ]
}
```

### Market Losers

```
GET /api/v1/market/losers/
```

Returns top losers based on percentage_change from the latest trading date.

**Query Parameters:**
- `limit` — Number of results (default: 20, max: 100)

### Market Turnover

```
GET /api/v1/market/turnover/
```

Returns top stocks by turnover from the latest trading date.

**Query Parameters:**
- `limit` — Number of results (default: 20, max: 100)

### Market Volume

```
GET /api/v1/market/volume/
```

Returns top stocks by volume from the latest trading date.

**Query Parameters:**
- `limit` — Number of results (default: 20, max: 100)

## OpenAPI Documentation

Interactive API docs are available at:

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- Schema: `/api/schema/`

## Caching

Market ranking endpoints (gainers, losers, turnover, volume) and market summary are cached in Redis for 5 minutes (300 seconds). Cache is keyed by trading date and limit.

## Error Responses

```json
{
    "detail": "Not found."
}
```

## Known Limitations

- Market status endpoint not implemented (no MarketStatus model exists)
- Intraday data has no deduplication (by design — upstream semantics unclear)
- No live market status — the API uses the latest available trading date from stored data
- Sector-to-stocks endpoint not implemented (use securities list with sector filter instead)

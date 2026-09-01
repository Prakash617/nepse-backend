# Database / Domain Design

Phase 3 — PostgreSQL domain model for the NEPSE platform.

## Overview

```
Sector
   │
   └── Security
          │
          ├── DailyPrice
          │
          └── IntradayPrice

MarketIndex
   │
   └── IndexSnapshot

MarketSnapshot
   └── market-wide aggregate (one per trading day)
```

## Models

### Sector (`apps.sectors.models.Sector`)

Represents a NEPSE market sector (e.g., Commercial Banks, Hydro Power).

| Field | Type | Constraints | Source |
|---|---|---|---|
| `nepse_id` | PositiveIntegerField | unique | `parse_sectors().id` |
| `name` | CharField(100) | unique | `parse_sectors().name` |
| `display_name` | CharField(200) | blank | `parse_sectors().display_name` |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Ordering:** `name`
**Upstream:** `/api/nots/sector` → `parse_sectors()`

---

### Security (`apps.securities.models.Security`)

A listed security/instrument on NEPSE. Supports multiple security types (ordinary shares, debentures, mutual funds, etc.).

| Field | Type | Constraints | Source |
|---|---|---|---|
| `nepse_id` | PositiveIntegerField | unique | `parse_securities_list().id` |
| `symbol` | CharField(20) | unique, indexed | `parse_securities_list().symbol` |
| `company_name` | CharField(300) | — | `parse_securities_list().company_name` |
| `sector` | FK → Sector | nullable, SET_NULL | `parse_securities_list().sector` (name matched) |
| `security_type` | CharField(50) | blank | `parse_securities_list().security_type` |
| `listing_date` | DateField | nullable | `parse_securities_list().listing_date` |
| `paid_up_value` | DecimalField(12,2) | nullable | `parse_securities_list().paid_up_value` |
| `face_value` | DecimalField(12,2) | nullable | `parse_securities_list().face_value` |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Ordering:** `symbol`
**Upstream:** `/api/nots/company/list` → `parse_securities_list()`

**Design decisions:**
- `sector` is nullable because upstream sector data may be incomplete or use string names that don't exactly match Sector records. `SET_NULL` preserves historical price data when a sector is deleted.
- `symbol` has `unique=True` at the database level.
- `security_type` is a free-form string (not an enum) because upstream values are not fully known and may change.

---

### DailyPrice (`apps.prices.models.DailyPrice`)

Daily market data for a security on a specific trading date.

| Field | Type | Constraints | Source |
|---|---|---|---|
| `security` | FK → Security | CASCADE | — |
| `trading_date` | DateField | indexed | `businessDate` |
| `open` | DecimalField(12,2) | nullable | `openPrice` |
| `high` | DecimalField(12,2) | nullable | `maxPrice` |
| `low` | DecimalField(12,2) | nullable | `minPrice` |
| `close` | DecimalField(12,2) | nullable | `closePrice` |
| `ltp` | DecimalField(12,2) | nullable | `lastTradedPrice` |
| `previous_close` | DecimalField(12,2) | nullable | `previousClose` |
| `volume` | PositiveBigIntegerField | nullable | `totalTradedVolume` |
| `turnover` | DecimalField(18,2) | nullable | `totalTradedValue` |
| `percentage_change` | DecimalField(8,4) | nullable | `percentChange` |
| `point_change` | DecimalField(10,4) | nullable | `pointChange` |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Constraints:** `UniqueConstraint(security, trading_date)`
**Indexes:** `(security, trading_date)`, `(trading_date)`
**Ordering:** `-trading_date`, `security__symbol`
**Upstream:** `/api/nots/nepse-data/today-price` → `parse_today_prices()`, `/api/nots/market/security/price/{id}` → `parse_price_history()`

**Design decisions:**
- All financial fields are nullable (not default=0) to distinguish between actual zero and missing data.
- `on_delete=CASCADE` — if a security is removed, its price history is removed. This is acceptable because delisted securities should keep their records; the sync service should not delete securities that still have historical data.
- `DecimalField` for all monetary/price values. `PositiveBigIntegerField` for volume (always non-negative integer).
- No duplicate `(security, trading_date)` enforced at database level.

---

### IntradayPrice (`apps.prices.models.IntradayPrice`)

Intraday/tick data for a security from live trades.

| Field | Type | Constraints | Source |
|---|---|---|---|
| `security` | FK → Security | CASCADE | — |
| `timestamp` | DateTimeField | indexed | trade timestamp |
| `ltp` | DecimalField(12,2) | nullable | `lastTradedPrice` |
| `volume` | PositiveBigIntegerField | nullable | `totalTradedVolume` |
| `turnover` | DecimalField(18,2) | nullable | `totalTradedValue` |
| `created_at` | DateTimeField | auto_now_add | — |

**Indexes:** `(security, timestamp)`
**Ordering:** `-timestamp`, `security__symbol`
**Upstream:** `/api/nots/lives-market` → `parse_today_prices()` (same schema)

**Design decisions:**
- No uniqueness constraint on `(security, timestamp)` because upstream live data may contain multiple trades at the same timestamp. The exact semantics of the upstream timestamp are not documented.
- Timestamps are stored as `DateTimeField` with UTC.

---

### MarketIndex (`apps.indices.models.MarketIndex`)

A NEPSE market index definition (both main NEPSE index and sector sub-indices).

| Field | Type | Constraints | Source |
|---|---|---|---|
| `nepse_id` | PositiveIntegerField | unique | `parse_indices().id` / `parse_sector_indices().id` |
| `name` | CharField(100) | unique | `parse_indices().name` |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Ordering:** `nepse_id`
**Upstream:** `/api/nots/nepse-index` → `parse_indices()`, `/api/nots/index` → `parse_sector_indices()`

**Design decisions:**
- Both NEPSE and sector indices share the same ID space (51-67). A single model with unique `nepse_id` handles both.
- `name` is also unique — no two indices can share the same name.

---

### IndexSnapshot (`apps.indices.models.IndexSnapshot`)

Historical daily snapshot of a market index.

| Field | Type | Constraints | Source |
|---|---|---|---|
| `index` | FK → MarketIndex | CASCADE | — |
| `trading_date` | DateField | indexed | `businessDate` |
| `open` | DecimalField(12,4) | nullable | `open` |
| `high` | DecimalField(12,4) | nullable | `high` |
| `low` | DecimalField(12,4) | nullable | `low` |
| `close` | DecimalField(12,4) | nullable | `close` |
| `volume` | PositiveBigIntegerField | nullable | `totalTradedVolume` |
| `turnover` | DecimalField(18,2) | nullable | `totalTradedValue` |
| `point_change` | DecimalField(10,4) | nullable | `pointChange` |
| `percentage_change` | DecimalField(8,4) | nullable | `percentChange` |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Constraints:** `UniqueConstraint(index, trading_date)`
**Indexes:** `(index, trading_date)`, `(trading_date)`
**Ordering:** `-trading_date`, `index__name`
**Upstream:** `/api/nots/index/history/{id}` → `parse_index_history()`

**Design decisions:**
- Index values use 4 decimal places (vs 2 for stock prices) because index values can have fractional precision.
- `point_change` and `percentage_change` are included from `parse_indices()` daily snapshots (not available in `parse_index_history()`).

---

### MarketSnapshot (`apps.market.models.MarketSnapshot`)

Daily market-wide aggregate snapshot. One record per trading day.

| Field | Type | Constraints | Source |
|---|---|---|---|
| `trading_date` | DateField | unique, indexed | — |
| `total_volume` | PositiveBigIntegerField | nullable | `totalTradedVolume` |
| `total_turnover` | DecimalField(18,2) | nullable | `totalTradedValue` |
| `transactions` | PositiveIntegerField | nullable | `transactions` |
| `open` | DecimalField(12,4) | nullable | `open` |
| `high` | DecimalField(12,4) | nullable | `high` |
| `low` | DecimalField(12,4) | nullable | `low` |
| `close` | DecimalField(12,4) | nullable | `close` |
| `previous_close` | DecimalField(12,4) | nullable | `previousClose` |
| `point_change` | DecimalField(10,4) | nullable | `pointChange` |
| `percentage_change` | DecimalField(8,4) | nullable | `percentChange` |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Ordering:** `-trading_date`
**Upstream:** `/api/nots/market-summary` → `parse_market_summary()`

**Design decisions:**
- Trading-date-based (not timestamp) because upstream returns daily aggregates.
- `trading_date` is unique — only one snapshot per day.
- No separate `traded_companies` field because it's not in the upstream response.

---

## Database Constraints Summary

| Model | Constraint | Type |
|---|---|---|
| Sector | `nepse_id` unique | UNIQUE |
| Sector | `name` unique | UNIQUE |
| Security | `nepse_id` unique | UNIQUE |
| Security | `symbol` unique | UNIQUE |
| DailyPrice | `(security, trading_date)` unique | UNIQUE CONSTRAINT |
| MarketIndex | `nepse_id` unique | UNIQUE |
| MarketIndex | `name` unique | UNIQUE |
| IndexSnapshot | `(index, trading_date)` unique | UNIQUE CONSTRAINT |
| MarketSnapshot | `trading_date` unique | UNIQUE |

## Database Indexes Summary

| Model | Fields | Purpose |
|---|---|---|
| Security | `symbol` | Lookup by ticker symbol |
| DailyPrice | `(security, trading_date)` | Historical price queries |
| DailyPrice | `trading_date` | Date-range queries across securities |
| IntradayPrice | `(security, timestamp)` | Intraday history queries |
| IndexSnapshot | `(index, trading_date)` | Index history queries |
| IndexSnapshot | `trading_date` | Date-range queries across indices |

## Precision Rationale

- **Stock prices** (DailyPrice, IntradayPrice): `DecimalField(12,2)` — NEPSE stock prices are in NPR with 2 decimal places. Max value ~999,999,999.99.
- **Index values** (IndexSnapshot, MarketSnapshot): `DecimalField(12,4)` — index values can have fractional precision beyond 2 decimals.
- **Turnover**: `DecimalField(18,2)` — total traded value can be very large (millions/billions NPR).
- **Percentage**: `DecimalField(8,4)` — supports values like -99.9999 to 9999.9999.
- **Volume**: `PositiveBigIntegerField` — always non-negative integer, can be very large.

## Fields Intentionally Not Included

- **ISIN**: Not present in upstream NEPSE API responses.
- **Sector description**: Upstream only provides `name` and `displayName`.
- **Security status (active/delisted)**: Not explicitly provided by upstream. The sync service can infer this from data presence.
- **MarketSnapshot.traded_companies**: Not in upstream response.
- **IndexSnapshot.turnover for sector indices**: Not available in `parse_sector_indices()`.

## Future Scalability Considerations

- **DailyPrice** and **IntradayPrice** will be the highest-volume tables. Indexes are designed for the most common query patterns.
- **Table partitioning** by `trading_date` could be considered when data volume grows (e.g., partitioning DailyPrice by year).
- **Archival strategy**: Old intraday data could be aggregated into daily summaries and purged.
- **Connection pooling**: `CONN_MAX_AGE=600` is configured in settings for persistent connections.

## Files Changed

- `apps/sectors/models.py` — Sector model
- `apps/sectors/admin.py` — SectorAdmin
- `apps/securities/models.py` — Security model
- `apps/securities/admin.py` — SecurityAdmin
- `apps/prices/models.py` — DailyPrice, IntradayPrice models
- `apps/prices/admin.py` — DailyPriceAdmin, IntradayPriceAdmin
- `apps/indices/models.py` — MarketIndex, IndexSnapshot models
- `apps/indices/admin.py` — MarketIndexAdmin, IndexSnapshotAdmin
- `apps/market/models.py` — MarketSnapshot model
- `apps/market/admin.py` — MarketSnapshotAdmin
- `apps/sectors/migrations/0001_initial.py`
- `apps/securities/migrations/0001_initial.py`
- `apps/prices/migrations/0001_initial.py`
- `apps/indices/migrations/0001_initial.py`
- `apps/market/migrations/0001_initial.py`
- `tests/test_sector_models.py`
- `tests/test_security_models.py`
- `tests/test_price_models.py`
- `tests/test_index_models.py`
- `tests/test_market_models.py`

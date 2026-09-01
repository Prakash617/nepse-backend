# Historical Data & Backfill

Phase 6 — Historical market-data backfill system for DailyPrice.

## Architecture

```
NEPSE Historical API
        ↓
NepseClient.get_price_history()
        ↓
parse_price_history()
        ↓
sync_historical_prices()
        ↓
sync_daily_prices()
        ↓
PostgreSQL (DailyPrice)
```

## Historical Endpoint

**Primary:** `GET /api/nots/market/security/price/{id}`

- Per-security (one ticker at a time)
- Date-range filtering: `startDate`, `endDate` (YYYY-MM-DD)
- Paginated: `page` (0-indexed), `size` (max 500)
- Returns: `businessDate`, `openPrice`, `maxPrice`, `minPrice`, `closePrice`, `lastTradedPrice`, `totalTradedVolume`, `totalTradedValue`

**Note:** `parse_price_history()` does NOT return `previousClose`, `percentChange`, or `pointChange`. Those fields are only available from `parse_today_prices()` (single-date endpoint).

## Date Semantics

- `businessDate` in upstream response corresponds to `trading_date` in DailyPrice
- Dates are in `YYYY-MM-DD` format
- Weekends and holidays: the upstream API simply returns no data for non-trading days. No empty records are created.

## Service Functions

### `sync_historical_prices()`

```python
sync_historical_prices(
    symbols: list[str],
    start_date: date,
    end_date: date,
    client: NepseClient | None = None,
    page_size: int = 500,
) -> SyncResult
```

Fetches historical price data for each symbol over the date range, handling pagination. Delegates persistence to the existing `sync_daily_prices()` function.

**Behavior:**
- Iterates over each symbol
- Fetches pages until fewer than `page_size` records returned
- Tags each record with the symbol for `sync_daily_prices()`
- Returns aggregated `SyncResult` across all symbols and pages

## Management Commands

### `sync_historical_prices`

```bash
python manage.py sync_historical_prices \
    --start 2024-01-01 \
    --end 2024-12-31

# Specific symbols
python manage.py sync_historical_prices \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --symbols NABIL NHPC

# Dry run
python manage.py sync_historical_prices \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --dry-run
```

**Output:**
```
Historical Price Synchronization
  Date range: 2024-01-01 → 2024-12-31
  Securities: 312

Historical Prices:
  Created: 97000
  Updated: 0
  Skipped: 0
  Failed: 0
```

### `check_price_data`

```bash
python manage.py check_price_data
```

**Checks:**
- Duplicate records
- Orphan records (no valid security)
- OHLC consistency (high >= low)
- Negative volume
- All-null price fields
- Securities without history

## Celery Task

```python
# Thin wrapper
sync_historical_prices_task(
    symbols=["NABIL", "NHPC"],
    start_date="2024-01-01",
    end_date="2024-12-31",
)
```

**Note:** Historical backfills should be manually initiated, not scheduled automatically.

## Idempotency

DailyPrice has `UNIQUE(security, trading_date)`. Running the same sync twice:
- First run: creates records
- Second run: updates existing records (or skips if unchanged)

Overlapping ranges are safe:
- First: 2024-01-01 → 2024-06-30
- Second: 2024-04-01 → 2024-12-31
- Overlapping records (April–June) are updated/skipped, not duplicated

## Bulk Processing

- Uses `bulk_create(ignore_conflicts=True)` for new records
- Uses `bulk_update(fields=[...])` for changed records
- In-memory security lookup maps (no N+1 queries)
- Single `transaction.atomic()` per sync call

## Transaction Strategy

- Each `sync_historical_prices()` call uses one transaction
- For very large backfills, chunking at the command/task level provides natural boundaries
- If a chunk fails, previous committed chunks are preserved

## Chunk Strategy

The upstream API paginates at 500 records per request. The service automatically handles pagination. For multi-year backfills, the command processes the entire range in one call, relying on pagination.

If the upstream API fails mid-range, the service records the failure and continues with the next symbol.

## Error Handling

- API failures: recorded in `SyncResult.errors`, counted as `failed`
- Unknown securities: skipped with error message
- Invalid records: skipped with error message
- Network errors: caught and recorded, do not corrupt other symbols

## Data Validation

The existing `sync_daily_prices()` validates:
- `trading_date` is present and valid
- Security can be resolved to a database ID
- Financial values are convertible to Decimal/Int

OHLC consistency is checked by `check_price_data` command (not enforced during sync, because upstream data may have edge cases).

## Performance Baseline

- Upstream API: paginated at 500 records/request
- Database: bulk operations (no individual INSERT/UPDATE per row)
- Security lookup: O(1) per record via in-memory map
- Typical throughput: limited by upstream API response time, not database

## Files Changed

- `apps/prices/services.py` — Added `sync_historical_prices()`
- `apps/prices/tasks.py` — Added `sync_historical_prices_task`
- `apps/prices/management/commands/sync_historical_prices.py` — New
- `apps/prices/management/commands/check_price_data.py` — New
- `apps/sectors/views.py` — Fixed ordering (pre-existing bug)
- `tests/test_historical_sync.py` — New (11 tests)
- `docs/historical-data.md` — New

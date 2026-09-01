# Data Synchronization Architecture

Phase 4 — Reliable, idempotent data synchronization pipeline.

## Architecture

```
NEPSE API
  ↓
NepseClient (Phase 2)
  ↓
Parsers (Phase 2)
  ↓
Sync Services (Phase 4)
  ↓
PostgreSQL (Phase 3)
```

## Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Management Cmd  │────▶│  Sync Service    │────▶│   PostgreSQL    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              ▲
┌─────────────────┐           │
│  Celery Task    │───────────┘
└─────────────────┘
```

- **Management commands** are thin wrappers that call services
- **Celery tasks** are thin wrappers that call services
- **Services** contain ALL synchronization logic
- **Models** are never modified with sync logic

## Sync Order

Recommended order due to foreign key dependencies:

1. `sync_sectors` — Sector definitions
2. `sync_securities` — Security definitions (references Sector)
3. `sync_indices` — Market index definitions
4. `sync_daily_prices` — Daily price data (references Security)
5. `sync_index_snapshots` — Index history (references MarketIndex)
6. `sync_market_snapshot` — Market-wide daily aggregates
7. `sync_intraday_prices` — Live trade data (references Security)

## Services

### `apps/sectors/services.py`

| Function | Identity | Behavior |
|---|---|---|
| `sync_sectors(data)` | `nepse_id` | Create/update, never delete |

### `apps/securities/services.py`

| Function | Identity | Behavior |
|---|---|---|
| `sync_securities(data)` | `nepse_id` | Create/update, never delete |

**Sector matching:** Normalizes upstream sector names (lowercase, strip whitespace) before matching to Sector.name. Unknown sectors are left as NULL.

### `apps/prices/services.py`

| Function | Identity | Behavior |
|---|---|---|
| `sync_daily_prices(data)` | `(security_id, trading_date)` | Create/update, preserves history |
| `sync_intraday_prices(data)` | None (append-only) | Creates all records, no dedup |

**Note on intraday:** No uniqueness constraint is enforced because upstream timestamp semantics are unclear. Each sync call appends new records.

### `apps/indices/services.py`

| Function | Identity | Behavior |
|---|---|---|
| `sync_indices(data)` | `nepse_id` | Create/update, never delete |
| `sync_index_snapshots(index_id, data)` | `(index, trading_date)` | Create/update, preserves history |

### `apps/market/services.py`

| Function | Identity | Behavior |
|---|---|---|
| `sync_market_snapshot(data, date)` | `trading_date` | Create/update single record |

## SyncResult

Every service returns a `SyncResult`:

```python
@dataclass
class SyncResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
```

## Idempotency Strategy

All services are idempotent:

- **Sectors/Securities/Indices:** Match by `nepse_id`. Create if missing, update if changed, skip if unchanged.
- **DailyPrice/IndexSnapshot:** Match by composite key. Create if missing, update if changed.
- **MarketSnapshot:** Match by `trading_date`. Create if missing, update if changed.
- **IntradayPrice:** Append-only (no uniqueness constraint).

## Transaction Strategy

Each sync function uses a single `transaction.atomic()` block:
- Creates are done via `bulk_create` (single query)
- Updates are done via `bulk_update` (single query)
- No individual row queries in loops

## Bulk Operations

- **`bulk_create`** with `ignore_conflicts=True` for new records
- **`bulk_update`** for changed records
- **In-memory lookup maps** for existing record comparison
- Single database queries for filtering, not N+1

## Management Commands

```bash
# Sync sectors
python manage.py sync_sectors [--dry-run]

# Sync securities
python manage.py sync_securities [--dry-run]

# Sync daily prices
python manage.py sync_prices [--business-date YYYY-MM-DD] [--dry-run]

# Sync indices
python manage.py sync_indices [--dry-run]

# Sync market snapshot
python manage.py sync_market [--dry-run]
```

## Celery Tasks

```python
# tasks are thin wrappers around services
sectors.sync_sectors
securities.sync_securities
prices.sync_daily_prices
prices.sync_intraday_prices
indices.sync_indices
indices.sync_index_snapshots
market.sync_market_snapshot
```

## Error Handling

Services distinguish between:
- **Upstream unavailable** — NepseError raised, logged, task retries
- **Invalid data** — skipped with error message in SyncResult.errors
- **Unresolved foreign keys** — skipped with clear error message
- **Database errors** — raised, transaction rolls back

## Logging

```python
logger.info(
    "Sector sync complete: created=%d, updated=%d, skipped=%d, failed=%d",
    result.created, result.updated, result.skipped, result.failed,
)
```

Services log start/summary at INFO level. No per-row logging.

## Files Changed

- `apps/common/__init__.py`
- `apps/common/sync.py` — SyncResult dataclass
- `apps/sectors/services.py`
- `apps/sectors/tasks.py`
- `apps/sectors/management/commands/sync_sectors.py`
- `apps/securities/services.py`
- `apps/securities/tasks.py`
- `apps/securities/management/commands/sync_securities.py`
- `apps/prices/services.py`
- `apps/prices/tasks.py`
- `apps/prices/management/commands/sync_prices.py`
- `apps/indices/services.py`
- `apps/indices/tasks.py`
- `apps/indices/management/commands/sync_indices.py`
- `apps/market/services.py`
- `apps/market/tasks.py`
- `apps/market/management/commands/sync_market.py`
- `tests/test_sector_sync.py`
- `tests/test_security_sync.py`
- `tests/test_price_sync.py`
- `tests/test_index_sync.py`
- `tests/test_market_sync.py`
- `tests/test_sync_tasks.py`
- `docs/sync-architecture.md`

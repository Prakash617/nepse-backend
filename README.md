# NEPSE Platform — Backend

Production-oriented market-data platform for the Nepal Stock Exchange (NEPSE). Backend API built with Django REST Framework, PostgreSQL, Redis, and Celery.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | Django 5.1 + Django REST Framework |
| Database | PostgreSQL 16 |
| Cache/Broker | Redis 7 |
| Task Queue | Celery + Celery Beat |
| API Docs | drf-spectacular (Swagger/ReDoc) |
| Package Manager | uv |
| Python | 3.12+ |

## Project Structure

```
backend/
├── apps/                    # Django applications
│   ├── market/              # Market snapshot (daily aggregates)
│   ├── prices/              # Daily stock prices (LTP, OHLCV)
│   ├── securities/          # Stock listings
│   ├── sectors/             # Market sectors
│   ├── indices/             # Market indices (NEPSE Index, Sensitive, etc.)
│   ├── fundamentals/        # Company profiles, financial reports
│   ├── corporate_actions/   # Dividends, bonuses, AGMs
│   ├── watchlist/           # User watchlists
│   ├── alerts/              # Price/volume alerts
│   ├── notifications/       # Alert notifications
│   ├── users/               # User auth
│   ├── common/              # Shared utilities (SyncResult, etc.)
│   ├── ipo/                 # IPO data
│   └── news/                # News feed
├── integrations/            # External API clients
│   ├── nepse/               # Live NEPSE API client (nepalstock.com)
│   └── yonepse/             # YONEPSE historical data (GitHub Pages)
├── tasks/                   # Celery task definitions
├── config/                  # Django settings, Celery config, URLs
├── tests/                   # Test suite
├── docs/                    # Internal documentation
├── manage.py
├── pyproject.toml
├── docker-compose.yml
└── .env
```

## Quick Start

### 1. Prerequisites

- Python 3.12+
- uv (package manager)
- Docker & Docker Compose

### 2. Start Infrastructure (PostgreSQL + Redis)

```bash
cd backend
docker compose up -d
```

This starts:
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6380`

### 3. Install Dependencies

```bash
uv sync
```

### 4. Configure Environment

Copy and edit `.env` if needed (defaults work for local dev):

```bash
cp .env.example .env  # or edit directly
```

Key variables:
```
POSTGRES_DB=nepse_platform
POSTGRES_USER=nepse
POSTGRES_PASSWORD=nepse
REDIS_URL=redis://localhost:6380/0
CELERY_BROKER_URL=redis://localhost:6380/1
```

### 5. Run Migrations

```bash
uv run python manage.py migrate
```

### 6. Create Superuser (optional)

```bash
uv run python manage.py createsuperuser
```

### 7. Sync Market Data

**Bootstrap all historical data from YONEPSE** (recommended first time):

```bash
uv run python manage.py bootstrap_yonepse_data
```

This fetches from YONEPSE GitHub Pages:
- Sectors and securities
- Market indices
- Market history snapshots
- Historical daily prices (LTP)

**Sync today's live market data:**

```bash
uv run python manage.py sync_market
```

### 8. Start the Server

```bash
uv run python manage.py runserver
```

API available at: `http://localhost:8000/api/v1/`

### 9. Start Celery Workers (optional, for background tasks)

```bash
# Terminal 1 - Worker
uv run celery -A config worker -l info

# Terminal 2 - Beat scheduler
uv run celery -A config beat -l info
```

## Data Sync Commands

All commands support `--dry-run` flag to preview without writing to database.

| Command | Description |
|---------|-------------|
| `bootstrap_yonepse_data` | Bootstrap all historical data from YONEPSE |
| `sync_market` | Sync today's market snapshot from NEPSE |
| `sync_prices` | Sync today's stock prices from NEPSE |
| `sync_securities` | Sync security listings from NEPSE |
| `sync_sectors` | Sync sector definitions from NEPSE |
| `sync_indices` | Sync market indices from NEPSE |
| `sync_historical_prices` | Sync historical prices from NEPSE |
| `sync_company_profiles` | Sync company profiles |
| `sync_financial_reports` | Sync financial reports |

### Bootstrap Options

```bash
# Bootstrap everything
uv run python manage.py bootstrap_yonepse_data

# Bootstrap only specific datasets
uv run python manage.py bootstrap_yonepse_data --securities
uv run python manage.py bootstrap_yonepse_data --indices
uv run python manage.py bootstrap_yonepse_data --market
uv run python manage.py bootstrap_yonepse_data --prices

# Date range for prices
uv run python manage.py bootstrap_yonepse_data --start 2020-01-01 --end 2025-12-31

# Dry run
uv run python manage.py bootstrap_yonepse_data --dry-run
```

### Sync Market Snapshot

```bash
# Sync from index history (primary method)
uv run python manage.py sync_market

# Dry run
uv run python manage.py sync_market --dry-run
```

### Sync Daily Prices

```bash
# Sync latest
uv run python manage.py sync_prices

# Specific date
uv run python manage.py sync_prices --business-date 2025-08-15

# Dry run
uv run python manage.py sync_prices --dry-run
```

## API Endpoints

All endpoints are under `/api/v1/`.

### Market Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/market/summary/` | GET | Latest market snapshot |
| `/api/v1/market/gainers/` | GET | Top gainers by % change |
| `/api/v1/market/losers/` | GET | Top losers by % change |
| `/api/v1/market/turnover/` | GET | Top stocks by turnover |
| `/api/v1/market/volume/` | GET | Top stocks by volume |

### Securities

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/securities/` | GET | List all securities |
| `/api/v1/securities/{symbol}/` | GET | Security detail |
| `/api/v1/securities/{symbol}/history/` | GET | Price history |

### Other

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/sectors/` | GET | List sectors |
| `/api/v1/indices/` | GET | List market indices |
| `/api/v1/indices/{id}/history/` | GET | Index history |
| `/api/v1/fundamentals/profiles/` | GET | Company profiles |
| `/api/v1/fundamentals/reports/` | GET | Financial reports |
| `/api/v1/corporate-actions/dividends/` | GET | Dividend data |
| `/api/v1/watchlists/` | GET/POST | User watchlists |
| `/api/v1/alerts/` | GET/POST | Price alerts |

### API Documentation

- Swagger UI: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`
- Schema: `http://localhost:8000/api/schema/`

## Data Sources

### 1. YONEPSE (Historical Data)

Static JSON datasets hosted on GitHub Pages via [YONEPSE](https://github.com/shubhamnpk/yonepse).

Used for:
- Bootstrapping historical data
- Securities, sectors, indices definitions
- Historical daily prices (LTP)
- Market history snapshots

**Base URL:** `https://shubhamnpk.github.io/yonepse/data/`

### 2. NEPSE Live API (Real-time Data)

Live data from [nepalstock.com](https://www.nepalstock.com).

Used for:
- Live market summary
- Today's prices
- Current indices

**Base URL:** `https://www.nepalstock.com`

## Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_market_sync.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=apps --cov-report=term-missing
```

## Linting & Type Checking

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy .
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | (dev key) | Django secret key |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | Settings module |
| `DEBUG` | `true` | Debug mode |
| `POSTGRES_DB` | `nepse_platform` | Database name |
| `POSTGRES_USER` | `nepse` | Database user |
| `POSTGRES_PASSWORD` | `nepse` | Database password |
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `REDIS_URL` | `redis://localhost:6380/0` | Redis cache URL |
| `CELERY_BROKER_URL` | `redis://localhost:6380/1` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6380/2` | Celery result backend |
| `NEPSE_API_BASE_URL` | `https://www.nepalstock.com` | NEPSE API base |
| `NEPSE_TIMEOUT` | `30` | API timeout (seconds) |

## Architecture Notes

### Data Flow

```
YONEPSE (GitHub Pages)  ──┐
                           ├──> Management Commands ──> Services ──> PostgreSQL
NEPSE Live API           ─┘                                              │
                                                                         │
Frontend (Next.js:3000)  <── DRF API Views <──────────────────────────────┘
```

### Key Patterns

1. **Services contain business logic** — Views and tasks call services, not vice versa
2. **Idempotent sync** — All sync services use `SyncResult` tracking created/updated/skipped/failed
3. **Management commands** — Entry points for data sync (can be called manually or via Celery)
4. **Celery tasks are thin wrappers** — Tasks call service functions, not business logic directly
5. **Cache-first API** — Market summary views cache results for 5 minutes

### SyncResult

All sync services return a `SyncResult` dataclass:

```python
@dataclass
class SyncResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
```

## License

MIT

# NEPSE Platform — Backend

Production-oriented market-data platform for the Nepal Stock Exchange (NEPSE). Backend API built with Django REST Framework, PostgreSQL, Redis, Celery, and Django Channels.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | Django 5.1 + Django REST Framework |
| Real-time WebSockets | Django Channels + Redis Channel Layer |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 (Dual-use: Caching & Celery Broker) |
| Task Queue | Celery + Celery Beat |
| Bot Integration | Telegram Bot API (`requests` / Async tasks) |
| Push Notifications | Web Push (pywebpush / VAPID) |
| API Docs | drf-spectacular (Swagger / ReDoc) |
| Package Manager | uv |
| Python | 3.12+ |

---

## Project Structure

```
.
├── apps/                    # Django applications
│   ├── market/              # Market snapshot (daily aggregates)
│   ├── prices/              # Daily stock prices (LTP, OHLCV)
│   ├── securities/          # Stock listings & historical data APIs
│   ├── sectors/             # Market sectors
│   ├── indices/             # Market indices (NEPSE Index, Sensitive, etc.)
│   ├── fundamentals/        # Company profiles, financial reports
│   ├── corporate_actions/   # Dividends, bonuses, AGMs
│   ├── watchlist/           # User watchlists
│   ├── alerts/              # Price/volume AlertEngine & triggers
│   ├── notifications/       # Multi-channel notifications (In-app, Push, Telegram)
│   │   ├── telegram.py      # Telegram bot client, formatting, and update processor
│   │   ├── push.py          # Web Push VAPID dispatcher
│   │   ├── services.py      # Notification lifecycle & WebSocket broadcaster
│   │   └── management/commands/run_telegram_bot.py # Bot polling daemon
│   ├── users/               # JWT authentication & profile management
│   ├── common/              # Shared utilities (SyncResult, etc.)
│   ├── ipo/                 # IPO data
│   └── news/                # News feed
├── integrations/            # External API clients
│   ├── nepse/               # Live NEPSE API client (nepalstock.com)
│   └── yonepse/             # YONEPSE historical data (GitHub Pages)
├── tasks/                   # Celery task definitions
├── config/                  # Django settings, Celery config, URLs, ASGI
├── tests/                   # Test suite (420+ automated unit & integration tests)
├── docs/                    # Internal documentation
├── manage.py
├── pyproject.toml
├── docker-compose.yml
└── .env
```

---

## Quick Start

### 1. Prerequisites
- Python 3.12+
- `uv` (package manager)
- Docker & Docker Compose

### 2. Start Infrastructure (PostgreSQL + Redis)
```bash
docker compose up -d
```
Starts:
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6380`

### 3. Install Dependencies
```bash
uv sync
```

### 4. Configure Environment
```bash
cp .env.example .env
```
Key variables in `.env`:
```ini
DJANGO_SECRET_KEY=your-secret-key
DJANGO_SETTINGS_MODULE=config.settings.development
DEBUG=true

POSTGRES_DB=nepse_platform
POSTGRES_USER=nepse
POSTGRES_PASSWORD=nepse
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

REDIS_URL=redis://localhost:6380/0
CELERY_BROKER_URL=redis://localhost:6380/1
CELERY_RESULT_BACKEND=redis://localhost:6380/2

# Telegram Bot Integration
TELEGRAM_BOT_TOKEN=8274788886:AAGHiSL0i4nuYM_AYjraWI31ltlcu_frKHk
TELEGRAM_BOT_USERNAME=stock_napal_bot

# Web Push VAPID Keys
VAPID_PUBLIC_KEY=your-vapid-public-key
VAPID_PRIVATE_KEY=your-vapid-private-key
VAPID_ADMIN_EMAIL=admin@nepseplatform.local
```

### 5. Run Database Migrations
```bash
uv run python manage.py migrate
```

### 6. Create Superuser (optional)
```bash
uv run python manage.py createsuperuser
```

### 7. Sync Market Data
```bash
# Bootstrap historical data from YONEPSE:
uv run python manage.py bootstrap_yonepse_data

# Sync today's live market data:
uv run python manage.py sync_market
uv run python manage.py sync_prices
```

### 8. Start the API Server
```bash
uv run python manage.py runserver 0.0.0.0:8000
```
API Root: `http://localhost:8000/api/v1/`

### 9. Start Telegram Bot Daemon (for Live Account Pairing)
```bash
uv run python manage.py run_telegram_bot
```

### 10. Start Celery Worker & Beat Scheduler
```bash
# Terminal 1 - Worker
uv run celery -A config worker -l info

# Terminal 2 - Beat scheduler
uv run celery -A config beat -l info
```

---

## Multi-Channel Notification System

The platform supports 3 unified notification delivery channels:

1. **In-App Real-time Notifications (WebSockets)**:
   - WebSocket endpoint: `ws://localhost:8000/ws/notifications/`
   - Real-time popups and unread badge count updates on the frontend.
2. **Browser Web Push Notifications (PWA / VAPID)**:
   - Desktop and mobile push alerts delivered even when the browser tab is closed.
   - Subscriptions managed via `/api/v1/notifications/push/subscribe/`.
3. **Telegram Bot Alerts (`@stock_napal_bot`)**:
   - Secure deep-link account pairing via `/start <token>`.
   - Multi-user isolation — each user receives only their own triggered alerts.
   - Asynchronous delivery via Celery task `send_telegram_notification_task`.

---

## API Endpoints (`/api/v1/`)

### Market & Securities
| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/market/summary/` | GET | Latest market aggregate summary |
| `/api/v1/market/gainers/` | GET | Top gainers |
| `/api/v1/market/losers/` | GET | Top losers |
| `/api/v1/market/turnover/` | GET | Top stocks by turnover |
| `/api/v1/market/volume/` | GET | Top stocks by volume |
| `/api/v1/securities/` | GET | List securities with search & sector filters |
| `/api/v1/securities/{symbol}/` | GET | Security metadata and profile |
| `/api/v1/securities/{symbol}/history/` | GET | Historical daily OHLCV prices (`start`, `end`) |
| `/api/v1/securities/{symbol}/intraday/` | GET | Intraday trading prices |

### Alerts & Watchlists
| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/alerts/` | GET / POST | List and create price/volume market alerts |
| `/api/v1/alerts/{id}/` | GET / PUT / DELETE | Manage existing alert configuration |
| `/api/v1/watchlists/` | GET / POST | User watchlist management |
| `/api/v1/watchlists/{id}/items/` | POST / DELETE | Add or remove stocks from watchlist |

### Notifications & Telegram Bot
| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/notifications/` | GET | List user notifications |
| `/api/v1/notifications/unread-count/` | GET | Unread notification count |
| `/api/v1/notifications/{id}/read/` | POST | Mark notification as read |
| `/api/v1/notifications/push/subscribe/` | POST | Register Web Push VAPID subscription |
| `/api/v1/notifications/push/status/` | GET | Check Web Push subscription status |
| `/api/v1/notifications/telegram/status/` | GET | Check Telegram connection status |
| `/api/v1/notifications/telegram/connect/` | POST | Generate one-time Telegram pairing link |
| `/api/v1/notifications/telegram/disconnect/` | POST | Disconnect Telegram account |
| `/api/v1/notifications/telegram/test/` | POST | Send test alert to connected Telegram |
| `/api/v1/notifications/telegram/webhook/` | POST | Telegram Bot webhook receiver |

---

## Running Tests

```bash
# Run entire test suite (420+ tests)
uv run pytest --reuse-db

# Run notifications & Telegram bot test suite
uv run pytest tests/test_notification_api.py tests/test_push_notifications.py tests/test_telegram_bot.py --reuse-db

# Run with coverage report
uv run pytest --cov=apps --cov-report=term-missing
```

---

## Code Quality & Type Checking

```bash
# Lint with ruff
uv run ruff check .

# Type check with mypy
uv run mypy .
```

---

## CI/CD

This repository is the backend-only repository. It was split from the
`nepse-alert` monorepo and deploys independently to the VPS.

- **CI** (`.github/workflows/ci.yml`) runs on pushes/PRs to `main`:
  Ruff, Django system check, migration drift check, pytest, and a Docker
  image build/smoke test.
- **CD** (`.github/workflows/deploy.yml`) runs after CI succeeds on `main`:
  it checks out the exact tested SHA on the VPS, rebuilds
  `docker-compose.prod.yml`, restarts nginx, and waits for
  `GET /api/v1/system/health/` to return `200`.

### Required repository secrets

| Secret | Purpose |
|---|---|
| `VPS_HOST` | VPS hostname or IP |
| `VPS_USER` | SSH user |
| `VPS_SSH_KEY` | Private SSH key with access to the VPS |

Optional repository variable: `DEPLOY_PATH` (defaults to `~/nepse-backend`).

### VPS setup

```bash
git clone git@github.com:Prakash617/nepse-backend.git ~/nepse-backend
cd ~/nepse-backend
cp .env.production.example .env
# edit .env with production values
```

The VPS needs Docker + Compose, a GitHub deploy key with read access to this
repository, and the nginx certificates referenced by
`docker-compose.prod.yml`.

### Health endpoint

`GET /api/v1/system/health/` returns `200 {"status":"ok","database":"ok"}` when
PostgreSQL is reachable, or `503` otherwise. The CD workflow uses it as the
deploy readiness gate.

---

## License

MIT

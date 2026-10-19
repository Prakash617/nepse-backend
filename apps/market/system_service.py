"""System specifications and sync schedule telemetry service."""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import django
from django.conf import settings
from django.db import connection

from apps.alerts.models import Alert, AlertHistory
from apps.corporate_actions.models import BonusShare, Dividend
from apps.indices.models import IndexSnapshot, MarketIndex
from apps.market.models import MarketSnapshot
from apps.notifications.models import TelegramSubscription
from apps.prices.models import DailyPrice, IntradayPrice
from apps.securities.models import Security

logger = logging.getLogger(__name__)

NPT_ZONE = ZoneInfo("Asia/Kathmandu")
REDIS_EXEC_LOGS_KEY = "nepse:sync_execution_logs"


def get_nepal_now() -> datetime:
    """Return the current datetime in Asia/Kathmandu timezone."""
    return datetime.now(NPT_ZONE)


def calculate_market_session(now: datetime) -> dict[str, Any]:
    """Calculate the market session state and countdown for Nepal Stock Exchange.

    Trading Days: Monday (0) through Friday (4).
    Weekend: Saturday (5) and Sunday (6).
    Pre-open: 11:00 AM to 11:15 AM NPT.
    Regular trading: 11:15 AM to 3:00 PM (15:00) NPT.
    """
    weekday = now.weekday()  # Monday is 0, Sunday is 6
    is_trading_day = 0 <= weekday <= 4

    # Current time as time object
    current_time = now.time()
    t_1100 = datetime.strptime("11:00:00", "%H:%M:%S").time()
    t_1115 = datetime.strptime("11:15:00", "%H:%M:%S").time()
    t_1500 = datetime.strptime("15:00:00", "%H:%M:%S").time()

    is_open = False
    session = "CLOSED"

    if is_trading_day:
        if t_1100 <= current_time < t_1115:
            is_open = True
            session = "PRE_OPEN"
        elif t_1115 <= current_time < t_1500:
            is_open = True
            session = "REGULAR"
        else:
            session = "CLOSED"
    else:
        session = "CLOSED"

    # Compute next session start
    next_session_name = "Pre-Open Session"
    if session == "PRE_OPEN":
        next_session_name = "Regular Trading Session"
        target_dt = now.replace(hour=11, minute=15, second=0, microsecond=0)
    elif session == "REGULAR":
        next_session_name = "Market Close (EOD Settlement)"
        target_dt = now.replace(hour=15, minute=0, second=0, microsecond=0)
    else:
        # Determine next trading day's 11:00 AM
        candidate = now.replace(hour=11, minute=0, second=0, microsecond=0)
        if candidate <= now or candidate.weekday() > 4:
            days_ahead = 1
            candidate_date = now + timedelta(days=days_ahead)
            while candidate_date.weekday() > 4:  # Skip Saturday (5) and Sunday (6)
                days_ahead += 1
                candidate_date = now + timedelta(days=days_ahead)
            target_dt = candidate_date.replace(hour=11, minute=0, second=0, microsecond=0)
        else:
            target_dt = candidate

    delta = target_dt - now
    total_seconds = max(0, int(delta.total_seconds()))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    countdown_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

    return {
        "is_open": is_open,
        "current_session": session,
        "trading_days": "Monday through Friday",
        "weekend_days": "Saturday and Sunday",
        "pre_open_session": "11:00 AM – 11:15 AM NPT",
        "regular_session": "11:15 AM – 03:00 PM NPT",
        "order_placement": "24/7 (Queued and executed during market hours)",
        "next_session_name": next_session_name,
        "next_session_time": target_dt.isoformat(),
        "time_until_next_session": countdown_str,
    }


def get_database_latency() -> tuple[str, float | None]:
    """Test PostgreSQL connection and return status and latency in ms."""
    try:
        t0 = time.perf_counter()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return "Connected", latency
    except Exception:
        return "Disconnected", None


def get_redis_client() -> Any | None:
    """Return a connected Redis client instance."""
    try:
        import redis
        broker_url = getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/1")
        return redis.from_url(broker_url, socket_timeout=1.0)
    except Exception:
        return None


def get_redis_latency() -> tuple[str, float | None]:
    """Test Redis connection and return status and latency in ms."""
    try:
        client = get_redis_client()
        if not client:
            return "Disconnected", None
        t0 = time.perf_counter()
        client.ping()
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return "Connected", latency
    except Exception:
        return "Disconnected", None


def record_sync_execution_log(log_entry: dict[str, Any]) -> None:
    """Persist a sync task execution log in Redis (capped at 50 entries)."""
    try:
        client = get_redis_client()
        if not client:
            return
        payload = json.dumps(log_entry)
        client.lpush(REDIS_EXEC_LOGS_KEY, payload)
        client.ltrim(REDIS_EXEC_LOGS_KEY, 0, 49)
    except Exception as e:
        logger.warning("Failed to record sync execution log in Redis: %s", e)


def get_sync_execution_logs(limit: int = 15) -> list[dict[str, Any]]:
    """Retrieve recent task execution logs from Redis."""
    try:
        client = get_redis_client()
        if not client:
            return []
        raw_items = client.lrange(REDIS_EXEC_LOGS_KEY, 0, limit - 1)
        logs = []
        for raw in raw_items:
            try:
                logs.append(json.loads(raw))
            except Exception:
                continue
        return logs
    except Exception as e:
        logger.warning("Failed to retrieve sync execution logs from Redis: %s", e)
        return []


def trigger_feed_sync(feed_id: str) -> dict[str, Any]:
    """Execute an immediate manual synchronization for a specific data feed."""
    t0 = time.perf_counter()
    now_nepal = get_nepal_now()
    log_id = str(uuid.uuid4())[:8]

    status = "SUCCESS"
    message = ""
    records_processed = 0

    try:
        if feed_id == "intraday_prices":
            from apps.prices.tasks import sync_intraday_prices_task
            res = sync_intraday_prices_task()
            records_processed = res.get("created", 0) + res.get("updated", 0)
            message = f"Synchronized live intraday trades ({records_processed} updated, {res.get('skipped', 0)} unchanged)."

        elif feed_id == "market_summary":
            from apps.market.tasks import sync_market_snapshot_task
            res = sync_market_snapshot_task()
            records_processed = res.get("created", 0) + res.get("updated", 0)
            message = f"Market summary snapshot updated ({records_processed} records)."

        elif feed_id == "market_indices":
            from apps.indices.tasks import sync_indices_task
            res = sync_indices_task()
            records_processed = res.get("created", 0) + res.get("updated", 0)
            message = f"Market indices synchronized ({records_processed} updated)."

        elif feed_id == "alerts_engine":
            from apps.notifications.tasks import evaluate_alerts_task
            res = evaluate_alerts_task()
            records_processed = res.get("evaluated", 0)
            triggered = res.get("triggered", 0)
            message = f"Evaluated {records_processed} alerts ({triggered} triggered)."

        elif feed_id == "daily_prices":
            from apps.prices.tasks import sync_daily_prices_task
            res = sync_daily_prices_task()
            records_processed = res.get("created", 0) + res.get("updated", 0)
            message = f"Daily closing prices synchronized ({records_processed} records)."

        elif feed_id == "all":
            from apps.indices.tasks import sync_indices_task
            from apps.market.tasks import sync_market_snapshot_task
            from apps.notifications.tasks import evaluate_alerts_task
            from apps.prices.tasks import sync_daily_prices_task, sync_intraday_prices_task

            r1 = sync_indices_task()
            r2 = sync_market_snapshot_task()
            r3 = sync_intraday_prices_task()
            r4 = sync_daily_prices_task()
            r5 = evaluate_alerts_task()
            records_processed = (
                r1.get("created", 0)
                + r2.get("created", 0)
                + r3.get("created", 0)
                + r4.get("created", 0)
                + r5.get("evaluated", 0)
            )
            message = f"Full market synchronization completed ({records_processed} total items processed)."
        else:
            status = "FAILED"
            message = f"Unknown feed identifier: '{feed_id}'"

    except Exception as e:
        status = "FAILED"
        message = f"Sync failed: {str(e)}"
        logger.exception("Error executing manual feed sync for %s", feed_id)

    duration_ms = round((time.perf_counter() - t0) * 1000, 2)

    log_entry = {
        "id": log_id,
        "feed_id": feed_id,
        "status": status,
        "duration_ms": duration_ms,
        "records_processed": records_processed,
        "message": message,
        "timestamp": now_nepal.strftime("%H:%M:%S NPT"),
        "executed_at": now_nepal.isoformat(),
    }
    record_sync_execution_log(log_entry)
    return log_entry


def get_telegram_bot_telemetry() -> dict[str, Any]:
    """Retrieve live status and metrics for the Telegram Alert Bot."""
    from apps.notifications.telegram import get_bot_username, get_telegram_token

    token = get_telegram_token()
    username = get_bot_username()
    is_configured = bool(token)
    subscribers_count = TelegramSubscription.objects.filter(is_active=True).count()
    total_links = TelegramSubscription.objects.count()

    return {
        "is_configured": is_configured,
        "bot_username": f"@{username}" if username else "Not configured",
        "bot_url": f"https://t.me/{username}" if username else "",
        "active_subscribers": subscribers_count,
        "total_subscriptions": total_links,
        "status": "Online (Polling Active)" if is_configured else "Unconfigured",
    }


def get_system_specs() -> dict[str, Any]:
    """Compile comprehensive system specifications, sync intervals, and telemetry."""
    now_nepal = get_nepal_now()
    now_utc = datetime.now(ZoneInfo("UTC"))

    # Market state
    market_info = calculate_market_session(now_nepal)

    # Database & Redis Latencies
    db_status, db_latency = get_database_latency()
    redis_status, redis_latency = get_redis_latency()

    # Query latest records for sync telemetry
    latest_intraday = IntradayPrice.objects.order_by("-timestamp").first()
    intraday_count = IntradayPrice.objects.count()

    latest_market_snapshot = MarketSnapshot.objects.order_by("-trading_date").first()
    market_snapshot_count = MarketSnapshot.objects.count()

    latest_index_snapshot = IndexSnapshot.objects.order_by("-trading_date").first()
    index_snapshot_count = IndexSnapshot.objects.count()
    index_count = MarketIndex.objects.count()

    latest_daily_price = DailyPrice.objects.order_by("-trading_date").first()
    daily_price_count = DailyPrice.objects.count()

    active_alerts_count = Alert.objects.filter(is_active=True).count()
    total_alerts_count = Alert.objects.count()
    latest_alert_trigger = AlertHistory.objects.order_by("-triggered_at").first()
    alert_history_count = AlertHistory.objects.count()

    securities_count = Security.objects.count()
    dividends_count = Dividend.objects.count() + BonusShare.objects.count()

    # Data fetch schedules & intervals
    fetch_intervals = [
        {
            "id": "intraday_prices",
            "name": "Live Intraday Prices",
            "data_type": "LTP, Bids, Asks & Volume",
            "interval_minutes": 5,
            "interval_display": "Every 5 minutes",
            "cron_schedule": "*/5 11-15 * * 1-5",
            "trading_hours_only": True,
            "upstream_source": "NEPSE official_api (/api/npts/nepse-data/today-price)",
            "status": "Active" if market_info["is_open"] else "Standby (Market Closed)",
            "last_synced_at": (
                latest_intraday.timestamp.isoformat() if latest_intraday and latest_intraday.timestamp else None
            ),
            "total_records": intraday_count,
            "description": "Fetches real-time price changes, transaction count, and volume for all traded securities.",
        },
        {
            "id": "market_summary",
            "name": "Market Summary & Status",
            "data_type": "Macro Aggregate Turnover",
            "interval_minutes": 5,
            "interval_display": "Every 5 minutes",
            "cron_schedule": "*/5 11-15 * * 1-5",
            "trading_hours_only": True,
            "upstream_source": "NEPSE official_api (/api/npts/nepse-data/market-summary)",
            "status": "Active" if market_info["is_open"] else "Standby (Market Closed)",
            "last_synced_at": (
                str(latest_market_snapshot.trading_date) if latest_market_snapshot else None
            ),
            "total_records": market_snapshot_count,
            "description": "Total market turnover, transactions count, market capitalization, advances, and declines.",
        },
        {
            "id": "market_indices",
            "name": "Market & Sector Indices",
            "data_type": "NEPSE, Banking, Hydro, Float",
            "interval_minutes": 5,
            "interval_display": "Every 5 minutes",
            "cron_schedule": "*/5 11-15 * * 1-5",
            "trading_hours_only": True,
            "upstream_source": "NEPSE official_api (/api/npts/nepse-data/index)",
            "status": "Active" if market_info["is_open"] else "Standby (Market Closed)",
            "last_synced_at": (
                str(latest_index_snapshot.trading_date) if latest_index_snapshot else None
            ),
            "total_records": index_snapshot_count,
            "tracked_count": index_count,
            "description": "Continuous monitoring of the 18 NEPSE benchmark indices and sector averages.",
        },
        {
            "id": "alerts_engine",
            "name": "Alerts & Notification Engine",
            "data_type": "Price & Volatility Triggers",
            "interval_minutes": 2,
            "interval_display": "Every 2 minutes",
            "cron_schedule": "*/2 11-15 * * 1-5",
            "trading_hours_only": True,
            "upstream_source": "Internal Trigger Engine (evaluates against live LTP quotes)",
            "status": "Active" if market_info["is_open"] else "Standby (Market Closed)",
            "last_synced_at": (
                latest_alert_trigger.triggered_at.isoformat() if latest_alert_trigger else None
            ),
            "total_records": alert_history_count,
            "active_count": active_alerts_count,
            "total_alerts": total_alerts_count,
            "description": "Scans active price alert rules (>=, <=, % gain/loss) and sends push & web notifications.",
        },
        {
            "id": "daily_prices",
            "name": "Daily Closing Prices & OHLC",
            "data_type": "EOD Historical Candles",
            "interval_minutes": 5,
            "interval_display": "Every 5 mins & EOD Close (3:15 PM NPT)",
            "cron_schedule": "*/5 11-15 * * 1-5",
            "trading_hours_only": True,
            "upstream_source": "NEPSE official_api & Historical Archive",
            "status": "Settled",
            "last_synced_at": (
                str(latest_daily_price.trading_date) if latest_daily_price else None
            ),
            "total_records": daily_price_count,
            "description": "Final settlement OHLC, 52-week high/low, traded shares, and official closing prices.",
        },
        {
            "id": "securities_master",
            "name": "Securities Master & Sectors",
            "data_type": "Listed Companies Directory",
            "interval_minutes": 1440,
            "interval_display": "Daily / On-demand",
            "cron_schedule": "0 2 * * *",
            "trading_hours_only": False,
            "upstream_source": "NEPSE official_api & YONEPSE",
            "status": "Active",
            "last_synced_at": "Daily Bootstrap",
            "total_records": securities_count,
            "description": "Company profile directory, sector classification, ISIN, listing dates, and active flags.",
        },
        {
            "id": "corporate_actions",
            "name": "Corporate Actions & Dividends",
            "data_type": "Dividends & Bonus Shares",
            "interval_minutes": 1440,
            "interval_display": "Daily / On-demand",
            "cron_schedule": "0 3 * * *",
            "trading_hours_only": False,
            "upstream_source": "YONEPSE & NEPSE Disclosures",
            "status": "Active",
            "last_synced_at": "Daily Bootstrap",
            "total_records": dividends_count,
            "description": "Cash dividends, bonus shares, right shares, book closure dates, and fiscal year distributions.",
        },
    ]

    # Retrieve execution logs & Telegram telemetry
    execution_logs = get_sync_execution_logs(limit=15)
    telegram_telemetry = get_telegram_bot_telemetry()

    return {
        "system_time": {
            "utc": now_utc.isoformat(),
            "nepal": now_nepal.isoformat(),
            "timezone": "Asia/Kathmandu (NPT, UTC+05:45)",
            "formatted": now_nepal.strftime("%A, %d %b %Y, %I:%M:%S %p NPT"),
        },
        "market_schedule": market_info,
        "fetch_intervals": fetch_intervals,
        "telegram_bot": telegram_telemetry,
        "recent_execution_logs": execution_logs,
        "infrastructure": {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "django_version": django.get_version(),
            "database": {
                "engine": "PostgreSQL 16",
                "status": db_status,
                "latency_ms": db_latency,
            },
            "cache_broker": {
                "engine": "Redis 7.x",
                "status": redis_status,
                "latency_ms": redis_latency,
            },
            "celery": {
                "broker": "Redis (db 1)",
                "result_backend": "Redis (db 2)",
                "scheduled_tasks_count": len(getattr(settings, "CELERY_BEAT_SCHEDULE", {})),
                "timezone": getattr(settings, "CELERY_TIMEZONE", "Asia/Kathmandu"),
            },
            "frontend": {
                "framework": "Next.js 15 (App Router)",
                "bundler": "Turbopack",
                "ui": "Tailwind CSS + shadcn/ui",
                "charting": "TradingView Lightweight Charts v5 + Recharts",
            },
        },
    }

"""Telegram Bot notification client and dispatch service.

Delivers instant market and price alert notifications to connected user Telegram accounts.
"""

import html
import logging
import secrets
from typing import Any

import requests
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.notifications.models import TelegramSubscription

logger = logging.getLogger(__name__)

User = get_user_model()

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


def get_telegram_token() -> str:
    """Retrieve Telegram Bot Token from settings."""
    return getattr(settings, "TELEGRAM_BOT_TOKEN", "").strip()


def get_bot_username() -> str:
    """Retrieve Telegram Bot username from settings."""
    return getattr(settings, "TELEGRAM_BOT_USERNAME", "stock_napal_bot").strip()


def generate_verification_code() -> str:
    """Generate a secure 8-character verification token for account linking."""
    return secrets.token_hex(4).upper()


def send_telegram_raw_message(chat_id: str | int, text: str, parse_mode: str = "HTML") -> bool:
    """Send a message via Telegram HTTP Bot API.

    Returns True if successfully sent, False otherwise.
    Deactivates subscription if user blocked the bot (403 Forbidden).
    """
    token = get_telegram_token()
    if not token:
        logger.warning("[Telegram] Token not configured in settings.")
        return False

    url = f"{TELEGRAM_API_BASE}{token}/sendMessage"
    payload = {
        "chat_id": str(chat_id),
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            return True
        elif res.status_code == 403:
            logger.warning("[Telegram] Bot was blocked or chat deleted for chat_id=%s. Deactivating.", chat_id)
            TelegramSubscription.objects.filter(chat_id=str(chat_id)).update(is_active=False)
            return False
        else:
            logger.error("[Telegram] API error %d: %s", res.status_code, res.text)
            return False
    except Exception as e:
        logger.error("[Telegram] Network error sending to chat_id=%s: %s", chat_id, e)
        return False


def format_alert_message(title: str, body: str, data: dict[str, Any] | None = None) -> str:
    """Format a rich HTML market alert message for Telegram."""
    data = data or {}
    symbol = data.get("symbol", "")
    price = data.get("current_price") or data.get("price")
    target = data.get("target_price") or data.get("threshold")
    condition = data.get("condition", "")

    esc_title = html.escape(str(title))
    esc_body = html.escape(str(body))
    esc_symbol = html.escape(str(symbol))
    esc_condition = html.escape(str(condition))
    esc_price = html.escape(str(price)) if price is not None else None
    esc_target = html.escape(str(target)) if target is not None else None

    lines = [
        "🔔 <b>NEPSE MARKET ALERT</b>",
        "",
        f"<b>{esc_title}</b>",
        f"{esc_body}",
        "",
    ]

    if symbol:
        lines.append(f"• <b>Security:</b> <code>{esc_symbol}</code>")
    if price is not None:
        lines.append(f"• <b>Current Price:</b> Rs. {esc_price}")
    if target is not None:
        lines.append(f"• <b>Target Threshold:</b> Rs. {esc_target}")
    if condition:
        lines.append(f"• <b>Condition:</b> {esc_condition}")

    lines.append("")
    lines.append("⚡ <i>Delivered by NEPSE Platform</i>")
    return "\n".join(lines)


def send_telegram_alert(user: Any, title: str, body: str, data: dict[str, Any] | None = None) -> int:
    """Send an alert to all active Telegram subscriptions for a given user.

    Returns the number of successfully delivered Telegram messages.
    """
    subscriptions = TelegramSubscription.objects.filter(user=user, is_active=True)
    if not subscriptions.exists():
        return 0

    message_text = format_alert_message(title, body, data)
    delivered = 0

    for sub in subscriptions:
        success = send_telegram_raw_message(sub.chat_id, message_text)
        if success:
            delivered += 1

    return delivered


def send_test_telegram(user: Any) -> bool:
    """Send a test notification to verify user's Telegram connection."""
    subscriptions = TelegramSubscription.objects.filter(user=user, is_active=True)
    if not subscriptions.exists():
        return False

    esc_username = html.escape(str(user.username))
    text = (
        "✅ <b>NEPSE Telegram Bot Connected!</b>\n\n"
        f"Hello <b>{esc_username}</b>!\n"
        "Your Telegram account is successfully connected to the <b>NEPSE Platform</b>.\n\n"
        "You will receive instant price targets, volume alerts, and market crossing notifications here in real-time."
    )

    success_any = False
    for sub in subscriptions:
        if send_telegram_raw_message(sub.chat_id, text):
            success_any = True

    return success_any


def process_telegram_update(update: dict[str, Any]) -> dict[str, Any]:
    """Process an incoming Telegram update webhook or polling message."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"status": "ignored"}

    chat = message.get("chat", {})
    chat_id = str(chat.get("id"))
    from_user = message.get("from", {})
    username = from_user.get("username", "")
    first_name = from_user.get("first_name", "")
    text = (message.get("text") or "").strip()

    if not chat_id:
        return {"status": "error", "message": "No chat ID"}

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            code = parts[1].strip().upper()
            try:
                sub = TelegramSubscription.objects.get(verification_code=code)
                # Deactivate any other subscription previously using this chat_id
                TelegramSubscription.objects.filter(chat_id=chat_id).exclude(id=sub.id).update(is_active=False)

                sub.chat_id = chat_id
                sub.username = username
                sub.first_name = first_name
                sub.is_active = True
                sub.verification_code = ""  # Consume one-time token
                sub.save()

                welcome_text = (
                    f"🎉 <b>Welcome to NEPSE Alerts, {first_name or username}!</b>\n\n"
                    f"Your Telegram has been successfully linked to your NEPSE account (<b>{sub.user.username}</b>).\n\n"
                    "You will now receive instant push notifications whenever your stock price targets and alerts are triggered."
                )
                send_telegram_raw_message(chat_id, welcome_text)
                return {"status": "connected", "user": sub.user.username}
            except TelegramSubscription.DoesNotExist:
                send_telegram_raw_message(
                    chat_id,
                    "⚠️ <b>Invalid or expired link code.</b>\nPlease open your NEPSE web dashboard and click 'Connect Telegram' to generate a fresh link."
                )
                return {"status": "invalid_code"}
        else:
            send_telegram_raw_message(
                chat_id,
                "👋 <b>Welcome to the official NEPSE Alerts Bot!</b>\n\n"
                "To link this bot to your account, visit your NEPSE web dashboard under <b>Notifications</b> and click <b>Connect Telegram</b>."
            )
            return {"status": "welcome"}

    elif text == "/status":
        sub = TelegramSubscription.objects.filter(chat_id=chat_id, is_active=True).first()
        if sub:
            send_telegram_raw_message(
                chat_id,
                f"✅ <b>Status: Active</b>\nLinked account: <b>{sub.user.username}</b>\nNotifications: Enabled"
            )
        else:
            send_telegram_raw_message(
                chat_id,
                "❌ <b>Not Connected:</b> This chat is not linked to any active NEPSE account."
            )
        return {"status": "status_checked"}

    elif text == "/stop":
        TelegramSubscription.objects.filter(chat_id=chat_id).update(is_active=False)
        send_telegram_raw_message(
            chat_id,
            "🛑 <b>Notifications Paused.</b> You will no longer receive NEPSE alerts on this Telegram chat."
        )
        return {"status": "stopped"}

    elif text == "/help":
        send_telegram_raw_message(
            chat_id,
            "📖 <b>NEPSE Bot Commands:</b>\n\n"
            "/status - Check your account connection status\n"
            "/stop - Pause alerts on Telegram\n"
            "/help - View available commands"
        )
        return {"status": "help"}

    return {"status": "unhandled"}

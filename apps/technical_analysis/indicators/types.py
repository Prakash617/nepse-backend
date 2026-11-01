"""Data types and validation for technical analysis indicators.

Provides immutable candle structures, data validation, and conversion
helpers from Django ORM price models to numerical structures.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Candle:
    """Represents a single trading session OHLCV candle.

    All numerical fields are floats for high-performance deterministic
    vector-like mathematical calculations.
    """

    trading_date: datetime.date
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    turnover: float = 0.0

    def __post_init__(self) -> None:
        """Validate candle integrity upon initialization."""
        if self.close < 0:
            raise ValueError(f"Close price cannot be negative: {self.close}")
        if self.volume < 0:
            raise ValueError(f"Volume cannot be negative: {self.volume}")


def sanitize_and_sort_candles(
    candles: Sequence[Candle],
    *,
    min_required: int = 1,
    fill_missing_hl: bool = True,
) -> list[Candle]:
    """Validate, sanitize, and sort a sequence of candles chronologically.

    Args:
        candles: Sequence of Candle instances.
        min_required: Minimum number of candles expected.
        fill_missing_hl: If True, corrects high/low if inverted or zero
                         by bounding them with open and close.

    Returns:
        A list of clean, chronologically ascending candles.

    Raises:
        ValueError: If candles sequence has fewer than min_required items.
    """
    if len(candles) < min_required:
        return []

    # Sort chronologically ascending
    sorted_candles = sorted(candles, key=lambda c: c.trading_date)

    clean_candles: list[Candle] = []
    seen_dates: set[datetime.date] = set()

    for c in sorted_candles:
        if c.trading_date in seen_dates:
            # Skip duplicates, keeping the first occurrence
            continue
        seen_dates.add(c.trading_date)

        c_open = c.open if c.open > 0 else c.close
        c_close = c.close
        c_high = c.high
        c_low = c.low
        c_vol = max(0.0, float(c.volume))

        if fill_missing_hl:
            # Ensure high is at least max(open, close)
            # Ensure low is at most min(open, close)
            max_oc = max(c_open, c_close)
            min_oc = min(c_open, c_close)
            if c_high < max_oc or c_high <= 0:
                c_high = max_oc
            if c_low > min_oc or c_low <= 0:
                c_low = min_oc

        clean_candles.append(
            Candle(
                trading_date=c.trading_date,
                open=float(c_open),
                high=float(c_high),
                low=float(c_low),
                close=float(c_close),
                volume=c_vol,
                turnover=float(c.turnover) if c.turnover else 0.0,
            )
        )

    return clean_candles


def candles_from_records(records: Sequence[Any]) -> list[Candle]:
    """Convert Django DailyPrice / IndexSnapshot or dict objects into clean Candles.

    Safely handles Decimals, None values, and attribute/dict access.
    """
    raw_candles: list[Candle] = []

    for r in records:
        if isinstance(r, dict):
            t_date = r.get("trading_date")
            c_open = r.get("open")
            c_high = r.get("high")
            c_low = r.get("low")
            c_close = r.get("close")
            c_vol = r.get("volume") or 0.0
            c_turnover = r.get("turnover") or 0.0
        else:
            t_date = getattr(r, "trading_date", None)
            c_open = getattr(r, "open", None)
            c_high = getattr(r, "high", None)
            c_low = getattr(r, "low", None)
            c_close = getattr(r, "close", None)
            c_vol = getattr(r, "volume", 0) or 0.0
            c_turnover = getattr(r, "turnover", 0.0) or 0.0

        if t_date is None or c_close is None:
            continue

        if isinstance(t_date, str):
            t_date = datetime.date.fromisoformat(t_date)

        close_val = float(c_close)
        if close_val <= 0:
            continue

        open_val = float(c_open) if c_open is not None and float(c_open) > 0 else close_val
        high_val = float(c_high) if c_high is not None and float(c_high) > 0 else max(open_val, close_val)
        low_val = float(c_low) if c_low is not None and float(c_low) > 0 else min(open_val, close_val)
        vol_val = float(c_vol) if c_vol is not None else 0.0
        turnover_val = float(c_turnover) if c_turnover is not None else 0.0

        raw_candles.append(
            Candle(
                trading_date=t_date,
                open=open_val,
                high=high_val,
                low=low_val,
                close=close_val,
                volume=vol_val,
                turnover=turnover_val,
            )
        )

    return sanitize_and_sort_candles(raw_candles)

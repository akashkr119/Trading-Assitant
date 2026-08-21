"""Rule-based intraday setup detection.

This module identifies candidate setups only. It does not decide whether a
trade should be taken, calculate position size, or issue a final BUY/SELL
recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

from trading_assistant.indicators import ema, macd, relative_volume, supertrend, vwap


class SetupType(StrEnum):
    """V1 setup families."""

    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    BULLISH_PULLBACK = "bullish_pullback"
    BEARISH_PULLBACK = "bearish_pullback"
    EMA_BULLISH_CROSS = "ema_bullish_cross"
    EMA_BEARISH_CROSS = "ema_bearish_cross"
    VWAP_RECLAIM = "vwap_reclaim"
    VWAP_REJECTION = "vwap_rejection"
    TREND_CONTINUATION = "trend_continuation"


class SetupDirection(StrEnum):
    """Directional bias of a detected setup."""

    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass(frozen=True)
class SetupCandidate:
    """A detected setup with supporting evidence."""

    setup_type: SetupType
    direction: SetupDirection
    index: int
    confidence: float
    evidence: tuple[str, ...]
    invalidation: str


def _require_columns(frame: pd.DataFrame) -> None:
    required = {"high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    if len(frame) < 30:
        raise ValueError("at least 30 bars are required for setup detection")


def _near(value: float, reference: float, tolerance: float = 0.003) -> bool:
    return abs(value - reference) / max(abs(reference), 1e-12) <= tolerance


def detect_setups(frame: pd.DataFrame) -> list[SetupCandidate]:
    """Detect V1 candidate setups using the latest completed candle."""
    _require_columns(frame)

    close = frame["close"]
    high = frame["high"]
    low = frame["low"]
    ema9 = ema(close, 9)
    ema20 = ema(close, 20)
    macd_values = macd(close)
    vwap_values = vwap(frame)
    relative_volume_values = relative_volume(frame)
    supertrend_values = supertrend(frame)

    i = len(frame) - 1
    p = i - 1
    if any(
        pd.isna(series.iloc[i]) or pd.isna(series.iloc[p])
        for series in (ema9, ema20, vwap_values, relative_volume_values)
    ):
        return []

    latest = float(close.iloc[i])
    previous = float(close.iloc[p])
    latest_rvol = float(relative_volume_values.iloc[i])
    results: list[SetupCandidate] = []

    prior_high = float(high.iloc[i - 20 : i].max())
    prior_low = float(low.iloc[i - 20 : i].min())
    if latest > prior_high and latest_rvol >= 1.2:
        results.append(
            SetupCandidate(
                SetupType.BREAKOUT,
                SetupDirection.BULLISH,
                i,
                min(100.0, 60.0 + latest_rvol * 15.0),
                ("close above prior 20-bar high", "relative volume >= 1.2"),
                f"Close back below {prior_high:.2f}",
            )
        )
    if latest < prior_low and latest_rvol >= 1.2:
        results.append(
            SetupCandidate(
                SetupType.BREAKDOWN,
                SetupDirection.BEARISH,
                i,
                min(100.0, 60.0 + latest_rvol * 15.0),
                ("close below prior 20-bar low", "relative volume >= 1.2"),
                f"Close back above {prior_low:.2f}",
            )
        )

    if float(ema9.iloc[p]) <= float(ema20.iloc[p]) and float(ema9.iloc[i]) > float(ema20.iloc[i]):
        results.append(
            SetupCandidate(
                SetupType.EMA_BULLISH_CROSS,
                SetupDirection.BULLISH,
                i,
                65.0,
                ("EMA 9 crossed above EMA 20",),
                "EMA 9 closes back below EMA 20",
            )
        )
    if float(ema9.iloc[p]) >= float(ema20.iloc[p]) and float(ema9.iloc[i]) < float(ema20.iloc[i]):
        results.append(
            SetupCandidate(
                SetupType.EMA_BEARISH_CROSS,
                SetupDirection.BEARISH,
                i,
                65.0,
                ("EMA 9 crossed below EMA 20",),
                "EMA 9 closes back above EMA 20",
            )
        )

    latest_vwap = float(vwap_values.iloc[i])
    previous_vwap = float(vwap_values.iloc[p])
    if previous < previous_vwap and latest > latest_vwap:
        results.append(
            SetupCandidate(
                SetupType.VWAP_RECLAIM,
                SetupDirection.BULLISH,
                i,
                60.0,
                ("price crossed above VWAP",),
                "Close below VWAP",
            )
        )
    if previous > previous_vwap and latest < latest_vwap:
        results.append(
            SetupCandidate(
                SetupType.VWAP_REJECTION,
                SetupDirection.BEARISH,
                i,
                60.0,
                ("price crossed below VWAP",),
                "Close above VWAP",
            )
        )

    if (
        float(ema9.iloc[i]) > float(ema20.iloc[i])
        and float(supertrend_values["direction"].iloc[i]) == 1
        and latest >= float(ema20.iloc[i])
        and _near(latest, float(ema20.iloc[i]), 0.01)
        and latest_rvol >= 1.0
    ):
        results.append(
            SetupCandidate(
                SetupType.BULLISH_PULLBACK,
                SetupDirection.BULLISH,
                i,
                70.0,
                (
                    "EMA 9 above EMA 20",
                    "Supertrend bullish",
                    "price near EMA 20",
                    "volume >= average",
                ),
                "Close below EMA 20 or Supertrend turns bearish",
            )
        )

    if (
        float(ema9.iloc[i]) < float(ema20.iloc[i])
        and float(supertrend_values["direction"].iloc[i]) == -1
        and latest <= float(ema20.iloc[i])
        and _near(latest, float(ema20.iloc[i]), 0.01)
        and latest_rvol >= 1.0
    ):
        results.append(
            SetupCandidate(
                SetupType.BEARISH_PULLBACK,
                SetupDirection.BEARISH,
                i,
                70.0,
                (
                    "EMA 9 below EMA 20",
                    "Supertrend bearish",
                    "price near EMA 20",
                    "volume >= average",
                ),
                "Close above EMA 20 or Supertrend turns bullish",
            )
        )

    if not pd.isna(macd_values["histogram"].iloc[i]):
        current_histogram = float(macd_values["histogram"].iloc[i])
        previous_histogram = float(macd_values["histogram"].iloc[p])
        if current_histogram > 0 and previous_histogram <= 0:
            results.append(
                SetupCandidate(
                    SetupType.EMA_BULLISH_CROSS,
                    SetupDirection.BULLISH,
                    i,
                    55.0,
                    ("MACD histogram crossed above zero",),
                    "MACD histogram returns below zero",
                )
            )
        elif current_histogram < 0 and previous_histogram >= 0:
            results.append(
                SetupCandidate(
                    SetupType.EMA_BEARISH_CROSS,
                    SetupDirection.BEARISH,
                    i,
                    55.0,
                    ("MACD histogram crossed below zero",),
                    "MACD histogram returns above zero",
                )
            )

    return results

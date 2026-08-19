"""Deterministic technical indicators used by the V1 strategy engine."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def simple_moving_average(series: pd.Series, period: int) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be positive")
    return series.rolling(period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be positive")
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be positive")
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    average_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + relative_strength))
    result = result.mask((average_loss == 0) & (average_gain > 0), 100)
    return result.mask((average_gain == 0) & (average_loss > 0), 0)


def macd(
    series: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    if not (0 < fast_period < slow_period and signal_period > 0):
        raise ValueError("MACD periods must satisfy 0 < fast < slow and signal > 0")
    line = ema(series, fast_period) - ema(series, slow_period)
    signal = line.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    return pd.DataFrame({"macd": line, "signal": signal, "histogram": line - signal})


def vwap(frame: pd.DataFrame) -> pd.Series:
    _require_columns(frame, ("high", "low", "close", "volume"))
    typical_price = (frame["high"] + frame["low"] + frame["close"]) / 3
    cumulative_volume = frame["volume"].cumsum()
    return (typical_price * frame["volume"]).cumsum() / cumulative_volume.replace(0, np.nan)


def relative_volume(frame: pd.DataFrame, period: int = 20) -> pd.Series:
    _require_columns(frame, ("volume",))
    if period <= 0:
        raise ValueError("period must be positive")
    average = frame["volume"].rolling(period, min_periods=period).mean()
    return frame["volume"] / average.replace(0, np.nan)


def supertrend(
    frame: pd.DataFrame,
    period: int = 10,
    multiplier: float = 3.0,
) -> pd.DataFrame:
    """Calculate Supertrend using Wilder-style ATR smoothing."""
    _require_columns(frame, ("high", "low", "close"))
    if period <= 0 or multiplier <= 0:
        raise ValueError("period and multiplier must be positive")

    high = frame["high"]
    low = frame["low"]
    close = frame["close"]
    previous_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1
    ).max(axis=1)
    atr = true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    hl2 = (high + low) / 2
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    final_upper = upper.copy()
    final_lower = lower.copy()
    direction = pd.Series(index=frame.index, dtype="float64")
    trend = pd.Series(index=frame.index, dtype="float64")

    for i in range(len(frame)):
        if i == 0:
            direction.iloc[i] = np.nan
            trend.iloc[i] = np.nan
            continue
        if pd.isna(atr.iloc[i]):
            direction.iloc[i] = np.nan
            trend.iloc[i] = np.nan
            continue
        if close.iloc[i - 1] <= final_upper.iloc[i - 1]:
            final_upper.iloc[i] = min(upper.iloc[i], final_upper.iloc[i - 1])
        if close.iloc[i - 1] >= final_lower.iloc[i - 1]:
            final_lower.iloc[i] = max(lower.iloc[i], final_lower.iloc[i - 1])
        if close.iloc[i] > final_upper.iloc[i - 1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < final_lower.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]
        trend.iloc[i] = final_lower.iloc[i] if direction.iloc[i] == 1 else final_upper.iloc[i]

    return pd.DataFrame({"supertrend": trend, "direction": direction})

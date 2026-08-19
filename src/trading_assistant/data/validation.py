"""Validation for market-data bars before they enter the analysis pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from trading_assistant.data.interfaces import OHLCVBar


class MarketDataValidationError(ValueError):
    """Raised when market data cannot safely be analyzed."""


def validate_ohlcv(
    bars: Sequence[OHLCVBar],
    *,
    expected_interval: timedelta,
    as_of: datetime | None = None,
    max_staleness: timedelta | None = None,
) -> None:
    """Validate ordering, uniqueness, prices, intraday gaps, and freshness."""
    if not bars:
        raise MarketDataValidationError("No market data available")

    previous = None
    for bar in bars:
        if not (bar.low <= bar.open <= bar.high):
            raise MarketDataValidationError(
                f"Invalid open price at {bar.timestamp.isoformat()}"
            )
        if not (bar.low <= bar.close <= bar.high):
            raise MarketDataValidationError(
                f"Invalid close price at {bar.timestamp.isoformat()}"
            )
        if previous is not None:
            delta = bar.timestamp - previous
            if delta <= timedelta(0):
                raise MarketDataValidationError("Candle timestamps are not increasing")
            # Overnight, weekend, and holiday gaps are expected in exchange data.
            # Only reject missing candles inside the same trading date.
            if bar.timestamp.astimezone().date() == previous.astimezone().date():
                if delta > expected_interval:
                    raise MarketDataValidationError(
                        f"Candle gap detected after {previous.isoformat()}"
                    )
        previous = bar.timestamp

    if as_of is not None and max_staleness is not None:
        age = as_of - bars[-1].timestamp
        if age < timedelta(0) or age > max_staleness:
            raise MarketDataValidationError(f"Latest candle is stale: age={age}")

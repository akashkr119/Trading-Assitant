"""Provider-neutral market-data contracts.

The trading engine depends on these contracts rather than a specific broker/data vendor.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol, Sequence

from pydantic import BaseModel, Field


class Timeframe(StrEnum):
    """Supported analysis timeframes."""

    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"


class OHLCVBar(BaseModel):
    """A normalized OHLCV candle."""

    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)


class MarketDataProvider(Protocol):
    """Provider-neutral contract used by the application and strategy engine."""

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> Sequence[OHLCVBar]:
        """Return normalized OHLCV bars for a symbol and timeframe."""
        ...

    def get_latest_bar(self, symbol: str, timeframe: Timeframe) -> OHLCVBar:
        """Return the latest completed/usable candle for a symbol and timeframe."""
        ...

    def is_market_open(self) -> bool:
        """Return whether the target market is currently open for trading."""
        ...

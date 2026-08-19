"""Deterministic in-memory market data provider for tests and development."""

from __future__ import annotations

from datetime import datetime

from trading_assistant.data.interfaces import MarketDataProvider, OHLCVBar, Timeframe


class InMemoryMarketDataProvider:
    """Provider implementation used before a live vendor is selected."""

    def __init__(self, bars: dict[tuple[str, Timeframe], list[OHLCVBar]]) -> None:
        self._bars = bars

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        return [
            bar
            for bar in self._bars.get((symbol, timeframe), [])
            if start <= bar.timestamp <= end
        ]

    def get_latest_bar(self, symbol: str, timeframe: Timeframe) -> OHLCVBar:
        bars = self._bars.get((symbol, timeframe), [])
        if not bars:
            raise LookupError(f"no market data for {symbol} {timeframe.value}")
        return max(bars, key=lambda bar: bar.timestamp)

    def is_market_open(self) -> bool:
        return True


# Structural protocol check kept close to the implementation so a provider
# cannot silently drift from the application contract during refactoring.
_: MarketDataProvider = InMemoryMarketDataProvider({})

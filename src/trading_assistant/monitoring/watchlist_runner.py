"""Connect the user-selected watchlist to the one-minute monitor."""

from __future__ import annotations

from datetime import datetime

from trading_assistant.monitoring.loop import OneMinuteMonitor
from trading_assistant.monitoring.watchlist import Watchlist


class WatchlistMonitor:
    """Run analysis only for symbols explicitly selected by the user."""

    def __init__(self, watchlist: Watchlist, process_symbol) -> None:
        self.watchlist = watchlist
        self._process_symbol = process_symbol

    def process_cycle(self, timestamp: datetime) -> tuple[str, ...]:
        """Process the current user watchlist once and return processed symbols."""
        symbols = self.watchlist.symbols()
        for symbol in symbols:
            self._process_symbol(symbol, timestamp)
        return symbols

    def build_monitor(self, *, clock, sleeper=None) -> OneMinuteMonitor:
        """Create the standard one-minute scheduler over the current watchlist."""
        kwargs = {"clock": clock}
        if sleeper is not None:
            kwargs["sleeper"] = sleeper
        return OneMinuteMonitor(
            self.watchlist.symbols(),
            self._process_symbol,
            **kwargs,
        )

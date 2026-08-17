"""Top-level application service joining broker, watchlist, and dashboard state."""

from __future__ import annotations

from datetime import datetime

from trading_assistant.brokers.connection import BrokerName
from trading_assistant.brokers.facade import BrokerFacade
from trading_assistant.monitoring.dashboard import DashboardSnapshot, build_dashboard_snapshot
from trading_assistant.monitoring.watchlist import Watchlist


class TradingAssistantApplication:
    """Thin application boundary used by a CLI, Streamlit UI, or API later."""

    def __init__(self, broker: BrokerFacade) -> None:
        self.broker = broker
        self.watchlist = Watchlist()
        self._results = ()

    def connect_broker(self, broker: BrokerName, now: datetime):
        """Connect and verify a selected broker without placing orders."""
        return self.broker.connect(broker, now)

    def disconnect_broker(self):
        return self.broker.disconnect()

    def add_symbol(self, symbol: str, added_at: str) -> None:
        self.watchlist.add(symbol, added_at)

    def remove_symbol(self, symbol: str) -> bool:
        return self.watchlist.remove(symbol)

    def set_results(self, results: tuple) -> None:
        """Accept the latest analysis results for display."""
        self._results = results

    def dashboard(self, now: datetime) -> DashboardSnapshot:
        """Return the complete current UI snapshot."""
        return build_dashboard_snapshot(
            generated_at=now,
            broker=self.broker.session(now),
            watchlist=self.watchlist,
            results=self._results,
        )

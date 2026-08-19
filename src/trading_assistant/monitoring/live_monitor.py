"""Wire market data, analysis, signal dispatch, and one-minute scheduling."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

from trading_assistant.data.interfaces import MarketDataProvider
from trading_assistant.monitoring.analysis_runner import WatchlistAnalysisRunner
from trading_assistant.monitoring.loop import MonitorCycle, OneMinuteMonitor
from trading_assistant.monitoring.market_data_input import (
    AnalysisMetadata,
    MarketDataInputBuilder,
)
from trading_assistant.monitoring.signal_dispatch import SignalDispatcher


class LiveMonitor:
    """Run the complete provider-to-signal workflow on a watchlist."""

    def __init__(
        self,
        provider: MarketDataProvider,
        symbols: Sequence[str],
        metadata_loader: Callable[[str], AnalysisMetadata],
        signal_dispatcher: SignalDispatcher,
        *,
        clock: Callable[[], datetime],
        sleeper: Callable[[float], None],
        interval_seconds: int = 60,
        lookback_bars: int = 250,
    ) -> None:
        builder = MarketDataInputBuilder(
            provider,
            metadata_loader,
            lookback_bars=lookback_bars,
        )
        runner = WatchlistAnalysisRunner(builder.build, signal_dispatcher)
        self.monitor = OneMinuteMonitor(
            symbols,
            runner.process_symbol,
            interval_seconds=interval_seconds,
            clock=clock,
            sleeper=sleeper,
        )

    def run_cycle(self) -> MonitorCycle:
        """Run one market-session monitoring cycle."""
        return self.monitor.run_cycle()

    def run(self, cycles: int | None = None) -> None:
        """Run the live monitor until the requested cycle count is reached."""
        self.monitor.run(cycles=cycles)

"""Provider-neutral one-minute monitoring loop."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from time import monotonic, sleep

from trading_assistant.data.market_calendar import is_regular_session


@dataclass(frozen=True)
class MonitorCycle:
    started_at: datetime
    symbols: tuple[str, ...]
    processed: int
    skipped_market_closed: bool = False


class OneMinuteMonitor:
    """Run a monitoring callback at one-minute boundaries.

    The callback owns market-data retrieval and analysis. This keeps scheduling
    independent from the provider and trading strategy implementation.
    """

    def __init__(
        self,
        symbols: Sequence[str],
        process_symbol: Callable[[str, datetime], None],
        *,
        interval_seconds: int = 60,
        clock: Callable[[], datetime],
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.symbols = tuple(symbols)
        self.process_symbol = process_symbol
        self.interval_seconds = interval_seconds
        self.clock = clock
        self.sleeper = sleeper

    def run_cycle(self) -> MonitorCycle:
        """Process the selected symbols once when the regular market is open."""
        now = self.clock()
        if not is_regular_session(now):
            return MonitorCycle(now, self.symbols, 0, skipped_market_closed=True)

        for symbol in self.symbols:
            self.process_symbol(symbol, now)
        return MonitorCycle(now, self.symbols, len(self.symbols))

    def run(self, cycles: int | None = None) -> None:
        """Run cycles at a one-minute cadence until ``cycles`` is reached."""
        completed = 0
        next_run = monotonic()
        while cycles is None or completed < cycles:
            self.run_cycle()
            completed += 1
            next_run += self.interval_seconds
            self.sleeper(max(0.0, next_run - monotonic()))

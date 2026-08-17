"""Execute stock analysis for each selected symbol in a monitor cycle."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from trading_assistant.analysis.pipeline import (
    StockAnalysisInput,
    analyze_stock,
)
from trading_assistant.monitoring.signal_dispatch import SignalDispatcher


class WatchlistAnalysisRunner:
    """Bridge watchlist scheduling with the analysis and signal pipeline."""

    def __init__(
        self,
        input_builder: Callable[[str, datetime], StockAnalysisInput],
        signal_dispatcher: SignalDispatcher,
    ) -> None:
        self.input_builder = input_builder
        self.signal_dispatcher = signal_dispatcher

    def process_symbol(self, symbol: str, timestamp: datetime) -> None:
        """Build fresh analysis input, run analysis, and dispatch any signal."""
        inputs = self.input_builder(symbol, timestamp)
        result = analyze_stock(inputs)
        if result is not None:
            self.signal_dispatcher.process(result, timestamp)

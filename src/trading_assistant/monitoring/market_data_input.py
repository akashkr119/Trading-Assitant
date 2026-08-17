"""Build analysis inputs from a provider-neutral market-data source."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from trading_assistant.analysis.pipeline import StockAnalysisInput
from trading_assistant.analysis.timeframe import TimeframeTrend
from trading_assistant.data.interfaces import MarketDataProvider, Timeframe
from trading_assistant.data.validation import validate_ohlcv


@dataclass(frozen=True)
class AnalysisMetadata:
    """Non-market inputs required by the stock analysis pipeline."""

    sector: str
    market_score: float
    sector_score: float
    stock_score: float
    confirmation_score: float
    timeframe_trends: tuple[TimeframeTrend, ...]
    stop_loss: float
    target_1: float
    target_2: float


class MarketDataInputBuilder:
    """Convert provider candles plus strategy metadata into analysis input."""

    def __init__(
        self,
        provider: MarketDataProvider,
        metadata_loader: Callable[[str, datetime], AnalysisMetadata],
        lookback_bars: int = 250,
    ) -> None:
        if lookback_bars < 1:
            raise ValueError("lookback_bars must be positive")
        self.provider = provider
        self.metadata_loader = metadata_loader
        self.lookback_bars = lookback_bars

    def build(self, symbol: str, timestamp: datetime) -> StockAnalysisInput:
        """Fetch, validate, and assemble one complete analysis input."""
        metadata = self.metadata_loader(symbol, timestamp)
        bars = self.provider.get_ohlcv(
            symbol,
            Timeframe.ONE_MINUTE,
            timestamp - pd.Timedelta(minutes=self.lookback_bars),
            timestamp,
        )
        bars = list(bars[-self.lookback_bars :])
        minimum_bars = min(self.lookback_bars, 30)
        if len(bars) < minimum_bars:
            raise ValueError(
                f"Insufficient market data for {symbol}: "
                f"expected at least {minimum_bars}, got {len(bars)}"
            )
        validate_ohlcv(
            bars,
            expected_interval=pd.Timedelta(minutes=1).to_pytimedelta(),
            as_of=timestamp,
            max_staleness=pd.Timedelta(minutes=2).to_pytimedelta(),
        )

        frame = pd.DataFrame(
            [
                {
                    "timestamp": bar.timestamp,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in bars
            ]
        )
        entry = float(frame["close"].iloc[-1])
        return StockAnalysisInput(
            symbol=symbol,
            sector=metadata.sector,
            frame=frame,
            market_score=metadata.market_score,
            sector_score=metadata.sector_score,
            stock_score=metadata.stock_score,
            confirmation_score=metadata.confirmation_score,
            timeframe_trends=metadata.timeframe_trends,
            entry=entry,
            stop_loss=metadata.stop_loss,
            target_1=metadata.target_1,
            target_2=metadata.target_2,
        )

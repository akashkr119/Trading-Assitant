"""Build analysis inputs from a provider-neutral market-data source."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pandas as pd

from trading_assistant.analysis.pipeline import StockAnalysisInput
from trading_assistant.analysis.timeframe import TimeframeTrend
from trading_assistant.data.interfaces import MarketDataProvider, Timeframe


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
        metadata_loader: Callable[[str], AnalysisMetadata],
        lookback_bars: int = 250,
    ) -> None:
        if lookback_bars < 1:
            raise ValueError("lookback_bars must be positive")
        self.provider = provider
        self.metadata_loader = metadata_loader
        self.lookback_bars = lookback_bars

    def build(self, symbol: str, timestamp: datetime) -> StockAnalysisInput:
        """Fetch fresh candles and assemble one complete analysis input."""
        metadata = self.metadata_loader(symbol)
        bars = self.provider.get_ohlcv(
            symbol,
            Timeframe.ONE_MINUTE,
            timestamp - pd.Timedelta(minutes=self.lookback_bars),
            timestamp,
        )
        if len(bars) < self.lookback_bars:
            raise ValueError(
                f"Insufficient market data for {symbol}: "
                f"expected {self.lookback_bars}, got {len(bars)}"
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
                for bar in bars[-self.lookback_bars :]
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

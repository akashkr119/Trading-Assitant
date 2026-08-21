"""Live technical-analysis service used by the V1 dashboard."""

# isort: skip_file

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

import pandas as pd

from trading_assistant.analysis.pipeline import StockAnalysisResult, analyze_stock
from trading_assistant.analysis.timeframe import TimeframeTrend
from trading_assistant.data.interfaces import MarketDataProvider, OHLCVBar, Timeframe
from trading_assistant.data.reliability import RetryPolicy, with_retry
from trading_assistant.indicators import ema, macd, relative_volume, rsi, supertrend
from trading_assistant.monitoring.market_data_input import (
    AnalysisMetadata,
    MarketDataInputBuilder,
)
from trading_assistant.monitoring.signal_dispatch import SignalDispatcher


_TIMEFRAME_LOOKBACKS = {
    Timeframe.ONE_MINUTE: 250,
    Timeframe.FIVE_MINUTES: 100,
    Timeframe.FIFTEEN_MINUTES: 60,
    Timeframe.ONE_HOUR: 40,
}


class TechnicalMetadataLoader:
    """Build technical metadata from broker candles for the selected timeframe."""

    def __init__(
        self,
        provider: MarketDataProvider,
        analysis_timeframe: Timeframe = Timeframe.ONE_MINUTE,
    ) -> None:
        self.provider = provider
        self.analysis_timeframe = analysis_timeframe

    def load(self, symbol: str, timestamp: datetime) -> AnalysisMetadata:
        primary_bars = self._bars(symbol, self.analysis_timeframe, timestamp)
        frame = self._frame(primary_bars)
        close = frame["close"]
        ema9_values = ema(close, 9)
        ema20_values = ema(close, 20)
        rsi_values = rsi(close, 14)
        macd_values = macd(close)
        supertrend_values = supertrend(frame)
        relative_volume_values = relative_volume(frame)

        latest_close = float(close.iloc[-1])
        ema9_value = float(ema9_values.iloc[-1])
        ema20_value = float(ema20_values.iloc[-1])
        rsi_value = float(rsi_values.iloc[-1])
        macd_histogram = float(macd_values["histogram"].iloc[-1])
        supertrend_direction = float(supertrend_values["direction"].iloc[-1])
        relative_volume_value = float(relative_volume_values.iloc[-1])

        bullish = latest_close >= ema20_value
        ema_aligned = (ema9_value >= ema20_value) == bullish
        supertrend_aligned = (supertrend_direction > 0) == bullish
        macd_aligned = (macd_histogram >= 0) == bullish
        volume_confirmed = relative_volume_value >= 0.8
        rsi_confirmed = (
            45.0 <= rsi_value <= 80.0
            if bullish
            else 20.0 <= rsi_value <= 55.0
        )

        stock_score = 50.0
        stock_score += 10.0 if ema_aligned else 0.0
        stock_score += 10.0 if supertrend_aligned else 0.0
        stock_score += 10.0 if macd_aligned else 0.0
        stock_score += 10.0 if volume_confirmed else 0.0
        stock_score += 10.0 if rsi_confirmed else 0.0

        confirmation_frame = frame
        if self.analysis_timeframe != Timeframe.ONE_MINUTE:
            one_minute = self._bars(symbol, Timeframe.ONE_MINUTE, timestamp)
            confirmation_frame = self._frame(one_minute)
        confirmation_supertrend = supertrend(confirmation_frame)
        confirmation_macd = macd(confirmation_frame)["histogram"]
        confirmation_rvol = relative_volume(confirmation_frame)
        confirmation_bullish = float(confirmation_frame["close"].iloc[-1]) >= float(
            ema(confirmation_frame["close"], 20).iloc[-1]
        )
        confirmation_supertrend_aligned = (
            float(confirmation_supertrend["direction"].iloc[-1]) > 0
        ) == confirmation_bullish
        confirmation_macd_aligned = (
            float(confirmation_macd.iloc[-1]) >= 0
        ) == confirmation_bullish
        confirmation_score = 50.0
        confirmation_score += 15.0 if confirmation_supertrend_aligned else 0.0
        confirmation_score += 15.0 if confirmation_macd_aligned else 0.0
        confirmation_score += 20.0 if float(confirmation_rvol.iloc[-1]) >= 1.2 else 0.0

        entry = latest_close
        recent = frame.tail(20)
        if bullish:
            stop_loss = min(float(recent["low"].min()), entry * 0.995)
            risk = max(entry - stop_loss, entry * 0.005)
            target_1 = entry + 1.5 * risk
            target_2 = entry + 3.0 * risk
        else:
            stop_loss = max(float(recent["high"].max()), entry * 1.005)
            risk = max(stop_loss - entry, entry * 0.005)
            target_1 = entry - 1.5 * risk
            target_2 = entry - 3.0 * risk

        trends = tuple(
            self._trend(symbol, timeframe, timestamp)
            for timeframe in (
                Timeframe.ONE_HOUR,
                Timeframe.FIFTEEN_MINUTES,
                Timeframe.FIVE_MINUTES,
                Timeframe.ONE_MINUTE,
            )
        )
        return AnalysisMetadata(
            sector="Technical-only mode",
            market_score=50.0,
            sector_score=50.0,
            stock_score=min(stock_score, 100.0),
            confirmation_score=min(confirmation_score, 100.0),
            timeframe_trends=trends,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            analysis_timeframe=self.analysis_timeframe,
        )

    def _bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        timestamp: datetime,
    ) -> list[OHLCVBar]:
        lookback = _TIMEFRAME_LOOKBACKS[timeframe]
        minutes = lookback * {
            Timeframe.ONE_MINUTE: 1,
            Timeframe.FIVE_MINUTES: 5,
            Timeframe.FIFTEEN_MINUTES: 15,
            Timeframe.ONE_HOUR: 60,
        }[timeframe]
        start = timestamp - timedelta(minutes=minutes)
        bars = with_retry(
            lambda: self.provider.get_ohlcv(symbol, timeframe, start, timestamp),
            policy=RetryPolicy(attempts=2, initial_delay_seconds=0.25),
            sleeper=lambda _: None,
        )
        if len(bars) < min(lookback, 30):
            raise ValueError(
                f"Insufficient {timeframe.value} data for {symbol}: "
                f"expected at least {min(lookback, 30)}, got {len(bars)}"
            )
        return list(bars[-lookback:])

    @staticmethod
    def _frame(bars: Sequence[OHLCVBar]) -> pd.DataFrame:
        return pd.DataFrame(
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

    def _trend(
        self,
        symbol: str,
        timeframe: Timeframe,
        timestamp: datetime,
    ) -> TimeframeTrend:
        bars = self._bars(symbol, timeframe, timestamp)
        frame = self._frame(bars)
        close = frame["close"]
        if len(close) < 20:
            direction = "neutral"
        else:
            direction = (
                "bullish"
                if close.iloc[-1] >= ema(close, 20).iloc[-1]
                else "bearish"
            )
        return TimeframeTrend(timeframe=timeframe.value, direction=direction)


class LiveAnalysisService:
    """Analyze the active watchlist and optionally dispatch changed alerts."""

    def __init__(
        self,
        provider: MarketDataProvider,
        signal_dispatcher: SignalDispatcher | None = None,
        analysis_timeframe: Timeframe = Timeframe.FIVE_MINUTES,
    ) -> None:
        self.builder = MarketDataInputBuilder(
            provider,
            TechnicalMetadataLoader(provider, analysis_timeframe).load,
            lookback_bars=_TIMEFRAME_LOOKBACKS[analysis_timeframe],
        )
        self.signal_dispatcher = signal_dispatcher
        self.errors: dict[str, str] = {}

    def analyze(
        self,
        symbols: Sequence[str],
        timestamp: datetime,
    ) -> tuple[StockAnalysisResult, ...]:
        """Analyze each symbol independently and retain failures for the UI."""
        results: list[StockAnalysisResult] = []
        self.errors = {}
        for symbol in symbols:
            try:
                inputs = self.builder.build(symbol, timestamp)
                result = analyze_stock(inputs)
                if result is not None:
                    results.append(result)
                    if self.signal_dispatcher is not None:
                        self.signal_dispatcher.process(result, timestamp)
            except Exception as error:
                self.errors[symbol] = str(error)
        return tuple(results)

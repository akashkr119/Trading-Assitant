"""Intraday crypto scanner with explainable long/short ranking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from trading_assistant.data.interfaces import MarketDataProvider, OHLCVBar, Timeframe
from trading_assistant.indicators import ema, macd, relative_volume, rsi, supertrend


CRYPTO_UNIVERSE = (
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "LTCUSDT",
    "TRXUSDT",
)


@dataclass(frozen=True)
class CryptoCandidate:
    """A ranked crypto intraday opportunity."""

    symbol: str
    direction: str
    score: float
    price: float
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward: float
    reason: str


class CryptoIntradayScanner:
    """Rank liquid crypto pairs using 5m momentum and 15m confirmation."""

    def __init__(
        self,
        provider: MarketDataProvider,
        universe: tuple[str, ...] = CRYPTO_UNIVERSE,
    ) -> None:
        self.provider = provider
        self.universe = universe
        self.last_scan_count = 0
        self.last_qualified_count = 0
        self.last_scan_errors: dict[str, str] = {}

    def scan(
        self,
        timestamp: datetime,
        limit: int = 10,
    ) -> tuple[CryptoCandidate, ...]:
        candidates: list[CryptoCandidate] = []
        self.last_scan_errors = {}
        self.last_scan_count = len(self.universe)
        start = timestamp - timedelta(days=3)
        for symbol in self.universe:
            try:
                bars_5m = self.provider.get_ohlcv(
                    symbol, Timeframe.FIVE_MINUTES, start, timestamp
                )
                bars_15m = self.provider.get_ohlcv(
                    symbol, Timeframe.FIFTEEN_MINUTES, start, timestamp
                )
                if len(bars_5m) < 60 or len(bars_15m) < 40:
                    self.last_scan_errors[symbol] = "Insufficient candles"
                    continue
                candidate = self._score(symbol, list(bars_5m), list(bars_15m))
                if candidate is not None:
                    candidates.append(candidate)
            except Exception as error:
                self.last_scan_errors[symbol] = str(error)

        candidates.sort(key=lambda item: item.score, reverse=True)
        self.last_qualified_count = len(candidates)
        return tuple(candidates[:limit])

    @staticmethod
    def _score(
        symbol: str,
        bars_5m: list[OHLCVBar],
        bars_15m: list[OHLCVBar],
    ) -> CryptoCandidate | None:
        frame_5m = pd.DataFrame(
            {
                "high": [bar.high for bar in bars_5m],
                "low": [bar.low for bar in bars_5m],
                "close": [bar.close for bar in bars_5m],
                "volume": [bar.volume for bar in bars_5m],
            }
        )
        frame_15m = pd.DataFrame(
            {
                "high": [bar.high for bar in bars_15m],
                "low": [bar.low for bar in bars_15m],
                "close": [bar.close for bar in bars_15m],
                "volume": [bar.volume for bar in bars_15m],
            }
        )
        close = frame_5m["close"]
        latest = float(close.iloc[-1])
        ema9 = float(ema(close, 9).iloc[-1])
        ema20 = float(ema(close, 20).iloc[-1])
        rsi_value = float(rsi(close, 14).iloc[-1])
        macd_histogram = float(macd(close)["histogram"].iloc[-1])
        rvol = float(relative_volume(frame_5m).iloc[-1])
        trend_5m = float(supertrend(frame_5m)["direction"].iloc[-1])
        close_15m = frame_15m["close"]
        trend_15m = float(supertrend(frame_15m)["direction"].iloc[-1])

        bullish = ema9 > ema20 and macd_histogram > 0 and trend_5m > 0 and trend_15m > 0
        bearish = ema9 < ema20 and macd_histogram < 0 and trend_5m < 0 and trend_15m < 0
        if not bullish and not bearish:
            return None
        if bullish and not 50 <= rsi_value <= 75:
            return None
        if bearish and not 25 <= rsi_value <= 50:
            return None

        direction = "LONG" if bullish else "SHORT"
        score = 60.0
        score += 15.0 if rvol >= 1.2 else 0.0
        score += 10.0 if 55 <= rsi_value <= 70 if bullish else 30 <= rsi_value <= 45 else 0.0
        score += 15.0

        recent_range = frame_5m["high"].iloc[-20:] - frame_5m["low"].iloc[-20:]
        risk = max(float(recent_range.median()), latest * 0.002)
        if bullish:
            entry = latest
            stop = entry - risk
            target_1 = entry + risk * 2
            target_2 = entry + risk * 4
        else:
            entry = latest
            stop = entry + risk
            target_1 = entry - risk * 2
            target_2 = entry - risk * 4

        reason = (
            f"5m EMA9/20 {'bullish' if bullish else 'bearish'}, "
            f"15m Supertrend aligned, MACD {'positive' if bullish else 'negative'}, "
            f"RSI {rsi_value:.1f}, RVOL {rvol:.2f}x"
        )
        return CryptoCandidate(
            symbol=symbol,
            direction=direction,
            score=min(score, 100.0),
            price=latest,
            entry=entry,
            stop_loss=stop,
            target_1=target_1,
            target_2=target_2,
            risk_reward=4.0,
            reason=reason,
        )

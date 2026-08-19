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


@dataclass(frozen=True)
class CryptoMarketSnapshot:
    """Detailed market state for a user-selected crypto pair."""

    symbol: str
    timestamp: datetime
    price: float
    ema9: float
    ema20: float
    rsi: float
    macd_histogram: float
    relative_volume: float
    supertrend_direction: str
    support_levels: tuple[float, ...]
    resistance_levels: tuple[float, ...]
    alert: str
    alert_reason: str
    candidate: CryptoCandidate | None


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

    def analyze_symbol(
        self,
        symbol: str,
        timestamp: datetime,
    ) -> CryptoMarketSnapshot:
        """Build the detailed dashboard view for a selected crypto pair."""
        start = timestamp - timedelta(days=3)
        bars_5m = list(
            self.provider.get_ohlcv(
                symbol, Timeframe.FIVE_MINUTES, start, timestamp
            )
        )
        bars_15m = list(
            self.provider.get_ohlcv(
                symbol, Timeframe.FIFTEEN_MINUTES, start, timestamp
            )
        )
        if len(bars_5m) < 60 or len(bars_15m) < 40:
            raise ValueError("Insufficient candles for selected crypto pair")

        frame_5m = self._frame(bars_5m)
        frame_15m = self._frame(bars_15m)
        close = frame_5m["close"]
        price = float(close.iloc[-1])
        ema9 = float(ema(close, 9).iloc[-1])
        ema20 = float(ema(close, 20).iloc[-1])
        rsi_value = float(rsi(close, 14).iloc[-1])
        macd_histogram = float(macd(close)["histogram"].iloc[-1])
        rvol = float(relative_volume(frame_5m).iloc[-1])
        trend_5m = self._trend_direction(frame_5m)
        trend_15m = self._trend_direction(frame_15m)
        candidate = self._score(symbol, bars_5m, bars_15m)
        if candidate is not None:
            alert = "BUY ALERT" if candidate.direction == "LONG" else "SELL ALERT"
            alert_reason = candidate.reason
        else:
            alert = "WATCH"
            alert_reason = self._watch_reason(
                ema9, ema20, rsi_value, macd_histogram, trend_5m, trend_15m
            )

        supports, resistances = self._support_resistance(frame_5m, price)
        return CryptoMarketSnapshot(
            symbol=symbol,
            timestamp=timestamp,
            price=price,
            ema9=ema9,
            ema20=ema20,
            rsi=rsi_value,
            macd_histogram=macd_histogram,
            relative_volume=rvol,
            supertrend_direction="BULLISH" if trend_5m > 0 else "BEARISH",
            support_levels=supports,
            resistance_levels=resistances,
            alert=alert,
            alert_reason=alert_reason,
            candidate=candidate,
        )

    @staticmethod
    def _frame(bars: list[OHLCVBar]) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "high": [bar.high for bar in bars],
                "low": [bar.low for bar in bars],
                "close": [bar.close for bar in bars],
                "volume": [bar.volume for bar in bars],
            }
        )

    @staticmethod
    def _trend_direction(frame: pd.DataFrame) -> float:
        """Return Supertrend direction, with an EMA fallback during warm-up."""
        direction = float(supertrend(frame)["direction"].iloc[-1])
        if pd.notna(direction):
            return direction
        close = float(frame["close"].iloc[-1])
        ema20 = float(ema(frame["close"], 20).iloc[-1])
        return 1.0 if close > ema20 else -1.0

    @staticmethod
    def _support_resistance(
        frame: pd.DataFrame,
        price: float,
    ) -> tuple[tuple[float, ...], tuple[float, ...]]:
        """Return up to three nearest confirmed swing supports/resistances."""
        highs = frame["high"].to_numpy()
        lows = frame["low"].to_numpy()
        resistance: list[float] = []
        support: list[float] = []
        for index in range(1, len(frame) - 1):
            if highs[index] >= highs[index - 1] and highs[index] > highs[index + 1]:
                level = float(highs[index])
                if level > price:
                    resistance.append(level)
            if lows[index] <= lows[index - 1] and lows[index] < lows[index + 1]:
                level = float(lows[index])
                if level < price:
                    support.append(level)

        def unique_nearby(levels: list[float]) -> tuple[float, ...]:
            selected: list[float] = []
            for level in sorted(levels, key=lambda value: abs(value - price)):
                if not any(abs(level - item) / price < 0.002 for item in selected):
                    selected.append(level)
                if len(selected) == 3:
                    break
            return tuple(sorted(selected))

        return unique_nearby(support), unique_nearby(resistance)

    @staticmethod
    def _watch_reason(
        ema9: float,
        ema20: float,
        rsi_value: float,
        macd_histogram: float,
        trend_5m: float,
        trend_15m: float,
    ) -> str:
        reasons: list[str] = []
        if ema9 <= ema20:
            reasons.append("EMA9 is not above EMA20")
        if ema9 >= ema20:
            reasons.append("EMA9 is not below EMA20")
        if macd_histogram == 0:
            reasons.append("MACD is neutral")
        if trend_5m != trend_15m:
            reasons.append("5m and 15m trend are not aligned")
        if not reasons:
            reasons.append(f"RSI {rsi_value:.1f} is outside the entry zone")
        return "; ".join(reasons)

    @staticmethod
    def _score(
        symbol: str,
        bars_5m: list[OHLCVBar],
        bars_15m: list[OHLCVBar],
    ) -> CryptoCandidate | None:
        frame_5m = CryptoIntradayScanner._frame(bars_5m)
        frame_15m = CryptoIntradayScanner._frame(bars_15m)
        close = frame_5m["close"]
        latest = float(close.iloc[-1])
        ema9 = float(ema(close, 9).iloc[-1])
        ema20 = float(ema(close, 20).iloc[-1])
        rsi_value = float(rsi(close, 14).iloc[-1])
        macd_histogram = float(macd(close)["histogram"].iloc[-1])
        rvol = float(relative_volume(frame_5m).iloc[-1])
        trend_5m = CryptoIntradayScanner._trend_direction(frame_5m)
        trend_15m = CryptoIntradayScanner._trend_direction(frame_15m)

        bullish = (
            ema9 > ema20
            and macd_histogram > 0
            and trend_5m > 0
            and trend_15m > 0
        )
        bearish = (
            ema9 < ema20
            and macd_histogram < 0
            and trend_5m < 0
            and trend_15m < 0
        )
        if not bullish and not bearish:
            return None
        if bullish and not 50 <= rsi_value <= 75:
            return None
        if bearish and not 25 <= rsi_value <= 50:
            return None

        direction = "LONG" if bullish else "SHORT"
        score = 75.0
        if rvol >= 1.2:
            score += 10.0
        if bullish and 55 <= rsi_value <= 70:
            score += 5.0
        if bearish and 30 <= rsi_value <= 45:
            score += 5.0
        score += 10.0

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

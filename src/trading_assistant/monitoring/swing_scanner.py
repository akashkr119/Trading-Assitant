"""Daily-candle scanner for long swing-trading candidates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from trading_assistant.data.interfaces import MarketDataProvider, OHLCVBar, Timeframe
from trading_assistant.data.reliability import RetryPolicy, with_retry
from trading_assistant.indicators import ema, macd, relative_volume, rsi
from trading_assistant.monitoring.cap_universe import SWING_UNIVERSE, current_cap_classification


@dataclass(frozen=True)
class SwingCandidate:
    """A ranked long setup for a multi-day holding period."""

    symbol: str
    direction: str
    score: float
    price: float
    change_20d_pct: float
    stop_loss: float
    target_1: float
    target_2: float
    holding_period: str
    reason: str
    cap_segment: str = "Unclassified"


class SwingScanner:
    """Rank NSE stocks using daily trend, momentum and volume."""

    def __init__(
        self,
        provider: MarketDataProvider,
        universe: tuple[str, ...] = SWING_UNIVERSE,
    ) -> None:
        self.provider = provider
        self.universe = universe
        self.last_scan_errors: dict[str, str] = {}
        self.last_scan_count = 0
        self.last_qualified_count = 0
        self.cap_source = "AMFI"
        try:
            classification = current_cap_classification()
            self.symbol_to_cap = {
                symbol: item.segment
                for symbol, item in classification.items()
                if symbol in self.universe
            }
        except Exception as error:
            self.symbol_to_cap = {}
            self.cap_source = f"AMFI unavailable: {error}"

    def scan(
        self,
        timestamp: datetime,
        limit: int = 10,
    ) -> tuple[SwingCandidate, ...]:
        """Return up to ``limit`` candidates per current AMFI cap segment."""
        candidates: list[SwingCandidate] = []
        errors: dict[str, str] = {}
        start = timestamp - timedelta(days=420)

        for symbol in self.universe:
            try:
                bars = with_retry(
                    lambda symbol=symbol: self.provider.get_ohlcv(
                        symbol,
                        Timeframe.ONE_DAY,
                        start,
                        timestamp,
                    ),
                    policy=RetryPolicy(attempts=2, initial_delay_seconds=0.1),
                    sleeper=lambda _: None,
                )
                usable_bars = list(bars)
                if self.provider.is_market_open() and len(usable_bars) > 1:
                    usable_bars = usable_bars[:-1]
                if len(usable_bars) < 200:
                    errors[symbol] = (
                        f"Only {len(usable_bars)} daily candles returned; "
                        "at least 200 are required."
                    )
                    continue
                candidate = self._score(symbol, usable_bars)
                if candidate is not None:
                    candidates.append(candidate)
            except Exception as error:
                errors[symbol] = str(error)

        candidates.sort(key=lambda item: item.score, reverse=True)
        segments = ("Large Cap", "Mid Cap", "Small Cap")
        categorized = any(item.cap_segment in segments for item in candidates)
        if categorized:
            selected: list[SwingCandidate] = []
            for segment in segments:
                segment_candidates = [
                    item for item in candidates if item.cap_segment == segment
                ]
                selected.extend(segment_candidates[:limit])
        else:
            selected = candidates[:limit]

        self.last_scan_errors = errors
        self.last_scan_count = len(self.universe)
        self.last_qualified_count = len(candidates)
        return tuple(selected)

    def _score(self, symbol: str, bars: list[OHLCVBar]) -> SwingCandidate:
        frame = pd.DataFrame(
            {
                "close": [bar.close for bar in bars],
                "high": [bar.high for bar in bars],
                "low": [bar.low for bar in bars],
                "volume": [bar.volume for bar in bars],
            }
        )
        close = frame["close"]
        latest = float(close.iloc[-1])
        ema20 = float(ema(close, 20).iloc[-1])
        ema50 = float(ema(close, 50).iloc[-1])
        ema200 = float(ema(close, 200).iloc[-1])
        rsi_value = float(rsi(close, 14).iloc[-1])
        macd_histogram = float(macd(close)["histogram"].iloc[-1])
        rvol = float(relative_volume(frame).iloc[-1])
        previous_20_high = float(frame["high"].iloc[-21:-1].max())
        change_20d_pct = (latest / float(close.iloc[-21]) - 1.0) * 100.0

        trend = latest > ema20 > ema50 > ema200
        momentum = macd_histogram > 0 and 50.0 <= rsi_value <= 72.0
        volume = rvol >= 1.0
        breakout = latest >= previous_20_high

        score = 45.0
        score += 20.0 if trend else 0.0
        score += 15.0 if momentum else 0.0
        score += 10.0 if volume else 0.0
        score += 10.0 if breakout else 0.0

        recent_low = float(frame["low"].tail(20).min())
        risk = max(latest - recent_low, latest * 0.03)
        stop_loss = latest - risk
        target_1 = latest + 1.5 * risk
        target_2 = latest + 3.0 * risk

        direction = "BUY" if trend and score >= 70.0 else "WATCH"
        reasons = [
            "daily trend aligned" if trend else "trend not fully aligned",
            "MACD momentum positive" if macd_histogram > 0 else "MACD momentum negative",
            f"RSI {rsi_value:.1f}",
            f"volume {rvol:.2f}x average",
        ]
        if breakout:
            reasons.append("20-day breakout")
        if self.cap_source != "AMFI":
            reasons.append("market-cap classification unavailable")

        return SwingCandidate(
            symbol=symbol,
            direction=direction,
            score=min(score, 100.0),
            price=latest,
            change_20d_pct=change_20d_pct,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            holding_period="2–8 weeks",
            reason=", ".join(reasons),
            cap_segment=self.symbol_to_cap.get(symbol, "Unclassified"),
        )

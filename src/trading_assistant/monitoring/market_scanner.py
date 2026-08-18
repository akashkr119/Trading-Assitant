"""Market scanner that ranks candidate NSE stocks before detailed analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from trading_assistant.data.interfaces import MarketDataProvider, OHLCVBar, Timeframe
from trading_assistant.data.reliability import RetryPolicy, with_retry
from trading_assistant.indicators import ema, macd, relative_volume, rsi


# A stable liquid universe for V1. The universe is deliberately limited so a
# broker's historical-data quota is not exhausted during intraday scanning.
NIFTY50_UNIVERSE = (
    "ADANIENT",
    "ADANIPORTS",
    "APOLLOHOSP",
    "ASIANPAINT",
    "AXISBANK",
    "BAJAJ-AUTO",
    "BAJFINANCE",
    "BAJAJFINSV",
    "BEL",
    "BHARTIARTL",
    "CIPLA",
    "COALINDIA",
    "DRREDDY",
    "EICHERMOT",
    "ETERNAL",
    "GRASIM",
    "HCLTECH",
    "HDFCBANK",
    "HDFCLIFE",
    "HEROMOTOCO",
    "HINDALCO",
    "HINDUNILVR",
    "ICICIBANK",
    "INDUSINDBK",
    "INFY",
    "ITC",
    "JIOFIN",
    "JSWSTEEL",
    "KOTAKBANK",
    "LT",
    "M&M",
    "MARUTI",
    "MAXHEALTH",
    "NESTLEIND",
    "NTPC",
    "ONGC",
    "POWERGRID",
    "RELIANCE",
    "SBILIFE",
    "SBIN",
    "SHRIRAMFIN",
    "SUNPHARMA",
    "TATACONSUM",
    "TATAMOTORS",
    "TATASTEEL",
    "TCS",
    "TECHM",
    "TITAN",
    "TRENT",
    "ULTRACEMCO",
    "WIPRO",
)


@dataclass(frozen=True)
class ScanCandidate:
    """A ranked candidate awaiting detailed multi-timeframe analysis."""

    symbol: str
    direction: str
    score: float
    price: float
    change_pct: float
    relative_volume: float
    reason: str


class MarketScanner:
    """Rank a bounded liquid universe using cheap 5-minute technical signals."""

    def __init__(
        self,
        provider: MarketDataProvider,
        universe: tuple[str, ...] = NIFTY50_UNIVERSE,
    ) -> None:
        self.provider = provider
        self.universe = universe

    def scan(
        self,
        timestamp: datetime,
        limit: int = 10,
    ) -> tuple[ScanCandidate, ...]:
        candidates: list[ScanCandidate] = []
        start = timestamp - timedelta(minutes=5 * 80)
        for symbol in self.universe:
            try:
                bars = with_retry(
                    lambda symbol=symbol: self.provider.get_ohlcv(
                        symbol,
                        Timeframe.FIVE_MINUTES,
                        start,
                        timestamp,
                    ),
                    policy=RetryPolicy(attempts=2, initial_delay_seconds=0.1),
                    sleeper=lambda _: None,
                )
                if len(bars) < 30:
                    continue
                candidate = self._score(symbol, list(bars))
                if candidate is not None:
                    candidates.append(candidate)
            except Exception:
                # One unavailable symbol must not prevent the market scan.
                continue

        candidates.sort(key=lambda item: item.score, reverse=True)
        return tuple(candidates[:limit])

    @staticmethod
    def _score(symbol: str, bars: list[OHLCVBar]) -> ScanCandidate | None:
        frame = pd.DataFrame(
            {
                "close": [bar.close for bar in bars],
                "volume": [bar.volume for bar in bars],
            }
        )
        close = frame["close"]
        latest = float(close.iloc[-1])
        previous = float(close.iloc[-6])
        change_pct = (latest / previous - 1.0) * 100.0
        ema9_value = float(ema(close, 9).iloc[-1])
        ema20_value = float(ema(close, 20).iloc[-1])
        rsi_value = float(rsi(close, 14).iloc[-1])
        macd_histogram = float(macd(close)["histogram"].iloc[-1])
        relative_volume_value = float(relative_volume(frame).iloc[-1])

        bullish = ema9_value >= ema20_value
        direction = "BUY" if bullish else "SELL"
        score = 50.0
        score += 15.0 if bullish == (change_pct >= 0) else 0.0
        score += 15.0 if bullish == (macd_histogram >= 0) else 0.0
        score += 10.0 if relative_volume_value >= 1.0 else 0.0
        score += 10.0 if (
            45.0 <= rsi_value <= 75.0 if bullish else 25.0 <= rsi_value <= 55.0
        ) else 0.0

        reason = (
            f"EMA {'bullish' if bullish else 'bearish'}, "
            f"MACD {'positive' if macd_histogram >= 0 else 'negative'}, "
            f"RVOL {relative_volume_value:.2f}x, RSI {rsi_value:.1f}"
        )
        return ScanCandidate(
            symbol=symbol,
            direction=direction,
            score=min(score, 100.0),
            price=latest,
            change_pct=change_pct,
            relative_volume=relative_volume_value,
            reason=reason,
        )

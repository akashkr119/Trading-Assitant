"""Market scanner that ranks current NSE movers before detailed analysis."""

# isort: skip_file

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from time import monotonic
from urllib.request import Request, urlopen

import pandas as pd

from trading_assistant.data.interfaces import MarketDataProvider, OHLCVBar, Timeframe
from trading_assistant.data.reliability import RetryPolicy, with_retry
from trading_assistant.indicators import ema, macd, relative_volume, rsi
from trading_assistant.monitoring.sector_scanner import symbol_sector


_FALLBACK_UNIVERSE = (
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL",
    "INFY", "ITC", "LT", "AXISBANK", "BAJFINANCE", "KOTAKBANK", "MARUTI",
    "M&M", "SUNPHARMA", "HCLTECH", "TITAN", "TATAMOTORS", "TATASTEEL", "TRENT",
    "ADANIENT", "ADANIPORTS", "BEL", "NTPC", "POWERGRID", "ONGC", "WIPRO",
    "HINDUNILVR", "ULTRACEMCO", "NESTLEIND", "HINDALCO", "JSWSTEEL", "COALINDIA",
    "CIPLA", "DRREDDY", "EICHERMOT", "HEROMOTOCO", "HDFCLIFE", "SBILIFE",
    "SHRIRAMFIN", "JIOFIN", "GRASIM", "TATACONSUM", "TECHM", "APOLLOHOSP",
    "MAXHEALTH", "ASIANPAINT", "ETERNAL", "BAJAJFINSV", "INDUSINDBK",
)
_NSE_ACTIVE_URL = "https://www.nseindia.com/api/live-analysis-most-active-securities?index={}"


@dataclass(frozen=True)
class ScanCandidate:
    """A ranked candidate with market bias awaiting detailed trade analysis."""

    symbol: str
    direction: str
    score: float
    price: float
    change_pct: float
    relative_volume: float
    reason: str
    sector: str = "Other"



def _nse_active_symbols(activity: str, limit: int = 40) -> tuple[str, ...]:
    """Read the current most-active equity symbols from NSE."""
    request = Request(
        _NSE_ACTIVE_URL.format(activity),
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/market-data/most-active-equities",
        },
    )
    with urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    symbols: list[str] = []
    for item in payload.get("data", []):
        symbol = str(item.get("symbol", "")).strip().upper()
        if symbol and symbol.replace("&", "").replace("-", "").isalnum() and symbol not in symbols:
            symbols.append(symbol)
        if len(symbols) >= limit:
            break
    return tuple(symbols)


class MarketScanner:
    """Rank current market movers using live NSE discovery plus broker candles."""

    def __init__(
        self,
        provider: MarketDataProvider,
        universe: tuple[str, ...] | None = None,
    ) -> None:
        self.provider = provider
        self.universe = universe
        self.last_scan_errors: dict[str, str] = {}
        self.last_scan_count = 0
        self.last_data_count = 0
        self.last_qualified_count = 0
        self.last_universe_source = "not loaded"
        self._cached_universe: tuple[str, ...] = ()
        self._universe_loaded_at = 0.0

    def _resolve_universe(self) -> tuple[str, ...]:
        if self.universe is not None:
            self.last_universe_source = "configured"
            return self.universe
        if self._cached_universe and monotonic() - self._universe_loaded_at < 60:
            return self._cached_universe

        try:
            by_volume = _nse_active_symbols("volume")
            by_value = _nse_active_symbols("value")
            merged = list(dict.fromkeys((*by_volume, *by_value)))
            if merged:
                self._cached_universe = tuple(merged[:60])
                self._universe_loaded_at = monotonic()
                self.last_universe_source = "NSE most-active"
                return self._cached_universe
        except Exception as error:
            self.last_scan_errors["__universe__"] = str(error)

        self.last_universe_source = "fallback"
        return _FALLBACK_UNIVERSE

    def scan(
        self,
        timestamp: datetime,
        limit: int = 10,
    ) -> tuple[ScanCandidate, ...]:
        """Rank the stocks actually moving in the current market."""
        candidates: list[ScanCandidate] = []
        errors: dict[str, str] = dict(self.last_scan_errors)
        universe = self._resolve_universe()
        self.last_scan_count = len(universe)
        self.last_data_count = 0
        self.last_qualified_count = 0

        start = timestamp - timedelta(days=7)
        for symbol in universe:
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
                    errors[symbol] = f"Only {len(bars)} five-minute candles returned"
                    continue
                self.last_data_count += 1
                candidate = self._score(symbol, list(bars))
                if candidate is not None:
                    candidates.append(candidate)
            except Exception as error:
                errors[symbol] = str(error)

        candidates.sort(key=lambda item: item.score, reverse=True)
        self.last_scan_errors = errors
        self.last_qualified_count = len(candidates)
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

        bullish_votes = sum(
            (
                ema9_value > ema20_value,
                change_pct > 0,
                macd_histogram > 0,
                rsi_value >= 50,
            )
        )
        bearish_votes = sum(
            (
                ema9_value < ema20_value,
                change_pct < 0,
                macd_histogram < 0,
                rsi_value < 50,
            )
        )
        bullish = bullish_votes >= bearish_votes
        bias = "BULLISH" if bullish else "BEARISH"
        directional_votes = bullish_votes if bullish else bearish_votes
        momentum = min(abs(change_pct) / 1.5, 1.0) * 15.0
        volume_points = min(relative_volume_value / 2.0, 1.0) * 20.0
        score = 35.0 + directional_votes * 10.0 + momentum + volume_points
        score = min(score, 100.0)

        reason = (
            f"Market bias: {bias}. "
            f"EMA {'bullish' if bullish else 'bearish'}, "
            f"MACD {'positive' if macd_histogram > 0 else 'negative'}, "
            f"RSI {rsi_value:.1f}, RVOL {relative_volume_value:.2f}x, "
            f"5m move {change_pct:+.2f}%. "
            "Formal BUY/SELL requires live trade confirmation."
        )
        return ScanCandidate(
            symbol=symbol,
            direction=bias,
            score=round(score, 1),
            price=latest,
            change_pct=change_pct,
            relative_volume=relative_volume_value,
            reason=reason,
            sector=symbol_sector(symbol),
        )

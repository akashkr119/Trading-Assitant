"""Upstox V3 market-data adapter for Indian equities."""

# isort: skip_file

from __future__ import annotations

import gzip
import json
from datetime import datetime
from typing import ClassVar
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from trading_assistant.data.interfaces import MarketDataProvider, OHLCVBar, Timeframe


IST = ZoneInfo("Asia/Kolkata")


class UpstoxDataError(RuntimeError):
    """Raised when the Upstox market-data API cannot provide data."""


_INTERVALS = {
    Timeframe.ONE_MINUTE: ("minutes", "1"),
    Timeframe.FIVE_MINUTES: ("minutes", "5"),
    Timeframe.FIFTEEN_MINUTES: ("minutes", "15"),
    Timeframe.ONE_HOUR: ("hours", "1"),
    Timeframe.ONE_DAY: ("days", "1"),
}

_INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"


class UpstoxMarketDataProvider(MarketDataProvider):
    """Fetch normalized candles from the authenticated Upstox V3 API."""

    _instrument_cache: ClassVar[dict[str, str] | None] = None

    def __init__(
        self,
        access_token: str,
        instrument_keys: dict[str, str] | None = None,
        *,
        base_url: str = "https://api.upstox.com/v3",
        timeout_seconds: float = 10.0,
    ) -> None:
        if not access_token.strip():
            raise ValueError("access_token cannot be empty")
        self.access_token = access_token
        self.instrument_keys = {
            symbol.strip().upper(): key
            for symbol, key in (instrument_keys or {}).items()
        }
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        """Fetch candles for a date range using the V3 historical endpoint."""
        if start.date() > end.date():
            raise ValueError("start must not be after end")
        unit, interval = _INTERVALS[timeframe]
        instrument_key = self._instrument_key(symbol)
        path = (
            f"/historical-candle/{quote(instrument_key, safe='')}/"
            f"{unit}/{interval}/{end.date()}/{start.date()}"
        )
        return self._parse_candles(self._request(path))

    def get_latest_bar(self, symbol: str, timeframe: Timeframe) -> OHLCVBar:
        """Fetch the latest available candle."""
        instrument_key = self._instrument_key(symbol)
        if timeframe == Timeframe.ONE_DAY:
            unit, interval = _INTERVALS[timeframe]
            end = datetime.now(IST).date()
            path = (
                f"/historical-candle/{quote(instrument_key, safe='')}/"
                f"{unit}/{interval}/{end}"
            )
        else:
            unit, interval = _INTERVALS[timeframe]
            path = (
                f"/historical-candle/intraday/{quote(instrument_key, safe='')}/"
                f"{unit}/{interval}"
            )
        candles = self._parse_candles(self._request(path))
        if not candles:
            raise UpstoxDataError(f"No candles returned for {symbol}")
        return candles[-1]

    def is_market_open(self) -> bool:
        """Return NSE-equity session state in India Standard Time."""
        now = datetime.now(IST)
        current = (now.hour, now.minute)
        return now.weekday() < 5 and (9, 15) <= current < (15, 30)

    def _instrument_key(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if normalized in self.instrument_keys:
            return self.instrument_keys[normalized]
        keys = self._load_instrument_keys()
        try:
            return keys[normalized]
        except KeyError as error:
            raise UpstoxDataError(
                f"No NSE equity instrument key found for {normalized}"
            ) from error

    @classmethod
    def _load_instrument_keys(cls) -> dict[str, str]:
        if cls._instrument_cache is not None:
            return cls._instrument_cache
        request = Request(
            _INSTRUMENTS_URL,
            headers={"Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=20.0) as response:
                payload = gzip.decompress(response.read())
            instruments = json.loads(payload)
        except Exception as error:
            raise UpstoxDataError(
                f"Unable to load Upstox NSE instrument master: {error}"
            ) from error
        cls._instrument_cache = {
            str(item["trading_symbol"]).strip().upper(): str(item["instrument_key"])
            for item in instruments
            if item.get("segment") == "NSE_EQ"
            and item.get("instrument_type") == "EQ"
            and item.get("trading_symbol")
            and item.get("instrument_key")
        }
        return cls._instrument_cache

    def _request(self, path: str) -> dict:
        request = Request(
            f"{self.base_url}{path}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except Exception as error:
            raise UpstoxDataError(f"Upstox request failed: {error}") from error
        if payload.get("status") != "success":
            raise UpstoxDataError(f"Upstox API returned an error: {payload}")
        return payload

    @staticmethod
    def _parse_candles(payload: dict) -> list[OHLCVBar]:
        candles = payload.get("data", {}).get("candles", [])
        return [
            OHLCVBar(
                timestamp=datetime.fromisoformat(candle[0]),
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=float(candle[5]),
            )
            for candle in reversed(candles)
        ]

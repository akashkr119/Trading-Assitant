"""Public crypto market-data adapter using Binance spot klines."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from trading_assistant.data.interfaces import MarketDataProvider, OHLCVBar, Timeframe


class CryptoDataError(RuntimeError):
    """Raised when the crypto market-data API cannot provide data."""


_INTERVALS = {
    Timeframe.ONE_MINUTE: "1m",
    Timeframe.FIVE_MINUTES: "5m",
    Timeframe.FIFTEEN_MINUTES: "15m",
    Timeframe.ONE_HOUR: "1h",
    Timeframe.ONE_DAY: "1d",
}


class BinanceMarketDataProvider(MarketDataProvider):
    """Fetch public spot candles without requiring a trading API key."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.binance.com/api/v3",
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        if start > end:
            raise ValueError("start must not be after end")
        interval = _INTERVALS[timeframe]
        query = urlencode(
            {
                "symbol": symbol.strip().upper(),
                "interval": interval,
                "startTime": self._epoch_ms(start),
                "endTime": self._epoch_ms(end),
                "limit": 1000,
            }
        )
        payload = self._request(f"/klines?{query}")
        if not isinstance(payload, list):
            raise CryptoDataError(f"Unexpected Binance response: {payload}")
        return self._parse(payload)

    def get_latest_bar(self, symbol: str, timeframe: Timeframe) -> OHLCVBar:
        query = urlencode(
            {
                "symbol": symbol.strip().upper(),
                "interval": _INTERVALS[timeframe],
                "limit": 2,
            }
        )
        payload = self._request(f"/klines?{query}")
        candles = self._parse(payload)
        if not candles:
            raise CryptoDataError(f"No candles returned for {symbol}")
        return candles[-1]

    def is_market_open(self) -> bool:
        return True

    @staticmethod
    def _epoch_ms(value: datetime) -> int:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp() * 1000)

    def _request(self, path: str):
        request = Request(
            f"{self.base_url}{path}",
            headers={
                "Accept": "application/json",
                "User-Agent": "TradingAssistant/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except Exception as error:
            raise CryptoDataError(f"Crypto market-data request failed: {error}") from error
        return payload

    @staticmethod
    def _parse(payload: list) -> list[OHLCVBar]:
        return [
            OHLCVBar(
                timestamp=datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc),
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=float(candle[5]),
            )
            for candle in payload
        ]

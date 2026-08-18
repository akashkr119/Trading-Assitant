"""Groww market-data adapter using the current historical/live APIs."""

# isort: skip_file

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from trading_assistant.data.interfaces import MarketDataProvider, OHLCVBar, Timeframe


IST = ZoneInfo("Asia/Kolkata")


class GrowwDataError(RuntimeError):
    """Raised when Groww market data cannot be retrieved or parsed."""


_INTERVALS = {
    Timeframe.ONE_MINUTE: "1minute",
    Timeframe.FIVE_MINUTES: "5minute",
    Timeframe.FIFTEEN_MINUTES: "15minute",
    Timeframe.ONE_HOUR: "1hour",
    Timeframe.ONE_DAY: "1day",
}


class GrowwMarketDataProvider(MarketDataProvider):
    """Fetch normalized NSE cash candles from Groww."""

    def __init__(
        self,
        access_token: str,
        *,
        base_url: str = "https://api.groww.in/v1",
        timeout_seconds: float = 10.0,
    ) -> None:
        if not access_token.strip():
            raise ValueError("access_token cannot be empty")
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        """Fetch historical candles for an NSE cash instrument."""
        if start > end:
            raise ValueError("start must not be after end")
        params = {
            "exchange": "NSE",
            "segment": "CASH",
            "groww_symbol": f"NSE-{symbol.strip().upper()}",
            "start_time": self._format_time(start),
            "end_time": self._format_time(end),
            "candle_interval": _INTERVALS[timeframe],
        }
        payload = self._request("/historical/candles", params)
        return self._parse_candles(payload)

    def get_latest_bar(self, symbol: str, timeframe: Timeframe) -> OHLCVBar:
        """Fetch the latest completed candle using a short historical window."""
        end = datetime.now(timezone.utc)
        if timeframe == Timeframe.ONE_DAY:
            start = end - timedelta(days=7)
        else:
            start = end.replace(second=0, microsecond=0)
            start = start - timedelta(minutes=10)
        candles = self.get_ohlcv(symbol, timeframe, start, end)
        if not candles:
            raise GrowwDataError(f"No candles returned for {symbol}")
        return candles[-1]

    def is_market_open(self) -> bool:
        """Return NSE cash-market session state in India Standard Time."""
        now = datetime.now(IST)
        current = (now.hour, now.minute)
        return now.weekday() < 5 and (9, 15) <= current < (15, 30)

    def _request(self, path: str, params: dict[str, str]) -> dict:
        url = f"{self.base_url}{path}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
                "X-API-VERSION": "1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except Exception as error:
            raise GrowwDataError(f"Groww request failed: {error}") from error
        if payload.get("status") not in {"SUCCESS", "success"}:
            raise GrowwDataError(f"Groww API returned an error: {payload}")
        return payload

    @staticmethod
    def _format_time(value: datetime) -> str:
        return value.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _parse_candles(payload: dict) -> list[OHLCVBar]:
        candles = payload.get("payload", {}).get("candles", [])
        result: list[OHLCVBar] = []
        for candle in candles:
            timestamp = datetime.fromtimestamp(float(candle[0]), tz=timezone.utc)
            result.append(
                OHLCVBar(
                    timestamp=timestamp,
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5]),
                )
            )
        return result

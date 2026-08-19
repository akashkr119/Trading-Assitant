from datetime import datetime, timezone

import pytest

from trading_assistant.data.groww import GrowwDataError, GrowwMarketDataProvider
from trading_assistant.data.interfaces import Timeframe


def test_historical_request_normalizes_groww_candles(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GrowwMarketDataProvider("token")
    payload = {
        "status": "SUCCESS",
        "payload": {
            "candles": [[
                1776339900,
                100.0,
                102.0,
                99.5,
                101.5,
                1200,
            ]]
        },
    }

    monkeypatch.setattr(provider, "_request", lambda path, params: payload)

    result = provider.get_ohlcv(
        "RELIANCE",
        Timeframe.ONE_MINUTE,
        datetime(2026, 4, 15, 9, 15),
        datetime(2026, 4, 15, 9, 16),
    )

    assert result[0].open == 100.0
    assert result[0].close == 101.5
    assert result[0].volume == 1200
    assert result[0].timestamp.tzinfo == timezone.utc


def test_empty_latest_data_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GrowwMarketDataProvider("token")
    monkeypatch.setattr(provider, "get_ohlcv", lambda *args: [])

    with pytest.raises(GrowwDataError, match="No candles returned"):
        provider.get_latest_bar("RELIANCE", Timeframe.ONE_MINUTE)


def test_provider_rejects_empty_token() -> None:
    with pytest.raises(ValueError, match="access_token cannot be empty"):
        GrowwMarketDataProvider(" ")

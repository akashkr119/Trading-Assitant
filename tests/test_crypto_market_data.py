from datetime import datetime, timezone

from trading_assistant.data.crypto import BinanceMarketDataProvider
from trading_assistant.data.interfaces import Timeframe


def test_crypto_provider_parses_klines() -> None:
    payload = [
        [1700000000000, "100", "105", "99", "103", "500", 0, 0, 0, 0, 0, 0],
        [1700000300000, "103", "108", "102", "107", "700", 0, 0, 0, 0, 0, 0],
    ]
    bars = BinanceMarketDataProvider._parse(payload)

    assert len(bars) == 2
    assert bars[0].open == 100
    assert bars[1].close == 107
    assert bars[1].timestamp == datetime.fromtimestamp(1700000300, tz=timezone.utc)


def test_crypto_provider_is_always_open() -> None:
    provider = BinanceMarketDataProvider()

    assert provider.is_market_open()
    assert Timeframe.FIVE_MINUTES.value == "5m"

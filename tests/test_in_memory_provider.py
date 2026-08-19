from datetime import datetime, timedelta

from trading_assistant.data.interfaces import OHLCVBar, Timeframe
from trading_assistant.data.providers.in_memory import InMemoryMarketDataProvider


def test_in_memory_provider_returns_latest_and_range_data() -> None:
    start = datetime(2026, 8, 17, 10, 0)
    bars = [
        OHLCVBar(
            timestamp=start + timedelta(minutes=index),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100.5 + index,
            volume=1000 + index,
        )
        for index in range(3)
    ]
    provider = InMemoryMarketDataProvider({("RELIANCE", Timeframe.ONE_MINUTE): bars})

    result = provider.get_ohlcv(
        "RELIANCE", Timeframe.ONE_MINUTE, start + timedelta(minutes=1), start + timedelta(minutes=2)
    )

    assert len(result) == 2
    assert provider.get_latest_bar("RELIANCE", Timeframe.ONE_MINUTE) == bars[-1]


def test_missing_latest_bar_raises() -> None:
    provider = InMemoryMarketDataProvider({})

    try:
        provider.get_latest_bar("TCS", Timeframe.ONE_MINUTE)
    except LookupError as error:
        assert "TCS" in str(error)
    else:
        raise AssertionError("expected LookupError")

from datetime import datetime

from trading_assistant.data.interfaces import OHLCVBar, Timeframe
from trading_assistant.data.market_calendar import IST, is_regular_session


def test_ohlcv_bar_validates_positive_prices() -> None:
    bar = OHLCVBar(
        timestamp=datetime(2026, 8, 17, 9, 16, tzinfo=IST),
        open=100,
        high=101,
        low=99,
        close=100.5,
        volume=1200,
    )
    assert bar.close == 100.5
    assert Timeframe.ONE_MINUTE.value == "1m"


def test_regular_session_uses_indian_market_hours() -> None:
    assert is_regular_session(datetime(2026, 8, 17, 10, 0, tzinfo=IST))
    assert not is_regular_session(datetime(2026, 8, 17, 16, 0, tzinfo=IST))
    assert not is_regular_session(datetime(2026, 8, 16, 10, 0, tzinfo=IST))

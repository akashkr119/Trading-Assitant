from datetime import datetime, timedelta

import pytest

from trading_assistant.data.interfaces import OHLCVBar
from trading_assistant.data.validation import MarketDataValidationError, validate_ohlcv


def bar(timestamp: datetime, close: float = 100.0) -> OHLCVBar:
    return OHLCVBar(
        timestamp=timestamp,
        open=99.0,
        high=max(101.0, close),
        low=min(98.0, close),
        close=close,
        volume=1000,
    )


def test_valid_bars_pass_validation() -> None:
    start = datetime(2026, 8, 18, 10, 0)
    validate_ohlcv(
        [bar(start), bar(start + timedelta(minutes=1))],
        expected_interval=timedelta(minutes=1),
    )


def test_duplicate_or_out_of_order_timestamp_is_rejected() -> None:
    start = datetime(2026, 8, 18, 10, 0)
    with pytest.raises(MarketDataValidationError, match="not increasing"):
        validate_ohlcv(
            [bar(start), bar(start)],
            expected_interval=timedelta(minutes=1),
        )


def test_same_day_candle_gap_is_rejected() -> None:
    start = datetime(2026, 8, 18, 10, 0)
    with pytest.raises(MarketDataValidationError, match="gap"):
        validate_ohlcv(
            [bar(start), bar(start + timedelta(minutes=3))],
            expected_interval=timedelta(minutes=1),
        )


def test_overnight_gap_is_allowed() -> None:
    first = datetime(2026, 8, 18, 15, 29)
    next_day = datetime(2026, 8, 19, 9, 15)
    validate_ohlcv(
        [bar(first), bar(next_day)],
        expected_interval=timedelta(minutes=1),
    )


def test_stale_latest_candle_is_rejected() -> None:
    start = datetime(2026, 8, 18, 10, 0)
    with pytest.raises(MarketDataValidationError, match="stale"):
        validate_ohlcv(
            [bar(start)],
            expected_interval=timedelta(minutes=1),
            as_of=start + timedelta(minutes=5),
            max_staleness=timedelta(minutes=2),
        )

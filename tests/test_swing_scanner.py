from datetime import datetime, timedelta

from trading_assistant.data.interfaces import OHLCVBar, Timeframe
from trading_assistant.monitoring.swing_scanner import SwingScanner


class FakeProvider:
    def get_ohlcv(self, symbol, timeframe, start, end):
        base = datetime(2025, 8, 1)
        return [
            OHLCVBar(
                timestamp=base + timedelta(days=index),
                open=100 + index * 0.5,
                high=100.4 + index * 0.5,
                low=99.8 + index * 0.5,
                close=100.2 + index * 0.5,
                volume=1000 + index * 8,
            )
            for index in range(260)
        ]

    def get_latest_bar(self, symbol, timeframe):
        raise NotImplementedError

    def is_market_open(self):
        return False


def test_swing_scanner_returns_long_candidate() -> None:
    scanner = SwingScanner(FakeProvider(), universe=("AAA",))

    result = scanner.scan(datetime(2026, 8, 18), limit=1)

    assert len(result) == 1
    assert result[0].symbol == "AAA"
    assert result[0].direction == "BUY"
    assert result[0].score >= 70.0
    assert result[0].target_1 > result[0].price > result[0].stop_loss
    assert result[0].holding_period == "2–8 weeks"
    assert Timeframe.ONE_DAY.value == "1d"

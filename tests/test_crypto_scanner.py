from datetime import datetime, timedelta, timezone

from trading_assistant.data.interfaces import OHLCVBar, Timeframe
from trading_assistant.monitoring.crypto_scanner import CryptoIntradayScanner


class FakeCryptoProvider:
    def __init__(self, bars: list[OHLCVBar]) -> None:
        self.bars = bars

    def get_ohlcv(self, symbol, timeframe, start, end):
        return self.bars

    def get_latest_bar(self, symbol, timeframe):
        return self.bars[-1]

    def is_market_open(self):
        return True


def _bars(count: int) -> list[OHLCVBar]:
    start = datetime(2026, 8, 19, tzinfo=timezone.utc)
    return [
        OHLCVBar(
            timestamp=start + timedelta(minutes=5 * index),
            open=100 + index,
            high=102 + index,
            low=99 + index,
            close=101 + index,
            volume=1000 + index * 10,
        )
        for index in range(count)
    ]


def test_crypto_scanner_sets_four_to_one_reward_risk() -> None:
    bars = _bars(80)
    scanner = CryptoIntradayScanner(
        FakeCryptoProvider(bars),
        universe=("BTCUSDT",),
    )

    results = scanner.scan(bars[-1].timestamp, limit=1)

    assert results
    result = results[0]
    assert result.direction == "LONG"
    assert result.risk_reward == 4.0
    assert result.target_2 > result.entry > result.stop_loss
    assert result.target_1 > result.entry

from datetime import datetime, timedelta, timezone

import pandas as pd

from trading_assistant.data.interfaces import OHLCVBar
from trading_assistant.monitoring import crypto_scanner
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
    bars: list[OHLCVBar] = []
    price = 100.0
    for index in range(count):
        close = price + 0.5
        bars.append(
            OHLCVBar(
                timestamp=start + timedelta(minutes=5 * index),
                open=price,
                high=close + 0.2,
                low=price - 0.2,
                close=close,
                volume=1000,
            )
        )
        price = close
    return bars


def test_crypto_scanner_sets_four_to_one_reward_risk(monkeypatch) -> None:
    bars = _bars(120)
    index = pd.RangeIndex(len(bars))

    monkeypatch.setattr(
        crypto_scanner,
        "ema",
        lambda series, period: pd.Series(
            101.0 if period == 9 else 100.0, index=index
        ),
    )
    monkeypatch.setattr(
        crypto_scanner,
        "rsi",
        lambda series, period: pd.Series(60.0, index=index),
    )
    monkeypatch.setattr(
        crypto_scanner,
        "macd",
        lambda series: pd.DataFrame({"histogram": pd.Series(1.0, index=index)}),
    )
    monkeypatch.setattr(
        crypto_scanner,
        "relative_volume",
        lambda frame: pd.Series(1.5, index=frame.index),
    )
    monkeypatch.setattr(
        crypto_scanner,
        "supertrend",
        lambda frame: pd.DataFrame({"direction": pd.Series(1.0, index=frame.index)}),
    )

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

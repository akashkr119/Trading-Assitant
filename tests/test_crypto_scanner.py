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
        close = price + (0.7 if index % 4 else 0.35)
        high = max(price, close) + 0.25
        low = min(price, close) - 0.25
        bars.append(
            OHLCVBar(
                timestamp=start + timedelta(minutes=5 * index),
                open=price,
                high=high,
                low=low,
                close=close,
                volume=1000,
            )
        )
        price = close
    return bars


def test_crypto_scanner_sets_four_to_one_reward_risk(monkeypatch) -> None:
    bars = _bars(120)
    ema9 = pd.Series([101.0] * 120)
    ema20 = pd.Series([100.0] * 120)

    def fake_ema(values, period):
        return ema9 if period == 9 else ema20

    monkeypatch.setattr(crypto_scanner, "ema", fake_ema)
    monkeypatch.setattr(
        crypto_scanner,
        "rsi",
        lambda values, period: pd.Series([60.0] * len(values)),
    )
    monkeypatch.setattr(
        crypto_scanner,
        "macd",
        lambda values: pd.DataFrame({"histogram": [1.0] * len(values)}),
    )
    monkeypatch.setattr(
        crypto_scanner,
        "relative_volume",
        lambda frame: pd.Series([1.5] * len(frame)),
    )
    monkeypatch.setattr(
        crypto_scanner,
        "supertrend",
        lambda frame: pd.DataFrame({"direction": [1.0] * len(frame)}),
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

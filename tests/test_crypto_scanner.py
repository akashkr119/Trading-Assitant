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


def _patch_indicators(monkeypatch) -> None:
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


def test_crypto_scanner_sets_four_to_one_reward_risk(monkeypatch) -> None:
    bars = _bars(120)
    _patch_indicators(monkeypatch)
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


def test_selected_crypto_detail_has_alert_and_indicator_snapshot(monkeypatch) -> None:
    bars = _bars(120)
    _patch_indicators(monkeypatch)
    scanner = CryptoIntradayScanner(
        FakeCryptoProvider(bars),
        universe=("BTCUSDT",),
    )

    snapshot = scanner.analyze_symbol("BTCUSDT", bars[-1].timestamp)

    assert snapshot.symbol == "BTCUSDT"
    assert snapshot.alert == "BUY ALERT"
    assert snapshot.price == bars[-1].close
    assert snapshot.ema9 == 101.0
    assert snapshot.ema20 == 100.0
    assert snapshot.rsi == 60.0
    assert snapshot.relative_volume == 1.5
    assert snapshot.candidate is not None


def test_support_resistance_returns_at_most_three_levels() -> None:
    frame = pd.DataFrame(
        {
            "high": [99, 105, 101, 108, 102, 111, 103, 115, 104, 120],
            "low": [95, 98, 96, 99, 97, 100, 98, 101, 99, 102],
            "close": [98, 100, 99, 102, 100, 104, 101, 106, 102, 110],
            "volume": [1000] * 10,
        }
    )

    supports, resistances = CryptoIntradayScanner._support_resistance(frame, 110.0)

    assert len(supports) <= 3
    assert len(resistances) <= 3
    assert all(level < 110 for level in supports)
    assert all(level > 110 for level in resistances)

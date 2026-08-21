from datetime import datetime, timedelta

from trading_assistant.data.interfaces import OHLCVBar
from trading_assistant.monitoring import market_scanner
from trading_assistant.monitoring.market_scanner import MarketScanner


class FakeProvider:
    def get_ohlcv(self, symbol, timeframe, start, end):
        base = datetime(2026, 8, 18, 9, 15)
        return [
            OHLCVBar(
                timestamp=base + timedelta(minutes=5 * index),
                open=100 + index * 0.2,
                high=100.3 + index * 0.2,
                low=99.8 + index * 0.2,
                close=100.1 + index * 0.2,
                volume=1000 + index * 10,
            )
            for index in range(80)
        ]

    def get_latest_bar(self, symbol, timeframe):
        raise NotImplementedError

    def is_market_open(self):
        return True


def test_market_scanner_returns_ranked_candidates() -> None:
    scanner = MarketScanner(FakeProvider(), universe=("AAA", "BBB"))

    result = scanner.scan(datetime(2026, 8, 18, 10, 0), limit=1)

    assert len(result) == 1
    assert result[0].symbol == "AAA"
    assert result[0].direction == "BULLISH"
    assert result[0].score >= 50.0
    assert result[0].price > 100.0


def test_market_scanner_uses_live_nse_universe(monkeypatch) -> None:
    calls = []

    def fake_active(activity, limit=40):
        calls.append(activity)
        return ("AAA", "BBB")

    monkeypatch.setattr(market_scanner, "_nse_active_symbols", fake_active)
    scanner = MarketScanner(FakeProvider())

    result = scanner.scan(datetime(2026, 8, 18, 10, 0), limit=2)

    assert {item.symbol for item in result} == {"AAA", "BBB"}
    assert calls == ["volume", "value"]
    assert scanner.last_universe_source == "NSE most-active"

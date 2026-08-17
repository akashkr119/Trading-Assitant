from datetime import datetime

from trading_assistant.analysis.timeframe import TimeframeTrend
from trading_assistant.data.interfaces import OHLCVBar, Timeframe
from trading_assistant.monitoring.live_monitor import LiveMonitor
from trading_assistant.monitoring.market_data_input import AnalysisMetadata


class FakeProvider:
    def __init__(self, bars: list[OHLCVBar]) -> None:
        self.bars = bars

    def get_ohlcv(self, symbol, timeframe, start, end):
        assert symbol == "RELIANCE"
        assert timeframe == Timeframe.ONE_MINUTE
        return self.bars

    def get_latest_bar(self, symbol, timeframe):
        return self.bars[-1]

    def is_market_open(self):
        return True


class RecordingDispatcher:
    def __init__(self) -> None:
        self.results = []

    def process(self, result, timestamp) -> None:
        self.results.append((result.symbol, timestamp))


def test_live_monitor_connects_provider_to_analysis_pipeline(monkeypatch) -> None:
    bars = [
        OHLCVBar(
            timestamp=datetime(2026, 8, 18, 10, minute),
            open=100,
            high=101,
            low=99,
            close=100.5,
            volume=1000,
        )
        for minute in range(1, 6)
    ]
    dispatcher = RecordingDispatcher()
    provider = FakeProvider(bars)
    metadata = AnalysisMetadata(
        sector="Energy",
        market_score=80,
        sector_score=80,
        stock_score=80,
        confirmation_score=80,
        timeframe_trends=(TimeframeTrend("1m", "bullish"),),
        stop_loss=99,
        target_1=102,
        target_2=104,
    )

    def fake_analysis(inputs):
        class Result:
            symbol = inputs.symbol

        return Result()

    monkeypatch.setattr(
        "trading_assistant.monitoring.analysis_runner.analyze_stock",
        fake_analysis,
    )

    monitor = LiveMonitor(
        provider,
        ["RELIANCE"],
        lambda symbol, timestamp: metadata,
        dispatcher,
        clock=lambda: datetime(2026, 8, 18, 10, 5),
        sleeper=lambda seconds: None,
        lookback_bars=5,
    )

    cycle = monitor.run_cycle()

    assert cycle.processed == 1
    assert dispatcher.results == [("RELIANCE", datetime(2026, 8, 18, 10, 5))]

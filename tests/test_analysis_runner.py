from datetime import datetime
from types import SimpleNamespace

from trading_assistant.monitoring.analysis_runner import WatchlistAnalysisRunner


class RecordingDispatcher:
    def __init__(self) -> None:
        self.results = []

    def process(self, result, timestamp) -> None:
        self.results.append((result.symbol, timestamp))


def test_runner_executes_analysis_and_dispatches_result(monkeypatch) -> None:
    dispatcher = RecordingDispatcher()
    timestamp = datetime(2026, 8, 17, 10, 24)
    built_inputs = []

    def build_input(symbol, current_time):
        built_inputs.append((symbol, current_time))
        return object()

    result = SimpleNamespace(symbol="RELIANCE")

    def fake_analyze_stock(inputs):
        assert inputs is not None
        return result

    monkeypatch.setattr(
        "trading_assistant.monitoring.analysis_runner.analyze_stock",
        fake_analyze_stock,
    )

    runner = WatchlistAnalysisRunner(build_input, dispatcher)
    runner.process_symbol("RELIANCE", timestamp)

    assert built_inputs == [("RELIANCE", timestamp)]
    assert dispatcher.results == [("RELIANCE", timestamp)]

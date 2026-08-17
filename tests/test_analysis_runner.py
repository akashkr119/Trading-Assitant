from datetime import datetime

from trading_assistant.monitoring.analysis_runner import WatchlistAnalysisRunner


class RecordingDispatcher:
    def __init__(self) -> None:
        self.results = []

    def process(self, result, timestamp) -> None:
        self.results.append((result.symbol, timestamp))


def test_runner_executes_analysis_and_dispatches_result(sample_stock_input) -> None:
    dispatcher = RecordingDispatcher()
    timestamp = datetime(2026, 8, 17, 10, 24)

    runner = WatchlistAnalysisRunner(
        lambda symbol, current_time: sample_stock_input(symbol, current_time),
        dispatcher,
    )

    runner.process_symbol("RELIANCE", timestamp)

    assert dispatcher.results == [("RELIANCE", timestamp)]

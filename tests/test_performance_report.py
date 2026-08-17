from datetime import datetime

from trading_assistant.analysis.trade_decision import TradeAction
from trading_assistant.monitoring.performance import SignalPerformance
from trading_assistant.monitoring.performance_report import build_report, report_as_markdown
from trading_assistant.monitoring.performance_store import PerformanceStore, StoredPerformance


def performance(action: TradeAction, returns: tuple[tuple[int, float], ...]) -> SignalPerformance:
    return SignalPerformance(
        symbol="TEST",
        action=action,
        signal_price=100.0,
        returns=returns,
        max_favorable_pct=max(value for _, value in returns),
        max_adverse_pct=min(value for _, value in returns),
        target_1_hit=True,
        target_2_hit=False,
        stop_loss_hit=False,
    )


def test_report_aggregates_signal_outcomes() -> None:
    report = build_report(
        [
            performance(TradeAction.BUY, ((5, 1.0), (15, 2.0))),
            performance(TradeAction.SELL, ((5, -1.0), (15, 1.0))),
        ]
    )
    assert report.total_signals == 2
    assert report.target_1_rate_pct == 100.0
    assert report.horizon_accuracy_pct == ((5, 50.0), (15, 100.0))
    assert "Target 1 hit rate: 100.0%" in report_as_markdown(report)


def test_performance_store_round_trips(tmp_path) -> None:
    result = performance(TradeAction.BUY, ((5, 1.0),))
    stored = StoredPerformance.from_performance(result, datetime(2026, 8, 18, 10, 0))
    store = PerformanceStore(tmp_path / "signals.json")
    store.append(stored)
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].to_performance() == result

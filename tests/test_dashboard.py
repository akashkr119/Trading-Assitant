from datetime import datetime
from types import SimpleNamespace

from trading_assistant.analysis.trade_decision import TradeAction
from trading_assistant.brokers.session import BrokerSession
from trading_assistant.monitoring.dashboard import build_dashboard_snapshot
from trading_assistant.monitoring.watchlist import Watchlist


def test_dashboard_snapshot_contains_safe_signal_cards() -> None:
    now = datetime(2026, 8, 18, 10, 0)
    watchlist = Watchlist()
    watchlist.add("RELIANCE", now.isoformat())
    result = SimpleNamespace(
        symbol="RELIANCE",
        decision=SimpleNamespace(action=TradeAction.BUY, score=85.0),
        setup=SimpleNamespace(setup_type=SimpleNamespace(value="breakout")),
        explanation=SimpleNamespace(
            why_this_decision="Strong confirmation",
            risk_summary="Entry 100, stop 98, T1 104.",
            invalidation="Close below 98.",
        ),
    )
    broker = BrokerSession("groww", now)

    snapshot = build_dashboard_snapshot(
        generated_at=now,
        broker=broker,
        watchlist=watchlist,
        results=(result,),
    )

    assert snapshot.watchlist.symbols() == ("RELIANCE",)
    assert snapshot.broker == broker
    assert snapshot.signals[0].decision == "BUY"

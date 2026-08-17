from datetime import datetime
from types import SimpleNamespace

from trading_assistant.analysis.explanation import build_explanation
from trading_assistant.analysis.trade_decision import TradeAction, TradeDecision
from trading_assistant.monitoring.alerts import AlertType
from trading_assistant.monitoring.notifier import ConsoleNotifier, NotificationDispatcher
from trading_assistant.monitoring.signal_dispatch import SignalDispatcher
from trading_assistant.monitoring.state import MonitorStateMachine


def test_buy_result_is_notified_once_when_unchanged() -> None:
    decision = TradeDecision(
        action=TradeAction.BUY,
        score=85.0,
        risk_reward=2.0,
        reasons=("thresholds satisfied",),
        invalidation="Close below setup low.",
    )
    explanation = build_explanation(
        symbol="RELIANCE",
        decision="BUY",
        sector="Energy",
        market_reason="market is bullish",
        stock_reason="relative strength is strong",
        setup_reason="breakout",
        confirmations=("thresholds satisfied",),
        entry=100.0,
        stop_loss=98.0,
        target_1=104.0,
        target_2=106.0,
        risk_reward_1=2.0,
        invalidation="Close below setup low.",
    )
    result = SimpleNamespace(
        symbol="RELIANCE",
        decision=decision,
        explanation=explanation,
    )
    notifier = ConsoleNotifier(sent=[])
    dispatcher = SignalDispatcher(
        MonitorStateMachine(),
        NotificationDispatcher(notifier),
    )
    timestamp = datetime(2026, 8, 17, 10, 24)

    first = dispatcher.process(result, timestamp)
    second = dispatcher.process(result, datetime(2026, 8, 17, 10, 25))

    assert first is not None
    assert first.alert.alert_type == AlertType.BUY
    assert second is None
    assert len(notifier.sent) == 1

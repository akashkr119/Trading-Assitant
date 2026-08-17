"""Connect analysis results to alert state and notification delivery."""

from __future__ import annotations

from datetime import datetime

from trading_assistant.analysis.pipeline import StockAnalysisResult
from trading_assistant.analysis.trade_decision import TradeAction
from trading_assistant.monitoring.alert_payload import (
    AlertPayload,
    build_explained_alert,
)
from trading_assistant.monitoring.alerts import AlertType
from trading_assistant.monitoring.notifier import NotificationDispatcher
from trading_assistant.monitoring.state import MonitorState, MonitorStateMachine


_ACTION_ALERTS = {
    TradeAction.BUY: (AlertType.BUY, MonitorState.ACTIVE),
    TradeAction.SELL: (AlertType.SELL, MonitorState.ACTIVE),
    TradeAction.WATCH: (AlertType.SETUP_NEAR, MonitorState.TRIGGER_NEAR),
}


class SignalDispatcher:
    """Dispatch meaningful analysis changes and suppress unchanged repeats."""

    def __init__(
        self,
        state_machine: MonitorStateMachine,
        notification_dispatcher: NotificationDispatcher,
    ) -> None:
        self.state_machine = state_machine
        self.notification_dispatcher = notification_dispatcher

    def process(
        self,
        result: StockAnalysisResult,
        timestamp: datetime,
    ) -> AlertPayload | None:
        """Convert an actionable result into one notification when state changes."""
        action = result.decision.action
        alert_config = _ACTION_ALERTS.get(action)
        if alert_config is None:
            return None

        alert_type, state = alert_config
        trigger_key = f"{action.value}:{result.decision.score:.2f}"
        _, should_alert = self.state_machine.update(
            symbol=result.symbol,
            decision=action.value,
            state=state,
            trigger_key=trigger_key,
            timestamp=timestamp,
        )
        if not should_alert:
            return None

        payload = build_explained_alert(
            symbol=result.symbol,
            alert_type=alert_type,
            timestamp=timestamp.isoformat(),
            explanation=result.explanation,
        )
        self.notification_dispatcher.dispatch(payload.alert)
        return payload

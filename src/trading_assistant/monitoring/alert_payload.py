"""Combine signal explanations and trade levels into alert-ready payloads."""

from __future__ import annotations

from dataclasses import dataclass

from trading_assistant.analysis.explanation import SignalExplanation
from trading_assistant.monitoring.alerts import Alert, AlertType, build_alert


@dataclass(frozen=True)
class AlertPayload:
    alert: Alert
    explanation: SignalExplanation


def build_explained_alert(
    *,
    symbol: str,
    alert_type: AlertType,
    timestamp: str,
    explanation: SignalExplanation,
) -> AlertPayload:
    """Create an alert whose message preserves the full decision evidence."""
    confirmations = "; ".join(explanation.confirmations) or "None recorded."
    message = (
        f"{explanation.why_this_stock}\n"
        f"{explanation.why_this_decision}\n"
        f"Confirmations: {confirmations}\n"
        f"Risk plan: {explanation.risk_summary}\n"
        f"Invalidation: {explanation.invalidation}"
    )
    return AlertPayload(
        alert=build_alert(
            symbol=symbol,
            alert_type=alert_type,
            timestamp=timestamp,
            message=message,
        ),
        explanation=explanation,
    )

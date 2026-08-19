"""Provider-neutral alert generation for meaningful trading events."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AlertType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    SETUP_NEAR = "setup_near"
    TARGET = "target"
    STOP = "stop"
    INVALIDATED = "invalidated"
    SIGNAL_CHANGED = "signal_changed"


@dataclass(frozen=True)
class Alert:
    symbol: str
    alert_type: AlertType
    title: str
    message: str
    timestamp: str


def build_alert(
    *,
    symbol: str,
    alert_type: AlertType,
    timestamp: str,
    message: str,
) -> Alert:
    """Build a normalized alert without choosing a delivery channel."""
    title = f"{symbol.upper()} — {alert_type.value.upper()}"
    return Alert(
        symbol=symbol.upper(),
        alert_type=alert_type,
        title=title,
        message=message,
        timestamp=timestamp,
    )

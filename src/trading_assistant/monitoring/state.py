"""One-minute signal monitoring state and duplicate-alert suppression."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MonitorState(StrEnum):
    WATCH = "watch"
    TRIGGER_NEAR = "trigger_near"
    ACTIVE = "active"
    TARGET = "target"
    STOPPED = "stopped"
    INVALIDATED = "invalidated"


@dataclass(frozen=True)
class SignalSnapshot:
    symbol: str
    decision: str
    state: MonitorState
    trigger_key: str
    timestamp: datetime


class MonitorStateMachine:
    """Track a selected stock and suppress duplicate unchanged alerts."""

    def __init__(self) -> None:
        self._signals: dict[str, SignalSnapshot] = {}

    def update(
        self,
        *,
        symbol: str,
        decision: str,
        state: MonitorState,
        trigger_key: str,
        timestamp: datetime,
    ) -> tuple[SignalSnapshot, bool]:
        """Store the latest state and return whether an alert should be emitted."""
        current = SignalSnapshot(
            symbol=symbol,
            decision=decision,
            state=state,
            trigger_key=trigger_key,
            timestamp=timestamp,
        )
        previous = self._signals.get(symbol)
        self._signals[symbol] = current

        should_alert = previous is None or (
            previous.state != state or previous.trigger_key != trigger_key
        )
        return current, should_alert

    def get(self, symbol: str) -> SignalSnapshot | None:
        return self._signals.get(symbol)

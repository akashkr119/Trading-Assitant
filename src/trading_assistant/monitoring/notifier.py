"""Notification delivery abstraction with a deterministic console channel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from trading_assistant.monitoring.alerts import Alert


class Notifier(Protocol):
    def send(self, alert: Alert) -> None:
        """Deliver an alert through a notification channel."""


@dataclass
class ConsoleNotifier:
    """Simple notifier for development and end-to-end testing."""

    sent: list[Alert]

    def send(self, alert: Alert) -> None:
        self.sent.append(alert)


class NotificationDispatcher:
    """Dispatch alerts to a configured notifier."""

    def __init__(self, notifier: Notifier) -> None:
        self.notifier = notifier

    def dispatch(self, alert: Alert) -> None:
        self.notifier.send(alert)

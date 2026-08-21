"""V2 alert rules with cooldown and duplicate suppression."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class AlertEvent:
    """A user-facing V2 alert event."""

    key: str
    title: str
    message: str
    severity: str
    created_at: datetime


@dataclass
class AlertEngine:
    """Keep alert delivery deterministic and suppress repeated events."""

    cooldown_minutes: int = 15

    def __post_init__(self) -> None:
        self._last_sent: dict[str, datetime] = {}

    def evaluate(
        self,
        key: str,
        title: str,
        message: str,
        severity: str = "INFO",
        now: datetime | None = None,
    ) -> AlertEvent | None:
        """Create an alert unless the same key is inside its cooldown window."""
        current = now or datetime.now(timezone.utc)
        previous = self._last_sent.get(key)
        if previous is not None and current - previous < timedelta(minutes=self.cooldown_minutes):
            return None
        event = AlertEvent(key, title, message, severity.upper(), current)
        self._last_sent[key] = current
        return event

    def clear(self, key: str | None = None) -> None:
        """Clear one alert cooldown or all cooldowns."""
        if key is None:
            self._last_sent.clear()
        else:
            self._last_sent.pop(key, None)

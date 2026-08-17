"""Short-lived broker session metadata without storing secret values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from trading_assistant.brokers.connection import BrokerConnectionState, ConnectionStatus


@dataclass(frozen=True)
class BrokerSession:
    """Safe session metadata exposed to application/UI code."""

    broker: str
    connected_at: datetime
    expires_at: datetime | None = None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at


class BrokerSessionManager:
    """Track connection metadata while keeping access tokens out of UI state."""

    def __init__(self) -> None:
        self._session: BrokerSession | None = None

    def accept(self, state: BrokerConnectionState, now: datetime) -> BrokerSession | None:
        if state.status != ConnectionStatus.CONNECTED:
            self._session = None
            return None
        self._session = BrokerSession(state.broker.value, now)
        return self._session

    def current(self, now: datetime) -> BrokerSession | None:
        if self._session is not None and self._session.is_expired(now):
            self._session = None
        return self._session

    def clear(self) -> None:
        self._session = None

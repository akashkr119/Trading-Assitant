"""Application-facing broker connection facade."""

from __future__ import annotations

from datetime import datetime

from trading_assistant.brokers.connection import (
    BrokerConnectionService,
    BrokerConnectionState,
    BrokerName,
)
from trading_assistant.brokers.session import BrokerSession, BrokerSessionManager


class BrokerFacade:
    """Expose connect/disconnect operations without leaking broker credentials."""

    def __init__(
        self,
        service: BrokerConnectionService,
        sessions: BrokerSessionManager | None = None,
    ) -> None:
        self.service = service
        self.sessions = sessions or BrokerSessionManager()

    def available_brokers(self) -> tuple[BrokerName, ...]:
        return self.service.supported_brokers()

    def connect(
        self,
        broker: BrokerName,
        now: datetime,
    ) -> BrokerConnectionState:
        state = self.service.connect(broker)
        self.sessions.accept(state, now)
        return state

    def disconnect(self) -> BrokerConnectionState:
        state = self.service.disconnect()
        self.sessions.clear()
        return state

    def session(self, now: datetime) -> BrokerSession | None:
        return self.sessions.current(now)

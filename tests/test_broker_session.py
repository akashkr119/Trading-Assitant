from datetime import datetime, timedelta

from trading_assistant.brokers.connection import (
    BrokerConnectionState,
    BrokerName,
    ConnectionStatus,
)
from trading_assistant.brokers.session import BrokerSessionManager


def test_session_manager_stores_safe_metadata_only() -> None:
    now = datetime(2026, 8, 18, 10, 0)
    manager = BrokerSessionManager()
    session = manager.accept(
        BrokerConnectionState(
            BrokerName.GROWW,
            ConnectionStatus.CONNECTED,
            "connected",
        ),
        now,
    )

    assert session is not None
    assert session.broker == "groww"
    assert manager.current(now) == session


def test_session_manager_expires_session() -> None:
    now = datetime(2026, 8, 18, 10, 0)
    manager = BrokerSessionManager()
    manager._session = manager.accept(
        BrokerConnectionState(
            BrokerName.UPSTOX,
            ConnectionStatus.CONNECTED,
            "connected",
        ),
        now,
    )
    session = manager.current(now + timedelta(days=1))
    assert session is not None

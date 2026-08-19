"""Provider-neutral broker connection contract and connection status."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class BrokerName(StrEnum):
    """Supported broker identifiers exposed by the connection layer."""

    GROWW = "groww"
    UPSTOX = "upstox"
    ZERODHA = "zerodha"


class ConnectionStatus(StrEnum):
    """Lifecycle states for a broker connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass(frozen=True)
class BrokerConnectionState:
    """Safe connection state that can be returned to the UI."""

    broker: BrokerName
    status: ConnectionStatus
    message: str


class BrokerConnector(Protocol):
    """Common contract for broker-specific authentication adapters."""

    broker: BrokerName

    def start(self) -> BrokerConnectionState:
        """Start broker authentication or token acquisition."""
        ...

    def disconnect(self) -> BrokerConnectionState:
        """End the current broker session."""
        ...

    def status(self) -> BrokerConnectionState:
        """Return safe connection state without exposing credentials."""
        ...


class BrokerConnectionService:
    """Manage the currently selected broker without exposing secrets."""

    def __init__(self, connectors: dict[BrokerName, BrokerConnector]) -> None:
        self._connectors = connectors
        self._active: BrokerName | None = None

    def supported_brokers(self) -> tuple[BrokerName, ...]:
        return tuple(self._connectors)

    def connect(self, broker: BrokerName) -> BrokerConnectionState:
        if broker not in self._connectors:
            raise ValueError(f"Unsupported broker: {broker}")
        if self._active is not None and self._active != broker:
            self._connectors[self._active].disconnect()
        state = self._connectors[broker].start()
        self._active = broker if state.status == ConnectionStatus.CONNECTED else None
        return state

    def disconnect(self) -> BrokerConnectionState:
        if self._active is None:
            raise RuntimeError("No broker is connected")
        state = self._connectors[self._active].disconnect()
        self._active = None
        return state

    def status(self) -> BrokerConnectionState:
        if self._active is None:
            return BrokerConnectionState(
                broker=BrokerName.GROWW,
                status=ConnectionStatus.DISCONNECTED,
                message="No broker connected.",
            )
        return self._connectors[self._active].status()

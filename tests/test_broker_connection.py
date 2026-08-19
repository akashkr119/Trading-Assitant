from dataclasses import dataclass

from trading_assistant.brokers.connection import (
    BrokerConnectionService,
    BrokerConnectionState,
    BrokerName,
    ConnectionStatus,
)


@dataclass
class FakeConnector:
    broker: BrokerName
    connected: bool = False

    def start(self) -> BrokerConnectionState:
        self.connected = True
        return BrokerConnectionState(
            self.broker, ConnectionStatus.CONNECTED, "Connected."
        )

    def disconnect(self) -> BrokerConnectionState:
        self.connected = False
        return BrokerConnectionState(
            self.broker, ConnectionStatus.DISCONNECTED, "Disconnected."
        )

    def status(self) -> BrokerConnectionState:
        status = (
            ConnectionStatus.CONNECTED
            if self.connected
            else ConnectionStatus.DISCONNECTED
        )
        return BrokerConnectionState(self.broker, status, "Status checked.")


def test_connection_service_lists_and_connects_broker() -> None:
    groww = FakeConnector(BrokerName.GROWW)
    upstox = FakeConnector(BrokerName.UPSTOX)
    service = BrokerConnectionService(
        {BrokerName.GROWW: groww, BrokerName.UPSTOX: upstox}
    )

    assert service.supported_brokers() == (BrokerName.GROWW, BrokerName.UPSTOX)
    assert service.connect(BrokerName.GROWW).status == ConnectionStatus.CONNECTED
    assert service.status().broker == BrokerName.GROWW


def test_switching_broker_disconnects_previous_connection() -> None:
    groww = FakeConnector(BrokerName.GROWW)
    upstox = FakeConnector(BrokerName.UPSTOX)
    service = BrokerConnectionService(
        {BrokerName.GROWW: groww, BrokerName.UPSTOX: upstox}
    )

    service.connect(BrokerName.GROWW)
    service.connect(BrokerName.UPSTOX)

    assert not groww.connected
    assert upstox.connected


def test_disconnect_requires_active_connection() -> None:
    service = BrokerConnectionService({})

    try:
        service.disconnect()
    except RuntimeError as error:
        assert str(error) == "No broker is connected"
    else:
        raise AssertionError("Expected disconnect to require an active broker")

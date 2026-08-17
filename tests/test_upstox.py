from trading_assistant.brokers.connection import BrokerName, ConnectionStatus
from trading_assistant.brokers.upstox import UpstoxConnector


def test_missing_upstox_token_returns_error() -> None:
    state = UpstoxConnector().start()

    assert state.broker == BrokerName.UPSTOX
    assert state.status == ConnectionStatus.ERROR
    assert "access token" in state.message.lower()


def test_upstox_disconnect_clears_token() -> None:
    connector = UpstoxConnector(access_token="test-token")

    state = connector.disconnect()

    assert state.status == ConnectionStatus.DISCONNECTED
    assert connector.access_token is None


def test_upstox_status_does_not_expose_token() -> None:
    connector = UpstoxConnector(access_token="secret-token")

    state = connector.status()

    assert state.status == ConnectionStatus.CONNECTED
    assert "secret-token" not in state.message

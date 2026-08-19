import pytest

from trading_assistant.brokers.groww import GrowwConnection, GrowwConnectionError


def test_groww_connection_uses_bearer_token() -> None:
    connection = GrowwConnection(access_token="secret")

    assert connection.broker_name == "groww"
    assert connection.is_connected()
    assert connection.authorization_header() == {"Authorization": "Bearer secret"}


def test_groww_connection_rejects_empty_token() -> None:
    connection = GrowwConnection(access_token="  ")

    assert not connection.is_connected()
    with pytest.raises(GrowwConnectionError, match="access token is required"):
        connection.authorization_header()

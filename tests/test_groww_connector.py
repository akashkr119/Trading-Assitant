import json
from io import BytesIO

from trading_assistant.brokers.connection import BrokerName, ConnectionStatus
from trading_assistant.brokers.groww_connector import GrowwConnector


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_groww_connector_requires_access_token() -> None:
    result = GrowwConnector(access_token="").start()

    assert result.broker == BrokerName.GROWW
    assert result.status == ConnectionStatus.ERROR
    assert "access token" in result.message


def test_groww_connector_verifies_account(monkeypatch) -> None:
    response = FakeResponse(
        json.dumps(
            {
                "status": "SUCCESS",
                "payload": {"ucc": "123456", "nse_enabled": True},
            }
        ).encode()
    )
    monkeypatch.setattr(
        "trading_assistant.brokers.groww_connector.urlopen",
        lambda request, timeout: response,
    )

    result = GrowwConnector(access_token="test-token").start()

    assert result.status == ConnectionStatus.CONNECTED
    assert "123456" in result.message


def test_groww_connector_rejects_failed_profile(monkeypatch) -> None:
    response = FakeResponse(json.dumps({"status": "FAILURE"}).encode())
    monkeypatch.setattr(
        "trading_assistant.brokers.groww_connector.urlopen",
        lambda request, timeout: response,
    )

    result = GrowwConnector(access_token="bad-token").start()

    assert result.status == ConnectionStatus.ERROR
    assert "rejected" in result.message


def test_disconnect_clears_token() -> None:
    connector = GrowwConnector(access_token="test-token")

    result = connector.disconnect()

    assert result.status == ConnectionStatus.DISCONNECTED
    assert connector.access_token is None

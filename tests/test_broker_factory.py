from trading_assistant.brokers.connection import BrokerName
from trading_assistant.brokers.factory import build_broker_connection_service


def test_factory_exposes_groww_without_exposing_credentials(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "test-token")

    service = build_broker_connection_service()

    assert service.supported_brokers() == (BrokerName.GROWW,)
    assert service.status().message == "No broker connected."

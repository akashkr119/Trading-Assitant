from datetime import datetime
from types import SimpleNamespace

from trading_assistant.application import TradingAssistantApplication
from trading_assistant.brokers.connection import BrokerConnectionState, BrokerName, ConnectionStatus


def test_application_connects_broker_and_manages_watchlist() -> None:
    now = datetime(2026, 8, 18, 10, 0)

    class FakeBroker:
        def connect(self, broker, current_time):
            return BrokerConnectionState(broker, ConnectionStatus.CONNECTED, "connected")

        def disconnect(self):
            return BrokerConnectionState(BrokerName.GROWW, ConnectionStatus.DISCONNECTED, "disconnected")

        def session(self, current_time):
            return SimpleNamespace(broker="groww", connected_at=current_time)

    app = TradingAssistantApplication(FakeBroker())
    state = app.connect_broker(BrokerName.GROWW, now)
    app.add_symbol("reliance", now.isoformat())

    assert state.status == ConnectionStatus.CONNECTED
    assert app.dashboard(now).watchlist.symbols() == ("RELIANCE",)

"""Construct the broker connection service from runtime configuration."""

from __future__ import annotations

from trading_assistant.brokers.connection import BrokerConnectionService, BrokerName
from trading_assistant.brokers.groww_connector import GrowwConnector
from trading_assistant.brokers.upstox import UpstoxConnector


def build_broker_connection_service() -> BrokerConnectionService:
    """Build supported broker connectors without exposing credentials."""
    return BrokerConnectionService(
        {
            BrokerName.GROWW: GrowwConnector.from_environment(),
            BrokerName.UPSTOX: UpstoxConnector.from_environment(),
        }
    )

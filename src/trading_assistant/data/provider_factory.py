"""Construct the selected broker market-data provider from environment settings."""

from __future__ import annotations

import os

from trading_assistant.brokers.connection import BrokerName
from trading_assistant.data.groww import GrowwMarketDataProvider
from trading_assistant.data.interfaces import MarketDataProvider
from trading_assistant.data.upstox import UpstoxMarketDataProvider


def build_market_data_provider(broker: BrokerName) -> MarketDataProvider:
    """Build a read-only market-data provider using runtime credentials."""
    timeout = float(os.getenv("MARKET_DATA_TIMEOUT_SECONDS", "10"))
    if broker == BrokerName.GROWW:
        token = os.getenv("GROWW_ACCESS_TOKEN", "").strip()
        return GrowwMarketDataProvider(token, timeout_seconds=timeout)

    if broker == BrokerName.UPSTOX:
        token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
        raw_keys = os.getenv("UPSTOX_INSTRUMENT_KEYS", "").strip()
        instrument_keys: dict[str, str] = {}
        for item in raw_keys.split(",") if raw_keys else []:
            symbol, separator, key = item.partition("=")
            if not separator or not symbol.strip() or not key.strip():
                raise ValueError(
                    "UPSTOX_INSTRUMENT_KEYS must use SYMBOL=INSTRUMENT_KEY entries"
                )
            instrument_keys[symbol.strip().upper()] = key.strip()
        return UpstoxMarketDataProvider(
            token,
            instrument_keys,
            timeout_seconds=timeout,
        )

    raise ValueError(f"Market data is not implemented for {broker.value}")

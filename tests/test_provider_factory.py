import pytest

from trading_assistant.brokers.connection import BrokerName
from trading_assistant.data.groww import GrowwMarketDataProvider
from trading_assistant.data.provider_factory import build_market_data_provider
from trading_assistant.data.upstox import UpstoxMarketDataProvider


def test_groww_provider_is_built_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "groww-token")

    provider = build_market_data_provider(BrokerName.GROWW)

    assert isinstance(provider, GrowwMarketDataProvider)


def test_upstox_provider_is_built_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "upstox-token")
    monkeypatch.setenv(
        "UPSTOX_INSTRUMENT_KEYS",
        "RELIANCE=NSE_EQ|INE002A01018,TCS=NSE_EQ|INE467B01029",
    )

    provider = build_market_data_provider(BrokerName.UPSTOX)

    assert isinstance(provider, UpstoxMarketDataProvider)
    assert provider.instrument_keys["RELIANCE"] == "NSE_EQ|INE002A01018"


def test_upstox_factory_rejects_malformed_instrument_mapping(monkeypatch) -> None:
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "upstox-token")
    monkeypatch.setenv("UPSTOX_INSTRUMENT_KEYS", "RELIANCE")

    with pytest.raises(ValueError, match="SYMBOL=INSTRUMENT_KEY"):
        build_market_data_provider(BrokerName.UPSTOX)

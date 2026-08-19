import pytest

from trading_assistant.config import Settings


def test_settings_loads_upstox_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "secret")
    monkeypatch.setenv(
        "UPSTOX_INSTRUMENT_KEYS",
        "RELIANCE=NSE_EQ|INE002A01018,TCS=NSE_EQ|INE467B01029",
    )
    monkeypatch.setenv("MARKET_DATA_TIMEOUT_SECONDS", "15")

    settings = Settings.from_environment()

    assert settings.upstox_access_token == "secret"
    assert settings.instrument_keys["RELIANCE"] == "NSE_EQ|INE002A01018"
    assert settings.api_timeout_seconds == 15.0


def test_settings_requires_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)

    with pytest.raises(ValueError, match="UPSTOX_ACCESS_TOKEN is required"):
        Settings.from_environment()


def test_settings_rejects_malformed_instrument_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "secret")
    monkeypatch.setenv("UPSTOX_INSTRUMENT_KEYS", "RELIANCE")

    with pytest.raises(ValueError, match="SYMBOL=INSTRUMENT_KEY"):
        Settings.from_environment()

"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Configuration required to connect to the live market-data provider."""

    upstox_access_token: str
    instrument_keys: dict[str, str]
    market_data_provider: str = "upstox"
    api_timeout_seconds: float = 10.0

    @classmethod
    def from_environment(cls) -> Settings:
        token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
        if not token:
            raise ValueError("UPSTOX_ACCESS_TOKEN is required")

        raw_keys = os.getenv("UPSTOX_INSTRUMENT_KEYS", "").strip()
        instrument_keys: dict[str, str] = {}
        for item in raw_keys.split(",") if raw_keys else []:
            symbol, separator, key = item.partition("=")
            if not separator or not symbol.strip() or not key.strip():
                raise ValueError(
                    "UPSTOX_INSTRUMENT_KEYS must use SYMBOL=INSTRUMENT_KEY entries"
                )
            instrument_keys[symbol.strip().upper()] = key.strip()

        timeout = float(os.getenv("MARKET_DATA_TIMEOUT_SECONDS", "10"))
        return cls(
            upstox_access_token=token,
            instrument_keys=instrument_keys,
            market_data_provider=os.getenv("MARKET_DATA_PROVIDER", "upstox").strip(),
            api_timeout_seconds=timeout,
        )

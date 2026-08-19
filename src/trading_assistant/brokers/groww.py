"""Groww Trading API connection adapter."""

from __future__ import annotations

from dataclasses import dataclass

from trading_assistant.brokers.base import BrokerConnection


class GrowwConnectionError(RuntimeError):
    """Raised when Groww credentials are missing or invalid."""


@dataclass(frozen=True)
class GrowwConnection(BrokerConnection):
    """Represent a Groww API connection without storing secrets in code."""

    access_token: str

    @property
    def broker_name(self) -> str:
        return "groww"

    def is_connected(self) -> bool:
        return bool(self.access_token.strip())

    def authorization_header(self) -> dict[str, str]:
        if not self.is_connected():
            raise GrowwConnectionError("Groww access token is required")
        return {"Authorization": f"Bearer {self.access_token}"}

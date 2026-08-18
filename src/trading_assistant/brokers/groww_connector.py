"""Groww authentication and connection verification adapter."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.request import Request, urlopen

import truststore

from trading_assistant.brokers.connection import (
    BrokerConnectionState,
    BrokerName,
    ConnectionStatus,
)


truststore.inject_into_ssl()


class GrowwAuthenticationError(RuntimeError):
    """Raised when Groww authentication or verification fails."""


@dataclass
class GrowwConnector:
    """Connect to Groww using a runtime access token and verify the account."""

    access_token: str | None = None
    base_url: str = "https://api.groww.in/v1"
    timeout_seconds: float = 10.0

    broker: BrokerName = BrokerName.GROWW

    @classmethod
    def from_environment(cls) -> GrowwConnector:
        """Build a connector from the runtime Groww access-token setting."""
        return cls(access_token=os.getenv("GROWW_ACCESS_TOKEN"))

    def start(self) -> BrokerConnectionState:
        """Verify the authenticated Groww account without placing an order."""
        if not self.access_token or not self.access_token.strip():
            return BrokerConnectionState(
                self.broker,
                ConnectionStatus.ERROR,
                "Groww access token is required.",
            )
        try:
            profile = self._get_profile()
        except GrowwAuthenticationError as error:
            return BrokerConnectionState(
                self.broker,
                ConnectionStatus.ERROR,
                str(error),
            )

        ucc = profile.get("ucc")
        message = "Groww account connected."
        if ucc:
            message = f"Groww account connected (UCC {ucc})."
        return BrokerConnectionState(
            self.broker,
            ConnectionStatus.CONNECTED,
            message,
        )

    def disconnect(self) -> BrokerConnectionState:
        """Clear the in-memory token reference."""
        self.access_token = None
        return BrokerConnectionState(
            self.broker,
            ConnectionStatus.DISCONNECTED,
            "Groww account disconnected.",
        )

    def status(self) -> BrokerConnectionState:
        """Return the local connection state without exposing credentials."""
        if self.access_token and self.access_token.strip():
            return BrokerConnectionState(
                self.broker,
                ConnectionStatus.CONNECTED,
                "Groww credentials are configured.",
            )
        return BrokerConnectionState(
            self.broker,
            ConnectionStatus.DISCONNECTED,
            "Groww account is not connected.",
        )

    def _get_profile(self) -> dict:
        request = Request(
            f"{self.base_url.rstrip('/')}/user/detail",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
                "X-API-VERSION": "1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except Exception as error:
            raise GrowwAuthenticationError(
                f"Unable to verify Groww connection: {error}"
            ) from error

        if payload.get("status") != "SUCCESS":
            raise GrowwAuthenticationError("Groww rejected the credentials.")
        return payload.get("payload", {})

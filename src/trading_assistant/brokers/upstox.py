"""Upstox authentication and connection verification adapter."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.request import Request, urlopen

from trading_assistant.brokers.connection import (
    BrokerConnectionState,
    BrokerName,
    ConnectionStatus,
)


class UpstoxAuthenticationError(RuntimeError):
    """Raised when Upstox authentication or verification fails."""


@dataclass
class UpstoxConnector:
    """Connect to Upstox using a runtime access token and verify the account."""

    access_token: str | None = None
    base_url: str = "https://api.upstox.com/v2"
    timeout_seconds: float = 10.0

    broker: BrokerName = BrokerName.UPSTOX

    @classmethod
    def from_environment(cls) -> UpstoxConnector:
        """Build a connector from the runtime Upstox access-token setting."""
        return cls(access_token=os.getenv("UPSTOX_ACCESS_TOKEN"))

    def start(self) -> BrokerConnectionState:
        """Verify the authenticated Upstox account without placing an order."""
        if not self.access_token or not self.access_token.strip():
            return BrokerConnectionState(
                self.broker,
                ConnectionStatus.ERROR,
                "Upstox access token is required.",
            )
        try:
            profile = self._get_profile()
        except UpstoxAuthenticationError as error:
            return BrokerConnectionState(
                self.broker,
                ConnectionStatus.ERROR,
                str(error),
            )

        user_id = profile.get("user_id")
        message = "Upstox account connected."
        if user_id:
            message = f"Upstox account connected (user {user_id})."
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
            "Upstox account disconnected.",
        )

    def status(self) -> BrokerConnectionState:
        """Return local connection state without exposing credentials."""
        if self.access_token and self.access_token.strip():
            return BrokerConnectionState(
                self.broker,
                ConnectionStatus.CONNECTED,
                "Upstox credentials are configured.",
            )
        return BrokerConnectionState(
            self.broker,
            ConnectionStatus.DISCONNECTED,
            "Upstox account is not connected.",
        )

    def _get_profile(self) -> dict:
        request = Request(
            f"{self.base_url.rstrip('/')}/user/profile",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except Exception as error:
            raise UpstoxAuthenticationError(
                f"Unable to verify Upstox connection: {error}"
            ) from error

        if payload.get("status") != "success":
            raise UpstoxAuthenticationError("Upstox rejected the credentials.")
        return payload.get("data", {})

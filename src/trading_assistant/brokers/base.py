"""Provider-neutral broker connection contracts."""

from __future__ import annotations

from typing import Protocol


class BrokerConnection(Protocol):
    """Common connection contract for supported brokers."""

    @property
    def broker_name(self) -> str:
        """Return the broker identifier."""
        ...

    def is_connected(self) -> bool:
        """Return whether the current broker credentials are usable."""
        ...

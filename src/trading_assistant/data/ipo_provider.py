"""Provider contract for current IPO information."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from trading_assistant.ipo import IPO


class IPOProvider(Protocol):
    """Return current IPO data from a configured external source."""

    def open_ipos(self, as_of: date) -> tuple[IPO, ...]:
        """Return IPOs open on the requested date."""
        ...

    def get_ipo(self, symbol: str) -> IPO | None:
        """Return one IPO by symbol, or None when unavailable."""
        ...

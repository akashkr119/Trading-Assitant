"""Provider interface for verified long-term fundamental data."""

from __future__ import annotations

from typing import Protocol

from trading_assistant.data.fundamentals import FundamentalsSnapshot


class FundamentalsProvider(Protocol):
    """Return normalized fundamentals from a configured, traceable data source."""

    def get_fundamentals(self, symbol: str) -> FundamentalsSnapshot:
        """Return the latest verified fundamentals snapshot for a symbol."""
        ...

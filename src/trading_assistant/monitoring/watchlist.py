"""User-controlled watchlist for candidate stocks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class WatchlistItem:
    symbol: str
    added_at: str


class Watchlist:
    """Maintain the stocks explicitly selected by the user for monitoring."""

    def __init__(self) -> None:
        self._items: dict[str, WatchlistItem] = {}

    def add(self, symbol: str, added_at: str) -> WatchlistItem:
        normalized = symbol.strip().upper()
        if not normalized:
            raise ValueError("symbol cannot be empty")
        item = WatchlistItem(symbol=normalized, added_at=added_at)
        self._items[normalized] = item
        return item

    def remove(self, symbol: str) -> bool:
        return self._items.pop(symbol.strip().upper(), None) is not None

    def contains(self, symbol: str) -> bool:
        return symbol.strip().upper() in self._items

    def symbols(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))

    def items(self) -> tuple[WatchlistItem, ...]:
        return tuple(self._items[symbol] for symbol in sorted(self._items))

    def export(self) -> tuple[dict[str, str], ...]:
        """Return a JSON-safe representation suitable for persistence."""
        return tuple(
            {"symbol": item.symbol, "added_at": item.added_at}
            for item in self.items()
        )

    @classmethod
    def from_items(cls, items: Iterable[dict[str, str]]) -> Watchlist:
        """Restore a watchlist from persisted JSON-safe records."""
        watchlist = cls()
        for item in items:
            if set(item) != {"symbol", "added_at"}:
                raise ValueError("watchlist item must contain symbol and added_at")
            watchlist.add(item["symbol"], item["added_at"])
        return watchlist

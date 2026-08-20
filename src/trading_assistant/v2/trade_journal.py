"""V2 trade journal records and setup-level analytics."""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict


@dataclass(frozen=True)
class JournalEntry:
    """Immutable record of one paper or historical trade."""

    symbol: str
    sector: str
    setup: str
    market_regime: str
    direction: str
    r_multiple: float
    outcome: str


def summarize_journal(entries: list[JournalEntry]) -> dict[str, object]:
    """Summarize outcomes and identify setup groups with positive expectancy."""
    if not entries:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "expectancy_r": 0.0,
            "best_setup": None,
        }

    grouped: dict[str, list[float]] = defaultdict(list)
    for entry in entries:
        grouped[entry.setup].append(entry.r_multiple)

    best_setup = max(
        grouped,
        key=lambda setup: sum(grouped[setup]) / len(grouped[setup]),
    )
    wins = sum(entry.r_multiple > 0 for entry in entries)
    return {
        "total_trades": len(entries),
        "win_rate": wins / len(entries) * 100,
        "expectancy_r": sum(entry.r_multiple for entry in entries) / len(entries),
        "best_setup": best_setup,
        "setup_expectancy": {
            setup: sum(values) / len(values)
            for setup, values in grouped.items()
        },
    }

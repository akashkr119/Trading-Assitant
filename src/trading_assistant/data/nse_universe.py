"""NSE equity universe helpers for long-term research."""

from __future__ import annotations

DEFAULT_NSE_LONG_TERM_UNIVERSE: tuple[str, ...] = (
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "INFY.NS",
    "ITC.NS",
    "LT.NS",
    "BHARTIARTL.NS",
    "SBIN.NS",
    "HINDUNILVR.NS",
)


def normalize_nse_symbol(symbol: str) -> str:
    """Normalize a user/provider symbol to Yahoo Finance NSE format."""
    value = symbol.strip().upper()
    if not value:
        raise ValueError("NSE symbol cannot be empty")
    return value if value.endswith(".NS") else f"{value}.NS"


def nse_long_term_universe(symbols: tuple[str, ...] = DEFAULT_NSE_LONG_TERM_UNIVERSE) -> list[str]:
    """Return a deduplicated, normalized research universe."""
    return list(dict.fromkeys(normalize_nse_symbol(symbol) for symbol in symbols))

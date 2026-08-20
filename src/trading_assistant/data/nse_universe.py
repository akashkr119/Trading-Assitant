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
    "AXISBANK.NS",
    "KOTAKBANK.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "MARUTI.NS",
    "M&M.NS",
    "TATAMOTORS.NS",
    "SUNPHARMA.NS",
    "CIPLA.NS",
    "DRREDDY.NS",
    "APOLLOHOSP.NS",
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "NTPC.NS",
    "POWERGRID.NS",
    "ONGC.NS",
    "COALINDIA.NS",
    "TATASTEEL.NS",
    "JSWSTEEL.NS",
    "HINDALCO.NS",
    "ASIANPAINT.NS",
    "ULTRACEMCO.NS",
    "GRASIM.NS",
    "TITAN.NS",
    "TRENT.NS",
    "NESTLEIND.NS",
    "BEL.NS",
    "HAL.NS",
    "EICHERMOT.NS",
    "HEROMOTOCO.NS",
    "BAJAJ-AUTO.NS",
    "TECHM.NS",
    "HCLTECH.NS",
    "WIPRO.NS",
    "LTIM.NS",
    "ETERNAL.NS",
    "SHRIRAMFIN.NS",
    "INDUSINDBK.NS",
    "DIVISLAB.NS",
    "BRITANNIA.NS",
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

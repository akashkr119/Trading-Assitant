"""Liquid NSE universe with dynamically sourced AMFI cap classification."""

from __future__ import annotations

from trading_assistant.monitoring.dynamic_cap_classification import (
    CapClassification,
    load_current_classification,
)

# The scanner universe stays liquidity-focused. Market-cap segments are resolved
# from AMFI and are never maintained manually in this file.
SWING_UNIVERSE = (
    "RELIANCE", "TCS", "HDFCBANK", "BHARTIARTL", "ICICIBANK", "INFY",
    "SBIN", "HINDUNILVR", "ITC", "LT", "BAJFINANCE", "MARUTI", "KOTAKBANK",
    "AXISBANK", "SUNPHARMA", "M&M", "HCLTECH", "TITAN", "ULTRACEMCO", "NTPC",
    "ONGC", "POWERGRID", "TATASTEEL", "ADANIENT", "ADANIPORTS", "TATAMOTORS",
    "WIPRO", "NESTLEIND", "ASIANPAINT", "DIXON", "POLYCAB", "TRENT", "MAXHEALTH",
    "HINDALCO", "JSWSTEEL", "TATACONSUM", "BEL", "INDUSTOWER", "VOLTAS", "CUMMINSIND",
    "HAVELLS", "TVSMOTOR", "BHARATFORG", "BOSCHLTD", "MPHASIS", "PERSISTENT", "COFORGE",
    "IDFCFIRSTB", "FEDERALBNK", "ASHOKLEY", "AUBANK", "BHEL", "CANBK", "INDIANB",
    "NMDC", "SAIL", "RECLTD", "PFC", "INDHOTEL", "KAYNES", "CDSL", "BSE", "IREDA",
    "IRFC", "RVNL", "HUDCO", "NBCC", "MAZDOCK", "COCHINSHIP", "ITI", "RITES", "CESC",
    "KPIL", "KALYANKJIL", "IEX", "MCX", "HFCL", "SONATSOFTW", "EASEMYTRIP", "JWL",
    "DELHIVERY", "CLEAN", "KFINTECH", "INOXWIND", "SUZLON", "UJJIVANSFB", "JYOTHYLAB",
)


def current_cap_classification() -> dict[str, CapClassification]:
    """Return the latest AMFI classification."""
    return load_current_classification()


try:
    _CURRENT = current_cap_classification()
    SYMBOL_TO_CAP = {
        symbol: item.segment
        for symbol, item in _CURRENT.items()
        if symbol in SWING_UNIVERSE
    }
except Exception:
    # The scanner can still start if AMFI is temporarily unavailable. The normal
    # path is dynamic; an unavailable source simply leaves symbols unclassified.
    SYMBOL_TO_CAP: dict[str, str] = {}

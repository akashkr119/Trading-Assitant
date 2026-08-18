"""Curated NSE equity universe grouped by market-cap segment for V1."""

from __future__ import annotations

# V1 uses a curated, periodically maintained classification rather than
# pretending that market-cap data is real-time. The scanner should later replace
# this with a live market-cap source when one is available.
LARGE_CAP_UNIVERSE = (
    "RELIANCE", "TCS", "HDFCBANK", "BHARTIARTL", "ICICIBANK", "INFY",
    "SBIN", "LICI", "HINDUNILVR", "ITC", "LT", "BAJFINANCE", "MARUTI",
    "KOTAKBANK", "AXISBANK", "SUNPHARMA", "M&M", "HCLTECH", "TITAN",
    "ULTRACEMCO", "NTPC", "ONGC", "POWERGRID", "TATASTEEL", "ADANIENT",
    "ADANIPORTS", "TATAMOTORS", "WIPRO", "NESTLEIND", "ASIANPAINT",
)

MID_CAP_UNIVERSE = (
    "DIXON", "POLYCAB", "TRENT", "MAXHEALTH", "HINDALCO", "JSWSTEEL",
    "TATACONSUM", "BEL", "INDUSTOWER", "VOLTAS", "CUMMINSIND", "HAVELLS",
    "TVSMOTOR", "BHARATFORG", "BOSCHLTD", "MPHASIS", "PERSISTENT", "COFORGE",
    "IDFCFIRSTB", "FEDERALBNK", "ASHOKLEY", "AUBANK", "BHEL", "CANBK",
    "INDIANB", "NMDC", "SAIL", "RECLTD", "PFC", "INDHOTEL",
)

SMALL_CAP_UNIVERSE = (
    "KAYNES", "CDSL", "BSE", "IREDA", "IRFC", "RVNL", "HUDCO", "NBCC",
    "MAZDOCK", "COCHINSHIP", "ITI", "RITES", "CESC", "KPIL", "KALYANKJIL",
    "IEX", "MCX", "HFCL", "SONATSOFTW", "EASEMYTRIP", "JWL", "DELHIVERY",
    "CLEAN", "KFINTECH", "INOXWIND", "SUZLON", "UJJIVANSFB", "JYOTHYLAB",
)

CAP_UNIVERSES = {
    "Large Cap": LARGE_CAP_UNIVERSE,
    "Mid Cap": MID_CAP_UNIVERSE,
    "Small Cap": SMALL_CAP_UNIVERSE,
}

SWING_UNIVERSE = tuple(
    dict.fromkeys(symbol for symbols in CAP_UNIVERSES.values() for symbol in symbols)
)

SYMBOL_TO_CAP = {
    symbol: cap
    for cap, symbols in CAP_UNIVERSES.items()
    for symbol in symbols
}

"""Live NSE sector performance and symbol classification helpers."""

# isort: skip_file

from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.request import Request, urlopen


_NSE_ALL_INDICES_URL = "https://www.nseindia.com/api/allIndices"

SECTOR_INDEXES = (
    "NIFTY AUTO",
    "NIFTY BANK",
    "NIFTY FINANCIAL SERVICES",
    "NIFTY FIN SERVICE",
    "NIFTY FMCG",
    "NIFTY IT",
    "NIFTY METAL",
    "NIFTY PHARMA",
    "NIFTY PSU BANK",
    "NIFTY PVT BANK",
    "NIFTY REALTY",
    "NIFTY ENERGY",
    "NIFTY INFRA",
    "NIFTY MEDIA",
    "NIFTY CONSUMER DURABLES",
    "NIFTY OIL & GAS",
)

_SYMBOL_SECTORS = {
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "AXISBANK": "Banking",
    "KOTAKBANK": "Banking",
    "INDUSINDBK": "Banking",
    "BAJFINANCE": "Financial Services",
    "BAJAJFINSV": "Financial Services",
    "SHRIRAMFIN": "Financial Services",
    "HDFCLIFE": "Insurance",
    "SBILIFE": "Insurance",
    "RELIANCE": "Energy",
    "ONGC": "Energy",
    "NTPC": "Power",
    "POWERGRID": "Power",
    "TCS": "IT",
    "INFY": "IT",
    "HCLTECH": "IT",
    "WIPRO": "IT",
    "TECHM": "IT",
    "LTIM": "IT",
    "TATAMOTORS": "Auto",
    "EICHERMOT": "Auto",
    "HEROMOTOCO": "Auto",
    "MARUTI": "Auto",
    "BAJAJ-AUTO": "Auto",
    "SUNPHARMA": "Pharma",
    "CIPLA": "Pharma",
    "DRREDDY": "Pharma",
    "APOLLOHOSP": "Healthcare",
    "MAXHEALTH": "Healthcare",
    "TATASTEEL": "Metal",
    "JSWSTEEL": "Metal",
    "HINDALCO": "Metal",
    "COALINDIA": "Metal",
    "ITC": "FMCG",
    "HINDUNILVR": "FMCG",
    "NESTLEIND": "FMCG",
    "BRITANNIA": "FMCG",
    "TATACONSUM": "FMCG",
    "ULTRACEMCO": "Cement",
    "GRASIM": "Cement",
    "ASIANPAINT": "Consumer",
    "TITAN": "Consumer",
    "TRENT": "Retail",
    "BEL": "Defence",
    "HAL": "Defence",
    "ADANIENT": "Infrastructure",
    "ADANIPORTS": "Infrastructure",
    "LT": "Infrastructure",
    "BHARTIARTL": "Telecom",
    "ETERNAL": "Consumer Internet",
}


@dataclass(frozen=True)
class SectorSnapshot:
    name: str
    change_pct: float
    advances: int
    declines: int
    unchanged: int

    @property
    def score(self) -> float:
        return max(0.0, min(100.0, 50.0 + self.change_pct * 10.0))


def symbol_sector(symbol: str) -> str:
    return _SYMBOL_SECTORS.get(symbol.upper().strip(), "Other")


def _fetch_all_indices() -> list[dict[str, object]]:
    request = Request(
        _NSE_ALL_INDICES_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/market-data/live-market-indices",
        },
    )
    with urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return list(payload.get("data", []))


def sector_performance() -> tuple[SectorSnapshot, ...]:
    """Return live sector-index performance from NSE, ranked strongest first."""
    rows = _fetch_all_indices()
    aliases = {
        "NIFTY FIN SERVICE": "NIFTY FINANCIAL SERVICES",
    }
    wanted = {name.upper(): name for name in SECTOR_INDEXES}
    snapshots: list[SectorSnapshot] = []
    seen: set[str] = set()
    for row in rows:
        raw_name = str(row.get("index", "")).strip().upper()
        name = aliases.get(raw_name, raw_name)
        if name not in wanted or name in seen:
            continue
        try:
            change = float(row.get("percentChange", 0.0) or 0.0)
            advances = int(row.get("advances", 0) or 0)
            declines = int(row.get("declines", 0) or 0)
            unchanged = int(row.get("unchanged", 0) or 0)
        except (TypeError, ValueError):
            continue
        snapshots.append(
            SectorSnapshot(wanted[name], change, advances, declines, unchanged)
        )
        seen.add(name)
    return tuple(sorted(snapshots, key=lambda item: item.change_pct, reverse=True))

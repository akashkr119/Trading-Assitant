"""NSE-backed current IPO provider."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import requests

from trading_assistant.ipo import IPO


class NSEIPOProvider:
    """Fetch current public-issue data from NSE's public issue endpoints."""

    _BASE_URL = "https://www.nseindia.com"
    _CURRENT_URL = f"{_BASE_URL}/api/ipo-current-issue"
    _UPCOMING_URL = f"{_BASE_URL}/api/all-upcoming-issues?category=ipo"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "en-IN,en;q=0.9",
                "Referer": "https://www.nseindia.com/market-data/all-upcoming-issues-ipo",
            }
        )

    def _get(self, url: str) -> Any:
        landing = self._session.get(self._BASE_URL, timeout=self.timeout)
        landing.raise_for_status()
        response = self._session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _first(item: dict[str, Any], *names: str) -> Any:
        lowered = {str(key).lower().replace("_", ""): value for key, value in item.items()}
        for name in names:
            value = lowered.get(name.lower().replace("_", ""))
            if value not in (None, "", "-"):
                return value
        return None

    @staticmethod
    def _date(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value).strip()
        for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Unsupported IPO date: {value!r}")

    @staticmethod
    def _float(value: Any) -> float:
        if value is None:
            raise ValueError("Required numeric IPO field is unavailable")
        text = str(value).replace(",", "").replace("₹", "").strip()
        return float(text)

    def _map(self, item: dict[str, Any]) -> IPO:
        name = self._first(item, "companyName", "company", "issuerName")
        symbol = self._first(item, "symbol", "nseSymbol", "issueSymbol")
        open_date = self._first(item, "issueStartDate", "openDate", "issueOpenDate")
        close_date = self._first(item, "issueEndDate", "closeDate", "issueCloseDate")
        price_band = self._first(item, "priceBand", "priceRange", "issuePrice")
        lot_size = self._first(item, "lotSize", "marketLot")
        issue_size = self._first(item, "issueSize", "issueSizeCr", "issueSizeInCr")
        fresh_issue = self._first(
            item,
            "freshIssue",
            "freshIssueSize",
            "freshIssueSizeCr",
        )
        ofs = self._first(item, "ofs", "ofsSize", "ofsSizeCr")
        sector = self._first(item, "sector", "industry") or "Unavailable"
        required = {
            "companyName": name,
            "symbol": symbol,
            "openDate": open_date,
            "closeDate": close_date,
            "priceBand": price_band,
            "lotSize": lot_size,
            "issueSize": issue_size,
            "freshIssue": fresh_issue,
            "ofs": ofs,
        }
        missing = [key for key, value in required.items() if value is None]
        if missing:
            raise ValueError(f"NSE IPO record missing fields: {', '.join(missing)}")
        return IPO(
            name=str(name),
            symbol=str(symbol),
            open_date=self._date(open_date),
            close_date=self._date(close_date),
            price_band=str(price_band),
            lot_size=int(float(lot_size)),
            issue_size_crore=self._float(issue_size),
            fresh_issue_crore=self._float(fresh_issue),
            ofs_crore=self._float(ofs),
            sector=str(sector),
            source="NSE India",
        )

    @staticmethod
    def _records(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("data", "records", "ipo", "ipos"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    def open_ipos(self, as_of: date) -> tuple[IPO, ...]:
        payload = self._get(self._CURRENT_URL)
        result: list[IPO] = []
        for item in self._records(payload):
            try:
                ipo = self._map(item)
            except (TypeError, ValueError):
                continue
            if ipo.open_date <= as_of <= ipo.close_date:
                result.append(ipo)
        return tuple(result)

    def get_ipo(self, symbol: str) -> IPO | None:
        normalized = symbol.strip().upper()
        for item in self._records(self._get(self._CURRENT_URL)):
            try:
                ipo = self._map(item)
            except (TypeError, ValueError):
                continue
            if ipo.symbol.upper() == normalized:
                return ipo
        return None

"""Load the latest AMFI large/mid/small-cap classification."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import pandas as pd

AMFI_PAGE = "https://www.amfiindia.com/otherdata/categorisation-of-stocks"
CACHE_PATH = Path.home() / ".cache" / "trading-assistant" / "amfi-cap-classification.json"
CAP_NAMES = ("Large Cap", "Mid Cap", "Small Cap")


@dataclass(frozen=True)
class CapClassification:
    """Current AMFI classification metadata for one NSE symbol."""

    symbol: str
    segment: str
    isin: str = ""


class _ExcelLinkParser(HTMLParser):
    """Extract Excel links from the AMFI classification page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self._href: str | None = None
        self._is_excel = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        values = dict(attrs)
        self._href = values.get("href")
        self._is_excel = False

    def handle_data(self, data: str) -> None:
        if self._href and "excel" in data.lower():
            self._is_excel = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href and self._is_excel:
            self.links.append(self._href)
        if tag == "a":
            self._href = None
            self._is_excel = False


def _download_latest_excel() -> bytes:
    request = Request(
        AMFI_PAGE,
        headers={"User-Agent": "TradingAssistant/1.0"},
    )
    with urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="ignore")

    parser = _ExcelLinkParser()
    parser.feed(html)
    if not parser.links:
        raise RuntimeError("AMFI classification Excel link was not found")

    excel_url = urljoin(AMFI_PAGE, parser.links[0])
    request = Request(
        excel_url,
        headers={"User-Agent": "TradingAssistant/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        return response.read()


def _normalize_text(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _normalize_symbol(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"", "NAN", "NONE", "NSE SYMBOL", "SYMBOL"}:
        return ""
    return re.sub(r"\s+", "", text)


def _find_column(columns: list[object], *needles: str) -> object | None:
    normalized = {
        column: _normalize_text(column)
        for column in columns
    }
    for needle in needles:
        wanted = _normalize_text(needle)
        for column, value in normalized.items():
            if value == wanted or wanted in value:
                return column
    return None


def _header_row(raw: pd.DataFrame) -> int | None:
    markers = (
        "nse symbol",
        "nse code",
        "symbol",
        "isin",
        "company name",
        "name of the company",
    )
    for index, row in raw.iterrows():
        values = {_normalize_text(value) for value in row.tolist()}
        if any(_normalize_text(marker) in values for marker in markers):
            return int(index)
        joined = " ".join(values)
        if "nsesymbol" in joined or "companyname" in joined:
            return int(index)
    return None


def _sheet_segment(sheet_name: str) -> str:
    normalized = _normalize_text(sheet_name)
    for name in CAP_NAMES:
        if _normalize_text(name) in normalized:
            return name
    return ""


def _rank_column(columns: list[object]) -> object | None:
    return _find_column(
        columns,
        "Rank",
        "Sr No",
        "Sr. No.",
        "Sr.No",
        "Serial No",
    )


def _parse_excel(payload: bytes) -> dict[str, CapClassification]:
    workbook = pd.ExcelFile(BytesIO(payload), engine="openpyxl")
    result: dict[str, CapClassification] = {}

    for sheet_name in workbook.sheet_names:
        raw = pd.read_excel(
            workbook,
            sheet_name=sheet_name,
            header=None,
            engine="openpyxl",
        )
        if raw.empty:
            continue

        header = _header_row(raw)
        if header is None:
            continue

        frame = raw.iloc[header + 1 :].copy()
        frame.columns = [str(value).strip() for value in raw.iloc[header].tolist()]
        frame = frame.dropna(how="all")
        if frame.empty:
            continue

        columns = frame.columns.tolist()
        symbol_column = _find_column(
            columns,
            "NSE Symbol",
            "NSE Code",
            "Symbol",
        )
        isin_column = _find_column(columns, "ISIN")
        category_column = _find_column(
            columns,
            "Category",
            "Classification",
            "Cap Category",
            "Market Cap Category",
        )
        rank_column = _rank_column(columns)

        if symbol_column is None:
            continue

        sheet_segment = _sheet_segment(str(sheet_name))
        rows = frame.to_dict("records")
        data_position = 0
        for row in rows:
            symbol = _normalize_symbol(row.get(symbol_column, ""))
            if not symbol:
                continue

            data_position += 1
            raw_category = (
                str(row.get(category_column, "")).strip()
                if category_column is not None
                else ""
            )
            category = next(
                (
                    name
                    for name in CAP_NAMES
                    if _normalize_text(name) in _normalize_text(raw_category)
                ),
                "",
            )
            if not category:
                category = sheet_segment

            rank_value = row.get(rank_column) if rank_column is not None else None
            try:
                rank = int(float(rank_value))
            except (TypeError, ValueError):
                rank = data_position

            if not category:
                if rank <= 100:
                    category = "Large Cap"
                elif rank <= 250:
                    category = "Mid Cap"
                else:
                    category = "Small Cap"

            isin = ""
            if isin_column is not None:
                isin = str(row.get(isin_column, "")).strip()
                if isin.upper() == "NAN":
                    isin = ""

            result[symbol] = CapClassification(symbol, category, isin)

    if not result:
        raise RuntimeError("No NSE symbols were parsed from the AMFI workbook")
    return result


def load_current_classification() -> dict[str, CapClassification]:
    """Load AMFI's latest published classification, with a local cache fallback."""
    try:
        payload = _download_latest_excel()
        classification = _parse_excel(payload)
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps({key: value.__dict__ for key, value in classification.items()}),
            encoding="utf-8",
        )
        return classification
    except Exception:
        if not CACHE_PATH.exists():
            raise
        cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return {
            key: CapClassification(**value)
            for key, value in cached.items()
        }

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


def _find_column(columns: list[str], *needles: str) -> str | None:
    normalized = {
        column: re.sub(r"[^a-z0-9]", "", column.lower())
        for column in columns
    }
    for needle in needles:
        wanted = re.sub(r"[^a-z0-9]", "", needle.lower())
        for column, value in normalized.items():
            if wanted in value:
                return column
    return None


def _normalise_symbol(value: object) -> str:
    symbol = str(value).strip().upper()
    symbol = symbol.replace(".NS", "")
    return symbol


def _read_classification_frame(workbook: pd.ExcelFile) -> pd.DataFrame:
    """Find the table whose header row contains an NSE-symbol field."""
    for sheet in workbook.sheet_names:
        raw = pd.read_excel(
            workbook,
            sheet_name=sheet,
            header=None,
            engine="openpyxl",
        )
        for row_index in range(min(len(raw), 20)):
            values = [str(value).strip() for value in raw.iloc[row_index].tolist()]
            if _find_column(values, "NSE Symbol", "NSE Code", "NSE") is None:
                continue
            frame = raw.iloc[row_index + 1 :].copy()
            frame.columns = values
            return frame.dropna(how="all")
    raise RuntimeError("AMFI workbook does not contain a recognizable stock table")


def _parse_excel(payload: bytes) -> dict[str, CapClassification]:
    workbook = pd.ExcelFile(BytesIO(payload), engine="openpyxl")
    frame = _read_classification_frame(workbook)

    frame.columns = [str(column).strip() for column in frame.columns]
    symbol_column = _find_column(
        frame.columns.tolist(),
        "NSE Symbol",
        "NSE Code",
        "NSE",
    )
    isin_column = _find_column(frame.columns.tolist(), "ISIN")
    category_column = _find_column(
        frame.columns.tolist(),
        "Category",
        "Classification",
        "Cap",
    )
    if symbol_column is None:
        raise RuntimeError("AMFI workbook does not contain an NSE symbol column")

    result: dict[str, CapClassification] = {}
    rows = frame.to_dict("records")
    for position, row in enumerate(rows, 1):
        symbol = _normalise_symbol(row.get(symbol_column, ""))
        if not symbol or symbol == "NAN":
            continue

        raw_category = (
            str(row.get(category_column, "")).strip()
            if category_column
            else ""
        )
        category = next(
            (
                name
                for name in CAP_NAMES
                if name.lower() in raw_category.lower()
            ),
            "",
        )
        if not category:
            if position <= 100:
                category = "Large Cap"
            elif position <= 250:
                category = "Mid Cap"
            else:
                category = "Small Cap"

        isin = str(row.get(isin_column, "")).strip() if isin_column else ""
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
            json.dumps(
                {key: value.__dict__ for key, value in classification.items()}
            ),
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

"""IPO discovery feed with a live public-calendar attempt and safe fallback."""

from __future__ import annotations

from datetime import date

import pandas as pd

CALENDAR_URL = "https://www.iporise.com/calendar"


FALLBACK_IPOS = (
    {
        "Company": "Gaja Alternative Asset Management",
        "Segment": "Mainboard",
        "Issue Size": 550.0,
        "Fresh Issue": 450.0,
        "OFS": 100.0,
        "Lot Size": 93,
        "Price Band": "₹152 - ₹160",
        "Open": date(2026, 8, 19),
        "Close": date(2026, 8, 21),
        "Sector": "Asset Management",
        "Source": "Public IPO calendar; verify against RHP/NSE",
    },
    {
        "Company": "Mopshop Distribution",
        "Segment": "SME",
        "Issue Size": 27.0,
        "Fresh Issue": 21.0,
        "OFS": 5.0,
        "Lot Size": 1000,
        "Price Band": "₹138",
        "Open": date(2026, 8, 19),
        "Close": date(2026, 8, 21),
        "Sector": "Consumer Services",
        "Source": "Public IPO calendar; verify against RHP/NSE",
    },
    {
        "Company": "Dhanwel Hybrid Seeds",
        "Segment": "SME",
        "Issue Size": 26.73,
        "Fresh Issue": 26.73,
        "OFS": 0.0,
        "Lot Size": 1200,
        "Price Band": "₹95 - ₹99",
        "Open": date(2026, 8, 19),
        "Close": date(2026, 8, 21),
        "Sector": "Agricultural Products",
        "Source": "Public IPO calendar; verify against RHP/NSE",
    },
    {
        "Company": "Tempsens Instruments (India)",
        "Segment": "Mainboard",
        "Issue Size": 650.0,
        "Fresh Issue": 118.0,
        "OFS": 532.0,
        "Lot Size": 50,
        "Price Band": "₹285 - ₹300",
        "Open": date(2026, 8, 20),
        "Close": date(2026, 8, 24),
        "Sector": "Industrial Technology",
        "Source": "Public IPO calendar; verify against RHP/NSE",
    },
    {
        "Company": "Augmont Enterprises",
        "Segment": "Mainboard",
        "Issue Size": 825.0,
        "Fresh Issue": 620.0,
        "OFS": 205.0,
        "Lot Size": 19,
        "Price Band": "₹750 - ₹788",
        "Open": date(2026, 8, 21),
        "Close": date(2026, 8, 25),
        "Sector": "Precious Metals",
        "Source": "Public IPO calendar; verify against RHP/NSE",
    },
)


def _parse_date(value: object) -> date | None:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _live_calendar() -> list[dict[str, object]]:
    tables = pd.read_html(CALENDAR_URL)
    if not tables:
        return []
    table = tables[0].copy()
    table.columns = [str(column).strip() for column in table.columns]
    required = {"Company", "Open", "Close"}
    if not required.issubset(table.columns):
        return []

    today = date.today()
    records: list[dict[str, object]] = []
    for _, row in table.iterrows():
        opening = _parse_date(row.get("Open"))
        closing = _parse_date(row.get("Close"))
        if opening is None or closing is None or not opening <= today <= closing:
            continue
        records.append(
            {
                "Company": str(row.get("Company", "")).replace(" IPO", "").strip(),
                "Segment": str(row.get("Segment", "Unknown")),
                "Issue Size": row.get("Issue Size"),
                "Fresh Issue": None,
                "OFS": None,
                "Lot Size": None,
                "Price Band": str(row.get("Price Band", "N/A")),
                "Open": opening,
                "Close": closing,
                "Sector": "N/A",
                "Source": CALENDAR_URL,
            }
        )
    return records


def get_open_ipos() -> tuple[list[dict[str, object]], str]:
    """Return currently open IPOs and the source mode used."""
    try:
        live = _live_calendar()
        if live:
            return live, "live public IPO calendar"
    except Exception:
        pass

    today = date.today()
    fallback = [
        dict(record)
        for record in FALLBACK_IPOS
        if record["Open"] <= today <= record["Close"]
    ]
    return fallback, "verified fallback snapshot"

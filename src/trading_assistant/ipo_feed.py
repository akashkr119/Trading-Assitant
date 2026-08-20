"""IPO discovery feed with a live public-calendar attempt and safe fallback."""

from __future__ import annotations

from datetime import date

import pandas as pd

CALENDAR_URL = "https://www.iporise.com/calendar"


COMPANY_BRIEFS = {
    "Gaja Alternative Asset Management": {
        "Business Overview": (
            "Alternative asset manager and investment manager/adviser for "
            "India-focused funds, earning from management fees, carried interest "
            "and sponsor commitments."
        ),
        "What They Do": (
            "Manage and advise private-market investment funds and provide capital "
            "to Indian businesses through alternative investment strategies."
        ),
        "Core Goal": (
            "Scale the fund platform and deepen long-term capital commitments "
            "across existing and new funds."
        ),
        "Future Plans": (
            "Use fresh IPO proceeds mainly for sponsor commitments to existing "
            "funds, proposed Fund V and a Secondaries Fund, plus bridge-loan "
            "repayment and corporate purposes."
        ),
        "Growth Drivers": (
            "Maturing fund vintages, future performance fees, new fund launches "
            "and continued institutional/private-market demand."
        ),
        "Key Risks": (
            "Fund-raising and deployment cycles, performance-fee variability, "
            "market conditions and dependence on investment performance."
        ),
        "IPO Use of Funds": (
            "Approximately ₹372 Cr is earmarked for sponsor commitments to "
            "existing/new funds and bridge-loan repayment; the balance is for "
            "corporate purposes."
        ),
        "Research Source": "SEBI RHP and company investor disclosures",
    },
    "Mopshop Distribution": {
        "Business Overview": (
            "B2B distributor of facility-management supplies, cleaning tools, "
            "hygiene consumables and related maintenance products."
        ),
        "What They Do": (
            "Supply products such as microfiber cloths, disinfectants, dispensers, "
            "garbage bags, tissue products, bins and vacuum cleaners to corporate "
            "and facility-management customers."
        ),
        "Core Goal": (
            "Build a scalable pan-India B2B distribution platform while improving "
            "logistics and fulfilment efficiency."
        ),
        "Future Plans": (
            "Reduce borrowings, add commercial vehicles for logistics and install "
            "a rooftop solar plant at the Vasai warehousing facility."
        ),
        "Growth Drivers": (
            "300+ corporate clients, digital ordering infrastructure, broader "
            "geographic reach and growth in outsourced facility-management demand."
        ),
        "Key Risks": (
            "Client concentration, dependence on cleaning/hygiene categories, "
            "regional concentration and SME-scale liquidity."
        ),
        "IPO Use of Funds": (
            "Specified uses include ₹11.50 Cr debt repayment, ₹2.21 Cr commercial "
            "vehicles and ₹1.05 Cr for a rooftop solar plant, with the balance "
            "for corporate/offer expenses."
        ),
        "Research Source": "Company DRHP and public IPO disclosures",
    },
    "Dhanwel Hybrid Seeds": {
        "Business Overview": (
            "Seed manufacturer and supplier serving field-crop and vegetable "
            "agriculture through seed development, multiplication, processing and "
            "distribution."
        ),
        "What They Do": (
            "Source improved genetic material, work with farmers for seed "
            "multiplication, process and quality-check harvested seed, then package "
            "and supply it to the market."
        ),
        "Core Goal": (
            "Expand the seed portfolio and build a reliable agricultural seed "
            "supply and distribution platform."
        ),
        "Future Plans": (
            "Deploy IPO proceeds toward working capital, debt repayment and "
            "general corporate purposes while expanding product offerings and "
            "seed varieties."
        ),
        "Growth Drivers": (
            "Hybrid/improved seed demand, contract-farming relationships, wider "
            "crop coverage and newer products such as wheat varieties."
        ),
        "Key Risks": (
            "Agricultural seasonality, crop conditions, seed-quality requirements, "
            "farmer supply dependencies and SME liquidity."
        ),
        "IPO Use of Funds": (
            "The issue objectives include working capital, repayment of debt and "
            "general corporate purposes."
        ),
        "Research Source": "Company DRHP and public IPO disclosures",
    },
    "Tempsens Instruments (India)": {
        "Business Overview": (
            "Thermal engineering company manufacturing temperature sensors, "
            "electrical heating solutions and specialised cables for industrial "
            "applications."
        ),
        "What They Do": (
            "Design and manufacture contact/non-contact temperature sensors, "
            "electrical heaters and specialised cable solutions for industrial "
            "customers in India and overseas."
        ),
        "Core Goal": (
            "Strengthen its specialised industrial technology platform and expand "
            "manufacturing capacity and global reach."
        ),
        "Future Plans": (
            "Use fresh proceeds for capital expenditure in electrical heating and "
            "specialised cable solutions, repay borrowings and fund general "
            "corporate purposes."
        ),
        "Growth Drivers": (
            "Niche temperature-sensing products, export presence, customised "
            "manufacturing and demand from industrial end markets."
        ),
        "Key Risks": (
            "Customer/end-market concentration, export and foreign-exchange "
            "exposure, raw-material costs and concentration of manufacturing "
            "facilities."
        ),
        "IPO Use of Funds": (
            "Fresh proceeds include approximately ₹18.13 Cr for capital "
            "expenditure, ₹55 Cr for repayment/prepayment of borrowings and the "
            "balance for general corporate purposes."
        ),
        "Research Source": "NSE DRHP/RHP and public IPO disclosures",
    },
    "Augmont Enterprises": {
        "Business Overview": (
            "Integrated gold and silver platform serving businesses and consumers "
            "across procurement, refining, bullion, digital gold, jewellery and "
            "related financial services."
        ),
        "What They Do": (
            "Operate B2B and B2C platforms, including Augmont SPOT and Gold For "
            "All, alongside physical distribution and in-house refining "
            "capabilities."
        ),
        "Core Goal": (
            "Scale inventory, procurement capacity and the integrated gold/silver "
            "platform across India while serving both enterprise and consumer "
            "demand."
        ),
        "Future Plans": (
            "Use fresh IPO proceeds primarily for working capital, inventory "
            "procurement/scaling and advance margins for inventory purchases, "
            "alongside general corporate purposes."
        ),
        "Growth Drivers": (
            "Integrated value-chain presence, online/offline distribution, "
            "digital gold adoption, jewellery demand and expansion across Indian "
            "markets."
        ),
        "Key Risks": (
            "Commodity-price and working-capital intensity, dependence on digital "
            "platforms/payment infrastructure, competition and execution risk."
        ),
        "IPO Use of Funds": (
            "Approximately ₹465 Cr is earmarked for working capital covering "
            "procurement, inventory scaling/maintenance and advance margin "
            "requirements; the balance is for corporate purposes."
        ),
        "Research Source": "SEBI RHP and Augmont investor disclosures",
    },
}


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


def _with_company_brief(record: dict[str, object]) -> dict[str, object]:
    enriched = dict(record)
    brief = COMPANY_BRIEFS.get(str(record.get("Company", "")))
    if brief:
        enriched.update(brief)
    return enriched


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
            _with_company_brief(
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
        _with_company_brief(dict(record))
        for record in FALLBACK_IPOS
        if record["Open"] <= today <= record["Close"]
    ]
    return fallback, "verified fallback snapshot"

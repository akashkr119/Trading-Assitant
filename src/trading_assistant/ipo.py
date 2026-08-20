"""IPO domain models and evidence-first assessment helpers."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class IPO:
    name: str
    symbol: str
    open_date: date
    close_date: date
    price_band: str
    lot_size: int
    issue_size_crore: float
    fresh_issue_crore: float
    ofs_crore: float
    sector: str
    source: str


@dataclass(frozen=True)
class IPOAssessment:
    valuation: str
    financial_quality: str
    long_term_view: str
    listing_view: str
    pros: tuple[str, ...]
    cons: tuple[str, ...]
    risks: tuple[str, ...]


def assess_ipo(
    *,
    revenue_growth: float,
    roe: float,
    roce: float,
    debt_to_equity: float,
    valuation_vs_peers: float,
    fresh_issue_share: float,
) -> IPOAssessment:
    pros: list[str] = []
    cons: list[str] = []
    risks: list[str] = []
    if revenue_growth >= 15:
        pros.append(
            f"Revenue growth is {revenue_growth:.1f}%, indicating meaningful expansion."
        )
    else:
        cons.append(
            f"Revenue growth is only {revenue_growth:.1f}%, limiting the growth case."
        )
    if roce >= 15 and roe >= 15:
        pros.append(f"Returns are healthy: ROCE {roce:.1f}% and ROE {roe:.1f}%.")
    else:
        cons.append(f"Returns are modest: ROCE {roce:.1f}% and ROE {roe:.1f}%.")
    if debt_to_equity <= 0.5:
        pros.append("Balance sheet leverage is relatively low.")
    else:
        risks.append(f"Debt/equity of {debt_to_equity:.2f} needs monitoring.")
    if valuation_vs_peers <= 0:
        pros.append("IPO valuation is not above the selected peer benchmark.")
    else:
        cons.append(
            f"IPO valuation is {valuation_vs_peers:.1f}% above the peer benchmark."
        )
    if fresh_issue_share >= 0.5:
        pros.append("A substantial part of the issue raises fresh capital for the company.")
    else:
        risks.append(
            "The issue is predominantly offer-for-sale, so less capital reaches the company."
        )
    if valuation_vs_peers <= -10:
        valuation = "ATTRACTIVE"
    elif valuation_vs_peers <= 10:
        valuation = "FAIR"
    else:
        valuation = "EXPENSIVE"
    financial_quality = (
        "STRONG" if revenue_growth >= 15 and roe >= 15 and roce >= 15 else "MIXED"
    )
    long_term_view = (
        "CONSIDER"
        if financial_quality == "STRONG" and valuation != "EXPENSIVE"
        else "WAIT / WATCH"
    )
    listing_view = "RESEARCH FURTHER"
    return IPOAssessment(
        valuation=valuation,
        financial_quality=financial_quality,
        long_term_view=long_term_view,
        listing_view=listing_view,
        pros=tuple(pros),
        cons=tuple(cons),
        risks=tuple(risks),
    )

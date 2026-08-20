"""Detailed evidence model for a selected long-term investment."""

from __future__ import annotations

from dataclasses import dataclass

from trading_assistant.analysis.multibagger_scoring import MultibaggerScore
from trading_assistant.data.fundamentals import FundamentalsSnapshot


@dataclass(frozen=True)
class LongTermDetail:
    """Complete explainable view built from normalized fundamentals."""

    symbol: str
    company_name: str
    score: MultibaggerScore
    revenue_cagr: float | None
    earnings_cagr: float | None
    cash_conversion: float | None
    balance_sheet_comment: str
    valuation_comment: str
    reasons: tuple[str, ...]
    risks: tuple[str, ...]
    thesis_killers: tuple[str, ...]


def _cagr(first: float | None, last: float | None, years: float) -> float | None:
    if first is None or last is None or first <= 0 or last <= 0 or years <= 0:
        return None
    return (last / first) ** (1 / years) - 1


def build_long_term_detail(
    snapshot: FundamentalsSnapshot,
    score: MultibaggerScore,
) -> LongTermDetail:
    periods = sorted(snapshot.periods, key=lambda item: item.period_end)
    revenue_cagr = earnings_cagr = None
    if len(periods) >= 2:
        first, last = periods[0], periods[-1]
        years = max((last.period_end - first.period_end).days / 365.25, 1.0)
        revenue_cagr = _cagr(first.revenue, last.revenue, years)
        earnings_cagr = _cagr(first.earnings, last.earnings, years)

    conversions = [
        period.operating_cash_flow / period.earnings
        for period in periods
        if period.operating_cash_flow is not None and period.earnings not in (None, 0)
    ]
    cash_conversion = sum(conversions) / len(conversions) if conversions else None

    if snapshot.debt_to_equity is None:
        balance_sheet_comment = (
            "Debt-to-equity is unavailable; balance-sheet risk needs verification."
        )
    elif snapshot.debt_to_equity <= 0.5:
        balance_sheet_comment = "Current debt-to-equity is relatively moderate."
    else:
        balance_sheet_comment = "Leverage needs closer review before a long-term decision."

    if snapshot.pe_ratio is None:
        valuation_comment = "P/E is unavailable; valuation cannot be concluded from this metric."
    elif snapshot.pe_ratio <= 20:
        valuation_comment = "P/E is below or around the configured moderate-valuation threshold."
    else:
        valuation_comment = (
            "P/E is elevated; future returns may depend heavily on continued growth."
        )

    thesis_killers = (
        "Sustained revenue or earnings growth deterioration.",
        "Material decline in ROE/ROCE or cash conversion.",
        "Rapid debt growth without productive returns on capital.",
        "Material governance, accounting, or competitive-position deterioration.",
    )

    return LongTermDetail(
        symbol=snapshot.symbol,
        company_name=snapshot.company_name,
        score=score,
        revenue_cagr=revenue_cagr,
        earnings_cagr=earnings_cagr,
        cash_conversion=cash_conversion,
        balance_sheet_comment=balance_sheet_comment,
        valuation_comment=valuation_comment,
        reasons=score.reasons,
        risks=score.risks,
        thesis_killers=thesis_killers,
    )

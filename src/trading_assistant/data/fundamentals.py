"""Provider-neutral normalized fundamentals contracts for long-term research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class FinancialPeriod:
    """One reported financial period."""

    period_end: date
    revenue: float | None
    earnings: float | None
    eps: float | None
    operating_cash_flow: float | None
    free_cash_flow: float | None
    debt: float | None
    equity: float | None


@dataclass(frozen=True)
class FundamentalsSnapshot:
    """Normalized company fundamentals with explicit source/freshness metadata."""

    symbol: str
    company_name: str
    as_of: datetime
    source: str
    periods: tuple[FinancialPeriod, ...]
    roe: float | None
    roce: float | None
    debt_to_equity: float | None
    market_cap: float | None
    pe_ratio: float | None
    pb_ratio: float | None
    ev_to_ebitda: float | None
    sector: str | None = None

    def has_required_financial_history(self, minimum_periods: int = 3) -> bool:
        """Return whether enough reported periods exist for long-term trend analysis."""
        complete = [
            period
            for period in self.periods
            if period.revenue is not None and period.earnings is not None
        ]
        return len(complete) >= minimum_periods

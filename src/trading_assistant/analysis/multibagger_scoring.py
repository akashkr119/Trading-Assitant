"""Evidence-based long-term stock scoring."""

from __future__ import annotations

from dataclasses import dataclass

from trading_assistant.data.fundamentals import FundamentalsSnapshot


@dataclass(frozen=True)
class MultibaggerScore:
    """Long-term score with component evidence and explicit data coverage."""

    overall: float
    growth: float
    profitability: float
    financial_strength: float
    cash_flow: float
    valuation: float
    coverage: float
    reasons: tuple[str, ...]
    risks: tuple[str, ...]


def _bounded(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _growth_score(snapshot: FundamentalsSnapshot) -> float:
    periods = sorted(snapshot.periods, key=lambda item: item.period_end)
    complete = [item for item in periods if item.revenue and item.earnings]
    if len(complete) < 2:
        return 0.0
    first, last = complete[0], complete[-1]
    years = max((last.period_end - first.period_end).days / 365.25, 1.0)
    revenue_cagr = ((last.revenue / first.revenue) ** (1 / years) - 1) * 100
    earnings_cagr = ((last.earnings / first.earnings) ** (1 / years) - 1) * 100
    return _bounded(50 + revenue_cagr + earnings_cagr * 0.75)


def _profitability_score(snapshot: FundamentalsSnapshot) -> float:
    values = [value for value in (snapshot.roe, snapshot.roce) if value is not None]
    if not values:
        return 0.0
    return _bounded(sum(values) / len(values) * 3.0)


def _financial_strength_score(snapshot: FundamentalsSnapshot) -> float:
    if snapshot.debt_to_equity is None:
        return 0.0
    return _bounded(100 - snapshot.debt_to_equity * 40)


def _cash_flow_score(snapshot: FundamentalsSnapshot) -> float:
    periods = [item for item in snapshot.periods if item.earnings is not None]
    if not periods:
        return 0.0
    available = [
        item
        for item in periods
        if item.operating_cash_flow is not None and item.earnings != 0
    ]
    if not available:
        return 0.0
    conversion = sum(
        item.operating_cash_flow / abs(item.earnings) for item in available
    ) / len(available)
    return _bounded(conversion * 100)


def _valuation_score(snapshot: FundamentalsSnapshot) -> float:
    if snapshot.pe_ratio is None or snapshot.pe_ratio <= 0:
        return 0.0
    return _bounded(100 - snapshot.pe_ratio * 2.0)


def score_multibagger(snapshot: FundamentalsSnapshot) -> MultibaggerScore:
    """Score a company without substituting missing metrics with zero-quality claims."""
    components = {
        "growth": _growth_score(snapshot),
        "profitability": _profitability_score(snapshot),
        "financial_strength": _financial_strength_score(snapshot),
        "cash_flow": _cash_flow_score(snapshot),
        "valuation": _valuation_score(snapshot),
    }
    available = [value for value in components.values() if value > 0]
    coverage = len(available) / len(components) * 100
    overall = sum(available) / len(available) if available else 0.0

    reasons: list[str] = []
    risks: list[str] = []
    if components["growth"] >= 70:
        reasons.append("Strong historical revenue and earnings growth.")
    if components["profitability"] >= 70:
        reasons.append("Healthy return metrics support efficient capital deployment.")
    if components["financial_strength"] >= 70:
        reasons.append("Balance-sheet leverage is currently manageable.")
    if components["cash_flow"] >= 70:
        reasons.append("Operating cash flow shows healthy conversion of reported earnings.")
    if components["valuation"] < 50:
        risks.append("Current P/E indicates valuation may limit future returns.")
    if coverage < 80:
        risks.append("Fundamental data coverage is incomplete; research should continue.")

    return MultibaggerScore(
        overall=round(overall, 1),
        growth=round(components["growth"], 1),
        profitability=round(components["profitability"], 1),
        financial_strength=round(components["financial_strength"], 1),
        cash_flow=round(components["cash_flow"], 1),
        valuation=round(components["valuation"], 1),
        coverage=round(coverage, 1),
        reasons=tuple(reasons),
        risks=tuple(risks),
    )

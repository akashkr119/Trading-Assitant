"""Evidence-backed long-term investment scoring and thesis generation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LongTermMetrics:
    revenue_cagr: float
    earnings_cagr: float
    roce: float
    roe: float
    debt_to_equity: float
    fcf_positive: bool
    cash_conversion: float
    valuation_percentile: float
    moat_score: float
    runway_score: float
    management_score: float
    governance_risk: float


@dataclass(frozen=True)
class LongTermAssessment:
    score: float
    business_quality: float
    growth_potential: float
    financial_strength: float
    profitability: float
    cash_flow: float
    management: float
    moat: float
    runway: float
    valuation: float
    risk: float
    verdict: str
    reasons: tuple[str, ...]
    risks: tuple[str, ...]
    thesis_breaks: tuple[str, ...]


def assess_long_term(metrics: LongTermMetrics) -> LongTermAssessment:
    """Score a company from supplied evidence; never invent missing fundamentals."""
    growth = min(
        100.0,
        max(0.0, metrics.revenue_cagr * 2.5 + metrics.earnings_cagr * 1.5),
    )
    profitability = min(
        100.0,
        max(0.0, metrics.roce * 2.2 + metrics.roe * 0.5),
    )
    financial = min(100.0, max(0.0, 100 - metrics.debt_to_equity * 35))
    cash_flow = min(
        100.0,
        max(0.0, (60 if metrics.fcf_positive else 25) + metrics.cash_conversion * 40),
    )
    valuation = min(100.0, max(0.0, 100 - metrics.valuation_percentile))
    risk = min(100.0, max(0.0, 100 - metrics.governance_risk))
    score = round(
        growth * 0.18
        + profitability * 0.16
        + financial * 0.12
        + cash_flow * 0.12
        + metrics.management_score * 0.10
        + metrics.moat_score * 0.10
        + metrics.runway_score * 0.12
        + valuation * 0.06
        + risk * 0.04,
        1,
    )
    if score >= 80:
        verdict = "STRONG LONG-TERM CANDIDATE"
    elif score >= 65:
        verdict = "WATCHLIST"
    else:
        verdict = "HIGH RISK / AVOID"
    reasons = (
        f"Revenue CAGR is {metrics.revenue_cagr:.1f}% and earnings CAGR is "
        f"{metrics.earnings_cagr:.1f}%.",
        f"ROCE is {metrics.roce:.1f}% and the runway score is "
        f"{metrics.runway_score:.0f}/100.",
        f"Moat score is {metrics.moat_score:.0f}/100 and management score is "
        f"{metrics.management_score:.0f}/100.",
        "Free cash flow is positive."
        if metrics.fcf_positive
        else "Free cash flow is not consistently positive.",
    )
    risks = (
        f"Debt/equity is {metrics.debt_to_equity:.2f}.",
        f"Valuation percentile is {metrics.valuation_percentile:.0f}/100.",
        f"Governance-risk score is {metrics.governance_risk:.0f}/100.",
    )
    thesis_breaks = (
        "Revenue growth falls materially below the long-term thesis assumption.",
        "ROCE deteriorates for sustained periods.",
        "Debt rises without a corresponding increase in productive earnings capacity.",
        "Cash generation persistently diverges from reported profit.",
        "Material governance or promoter-pledge concerns emerge.",
    )
    return LongTermAssessment(
        score=score,
        business_quality=round((metrics.moat_score + metrics.management_score) / 2, 1),
        growth_potential=round(growth, 1),
        financial_strength=round(financial, 1),
        profitability=round(profitability, 1),
        cash_flow=round(cash_flow, 1),
        management=metrics.management_score,
        moat=metrics.moat_score,
        runway=metrics.runway_score,
        valuation=round(valuation, 1),
        risk=round(risk, 1),
        verdict=verdict,
        reasons=reasons,
        risks=risks,
        thesis_breaks=thesis_breaks,
    )

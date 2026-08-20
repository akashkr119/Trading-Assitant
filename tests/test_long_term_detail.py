from datetime import date, datetime, timezone

from trading_assistant.analysis.long_term_detail import build_long_term_detail
from trading_assistant.analysis.multibagger_scoring import score_multibagger
from trading_assistant.data.fundamentals import FinancialPeriod, FundamentalsSnapshot


def test_detail_contains_growth_cash_conversion_and_thesis_killers() -> None:
    snapshot = FundamentalsSnapshot(
        symbol="TEST",
        company_name="Test Company",
        as_of=datetime.now(timezone.utc),
        source="test",
        periods=(
            FinancialPeriod(date(2023, 3, 31), 100, 10, 1, 12, 8, 20, 100),
            FinancialPeriod(date(2024, 3, 31), 125, 14, 1.4, 16, 10, 18, 110),
            FinancialPeriod(date(2025, 3, 31), 160, 20, 2, 24, 16, 15, 125),
        ),
        roe=20,
        roce=24,
        debt_to_equity=0.2,
        market_cap=1000,
        pe_ratio=18,
        pb_ratio=3,
        ev_to_ebitda=12,
    )
    score = score_multibagger(snapshot)
    detail = build_long_term_detail(snapshot, score)
    assert detail.revenue_cagr is not None
    assert detail.earnings_cagr is not None
    assert detail.cash_conversion is not None
    assert detail.thesis_killers
    assert detail.balance_sheet_comment
    assert detail.valuation_comment

from datetime import date, datetime, timezone

from trading_assistant.data.fundamentals import FinancialPeriod, FundamentalsSnapshot


def test_fundamentals_snapshot_requires_reported_history() -> None:
    periods = tuple(
        FinancialPeriod(
            period_end=date(2024 + index, 3, 31),
            revenue=100.0 + index,
            earnings=10.0 + index,
            eps=1.0 + index,
            operating_cash_flow=12.0,
            free_cash_flow=8.0,
            debt=20.0,
            equity=80.0,
        )
        for index in range(3)
    )
    snapshot = FundamentalsSnapshot(
        symbol="TEST",
        company_name="Test Company",
        as_of=datetime.now(timezone.utc),
        source="test",
        periods=periods,
        roe=15.0,
        roce=18.0,
        debt_to_equity=0.25,
        market_cap=1000.0,
        pe_ratio=20.0,
        pb_ratio=3.0,
        ev_to_ebitda=12.0,
    )
    assert snapshot.has_required_financial_history()


def test_missing_financial_history_is_not_treated_as_zero() -> None:
    snapshot = FundamentalsSnapshot(
        symbol="TEST",
        company_name="Test Company",
        as_of=datetime.now(timezone.utc),
        source="test",
        periods=(
            FinancialPeriod(
                period_end=date(2026, 3, 31),
                revenue=None,
                earnings=None,
                eps=None,
                operating_cash_flow=None,
                free_cash_flow=None,
                debt=None,
                equity=None,
            ),
        ),
        roe=None,
        roce=None,
        debt_to_equity=None,
        market_cap=None,
        pe_ratio=None,
        pb_ratio=None,
        ev_to_ebitda=None,
    )
    assert not snapshot.has_required_financial_history()

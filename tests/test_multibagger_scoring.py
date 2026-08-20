from datetime import date, datetime, timezone

from trading_assistant.analysis.multibagger_scoring import score_multibagger
from trading_assistant.data.fundamentals import FinancialPeriod, FundamentalsSnapshot


def _snapshot() -> FundamentalsSnapshot:
    periods = tuple(
        FinancialPeriod(
            period_end=date(2022 + index, 3, 31),
            revenue=100.0 * (1.2**index),
            earnings=10.0 * (1.3**index),
            eps=1.0,
            operating_cash_flow=13.0 * (1.3**index),
            free_cash_flow=8.0,
            debt=20.0,
            equity=100.0,
        )
        for index in range(4)
    )
    return FundamentalsSnapshot(
        symbol="TEST",
        company_name="Test Company",
        as_of=datetime.now(timezone.utc),
        source="test",
        periods=periods,
        roe=20.0,
        roce=24.0,
        debt_to_equity=0.2,
        market_cap=1000.0,
        pe_ratio=20.0,
        pb_ratio=4.0,
        ev_to_ebitda=14.0,
    )


def test_score_returns_components_and_coverage() -> None:
    result = score_multibagger(_snapshot())
    assert 0 <= result.overall <= 100
    assert result.coverage == 100.0
    assert result.growth > 50
    assert result.profitability > 50
    assert result.financial_strength > 50


def test_missing_data_reduces_coverage() -> None:
    snapshot = _snapshot()
    incomplete = FundamentalsSnapshot(
        **{**snapshot.__dict__, "pe_ratio": None, "roe": None, "roce": None}
    )
    result = score_multibagger(incomplete)
    assert result.coverage < 100
    assert any("coverage" in risk.lower() for risk in result.risks)

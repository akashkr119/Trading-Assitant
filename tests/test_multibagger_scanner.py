from datetime import date, datetime, timezone

from trading_assistant.analysis.multibagger_scanner import MultibaggerScanner
from trading_assistant.data.fundamentals import FinancialPeriod, FundamentalsSnapshot


class FakeProvider:
    def __init__(self, snapshots: dict[str, FundamentalsSnapshot]) -> None:
        self.snapshots = snapshots

    def get_fundamentals(self, symbol: str) -> FundamentalsSnapshot:
        return self.snapshots[symbol]


def snapshot(symbol: str, roe: float) -> FundamentalsSnapshot:
    periods = tuple(
        FinancialPeriod(
            period_end=date(2023 + index, 3, 31),
            revenue=100.0 * (1.2**index),
            earnings=10.0 * (1.25**index),
            eps=1.0,
            operating_cash_flow=12.0,
            free_cash_flow=8.0,
            debt=20.0,
            equity=100.0,
        )
        for index in range(3)
    )
    return FundamentalsSnapshot(
        symbol=symbol,
        company_name=symbol,
        as_of=datetime.now(timezone.utc),
        source="test",
        periods=periods,
        roe=roe,
        roce=22.0,
        debt_to_equity=0.2,
        market_cap=1000.0,
        pe_ratio=18.0,
        pb_ratio=3.0,
        ev_to_ebitda=12.0,
    )


def test_scanner_ranks_candidates() -> None:
    provider = FakeProvider({"AAA": snapshot("AAA", 25.0), "BBB": snapshot("BBB", 10.0)})
    result = MultibaggerScanner(provider).scan(["AAA", "BBB"], limit=1)
    assert len(result.candidates) == 1
    assert result.candidates[0].symbol == "AAA"
    assert not result.failures

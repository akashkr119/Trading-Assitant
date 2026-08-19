import pytest

from trading_assistant.analysis.stock_ranking import StockSnapshot, rank_stocks


def test_stock_ranking_orders_candidates_by_weighted_score() -> None:
    stocks = [
        StockSnapshot("WEAK", "IT", 50, 40, 50, 40, 40, 40, 30),
        StockSnapshot("STRONG", "IT", 90, 95, 90, 85, 80, 90, 90),
    ]

    ranked = rank_stocks(stocks)

    assert [item.symbol for item in ranked] == ["STRONG", "WEAK"]
    assert ranked[0].rank == 1
    assert ranked[0].score > ranked[1].score


def test_stock_ranking_can_filter_by_sector_strength() -> None:
    stocks = [
        StockSnapshot("GOOD", "BANK", 80, 80, 80, 80, 80, 80, 80),
        StockSnapshot("BAD", "IT", 100, 100, 100, 100, 100, 100, 100),
    ]
    sectors = {"BANK": 85, "IT": 45}

    ranked = rank_stocks(stocks, minimum_sector_score=60, sector_scores=sectors)

    assert [item.symbol for item in ranked] == ["GOOD"]


def test_negative_weight_is_rejected() -> None:
    stock = StockSnapshot("T", "IT", 50, 50, 50, 50, 50, 50, 50)
    with pytest.raises(ValueError, match="negative"):
        rank_stocks([stock], weights={"trend": -1})

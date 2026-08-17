from trading_assistant.analysis.candidates import select_candidates
from trading_assistant.analysis.stock_ranking import StockRanking


def test_select_candidates_requires_strong_sector_and_stock() -> None:
    rankings = [
        StockRanking("A", "BANK", 90, 1),
        StockRanking("B", "IT", 95, 2),
        StockRanking("C", "BANK", 55, 3),
    ]
    candidates = select_candidates(
        rankings,
        {"BANK": 80, "IT": 50},
    )
    assert [item.symbol for item in candidates] == ["A"]
    assert candidates[0].sector_score == 80
    assert "Strong sector" in candidates[0].reason


def test_candidate_limit_is_respected() -> None:
    rankings = [
        StockRanking("A", "BANK", 90, 1),
        StockRanking("B", "BANK", 89, 2),
    ]
    candidates = select_candidates(rankings, {"BANK": 80}, limit=1)
    assert [item.symbol for item in candidates] == ["A"]

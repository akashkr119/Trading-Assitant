"""Candidate watchlist selection from sector and stock rankings."""

from __future__ import annotations

from dataclasses import dataclass

from trading_assistant.analysis.stock_ranking import StockRanking


@dataclass(frozen=True)
class Candidate:
    symbol: str
    sector: str
    stock_score: float
    sector_score: float
    rank: int
    reason: str


def select_candidates(
    rankings: list[StockRanking],
    sector_scores: dict[str, float],
    *,
    minimum_sector_score: float = 60.0,
    minimum_stock_score: float = 60.0,
    limit: int = 10,
) -> list[Candidate]:
    """Select strongest stocks from sufficiently strong sectors."""
    if limit <= 0:
        raise ValueError("limit must be positive")

    candidates: list[Candidate] = []
    for ranking in rankings:
        sector_score = sector_scores.get(ranking.sector)
        if sector_score is None:
            continue
        if sector_score < minimum_sector_score:
            continue
        if ranking.score < minimum_stock_score:
            continue

        candidates.append(
            Candidate(
                symbol=ranking.symbol,
                sector=ranking.sector,
                stock_score=ranking.score,
                sector_score=sector_score,
                rank=len(candidates) + 1,
                reason=(
                    f"Strong sector ({sector_score:.1f}/100) and "
                    f"strong stock score ({ranking.score:.1f}/100)."
                ),
            )
        )
        if len(candidates) >= limit:
            break

    return candidates

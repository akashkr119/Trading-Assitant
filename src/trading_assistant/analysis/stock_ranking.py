"""Stock ranking for selecting candidates before signal generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StockSnapshot:
    """Normalized stock features used by the V1 ranking model.

    Each feature is expected on a 0-100 scale. The ranking model does not
    produce a trade signal; it only prioritizes stocks for deeper analysis.
    """

    symbol: str
    sector: str
    trend: float
    relative_strength: float
    vwap_position: float
    momentum: float
    volume: float
    price_action: float
    setup_quality: float


@dataclass(frozen=True)
class StockRanking:
    symbol: str
    sector: str
    score: float
    rank: int = 0


DEFAULT_WEIGHTS = {
    "trend": 20.0,
    "relative_strength": 20.0,
    "vwap_position": 15.0,
    "momentum": 15.0,
    "volume": 10.0,
    "price_action": 10.0,
    "setup_quality": 10.0,
}


def rank_stocks(
    stocks: list[StockSnapshot],
    *,
    weights: dict[str, float] | None = None,
    minimum_sector_score: float | None = None,
    sector_scores: dict[str, float] | None = None,
) -> list[StockRanking]:
    """Rank candidate stocks from strongest to weakest.

    Sector filtering is optional so the function remains reusable for a
    broader universe. Ties are resolved deterministically by symbol.
    """
    if not stocks:
        return []

    selected_weights = weights or DEFAULT_WEIGHTS
    if any(weight < 0 for weight in selected_weights.values()):
        raise ValueError("weights cannot be negative")
    total_weight = sum(selected_weights.values())
    if total_weight <= 0:
        raise ValueError("at least one positive weight is required")

    candidates = stocks
    if minimum_sector_score is not None and sector_scores is not None:
        candidates = [
            stock
            for stock in stocks
            if sector_scores.get(stock.sector, -1) >= minimum_sector_score
        ]

    rankings: list[StockRanking] = []
    for stock in candidates:
        values = {
            "trend": stock.trend,
            "relative_strength": stock.relative_strength,
            "vwap_position": stock.vwap_position,
            "momentum": stock.momentum,
            "volume": stock.volume,
            "price_action": stock.price_action,
            "setup_quality": stock.setup_quality,
        }
        score = sum(values[name] * weight for name, weight in selected_weights.items()) / total_weight
        rankings.append(
            StockRanking(symbol=stock.symbol, sector=stock.sector, score=round(score, 2))
        )

    rankings.sort(key=lambda item: (-item.score, item.symbol))
    return [
        StockRanking(symbol=item.symbol, sector=item.sector, score=item.score, rank=index)
        for index, item in enumerate(rankings, start=1)
    ]

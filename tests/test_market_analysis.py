from trading_assistant.analysis.market import (
    MarketInputs,
    MarketRegime,
    SectorInputs,
    rank_sectors,
    score_market,
    score_sector,
)


def test_market_score_uses_v1_weights() -> None:
    result = score_market(
        MarketInputs(
            nifty_trend=100,
            banknifty_trend=100,
            breadth=100,
            momentum=100,
            volatility=100,
        )
    )
    assert result.score == 100
    assert result.regime == MarketRegime.STRONG_BULLISH


def test_market_regime_boundaries() -> None:
    result = score_market(
        MarketInputs(
            nifty_trend=45,
            banknifty_trend=45,
            breadth=45,
            momentum=45,
            volatility=45,
        )
    )
    assert result.regime == MarketRegime.NEUTRAL


def test_sector_ranking_is_strongest_first() -> None:
    weak_inputs = SectorInputs(
        trend=40,
        relative_strength=40,
        volume=40,
        breadth=40,
        momentum=40,
    )
    strong_inputs = SectorInputs(
        trend=90,
        relative_strength=90,
        volume=90,
        breadth=90,
        momentum=90,
    )
    weak = score_sector("IT", weak_inputs)
    strong = score_sector("Banking", strong_inputs)
    assert [item.sector for item in rank_sectors([weak, strong])] == [
        "Banking",
        "IT",
    ]

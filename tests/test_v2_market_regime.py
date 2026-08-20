from trading_assistant.v2.market_regime import (
    MarketObservation,
    MarketRegime,
    classify_market_regime,
)


def test_bullish_regime_requires_supportive_observations() -> None:
    result = classify_market_regime(
        MarketObservation(
            index_trend=0.8,
            breadth_pct=72,
            volume_strength=0.5,
            sector_strength=0.6,
        )
    )

    assert result.regime == MarketRegime.BULLISH
    assert result.score > 0.35
    assert result.confidence == 100.0


def test_bearish_regime_is_transparent() -> None:
    result = classify_market_regime(
        MarketObservation(
            index_trend=-0.8,
            breadth_pct=25,
            volume_strength=-0.4,
            sector_strength=-0.5,
        )
    )

    assert result.regime == MarketRegime.BEARISH
    assert result.score < -0.35
    assert result.reasons


def test_high_volatility_takes_priority() -> None:
    result = classify_market_regime(
        MarketObservation(
            index_trend=0.8,
            breadth_pct=70,
            volatility_percentile=92,
        )
    )

    assert result.regime == MarketRegime.HIGH_VOLATILITY


def test_missing_data_does_not_create_false_confidence() -> None:
    result = classify_market_regime(MarketObservation())

    assert result.regime == MarketRegime.NEUTRAL
    assert result.score == 0.0
    assert result.confidence == 0.0

"""Pure V2 market-regime model.

The first V2 slice is intentionally provider-agnostic. It converts already
available market observations into a transparent regime without fetching data
or changing V1 scanner behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MarketRegime(StrEnum):
    """High-level market state used by V2 decision support."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"


@dataclass(frozen=True)
class MarketObservation:
    """Normalized observations supplied by a future market-data adapter."""

    index_trend: float | None = None
    breadth_pct: float | None = None
    volatility_percentile: float | None = None
    volume_strength: float | None = None
    sector_strength: float | None = None


@dataclass(frozen=True)
class MarketRegimeResult:
    """Transparent market-regime decision and supporting score."""

    regime: MarketRegime
    score: float
    confidence: float
    reasons: tuple[str, ...]


def classify_market_regime(observation: MarketObservation) -> MarketRegimeResult:
    """Classify the market using only observations that are actually present."""
    signals: list[float] = []
    reasons: list[str] = []

    if observation.index_trend is not None:
        signals.append(max(-1.0, min(1.0, observation.index_trend)))
        reasons.append(
            "Index trend supports bullish conditions."
            if observation.index_trend > 0.2
            else "Index trend supports bearish conditions."
            if observation.index_trend < -0.2
            else "Index trend is broadly neutral."
        )

    if observation.breadth_pct is not None:
        breadth_signal = max(-1.0, min(1.0, (observation.breadth_pct - 50) / 50))
        signals.append(breadth_signal)
        reasons.append(
            "Market breadth favors advancing stocks."
            if observation.breadth_pct > 60
            else "Market breadth favors declining stocks."
            if observation.breadth_pct < 40
            else "Market breadth is balanced."
        )

    if observation.volume_strength is not None:
        signals.append(max(-1.0, min(1.0, observation.volume_strength)))
        reasons.append(
            "Participation is strong."
            if observation.volume_strength > 0.2
            else "Participation is subdued."
        )

    if observation.sector_strength is not None:
        signals.append(max(-1.0, min(1.0, observation.sector_strength)))
        reasons.append(
            "Sector participation is supportive."
            if observation.sector_strength > 0.2
            else "Sector participation is weak."
        )

    score = sum(signals) / len(signals) if signals else 0.0
    confidence = min(100.0, len(signals) / 4 * 100)

    if (
        observation.volatility_percentile is not None
        and observation.volatility_percentile >= 85
    ):
        regime = MarketRegime.HIGH_VOLATILITY
        reasons.append("Volatility is in the high-risk regime.")
    elif score >= 0.35:
        regime = MarketRegime.BULLISH
    elif score <= -0.35:
        regime = MarketRegime.BEARISH
    else:
        regime = MarketRegime.NEUTRAL

    return MarketRegimeResult(
        regime=regime,
        score=round(score, 3),
        confidence=round(confidence, 1),
        reasons=tuple(reasons),
    )

"""Provider-neutral adapter for live NSE observations.

The adapter consumes normalized observations from an existing market-data
provider. It intentionally does not own HTTP requests or broker credentials.
"""

from __future__ import annotations

from dataclasses import dataclass

from trading_assistant.v2.market_regime import (
    MarketObservation,
    MarketRegimeResult,
    classify_market_regime,
)


@dataclass(frozen=True)
class NSEObservation:
    """Raw normalized NSE observations supplied by a provider adapter."""

    nifty_trend: float | None = None
    breadth_pct: float | None = None
    volatility_percentile: float | None = None
    volume_strength: float | None = None
    sector_strength: float | None = None


def evaluate_nse_market(observation: NSEObservation) -> MarketRegimeResult:
    """Convert an NSE observation into the V2 Market Brain regime."""
    return classify_market_regime(
        MarketObservation(
            index_trend=observation.nifty_trend,
            breadth_pct=observation.breadth_pct,
            volatility_percentile=observation.volatility_percentile,
            volume_strength=observation.volume_strength,
            sector_strength=observation.sector_strength,
        )
    )

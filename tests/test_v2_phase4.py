from datetime import datetime, timedelta, timezone

from trading_assistant.v2.live_nse import NSEObservation, evaluate_nse_market
from trading_assistant.v2.market_regime import MarketRegime
from trading_assistant.v2.stale_data import is_fresh


def test_nse_adapter_maps_observations_to_market_brain() -> None:
    result = evaluate_nse_market(
        NSEObservation(
            nifty_trend=0.8,
            breadth_pct=70,
            volatility_percentile=40,
            volume_strength=0.4,
            sector_strength=0.5,
        )
    )

    assert result.regime == MarketRegime.BULLISH
    assert result.confidence == 100.0


def test_nse_adapter_preserves_high_volatility_guard() -> None:
    result = evaluate_nse_market(
        NSEObservation(
            nifty_trend=0.8,
            breadth_pct=70,
            volatility_percentile=90,
        )
    )

    assert result.regime == MarketRegime.HIGH_VOLATILITY


def test_stale_data_is_rejected() -> None:
    now = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)
    assert is_fresh(now - timedelta(seconds=30), now=now)
    assert not is_fresh(now - timedelta(seconds=61), now=now)
    assert not is_fresh(now + timedelta(seconds=1), now=now)

import pytest

from trading_assistant.v2.sector_rotation import SectorObservation, rank_sectors
from trading_assistant.v2.setup_lifecycle import (
    SetupLifecycle,
    SetupStage,
    advance_setup,
)
from trading_assistant.v2.wait_no_trade import TradeContext, TradeState, decide_trade


def test_sector_rotation_ranks_leaders_first() -> None:
    result = rank_sectors(
        [
            SectorObservation("IT", 0.8, 0.7, 0.5, 75),
            SectorObservation("Pharma", -0.5, -0.4, -0.3, 30),
        ]
    )
    assert result[0].name == "IT"
    assert result[0].rank == 1
    assert result[0].interpretation == "LEADING"


def test_no_trade_when_risk_reward_is_missing() -> None:
    result = decide_trade(
        TradeContext(0.8, 90, None, True),
        "BUY",
    )
    assert result.state == TradeState.NO_TRADE


def test_wait_when_timeframes_conflict() -> None:
    result = decide_trade(
        TradeContext(0.8, 82, 2.0, False),
        "BUY",
    )
    assert result.state == TradeState.WAIT
    assert result.reasons


def test_confirmed_trade_requires_alignment_and_risk() -> None:
    result = decide_trade(
        TradeContext(0.7, 82, 2.2, True),
        "BUY",
    )
    assert result.state == TradeState.BUY


def test_setup_lifecycle_allows_ordered_transition() -> None:
    setup = SetupLifecycle("RELIANCE", "BUY", SetupStage.WATCH, 70, "Close below support")
    setup = advance_setup(setup, SetupStage.FORMING)
    setup = advance_setup(setup, SetupStage.NEAR_TRIGGER)
    assert setup.stage == SetupStage.NEAR_TRIGGER


def test_setup_lifecycle_rejects_invalid_transition() -> None:
    setup = SetupLifecycle("RELIANCE", "BUY", SetupStage.WATCH, 70, "Close below support")
    with pytest.raises(ValueError):
        advance_setup(setup, SetupStage.ACTIVE)

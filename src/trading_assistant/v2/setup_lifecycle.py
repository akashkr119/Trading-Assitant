"""State machine for tracking V2 opportunities from watch to exit."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SetupStage(StrEnum):
    WATCH = "WATCH"
    FORMING = "FORMING"
    NEAR_TRIGGER = "NEAR_TRIGGER"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    TARGET = "TARGET"
    EXIT = "EXIT"


@dataclass(frozen=True)
class SetupLifecycle:
    """Immutable opportunity state used by a future persistence layer."""

    symbol: str
    direction: str
    stage: SetupStage
    score: float
    invalidation: str


_ALLOWED: dict[SetupStage, tuple[SetupStage, ...]] = {
    SetupStage.WATCH: (SetupStage.FORMING, SetupStage.EXIT),
    SetupStage.FORMING: (SetupStage.NEAR_TRIGGER, SetupStage.EXIT),
    SetupStage.NEAR_TRIGGER: (SetupStage.CONFIRMED, SetupStage.EXIT),
    SetupStage.CONFIRMED: (SetupStage.ACTIVE, SetupStage.EXIT),
    SetupStage.ACTIVE: (SetupStage.TARGET, SetupStage.EXIT),
    SetupStage.TARGET: (SetupStage.ACTIVE, SetupStage.EXIT),
    SetupStage.EXIT: (),
}


def advance_setup(setup: SetupLifecycle, next_stage: SetupStage) -> SetupLifecycle:
    """Advance only through valid lifecycle transitions."""
    if next_stage not in _ALLOWED[setup.stage]:
        raise ValueError(
            f"Invalid setup transition: {setup.stage.value} -> {next_stage.value}"
        )
    return SetupLifecycle(
        symbol=setup.symbol,
        direction=setup.direction,
        stage=next_stage,
        score=setup.score,
        invalidation=setup.invalidation,
    )

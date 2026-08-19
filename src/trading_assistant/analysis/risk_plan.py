"""Setup-aware entry, stop-loss, target and risk/reward calculations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class RiskPlan:
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward_1: float
    risk_reward_2: float
    invalidation_level: float


class RiskPlanError(ValueError):
    """Raised when a valid trade plan cannot be calculated."""


def build_risk_plan(
    *,
    side: str,
    entry: float,
    stop_loss: float,
    target_1: float,
    target_2: float,
    minimum_risk_reward: float = 1.5,
) -> RiskPlan:
    """Validate a precomputed structure-based trade plan.

    Entry, stop and targets are supplied by the setup/market-structure layer;
    this function deliberately does not invent arbitrary percentage levels.
    """
    values = (entry, stop_loss, target_1, target_2, minimum_risk_reward)
    if not all(isfinite(value) and value > 0 for value in values):
        raise RiskPlanError("all risk-plan values must be positive finite numbers")
    if minimum_risk_reward <= 0:
        raise RiskPlanError("minimum risk/reward must be positive")

    normalized_side = side.lower()
    if normalized_side not in {"buy", "sell"}:
        raise RiskPlanError("side must be buy or sell")

    risk = abs(entry - stop_loss)
    if risk == 0:
        raise RiskPlanError("entry and stop-loss cannot be equal")

    if normalized_side == "buy":
        if not stop_loss < entry < target_1 <= target_2:
            raise RiskPlanError("buy plan requires stop < entry < target1 <= target2")
    else:
        if target_2 <= target_1 < entry < stop_loss:
            pass
        else:
            raise RiskPlanError("sell plan requires target2 <= target1 < entry < stop")

    reward_1 = abs(target_1 - entry)
    reward_2 = abs(target_2 - entry)
    rr_1 = reward_1 / risk
    rr_2 = reward_2 / risk
    if rr_1 < minimum_risk_reward:
        raise RiskPlanError("target 1 does not meet minimum risk/reward")

    return RiskPlan(
        entry=entry,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        risk_reward_1=round(rr_1, 2),
        risk_reward_2=round(rr_2, 2),
        invalidation_level=stop_loss,
    )

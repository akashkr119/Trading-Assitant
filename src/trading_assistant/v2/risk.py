"""V2 portfolio and trade-risk calculations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskPlan:
    """Calculated risk limits for one candidate trade."""

    entry: float
    stop_loss: float
    target: float
    risk_per_share: float
    reward_per_share: float
    risk_reward: float | None
    quantity: int
    capital_at_risk: float


def build_risk_plan(
    entry: float,
    stop_loss: float,
    target: float,
    capital: float,
    risk_percent: float = 1.0,
) -> RiskPlan:
    """Size a position from a fixed account-risk percentage."""
    if entry <= 0 or stop_loss <= 0 or target <= 0:
        raise ValueError("Prices must be positive")
    if capital <= 0 or risk_percent <= 0:
        raise ValueError("Capital and risk percentage must be positive")

    risk_per_share = abs(entry - stop_loss)
    if risk_per_share <= 0:
        raise ValueError("Entry and stop-loss must be different")

    reward_per_share = abs(target - entry)
    risk_reward = reward_per_share / risk_per_share
    capital_at_risk = capital * risk_percent / 100
    quantity = int(capital_at_risk / risk_per_share)

    return RiskPlan(
        entry=entry,
        stop_loss=stop_loss,
        target=target,
        risk_per_share=risk_per_share,
        reward_per_share=reward_per_share,
        risk_reward=risk_reward,
        quantity=quantity,
        capital_at_risk=quantity * risk_per_share,
    )

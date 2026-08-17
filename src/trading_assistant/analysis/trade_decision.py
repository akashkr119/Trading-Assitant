"""V1 trade-decision engine.

This module converts an already-detected setup into a conservative
BUY/SELL/WATCH/NO_TRADE decision. It does not place orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from trading_assistant.analysis.setup_detection import SetupCandidate, SetupDirection


class TradeAction(StrEnum):
    """Allowed user-facing decisions."""

    BUY = "BUY"
    SELL = "SELL"
    WATCH = "WATCH"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True)
class DecisionInputs:
    """Normalized evidence used by the decision engine."""

    market_score: float
    sector_score: float
    stock_score: float
    timeframe_alignment: float
    confirmation_score: float
    risk_reward: float
    setup: SetupCandidate


@dataclass(frozen=True)
class TradeDecision:
    """A decision plus the evidence needed to explain it."""

    action: TradeAction
    score: float
    risk_reward: float
    reasons: tuple[str, ...]
    invalidation: str


MIN_TRADE_SCORE = 70.0
MIN_RISK_REWARD = 1.5
WATCH_SCORE = 55.0


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _decision_score(inputs: DecisionInputs) -> float:
    weighted = (
        inputs.market_score * 0.20
        + inputs.sector_score * 0.15
        + inputs.stock_score * 0.20
        + inputs.setup.confidence * 0.20
        + inputs.timeframe_alignment * 0.10
        + inputs.confirmation_score * 0.15
    )
    return round(_clamp(weighted), 2)


def evaluate_trade(inputs: DecisionInputs) -> TradeDecision:
    """Evaluate a setup without placing an order.

    A trade is blocked when risk/reward is below the V1 minimum. Conflicting
    or incomplete evidence falls back to WATCH or NO_TRADE rather than forcing
    a directional recommendation.
    """
    score = _decision_score(inputs)
    reasons = [
        f"market score {inputs.market_score:.1f}/100",
        f"sector score {inputs.sector_score:.1f}/100",
        f"stock score {inputs.stock_score:.1f}/100",
        f"setup confidence {inputs.setup.confidence:.1f}/100",
        f"timeframe alignment {inputs.timeframe_alignment:.1f}/100",
        f"confirmation score {inputs.confirmation_score:.1f}/100",
    ]

    if inputs.risk_reward < MIN_RISK_REWARD:
        reasons.append(
            f"risk/reward {inputs.risk_reward:.2f} is below the {MIN_RISK_REWARD:.1f} minimum"
        )
        action = TradeAction.NO_TRADE if score < WATCH_SCORE else TradeAction.WATCH
        return TradeDecision(
            action=action,
            score=score,
            risk_reward=inputs.risk_reward,
            reasons=tuple(reasons),
            invalidation=inputs.setup.invalidation,
        )

    if score < WATCH_SCORE:
        return TradeDecision(
            action=TradeAction.NO_TRADE,
            score=score,
            risk_reward=inputs.risk_reward,
            reasons=tuple(reasons),
            invalidation=inputs.setup.invalidation,
        )

    if score < MIN_TRADE_SCORE:
        reasons.append("evidence is promising but below the trade threshold")
        return TradeDecision(
            action=TradeAction.WATCH,
            score=score,
            risk_reward=inputs.risk_reward,
            reasons=tuple(reasons),
            invalidation=inputs.setup.invalidation,
        )

    action = (
        TradeAction.BUY
        if inputs.setup.direction == SetupDirection.BULLISH
        else TradeAction.SELL
    )
    reasons.append("all V1 trade-quality thresholds are satisfied")
    return TradeDecision(
        action=action,
        score=score,
        risk_reward=inputs.risk_reward,
        reasons=tuple(reasons),
        invalidation=inputs.setup.invalidation,
    )

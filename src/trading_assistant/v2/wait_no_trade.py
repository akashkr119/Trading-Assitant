"""Conservative WAIT / NO-TRADE decision logic for V2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TradeState(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True)
class TradeContext:
    """Normalized setup context used before a stock-level decision."""

    market_score: float
    setup_score: float
    risk_reward: float | None
    timeframe_aligned: bool
    high_volatility: bool = False


@dataclass(frozen=True)
class TradeDecision:
    """Decision plus explicit reasons so a signal is never a black box."""

    state: TradeState
    score: float
    reasons: tuple[str, ...]


def decide_trade(context: TradeContext, direction: str) -> TradeDecision:
    """Return BUY/SELL only when market, setup and risk agree."""
    direction = direction.upper()
    reasons: list[str] = []
    score = max(0.0, min(100.0, context.setup_score))

    if context.risk_reward is None:
        return TradeDecision(
            TradeState.NO_TRADE,
            round(score, 1),
            ("Risk/reward is unavailable; no trade is permitted.",),
        )
    if context.risk_reward < 1.5:
        return TradeDecision(
            TradeState.NO_TRADE,
            round(score, 1),
            ("Risk/reward is below the 1:1.5 minimum threshold.",),
        )
    if context.high_volatility:
        reasons.append("High volatility requires stronger confirmation.")
    if not context.timeframe_aligned:
        reasons.append("Timeframes are not aligned.")
    if direction == "BUY" and context.market_score < 0.15:
        reasons.append("Market context does not sufficiently support longs.")
    if direction == "SELL" and context.market_score > -0.15:
        reasons.append("Market context does not sufficiently support shorts.")

    if context.high_volatility or not context.timeframe_aligned:
        if context.setup_score >= 80 and context.risk_reward >= 2.0:
            reasons.append(
                "Setup is strong enough to remain under review, "
                "but confirmation is required."
            )
            return TradeDecision(TradeState.WAIT, round(score, 1), tuple(reasons))
        return TradeDecision(TradeState.NO_TRADE, round(score, 1), tuple(reasons))

    if reasons:
        return TradeDecision(TradeState.WAIT, round(score, 1), tuple(reasons))
    if context.setup_score >= 75:
        return TradeDecision(
            TradeState.BUY if direction == "BUY" else TradeState.SELL,
            round(score, 1),
            ("Market context, timeframe alignment and risk/reward agree.",),
        )
    return TradeDecision(
        TradeState.WAIT,
        round(score, 1),
        ("Setup score is below the confirmed-trade threshold.",),
    )

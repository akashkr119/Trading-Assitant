"""Explainable trade-signal narratives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalExplanation:
    why_this_stock: str
    why_this_decision: str
    confirmations: tuple[str, ...]
    risk_summary: str
    invalidation: str


def build_explanation(
    *,
    symbol: str,
    decision: str,
    sector: str,
    market_reason: str,
    stock_reason: str,
    setup_reason: str,
    confirmations: tuple[str, ...],
    entry: float | None = None,
    stop_loss: float | None = None,
    target_1: float | None = None,
    target_2: float | None = None,
    risk_reward_1: float | None = None,
    invalidation: str = "Setup invalidated when its defined structure fails.",
) -> SignalExplanation:
    """Build a deterministic explanation from already-computed engine evidence."""
    stock_text = (
        f"{symbol} is prioritized because it is in {sector}: "
        f"{stock_reason}"
    )
    decision_text = (
        f"{decision.upper()} is supported by market conditions ({market_reason}), "
        f"the detected setup ({setup_reason}), and the available confirmations."
    )

    if entry is None or stop_loss is None:
        risk_text = "No trade levels are available yet."
    else:
        targets = []
        if target_1 is not None:
            targets.append(f"T1 {target_1:.2f}")
        if target_2 is not None:
            targets.append(f"T2 {target_2:.2f}")
        target_text = ", ".join(targets) if targets else "targets pending"
        rr_text = f", R:R {risk_reward_1:.2f}" if risk_reward_1 else ""
        risk_text = (
            f"Entry {entry:.2f}, stop {stop_loss:.2f}, {target_text}{rr_text}."
        )

    return SignalExplanation(
        why_this_stock=stock_text,
        why_this_decision=decision_text,
        confirmations=confirmations,
        risk_summary=risk_text,
        invalidation=invalidation,
    )

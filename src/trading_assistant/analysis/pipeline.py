"""End-to-end orchestration of the V1 stock analysis components."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from trading_assistant.analysis.explanation import SignalExplanation, build_explanation
from trading_assistant.analysis.risk_plan import RiskPlan, RiskPlanError, build_risk_plan
from trading_assistant.analysis.setup_detection import (
    SetupCandidate,
    SetupDirection,
    SetupType,
    detect_setups,
)
from trading_assistant.analysis.timeframe import (
    AlignmentResult,
    TimeframeAlignment,
    TimeframeTrend,
    evaluate_alignment,
)
from trading_assistant.analysis.trade_decision import (
    DecisionInputs,
    TradeDecision,
    evaluate_trade,
)
from trading_assistant.indicators import ema, macd, relative_volume, supertrend


@dataclass(frozen=True)
class StockAnalysisInput:
    symbol: str
    sector: str
    frame: pd.DataFrame
    market_score: float
    sector_score: float
    stock_score: float
    confirmation_score: float
    timeframe_trends: tuple[TimeframeTrend, ...]
    entry: float
    stop_loss: float
    target_1: float
    target_2: float


@dataclass(frozen=True)
class StockAnalysisResult:
    symbol: str
    sector: str
    setup: SetupCandidate
    timeframe: AlignmentResult
    risk_plan: RiskPlan | None
    decision: TradeDecision
    explanation: SignalExplanation


_ALIGNMENT_SCORE = {
    TimeframeAlignment.ALIGNED: 100.0,
    TimeframeAlignment.PARTIAL: 65.0,
    TimeframeAlignment.CONFLICTING: 25.0,
    TimeframeAlignment.INSUFFICIENT: 0.0,
}


def _trend_continuation_setup(inputs: StockAnalysisInput) -> SetupCandidate | None:
    """Create a setup when live indicators agree but no one-candle trigger fired."""
    frame = inputs.frame
    if len(frame) < 30:
        return None
    close = frame["close"]
    ema9_values = ema(close, 9)
    ema20_values = ema(close, 20)
    macd_values = macd(close)
    relative_volume_values = relative_volume(frame)
    supertrend_values = supertrend(frame)
    index = len(frame) - 1
    price = float(close.iloc[index])
    ema9_value = float(ema9_values.iloc[index])
    ema20_value = float(ema20_values.iloc[index])
    macd_histogram = float(macd_values["histogram"].iloc[index])
    relative_volume_value = float(relative_volume_values.iloc[index])
    supertrend_direction = float(supertrend_values["direction"].iloc[index])

    bullish = (
        price > ema20_value
        and ema9_value > ema20_value
        and macd_histogram > 0
        and supertrend_direction > 0
        and relative_volume_value >= 1.0
    )
    bearish = (
        price < ema20_value
        and ema9_value < ema20_value
        and macd_histogram < 0
        and supertrend_direction < 0
        and relative_volume_value >= 1.0
    )
    if not bullish and not bearish:
        return None

    direction = SetupDirection.BULLISH if bullish else SetupDirection.BEARISH
    confidence = min(95.0, 65.0 + relative_volume_value * 10.0)
    side = "bullish" if bullish else "bearish"
    invalidation = (
        f"Close below EMA 20 for {side} setup"
        if bullish
        else f"Close above EMA 20 for {side} setup"
    )
    return SetupCandidate(
        SetupType.TREND_CONTINUATION,
        direction,
        index,
        confidence,
        (
            f"price {side} of EMA 20",
            f"EMA 9 {side} of EMA 20",
            f"MACD histogram {side}",
            f"Supertrend {side}",
            "relative volume >= 1.0",
        ),
        invalidation,
    )


def analyze_stock(inputs: StockAnalysisInput) -> StockAnalysisResult | None:
    """Run setup, timeframe, risk, decision and explanation stages for one stock."""
    setups = detect_setups(inputs.frame)
    fallback = _trend_continuation_setup(inputs)
    if fallback is not None:
        setups.append(fallback)
    if not setups:
        return None

    setup = max(setups, key=lambda candidate: candidate.confidence)
    timeframe = evaluate_alignment(list(inputs.timeframe_trends))
    alignment_score = _ALIGNMENT_SCORE[timeframe.alignment]

    risk_plan: RiskPlan | None = None
    risk_reward = 0.0
    risk_error: str | None = None
    try:
        risk_plan = build_risk_plan(
            side="buy" if setup.direction.value == "bullish" else "sell",
            entry=inputs.entry,
            stop_loss=inputs.stop_loss,
            target_1=inputs.target_1,
            target_2=inputs.target_2,
        )
        risk_reward = risk_plan.risk_reward_1
    except RiskPlanError as error:
        risk_error = str(error)

    decision = evaluate_trade(
        DecisionInputs(
            market_score=inputs.market_score,
            sector_score=inputs.sector_score,
            stock_score=inputs.stock_score,
            timeframe_alignment=alignment_score,
            confirmation_score=inputs.confirmation_score,
            risk_reward=risk_reward,
            setup=setup,
        )
    )
    reasons = setup.evidence + (timeframe.reason,)
    if risk_error:
        reasons = reasons + (f"risk plan rejected: {risk_error}",)

    explanation = build_explanation(
        symbol=inputs.symbol,
        decision=decision.action.value,
        sector=inputs.sector,
        market_reason=f"market score {inputs.market_score:.1f}/100",
        stock_reason=f"stock score {inputs.stock_score:.1f}/100",
        setup_reason=setup.setup_type.value,
        confirmations=reasons + decision.reasons,
        entry=risk_plan.entry if risk_plan else None,
        stop_loss=risk_plan.stop_loss if risk_plan else None,
        target_1=risk_plan.target_1 if risk_plan else None,
        target_2=risk_plan.target_2 if risk_plan else None,
        risk_reward_1=risk_plan.risk_reward_1 if risk_plan else None,
        invalidation=setup.invalidation,
    )
    return StockAnalysisResult(
        symbol=inputs.symbol,
        sector=inputs.sector,
        setup=setup,
        timeframe=timeframe,
        risk_plan=risk_plan,
        decision=decision,
        explanation=explanation,
    )

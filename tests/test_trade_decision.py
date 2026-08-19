from trading_assistant.analysis.setup_detection import SetupCandidate, SetupDirection, SetupType
from trading_assistant.analysis.trade_decision import (
    DecisionInputs,
    TradeAction,
    evaluate_trade,
)


def setup(direction: SetupDirection = SetupDirection.BULLISH) -> SetupCandidate:
    return SetupCandidate(
        setup_type=(
            SetupType.BREAKOUT
            if direction == SetupDirection.BULLISH
            else SetupType.BREAKDOWN
        ),
        direction=direction,
        index=50,
        confidence=85,
        evidence=("confirmed setup",),
        invalidation="setup invalidated",
    )


def inputs(direction: SetupDirection = SetupDirection.BULLISH, rr: float = 2.0) -> DecisionInputs:
    return DecisionInputs(
        market_score=80,
        sector_score=85,
        stock_score=90,
        timeframe_alignment=80,
        confirmation_score=85,
        risk_reward=rr,
        setup=setup(direction),
    )


def test_strong_bullish_setup_produces_buy() -> None:
    decision = evaluate_trade(inputs())
    assert decision.action == TradeAction.BUY
    assert decision.score >= 70
    assert decision.risk_reward == 2.0


def test_strong_bearish_setup_produces_sell() -> None:
    decision = evaluate_trade(inputs(SetupDirection.BEARISH))
    assert decision.action == TradeAction.SELL


def test_low_risk_reward_never_forces_trade() -> None:
    decision = evaluate_trade(inputs(rr=1.2))
    assert decision.action in {TradeAction.WATCH, TradeAction.NO_TRADE}
    assert any("risk/reward" in reason for reason in decision.reasons)


def test_mid_score_produces_watch() -> None:
    base = inputs()
    decision = evaluate_trade(
        DecisionInputs(
            market_score=60,
            sector_score=60,
            stock_score=60,
            timeframe_alignment=60,
            confirmation_score=60,
            risk_reward=2.0,
            setup=setup(),
        )
    )
    assert 55 <= decision.score < 70
    assert decision.action == TradeAction.WATCH
    assert base.setup.invalidation == "setup invalidated"

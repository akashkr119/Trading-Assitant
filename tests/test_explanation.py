from trading_assistant.analysis.explanation import build_explanation


def test_explanation_contains_stock_decision_and_risk_details() -> None:
    explanation = build_explanation(
        symbol="RELIANCE",
        decision="buy",
        sector="Energy",
        market_reason="market is bullish",
        stock_reason="relative strength is strong",
        setup_reason="breakout confirmed",
        confirmations=("above VWAP", "relative volume confirmed"),
        entry=100.0,
        stop_loss=98.0,
        target_1=104.0,
        target_2=106.0,
        risk_reward_1=2.0,
        invalidation="Close below breakout level.",
    )

    assert "RELIANCE" in explanation.why_this_stock
    assert "BUY" in explanation.why_this_decision
    assert explanation.confirmations == ("above VWAP", "relative volume confirmed")
    assert "Entry 100.00" in explanation.risk_summary
    assert "R:R 2.00" in explanation.risk_summary
    assert explanation.invalidation == "Close below breakout level."

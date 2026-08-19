from trading_assistant.analysis.explanation import build_explanation
from trading_assistant.monitoring.alert_payload import build_explained_alert
from trading_assistant.monitoring.alerts import AlertType


def test_alert_contains_full_signal_explanation() -> None:
    explanation = build_explanation(
        symbol="RELIANCE",
        decision="buy",
        sector="Energy",
        market_reason="market is bullish",
        stock_reason="relative strength is strong",
        setup_reason="breakout confirmed",
        confirmations=("above VWAP", "volume confirmed"),
        entry=100.0,
        stop_loss=98.0,
        target_1=104.0,
        target_2=106.0,
        risk_reward_1=2.0,
        invalidation="Close below breakout level.",
    )

    payload = build_explained_alert(
        symbol="RELIANCE",
        alert_type=AlertType.BUY,
        timestamp="2026-08-17T10:24:00+05:30",
        explanation=explanation,
    )

    assert payload.alert.title == "RELIANCE — BUY"
    assert "Why this stock" not in payload.alert.message
    assert "RELIANCE is prioritized" in payload.alert.message
    assert "market is bullish" in payload.alert.message
    assert "above VWAP" in payload.alert.message
    assert "Entry 100.00" in payload.alert.message
    assert "R:R 2.00" in payload.alert.message
    assert "Close below breakout level" in payload.alert.message

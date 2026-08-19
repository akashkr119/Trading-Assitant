from trading_assistant.monitoring.alerts import AlertType, build_alert


def test_build_buy_alert() -> None:
    alert = build_alert(
        symbol="reliance",
        alert_type=AlertType.BUY,
        timestamp="2026-08-17T10:24:00+05:30",
        message="Strong sector and bullish setup confirmed.",
    )

    assert alert.symbol == "RELIANCE"
    assert alert.title == "RELIANCE — BUY"
    assert alert.alert_type == AlertType.BUY
    assert "bullish setup" in alert.message


def test_alert_types_cover_trade_lifecycle() -> None:
    assert {
        AlertType.BUY,
        AlertType.SELL,
        AlertType.SETUP_NEAR,
        AlertType.TARGET,
        AlertType.STOP,
        AlertType.INVALIDATED,
        AlertType.SIGNAL_CHANGED,
    } == set(AlertType)

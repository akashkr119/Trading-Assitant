from trading_assistant.monitoring.alerts import AlertType, build_alert
from trading_assistant.monitoring.notifier import ConsoleNotifier, NotificationDispatcher


def test_dispatcher_sends_alert_to_configured_notifier() -> None:
    notifier = ConsoleNotifier(sent=[])
    dispatcher = NotificationDispatcher(notifier)
    alert = build_alert(
        symbol="RELIANCE",
        alert_type=AlertType.BUY,
        timestamp="2026-08-17T10:24:00+05:30",
        message="Bullish setup confirmed.",
    )

    dispatcher.dispatch(alert)

    assert notifier.sent == [alert]

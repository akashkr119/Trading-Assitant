from datetime import datetime

from trading_assistant.monitoring.state import MonitorState, MonitorStateMachine


def test_first_signal_emits_alert() -> None:
    machine = MonitorStateMachine()
    _, should_alert = machine.update(
        symbol="RELIANCE",
        decision="BUY",
        state=MonitorState.ACTIVE,
        trigger_key="breakout-100",
        timestamp=datetime(2026, 8, 17, 10, 24),
    )
    assert should_alert


def test_unchanged_signal_does_not_repeat_alert() -> None:
    machine = MonitorStateMachine()
    timestamp = datetime(2026, 8, 17, 10, 24)
    machine.update(
        symbol="RELIANCE",
        decision="BUY",
        state=MonitorState.ACTIVE,
        trigger_key="breakout-100",
        timestamp=timestamp,
    )
    _, should_alert = machine.update(
        symbol="RELIANCE",
        decision="BUY",
        state=MonitorState.ACTIVE,
        trigger_key="breakout-100",
        timestamp=datetime(2026, 8, 17, 10, 25),
    )
    assert not should_alert


def test_state_or_trigger_change_emits_alert() -> None:
    machine = MonitorStateMachine()
    timestamp = datetime(2026, 8, 17, 10, 24)
    machine.update(
        symbol="RELIANCE",
        decision="WATCH",
        state=MonitorState.TRIGGER_NEAR,
        trigger_key="breakout-100",
        timestamp=timestamp,
    )
    _, should_alert = machine.update(
        symbol="RELIANCE",
        decision="BUY",
        state=MonitorState.ACTIVE,
        trigger_key="breakout-101",
        timestamp=datetime(2026, 8, 17, 10, 25),
    )
    assert should_alert

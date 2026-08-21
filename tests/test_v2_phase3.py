from datetime import datetime, timezone

import pytest

from trading_assistant.v2.alerts import AlertEngine
from trading_assistant.v2.risk import build_risk_plan


def test_risk_plan_sizes_from_account_risk() -> None:
    plan = build_risk_plan(100, 95, 110, 100_000, 1.0)

    assert plan.risk_per_share == 5
    assert plan.risk_reward == 2
    assert plan.quantity == 200
    assert plan.capital_at_risk == 1_000


def test_risk_plan_rejects_zero_stop_distance() -> None:
    with pytest.raises(ValueError, match="different"):
        build_risk_plan(100, 100, 110, 100_000)


def test_alert_engine_suppresses_duplicate_within_cooldown() -> None:
    engine = AlertEngine(cooldown_minutes=15)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    first = engine.evaluate("NIFTY-BUY", "BUY", "confirmed", now=now)
    second = engine.evaluate(
        "NIFTY-BUY",
        "BUY",
        "confirmed again",
        now=now.replace(minute=10),
    )

    assert first is not None
    assert second is None


def test_alert_engine_allows_event_after_cooldown() -> None:
    engine = AlertEngine(cooldown_minutes=15)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    engine.evaluate("NIFTY-BUY", "BUY", "confirmed", now=now)
    event = engine.evaluate(
        "NIFTY-BUY",
        "BUY",
        "confirmed again",
        now=now.replace(minute=16),
    )

    assert event is not None
    assert event.severity == "INFO"

import pytest

from trading_assistant.analysis.risk_plan import RiskPlanError, build_risk_plan


def test_buy_risk_plan_calculates_rr() -> None:
    plan = build_risk_plan(
        side="buy",
        entry=100,
        stop_loss=98,
        target_1=104,
        target_2=106,
    )
    assert plan.risk_reward_1 == 2.0
    assert plan.risk_reward_2 == 3.0
    assert plan.invalidation_level == 98


def test_sell_risk_plan_calculates_rr() -> None:
    plan = build_risk_plan(
        side="sell",
        entry=100,
        stop_loss=102,
        target_1=96,
        target_2=94,
    )
    assert plan.risk_reward_1 == 2.0
    assert plan.risk_reward_2 == 3.0


def test_risk_plan_rejects_insufficient_rr() -> None:
    with pytest.raises(RiskPlanError, match="minimum risk/reward"):
        build_risk_plan(
            side="buy",
            entry=100,
            stop_loss=98,
            target_1=101,
            target_2=103,
        )


def test_risk_plan_rejects_wrong_price_order() -> None:
    with pytest.raises(RiskPlanError, match="buy plan"):
        build_risk_plan(
            side="buy",
            entry=100,
            stop_loss=102,
            target_1=104,
            target_2=106,
        )

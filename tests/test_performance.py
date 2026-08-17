from datetime import datetime, timedelta

from trading_assistant.analysis.trade_decision import TradeAction
from trading_assistant.monitoring.performance import SignalObservation, evaluate_signal


def test_buy_signal_reports_forward_move_mfe_mae_and_targets() -> None:
    start = datetime(2026, 8, 18, 10, 0)
    observation = SignalObservation(
        symbol="TEST",
        action=TradeAction.BUY,
        signal_price=100.0,
        signal_time=start,
        stop_loss=99.0,
        target_1=101.5,
        target_2=103.0,
        prices=(
            (start + timedelta(minutes=5), 100.5),
            (start + timedelta(minutes=15), 101.7),
            (start + timedelta(minutes=30), 99.5),
            (start + timedelta(minutes=60), 103.2),
        ),
    )

    result = evaluate_signal(observation)

    assert result.return_at(5) == 0.5
    assert result.return_at(15) == 1.7
    assert result.return_at(30) == -0.5
    assert result.return_at(60) == 3.2
    assert result.max_favorable_pct == 3.2
    assert result.max_adverse_pct == -0.5
    assert result.target_1_hit
    assert result.target_2_hit
    assert not result.stop_loss_hit


def test_sell_signal_inverts_price_direction() -> None:
    start = datetime(2026, 8, 18, 10, 0)
    observation = SignalObservation(
        symbol="TEST",
        action=TradeAction.SELL,
        signal_price=100.0,
        signal_time=start,
        stop_loss=101.0,
        target_1=98.5,
        target_2=97.0,
        prices=(
            (start + timedelta(minutes=5), 99.0),
            (start + timedelta(minutes=15), 98.0),
        ),
    )

    result = evaluate_signal(observation)

    assert result.return_at(5) == 1.0
    assert result.max_favorable_pct == 2.0
    assert result.max_adverse_pct == 1.0
    assert result.target_1_hit
    assert result.target_2_hit
    assert not result.stop_loss_hit

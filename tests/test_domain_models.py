from datetime import UTC, datetime

from trading_assistant.domain import Decision, SetupType, SignalState, TradeSignal


def test_trade_signal_accepts_valid_v1_signal() -> None:
    signal = TradeSignal(
        symbol="HDFCBANK",
        decision=Decision.BUY,
        state=SignalState.BUY,
        setup=SetupType.BREAKOUT,
        score=89,
        timestamp=datetime.now(UTC),
        reasons=["Price above VWAP", "Breakout confirmed"],
    )

    assert signal.symbol == "HDFCBANK"
    assert signal.decision is Decision.BUY
    assert signal.score == 89


def test_trade_signal_score_is_bounded() -> None:
    try:
        TradeSignal(
            symbol="TEST",
            decision=Decision.WATCH,
            state=SignalState.WATCH,
            score=101,
            timestamp=datetime.now(UTC),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Scores above 100 must be rejected")

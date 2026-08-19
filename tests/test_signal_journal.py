from datetime import datetime, timezone

from trading_assistant.monitoring.signal_journal import SignalJournal, SignalRecord


def _signal(signal_id: str = "s1") -> SignalRecord:
    return SignalRecord(
        signal_id=signal_id,
        timestamp="2026-08-20T09:30:00+00:00",
        market="CRYPTO",
        symbol="BTCUSDT",
        direction="LONG",
        score=92,
        entry=100.0,
        stop_loss=99.0,
        target_1=102.0,
        target_2=104.0,
        risk_reward=4.0,
        reason="EMA + RSI + MACD + Supertrend",
    )


def test_journal_preserves_signal_and_resolves_result(tmp_path) -> None:
    journal = SignalJournal(tmp_path / "signals.csv")
    journal.record(_signal())

    assert journal.resolve(
        "s1",
        "TARGET_2",
        104.0,
        4.0,
        datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc),
    )

    record = journal.records()[0]
    assert record.entry == 100.0
    assert record.stop_loss == 99.0
    assert record.target_2 == 104.0
    assert record.status == "TARGET_2"
    assert record.outcome_r == 4.0


def test_summary_calculates_win_rate_expectancy_and_drawdown(tmp_path) -> None:
    journal = SignalJournal(tmp_path / "signals.csv")
    journal.record(_signal("win"))
    journal.record(_signal("loss"))
    journal.resolve("win", "TARGET_2", 104.0, 4.0, datetime.now(timezone.utc))
    journal.resolve("loss", "STOP_LOSS", 99.0, -1.0, datetime.now(timezone.utc))

    summary = journal.summary()

    assert summary.total == 2
    assert summary.wins == 1
    assert summary.losses == 1
    assert summary.win_rate == 50.0
    assert summary.average_r == 1.5
    assert summary.expectancy_r == 1.5
    assert summary.profit_factor == 4.0
    assert summary.max_drawdown_r == 1.0
    assert summary.target_2_rate == 50.0

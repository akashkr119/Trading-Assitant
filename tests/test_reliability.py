import pytest

from trading_assistant.data.reliability import (
    RetryPolicy,
    process_independently,
    with_retry,
)


def test_with_retry_recovers_from_transient_failure() -> None:
    attempts = 0
    delays: list[float] = []

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError("temporary")
        return "ok"

    result = with_retry(
        operation,
        policy=RetryPolicy(attempts=3, initial_delay_seconds=1),
        sleeper=delays.append,
    )

    assert result == "ok"
    assert attempts == 3
    assert delays == [1, 2]


def test_with_retry_raises_after_attempt_limit() -> None:
    def operation() -> None:
        raise TimeoutError("unavailable")

    with pytest.raises(TimeoutError, match="unavailable"):
        with_retry(operation, policy=RetryPolicy(attempts=2), sleeper=lambda _: None)


def test_process_independently_keeps_other_symbols_running() -> None:
    processed: list[str] = []

    def process(symbol: str) -> None:
        processed.append(symbol)
        if symbol == "FAIL":
            raise RuntimeError("provider failure")

    failed = process_independently(("A", "FAIL", "B"), process)

    assert processed == ["A", "FAIL", "B"]
    assert failed == ("FAIL",)

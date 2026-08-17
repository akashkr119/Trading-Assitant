"""Retry and failure-isolation helpers for market-data operations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import sleep
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry policy with exponential backoff."""

    attempts: int = 3
    initial_delay_seconds: float = 0.5
    backoff: float = 2.0

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("attempts must be positive")
        if self.initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds cannot be negative")
        if self.backoff < 1:
            raise ValueError("backoff must be at least 1")


def with_retry(
    operation: Callable[[], T],
    *,
    policy: RetryPolicy = RetryPolicy(),
    sleeper: Callable[[float], None] = sleep,
) -> T:
    """Retry an operation a bounded number of times before raising."""
    last_error: Exception | None = None
    for attempt in range(policy.attempts):
        try:
            return operation()
        except Exception as error:
            last_error = error
            if attempt == policy.attempts - 1:
                break
            delay = policy.initial_delay_seconds * (policy.backoff**attempt)
            sleeper(delay)
    assert last_error is not None
    raise last_error


def process_independently(
    symbols: tuple[str, ...],
    process: Callable[[str], None],
) -> tuple[str, ...]:
    """Process each symbol independently and return symbols that failed."""
    failed: list[str] = []
    for symbol in symbols:
        try:
            process(symbol)
        except Exception:
            failed.append(symbol)
    return tuple(failed)

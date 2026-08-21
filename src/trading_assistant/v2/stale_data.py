"""Safety checks for live V2 market observations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def is_fresh(
    observed_at: datetime,
    max_age_seconds: int = 60,
    now: datetime | None = None,
) -> bool:
    """Return False when an observation is missing, future-dated or stale."""
    current = now or datetime.now(timezone.utc)
    timestamp = observed_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age = current - timestamp.astimezone(timezone.utc)
    return timedelta(0) <= age <= timedelta(seconds=max_age_seconds)

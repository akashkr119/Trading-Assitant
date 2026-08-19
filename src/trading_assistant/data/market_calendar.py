"""Indian equity market session helpers."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


def is_weekday(value: date) -> bool:
    """Return True for Monday-Friday."""
    return value.weekday() < 5


def is_regular_session(dt: datetime) -> bool:
    """Return True when ``dt`` falls inside the weekday regular session.

    Exchange holidays are deliberately not embedded here yet. A future calendar
    provider will supply the authoritative NSE/BSE holiday schedule.
    """
    local_dt = dt.astimezone(IST) if dt.tzinfo else dt.replace(tzinfo=IST)
    return is_weekday(local_dt.date()) and MARKET_OPEN <= local_dt.time() <= MARKET_CLOSE

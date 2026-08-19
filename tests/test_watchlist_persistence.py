import pytest

from trading_assistant.monitoring.watchlist import Watchlist


def test_watchlist_can_round_trip_through_json_safe_records() -> None:
    watchlist = Watchlist()
    watchlist.add("reliance", "2026-08-18T10:00:00")
    watchlist.add("TCS", "2026-08-18T10:01:00")

    restored = Watchlist.from_items(watchlist.export())

    assert restored.symbols() == ("RELIANCE", "TCS")
    assert restored.items() == watchlist.items()


def test_watchlist_rejects_malformed_persisted_records() -> None:
    with pytest.raises(ValueError, match="symbol and added_at"):
        Watchlist.from_items(({"symbol": "TCS"},))

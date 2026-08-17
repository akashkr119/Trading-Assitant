from trading_assistant.monitoring.watchlist import Watchlist


def test_watchlist_normalizes_and_deduplicates_symbols() -> None:
    watchlist = Watchlist()
    watchlist.add(" reliance ", "2026-08-18T10:00:00")
    watchlist.add("RELIANCE", "2026-08-18T10:01:00")
    watchlist.add("tcs", "2026-08-18T10:02:00")

    assert watchlist.symbols() == ("RELIANCE", "TCS")
    assert watchlist.contains("tcs")


def test_watchlist_remove_is_idempotent() -> None:
    watchlist = Watchlist()
    watchlist.add("INFY", "2026-08-18T10:00:00")

    assert watchlist.remove("INFY") is True
    assert watchlist.remove("INFY") is False

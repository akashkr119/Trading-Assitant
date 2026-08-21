from trading_assistant.monitoring.market_scanner import ScanCandidate
from trading_assistant.monitoring.sector_scanner import SectorSnapshot, symbol_sector


def test_known_intraday_symbols_have_sector() -> None:
    assert symbol_sector("HDFCBANK") == "Banking"
    assert symbol_sector("JBMA") == "Auto"
    assert symbol_sector("PCJEWELLER") == "Consumer Durables"
    assert symbol_sector("UNKNOWN") == "Other"


def test_scan_candidate_exposes_sector_without_breaking_defaults() -> None:
    candidate = ScanCandidate("HDFCBANK", "BULLISH", 90, 700, 1.0, 1.2, "test")
    assert candidate.sector == "Other"


def test_sector_score_uses_price_and_breadth() -> None:
    strong = SectorSnapshot("NIFTY BANK", 1.5, 10, 2, 0)
    weak = SectorSnapshot("NIFTY BANK", -1.0, 2, 10, 0)
    assert strong.score > weak.score

from trading_assistant.monitoring.sector_scanner import SectorSnapshot, symbol_sector


def test_symbol_sector_classifies_common_nse_stocks() -> None:
    assert symbol_sector("HDFCBANK") == "Banking"
    assert symbol_sector("TCS") == "IT"
    assert symbol_sector("SUNPHARMA") == "Pharma"
    assert symbol_sector("UNKNOWN") == "Other"


def test_sector_snapshot_strength_is_bounded() -> None:
    assert SectorSnapshot("Test", 0.0, 1, 1, 0).score == 50.0
    assert SectorSnapshot("Test", 10.0, 1, 0, 0).score == 100.0
    assert SectorSnapshot("Test", -10.0, 0, 1, 0).score == 0.0

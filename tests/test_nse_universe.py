import pytest

from trading_assistant.data.nse_universe import normalize_nse_symbol, nse_long_term_universe


def test_normalize_nse_symbol() -> None:
    assert normalize_nse_symbol("reliance") == "RELIANCE.NS"
    assert normalize_nse_symbol("TCS.NS") == "TCS.NS"


def test_empty_symbol_is_rejected() -> None:
    with pytest.raises(ValueError):
        normalize_nse_symbol("   ")


def test_universe_is_normalized_and_deduplicated() -> None:
    assert nse_long_term_universe(("tcs", "TCS.NS", "INFY")) == ["TCS.NS", "INFY.NS"]

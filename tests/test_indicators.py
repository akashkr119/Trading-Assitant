import numpy as np
import pandas as pd

from trading_assistant.indicators import ema, macd, relative_volume, rsi, supertrend, vwap


def sample_frame(size: int = 60) -> pd.DataFrame:
    close = pd.Series(np.linspace(100, 120, size))
    return pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.linspace(1000, 2000, size),
        }
    )


def test_ema_and_rsi_produce_expected_ranges() -> None:
    close = sample_frame()["close"]
    assert ema(close, 9).iloc[-1] > ema(close, 20).iloc[-1]
    assert 0 <= rsi(close).iloc[-1] <= 100


def test_macd_returns_line_signal_and_histogram() -> None:
    result = macd(sample_frame()["close"])
    assert list(result.columns) == ["macd", "signal", "histogram"]
    assert np.isclose(result.iloc[-1]["histogram"], result.iloc[-1]["macd"] - result.iloc[-1]["signal"])


def test_vwap_and_relative_volume_are_defined_after_warmup() -> None:
    frame = sample_frame()
    assert pd.notna(vwap(frame).iloc[-1])
    assert pd.notna(relative_volume(frame).iloc[-1])


def test_supertrend_returns_direction() -> None:
    result = supertrend(sample_frame())
    assert set(result.columns) == {"supertrend", "direction"}
    assert result["direction"].iloc[-1] in {-1, 1}

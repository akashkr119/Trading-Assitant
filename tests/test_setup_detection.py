import numpy as np
import pandas as pd

from trading_assistant.analysis.setup_detection import (
    SetupDirection,
    SetupType,
    detect_setups,
)


def base_frame(size: int = 60) -> pd.DataFrame:
    close = np.linspace(100, 110, size)
    return pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(size, 1000.0),
        }
    )


def test_breakout_requires_range_close_and_relative_volume() -> None:
    frame = base_frame()
    frame.loc[59, "close"] = frame.loc[39:58, "high"].max() + 1
    frame.loc[59, "high"] = frame.loc[59, "close"] + 0.2
    frame.loc[59, "volume"] = 1500

    setups = detect_setups(frame)

    assert any(item.setup_type == SetupType.BREAKOUT for item in setups)
    assert all(item.direction == SetupDirection.BULLISH for item in setups if item.setup_type == SetupType.BREAKOUT)


def test_short_input_is_rejected() -> None:
    frame = base_frame(29)
    try:
        detect_setups(frame)
    except ValueError as exc:
        assert "30 bars" in str(exc)
    else:
        raise AssertionError("expected a minimum-bar validation error")


def test_missing_columns_are_rejected() -> None:
    frame = base_frame().drop(columns=["volume"])
    try:
        detect_setups(frame)
    except ValueError as exc:
        assert "volume" in str(exc)
    else:
        raise AssertionError("expected a missing-column validation error")

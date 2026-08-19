import pytest

from trading_assistant.analysis.timeframe import (
    TimeframeAlignment,
    TimeframeTrend,
    evaluate_alignment,
)


def test_all_bullish_timeframes_are_aligned() -> None:
    result = evaluate_alignment(
        [
            TimeframeTrend("1m", "bullish"),
            TimeframeTrend("5m", "bullish"),
            TimeframeTrend("15m", "bullish"),
            TimeframeTrend("1h", "bullish"),
        ]
    )
    assert result.alignment == TimeframeAlignment.ALIGNED
    assert result.bullish_count == 4


def test_mixed_directional_timeframes_are_conflicting() -> None:
    result = evaluate_alignment(
        [
            TimeframeTrend("1m", "bullish"),
            TimeframeTrend("5m", "bullish"),
            TimeframeTrend("15m", "bearish"),
            TimeframeTrend("1h", "bearish"),
        ]
    )
    assert result.alignment == TimeframeAlignment.CONFLICTING
    assert result.bullish_count == 2
    assert result.bearish_count == 2


def test_neutral_only_data_is_insufficient() -> None:
    result = evaluate_alignment([TimeframeTrend("1m", "neutral")])
    assert result.alignment == TimeframeAlignment.INSUFFICIENT


def test_unknown_direction_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        evaluate_alignment([TimeframeTrend("1m", "sideways")])

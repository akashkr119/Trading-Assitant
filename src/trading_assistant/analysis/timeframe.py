"""Multi-timeframe confirmation logic for V1 trade decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TimeframeAlignment(StrEnum):
    ALIGNED = "aligned"
    PARTIAL = "partial"
    CONFLICTING = "conflicting"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class TimeframeTrend:
    timeframe: str
    direction: str


@dataclass(frozen=True)
class AlignmentResult:
    alignment: TimeframeAlignment
    bullish_count: int
    bearish_count: int
    neutral_count: int
    reason: str


def evaluate_alignment(trends: list[TimeframeTrend]) -> AlignmentResult:
    """Evaluate directional agreement across supplied timeframes.

    Direction values are normalized to bullish, bearish, or neutral. The
    higher-timeframe trend is not given special magic weighting here; callers
    can supply the desired timeframe set and use this result as one input to
    the decision engine.
    """
    if not trends:
        return AlignmentResult(
            alignment=TimeframeAlignment.INSUFFICIENT,
            bullish_count=0,
            bearish_count=0,
            neutral_count=0,
            reason="No timeframe trend data available.",
        )

    counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    for trend in trends:
        direction = trend.direction.lower()
        if direction not in counts:
            raise ValueError(f"unsupported timeframe direction: {trend.direction}")
        counts[direction] += 1

    directional = counts["bullish"] + counts["bearish"]
    if directional == 0:
        alignment = TimeframeAlignment.INSUFFICIENT
    elif counts["bullish"] == len(trends) or counts["bearish"] == len(trends):
        alignment = TimeframeAlignment.ALIGNED
    elif counts["bullish"] == 0 or counts["bearish"] == 0:
        alignment = TimeframeAlignment.PARTIAL
    else:
        alignment = TimeframeAlignment.CONFLICTING

    reason = (
        f"Bullish={counts['bullish']}, bearish={counts['bearish']}, "
        f"neutral={counts['neutral']} across {len(trends)} timeframes."
    )
    return AlignmentResult(
        alignment=alignment,
        bullish_count=counts["bullish"],
        bearish_count=counts["bearish"],
        neutral_count=counts["neutral"],
        reason=reason,
    )

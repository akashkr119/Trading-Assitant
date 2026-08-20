"""Transparent sector-rotation scoring for V2."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SectorObservation:
    """Normalized sector observations supplied by a future data adapter."""

    name: str
    relative_strength: float
    trend: float
    volume_strength: float
    breadth_pct: float


@dataclass(frozen=True)
class SectorScore:
    """Rankable sector score with a plain-language interpretation."""

    name: str
    score: float
    rank: int
    interpretation: str


def rank_sectors(observations: list[SectorObservation]) -> tuple[SectorScore, ...]:
    """Rank sectors without inventing values for missing observations."""
    scored: list[tuple[SectorObservation, float]] = []
    for item in observations:
        breadth_signal = max(-1.0, min(1.0, (item.breadth_pct - 50.0) / 50.0))
        score = (
            max(-1.0, min(1.0, item.relative_strength)) * 0.35
            + max(-1.0, min(1.0, item.trend)) * 0.30
            + max(-1.0, min(1.0, item.volume_strength)) * 0.15
            + breadth_signal * 0.20
        )
        scored.append((item, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    result: list[SectorScore] = []
    for rank, (item, score) in enumerate(scored, 1):
        if score >= 0.35:
            interpretation = "LEADING"
        elif score <= -0.35:
            interpretation = "WEAK"
        else:
            interpretation = "MIXED"
        result.append(
            SectorScore(
                name=item.name,
                score=round(score, 3),
                rank=rank,
                interpretation=interpretation,
            )
        )
    return tuple(result)

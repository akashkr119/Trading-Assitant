"""Deterministic market and sector scoring for the V1 decision pipeline."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class MarketRegime(StrEnum):
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


class MarketInputs(BaseModel):
    nifty_trend: float = Field(ge=0, le=100)
    banknifty_trend: float = Field(ge=0, le=100)
    breadth: float = Field(ge=0, le=100)
    momentum: float = Field(ge=0, le=100)
    volatility: float = Field(ge=0, le=100)


class MarketScore(BaseModel):
    score: float = Field(ge=0, le=100)
    regime: MarketRegime


def _regime(score: float) -> MarketRegime:
    if score >= 80:
        return MarketRegime.STRONG_BULLISH
    if score >= 65:
        return MarketRegime.BULLISH
    if score >= 45:
        return MarketRegime.NEUTRAL
    if score >= 30:
        return MarketRegime.BEARISH
    return MarketRegime.STRONG_BEARISH


def score_market(inputs: MarketInputs) -> MarketScore:
    """Score current market conditions using the V1 25/20/20/20/15 weights."""
    score = (
        inputs.nifty_trend * 0.25
        + inputs.banknifty_trend * 0.20
        + inputs.breadth * 0.20
        + inputs.momentum * 0.20
        + inputs.volatility * 0.15
    )
    return MarketScore(score=round(score, 2), regime=_regime(score))


class SectorInputs(BaseModel):
    trend: float = Field(ge=0, le=100)
    relative_strength: float = Field(ge=0, le=100)
    volume: float = Field(ge=0, le=100)
    breadth: float = Field(ge=0, le=100)
    momentum: float = Field(ge=0, le=100)


class SectorScore(BaseModel):
    sector: str
    score: float = Field(ge=0, le=100)


def score_sector(sector: str, inputs: SectorInputs) -> SectorScore:
    """Score a sector using the V1 25/25/20/20/10 weights."""
    score = (
        inputs.trend * 0.25
        + inputs.relative_strength * 0.25
        + inputs.volume * 0.20
        + inputs.breadth * 0.20
        + inputs.momentum * 0.10
    )
    return SectorScore(sector=sector, score=round(score, 2))


def rank_sectors(scores: list[SectorScore]) -> list[SectorScore]:
    """Return sectors strongest-first without changing their underlying scores."""
    return sorted(scores, key=lambda item: item.score, reverse=True)

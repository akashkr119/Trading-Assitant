"""Core domain models used across the V1 trading engine.

These models intentionally contain no market-data or strategy logic. They define the
stable contracts that later market, indicator, setup, risk, and alert modules will use.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MarketRegime(StrEnum):
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


class SignalState(StrEnum):
    NO_SETUP = "no_setup"
    WATCH = "watch"
    SETUP_FORMING = "setup_forming"
    TRIGGER_NEAR = "trigger_near"
    BUY = "buy"
    SELL = "sell"
    ACTIVE = "active"
    TARGET = "target"
    STOP = "stop"
    EXIT = "exit"
    INVALIDATED = "invalidated"


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class SetupType(StrEnum):
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    BULLISH_PULLBACK = "bullish_pullback"
    BEARISH_PULLBACK = "bearish_pullback"
    CONSOLIDATION = "consolidation"


class Decision(StrEnum):
    BUY = "buy"
    SELL = "sell"
    WATCH = "watch"
    NO_TRADE = "no_trade"


class PriceLevel(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: float = Field(gt=0)
    label: str


class RiskPlan(BaseModel):
    """Entry/stop/target contract produced by the risk engine."""

    entry: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    target_1: float | None = Field(default=None, gt=0)
    target_2: float | None = Field(default=None, gt=0)
    risk_reward_1: float | None = Field(default=None, gt=0)
    risk_reward_2: float | None = Field(default=None, gt=0)
    invalidation_level: float | None = Field(default=None, gt=0)


class TradeSignal(BaseModel):
    """Explainable decision emitted by the decision engine."""

    symbol: str = Field(min_length=1)
    decision: Decision
    state: SignalState
    setup: SetupType | None = None
    score: float = Field(ge=0, le=100)
    timestamp: datetime
    reasons: list[str] = Field(default_factory=list)
    risk_plan: RiskPlan | None = None
    invalidation_reason: str | None = None


class IndicatorSnapshot(BaseModel):
    """Indicator values calculated for a single market-data snapshot."""

    ema_9: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    vwap: float | None = None
    rsi: float | None = Field(default=None, ge=0, le=100)
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    supertrend: float | None = None
    relative_volume: float | None = Field(default=None, ge=0)

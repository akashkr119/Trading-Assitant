"""Track forward price outcomes for generated trading signals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from trading_assistant.analysis.trade_decision import TradeAction


class SignalOutcome(StrEnum):
    PENDING = "PENDING"
    FAVORABLE = "FAVORABLE"
    ADVERSE = "ADVERSE"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class SignalObservation:
    """A signal and the market observations used to evaluate it."""

    symbol: str
    action: TradeAction
    signal_price: float
    signal_time: datetime
    stop_loss: float
    target_1: float
    target_2: float
    prices: tuple[tuple[datetime, float], ...] = ()


@dataclass(frozen=True)
class SignalPerformance:
    """Calculated forward performance for one signal."""

    symbol: str
    action: TradeAction
    signal_price: float
    returns: tuple[tuple[int, float], ...]
    max_favorable_pct: float
    max_adverse_pct: float
    target_1_hit: bool
    target_2_hit: bool
    stop_loss_hit: bool

    def return_at(self, minutes: int) -> float | None:
        for horizon, value in self.returns:
            if horizon == minutes:
                return value
        return None


def evaluate_signal(
    observation: SignalObservation,
    *,
    horizons: tuple[int, ...] = (5, 15, 30, 60),
) -> SignalPerformance:
    """Evaluate direction, MFE/MAE, and target/stop outcomes from observations."""
    if observation.signal_price <= 0:
        raise ValueError("signal_price must be positive")

    def move(price: float) -> float:
        raw = (price - observation.signal_price) / observation.signal_price * 100
        return raw if observation.action == TradeAction.BUY else -raw

    favorable = [move(price) for _, price in observation.prices]
    returns = []
    for horizon in horizons:
        eligible = [
            move(price)
            for timestamp, price in observation.prices
            if (timestamp - observation.signal_time).total_seconds() >= horizon * 60
        ]
        if eligible:
            returns.append((horizon, eligible[0]))

    return SignalPerformance(
        symbol=observation.symbol,
        action=observation.action,
        signal_price=observation.signal_price,
        returns=tuple(returns),
        max_favorable_pct=max(favorable, default=0.0),
        max_adverse_pct=min(favorable, default=0.0),
        target_1_hit=any(
            price >= observation.target_1
            if observation.action == TradeAction.BUY
            else price <= observation.target_1
            for _, price in observation.prices
        ),
        target_2_hit=any(
            price >= observation.target_2
            if observation.action == TradeAction.BUY
            else price <= observation.target_2
            for _, price in observation.prices
        ),
        stop_loss_hit=any(
            price <= observation.stop_loss
            if observation.action == TradeAction.BUY
            else price >= observation.stop_loss
            for _, price in observation.prices
        ),
    )

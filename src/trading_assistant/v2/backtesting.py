"""Deterministic V2 backtesting primitives.

The engine consumes precomputed trade signals and never invents market data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestTrade:
    """One completed or simulated trade expressed in R multiples."""

    symbol: str
    direction: str
    entry: float
    exit_price: float
    stop_loss: float
    target: float

    @property
    def risk_per_share(self) -> float:
        return abs(self.entry - self.stop_loss)

    @property
    def r_multiple(self) -> float:
        risk = self.risk_per_share
        if risk <= 0:
            return 0.0
        reward = (
            self.exit_price - self.entry
            if self.direction.upper() == "BUY"
            else self.entry - self.exit_price
        )
        return reward / risk


@dataclass(frozen=True)
class BacktestResult:
    """Summary metrics for a collection of completed trades."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_win_r: float
    average_loss_r: float
    expectancy_r: float
    profit_factor: float | None
    max_drawdown_r: float
    total_r: float


def run_backtest(trades: list[BacktestTrade]) -> BacktestResult:
    """Calculate performance without changing or filtering supplied trades."""
    returns = [trade.r_multiple for trade in trades]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)

    total = len(returns)
    return BacktestResult(
        total_trades=total,
        winning_trades=len(wins),
        losing_trades=len(losses),
        win_rate=(len(wins) / total * 100) if total else 0.0,
        average_win_r=(sum(wins) / len(wins)) if wins else 0.0,
        average_loss_r=(sum(losses) / len(losses)) if losses else 0.0,
        expectancy_r=(sum(returns) / total) if total else 0.0,
        profit_factor=(gross_profit / gross_loss) if gross_loss else None,
        max_drawdown_r=max_drawdown,
        total_r=sum(returns),
    )

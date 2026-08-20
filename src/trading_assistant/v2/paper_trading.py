"""Simple in-memory paper-trading portfolio for V2 validation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PaperPosition:
    """A simulated position with a fixed entry and risk plan."""

    symbol: str
    direction: str
    quantity: int
    entry: float
    stop_loss: float
    target: float

    def unrealized_pnl(self, price: float) -> float:
        move = price - self.entry
        if self.direction.upper() == "SELL":
            move = -move
        return move * self.quantity


@dataclass
class PaperPortfolio:
    """Cash and positions for non-broker paper trading."""

    starting_cash: float
    cash: float | None = None
    positions: list[PaperPosition] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.starting_cash <= 0:
            raise ValueError("starting_cash must be positive")
        if self.cash is None:
            self.cash = self.starting_cash

    def open_position(self, position: PaperPosition) -> None:
        if position.quantity <= 0:
            raise ValueError("quantity must be positive")
        required = position.entry * position.quantity
        if required > (self.cash or 0):
            raise ValueError("insufficient paper cash")
        self.cash = (self.cash or 0) - required
        self.positions.append(position)

    def mark_to_market(self, prices: dict[str, float]) -> float:
        """Return cash plus marked value of all open positions."""
        value = self.cash or 0
        for position in self.positions:
            price = prices.get(position.symbol, position.entry)
            value += position.entry * position.quantity
            value += position.unrealized_pnl(price)
        return value

    @property
    def realized_free_cash(self) -> float:
        return self.cash or 0

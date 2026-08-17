"""Persistent, JSON-friendly signal performance history."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from trading_assistant.analysis.trade_decision import TradeAction
from trading_assistant.monitoring.performance import SignalPerformance


@dataclass(frozen=True)
class StoredPerformance:
    """Serializable performance record."""

    symbol: str
    action: str
    signal_price: float
    signal_time: str
    returns: tuple[tuple[int, float], ...]
    max_favorable_pct: float
    max_adverse_pct: float
    target_1_hit: bool
    target_2_hit: bool
    stop_loss_hit: bool

    @classmethod
    def from_performance(
        cls,
        result: SignalPerformance,
        signal_time: datetime,
    ) -> "StoredPerformance":
        return cls(
            symbol=result.symbol,
            action=result.action.value,
            signal_price=result.signal_price,
            signal_time=signal_time.isoformat(),
            returns=result.returns,
            max_favorable_pct=result.max_favorable_pct,
            max_adverse_pct=result.max_adverse_pct,
            target_1_hit=result.target_1_hit,
            target_2_hit=result.target_2_hit,
            stop_loss_hit=result.stop_loss_hit,
        )

    def to_performance(self) -> SignalPerformance:
        return SignalPerformance(
            symbol=self.symbol,
            action=TradeAction(self.action),
            signal_price=self.signal_price,
            returns=self.returns,
            max_favorable_pct=self.max_favorable_pct,
            max_adverse_pct=self.max_adverse_pct,
            target_1_hit=self.target_1_hit,
            target_2_hit=self.target_2_hit,
            stop_loss_hit=self.stop_loss_hit,
        )


class PerformanceStore:
    """Append and reload signal-performance records from a JSON file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: StoredPerformance) -> None:
        records = self.load()
        records.append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([asdict(item) for item in records], indent=2),
            encoding="utf-8",
        )

    def load(self) -> list[StoredPerformance]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [
            StoredPerformance(
                symbol=item["symbol"],
                action=item["action"],
                signal_price=float(item["signal_price"]),
                signal_time=item["signal_time"],
                returns=tuple((int(h), float(v)) for h, v in item["returns"]),
                max_favorable_pct=float(item["max_favorable_pct"]),
                max_adverse_pct=float(item["max_adverse_pct"]),
                target_1_hit=bool(item["target_1_hit"]),
                target_2_hit=bool(item["target_2_hit"]),
                stop_loss_hit=bool(item["stop_loss_hit"]),
            )
            for item in raw
        ]

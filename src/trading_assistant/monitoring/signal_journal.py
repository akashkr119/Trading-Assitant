"""Persistent paper-trading signal journal and outcome evaluation."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SignalRecord:
    """Immutable alert plan plus live paper-trading outcome state."""

    signal_id: str
    timestamp: str
    market: str
    symbol: str
    direction: str
    score: float
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward: float
    reason: str
    status: str = "OPEN"
    exit_price: float | None = None
    outcome_r: float | None = None
    resolved_at: str | None = None
    target_1_achieved: bool = False
    target_2_achieved: bool = False
    stop_loss_hit: bool = False
    sell_price: float | None = None


@dataclass(frozen=True)
class JournalSummary:
    """Aggregate paper-trading performance."""

    total: int
    open: int
    wins: int
    losses: int
    invalidated: int
    win_rate: float
    target_1_rate: float
    target_2_rate: float
    average_r: float
    expectancy_r: float
    profit_factor: float
    max_drawdown_r: float


class SignalJournal:
    """Store alert plans and their live paper-trading outcome state."""

    FIELDS = tuple(SignalRecord.__dataclass_fields__)

    def __init__(self, path: str | Path = "reports/signal_journal.csv") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._rewrite([])
        else:
            self._migrate_schema()

    def record(self, signal: SignalRecord) -> None:
        """Append a signal without overwriting historical records."""
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=self.FIELDS).writerow(asdict(signal))

    def records(self) -> list[SignalRecord]:
        if not self.path.exists():
            return []
        with self.path.open("r", newline="", encoding="utf-8") as handle:
            return [self._from_row(row) for row in csv.DictReader(handle)]

    def update_live_state(
        self,
        signal_id: str,
        target_1_achieved: bool,
        target_2_achieved: bool,
        stop_loss_hit: bool,
        sell_price: float | None,
    ) -> bool:
        """Update live target/stop state and the planned paper sell price."""
        records = self.records()
        updated = False
        replacement: list[SignalRecord] = []
        for record in records:
            if record.signal_id != signal_id or record.status != "OPEN":
                replacement.append(record)
                continue
            replacement.append(
                SignalRecord(
                    **{
                        **asdict(record),
                        "target_1_achieved": record.target_1_achieved or target_1_achieved,
                        "target_2_achieved": record.target_2_achieved or target_2_achieved,
                        "stop_loss_hit": record.stop_loss_hit or stop_loss_hit,
                        "sell_price": sell_price or record.sell_price,
                    }
                )
            )
            updated = True
        if updated:
            self._rewrite(replacement)
        return updated

    def resolve(
        self,
        signal_id: str,
        status: str,
        exit_price: float,
        outcome_r: float,
        resolved_at: datetime,
    ) -> bool:
        """Close a signal while preserving its original risk plan."""
        records = self.records()
        updated = False
        replacement: list[SignalRecord] = []
        for record in records:
            if record.signal_id != signal_id or record.status != "OPEN":
                replacement.append(record)
                continue
            replacement.append(
                SignalRecord(
                    **{
                        **asdict(record),
                        "status": status,
                        "exit_price": exit_price,
                        "sell_price": exit_price,
                        "outcome_r": outcome_r,
                        "resolved_at": resolved_at.isoformat(),
                    }
                )
            )
            updated = True
        if updated:
            self._rewrite(replacement)
        return updated

    def summary(self) -> JournalSummary:
        records = self.records()
        closed = [r for r in records if r.outcome_r is not None]
        wins = [r for r in closed if r.outcome_r > 0]
        losses = [r for r in closed if r.outcome_r < 0]
        target_1 = [
            r
            for r in records
            if r.target_1_achieved or r.status in {"TARGET_1", "TARGET_2"}
        ]
        target_2 = [
            r for r in records if r.target_2_achieved or r.status == "TARGET_2"
        ]
        values = [float(r.outcome_r) for r in closed]
        average_r = sum(values) / len(values) if values else 0.0
        gross_profit = sum(v for v in values if v > 0)
        gross_loss = abs(sum(v for v in values if v < 0))
        equity = peak = drawdown = 0.0
        for value in values:
            equity += value
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
        return JournalSummary(
            total=len(records),
            open=len(records) - len(closed),
            wins=len(wins),
            losses=len(losses),
            invalidated=sum(r.status == "INVALIDATED" for r in closed),
            win_rate=(len(wins) / len(closed) * 100) if closed else 0.0,
            target_1_rate=(len(target_1) / len(records) * 100) if records else 0.0,
            target_2_rate=(len(target_2) / len(records) * 100) if records else 0.0,
            average_r=average_r,
            expectancy_r=average_r,
            profit_factor=(gross_profit / gross_loss) if gross_loss else 0.0,
            max_drawdown_r=drawdown,
        )

    def _migrate_schema(self) -> None:
        with self.path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) == self.FIELDS:
                return
            records = [self._from_row(row) for row in reader]
        self._rewrite(records)

    def _rewrite(self, records: list[SignalRecord]) -> None:
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.FIELDS)
            writer.writeheader()
            writer.writerows(asdict(record) for record in records)

    @staticmethod
    def _from_row(row: dict[str, str]) -> SignalRecord:
        def optional_float(value: str | None) -> float | None:
            return float(value) if value else None

        def optional_bool(value: str | None) -> bool:
            return str(value).lower() == "true"

        return SignalRecord(
            signal_id=row["signal_id"],
            timestamp=row["timestamp"],
            market=row["market"],
            symbol=row["symbol"],
            direction=row["direction"],
            score=float(row["score"]),
            entry=float(row["entry"]),
            stop_loss=float(row["stop_loss"]),
            target_1=float(row["target_1"]),
            target_2=float(row["target_2"]),
            risk_reward=float(row["risk_reward"]),
            reason=row["reason"],
            status=row.get("status") or "OPEN",
            exit_price=optional_float(row.get("exit_price")),
            outcome_r=optional_float(row.get("outcome_r")),
            resolved_at=row.get("resolved_at") or None,
            target_1_achieved=optional_bool(row.get("target_1_achieved")),
            target_2_achieved=optional_bool(row.get("target_2_achieved")),
            stop_loss_hit=optional_bool(row.get("stop_loss_hit")),
            sell_price=optional_float(row.get("sell_price")),
        )

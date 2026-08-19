"""UI-neutral dashboard snapshot built from the trading engine state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from trading_assistant.analysis.pipeline import StockAnalysisResult
from trading_assistant.brokers.session import BrokerSession
from trading_assistant.monitoring.watchlist import Watchlist


@dataclass(frozen=True)
class SignalCard:
    symbol: str
    decision: str
    score: float
    setup: str
    reason: str
    risk_summary: str
    invalidation: str


@dataclass(frozen=True)
class DashboardSnapshot:
    generated_at: datetime
    broker: BrokerSession | None
    watchlist: Watchlist
    signals: tuple[SignalCard, ...]


def build_dashboard_snapshot(
    *,
    generated_at: datetime,
    broker: BrokerSession | None,
    watchlist: Watchlist,
    results: tuple[StockAnalysisResult, ...],
) -> DashboardSnapshot:
    """Convert analysis results into safe, display-ready dashboard cards."""
    cards = tuple(
        SignalCard(
            symbol=result.symbol,
            decision=result.decision.action.value,
            score=result.decision.score,
            setup=result.setup.setup_type.value,
            reason=result.explanation.why_this_decision,
            risk_summary=result.explanation.risk_summary,
            invalidation=result.explanation.invalidation,
        )
        for result in results
    )
    return DashboardSnapshot(
        generated_at=generated_at,
        broker=broker,
        watchlist=watchlist,
        signals=cards,
    )

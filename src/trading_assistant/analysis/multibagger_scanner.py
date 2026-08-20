"""Rank an explicitly supplied NSE universe using fundamental evidence."""

from __future__ import annotations

from dataclasses import dataclass

from trading_assistant.analysis.multibagger_scoring import MultibaggerScore, score_multibagger
from trading_assistant.data.fundamentals import FundamentalsSnapshot
from trading_assistant.data.fundamentals_provider import FundamentalsProvider


@dataclass(frozen=True)
class MultibaggerCandidate:
    """One ranked long-term candidate."""

    symbol: str
    company_name: str
    score: MultibaggerScore


@dataclass(frozen=True)
class ScanFailure:
    """A symbol that could not be scored without hiding the data failure."""

    symbol: str
    reason: str


@dataclass(frozen=True)
class MultibaggerScan:
    """Ranked candidates plus transparent failures."""

    candidates: tuple[MultibaggerCandidate, ...]
    failures: tuple[ScanFailure, ...]


class MultibaggerScanner:
    """Scan a supplied universe through the configured fundamentals provider."""

    def __init__(self, provider: FundamentalsProvider) -> None:
        self.provider = provider

    def scan(self, symbols: list[str], limit: int = 10) -> MultibaggerScan:
        candidates: list[MultibaggerCandidate] = []
        failures: list[ScanFailure] = []
        for symbol in symbols:
            try:
                snapshot: FundamentalsSnapshot = self.provider.get_fundamentals(symbol)
                score = score_multibagger(snapshot)
                if score.coverage < 60:
                    failures.append(
                        ScanFailure(symbol, "Insufficient fundamental data coverage.")
                    )
                    continue
                candidates.append(
                    MultibaggerCandidate(symbol, snapshot.company_name, score)
                )
            except Exception as error:
                failures.append(ScanFailure(symbol, str(error)))
        candidates.sort(key=lambda item: item.score.overall, reverse=True)
        return MultibaggerScan(tuple(candidates[:limit]), tuple(failures))

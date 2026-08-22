"""Standalone crypto validation runner for full-session engine testing.

This runner is intentionally separate from the Streamlit live dashboard. A single
cycle scans the same production crypto engine, records confirmed alerts, and
checks existing open alerts for target/stop outcomes using recent 1-minute bars.
The workflow can invoke one cycle repeatedly without requiring a browser session.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone

from trading_assistant.data.crypto import BinanceMarketDataProvider
from trading_assistant.data.interfaces import Timeframe
from trading_assistant.monitoring.crypto_intraday_scanner import (
    CryptoCandidate,
    RobustCryptoIntradayScanner,
)
from trading_assistant.monitoring.signal_journal import SignalJournal, SignalRecord

JOURNAL_PATH = "reports/crypto_validation_journal.csv"
SCAN_INTERVAL_SECONDS = 300


def _candidate_record(candidate: CryptoCandidate, timestamp: datetime) -> SignalRecord:
    return SignalRecord(
        signal_id=(
            f"validation-{candidate.symbol}-{candidate.direction}-"
            f"{timestamp.isoformat()}"
        ),
        timestamp=timestamp.isoformat(),
        market="CRYPTO_VALIDATION",
        symbol=candidate.symbol,
        direction=candidate.direction,
        score=candidate.score,
        entry=candidate.entry,
        stop_loss=candidate.stop_loss,
        target_1=candidate.target_1,
        target_2=candidate.target_2,
        risk_reward=candidate.risk_reward,
        reason=candidate.reason,
    )


def _record_new_alerts(
    journal: SignalJournal,
    candidates: tuple[CryptoCandidate, ...],
    timestamp: datetime,
) -> int:
    records = journal.records()
    added = 0
    for candidate in candidates:
        if candidate.score < 75:
            continue
        duplicate = any(
            record.symbol == candidate.symbol
            and record.direction == candidate.direction
            and record.status == "OPEN"
            and abs(record.entry - candidate.entry) / max(candidate.entry, 1e-12) < 0.0005
            for record in records
            if record.market == "CRYPTO_VALIDATION"
        )
        if duplicate:
            continue
        record = _candidate_record(candidate, timestamp)
        journal.record(record)
        records.append(record)
        added += 1
    return added


def _open_validation_records(journal: SignalJournal) -> list[SignalRecord]:
    return [
        record
        for record in journal.records()
        if record.market == "CRYPTO_VALIDATION" and record.status == "OPEN"
    ]


def _first_closed_bar_start(signal_timestamp: datetime) -> datetime:
    """Return the first full 1m candle that begins after the signal."""
    return signal_timestamp.replace(second=0, microsecond=0) + timedelta(minutes=1)


def _update_outcomes(
    provider: BinanceMarketDataProvider,
    journal: SignalJournal,
    timestamp: datetime,
) -> int:
    """Evaluate only candles that formed after each alert was generated."""
    resolved = 0
    current_bar_start = timestamp.replace(second=0, microsecond=0)
    for record in _open_validation_records(journal):
        try:
            signal_timestamp = datetime.fromisoformat(record.timestamp)
            start = _first_closed_bar_start(signal_timestamp)
            if start >= current_bar_start:
                continue
            bars = provider.get_ohlcv(
                record.symbol,
                Timeframe.ONE_MINUTE,
                start,
                current_bar_start,
            )
        except Exception:
            continue

        for bar in bars:
            # Never use a candle from before the alert or the still-forming candle.
            if bar.timestamp < start or bar.timestamp >= current_bar_start:
                continue
            long = record.direction == "LONG"
            target_1 = bar.high >= record.target_1 if long else bar.low <= record.target_1
            target_2 = bar.high >= record.target_2 if long else bar.low <= record.target_2
            stop = bar.low <= record.stop_loss if long else bar.high >= record.stop_loss

            if target_2 and stop:
                # Intrabar ordering is unknowable from OHLC alone. Use a
                # conservative stop-first rule rather than overstating accuracy.
                target_2 = False
                target_1 = False
                stop = True

            if stop:
                journal.update_live_state(
                    record.signal_id,
                    target_1_achieved=record.target_1_achieved,
                    target_2_achieved=False,
                    stop_loss_hit=True,
                    sell_price=record.stop_loss,
                )
                journal.resolve(
                    record.signal_id,
                    status="STOP_LOSS",
                    exit_price=record.stop_loss,
                    outcome_r=-1.0,
                    resolved_at=bar.timestamp,
                )
                resolved += 1
                break

            if target_2:
                journal.update_live_state(
                    record.signal_id,
                    target_1_achieved=True,
                    target_2_achieved=True,
                    stop_loss_hit=False,
                    sell_price=record.target_2,
                )
                journal.resolve(
                    record.signal_id,
                    status="TARGET_2",
                    exit_price=record.target_2,
                    outcome_r=record.risk_reward,
                    resolved_at=bar.timestamp,
                )
                resolved += 1
                break

            if target_1 and not record.target_1_achieved:
                journal.update_live_state(
                    record.signal_id,
                    target_1_achieved=True,
                    target_2_achieved=False,
                    stop_loss_hit=False,
                    sell_price=record.target_1,
                )
                record = next(
                    item
                    for item in journal.records()
                    if item.signal_id == record.signal_id
                )
    return resolved


def run_cycle(
    *,
    provider: BinanceMarketDataProvider | None = None,
    journal: SignalJournal | None = None,
) -> dict[str, int | float]:
    """Run one validation scan plus outcome-check cycle."""
    provider = provider or BinanceMarketDataProvider()
    journal = journal or SignalJournal(JOURNAL_PATH)
    timestamp = datetime.now(timezone.utc)
    scanner = RobustCryptoIntradayScanner(provider)
    candidates = scanner.scan(timestamp, limit=10)
    alerts_added = _record_new_alerts(journal, candidates, timestamp)
    outcomes = _update_outcomes(provider, journal, timestamp)
    summary = journal.summary()
    return {
        "scanned": scanner.last_scan_count,
        "qualified": scanner.last_qualified_count,
        "alerts_added": alerts_added,
        "outcomes_resolved": outcomes,
        "total_alerts": summary.total,
        "closed": summary.total - summary.open,
        "win_rate": round(summary.win_rate, 2),
        "target_1_rate": round(summary.target_1_rate, 2),
        "target_2_rate": round(summary.target_2_rate, 2),
        "average_r": round(summary.average_r, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Crypto engine validation.")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit.")
    parser.add_argument(
        "--interval",
        type=int,
        default=SCAN_INTERVAL_SECONDS,
        help="Seconds between cycles when running continuously.",
    )
    args = parser.parse_args()

    while True:
        result = run_cycle()
        print(result, flush=True)
        if args.once:
            return
        time.sleep(max(args.interval, 60))


if __name__ == "__main__":
    main()

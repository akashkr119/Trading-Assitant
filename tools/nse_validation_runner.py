"""Run the live NSE intraday engine continuously during market hours."""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime

from trading_assistant.application.live_analysis import LiveAnalysisService
from trading_assistant.brokers.connection import BrokerName
from trading_assistant.data.interfaces import Timeframe
from trading_assistant.data.market_calendar import IST
from trading_assistant.data.provider_factory import build_market_data_provider
from trading_assistant.monitoring.market_scanner import MarketScanner
from trading_assistant.monitoring.signal_journal import SignalJournal, SignalRecord

JOURNAL_PATH = "reports/nse_signal_journal.csv"
DEFAULT_INTERVAL = 60


def _outcome_r(record: SignalRecord, exit_price: float) -> float:
    risk = abs(record.entry - record.stop_loss)
    if risk == 0:
        return 0.0
    if record.direction == "BUY":
        return (exit_price - record.entry) / risk
    return (record.entry - exit_price) / risk


def _record_results(
    results: tuple[object, ...],
    now: datetime,
    journal: SignalJournal,
) -> int:
    existing = journal.records()
    recorded = 0
    for result in results:
        action = result.decision.action.value
        if action not in {"BUY", "SELL"} or result.risk_plan is None:
            continue
        if any(
            record.symbol == result.symbol
            and record.direction == action
            and record.status == "OPEN"
            for record in existing
        ):
            continue
        risk = result.risk_plan
        risk_amount = abs(risk.entry - risk.stop_loss)
        journal.record(
            SignalRecord(
                signal_id=f"nse-{result.symbol}-{action}-{now.isoformat()}",
                timestamp=now.isoformat(),
                market="NSE",
                symbol=result.symbol,
                direction=action,
                score=result.decision.score,
                entry=risk.entry,
                stop_loss=risk.stop_loss,
                target_1=risk.target_1,
                target_2=risk.target_2,
                risk_reward=(
                    abs(risk.target_2 - risk.entry) / risk_amount
                    if risk_amount
                    else 0.0
                ),
                reason=result.explanation.why_this_decision,
            )
        )
        existing.append(journal.records()[-1])
        recorded += 1
    return recorded


def _update_outcomes(
    provider,
    journal: SignalJournal,
    now: datetime,
) -> tuple[int, int, int]:
    t1_count = 0
    t2_count = 0
    stop_count = 0
    for record in journal.records():
        if record.status != "OPEN":
            continue
        try:
            latest = provider.get_latest_bar(record.symbol, Timeframe.ONE_MINUTE)
            price = float(latest.close)
        except Exception as error:
            print(f"  outcome data error {record.symbol}: {error}", flush=True)
            continue
        if record.direction == "BUY":
            t1_hit = price >= record.target_1
            t2_hit = price >= record.target_2
            stop_hit = price <= record.stop_loss
        else:
            t1_hit = price <= record.target_1
            t2_hit = price <= record.target_2
            stop_hit = price >= record.stop_loss
        exit_price = record.target_2 if t2_hit else record.stop_loss if stop_hit else None
        journal.update_live_state(
            record.signal_id,
            t1_hit,
            t2_hit,
            stop_hit,
            exit_price,
        )
        if t1_hit:
            t1_count += 1
        if t2_hit:
            t2_count += 1
        if stop_hit:
            stop_count += 1
        if t2_hit:
            journal.resolve(
                record.signal_id,
                "TARGET_2_ACHIEVED",
                record.target_2,
                _outcome_r(record, record.target_2),
                now,
            )
        elif stop_hit:
            journal.resolve(
                record.signal_id,
                "STOP_LOSS_HIT",
                record.stop_loss,
                _outcome_r(record, record.stop_loss),
                now,
            )
    return t1_count, t2_count, stop_count


def _broker_name() -> BrokerName:
    value = os.getenv("NSE_VALIDATION_BROKER", "groww").strip().lower()
    return BrokerName(value)


def run_cycle(
    scanner: MarketScanner,
    service: LiveAnalysisService,
    journal: SignalJournal,
) -> None:
    now = datetime.now(IST)
    candidates = scanner.scan(now, limit=60)
    alert_candidates = candidates[:20]
    results = service.analyze([item.symbol for item in alert_candidates], now)
    recorded = _record_results(results, now, journal)
    t1_count, t2_count, stop_count = _update_outcomes(
        scanner.provider,
        journal,
        now,
    )
    summary = journal.summary()
    total_r = sum(r.outcome_r or 0.0 for r in journal.records())
    print(
        f"{now:%H:%M:%S} IST | NSE VALIDATOR ALIVE | "
        f"scanned={scanner.last_scan_count} "
        f"data={scanner.last_data_count} "
        f"qualified={scanner.last_qualified_count} "
        f"BUY/SELL recorded={recorded} "
        f"T1={t1_count} T2={t2_count} SL={stop_count} "
        f"open={summary.open} closed={summary.total - summary.open} "
        f"win-rate={summary.win_rate:.1f}% total-R={total_r:+.2f}R",
        flush=True,
    )
    if service.errors:
        print(
            f"  analysis errors={len(service.errors)}; "
            f"scanner universe={scanner.last_universe_source}",
            flush=True,
        )


def _sleep_until_market(provider, poll_seconds: int) -> bool:
    while not provider.is_market_open():
        now = datetime.now(IST)
        if now.weekday() >= 5:
            print(
                f"{now:%Y-%m-%d %H:%M:%S} IST | "
                "NSE closed (weekend). Exiting.",
                flush=True,
            )
            return False
        if now.hour > 15 or (now.hour == 15 and now.minute >= 31):
            print(
                f"{now:%Y-%m-%d %H:%M:%S} IST | "
                "NSE session finished. Exiting.",
                flush=True,
            )
            return False
        print(
            f"{now:%Y-%m-%d %H:%M:%S} IST | NSE market closed; "
            f"waiting {poll_seconds}s for the session...",
            flush=True,
        )
        time.sleep(poll_seconds)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help="Seconds between validation cycles (default: 60).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one cycle when the market is open.",
    )
    args = parser.parse_args()
    if args.interval < 10:
        parser.error("--interval must be at least 10 seconds")

    broker = _broker_name()
    provider = build_market_data_provider(broker)
    scanner = MarketScanner(provider)
    service = LiveAnalysisService(provider)
    journal = SignalJournal(JOURNAL_PATH)

    print(
        f"NSE validation monitor starting | broker={broker.value} | "
        f"interval={args.interval}s | journal={JOURNAL_PATH}",
        flush=True,
    )

    if not _sleep_until_market(provider, min(args.interval, 60)):
        return

    run_cycle(scanner, service, journal)
    if args.once:
        return

    while True:
        time.sleep(args.interval)
        now = datetime.now(IST)
        if not provider.is_market_open():
            print(
                f"{now:%Y-%m-%d %H:%M:%S} IST | NSE market closed. "
                "Final validation cycle complete; exiting.",
                flush=True,
            )
            return
        try:
            run_cycle(scanner, service, journal)
        except KeyboardInterrupt:
            print("NSE validation monitor stopped by user.", flush=True)
            return
        except Exception as error:
            print(f"Validation cycle failed: {error}", flush=True)
            print("Retrying on the next cycle.", flush=True)


if __name__ == "__main__":
    main()

"""Build a human-readable summary from the crypto validation journal."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from trading_assistant.monitoring.signal_journal import SignalJournal

JOURNAL_PATH = "reports/crypto_validation_journal.csv"
REPORT_PATH = "reports/crypto_validation_summary.md"


def build_report(
    journal_path: str = JOURNAL_PATH,
    report_path: str = REPORT_PATH,
) -> Path:
    journal = SignalJournal(journal_path)
    records = journal.records()
    summary = journal.summary()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Crypto Engine Validation",
        "",
        f"Generated: {generated}",
        "",
        "## Performance",
        "",
        f"- Total alerts: **{summary.total}**",
        f"- Closed alerts: **{summary.total - summary.open}**",
        f"- Open alerts: **{summary.open}**",
        f"- Wins: **{summary.wins}**",
        f"- Losses: **{summary.losses}**",
        f"- Win rate: **{summary.win_rate:.2f}%**",
        f"- Target 1 hit rate: **{summary.target_1_rate:.2f}%**",
        f"- Target 2 hit rate: **{summary.target_2_rate:.2f}%**",
        f"- Average outcome: **{summary.average_r:+.3f}R**",
        f"- Expectancy: **{summary.expectancy_r:+.3f}R**",
        f"- Profit factor: **{summary.profit_factor:.2f}**",
        f"- Max drawdown: **{summary.max_drawdown_r:.3f}R**",
        "",
        "## Alert History",
        "",
        "| Time | Symbol | Alert | Entry | T1 | T2 | Stop | Status | Outcome |",
        "|---|---|---|---:|---:|---:|---:|---|---:|",
    ]
    for record in reversed(records):
        alert = "BUY" if record.direction == "LONG" else "SELL"
        t1 = "✅" if record.target_1_achieved else "—"
        t2 = "✅" if record.target_2_achieved else "—"
        stop = "🛑" if record.stop_loss_hit else "—"
        outcome = f"{record.outcome_r:+.2f}R" if record.outcome_r is not None else "OPEN"
        lines.append(
            f"| {record.timestamp} | {record.symbol} | {alert} | "
            f"{record.entry:.8g} | {t1} | {t2} | {stop} | "
            f"{record.status} | {outcome} |"
        )

    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print(build_report())

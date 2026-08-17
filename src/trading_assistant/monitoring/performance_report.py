"""Aggregate persisted signal outcomes into human-readable reports."""

from __future__ import annotations

from dataclasses import dataclass

from trading_assistant.monitoring.performance import SignalPerformance


@dataclass(frozen=True)
class PerformanceReport:
    total_signals: int
    favorable_signals: int
    target_1_rate_pct: float
    target_2_rate_pct: float
    stop_loss_rate_pct: float
    average_favorable_pct: float
    average_adverse_pct: float
    horizon_accuracy_pct: tuple[tuple[int, float], ...]


def build_report(results: list[SignalPerformance]) -> PerformanceReport:
    """Build aggregate performance metrics from completed observations."""
    total = len(results)
    if not total:
        return PerformanceReport(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, ())

    def rate(predicate) -> float:
        return sum(predicate(item) for item in results) / total * 100

    horizons = sorted({h for item in results for h, _ in item.returns})
    horizon_accuracy = tuple(
        (
            horizon,
            rate(
                lambda item, horizon=horizon: next(
                    (value >= 0 for h, value in item.returns if h == horizon),
                    False,
                )
            ),
        )
        for horizon in horizons
    )
    return PerformanceReport(
        total_signals=total,
        favorable_signals=sum(item.max_favorable_pct > 0 for item in results),
        target_1_rate_pct=rate(lambda item: item.target_1_hit),
        target_2_rate_pct=rate(lambda item: item.target_2_hit),
        stop_loss_rate_pct=rate(lambda item: item.stop_loss_hit),
        average_favorable_pct=sum(item.max_favorable_pct for item in results) / total,
        average_adverse_pct=sum(item.max_adverse_pct for item in results) / total,
        horizon_accuracy_pct=horizon_accuracy,
    )


def report_as_markdown(report: PerformanceReport) -> str:
    """Render a compact report suitable for the dashboard or daily export."""
    lines = [
        "# Trading Assistant Signal Performance",
        "",
        f"Signals: {report.total_signals}",
        f"Favorable: {report.favorable_signals}",
        f"Target 1 hit rate: {report.target_1_rate_pct:.1f}%",
        f"Target 2 hit rate: {report.target_2_rate_pct:.1f}%",
        f"Stop-loss hit rate: {report.stop_loss_rate_pct:.1f}%",
        f"Average MFE: {report.average_favorable_pct:.2f}%",
        f"Average MAE: {report.average_adverse_pct:.2f}%",
        "",
        "## Forward performance",
    ]
    lines.extend(f"- {horizon} min: {accuracy:.1f}% favorable" for horizon, accuracy in report.horizon_accuracy_pct)
    return "\n".join(lines)

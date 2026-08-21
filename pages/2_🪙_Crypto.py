"""Crypto trading page for the Trading Assistant."""

from datetime import datetime, timezone

import streamlit as st

from trading_assistant.data.crypto import BinanceMarketDataProvider
from trading_assistant.monitoring.crypto_intraday_scanner import (
    CryptoCandidate,
    RobustCryptoIntradayScanner,
)
from trading_assistant.monitoring.signal_journal import SignalJournal, SignalRecord
from trading_assistant.ui.theme import inject_responsive_css, page_header, section_header

st.set_page_config(page_title="Crypto Trading", page_icon="🪙", layout="wide")
inject_responsive_css()
page_header(
    "🪙 Crypto Intraday",
    "24/7 market intelligence with locked trade plans and live confirmation.",
    accent="cyan",
)

provider = BinanceMarketDataProvider()
scanner = st.session_state.get("crypto_scanner")
if scanner is None or not isinstance(scanner, RobustCryptoIntradayScanner):
    scanner = RobustCryptoIntradayScanner(provider)
    st.session_state.crypto_scanner = scanner
journal = SignalJournal()


def _live_signal_state(candidate: CryptoCandidate, snapshot) -> tuple[str, str]:
    """Describe current health without rewriting the locked scan signal."""
    long = candidate.direction == "LONG"
    invalidated = (
        snapshot.price <= candidate.stop_loss
        if long
        else snapshot.price >= candidate.stop_loss
    )
    if invalidated:
        return "INVALIDATED", "Price has crossed the locked stop-loss level."

    trend_ok = snapshot.trend_5m == ("BULLISH" if long else "BEARISH")
    trend_15_ok = snapshot.trend_15m == ("BULLISH" if long else "BEARISH")
    ema_ok = snapshot.ema9 > snapshot.ema20 if long else snapshot.ema9 < snapshot.ema20
    macd_ok = snapshot.macd_histogram > 0 if long else snapshot.macd_histogram < 0
    rsi_ok = 50 <= snapshot.rsi <= 75 if long else 25 <= snapshot.rsi <= 50
    rvol_ok = snapshot.relative_volume >= 1.0

    if trend_ok and trend_15_ok and ema_ok and macd_ok and rsi_ok and rvol_ok:
        return "CONFIRMED", "Live conditions still confirm the original scan direction."
    if trend_ok and trend_15_ok and ema_ok and macd_ok:
        return (
            "MOMENTUM COOLING",
            "Trend, EMA and MACD remain aligned, but one confirmation is weaker.",
        )
    if not trend_ok and not trend_15_ok and not macd_ok:
        return "REVERSAL WATCH", "Multiple live indicators now oppose the original scan direction."
    return "WATCH", "The original signal remains locked, but live confirmation is mixed."


def _record_scan_alerts(candidates: tuple[CryptoCandidate, ...], timestamp: datetime) -> None:
    """Persist confirmed BUY/SELL scan decisions without duplicating an open plan."""
    existing = [record for record in journal.records() if record.market == "CRYPTO"]
    for candidate in candidates:
        if candidate.score < 75:
            continue
        duplicate = any(
            record.symbol == candidate.symbol
            and record.direction == candidate.direction
            and record.status == "OPEN"
            and abs(record.entry - candidate.entry) / max(candidate.entry, 1e-12) < 0.0005
            for record in existing
        )
        if duplicate:
            continue
        journal.record(
            SignalRecord(
                signal_id=(
                    f"crypto-{candidate.symbol}-{candidate.direction}-"
                    f"{timestamp.isoformat()}"
                ),
                timestamp=timestamp.isoformat(),
                market="CRYPTO",
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
        )
        existing.append(
            SignalRecord(
                signal_id="temporary",
                timestamp=timestamp.isoformat(),
                market="CRYPTO",
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
        )


def _find_open_record(candidate: CryptoCandidate) -> SignalRecord | None:
    """Find the journal record that belongs to the currently displayed plan."""
    records = journal.records()
    matches = [
        record
        for record in records
        if record.market == "CRYPTO"
        and record.symbol == candidate.symbol
        and record.direction == candidate.direction
        and record.status == "OPEN"
        and abs(record.entry - candidate.entry) / max(candidate.entry, 1e-12) < 0.0005
    ]
    return matches[-1] if matches else None


def _update_trade_outcome(candidate: CryptoCandidate, live_price: float) -> SignalRecord | None:
    """Persist target/stop milestones and close the paper trade when resolved."""
    record = _find_open_record(candidate)
    if record is None:
        return None

    long = candidate.direction == "LONG"
    target_1_hit = live_price >= candidate.target_1 if long else live_price <= candidate.target_1
    target_2_hit = live_price >= candidate.target_2 if long else live_price <= candidate.target_2
    stop_hit = live_price <= candidate.stop_loss if long else live_price >= candidate.stop_loss

    new_t1 = target_1_hit and not record.target_1_achieved
    new_t2 = target_2_hit and not record.target_2_achieved
    new_stop = stop_hit and not record.stop_loss_hit

    if new_t2:
        journal.update_live_state(
            record.signal_id,
            target_1_achieved=True,
            target_2_achieved=True,
            stop_loss_hit=False,
            sell_price=candidate.target_2,
        )
        journal.resolve(
            record.signal_id,
            status="TARGET_2",
            exit_price=candidate.target_2,
            outcome_r=candidate.risk_reward,
            resolved_at=datetime.now(timezone.utc),
        )
        st.rerun()
    elif new_stop:
        journal.update_live_state(
            record.signal_id,
            target_1_achieved=False,
            target_2_achieved=False,
            stop_loss_hit=True,
            sell_price=candidate.stop_loss,
        )
        journal.resolve(
            record.signal_id,
            status="STOP_LOSS",
            exit_price=candidate.stop_loss,
            outcome_r=-1.0,
            resolved_at=datetime.now(timezone.utc),
        )
        st.rerun()
    elif new_t1:
        journal.update_live_state(
            record.signal_id,
            target_1_achieved=True,
            target_2_achieved=False,
            stop_loss_hit=False,
            sell_price=candidate.target_1,
        )
        st.rerun()

    records = journal.records()
    return next((item for item in records if item.signal_id == record.signal_id), record)


def _render_trade_outcome(record: SignalRecord | None, candidate: CryptoCandidate, live_price: float) -> None:
    """Show live target/stop progress and the persisted outcome state."""
    section_header("🎯 Trade Outcome Tracking")
    if record is None:
        st.info("Outcome tracking starts when this confirmed alert is saved in the journal.")
        return

    if record.status == "TARGET_2":
        st.success(
            f"🎯 TARGET 2 ACHIEVED — {candidate.symbol} · "
            f"exit {record.exit_price:.8g} · +{record.outcome_r:.1f}R"
        )
    elif record.status == "STOP_LOSS":
        st.error(
            f"🛑 STOP LOSS HIT — {candidate.symbol} · "
            f"exit {record.exit_price:.8g} · {record.outcome_r:.1f}R"
        )
    else:
        if record.target_1_achieved:
            st.success(f"🎯 TARGET 1 ACHIEVED — {candidate.target_1:.8g}")
        else:
            st.info(f"🎯 Target 1 pending — {candidate.target_1:.8g}")
        if record.target_2_achieved:
            st.success(f"🏆 TARGET 2 ACHIEVED — {candidate.target_2:.8g}")
        else:
            st.info(f"🏆 Target 2 pending — {candidate.target_2:.8g}")
        st.caption(
            f"Live price {live_price:.8g} · stop {candidate.stop_loss:.8g} · "
            "outcome is checked every 5 seconds."
        )


def _render_live_selected_coin(
    selected_symbol: str,
    locked_candidate: CryptoCandidate,
) -> None:
    """Refresh indicators while keeping the scanned trade plan immutable."""
    try:
        snapshot = scanner.analyze_symbol(selected_symbol, datetime.now(timezone.utc))
    except Exception as error:
        st.error(f"Unable to load live {selected_symbol}: {error}")
        return

    candidate = locked_candidate
    outcome_record = _update_trade_outcome(candidate, snapshot.price)

    section_header(f"📈 {snapshot.symbol} Live Analysis")
    st.caption(
        f"Live snapshot: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')} · "
        "indicators update every 5 seconds · trade plan changes only on a new scan"
    )

    metric_cols = st.columns(7)
    metric_cols[0].metric("Current Price", f"{snapshot.price:.8g}")
    metric_cols[1].metric("EMA 9", f"{snapshot.ema9:.8g}")
    metric_cols[2].metric("EMA 20", f"{snapshot.ema20:.8g}")
    metric_cols[3].metric("RSI", f"{snapshot.rsi:.1f}")
    metric_cols[4].metric("MACD Hist", f"{snapshot.macd_histogram:.6g}")
    metric_cols[5].metric("RVOL", f"{snapshot.relative_volume:.2f}x")
    metric_cols[6].metric("Momentum", f"{snapshot.momentum_5bar_pct:+.2f}%")

    section_header("🧭 Multi-Timeframe Confirmation")
    timeframe_cols = st.columns(4)
    timeframe_cols[0].metric("5m Supertrend", snapshot.trend_5m)
    timeframe_cols[1].metric("15m Supertrend", snapshot.trend_15m)
    timeframe_cols[2].metric("1H Supertrend", snapshot.trend_1h)
    timeframe_cols[3].metric("Momentum", f"{snapshot.momentum_5bar_pct:+.2f}%")

    section_header("🧩 Confluence Breakdown")
    passed = sum(status for _, status in snapshot.confluence)
    total = len(snapshot.confluence)
    confluence_cols = st.columns(3)
    for index, (name, status) in enumerate(snapshot.confluence):
        with confluence_cols[index % 3]:
            st.write(f"{'✅' if status else '❌'} **{name}**")
    st.caption(f"{passed}/{total} live core conditions confirmed · 1H shown separately")

    level_cols = st.columns(2)
    with level_cols[0]:
        section_header("🟢 Support Levels")
        for index, level in enumerate(snapshot.support_levels, 1):
            st.write(f"S{index}: **{level:.8g}**")
        if not snapshot.support_levels:
            st.info("No confirmed support level below current price.")
    with level_cols[1]:
        section_header("🔴 Resistance Levels")
        for index, level in enumerate(snapshot.resistance_levels, 1):
            st.write(f"R{index}: **{level:.8g}**")
        if not snapshot.resistance_levels:
            st.info("No confirmed resistance level above current price.")

    state, state_reason = _live_signal_state(candidate, snapshot)
    section_header("🚨 Active Trading Plan")
    if candidate.direction == "LONG":
        st.success(f"🟢 BUY ALERT — {candidate.symbol} · locked entry {candidate.entry:.8g}")
    else:
        st.error(f"🔴 SELL ALERT — {candidate.symbol} · locked entry {candidate.entry:.8g}")
    st.caption("The alert is the historical scan decision. The state below is live.")

    if state == "CONFIRMED":
        st.success(f"🟢 CURRENT STATE — {state}")
    elif state == "MOMENTUM COOLING":
        st.warning(f"🟡 CURRENT STATE — {state}")
    elif state == "REVERSAL WATCH":
        st.error(f"🔴 CURRENT STATE — {state}")
    else:
        st.info(f"🔵 CURRENT STATE — {state}")
    st.write(state_reason)

    scan_time = st.session_state.get("crypto_scan_timestamp")
    plan_cols = st.columns(7)
    plan_cols[0].metric("Signal", candidate.direction)
    plan_cols[1].metric("Scan Score", f"{candidate.score:.0f}/100")
    plan_cols[2].metric("Live Confirmation", f"{passed}/{total}")
    plan_cols[3].metric("Locked Entry", f"{candidate.entry:.8g}")
    plan_cols[4].metric("Stop Loss", f"{candidate.stop_loss:.8g}")
    plan_cols[5].metric("Target 1", f"{candidate.target_1:.8g}")
    plan_cols[6].metric("Target 2", f"{candidate.target_2:.8g}")
    if scan_time is not None:
        st.caption(
            f"Scan score is locked from {scan_time.strftime('%Y-%m-%d %H:%M:%S UTC')}; "
            "live confirmation is recalculated every 5 seconds."
        )

    _render_trade_outcome(outcome_record, candidate, snapshot.price)

    entry_distance = abs(snapshot.price - candidate.entry) / candidate.entry * 100
    entry_status = (
        "🟢 IDEAL ENTRY ZONE" if entry_distance <= 0.25
        else "🟡 NEAR ENTRY — watch price" if entry_distance <= 0.75
        else "🟠 EXTENDED — avoid chasing"
    )
    st.markdown(
        f"**Current price vs locked entry:** {entry_status} · "
        f"{entry_distance:.2f}% from scan entry"
    )

    risk_cols = st.columns(2)
    with risk_cols[0]:
        section_header("⚠️ Invalidation")
        st.warning(
            f"{candidate.direction} invalid if price closes beyond "
            f"{candidate.stop_loss:.8g}"
        )
    with risk_cols[1]:
        section_header("🔄 Reversal Watch")
        opposite = "SHORT" if candidate.direction == "LONG" else "LONG"
        st.info(
            f"Watch for {opposite} confirmation if the 5m/15m trend flips "
            "and MACD confirms the opposite direction."
        )


section_header("⚡ Scanner")
scan_col, limit_col = st.columns([3, 1])
with scan_col:
    scan_clicked = st.button(
        "🔎 Scan crypto intraday opportunities",
        type="primary",
        use_container_width=True,
    )
with limit_col:
    scan_limit = st.selectbox("Candidates", [5, 10], index=0)

if scan_clicked:
    with st.spinner("Scanning crypto pairs and ranking intraday setups..."):
        scan_time = datetime.now(timezone.utc)
        scanned_candidates = scanner.scan(scan_time, limit=scan_limit)
        st.session_state.crypto_candidates = scanned_candidates
        st.session_state.crypto_scan_timestamp = scan_time
        _record_scan_alerts(scanned_candidates, scan_time)

candidates = st.session_state.get("crypto_candidates", ())
if candidates:
    section_header("🔥 Best Crypto Intraday Opportunities")
    st.dataframe(
        [
            {
                "Rank": index,
                "Coin": item.symbol,
                "Signal": item.direction,
                "Type": "CONFIRMED" if item.score >= 75 else "NEAR SETUP",
                "Score": f"{item.score:.0f}/100",
                "Scan Price": f"{item.price:.8g}",
                "Entry": f"{item.entry:.8g}",
                "Stop": f"{item.stop_loss:.8g}",
                "Target 1": f"{item.target_1:.8g}",
                "Target 2": f"{item.target_2:.8g}",
                "R:R": f"1:{item.risk_reward:.0f}",
                "Why": item.reason,
            }
            for index, item in enumerate(candidates, 1)
        ],
        use_container_width=True,
        hide_index=True,
    )
    candidate_options = [item.symbol for item in candidates]
    selected_symbol = st.selectbox(
        "🎯 Select a Coin to Trade", candidate_options, index=0,
        key="crypto_selected_symbol"
    )
    selected_candidate = next(
        (item for item in candidates if item.symbol == selected_symbol), None
    )
    if selected_candidate is not None:
        st.caption(
            "Live indicators update automatically. Entry, stop and targets remain "
            "locked to the latest scan. Target/stop outcomes are persisted to history."
        )

        @st.fragment(run_every="5s")
        def live_selected_coin() -> None:
            _render_live_selected_coin(selected_symbol, selected_candidate)

        live_selected_coin()
else:
    st.warning("No ranked crypto setup is available yet. Run a scan to populate opportunities.")

section_header("📊 Crypto Accuracy & Outcome Summary")
summary = journal.summary()
summary_cols = st.columns(6)
summary_cols[0].metric("Total Alerts", summary.total)
summary_cols[1].metric("Closed", summary.total - summary.open)
summary_cols[2].metric("Accuracy / Win Rate", f"{summary.win_rate:.1f}%")
summary_cols[3].metric("Target 1 Hit Rate", f"{summary.target_1_rate:.1f}%")
summary_cols[4].metric("Target 2 Hit Rate", f"{summary.target_2_rate:.1f}%")
summary_cols[5].metric("Average R", f"{summary.average_r:+.2f}R")
st.caption(
    f"Wins: {summary.wins} · Losses: {summary.losses} · Open: {summary.open} · "
    f"Profit factor: {summary.profit_factor:.2f} · Max drawdown: {summary.max_drawdown_r:.2f}R"
)

section_header("📒 BUY / SELL Alert History")
records = [record for record in journal.records() if record.market == "CRYPTO"]
if records:
    st.dataframe(
        [
            {
                "Time": record.timestamp,
                "Coin": record.symbol,
                "Alert": "BUY" if record.direction == "LONG" else "SELL",
                "Alert Price": f"{record.entry:.8g}",
                "Stop Loss": f"{record.stop_loss:.8g}",
                "Target 1": f"{record.target_1:.8g}",
                "Target 2": f"{record.target_2:.8g}",
                "T1 Achieved": "✅" if record.target_1_achieved else "—",
                "T2 Achieved": "✅" if record.target_2_achieved else "—",
                "Stop Hit": "🛑" if record.stop_loss_hit else "—",
                "Exit": f"{record.exit_price:.8g}" if record.exit_price is not None else "—",
                "Status": record.status,
                "Outcome": f"{record.outcome_r:+.1f}R" if record.outcome_r is not None else "OPEN",
                "Score": f"{record.score:.0f}/100",
            }
            for record in reversed(records)
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No BUY/SELL alerts have been recorded yet.")

if scanner.last_scan_count:
    with st.expander("🔧 Crypto scan diagnostics"):
        cols = st.columns(3)
        cols[0].metric("Pairs scanned", scanner.last_scan_count)
        cols[1].metric("Qualified", scanner.last_qualified_count)
        cols[2].metric("Data errors", len(scanner.last_scan_errors))
        for symbol, error in list(scanner.last_scan_errors.items())[:20]:
            st.warning(f"{symbol}: {error}")

st.divider()
section_header("📅 Crypto Swing")
st.info(
    "Crypto Swing is the next module. Crypto Intraday remains independent while "
    "its live scanner is validated."
)

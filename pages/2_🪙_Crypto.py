"""Crypto trading page for the Trading Assistant."""

from datetime import datetime, timezone

import streamlit as st

from trading_assistant.data.crypto import BinanceMarketDataProvider
from trading_assistant.monitoring.crypto_scanner import CryptoIntradayScanner
from trading_assistant.monitoring.signal_journal import SignalJournal, SignalRecord

st.set_page_config(page_title="Crypto Trading", page_icon="🪙", layout="wide")
st.title("🪙 Crypto Trading")
st.caption(
    "24/7 crypto market scanner. Market data is public; this V1 page does not place orders."
)

provider = BinanceMarketDataProvider()
scanner = st.session_state.get("crypto_scanner")
if scanner is None:
    scanner = CryptoIntradayScanner(provider)
    st.session_state.crypto_scanner = scanner
journal = SignalJournal()


def _alert_pnl_percent(direction: str, entry: float, price: float) -> float:
    """Return direction-aware paper P/L percentage from alert entry to price."""
    if entry == 0:
        return 0.0
    multiplier = 1.0 if direction == "LONG" else -1.0
    return ((price - entry) / entry) * 100.0 * multiplier


def _record_alert(snapshot) -> None:
    """Record one active BUY/SELL alert without duplicate polling entries."""
    if snapshot.alert not in {"BUY ALERT", "SELL ALERT"} or snapshot.candidate is None:
        return
    candidate = snapshot.candidate
    existing = journal.records()
    already_open = any(
        record.symbol == snapshot.symbol
        and record.direction == candidate.direction
        and record.status == "OPEN"
        for record in existing
    )
    if already_open:
        return
    signal_id = (
        f"crypto-{snapshot.symbol}-{candidate.direction}-"
        f"{snapshot.timestamp.isoformat()}"
    )
    journal.record(
        SignalRecord(
            signal_id=signal_id,
            timestamp=snapshot.timestamp.isoformat(),
            market="CRYPTO",
            symbol=snapshot.symbol,
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


def _update_live_alerts(snapshot) -> None:
    """Mark live target/stop achievements for the selected coin."""
    for record in journal.records():
        if record.symbol != snapshot.symbol or record.status != "OPEN":
            continue
        if record.direction == "LONG":
            target_1_hit = snapshot.price >= record.target_1
            target_2_hit = snapshot.price >= record.target_2
            stop_hit = snapshot.price <= record.stop_loss
        else:
            target_1_hit = snapshot.price <= record.target_1
            target_2_hit = snapshot.price <= record.target_2
            stop_hit = snapshot.price >= record.stop_loss

        sell_price = None
        if target_2_hit:
            sell_price = record.target_2
        elif stop_hit:
            sell_price = record.stop_loss
        elif target_1_hit:
            sell_price = record.target_1

        journal.update_live_state(
            record.signal_id,
            target_1_hit,
            target_2_hit,
            stop_hit,
            sell_price,
        )
        if target_2_hit:
            journal.resolve(
                record.signal_id,
                "TARGET_2_ACHIEVED",
                record.target_2,
                4.0,
                datetime.now(timezone.utc),
            )
        elif stop_hit:
            journal.resolve(
                record.signal_id,
                "STOP_LOSS_HIT",
                record.stop_loss,
                -1.0,
                datetime.now(timezone.utc),
            )


def _render_live_selected_coin(selected_symbol: str) -> None:
    """Refresh selected-coin market data, alerts, and trade outcome state."""
    try:
        with st.spinner(f"Loading live {selected_symbol} market data..."):
            snapshot = scanner.analyze_symbol(
                selected_symbol,
                datetime.now(timezone.utc),
            )
        _record_alert(snapshot)
        _update_live_alerts(snapshot)
    except Exception as error:
        st.error(f"Unable to load live {selected_symbol}: {error}")
        return

    st.markdown(f"### 📈 {snapshot.symbol} Live Analysis")
    st.caption(
        f"Live snapshot: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')} · "
        "updates automatically every 5 seconds"
    )
    metric_cols = st.columns(6)
    metric_cols[0].metric("Current Price", f"{snapshot.price:.8g}")
    metric_cols[1].metric("EMA 9", f"{snapshot.ema9:.8g}")
    metric_cols[2].metric("EMA 20", f"{snapshot.ema20:.8g}")
    metric_cols[3].metric("RSI", f"{snapshot.rsi:.1f}")
    metric_cols[4].metric("MACD Hist", f"{snapshot.macd_histogram:.6g}")
    metric_cols[5].metric("RVOL", f"{snapshot.relative_volume:.2f}x")

    level_cols = st.columns(2)
    with level_cols[0]:
        st.markdown("#### 🟢 Support Levels")
        if snapshot.support_levels:
            for index, level in enumerate(snapshot.support_levels, 1):
                st.write(f"S{index}: **{level:.8g}**")
        else:
            st.info("No confirmed support level below current price.")
    with level_cols[1]:
        st.markdown("#### 🔴 Resistance Levels")
        if snapshot.resistance_levels:
            for index, level in enumerate(snapshot.resistance_levels, 1):
                st.write(f"R{index}: **{level:.8g}**")
        else:
            st.info("No confirmed resistance level above current price.")

    st.markdown("#### 🚨 Live Trading Alert")
    if snapshot.alert == "BUY ALERT":
        st.success(f"🟢 LIVE BUY ALERT — {snapshot.symbol} at {snapshot.price:.8g}")
    elif snapshot.alert == "SELL ALERT":
        st.error(f"🔴 LIVE SELL ALERT — {snapshot.symbol} at {snapshot.price:.8g}")
    else:
        st.warning(f"🟡 LIVE WATCH — {snapshot.symbol}")
    st.write(snapshot.alert_reason)

    if snapshot.candidate is not None:
        plan = snapshot.candidate
        plan_cols = st.columns(5)
        plan_cols[0].metric("Alert Price", f"{plan.entry:.8g}")
        plan_cols[1].metric("Stop Loss", f"{plan.stop_loss:.8g}")
        plan_cols[2].metric("Target 1", f"{plan.target_1:.8g}")
        plan_cols[3].metric("Target 2", f"{plan.target_2:.8g}")
        plan_cols[4].metric("Risk : Reward", f"1:{plan.risk_reward:.0f}")

        current_pnl = _alert_pnl_percent(plan.direction, plan.entry, snapshot.price)
        pnl_label = "Profit" if current_pnl >= 0 else "Loss"
        st.metric(f"Current {pnl_label} from Alert", f"{current_pnl:+.2f}%")

    selected_alerts = [
        record for record in journal.records() if record.symbol == snapshot.symbol
    ]
    if selected_alerts:
        latest = selected_alerts[-1]
        st.markdown("#### 📌 Active Alert Trade Plan")
        alert_cols = st.columns(6)
        alert_cols[0].metric("Alert Price", f"{latest.entry:.8g}")
        alert_cols[1].metric("Stop Loss", f"{latest.stop_loss:.8g}")
        alert_cols[2].metric("Target 1", f"{latest.target_1:.8g}")
        alert_cols[3].metric("Target 2", f"{latest.target_2:.8g}")
        alert_cols[4].metric(
            "Sell Price",
            f"{latest.sell_price:.8g}" if latest.sell_price is not None else "—",
        )
        alert_cols[5].metric("Status", latest.status)
        if latest.target_2_achieved:
            st.success(f"🎯 Target 2 achieved at {latest.target_2:.8g}.")
        elif latest.target_1_achieved:
            st.success(f"🎯 Target 1 achieved at {latest.target_1:.8g}.")
        elif latest.stop_loss_hit:
            st.error(f"🛑 Stop loss hit at {latest.stop_loss:.8g}.")
        else:
            st.info("Alert is OPEN. Sell price and target status update from live prices.")


st.subheader("⚡ Crypto Intraday")
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
    with st.spinner("Scanning crypto pairs and checking 5m/15m confirmation..."):
        st.session_state.crypto_candidates = scanner.scan(
            datetime.now(timezone.utc), limit=scan_limit
        )

candidates = st.session_state.get("crypto_candidates", ())
if candidates:
    st.markdown("### 🔥 Best Crypto Intraday Opportunities")
    rows = [
        {
            "Rank": index,
            "Coin": item.symbol,
            "Signal": item.direction,
            "Score": f"{item.score:.0f}/100",
            "Price": f"{item.price:.8g}",
            "Entry": f"{item.entry:.8g}",
            "Stop": f"{item.stop_loss:.8g}",
            "Target 1": f"{item.target_1:.8g}",
            "Target 2": f"{item.target_2:.8g}",
            "R:R": f"1:{item.risk_reward:.0f}",
            "Why": item.reason,
        }
        for index, item in enumerate(candidates, 1)
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown("### 🎯 Select a Coin to Trade")
    selected_symbol = st.selectbox(
        "Select one of the scanned opportunities",
        [item.symbol for item in candidates],
        key="crypto_selected_symbol",
    )
    st.caption("The selected coin is monitored live; no manual refresh is required.")

    @st.fragment(run_every="5s")
    def live_selected_coin() -> None:
        _render_live_selected_coin(selected_symbol)

    live_selected_coin()
else:
    st.info("Run the crypto scanner to get automatically ranked opportunities.")

st.markdown("### 📒 BUY / SELL Alert History")
alert_records = journal.records()
if alert_records:
    history_rows = []
    for record in reversed(alert_records):
        if record.target_2_achieved:
            outcome = "TARGET 2 ACHIEVED"
        elif record.target_1_achieved:
            outcome = "TARGET 1 ACHIEVED"
        elif record.stop_loss_hit:
            outcome = "STOP LOSS HIT"
        else:
            outcome = "OPEN"
        history_rows.append(
            {
                "Time": record.timestamp,
                "Coin": record.symbol,
                "Alert": "BUY" if record.direction == "LONG" else "SELL",
                "Alert Price": f"{record.entry:.8g}",
                "Stop Loss": f"{record.stop_loss:.8g}",
                "Target 1": f"{record.target_1:.8g}",
                "Target 2": f"{record.target_2:.8g}",
                "Sell Price": (
                    f"{record.sell_price:.8g}" if record.sell_price is not None else "—"
                ),
                "Outcome": outcome,
                "P/L (R)": (
                    f"{record.outcome_r:+.2f}R"
                    if record.outcome_r is not None
                    else "OPEN"
                ),
                "Score": f"{record.score:.0f}/100",
            }
        )
    st.dataframe(history_rows, use_container_width=True, hide_index=True)
else:
    st.info("No BUY/SELL alerts have been recorded yet. Alerts are recorded automatically.")

if scanner.last_scan_count:
    with st.expander("🔧 Crypto scan diagnostics"):
        cols = st.columns(3)
        cols[0].metric("Pairs scanned", scanner.last_scan_count)
        cols[1].metric("Qualified", scanner.last_qualified_count)
        cols[2].metric("Data errors", len(scanner.last_scan_errors))
        if scanner.last_scan_errors:
            for symbol, error in list(scanner.last_scan_errors.items())[:20]:
                st.warning(f"{symbol}: {error}")

st.divider()
st.subheader("📅 Crypto Swing")
st.info(
    "Crypto Swing is the next module. We will add it after the Crypto Intraday data path "
    "has been validated with live market data and signal-performance tracking."
)

st.caption(
    "Live alerts are decision-support signals, not guaranteed trade outcomes. "
    "Validate signals with paper monitoring before real-money use."
)

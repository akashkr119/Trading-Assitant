"""Crypto trading page for the Trading Assistant."""

from datetime import datetime, timezone

import streamlit as st

from trading_assistant.data.crypto import BinanceMarketDataProvider
from trading_assistant.monitoring.crypto_intraday_scanner import (
    RobustCryptoIntradayScanner,
)
from trading_assistant.monitoring.signal_journal import SignalJournal

st.set_page_config(page_title="Crypto Trading", page_icon="🪙", layout="wide")
st.title("🪙 Crypto Trading")
st.caption(
    "24/7 crypto market scanner. Market data is public; this V1 page does not place orders."
)

provider = BinanceMarketDataProvider()
scanner = st.session_state.get("crypto_scanner")
if scanner is None or not isinstance(scanner, RobustCryptoIntradayScanner):
    scanner = RobustCryptoIntradayScanner(provider)
    st.session_state.crypto_scanner = scanner
journal = SignalJournal()


def _render_live_selected_coin(selected_symbol: str) -> None:
    """Refresh selected coin market data and its live alert state."""
    try:
        snapshot = scanner.analyze_symbol(
            selected_symbol,
            datetime.now(timezone.utc),
        )
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
        candidate = snapshot.candidate
        plan_cols = st.columns(6)
        plan_cols[0].metric("Signal", candidate.direction)
        plan_cols[1].metric("Score", f"{candidate.score:.0f}/100")
        plan_cols[2].metric("Entry", f"{candidate.entry:.8g}")
        plan_cols[3].metric("Stop Loss", f"{candidate.stop_loss:.8g}")
        plan_cols[4].metric("Target 1", f"{candidate.target_1:.8g}")
        plan_cols[5].metric("Target 2", f"{candidate.target_2:.8g}")
        st.info(candidate.reason)


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
    with st.spinner("Scanning crypto pairs and ranking intraday setups..."):
        st.session_state.crypto_candidates = scanner.scan(
            datetime.now(timezone.utc),
            limit=scan_limit,
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

    selected_symbol = st.selectbox(
        "🎯 Select a Coin to Trade",
        [item.symbol for item in candidates],
        key="crypto_selected_symbol",
    )
    st.caption("The selected coin is monitored live; no manual refresh is required.")

    @st.fragment(run_every="5s")
    def live_selected_coin() -> None:
        _render_live_selected_coin(selected_symbol)

    live_selected_coin()
else:
    st.warning(
        "No full-confluence setup is available right now. The scanner will rank "
        "near-setups when market conditions are mixed."
    )

st.markdown("### 📒 BUY / SELL Alert History")
records = journal.records()
if records:
    history_rows = []
    for record in reversed(records):
        history_rows.append(
            {
                "Time": record.timestamp,
                "Coin": record.symbol,
                "Alert": "BUY" if record.direction == "LONG" else "SELL",
                "Alert Price": f"{record.entry:.8g}",
                "Stop Loss": f"{record.stop_loss:.8g}",
                "Target 1": f"{record.target_1:.8g}",
                "Target 2": f"{record.target_2:.8g}",
                "Status": record.status,
                "Score": f"{record.score:.0f}/100",
            }
        )
    st.dataframe(history_rows, use_container_width=True, hide_index=True)
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
st.subheader("📅 Crypto Swing")
st.info(
    "Crypto Swing is the next module. Crypto Intraday is kept independent so its "
    "live scanner can be validated first."
)

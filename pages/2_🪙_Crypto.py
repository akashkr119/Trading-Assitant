"""Crypto trading page for the Trading Assistant."""

from datetime import datetime, timezone

import streamlit as st

from trading_assistant.data.crypto import BinanceMarketDataProvider
from trading_assistant.monitoring.crypto_scanner import CryptoIntradayScanner

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
        now = datetime.now(timezone.utc)
        st.session_state.crypto_candidates = scanner.scan(now, limit=scan_limit)

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
else:
    st.info("Run the crypto scanner to get automatically ranked opportunities.")

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
    "Risk/reward shown by the scanner is a planned 1:4 structure, not a guarantee that the "
    "market will reach the target. Validate signals with paper monitoring before real-money use."
)

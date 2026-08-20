"""Long-term investment research dashboard."""

from __future__ import annotations

import streamlit as st

from trading_assistant.analysis.long_term_detail import build_long_term_detail
from trading_assistant.analysis.multibagger_scanner import MultibaggerScanner
from trading_assistant.application.long_term_setup import build_long_term_research

st.set_page_config(page_title="Long-Term Investment", page_icon="🏆", layout="wide")
st.title("🏆 Long-Term Investment")
st.caption("Research and evidence-based ranking for long-term NSE opportunities.")

if "fundamentals_provider" not in st.session_state:
    st.session_state.fundamentals_provider, st.session_state.nse_long_term_universe = (
        build_long_term_research()
    )

provider = st.session_state.fundamentals_provider
universe = list(st.session_state.nse_long_term_universe)
scanner = MultibaggerScanner(provider)

limit = st.selectbox("Number of candidates", [5, 10, 15, 20], index=1)
if st.button("🔎 Find Best Long-Term Stocks", type="primary", use_container_width=True):
    with st.spinner("Examining company fundamentals and ranking opportunities..."):
        st.session_state.long_term_scan = scanner.scan(universe, limit=limit)

scan = st.session_state.get("long_term_scan")
if scan is None:
    st.info("Run the scanner to find long-term candidates.")
    st.stop()

if not scan.candidates:
    st.warning("No candidates passed the fundamental-data coverage threshold.")
    if scan.failures:
        with st.expander("Research diagnostics"):
            for failure in scan.failures:
                st.warning(f"{failure.symbol}: {failure.reason}")
    st.stop()

st.subheader("🏆 Best Long-Term Opportunities")
rows = [
    {
        "Rank": index,
        "Stock": item.symbol.replace(".NS", ""),
        "Company": item.company_name,
        "Score": f"{item.score.overall:.1f}/100",
        "Growth": f"{item.score.growth:.1f}",
        "Profitability": f"{item.score.profitability:.1f}",
        "Financial": f"{item.score.financial_strength:.1f}",
        "Cash Flow": f"{item.score.cash_flow:.1f}",
        "Valuation": f"{item.score.valuation:.1f}",
        "Data Coverage": f"{item.score.coverage:.0f}%",
    }
    for index, item in enumerate(scan.candidates, 1)
]
st.dataframe(rows, use_container_width=True, hide_index=True)

selected = st.selectbox(
    "🎯 Select a stock for complete examination",
    [item.symbol for item in scan.candidates],
    format_func=lambda symbol: symbol.replace(".NS", ""),
    key="long_term_selected",
)

candidate = next(item for item in scan.candidates if item.symbol == selected)
try:
    snapshot = provider.get_fundamentals(selected)
    detail = build_long_term_detail(snapshot, candidate.score)
except Exception as error:
    st.error(f"Unable to build the detailed examination: {error}")
    st.stop()

st.divider()
st.header(f"📊 Complete Investment Examination — {detail.company_name}")
score_cols = st.columns(6)
score_cols[0].metric("Overall", f"{detail.score.overall:.1f}/100")
score_cols[1].metric("Growth", f"{detail.score.growth:.1f}")
score_cols[2].metric("Profitability", f"{detail.score.profitability:.1f}")
score_cols[3].metric("Financial", f"{detail.score.financial_strength:.1f}")
score_cols[4].metric("Cash Flow", f"{detail.score.cash_flow:.1f}")
score_cols[5].metric("Valuation", f"{detail.score.valuation:.1f}")

st.subheader("📈 Growth")
growth_cols = st.columns(3)
growth_cols[0].metric(
    "Revenue CAGR",
    f"{detail.revenue_cagr * 100:.1f}%" if detail.revenue_cagr is not None else "Unavailable",
)
growth_cols[1].metric(
    "Earnings CAGR",
    f"{detail.earnings_cagr * 100:.1f}%" if detail.earnings_cagr is not None else "Unavailable",
)
growth_cols[2].metric(
    "Cash Conversion",
    f"{detail.cash_conversion * 100:.1f}%" if detail.cash_conversion is not None else "Unavailable",
)

st.subheader("🏦 Financial Strength")
st.write(detail.balance_sheet_comment)
st.write(f"ROE: {snapshot.roe:.1f}%" if snapshot.roe is not None else "ROE: Unavailable")
st.write(f"ROCE: {snapshot.roce:.1f}%" if snapshot.roce is not None else "ROCE: Unavailable")
st.write(
    f"Debt / Equity: {snapshot.debt_to_equity:.2f}"
    if snapshot.debt_to_equity is not None
    else "Debt / Equity: Unavailable"
)

st.subheader("💸 Valuation")
st.write(detail.valuation_comment)
valuation_cols = st.columns(4)
valuation_cols[0].metric(
    "P/E", f"{snapshot.pe_ratio:.1f}x" if snapshot.pe_ratio is not None else "Unavailable"
)
valuation_cols[1].metric(
    "P/B", f"{snapshot.pb_ratio:.1f}x" if snapshot.pb_ratio is not None else "Unavailable"
)
valuation_cols[2].metric(
    "EV/EBITDA",
    f"{snapshot.ev_to_ebitda:.1f}x"
    if snapshot.ev_to_ebitda is not None
    else "Unavailable",
)
valuation_cols[3].metric(
    "Market Cap",
    f"₹{snapshot.market_cap:,.0f}"
    if snapshot.market_cap is not None
    else "Unavailable",
)

st.subheader("🟢 Why the Tool Is Suggesting This Stock")
if detail.reasons:
    for reason in detail.reasons:
        st.success(reason)
else:
    st.info("No strong positive evidence was identified by the current scoring rules.")

st.subheader("🔴 Risks")
if detail.risks:
    for risk in detail.risks:
        st.warning(risk)
else:
    st.info("No additional automated risk flag was generated from the available metrics.")

st.subheader("☠️ What Would Break the Multibagger Thesis?")
for item in detail.thesis_killers:
    st.write(f"• {item}")

if scan.failures:
    with st.expander("🔧 Research diagnostics"):
        for failure in scan.failures:
            st.warning(f"{failure.symbol}: {failure.reason}")

st.caption(
    f"Data source: {snapshot.source} · Data as of: {snapshot.as_of.isoformat()} · "
    "This is research support, not a guarantee of future returns."
)

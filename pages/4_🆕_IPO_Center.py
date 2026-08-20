"""IPO discovery and evidence-first research dashboard."""

import streamlit as st

from trading_assistant.ipo import IPOAssessment, assess_ipo

st.set_page_config(page_title="IPO Center", page_icon="🆕", layout="wide")
st.title("🆕 IPO Center")
st.caption(
    "Research support only. IPO decisions are not guarantees of listing gains or long-term returns."
)

ipos = st.session_state.get("open_ipos", [])
if not ipos:
    st.info(
        "No verified open IPO feed is configured yet. Connect an IPO data provider with "
        "official issue documents before displaying live IPOs."
    )
    st.stop()

st.subheader("📅 Open IPOs")
st.dataframe(ipos, use_container_width=True, hide_index=True)
selected = st.selectbox("🎯 Select an IPO for full analysis", [item["Company"] for item in ipos])
record = next(item for item in ipos if item["Company"] == selected)

st.markdown("## 📄 IPO Details")
info = st.columns(4)
info[0].metric("Issue Size", f"₹{record['Issue Size']:.0f} Cr")
info[1].metric("Fresh Issue", f"₹{record['Fresh Issue']:.0f} Cr")
info[2].metric("OFS", f"₹{record['OFS']:.0f} Cr")
info[3].metric("Lot Size", str(record["Lot Size"]))
st.write(
    f"**Price band:** {record['Price Band']} · **Open:** {record['Open']} · "
    f"**Close:** {record['Close']} · **Sector:** {record['Sector']}"
)
st.caption(f"Primary source: {record['Source']}")

assessment: IPOAssessment = assess_ipo(
    revenue_growth=float(record["Revenue Growth"]),
    roe=float(record["ROE"]),
    roce=float(record["ROCE"]),
    debt_to_equity=float(record["Debt / Equity"]),
    valuation_vs_peers=float(record["Valuation vs Peers"]),
    fresh_issue_share=float(record["Fresh Issue Share"]),
)

st.markdown("## 🧮 Investment Assessment")
cols = st.columns(4)
cols[0].metric("Valuation", assessment.valuation)
cols[1].metric("Financial Quality", assessment.financial_quality)
cols[2].metric("Long-Term View", assessment.long_term_view)
cols[3].metric("Listing View", assessment.listing_view)

st.markdown("## 🟢 Why You May Consider It")
for item in assessment.pros:
    st.write(f"• {item}")

st.markdown("## 🔴 Why You May Not Invest")
for item in assessment.cons:
    st.write(f"• {item}")

st.markdown("## ⚠️ Risks")
for item in assessment.risks:
    st.write(f"• {item}")

st.markdown("## 📊 Full Financial Examination")
financial = {
    "Revenue Growth": f"{record['Revenue Growth']:.1f}%",
    "ROE": f"{record['ROE']:.1f}%",
    "ROCE": f"{record['ROCE']:.1f}%",
    "Debt / Equity": f"{record['Debt / Equity']:.2f}",
    "Valuation vs Peers": f"{record['Valuation vs Peers']:+.1f}%",
}
cols = st.columns(len(financial))
for column, (label, value) in zip(cols, financial.items()):
    column.metric(label, value)

st.info(
    "The production version must ingest the RHP/DRHP and company financial statements, "
    "then show the source beside each material conclusion. Missing data is not treated as zero."
)

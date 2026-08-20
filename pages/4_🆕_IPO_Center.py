"""IPO discovery and evidence-first research dashboard."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from trading_assistant.ipo import IPOAssessment, assess_ipo
from trading_assistant.ipo_feed import get_open_ipos

st.set_page_config(page_title="IPO Center", page_icon="🆕", layout="wide")
st.title("🆕 IPO Center")
st.caption(
    "Live IPO discovery with evidence-first analysis. IPO data and market sentiment "
    "can change quickly; verify the RHP and exchange notice before applying."
)

refresh = st.button("🔄 Refresh IPO Feed", type="primary")
if refresh or "open_ipos" not in st.session_state:
    with st.spinner("Loading currently open Indian IPOs..."):
        ipos, source_mode = get_open_ipos()
    st.session_state.open_ipos = ipos
    st.session_state.ipo_source_mode = source_mode

ipos = st.session_state.get("open_ipos", [])
source_mode = st.session_state.get("ipo_source_mode", "unknown")

def _number(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").replace("₹", "").replace("Cr", "")
    try:
        return float(text.strip())
    except ValueError:
        return None


def _money(value: object) -> str:
    number = _number(value)
    return "N/A" if number is None else f"₹{number:,.2f} Cr"


def _assessment(record: dict[str, object]) -> IPOAssessment | None:
    keys = (
        "Revenue Growth",
        "ROE",
        "ROCE",
        "Debt / Equity",
        "Valuation vs Peers",
        "Fresh Issue Share",
    )
    if not all(record.get(key) is not None for key in keys):
        return None
    return assess_ipo(
        revenue_growth=float(record["Revenue Growth"]),
        roe=float(record["ROE"]),
        roce=float(record["ROCE"]),
        debt_to_equity=float(record["Debt / Equity"]),
        valuation_vs_peers=float(record["Valuation vs Peers"]),
        fresh_issue_share=float(record["Fresh Issue Share"]),
    )

if not ipos:
    st.info(
        "There are no IPOs currently shown as open. Use **Refresh IPO Feed** to check again."
    )
    st.stop()

st.success(
    f"{len(ipos)} IPO(s) currently open · feed: {source_mode} · "
    f"checked {date.today().isoformat()}"
)

st.subheader("📅 Open IPOs")
display_rows = []
for item in ipos:
    display_rows.append(
        {
            "Company": item["Company"],
            "Segment": item.get("Segment", "N/A"),
            "Price Band": item.get("Price Band", "N/A"),
            "Issue Size": _money(item.get("Issue Size")),
            "Lot Size": item.get("Lot Size") or "N/A",
            "Open": item["Open"].strftime("%d %b %Y"),
            "Close": item["Close"].strftime("%d %b %Y"),
            "Sector": item.get("Sector", "N/A"),
        }
    )
st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

selected = st.selectbox(
    "🎯 Select an IPO for full analysis",
    [item["Company"] for item in ipos],
)
record = next(item for item in ipos if item["Company"] == selected)

st.markdown("## 📄 IPO Details")
info = st.columns(5)
info[0].metric("Issue Size", _money(record.get("Issue Size")))
info[1].metric("Fresh Issue", _money(record.get("Fresh Issue")))
info[2].metric("OFS", _money(record.get("OFS")))
info[3].metric("Lot Size", str(record.get("Lot Size") or "N/A"))
info[4].metric("Segment", str(record.get("Segment", "N/A")))
st.write(
    f"**Price band:** {record.get('Price Band', 'N/A')} · "
    f"**Open:** {record['Open'].strftime('%d %b %Y')} · "
    f"**Close:** {record['Close'].strftime('%d %b %Y')} · "
    f"**Sector:** {record.get('Sector', 'N/A')}"
)
st.caption(f"Data source: {record.get('Source', 'N/A')}")

assessment = _assessment(record)
if assessment is None:
    st.info(
        "📚 Fundamental IPO scoring is not shown for this issue because verified "
        "Revenue Growth, ROE, ROCE, debt/equity and peer-valuation data are not "
        "connected to the IPO feed. The tool will not invent those values."
    )
else:
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

st.markdown("## 📊 Fundamental Examination")
fundamental_fields = {
    "Revenue Growth": record.get("Revenue Growth"),
    "ROE": record.get("ROE"),
    "ROCE": record.get("ROCE"),
    "Debt / Equity": record.get("Debt / Equity"),
    "Valuation vs Peers": record.get("Valuation vs Peers"),
}
cols = st.columns(len(fundamental_fields))
for column, (label, value) in zip(cols, fundamental_fields.items()):
    column.metric(label, "N/A" if value is None else str(value))

st.markdown("## ⚠️ IPO Risk Checklist")
for item in (
    "Read the latest RHP/DRHP and verify the final price band and issue dates.",
    "Check whether proceeds are primarily fresh capital or an offer for sale.",
    "Review revenue, profit, cash flow, debt and promoter holding from the offer document.",
    "Compare valuation with listed peers rather than relying on grey-market premium alone.",
    "For SME IPOs, consider liquidity, lot size and post-listing volatility carefully.",
):
    st.write(f"• {item}")

st.info(
    "IPO discovery is now connected to a public calendar with a verified fallback snapshot. "
    "Financial conclusions remain evidence-gated: missing prospectus fundamentals are shown "
    "as N/A rather than guessed."
)

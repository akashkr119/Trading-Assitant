"""IPO discovery and evidence-first research dashboard."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from trading_assistant.ipo import IPOAssessment, assess_ipo
from trading_assistant.ipo_feed import get_open_ipos
from trading_assistant.ui.theme import apply_theme

st.set_page_config(page_title="IPO Center", page_icon="🆕", layout="wide")
apply_theme()

st.markdown("# 🆕 IPO Center")
st.caption(
    "Evidence-first IPO research · issue structure · valuation · fundamentals · risk. "
    "Verify the latest RHP/DRHP before applying."
)

refresh = st.button("🔄 Refresh IPO Feed", type="primary", use_container_width=True)
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


def _fresh_share(record: dict[str, object]) -> float | None:
    issue = _number(record.get("Issue Size"))
    fresh = _number(record.get("Fresh Issue"))
    if issue in (None, 0) or fresh is None:
        return None
    return fresh / issue * 100.0


def _days_remaining(record: dict[str, object]) -> int:
    return max(0, (record["Close"] - date.today()).days)


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


def _render_company_intelligence(record: dict[str, object]) -> None:
    """Render a concise company brief for the selected IPO."""
    st.markdown("## 🏢 Company Intelligence")
    st.caption(
        "A point-wise business summary for the selected IPO. "
        "Future plans are based on disclosed IPO/RHP objectives where available."
    )

    brief_fields = (
        ("What the company does", "What They Do"),
        ("Business model", "Business Overview"),
        ("Core goal", "Core Goal"),
        ("Future plans", "Future Plans"),
    )
    overview_cols = st.columns(2)
    for index, (label, key) in enumerate(brief_fields):
        with overview_cols[index % 2]:
            value = record.get(key)
            st.markdown(f"**{label}**")
            if value:
                st.write(f"• {value}")
            else:
                st.info(
                    "Not available in the current feed. Review the latest RHP/DRHP "
                    "before relying on company-specific plans."
                )

    detail_cols = st.columns(3)
    detail_fields = (
        ("🚀 Growth drivers", "Growth Drivers"),
        ("⚠️ Critical risks", "Key Risks"),
        ("💰 IPO money use", "IPO Use of Funds"),
    )
    for column, (label, key) in zip(detail_cols, detail_fields):
        with column:
            st.markdown(f"**{label}**")
            value = record.get(key)
            if value:
                st.write(f"• {value}")
            else:
                st.info("Not available in current feed.")

    source = record.get("Research Source")
    if source:
        st.caption(f"Research basis: {source}. Always cross-check the latest RHP/DRHP.")


if not ipos:
    st.warning("No IPO is currently shown as open.")
    st.info("Click **Refresh IPO Feed** to check the latest calendar again.")
    st.stop()

today = date.today()
ipos = [item for item in ipos if item["Open"] <= today <= item["Close"]]

if not ipos:
    st.warning("The IPO feed returned no issue that is open today.")
    st.stop()

mainboard_count = sum(item.get("Segment") == "Mainboard" for item in ipos)
sme_count = sum(item.get("Segment") == "SME" for item in ipos)
closing_soon = sum(_days_remaining(item) <= 1 for item in ipos)

st.success(
    f"{len(ipos)} IPO(s) open today · {source_mode} · checked {today.isoformat()}"
)

summary = st.columns(4)
summary[0].metric("Open IPOs", len(ipos))
summary[1].metric("Mainboard", mainboard_count)
summary[2].metric("SME", sme_count)
summary[3].metric("Closing ≤ 1 Day", closing_soon)

st.markdown("## 🔎 IPO Opportunity Board")
segment = st.selectbox("Segment", ["All", "Mainboard", "SME"])
filtered = [
    item
    for item in ipos
    if segment == "All" or item.get("Segment") == segment
]

if not filtered:
    st.info(f"No open {segment} IPOs are available in the current feed.")
    st.stop()

rows = []
for item in filtered:
    days = _days_remaining(item)
    share = _fresh_share(item)
    rows.append(
        {
            "Company": item["Company"],
            "Segment": item.get("Segment", "N/A"),
            "Price Band": item.get("Price Band", "N/A"),
            "Issue Size": _money(item.get("Issue Size")),
            "Fresh Capital": _money(item.get("Fresh Issue")),
            "Lot Size": item.get("Lot Size") or "N/A",
            "Open": item["Open"].strftime("%d %b"),
            "Close": item["Close"].strftime("%d %b"),
            "Time Left": "Closes today" if days == 0 else f"{days} day(s)",
            "Fresh Issue %": "N/A" if share is None else f"{share:.0f}%",
        }
    )
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

selected = st.selectbox(
    "🎯 Select an IPO for full analysis",
    [item["Company"] for item in filtered],
)
record = next(item for item in filtered if item["Company"] == selected)

days = _days_remaining(record)
share = _fresh_share(record)
st.markdown(f"## 📄 {record['Company']}")

info = st.columns(6)
info[0].metric("Issue Size", _money(record.get("Issue Size")))
info[1].metric("Fresh Issue", _money(record.get("Fresh Issue")))
info[2].metric("OFS", _money(record.get("OFS")))
info[3].metric("Lot Size", str(record.get("Lot Size") or "N/A"))
info[4].metric("Segment", str(record.get("Segment", "N/A")))
info[5].metric("Closing", "Today" if days == 0 else f"{days} day(s)")

st.write(
    f"**Price band:** {record.get('Price Band', 'N/A')} · "
    f"**Open:** {record['Open'].strftime('%d %b %Y')} · "
    f"**Close:** {record['Close'].strftime('%d %b %Y')} · "
    f"**Sector:** {record.get('Sector', 'N/A')}"
)
if share is not None:
    st.caption(f"Fresh issue represents approximately {share:.1f}% of the stated issue size.")
st.caption(f"Data source: {record.get('Source', 'N/A')}")

_render_company_intelligence(record)

st.markdown("## 🧭 Investor Checklist")
checklist = st.columns(3)
checklist[0].markdown(
    "**Issue structure**\n\n"
    "Review fresh issue versus OFS. Fresh capital funds the company; "
    "OFS proceeds go to selling holders."
)
checklist[1].markdown(
    "**Valuation**\n\n"
    "Compare the IPO valuation with listed peers using RHP financials. "
    "Do not treat GMP as valuation evidence."
)
checklist[2].markdown(
    "**Risk & liquidity**\n\n"
    "Review debt, cash flow, promoter holding, lot size, SME liquidity and "
    "post-listing volatility."
)

assessment = _assessment(record)
st.markdown("## 🧮 Investment Assessment")
if assessment is None:
    st.info(
        "Fundamental scoring is **not available for this issue yet**. Verified "
        "Revenue Growth, ROE, ROCE, debt/equity, peer valuation and fresh-issue-share "
        "inputs are not all present in the IPO feed. Missing data is shown as N/A."
    )
else:
    cols = st.columns(4)
    cols[0].metric("Valuation", assessment.valuation)
    cols[1].metric("Financial Quality", assessment.financial_quality)
    cols[2].metric("Long-Term View", assessment.long_term_view)
    cols[3].metric("Listing View", assessment.listing_view)

    with st.expander("Why this assessment?", expanded=True):
        left, right = st.columns(2)
        with left:
            st.markdown("**Reasons to consider**")
            for item in assessment.pros:
                st.write(f"• {item}")
        with right:
            st.markdown("**Reasons for caution**")
            for item in assessment.cons:
                st.write(f"• {item}")
            for item in assessment.risks:
                st.write(f"⚠️ {item}")

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
    "Check revenue, profit, operating cash flow, debt and promoter holding "
    "from the offer document.",
    "Understand how IPO proceeds will be used and whether the issue is mostly "
    "fresh capital or OFS.",
    "Compare valuation with listed peers using consistent earnings and "
    "book-value measures.",
    "For SME IPOs, pay particular attention to lot size, liquidity and "
    "post-listing volatility.",
):
    st.write(f"• {item}")

st.info(
    "This dashboard is research support, not an application recommendation. IPO data can change; "
    "verify the latest RHP/DRHP and exchange filings before making an investment decision."
)

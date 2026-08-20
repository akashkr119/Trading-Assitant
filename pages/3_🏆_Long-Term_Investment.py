"""Long-term investment and multibagger research dashboard."""

import streamlit as st

from trading_assistant.analysis.long_term import LongTermMetrics, assess_long_term

st.set_page_config(page_title="Long-Term Investment", page_icon="🏆", layout="wide")
st.title("🏆 Long-Term Investment")
st.caption(
    "Evidence-based research support. A multibagger score is a thesis strength score, "
    "not a prediction or guarantee of future returns."
)

watchlist = st.session_state.get("long_term_candidates", [])
if not watchlist:
    st.info(
        "No verified long-term fundamentals are connected yet. Configure a fundamentals "
        "provider before ranking stocks so the scanner never invents financial data."
    )
    st.stop()

st.subheader("🏆 Best Long-Term / Multibagger Candidates")
st.dataframe(watchlist, use_container_width=True, hide_index=True)

symbols = [row["Stock"] for row in watchlist]
selected = st.selectbox("🎯 Select a stock for complete examination", symbols)
record = next(row for row in watchlist if row["Stock"] == selected)

metrics = LongTermMetrics(
    revenue_cagr=float(record["Revenue CAGR"]),
    earnings_cagr=float(record["Earnings CAGR"]),
    roce=float(record["ROCE"]),
    roe=float(record["ROE"]),
    debt_to_equity=float(record["Debt / Equity"]),
    fcf_positive=bool(record["FCF Positive"]),
    cash_conversion=float(record["Cash Conversion"]),
    valuation_percentile=float(record["Valuation Percentile"]),
    moat_score=float(record["Moat"]),
    runway_score=float(record["Runway"]),
    management_score=float(record["Management"]),
    governance_risk=float(record["Governance Risk"]),
)
assessment = assess_long_term(metrics)

st.markdown("## 📊 Complete Investment Examination")
score_cols = st.columns(5)
score_cols[0].metric("Long-Term Score", f"{assessment.score:.1f}/100")
score_cols[1].metric("Business Quality", f"{assessment.business_quality:.1f}")
score_cols[2].metric("Growth Potential", f"{assessment.growth_potential:.1f}")
score_cols[3].metric("Financial Strength", f"{assessment.financial_strength:.1f}")
score_cols[4].metric("Verdict", assessment.verdict)

sections = {
    "🏢 Business & Growth": {
        "Revenue CAGR": f"{metrics.revenue_cagr:.1f}%",
        "Earnings CAGR": f"{metrics.earnings_cagr:.1f}%",
        "Industry Runway": f"{metrics.runway_score:.0f}/100",
    },
    "💰 Profitability": {
        "ROCE": f"{metrics.roce:.1f}%",
        "ROE": f"{metrics.roe:.1f}%",
        "Profitability Score": f"{assessment.profitability:.1f}/100",
    },
    "💵 Cash Flow": {
        "FCF Positive": "Yes" if metrics.fcf_positive else "No",
        "Cash Conversion": f"{metrics.cash_conversion:.0%}",
        "Cash Flow Score": f"{assessment.cash_flow:.1f}/100",
    },
    "🏦 Balance Sheet & Working Capital": {
        "Debt / Equity": f"{metrics.debt_to_equity:.2f}",
        "Financial Strength": f"{assessment.financial_strength:.1f}/100",
        "Working Capital": "Requires provider-level statement data for full trend analysis",
    },
    "🏆 Moat & Competitive Advantage": {
        "Moat Score": f"{metrics.moat_score:.0f}/100",
        "Evidence": "Provider-backed moat evidence is required before a moat claim is made.",
    },
    "👨‍💼 Management & Governance": {
        "Management Score": f"{metrics.management_score:.0f}/100",
        "Governance Risk": f"{metrics.governance_risk:.0f}/100",
        "Risk Score": f"{assessment.risk:.1f}/100",
    },
    "💸 Valuation": {
        "Valuation Percentile": f"{metrics.valuation_percentile:.0f}/100",
        "Valuation Score": f"{assessment.valuation:.1f}/100",
        "Verdict": (
            "Attractive / Fair / Expensive requires verified peer and historical "
            "valuation data."
        ),
    },
}

for title, values in sections.items():
    with st.expander(title, expanded=True):
        cols = st.columns(len(values))
        for column, (label, value) in zip(cols, values.items()):
            column.metric(label, value)

st.markdown("## 🔬 Why the Tool Is Suggesting This Stock")
for reason in assessment.reasons:
    st.write(f"• {reason}")

st.markdown("## ⚠️ Risks / Reasons Not to Invest")
for risk in assessment.risks:
    st.write(f"• {risk}")

st.markdown("## 🔴 Thesis Break Conditions")
for item in assessment.thesis_breaks:
    st.write(f"• {item}")

st.markdown("## 📌 Evidence Policy")
st.info(
    "Every important investment conclusion must be traceable to normalized financial data, "
    "company filings, peer valuation or another configured source. Missing data is shown as "
    "missing rather than guessed."
)

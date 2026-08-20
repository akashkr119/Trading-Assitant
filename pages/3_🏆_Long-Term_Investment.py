"""Long-term investment research dashboard backed by verified fundamentals."""

from __future__ import annotations

from datetime import timezone

import pandas as pd
import streamlit as st

from trading_assistant.data.fundamentals import FundamentalsSnapshot
from trading_assistant.data.nse_universe import DEFAULT_NSE_LONG_TERM_UNIVERSE
from trading_assistant.data.yfinance_fundamentals import YFinanceFundamentalsProvider

st.set_page_config(page_title="Long-Term Investment", page_icon="🏆", layout="wide")
st.title("🏆 Long-Term Investment")
st.caption(
    "Evidence-based NSE long-term research. Scores are thesis-strength indicators, "
    "not predictions or guarantees of returns."
)

provider = YFinanceFundamentalsProvider()


def _cagr(values: list[float | None], periods: int = 3) -> float | None:
    clean = [value for value in values if value is not None and value > 0]
    if len(clean) < 2:
        return None
    years = max(1, min(periods, len(clean) - 1))
    return ((clean[0] / clean[-1]) ** (1 / years) - 1) * 100


def _safe(value: object, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.1f}{suffix}"


def _snapshot_row(snapshot: FundamentalsSnapshot) -> dict[str, object]:
    periods = list(snapshot.periods)
    latest = periods[0] if periods else None
    fcf = latest.free_cash_flow if latest else None
    earnings = latest.earnings if latest else None
    cash_conversion = None
    if fcf is not None and earnings not in (None, 0):
        cash_conversion = fcf / earnings
    return {
        "Stock": snapshot.symbol.removesuffix(".NS"),
        "Company": snapshot.company_name,
        "Revenue CAGR": _cagr([p.revenue for p in periods]),
        "Earnings CAGR": _cagr([p.earnings for p in periods]),
        "ROE": snapshot.roe,
        "Debt / Equity": snapshot.debt_to_equity,
        "FCF Positive": bool(fcf is not None and fcf > 0),
        "Cash Conversion": cash_conversion,
        "Market Cap": snapshot.market_cap,
        "P/E": snapshot.pe_ratio,
        "P/B": snapshot.pb_ratio,
        "EV / EBITDA": snapshot.ev_to_ebitda,
        "Valuation Percentile": None,
        "Periods": len(periods),
        "Snapshot": snapshot,
    }


def _score_rows(rows: list[dict[str, object]]) -> None:
    pe_values = [
        float(row["P/E"])
        for row in rows
        if row["P/E"] not in (None, 0) and float(row["P/E"]) > 0
    ]
    pb_values = [
        float(row["P/B"])
        for row in rows
        if row["P/B"] not in (None, 0) and float(row["P/B"]) > 0
    ]

    def percentile(value: object, values: list[float]) -> float | None:
        if value is None or not values:
            return None
        number = float(value)
        return sum(item <= number for item in values) / len(values) * 100

    for row in rows:
        growth_values = [
            float(value)
            for value in (row["Revenue CAGR"], row["Earnings CAGR"])
            if value is not None
        ]
        growth = 0.0
        if growth_values:
            growth = min(100.0, max(0.0, sum(growth_values) / len(growth_values) * 2.5))

        roe = float(row["ROE"]) if row["ROE"] is not None else 0.0
        profitability = min(100.0, max(0.0, roe * 2.5))
        debt = row["Debt / Equity"]
        financial = (
            50.0
            if debt is None
            else min(100.0, max(0.0, 100 - float(debt) * 35))
        )
        cash = 70.0 if row["FCF Positive"] else 30.0
        pe_pct = percentile(row["P/E"], pe_values)
        pb_pct = percentile(row["P/B"], pb_values)
        valuation = 50.0
        if pe_pct is not None and pb_pct is not None:
            row["Valuation Percentile"] = (pe_pct + pb_pct) / 2
            valuation = 100.0 - float(row["Valuation Percentile"])

        row["Score"] = round(
            growth * 0.30
            + profitability * 0.25
            + financial * 0.20
            + cash * 0.15
            + valuation * 0.10,
            1,
        )


st.subheader("🔎 Fundamental Stock Scanner")
scan_col, count_col = st.columns([3, 1])
with scan_col:
    scan_clicked = st.button(
        "🔎 Scan NSE Long-Term Opportunities",
        type="primary",
        use_container_width=True,
    )
with count_col:
    scan_count = st.selectbox("Stocks", [5, 10], index=1)

if scan_clicked:
    rows: list[dict[str, object]] = []
    errors: dict[str, str] = {}
    with st.spinner("Fetching verified financial statements and valuation data..."):
        for symbol in DEFAULT_NSE_LONG_TERM_UNIVERSE[:scan_count]:
            try:
                snapshot = provider.get_fundamentals(symbol)
                if not snapshot.has_required_financial_history(3):
                    errors[symbol] = "Fewer than 3 complete revenue/earnings periods"
                    continue
                rows.append(_snapshot_row(snapshot))
            except Exception as error:
                errors[symbol] = str(error)
    _score_rows(rows)
    rows.sort(key=lambda row: float(row["Score"]), reverse=True)
    st.session_state.long_term_candidates = rows
    st.session_state.long_term_errors = errors

watchlist = st.session_state.get("long_term_candidates", [])
errors = st.session_state.get("long_term_errors", {})

if not watchlist:
    st.info(
        "No scan has been run yet. Click **Scan NSE Long-Term Opportunities** to fetch "
        "verified financial statements from Yahoo Finance via yfinance."
    )
    if errors:
        with st.expander("🔧 Data diagnostics"):
            for symbol, error in errors.items():
                st.warning(f"{symbol}: {error}")
    st.stop()

st.success(
    f"Verified fundamentals loaded for {len(watchlist)} stocks · "
    "data source: Yahoo Finance via yfinance"
)

st.subheader("🏆 Best Long-Term / Multibagger Candidates")
display_rows = []
for index, row in enumerate(watchlist, 1):
    display_rows.append(
        {
            "Rank": index,
            "Stock": row["Stock"],
            "Company": row["Company"],
            "Score": f"{row['Score']:.1f}/100",
            "Revenue CAGR": _safe(row["Revenue CAGR"], "%"),
            "Earnings CAGR": _safe(row["Earnings CAGR"], "%"),
            "ROE": _safe(row["ROE"], "%"),
            "Debt / Equity": _safe(row["Debt / Equity"]),
            "P/E": _safe(row["P/E"]),
            "P/B": _safe(row["P/B"]),
            "FCF": "Positive" if row["FCF Positive"] else "Negative",
        }
    )
st.dataframe(display_rows, use_container_width=True, hide_index=True)

symbols = [row["Stock"] for row in watchlist]
selected = st.selectbox("🎯 Select a stock for complete examination", symbols)
record = next(row for row in watchlist if row["Stock"] == selected)
snapshot = record["Snapshot"]
periods = list(snapshot.periods)

st.caption(
    f"Verified source: {snapshot.source} · snapshot time: "
    f"{snapshot.as_of.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
    f"financial periods available: {len(periods)}"
)

st.markdown("## 📊 Complete Investment Examination")
score_cols = st.columns(5)
score_cols[0].metric("Long-Term Score", f"{record['Score']:.1f}/100")
score_cols[1].metric("Revenue CAGR", _safe(record["Revenue CAGR"], "%"))
score_cols[2].metric("Earnings CAGR", _safe(record["Earnings CAGR"], "%"))
score_cols[3].metric("ROE", _safe(record["ROE"], "%"))
score_cols[4].metric("P/E", _safe(record["P/E"]))

sections = {
    "🏢 Business & Growth": {
        "Revenue CAGR": _safe(record["Revenue CAGR"], "%"),
        "Earnings CAGR": _safe(record["Earnings CAGR"], "%"),
        "Reported periods": str(record["Periods"]),
    },
    "💰 Profitability": {
        "ROE": _safe(record["ROE"], "%"),
        "Latest earnings": _safe(periods[0].earnings if periods else None),
        "Evidence": "ROE from provider; ROCE requires EBIT/capital-employed normalization",
    },
    "💵 Cash Flow": {
        "FCF Positive": "Yes" if record["FCF Positive"] else "No",
        "Cash Conversion": _safe(record["Cash Conversion"], "x"),
        "Latest FCF": _safe(periods[0].free_cash_flow if periods else None),
    },
    "🏦 Balance Sheet": {
        "Debt / Equity": _safe(record["Debt / Equity"]),
        "Market Cap": _safe(record["Market Cap"]),
        "Evidence": "Provider-backed reported debt/equity",
    },
    "💸 Valuation": {
        "P/E": _safe(record["P/E"]),
        "P/B": _safe(record["P/B"]),
        "EV / EBITDA": _safe(record["EV / EBITDA"]),
        "Peer percentile": _safe(record["Valuation Percentile"]),
    },
    "🏆 Moat / Management / Governance": {
        "Status": "Not scored without verified provider evidence",
        "Moat": "N/A",
        "Management": "N/A",
        "Governance": "N/A",
    },
}

for title, values in sections.items():
    with st.expander(title, expanded=True):
        cols = st.columns(len(values))
        for column, (label, value) in zip(cols, values.items()):
            column.metric(label, value)

st.markdown("## 🔬 Why the Tool Is Suggesting This Stock")
reasons = [
    f"Revenue CAGR: {_safe(record['Revenue CAGR'], '%')}; "
    f"earnings CAGR: {_safe(record['Earnings CAGR'], '%')}.",
    f"ROE: {_safe(record['ROE'], '%')}; "
    f"debt/equity: {_safe(record['Debt / Equity'])}.",
    "Free cash flow is positive in the latest reported period."
    if record["FCF Positive"]
    else "Latest reported free cash flow is not positive.",
    f"Peer valuation: P/E {_safe(record['P/E'])}, "
    f"P/B {_safe(record['P/B'])}.",
]
for reason in reasons:
    st.write(f"• {reason}")

st.markdown("## ⚠️ Risks / Reasons Not to Invest")
risks = []
if record["Debt / Equity"] is not None and float(record["Debt / Equity"]) > 1.0:
    risks.append("Debt/equity is above 1.0 and deserves closer balance-sheet review.")
if not record["FCF Positive"]:
    risks.append("Latest reported free cash flow is not positive.")
if record["P/E"] is not None and float(record["P/E"]) > 40:
    risks.append("P/E is elevated relative to the scanned peer universe.")
if not risks:
    risks.append(
        "No automatic red flag was triggered; deeper qualitative review is still required."
    )
for risk in risks:
    st.write(f"• {risk}")

st.markdown("## 🔴 Thesis Break Conditions")
for item in (
    "Revenue or earnings growth deteriorates materially for sustained periods.",
    "ROE falls materially without a clear reinvestment explanation.",
    "Debt rises faster than productive earnings capacity.",
    "Cash generation persistently diverges from reported profit.",
    "Material governance, regulatory or competitive concerns emerge.",
):
    st.write(f"• {item}")

if errors:
    with st.expander("🔧 Stocks skipped during scan"):
        for symbol, error in errors.items():
            st.warning(f"{symbol}: {error}")

st.markdown("## 📌 Evidence Policy")
st.info(
    "Financial metrics come from the configured provider. Missing metrics are shown as "
    "N/A rather than guessed. Moat, management and governance are not scored until "
    "verified evidence is connected."
)

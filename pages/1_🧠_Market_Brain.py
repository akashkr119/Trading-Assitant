"""V2 Market Brain dashboard.

This page is intentionally data-provider agnostic in the first slice. It uses
transparent observations and does not alter V1 scanner behavior.
"""

from __future__ import annotations

import streamlit as st

from trading_assistant.ui.theme import apply_theme, page_header, section_header
from trading_assistant.v2.market_regime import (
    MarketObservation,
    MarketRegime,
    classify_market_regime,
)

st.set_page_config(page_title="Market Brain", page_icon="🧠", layout="wide")
apply_theme()
page_header(
    "🧠 Market Brain",
    "V2 market regime intelligence · context before stock selection",
    accent="cyan",
)
st.caption(
    "V2 preview: transparent market-regime analysis. Live market data will be "
    "connected in the next V2 slice."
)

section_header("🌐 Market Regime")

input_cols = st.columns(2)
with input_cols[0]:
    index_trend = st.slider(
        "Index trend",
        -1.0,
        1.0,
        0.0,
        0.1,
        help="Normalized trend: -1 bearish, 0 neutral, +1 bullish.",
    )
    breadth = st.slider(
        "Advance breadth (%)",
        0.0,
        100.0,
        50.0,
        1.0,
        help="Percentage of observed stocks advancing.",
    )
    volatility = st.slider(
        "Volatility percentile",
        0.0,
        100.0,
        50.0,
        1.0,
        help="Normalized volatility percentile. 85+ is treated as high volatility.",
    )
with input_cols[1]:
    volume = st.slider("Volume strength", -1.0, 1.0, 0.0, 0.1)
    sector = st.slider("Sector strength", -1.0, 1.0, 0.0, 0.1)
    st.caption(
        "These are temporary normalized inputs. The next V2 slice will replace "
        "them with live NSE observations."
    )

result = classify_market_regime(
    MarketObservation(
        index_trend=index_trend,
        breadth_pct=breadth,
        volatility_percentile=volatility,
        volume_strength=volume,
        sector_strength=sector,
    )
)

metric_cols = st.columns(3)
metric_cols[0].metric("Regime", result.regime.value.replace("_", " "))
metric_cols[1].metric("Regime Score", f"{result.score:+.2f}")
metric_cols[2].metric("Confidence", f"{result.confidence:.0f}%")

if result.regime == MarketRegime.BULLISH:
    st.success(
        "🟢 Market context is bullish. Prefer confirmed long setups over weak signals."
    )
elif result.regime == MarketRegime.BEARISH:
    st.error(
        "🔴 Market context is bearish. Be selective with longs and prioritize risk control."
    )
elif result.regime == MarketRegime.HIGH_VOLATILITY:
    st.warning(
        "⚠️ High-volatility regime. Reduce conviction and demand stronger confirmation."
    )
else:
    st.info(
        "🟡 Market context is neutral. Avoid forcing trades while directional evidence conflicts."
    )

section_header("🔎 Why the Market Brain Reached This View")
for reason in result.reasons:
    st.write(f"• {reason}")

section_header("📊 Market Context Inputs")
context = [
    {
        "Signal": "Index trend",
        "Value": f"{index_trend:+.1f}",
        "Interpretation": "Bullish"
        if index_trend > 0.2
        else "Bearish"
        if index_trend < -0.2
        else "Neutral",
    },
    {
        "Signal": "Breadth",
        "Value": f"{breadth:.0f}%",
        "Interpretation": "Advancing"
        if breadth > 60
        else "Declining"
        if breadth < 40
        else "Balanced",
    },
    {
        "Signal": "Volatility",
        "Value": f"{volatility:.0f}th percentile",
        "Interpretation": "High risk" if volatility >= 85 else "Normal",
    },
    {
        "Signal": "Volume strength",
        "Value": f"{volume:+.1f}",
        "Interpretation": "Strong"
        if volume > 0.2
        else "Weak"
        if volume < -0.2
        else "Normal",
    },
    {
        "Signal": "Sector strength",
        "Value": f"{sector:+.1f}",
        "Interpretation": "Supportive"
        if sector > 0.2
        else "Weak"
        if sector < -0.2
        else "Mixed",
    },
]
st.dataframe(context, use_container_width=True, hide_index=True)

section_header("🎯 V2 Decision Guidance")
guidance = {
    MarketRegime.BULLISH: (
        "Focus the NSE Intraday scanner on confirmed LONG setups. "
        "Do not treat the regime as a standalone entry signal."
    ),
    MarketRegime.BEARISH: (
        "Prioritize risk control and confirmed SHORT setups. "
        "Long signals should require stronger-than-normal confirmation."
    ),
    MarketRegime.HIGH_VOLATILITY: (
        "Demand stronger confirmation, smaller risk and wider awareness of "
        "rapid invalidation. Do not interpret volatility itself as direction."
    ),
    MarketRegime.NEUTRAL: (
        "Prefer WAIT when timeframes conflict. Let stock-level evidence prove "
        "direction before taking a setup."
    ),
}
st.info(guidance[result.regime])

st.divider()
st.caption(
    "V2 Market Brain currently uses manually supplied normalized inputs for "
    "validation. No live market decision is generated from this preview."
)

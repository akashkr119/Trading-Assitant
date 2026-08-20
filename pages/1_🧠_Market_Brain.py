"""V2 Market Brain dashboard.

Phase one combines market regime, sector rotation, conservative trade-state
logic and a setup lifecycle preview. Inputs remain provider-agnostic until the
live NSE adapter is introduced.
"""

from __future__ import annotations

import streamlit as st

from trading_assistant.ui.theme import apply_theme, page_header, section_header
from trading_assistant.v2.market_regime import (
    MarketObservation,
    MarketRegime,
    classify_market_regime,
)
from trading_assistant.v2.sector_rotation import SectorObservation, rank_sectors
from trading_assistant.v2.setup_lifecycle import (
    SetupLifecycle,
    SetupStage,
    advance_setup,
)
from trading_assistant.v2.wait_no_trade import TradeContext, decide_trade

st.set_page_config(page_title="Market Brain", page_icon="🧠", layout="wide")
apply_theme()
page_header(
    "🧠 Market Brain",
    "V2 phase one · market context before stock selection",
    accent="cyan",
)
st.caption(
    "Transparent decision support. Phase one validates the intelligence layer "
    "before live NSE observations are connected."
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
        help="85+ is treated as a high-volatility regime.",
    )
with input_cols[1]:
    volume = st.slider("Volume strength", -1.0, 1.0, 0.0, 0.1)
    sector = st.slider("Sector strength", -1.0, 1.0, 0.0, 0.1)
    st.caption(
        "Temporary normalized inputs. Live NSE observations are a later adapter."
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
        "🔴 Market context is bearish. Prioritize risk control and confirmation."
    )
elif result.regime == MarketRegime.HIGH_VOLATILITY:
    st.warning(
        "⚠️ High volatility. Demand stronger confirmation and reduce conviction."
    )
else:
    st.info("🟡 Neutral market. Do not force a directional trade.")

section_header("🔎 Why the Market Brain Reached This View")
for reason in result.reasons:
    st.write(f"• {reason}")

section_header("📊 Market Context")
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

st.divider()

section_header("🏭 Sector Rotation")
st.caption("Sector ranking combines relative strength, trend, volume and breadth.")
sector_names = ["Banking", "IT", "Auto", "Pharma", "Energy", "FMCG"]
sector_rows: list[SectorObservation] = []
sector_input_cols = st.columns(3)
for index, name in enumerate(sector_names):
    with sector_input_cols[index % 3]:
        strength = st.slider(
            f"{name} relative strength",
            -1.0,
            1.0,
            0.0,
            0.1,
            key=f"sector_rs_{name}",
        )
        trend = st.slider(
            f"{name} trend",
            -1.0,
            1.0,
            0.0,
            0.1,
            key=f"sector_trend_{name}",
        )
        sector_rows.append(
            SectorObservation(
                name=name,
                relative_strength=strength,
                trend=trend,
                volume_strength=volume,
                breadth_pct=breadth,
            )
        )

sector_scores = rank_sectors(sector_rows)
st.dataframe(
    [
        {
            "Rank": item.rank,
            "Sector": item.name,
            "Score": f"{item.score:+.2f}",
            "State": item.interpretation,
        }
        for item in sector_scores
    ],
    use_container_width=True,
    hide_index=True,
)

leader = sector_scores[0] if sector_scores else None
if leader:
    st.success(
        f"🏆 Current sector leader: {leader.name} · "
        f"{leader.score:+.2f} · {leader.interpretation}"
    )

st.divider()

section_header("🚦 WAIT / NO-TRADE Engine")
trade_cols = st.columns(2)
with trade_cols[0]:
    direction = st.radio("Candidate direction", ["BUY", "SELL"], horizontal=True)
    setup_score = st.slider("Setup score", 0, 100, 70, 1)
    risk_reward = st.number_input("Risk / Reward", min_value=0.0, value=2.0, step=0.1)
with trade_cols[1]:
    aligned = st.checkbox("Timeframes aligned", value=True)
    high_volatility = st.checkbox(
        "High-volatility conditions",
        value=result.regime == MarketRegime.HIGH_VOLATILITY,
    )

trade_decision = decide_trade(
    TradeContext(
        market_score=result.score,
        setup_score=float(setup_score),
        risk_reward=risk_reward,
        timeframe_aligned=aligned,
        high_volatility=high_volatility,
    ),
    direction,
)

trade_metric_cols = st.columns(3)
trade_metric_cols[0].metric("Decision", trade_decision.state.value)
trade_metric_cols[1].metric("Setup Score", f"{trade_decision.score:.0f}/100")
trade_metric_cols[2].metric("R:R", f"1:{risk_reward:.1f}")

if trade_decision.state.value == "BUY":
    st.success("🟢 BUY — all required context checks agree.")
elif trade_decision.state.value == "SELL":
    st.error("🔴 SELL — all required context checks agree.")
elif trade_decision.state.value == "WAIT":
    st.warning("🟡 WAIT — the setup needs stronger confirmation.")
else:
    st.error("⚪ NO TRADE — risk or market conditions do not qualify.")
for reason in trade_decision.reasons:
    st.write(f"• {reason}")

st.divider()

section_header("🎯 Setup Lifecycle")
st.caption("Opportunities progress through explicit states instead of jumping directly to a trade.")

initial_stage = st.selectbox("Current setup stage", list(SetupStage), index=0)
next_options = {
    SetupStage.WATCH: [SetupStage.FORMING, SetupStage.EXIT],
    SetupStage.FORMING: [SetupStage.NEAR_TRIGGER, SetupStage.EXIT],
    SetupStage.NEAR_TRIGGER: [SetupStage.CONFIRMED, SetupStage.EXIT],
    SetupStage.CONFIRMED: [SetupStage.ACTIVE, SetupStage.EXIT],
    SetupStage.ACTIVE: [SetupStage.TARGET, SetupStage.EXIT],
    SetupStage.TARGET: [SetupStage.ACTIVE, SetupStage.EXIT],
    SetupStage.EXIT: [],
}
setup = SetupLifecycle(
    symbol="NSE-CANDIDATE",
    direction=direction,
    stage=initial_stage,
    score=float(setup_score),
    invalidation="Break of the setup invalidation level",
)
if next_options[initial_stage]:
    next_stage = st.selectbox("Next valid stage", next_options[initial_stage])
    if st.button("Advance setup", type="primary"):
        setup = advance_setup(setup, next_stage)

lifecycle = list(SetupStage)
active_index = lifecycle.index(setup.stage)
st.progress((active_index + 1) / len(lifecycle))
st.caption(" → ".join(stage.value for stage in lifecycle))
life_cols = st.columns(4)
life_cols[0].metric("Symbol", setup.symbol)
life_cols[1].metric("Stage", setup.stage.value)
life_cols[2].metric("Direction", setup.direction)
life_cols[3].metric("Score", f"{setup.score:.0f}/100")

st.divider()
st.info(
    "V2 Phase 1 is provider-agnostic. The intelligence engines are now isolated "
    "and testable; the next phase can feed them verified live NSE observations."
)

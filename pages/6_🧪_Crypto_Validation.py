"""Crypto engine validation dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from trading_assistant.ui.theme import (
    apply_theme,
    page_header,
    section_header,
)


JOURNAL_PATH = Path("reports/crypto_validation_journal.csv")

st.set_page_config(
    page_title="Crypto Validation",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


def _load_data() -> pd.DataFrame:
    if not JOURNAL_PATH.exists():
        return pd.DataFrame()
    try:
        frame = pd.read_csv(JOURNAL_PATH)
    except (OSError, pd.errors.EmptyDataError):
        return pd.DataFrame()
    if frame.empty:
        return frame
    for column in [
        "score",
        "entry",
        "stop_loss",
        "target_1",
        "target_2",
        "risk_reward",
        "exit_price",
        "outcome_r",
    ]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in [
        "target_1_achieved",
        "target_2_achieved",
        "stop_loss_hit",
    ]:
        if column in frame:
            frame[column] = frame[column].fillna(False).astype(str).str.lower().eq("true")
    frame["timestamp"] = pd.to_datetime(frame.get("timestamp"), errors="coerce", utc=True)
    return frame.sort_values("timestamp", ascending=False).reset_index(drop=True)


def _status_label(row: pd.Series) -> str:
    status = str(row.get("status", "OPEN"))
    if status == "TARGET_2":
        return "🏆 T2 ACHIEVED"
    if status == "TARGET_1":
        return "🎯 T1 ACHIEVED"
    if status == "STOP_LOSS":
        return "🛑 STOP LOSS"
    if status == "INVALIDATED":
        return "⚠️ INVALIDATED"
    if bool(row.get("target_2_achieved", False)):
        return "🏆 T2 ACHIEVED"
    if bool(row.get("target_1_achieved", False)):
        return "🎯 T1 ACHIEVED"
    return "🟡 OPEN"


def _prepare_table(frame: pd.DataFrame) -> pd.DataFrame:
    table = frame.copy()
    table["Time"] = table["timestamp"].dt.strftime("%d %b %H:%M")
    table["Side"] = table["direction"].map(
        {"LONG": "🟢 BUY", "SHORT": "🔴 SELL"}
    ).fillna(table["direction"])
    table["Status"] = table.apply(_status_label, axis=1)
    table["Entry"] = table["entry"].map(lambda value: f"{value:.8g}")
    table["SL"] = table["stop_loss"].map(lambda value: f"{value:.8g}")
    table["T1"] = table["target_1"].map(lambda value: f"{value:.8g}")
    table["T2"] = table["target_2"].map(lambda value: f"{value:.8g}")
    table["Score"] = table["score"].map(lambda value: f"{value:.0f}")
    table["R:R"] = table["risk_reward"].map(lambda value: f"{value:.2f}R")
    table["Exit"] = table["exit_price"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.8g}"
    )
    table["Outcome"] = table["outcome_r"].map(
        lambda value: "OPEN" if pd.isna(value) else f"{value:+.2f}R"
    )
    table["T1 Hit"] = table["target_1_achieved"].map(lambda value: "✅" if value else "—")
    table["T2 Hit"] = table["target_2_achieved"].map(lambda value: "✅" if value else "—")
    table["SL Hit"] = table["stop_loss_hit"].map(lambda value: "🛑" if value else "—")
    return table[
        [
            "Time",
            "symbol",
            "Side",
            "Score",
            "Entry",
            "SL",
            "T1",
            "T2",
            "R:R",
            "T1 Hit",
            "T2 Hit",
            "SL Hit",
            "Status",
            "Exit",
            "Outcome",
        ]
    ].rename(columns={"symbol": "Coin"})


page_header(
    "🧪 Crypto Validation Lab",
    "Independent performance dashboard for the automated Crypto engine validation runner.",
    accent="purple",
)

left, right = st.columns([4, 1])
with left:
    st.caption(
        "This page reads the persisted validation journal. "
        "It does not control the live Crypto dashboard."
    )
with right:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

frame = _load_data()

if frame.empty:
    st.info(
        "No validation trades have been recorded yet. Once the scheduled runner generates signals, "
        "they will appear here automatically."
    )
    st.stop()

closed = frame[frame["outcome_r"].notna()]
wins = closed[closed["outcome_r"] > 0]
losses = closed[closed["outcome_r"] < 0]
t1_count = int(frame["target_1_achieved"].sum())
t2_count = int(frame["target_2_achieved"].sum())
sl_count = int(frame["stop_loss_hit"].sum())
total_r = float(closed["outcome_r"].sum()) if not closed.empty else 0.0
average_r = float(closed["outcome_r"].mean()) if not closed.empty else 0.0
win_rate = len(wins) / len(closed) * 100 if not closed.empty else 0.0
t1_rate = t1_count / len(frame) * 100
t2_rate = t2_count / len(frame) * 100

section_header("📊 Engine Performance")
metrics = st.columns(7)
metrics[0].metric("Alerts", len(frame))
metrics[1].metric("Closed", len(closed))
metrics[2].metric("Open", len(frame) - len(closed))
metrics[3].metric("Win Rate", f"{win_rate:.1f}%")
metrics[4].metric("T1 Hit Rate", f"{t1_rate:.1f}%")
metrics[5].metric("T2 Hit Rate", f"{t2_rate:.1f}%")
metrics[6].metric("Total R", f"{total_r:+.2f}R")

secondary = st.columns(4)
secondary[0].metric("T1 Achieved", t1_count)
secondary[1].metric("T2 Achieved", t2_count)
secondary[2].metric("Stop Loss", sl_count)
secondary[3].metric("Average R", f"{average_r:+.2f}R")

section_header("📈 Accuracy Snapshot")
summary_cols = st.columns([1, 1, 2])
with summary_cols[0]:
    st.metric("Winning Trades", len(wins))
with summary_cols[1]:
    st.metric("Losing Trades", len(losses))
with summary_cols[2]:
    if not closed.empty:
        st.progress(
            min(max(win_rate / 100, 0.0), 1.0),
            text=f"Closed-trade win rate: {win_rate:.1f}%",
        )
        st.caption(
            f"Total realized performance: {total_r:+.2f}R · "
            f"Average closed trade: {average_r:+.2f}R"
        )
    else:
        st.caption("Waiting for the first closed validation trade.")

section_header("🔎 Filters")
filter_cols = st.columns([2, 1, 1, 1])
with filter_cols[0]:
    coins = ["All"] + sorted(frame["symbol"].dropna().unique().tolist())
    selected_coin = st.selectbox("Coin", coins)
with filter_cols[1]:
    selected_side = st.selectbox("Side", ["All", "LONG", "SHORT"])
with filter_cols[2]:
    selected_status = st.selectbox(
        "Status",
        ["All", "OPEN", "TARGET_1", "TARGET_2", "STOP_LOSS", "INVALIDATED"],
    )
with filter_cols[3]:
    min_score = st.number_input("Min score", min_value=0, max_value=100, value=0, step=5)

filtered = frame.copy()
if selected_coin != "All":
    filtered = filtered[filtered["symbol"] == selected_coin]
if selected_side != "All":
    filtered = filtered[filtered["direction"] == selected_side]
if selected_status != "All":
    filtered = filtered[filtered["status"] == selected_status]
filtered = filtered[filtered["score"] >= min_score]

section_header(f"📋 Signal History · {len(filtered)} records")
if filtered.empty:
    st.warning("No validation records match the selected filters.")
else:
    st.dataframe(
        _prepare_table(filtered),
        use_container_width=True,
        hide_index=True,
        height=min(620, 120 + len(filtered) * 35),
    )

section_header("🧭 Validation Notes")
notes = st.columns(3)
notes[0].info("🎯 T1/T2 are counted from the persisted target-achievement flags.")
notes[1].warning("🛑 A stop-loss outcome is counted as a losing closed trade.")
notes[2].success("🧪 Results come from the same engine used by the live Crypto scanner.")

csv_data = frame.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download Validation CSV",
    data=csv_data,
    file_name="crypto_validation_journal.csv",
    mime="text/csv",
)

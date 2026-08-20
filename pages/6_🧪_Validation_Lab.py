"""V2 Validation Lab for backtesting, paper trading and journal analytics."""

from __future__ import annotations

import streamlit as st

from trading_assistant.ui.theme import apply_theme, page_header, section_header
from trading_assistant.v2.backtesting import BacktestTrade, run_backtest
from trading_assistant.v2.paper_trading import PaperPortfolio, PaperPosition
from trading_assistant.v2.trade_journal import JournalEntry, summarize_journal

st.set_page_config(page_title="Validation Lab", page_icon="🧪", layout="wide")
apply_theme()
page_header(
    "🧪 Validation Lab",
    "V2 backtesting · paper trading · trade journal",
    accent="cyan",
)
st.caption(
    "Validation only. This page does not place broker orders and does not claim "
    "future performance."
)

section_header("📊 Backtesting Lab")
trade_count = st.slider("Sample trades", 2, 50, 10)
win_rate = st.slider("Sample win rate (%)", 0, 100, 60)
avg_win = st.slider("Average winning trade (R)", 0.5, 5.0, 2.0, 0.1)
avg_loss = st.slider("Average losing trade (R)", -5.0, -0.1, -1.0, 0.1)

wins = round(trade_count * win_rate / 100)
losses = trade_count - wins
trades = [
    BacktestTrade(
        symbol=f"TEST{i + 1}",
        direction="BUY",
        entry=100,
        exit_price=100 + avg_win * 5,
        stop_loss=95,
        target=100 + avg_win * 5,
    )
    for i in range(wins)
]
trades.extend(
    BacktestTrade(
        symbol=f"LOSS{i + 1}",
        direction="BUY",
        entry=100,
        exit_price=100 + avg_loss * 5,
        stop_loss=95,
        target=110,
    )
    for i in range(losses)
)
result = run_backtest(trades)
metrics = st.columns(6)
metrics[0].metric("Trades", result.total_trades)
metrics[1].metric("Win Rate", f"{result.win_rate:.1f}%")
metrics[2].metric("Expectancy", f"{result.expectancy_r:+.2f}R")
metrics[3].metric("Profit Factor", "N/A" if result.profit_factor is None else f"{result.profit_factor:.2f}")
metrics[4].metric("Total Return", f"{result.total_r:+.2f}R")
metrics[5].metric("Max Drawdown", f"-{result.max_drawdown_r:.2f}R")

if result.expectancy_r > 0:
    st.success("🟢 Positive sample expectancy. Validate with out-of-sample data before relying on it.")
else:
    st.warning("🟡 Non-positive sample expectancy. Do not promote this configuration without further testing.")

section_header("🧪 Paper Trading")
capital = st.number_input("Virtual starting capital", min_value=10_000.0, value=1_000_000.0, step=10_000.0)
quantity = st.number_input("Example quantity", min_value=1, value=100, step=1)
entry = st.number_input("Example entry", min_value=0.01, value=100.0, step=1.0)
mark = st.number_input("Current mark", min_value=0.01, value=105.0, step=1.0)
portfolio = PaperPortfolio(capital)
portfolio.open_position(
    PaperPosition("DEMO", "BUY", int(quantity), entry, entry * 0.95, entry * 1.10)
)
paper_cols = st.columns(3)
paper_cols[0].metric("Available Cash", f"₹{portfolio.realized_free_cash:,.0f}")
paper_cols[1].metric("Marked Value", f"₹{portfolio.mark_to_market({'DEMO': mark}):,.0f}")
paper_cols[2].metric("Paper P/L", f"₹{portfolio.positions[0].unrealized_pnl(mark):,.0f}")
st.info("Paper positions are local simulation only; no broker order is sent.")

section_header("📔 Trade Journal")
journal = [
    JournalEntry("DEMO", "Technology", "breakout", "BULLISH", "BUY", 2.0, "WIN"),
    JournalEntry("DEMO2", "Banking", "pullback", "BULLISH", "BUY", 1.0, "WIN"),
    JournalEntry("DEMO3", "Technology", "breakout", "NEUTRAL", "BUY", -1.0, "LOSS"),
]
summary = summarize_journal(journal)
journal_cols = st.columns(4)
journal_cols[0].metric("Recorded Trades", summary["total_trades"])
journal_cols[1].metric("Win Rate", f"{summary['win_rate']:.1f}%")
journal_cols[2].metric("Expectancy", f"{summary['expectancy_r']:+.2f}R")
journal_cols[3].metric("Best Setup", str(summary["best_setup"]))

st.dataframe(
    [
        {
            "Setup": setup,
            "Expectancy (R)": f"{expectancy:+.2f}",
        }
        for setup, expectancy in summary["setup_expectancy"].items()
    ],
    use_container_width=True,
    hide_index=True,
)

section_header("🛡️ Validation Rules")
for rule in (
    "Backtests consume supplied trades; they do not invent historical prices.",
    "Paper trading never sends broker orders.",
    "Expectancy is preferred over win rate alone when comparing strategies.",
    "Positive sample performance must be validated out of sample before deployment.",
):
    st.write(f"• {rule}")

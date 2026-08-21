"""Live NSE intraday command center."""

from collections import defaultdict
from datetime import datetime

import pandas as pd
import streamlit as st

from trading_assistant.application.live_analysis import TechnicalMetadataLoader
from trading_assistant.data.interfaces import Timeframe
from trading_assistant.data.market_calendar import IST
from trading_assistant.indicators import ema, macd, relative_volume, rsi, supertrend
from trading_assistant.monitoring.sector_scanner import sector_performance, symbol_sector
from trading_assistant.monitoring.signal_journal import SignalJournal, SignalRecord
from trading_assistant.ui.theme import apply_theme, page_header, section_header

st.set_page_config(page_title="NSE Intraday", page_icon="📈", layout="wide")
apply_theme()
page_header(
    "📈 NSE Intraday Command Center",
    "Live NSE discovery · sector rotation · automatic trade alerts · live chart",
    accent="cyan",
)
st.caption(
    "Decision-support only. BUY/SELL alerts are generated only when the formal "
    "trade engine confirms the setup; the application never places orders."
)

service = st.session_state.get("live_service")
scanner = st.session_state.get("scanner")
if service is None or scanner is None:
    st.warning("Connect Groww or Upstox from the main Trading Assistant page first.")
    st.stop()

provider = service.builder.provider
loader = TechnicalMetadataLoader(provider)
journal = SignalJournal("reports/nse_signal_journal.csv")

for key, default in {
    "nse_candidates": (),
    "nse_alert_candidates": (),
    "nse_last_scan": None,
    "nse_alert_diagnostics": (),
    "nse_sector_rows": (),
    "nse_selected": None,
    "nse_auto_started": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def _pnl_percent(direction: str, entry: float, price: float) -> float:
    if entry == 0:
        return 0.0
    sign = 1.0 if direction == "BUY" else -1.0
    return ((price - entry) / entry) * 100.0 * sign


def _outcome_r(record: SignalRecord, exit_price: float) -> float:
    risk = abs(record.entry - record.stop_loss)
    if risk == 0:
        return 0.0
    if record.direction == "BUY":
        return (exit_price - record.entry) / risk
    return (record.entry - exit_price) / risk


def _support_resistance(frame: pd.DataFrame, price: float):
    supports: list[float] = []
    resistances: list[float] = []
    highs = frame["high"].to_numpy()
    lows = frame["low"].to_numpy()
    for index in range(1, len(frame) - 1):
        if highs[index] >= highs[index - 1] and highs[index] > highs[index + 1]:
            if highs[index] > price:
                resistances.append(float(highs[index]))
        if lows[index] <= lows[index - 1] and lows[index] < lows[index + 1]:
            if lows[index] < price:
                supports.append(float(lows[index]))

    def nearest(levels: list[float]) -> tuple[float, ...]:
        chosen: list[float] = []
        for level in sorted(levels, key=lambda value: abs(value - price)):
            if not any(abs(level - item) / max(price, 1e-9) < 0.002 for item in chosen):
                chosen.append(level)
            if len(chosen) == 3:
                break
        return tuple(sorted(chosen))

    return nearest(supports), nearest(resistances)


def _live_snapshot(symbol: str, now: datetime) -> dict[str, object]:
    bars = list(
        provider.get_ohlcv(
            symbol,
            Timeframe.ONE_MINUTE,
            now - pd.Timedelta(minutes=260).to_pytimedelta(),
            now,
        )
    )
    latest = provider.get_latest_bar(symbol, Timeframe.ONE_MINUTE)
    if latest.timestamp > bars[-1].timestamp:
        bars.append(latest)
    elif latest.timestamp == bars[-1].timestamp:
        bars[-1] = latest
    if len(bars) < 30:
        raise ValueError(f"Insufficient 1m data for {symbol}: {len(bars)} candles")

    frame = loader._frame(bars[-250:]).copy()
    frame = frame.drop_duplicates(subset=["timestamp"], keep="last").sort_values("timestamp")
    frame.index = pd.DatetimeIndex(frame["timestamp"])
    close = frame["close"]
    price = float(latest.close)
    ema9_values = ema(close, 9)
    ema20_values = ema(close, 20)
    trend = supertrend(frame)
    typical = (frame["high"] + frame["low"] + close) / 3.0
    cumulative_volume = frame["volume"].cumsum()
    vwap = float((typical * frame["volume"]).cumsum().iloc[-1] / cumulative_volume.iloc[-1])
    supports, resistances = _support_resistance(frame, price)
    chart = pd.DataFrame(
        {
            "Price": close.tail(120),
            "EMA 9": ema9_values.tail(120),
            "EMA 20": ema20_values.tail(120),
            "VWAP": pd.Series(vwap, index=close.tail(120).index),
        }
    )
    return {
        "price": price,
        "timestamp": latest.timestamp,
        "ema9": float(ema9_values.iloc[-1]),
        "ema20": float(ema20_values.iloc[-1]),
        "rsi": float(rsi(close, 14).iloc[-1]),
        "macd": float(macd(close)["histogram"].iloc[-1]),
        "rvol": float(relative_volume(frame).iloc[-1]),
        "supertrend": "BULLISH" if float(trend["direction"].iloc[-1]) > 0 else "BEARISH",
        "vwap": vwap,
        "supports": supports,
        "resistances": resistances,
        "chart": chart,
        "bars": len(frame),
    }


def _record_result(result, now: datetime) -> None:
    action = result.decision.action.value
    if action not in {"BUY", "SELL"} or result.risk_plan is None:
        return
    existing = journal.records()
    if any(
        record.symbol == result.symbol
        and record.direction == action
        and record.status == "OPEN"
        for record in existing
    ):
        return
    risk = result.risk_plan
    risk_amount = abs(risk.entry - risk.stop_loss)
    journal.record(
        SignalRecord(
            signal_id=f"nse-{result.symbol}-{action}-{now.isoformat()}",
            timestamp=now.isoformat(),
            market="NSE",
            symbol=result.symbol,
            direction=action,
            score=result.decision.score,
            entry=risk.entry,
            stop_loss=risk.stop_loss,
            target_1=risk.target_1,
            target_2=risk.target_2,
            risk_reward=(abs(risk.target_2 - risk.entry) / risk_amount if risk_amount else 0.0),
            reason=result.explanation.why_this_decision,
        )
    )


def _update_outcomes(symbol: str, price: float, now: datetime) -> None:
    for record in journal.records():
        if record.symbol != symbol or record.status != "OPEN":
            continue
        if record.direction == "BUY":
            t1 = price >= record.target_1
            t2 = price >= record.target_2
            stop = price <= record.stop_loss
        else:
            t1 = price <= record.target_1
            t2 = price <= record.target_2
            stop = price >= record.stop_loss
        exit_price = record.target_2 if t2 else record.stop_loss if stop else None
        journal.update_live_state(record.signal_id, t1, t2, stop, exit_price)
        if t2:
            journal.resolve(
                record.signal_id,
                "TARGET_2_ACHIEVED",
                record.target_2,
                _outcome_r(record, record.target_2),
                now,
            )
        elif stop:
            journal.resolve(
                record.signal_id,
                "STOP_LOSS_HIT",
                record.stop_loss,
                _outcome_r(record, record.stop_loss),
                now,
            )


def _top_by_sector(candidates, limit: int = 10):
    grouped = defaultdict(list)
    for candidate in candidates:
        grouped[symbol_sector(candidate.symbol)].append(candidate)
    return {
        sector: tuple(sorted(items, key=lambda item: item.score, reverse=True)[:limit])
        for sector, items in grouped.items()
    }


def _run_market_alert_engine() -> None:
    now = datetime.now(IST)
    try:
        universe_candidates = scanner.scan(now, limit=60)
        alert_candidates = universe_candidates[:20]
        results = service.analyze([item.symbol for item in alert_candidates], now)
        for result in results:
            _record_result(result, now)
        diagnostics = []
        result_by_symbol = {item.symbol: item for item in results}
        for candidate in alert_candidates:
            result = result_by_symbol.get(candidate.symbol)
            diagnostics.append(
                {
                    "Symbol": candidate.symbol,
                    "Sector": symbol_sector(candidate.symbol),
                    "Bias": candidate.direction,
                    "Scanner Score": f"{candidate.score:.0f}/100",
                    "Price": f"₹{candidate.price:.2f}",
                    "5m Move": f"{candidate.change_pct:+.2f}%",
                    "RVOL": f"{candidate.relative_volume:.2f}x",
                    "Trade Decision": (
                        result.decision.action.value if result is not None else "DATA ERROR"
                    ),
                    "Decision Score": (
                        f"{result.decision.score:.1f}/100" if result is not None else "-"
                    ),
                    "Blocker": (
                        " | ".join(result.decision.reasons[-2:])
                        if result is not None
                        else service.errors.get(candidate.symbol, "No analysis result")
                    ),
                }
            )
        st.session_state.nse_candidates = universe_candidates
        st.session_state.nse_alert_candidates = alert_candidates
        st.session_state.nse_alert_diagnostics = tuple(diagnostics)
        st.session_state.nse_last_scan = now
    except Exception as error:
        st.error(f"Automatic NSE alert scan failed: {error}")


if not st.session_state.nse_auto_started:
    st.session_state.nse_auto_started = True
    _run_market_alert_engine()

st.divider()
section_header("🧭 Market-Wide Alert Engine")
st.caption(
    "The engine discovers current NSE movers, ranks them across sectors, and "
    "checks the strongest candidates for formal BUY/SELL confirmation."
)
scan_col, status_col = st.columns([1, 3])
with scan_col:
    if st.button("🔎 Scan NSE now", type="primary", use_container_width=True):
        _run_market_alert_engine()
        st.rerun()
with status_col:
    last_scan = st.session_state.nse_last_scan
    if last_scan:
        st.success(
            f"Alert engine active · last scan {last_scan.strftime('%H:%M:%S IST')} · "
            "automatic re-scan every 60 seconds"
        )


@st.fragment(run_every=60)
def _alert_refresh() -> None:
    if provider.is_market_open():
        _run_market_alert_engine()


_alert_refresh()

candidates = st.session_state.nse_candidates
if candidates:
    section_header("🏆 Sector-wise Intraday Opportunities")
    st.caption("Up to the best 10 ranked movers are shown in each discovered sector.")
    sector_groups = _top_by_sector(candidates, limit=10)
    for sector in sorted(sector_groups):
        items = sector_groups[sector]
        with st.expander(f"{sector} · {len(items)} active candidates", expanded=False):
            st.dataframe(
                [
                    {
                        "Rank": rank,
                        "Symbol": item.symbol,
                        "Bias": item.direction,
                        "Score": f"{item.score:.0f}/100",
                        "Price": f"₹{item.price:.2f}",
                        "5m Move": f"{item.change_pct:+.2f}%",
                        "RVOL": f"{item.relative_volume:.2f}x",
                    }
                    for rank, item in enumerate(items, 1)
                ],
                use_container_width=True,
                hide_index=True,
            )

    sector_options = ["All sectors"] + sorted(sector_groups)
    selected_sector = st.selectbox("Sector filter", sector_options)
    sector_candidates = (
        candidates
        if selected_sector == "All sectors"
        else sector_groups.get(selected_sector, ())
    )
    symbols = [item.symbol for item in sector_candidates]
    if symbols:
        selected = st.selectbox(
            "🎯 Select stock for live terminal",
            symbols,
            index=(
                symbols.index(st.session_state.nse_selected)
                if st.session_state.nse_selected in symbols
                else 0
            ),
            key="nse_selected_widget",
        )
        st.session_state.nse_selected = selected
else:
    st.info("No scanner candidates are available yet. Use Scan NSE now.")

section_header("🏭 Sector Rotation — What Is Strong Today?")
try:
    sectors = sector_performance()
    st.session_state.nse_sector_rows = tuple(sectors)
except Exception as error:
    sectors = st.session_state.nse_sector_rows
    if not sectors:
        st.warning(f"Live NSE sector data unavailable: {error}")

if sectors:
    sector_table = [
        {
            "Rank": index,
            "Sector": item.name,
            "Today": f"{item.change_pct:+.2f}%",
            "Strength": f"{item.score:.0f}/100",
            "Adv": item.advances,
            "Dec": item.declines,
            "Unchanged": item.unchanged,
        }
        for index, item in enumerate(sectors, 1)
    ]
    st.dataframe(sector_table, use_container_width=True, hide_index=True)
    best = sectors[0]
    if best.change_pct > 0:
        st.success(
            f"🏆 Strongest sector right now: {best.name} ({best.change_pct:+.2f}%). "
            "Prefer stocks whose live setup agrees with sector direction."
        )
    else:
        st.warning("No tracked sector is currently positive; the market is broadly weak.")
else:
    st.info("Sector ranking will populate from NSE live index data during market hours.")


def _render_selected(symbol: str) -> None:
    now = datetime.now(IST)
    try:
        results = service.analyze([symbol], now)
        snapshot = _live_snapshot(symbol, now)
        result = next((item for item in results if item.symbol == symbol), None)
        if result is not None:
            _record_result(result, now)
        _update_outcomes(symbol, float(snapshot["price"]), now)
    except Exception as error:
        st.error(f"Unable to load live {symbol}: {error}")
        return

    records = [record for record in journal.records() if record.symbol == symbol]
    active = [record for record in records if record.status == "OPEN"]
    active_alert = active[-1] if active else None

    st.divider()
    section_header(f"📊 {symbol} Live Intraday Terminal")
    st.caption(
        f"Broker candle: {snapshot['timestamp'].strftime('%H:%M:%S %Z')} · "
        "terminal refreshes every 5 seconds"
    )
    cols = st.columns(7)
    cols[0].metric("Current Price", f"₹{snapshot['price']:.2f}")
    cols[1].metric("EMA 9", f"₹{snapshot['ema9']:.2f}")
    cols[2].metric("EMA 20", f"₹{snapshot['ema20']:.2f}")
    cols[3].metric("RSI", f"{snapshot['rsi']:.1f}")
    cols[4].metric("MACD Hist", f"{snapshot['macd']:.4f}")
    cols[5].metric("RVOL", f"{snapshot['rvol']:.2f}x")
    cols[6].metric("Supertrend", snapshot["supertrend"])

    chart_col, level_col = st.columns([2, 1])
    with chart_col:
        section_header("📈 Live Price Chart")
        st.line_chart(snapshot["chart"], height=380, use_container_width=True)
        st.caption("1-minute live price with EMA 9, EMA 20 and VWAP · last 120 bars")
    with level_col:
        section_header("🎯 Support / Resistance")
        st.markdown("**🔴 Resistance**")
        for index, level in enumerate(snapshot["resistances"], 1):
            st.write(f"R{index}: **₹{level:.2f}**")
        if not snapshot["resistances"]:
            st.info("No resistance detected.")
        st.markdown("**🟢 Support**")
        for index, level in enumerate(snapshot["supports"], 1):
            st.write(f"S{index}: **₹{level:.2f}**")
        if not snapshot["supports"]:
            st.info("No support detected.")

    section_header("🚨 Active Trading Alert")
    if active_alert is not None:
        if active_alert.direction == "BUY":
            st.success(f"🟢 LIVE BUY ALERT — {symbol} · ₹{active_alert.entry:.2f}")
        else:
            st.error(f"🔴 LIVE SELL ALERT — {symbol} · ₹{active_alert.entry:.2f}")
        st.write(active_alert.reason)
        plan = st.columns(6)
        plan[0].metric("Signal", active_alert.direction)
        plan[1].metric("Entry", f"₹{active_alert.entry:.2f}")
        plan[2].metric("Stop Loss", f"₹{active_alert.stop_loss:.2f}")
        plan[3].metric("Target 1", f"₹{active_alert.target_1:.2f}")
        plan[4].metric("Target 2", f"₹{active_alert.target_2:.2f}")
        plan[5].metric(
            "Live P/L",
            f"{_pnl_percent(active_alert.direction, active_alert.entry, float(snapshot['price'])):+.2f}%",
        )
    elif result is not None:
        action = result.decision.action.value
        if action == "BUY":
            st.success("🟢 BUY confirmed by the formal trade engine; waiting for alert journal refresh.")
        elif action == "SELL":
            st.error("🔴 SELL confirmed by the formal trade engine; waiting for alert journal refresh.")
        elif action == "WATCH":
            st.warning("🟡 WATCH — setup is promising but below the trade threshold.")
        else:
            st.info("⚪ NO TRADE — current evidence does not meet the trade requirements.")
        st.write(result.explanation.why_this_decision)
        st.caption(
            f"Decision score: {result.decision.score:.1f}/100 · "
            f"R:R: {result.decision.risk_reward:.2f}"
        )
    else:
        st.warning("No formal analysis result was produced for this symbol.")

    if records:
        section_header("📒 Alert History")
        st.dataframe(
            [
                {
                    "Time": record.timestamp,
                    "Alert": record.direction,
                    "Entry": f"₹{record.entry:.2f}",
                    "SL": f"₹{record.stop_loss:.2f}",
                    "T1": f"₹{record.target_1:.2f}",
                    "T2": f"₹{record.target_2:.2f}",
                    "Status": record.status,
                    "Score": f"{record.score:.0f}/100",
                }
                for record in reversed(records)
            ],
            use_container_width=True,
            hide_index=True,
        )


@st.fragment(run_every=5)
def _terminal_refresh() -> None:
    symbol = st.session_state.nse_selected
    if symbol and provider.is_market_open():
        _render_selected(symbol)


if st.session_state.nse_selected:
    _terminal_refresh()

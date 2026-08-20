"""Live NSE intraday dashboard matching the Crypto trading workflow."""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from trading_assistant.application.live_analysis import TechnicalMetadataLoader
from trading_assistant.data.interfaces import Timeframe
from trading_assistant.indicators import ema, macd, relative_volume, rsi, supertrend
from trading_assistant.monitoring.signal_journal import SignalJournal, SignalRecord

st.set_page_config(page_title="NSE Intraday", page_icon="📈", layout="wide")
st.title("📈 NSE Intraday Trading")
st.caption(
    "Live NSE decision-support dashboard. It does not place orders; "
    "validate alerts with paper trading first."
)

service = st.session_state.get("live_service")
scanner = st.session_state.get("scanner")
if service is None or scanner is None:
    st.warning("Connect Groww or Upstox from the main Trading Assistant page first.")
    st.stop()

provider = service.builder.provider
journal = SignalJournal("reports/nse_signal_journal.csv")
loader = TechnicalMetadataLoader(provider)


def _pnl_percent(direction: str, entry: float, price: float) -> float:
    if entry == 0:
        return 0.0
    multiplier = 1.0 if direction == "BUY" else -1.0
    return ((price - entry) / entry) * 100.0 * multiplier


def _outcome_r(record: SignalRecord, exit_price: float) -> float:
    risk = abs(record.entry - record.stop_loss)
    if risk == 0:
        return 0.0
    if record.direction == "BUY":
        return (exit_price - record.entry) / risk
    return (record.entry - exit_price) / risk


def _support_resistance(
    frame: pd.DataFrame,
    price: float,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
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
            if not any(abs(level - item) / price < 0.002 for item in chosen):
                chosen.append(level)
            if len(chosen) == 3:
                break
        return tuple(sorted(chosen))

    return nearest(supports), nearest(resistances)


def _trend_from_frame(frame: pd.DataFrame) -> str:
    if len(frame) < 20:
        return "UNKNOWN"
    close = frame["close"]
    fast = float(ema(close, 9).iloc[-1])
    slow = float(ema(close, 20).iloc[-1])
    if fast > slow and float(close.iloc[-1]) > fast:
        return "BULLISH"
    if fast < slow and float(close.iloc[-1]) < fast:
        return "BEARISH"
    return "MIXED"


def _live_snapshot(symbol: str, now: datetime) -> dict[str, object]:
    bars = list(
        provider.get_ohlcv(
            symbol,
            Timeframe.ONE_MINUTE,
            now - pd.Timedelta(minutes=260).to_pytimedelta(),
            now,
        )
    )
    if len(bars) < 30:
        raise ValueError(f"Insufficient 1m data for {symbol}: {len(bars)} candles")

    frame = loader._frame(bars[-250:]).copy()
    close = frame["close"]
    latest_price = float(close.iloc[-1])
    open_price = float(frame["open"].iloc[0])
    high_price = float(frame["high"].max())
    low_price = float(frame["low"].min())
    volume = float(frame["volume"].sum())
    change_pct = ((latest_price - open_price) / open_price * 100.0) if open_price else 0.0

    ema9_value = float(ema(close, 9).iloc[-1])
    ema20_value = float(ema(close, 20).iloc[-1])
    rsi_value = float(rsi(close, 14).iloc[-1])
    macd_histogram = float(macd(close)["histogram"].iloc[-1])
    relative_volume_value = float(relative_volume(frame).iloc[-1])
    trend = supertrend(frame)
    supertrend_direction = (
        "BULLISH" if float(trend["direction"].iloc[-1]) > 0 else "BEARISH"
    )

    typical_price = (frame["high"] + frame["low"] + frame["close"]) / 3.0
    volume_sum = frame["volume"].cumsum()
    vwap = float((typical_price * frame["volume"]).cumsum().iloc[-1] / volume_sum.iloc[-1])
    supports, resistances = _support_resistance(frame, latest_price)

    five_minute = (
        frame.resample("5min")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna()
    )
    fifteen_minute = (
        frame.resample("15min")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna()
    )

    recent = frame[["open", "high", "low", "close", "volume"]].tail(30).copy()
    recent.index = recent.index.strftime("%H:%M")
    recent.columns = ["Open", "High", "Low", "Close", "Volume"]

    chart = pd.DataFrame(
        {
            "Price": close.tail(120),
            "EMA 9": ema(close, 9).tail(120),
            "EMA 20": ema(close, 20).tail(120),
            "VWAP": pd.Series(vwap, index=close.tail(120).index),
        }
    )

    return {
        "price": latest_price,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "change_pct": change_pct,
        "volume": volume,
        "ema9": ema9_value,
        "ema20": ema20_value,
        "rsi": rsi_value,
        "macd": macd_histogram,
        "rvol": relative_volume_value,
        "vwap": vwap,
        "supertrend": supertrend_direction,
        "trend_1m": _trend_from_frame(frame),
        "trend_5m": _trend_from_frame(five_minute),
        "trend_15m": _trend_from_frame(fifteen_minute),
        "supports": supports,
        "resistances": resistances,
        "chart": chart,
        "recent": recent,
    }


def _record_result(result, now: datetime) -> None:
    action = result.decision.action.value
    if action not in {"BUY", "SELL"} or result.risk_plan is None:
        return
    risk = result.risk_plan
    existing = journal.records()
    if any(
        record.symbol == result.symbol
        and record.direction == action
        and record.status == "OPEN"
        for record in existing
    ):
        return
    risk_amount = abs(risk.entry - risk.stop_loss)
    target_2_r = (
        abs(risk.target_2 - risk.entry) / risk_amount
        if risk_amount
        else 0.0
    )
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
            risk_reward=target_2_r,
            reason=result.explanation.why_this_decision,
        )
    )


def _update_outcomes(symbol: str, price: float, now: datetime) -> None:
    for record in journal.records():
        if record.symbol != symbol or record.status != "OPEN":
            continue
        if record.direction == "BUY":
            target_1_hit = price >= record.target_1
            target_2_hit = price >= record.target_2
            stop_hit = price <= record.stop_loss
        else:
            target_1_hit = price <= record.target_1
            target_2_hit = price <= record.target_2
            stop_hit = price >= record.stop_loss

        sell_price = None
        if target_2_hit:
            sell_price = record.target_2
        elif stop_hit:
            sell_price = record.stop_loss
        elif target_1_hit:
            sell_price = record.target_1

        journal.update_live_state(
            record.signal_id,
            target_1_hit,
            target_2_hit,
            stop_hit,
            sell_price,
        )
        if target_2_hit:
            journal.resolve(
                record.signal_id,
                "TARGET_2_ACHIEVED",
                record.target_2,
                _outcome_r(record, record.target_2),
                now,
            )
        elif stop_hit:
            journal.resolve(
                record.signal_id,
                "STOP_LOSS_HIT",
                record.stop_loss,
                _outcome_r(record, record.stop_loss),
                now,
            )


def _render_selected(symbol: str) -> None:
    now = datetime.now(timezone.utc)
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

    st.markdown(f"### 📊 {symbol} Live Trading Terminal")
    st.caption(
        f"Live update: {now.strftime('%H:%M:%S UTC')} · "
        "auto-refresh every 5 seconds · paper-trading decision support"
    )

    price_cols = st.columns(7)
    price_cols[0].metric("LTP", f"₹{snapshot['price']:.2f}")
    price_cols[1].metric("Change", f"{snapshot['change_pct']:+.2f}%")
    price_cols[2].metric("Open", f"₹{snapshot['open']:.2f}")
    price_cols[3].metric("Day High", f"₹{snapshot['high']:.2f}")
    price_cols[4].metric("Day Low", f"₹{snapshot['low']:.2f}")
    price_cols[5].metric("Volume", f"{snapshot['volume']:,.0f}")
    price_cols[6].metric("VWAP", f"₹{snapshot['vwap']:.2f}")

    st.markdown("#### 📈 Live Technical Dashboard")
    indicator_cols = st.columns(7)
    indicator_cols[0].metric("EMA 9", f"₹{snapshot['ema9']:.2f}")
    indicator_cols[1].metric("EMA 20", f"₹{snapshot['ema20']:.2f}")
    indicator_cols[2].metric("RSI", f"{snapshot['rsi']:.1f}")
    indicator_cols[3].metric("MACD Hist", f"{snapshot['macd']:.4f}")
    indicator_cols[4].metric("RVOL", f"{snapshot['rvol']:.2f}x")
    indicator_cols[5].metric("Supertrend", str(snapshot["supertrend"]))
    indicator_cols[6].metric("VWAP Position", "ABOVE" if snapshot["price"] >= snapshot["vwap"] else "BELOW",)

    trend_cols = st.columns(4)
    trend_cols[0].metric("1m Trend", str(snapshot["trend_1m"]))
    trend_cols[1].metric("5m Trend", str(snapshot["trend_5m"]))
    trend_cols[2].metric("15m Trend", str(snapshot["trend_15m"]))
    if snapshot["rsi"] >= 60:
        momentum = "STRONG BULLISH"
    elif snapshot["rsi"] <= 40:
        momentum = "STRONG BEARISH"
    else:
        momentum = "NEUTRAL"
    trend_cols[3].metric("Momentum", momentum)

    chart_col, levels_col = st.columns([2, 1])
    with chart_col:
        st.markdown("#### 📉 Live Price Chart")
        st.line_chart(snapshot["chart"], height=360, use_container_width=True)
        st.caption("1-minute candles · last 120 bars · EMA 9 / EMA 20 / VWAP")
    with levels_col:
        st.markdown("#### 🎯 Support / Resistance")
        st.markdown("**🔴 Resistance**")
        if snapshot["resistances"]:
            for index, level in enumerate(snapshot["resistances"], 1):
                st.write(f"R{index}: **₹{level:.2f}**")
        else:
            st.info("No resistance detected.")
        st.markdown("**🟢 Support**")
        if snapshot["supports"]:
            for index, level in enumerate(snapshot["supports"], 1):
                st.write(f"S{index}: **₹{level:.2f}**")
        else:
            st.info("No support detected.")

    st.markdown("#### 🚨 Live Trading Alert")
    if active_alert is not None:
        if active_alert.direction == "BUY":
            st.success(f"🟢 LIVE BUY ALERT — {symbol} at ₹{active_alert.entry:.2f}")
        else:
            st.error(f"🔴 LIVE SELL ALERT — {symbol} at ₹{active_alert.entry:.2f}")
        st.write(active_alert.reason)
        plan_cols = st.columns(6)
        plan_cols[0].metric("Alert Price", f"₹{active_alert.entry:.2f}")
        plan_cols[1].metric("Stop Loss", f"₹{active_alert.stop_loss:.2f}")
        plan_cols[2].metric("Target 1", f"₹{active_alert.target_1:.2f}")
        plan_cols[3].metric("Target 2", f"₹{active_alert.target_2:.2f}")
        plan_cols[4].metric("Risk : Reward", f"1:{active_alert.risk_reward:.1f}")
        pnl = _pnl_percent(
            active_alert.direction,
            active_alert.entry,
            float(snapshot["price"]),
        )
        plan_cols[5].metric("Current P/L", f"{pnl:+.2f}%")
    elif result is not None and result.decision.action.value in {"BUY", "SELL"}:
        direction = result.decision.action.value
        if direction == "BUY":
            st.success("🟢 BUY conditions detected — waiting for persisted alert state.")
        else:
            st.error("🔴 SELL conditions detected — waiting for persisted alert state.")
        st.write(result.explanation.why_this_decision)
    else:
        st.warning("🟡 LIVE WATCH — no confirmed BUY/SELL alert at this moment.")
        if result is not None:
            st.write(result.explanation.why_this_decision)

    if records:
        latest = records[-1]
        st.markdown("#### 📌 Alert Trade Plan")
        cols = st.columns(6)
        cols[0].metric("Alert Price", f"₹{latest.entry:.2f}")
        cols[1].metric("Stop Loss", f"₹{latest.stop_loss:.2f}")
        cols[2].metric("Target 1", f"₹{latest.target_1:.2f}")
        cols[3].metric("Target 2", f"₹{latest.target_2:.2f}")
        cols[4].metric(
            "Sell Price",
            f"₹{latest.sell_price:.2f}" if latest.sell_price else "—",
        )
        cols[5].metric("Status", latest.status)
        if latest.target_2_achieved:
            st.success(f"🎯 Target 2 achieved at ₹{latest.target_2:.2f}")
        elif latest.target_1_achieved:
            st.success(f"🎯 Target 1 achieved at ₹{latest.target_1:.2f}")
        elif latest.stop_loss_hit:
            st.error(f"🛑 Stop loss hit at ₹{latest.stop_loss:.2f}")
        elif latest.status == "OPEN":
            st.info("Alert is OPEN. Sell price and target status update from live price.")

    with st.expander("🕯️ Recent 1-minute candles"):
        st.dataframe(snapshot["recent"], use_container_width=True)

    with st.expander("🔧 Live data diagnostics"):
        diag_cols = st.columns(5)
        diag_cols[0].metric("Broker", "CONNECTED")
        diag_cols[1].metric("1m Bars", len(snapshot["recent"]))
        diag_cols[2].metric("1m Trend", str(snapshot["trend_1m"]))
        diag_cols[3].metric("5m Trend", str(snapshot["trend_5m"]))
        diag_cols[4].metric("15m Trend", str(snapshot["trend_15m"]))
        st.caption("Data is refreshed from the configured broker market-data provider.")


st.subheader("🔎 NSE Intraday Scanner")
scan_col, limit_col = st.columns([3, 1])
with scan_col:
    scan_clicked = st.button(
        "🔎 Scan NSE intraday opportunities",
        type="primary",
        use_container_width=True,
    )
with limit_col:
    scan_limit = st.selectbox("Candidates", [5, 10, 15], index=1)

if scan_clicked:
    now = datetime.now(timezone.utc)
    with st.spinner("Scanning liquid NSE stocks and ranking intraday setups..."):
        st.session_state.nse_intraday_candidates = scanner.scan(
            now,
            limit=scan_limit,
        )

candidates = st.session_state.get("nse_intraday_candidates", ())
if candidates:
    st.markdown("### 🔥 Best NSE Intraday Opportunities")
    rows = [
        {
            "Rank": index,
            "Stock": item.symbol,
            "Signal": item.direction,
            "Score": f"{item.score:.0f}/100",
            "Price": f"₹{item.price:.2f}",
            "5m Move": f"{item.change_pct:+.2f}%",
            "RVOL": f"{item.relative_volume:.2f}x",
            "Why": item.reason,
        }
        for index, item in enumerate(candidates, 1)
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    selected = st.selectbox(
        "🎯 Select a stock to trade",
        [item.symbol for item in candidates],
        key="nse_intraday_selected",
    )
    st.caption("The selected stock is monitored live; no manual refresh is required.")

    @st.fragment(run_every="5s")
    def live_nse_selected() -> None:
        _render_selected(selected)

    live_nse_selected()
else:
    st.info("Run the NSE scanner to get automatically ranked opportunities.")

st.markdown("### 📒 NSE BUY / SELL Alert History")
records = journal.records()
if records:
    history = []
    for record in reversed(records):
        if record.target_2_achieved:
            outcome = "TARGET 2 ACHIEVED"
        elif record.target_1_achieved:
            outcome = "TARGET 1 ACHIEVED"
        elif record.stop_loss_hit:
            outcome = "STOP LOSS HIT"
        else:
            outcome = "OPEN"
        history.append(
            {
                "Time": record.timestamp,
                "Stock": record.symbol,
                "Alert": record.direction,
                "Alert Price": f"₹{record.entry:.2f}",
                "Stop Loss": f"₹{record.stop_loss:.2f}",
                "Target 1": f"₹{record.target_1:.2f}",
                "Target 2": f"₹{record.target_2:.2f}",
                "Sell Price": (
                    f"₹{record.sell_price:.2f}" if record.sell_price else "—"
                ),
                "Outcome": outcome,
                "P/L (R)": (
                    f"{record.outcome_r:+.2f}R"
                    if record.outcome_r is not None
                    else "OPEN"
                ),
                "Score": f"{record.score:.0f}/100",
            }
        )
    st.dataframe(history, use_container_width=True, hide_index=True)
else:
    st.info("No NSE BUY/SELL alerts have been recorded yet.")

if scanner.last_scan_count:
    with st.expander("🔧 NSE scan diagnostics"):
        cols = st.columns(4)
        cols[0].metric("Stocks scanned", scanner.last_scan_count)
        cols[1].metric("Data received", scanner.last_data_count)
        cols[2].metric("Qualified", scanner.last_qualified_count)
        cols[3].metric("Data errors", len(scanner.last_scan_errors))
        for symbol, error in list(scanner.last_scan_errors.items())[:20]:
            st.warning(f"{symbol}: {error}")

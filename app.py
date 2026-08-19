"""Streamlit dashboard for the Trading Assistant V1."""

# isort: skip_file

from datetime import datetime
import os

import pandas as pd
import streamlit as st

from trading_assistant.application import TradingAssistantApplication
from trading_assistant.application.live_analysis import LiveAnalysisService
from trading_assistant.brokers.connection import BrokerName
from trading_assistant.brokers.facade import BrokerFacade
from trading_assistant.brokers.factory import build_broker_connection_service
from trading_assistant.data.interfaces import Timeframe
from trading_assistant.data.market_calendar import IST
from trading_assistant.data.provider_factory import build_market_data_provider
from trading_assistant.indicators import ema, macd, relative_volume, rsi, supertrend
from trading_assistant.monitoring.cap_universe import current_cap_classification
from trading_assistant.monitoring.market_scanner import MarketScanner
from trading_assistant.monitoring.notifier import ConsoleNotifier, NotificationDispatcher
from trading_assistant.monitoring.signal_dispatch import SignalDispatcher
from trading_assistant.monitoring.signal_journal import SignalJournal, SignalRecord
from trading_assistant.monitoring.state import MonitorStateMachine
from trading_assistant.monitoring.swing_scanner import SwingScanner


st.set_page_config(
    page_title="Trading Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def build_application() -> TradingAssistantApplication:
    service = build_broker_connection_service()
    return TradingAssistantApplication(BrokerFacade(service))


app = build_application()

for key, default in {
    "monitoring": False,
    "results": (),
    "live_service": None,
    "notifier": ConsoleNotifier(sent=[]),
    "scanner_candidates": (),
    "scanner": None,
    "swing_candidates": (),
    "swing_scanner": None,
    "nse_intraday_selected": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


st.title("📈 Trading Assistant")
st.caption(
    "Intraday and swing decision-support for Indian equities — the tool scans the market, "
    "ranks candidates, and lets you choose what to monitor. It never places orders."
)


with st.sidebar:
    st.header("Connection")
    broker_name = st.selectbox(
        "Broker",
        [item.value for item in app.broker.available_brokers()],
    )
    selected_broker = BrokerName(broker_name)

    token_name = {
        BrokerName.GROWW: "GROWW_ACCESS_TOKEN",
        BrokerName.UPSTOX: "UPSTOX_ACCESS_TOKEN",
    }.get(selected_broker)

    if token_name and not os.getenv(token_name):
        st.warning("Broker credentials are not configured.")
        token = st.text_input(
            "Access token (session only)",
            type="password",
            help="Used only by this running app. It is not written to GitHub.",
        )
        if token and st.button("Use token", use_container_width=True):
            os.environ[token_name] = token.strip()
            st.success("Token loaded for this app session.")
            st.rerun()
    else:
        st.success("Broker credentials configured.")

    st.divider()
    st.header("Monitoring")
    refresh_seconds = st.select_slider(
        "Refresh interval",
        options=[5, 10, 15, 30, 60],
        value=5,
        format_func=lambda value: f"{value} seconds",
    )

    if st.button("Disconnect broker", use_container_width=True):
        try:
            state = app.disconnect_broker()
            st.session_state.monitoring = False
            st.session_state.live_service = None
            st.session_state.scanner = None
            st.session_state.swing_scanner = None
            st.info(state.message)
        except RuntimeError as error:
            st.warning(str(error))


now = datetime.now(IST)
connected = st.session_state.live_service is not None
market_open = (
    st.session_state.live_service.builder.provider.is_market_open()
    if connected
    else False
)
snapshot = app.dashboard(now)
symbols = snapshot.watchlist.symbols()

status_col, market_col, watch_col, signal_col = st.columns(4)
with status_col:
    st.metric("Broker", "Connected" if connected else "Disconnected")
with market_col:
    st.metric("NSE Market", "OPEN" if market_open else "CLOSED")
with watch_col:
    st.metric("Selected", len(symbols))
with signal_col:
    st.metric("Active Signals", len(st.session_state.results))

connect_col, refresh_col = st.columns([3, 1])
with connect_col:
    if st.button(
        f"Connect {broker_name.title()}",
        type="primary",
        use_container_width=True,
    ):
        try:
            state = app.connect_broker(selected_broker, now)
            if state.status.value == "connected":
                provider = build_market_data_provider(selected_broker)
                dispatcher = SignalDispatcher(
                    MonitorStateMachine(),
                    NotificationDispatcher(st.session_state.notifier),
                )
                st.session_state.live_service = LiveAnalysisService(provider, dispatcher)
                st.session_state.scanner = MarketScanner(provider)
                try:
                    cap_classification = current_cap_classification()
                except Exception as error:
                    cap_classification = {}
                    st.warning(f"AMFI cap classification unavailable: {error}")
                st.session_state.swing_scanner = SwingScanner(
                    provider,
                    classification=cap_classification,
                )
                st.success(state.message)
                st.rerun()
            else:
                st.error(state.message)
        except Exception as error:
            st.error(f"Unable to connect: {error}")
with refresh_col:
    if st.button("Refresh now", use_container_width=True):
        st.rerun()


if not connected:
    st.info("Connect Groww or Upstox first. The tool will then scan the market for you.")
else:
    st.subheader("🔎 Intraday Market Scanner")
    st.write(
        "You do **not** need to tell the tool which stock to use. "
        "Scan the liquid NSE universe, review the strongest current setups, "
        "then choose the stock you want to monitor intraday."
    )

    scan_col, limit_col = st.columns([3, 1])
    with scan_col:
        scan_clicked = st.button(
            "🔎 Scan intraday opportunities",
            type="primary",
            use_container_width=True,
            disabled=not market_open,
        )
    with limit_col:
        scan_limit = st.selectbox("Candidates", [5, 10, 15], index=1)

    if scan_clicked:
        scanner: MarketScanner = st.session_state.scanner
        with st.spinner("Scanning liquid NSE stocks and ranking intraday setups..."):
            st.session_state.scanner_candidates = scanner.scan(now, limit=scan_limit)
        st.rerun()

    candidates = st.session_state.scanner_candidates
    scanner = st.session_state.scanner
    if candidates:
        st.markdown("#### 🔥 Best NSE Intraday Opportunities")
        rows = [
            {
                "Rank": index,
                "Symbol": item.symbol,
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

        candidate_symbols = [item.symbol for item in candidates]
        selected = st.selectbox(
            "🎯 Select a stock to trade",
            candidate_symbols,
            index=(
                candidate_symbols.index(st.session_state.nse_intraday_selected)
                if st.session_state.nse_intraday_selected in candidate_symbols
                else 0
            ),
            key="nse_intraday_selected_widget",
        )
        st.session_state.nse_intraday_selected = selected
        st.caption(
            "The selected stock is monitored live. Entry/SL/targets are fixed when an "
            "alert is created; current price and P/L remain live."
        )

        if st.button("✅ Add selected stock to watchlist", type="secondary"):
            app.add_symbol(selected, now.isoformat())
            st.rerun()
    elif market_open:
        st.info("Run the intraday scanner to get ranked stock suggestions.")

    if scanner is not None and scanner.last_scan_count:
        with st.expander("🔧 Intraday scan diagnostics"):
            diag_cols = st.columns(4)
            diag_cols[0].metric("Stocks scanned", scanner.last_scan_count)
            diag_cols[1].metric("Data received", scanner.last_data_count)
            diag_cols[2].metric("Qualified", scanner.last_qualified_count)
            diag_cols[3].metric("Data errors", len(scanner.last_scan_errors))
            if scanner.last_scan_errors:
                st.caption("The first 20 data errors are shown below.")
                for failed_symbol, error in list(scanner.last_scan_errors.items())[:20]:
                    st.warning(f"{failed_symbol}: {error}")

    if not candidates and not market_open:
        st.warning("NSE regular session is closed. Intraday scanner is paused.")

    st.divider()
    st.subheader("📅 Swing Trading Scanner")
    st.write(
        "Swing mode is separate from intraday mode. It scans daily candles for "
        "multi-day setups and gives you a shortlist; you choose which stocks to study further."
    )
    st.caption(
        "Long-only cash-equity candidates for V1. Typical holding horizon: 2–8 weeks. "
        "The scanner does not place orders."
    )

    swing_col, swing_limit_col = st.columns([3, 1])
    with swing_col:
        swing_clicked = st.button(
            "📅 Scan swing opportunities",
            type="secondary",
            use_container_width=True,
        )
    with swing_limit_col:
        swing_limit = st.selectbox("Swing candidates", [5, 10, 15], index=1)

    if swing_clicked:
        swing_scanner: SwingScanner = st.session_state.swing_scanner
        with st.spinner("Scanning daily trends, momentum, volume and breakouts..."):
            st.session_state.swing_candidates = swing_scanner.scan(
                now,
                limit=swing_limit,
            )
        st.rerun()

    swing_candidates = st.session_state.swing_candidates
    if swing_candidates:
        overall = sorted(swing_candidates, key=lambda item: item.score, reverse=True)
        st.markdown("#### 🔥 Best Overall Swing Opportunities")
        overall_rows = [
            {
                "Rank": index,
                "Segment": item.cap_segment,
                "Symbol": item.symbol,
                "Bias": item.direction,
                "Score": f"{item.score:.0f}/100",
                "Price": f"₹{item.price:.2f}",
                "20D": f"{item.change_20d_pct:+.2f}%",
                "Stop": f"₹{item.stop_loss:.2f}",
                "Target 1": f"₹{item.target_1:.2f}",
                "Target 2": f"₹{item.target_2:.2f}",
            }
            for index, item in enumerate(overall, 1)
        ]
        st.dataframe(overall_rows, use_container_width=True, hide_index=True)

        for segment, icon in (
            ("Large Cap", "📈"),
            ("Mid Cap", "📊"),
            ("Small Cap", "🚀"),
        ):
            segment_candidates = [
                item for item in swing_candidates if item.cap_segment == segment
            ]
            st.markdown(f"#### {icon} {segment} — Top {swing_limit}")
            if not segment_candidates:
                st.info(f"No qualifying {segment.lower()} setup found in this scan.")
                continue
            rows = [
                {
                    "Rank": index,
                    "Symbol": item.symbol,
                    "Bias": item.direction,
                    "Score": f"{item.score:.0f}/100",
                    "Price": f"₹{item.price:.2f}",
                    "20D": f"{item.change_20d_pct:+.2f}%",
                    "Stop": f"₹{item.stop_loss:.2f}",
                    "Target 1": f"₹{item.target_1:.2f}",
                    "Target 2": f"₹{item.target_2:.2f}",
                    "Hold": item.holding_period,
                    "Why": item.reason,
                }
                for index, item in enumerate(segment_candidates, 1)
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)

        swing_symbols = [item.symbol for item in swing_candidates]
        swing_chosen = st.multiselect(
            "Choose swing candidates for detailed review",
            swing_symbols,
            default=[item.symbol for item in overall[:3]],
            key="swing_selection",
        )
        if st.button("📌 Add selected swing stocks to watchlist", type="primary"):
            for item in swing_chosen:
                app.add_symbol(item, now.isoformat())
            st.rerun()
    else:
        swing_scanner: SwingScanner | None = st.session_state.swing_scanner
        if swing_scanner is not None and swing_scanner.last_scan_count:
            st.warning(
                f"Swing scan completed: {swing_scanner.last_qualified_count} candidates "
                f"qualified from {swing_scanner.last_scan_count} symbols."
            )
            if swing_scanner.last_scan_errors:
                with st.expander(
                    f"Show data errors ({len(swing_scanner.last_scan_errors)})"
                ):
                    for failed_symbol, error in swing_scanner.last_scan_errors.items():
                        st.warning(f"{failed_symbol}: {error}")
        else:
            st.info("Run the swing scanner to get a daily-chart shortlist.")


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


def _live_stock_snapshot(symbol: str, current_time: datetime) -> dict[str, object]:
    provider = st.session_state.live_service.builder.provider
    bars = list(
        provider.get_ohlcv(
            symbol,
            Timeframe.ONE_MINUTE,
            current_time - pd.Timedelta(minutes=260).to_pytimedelta(),
            current_time,
        )
    )
    if len(bars) < 30:
        raise ValueError(f"Insufficient 1m data for {symbol}: {len(bars)} candles")

    frame = pd.DataFrame(
        [
            {
                "timestamp": bar.timestamp,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
            for bar in bars[-250:]
        ]
    )
    close = frame["close"]
    trend = supertrend(frame)
    price = float(close.iloc[-1])
    supports, resistances = _support_resistance(frame, price)
    return {
        "price": price,
        "ema9": float(ema(close, 9).iloc[-1]),
        "ema20": float(ema(close, 20).iloc[-1]),
        "rsi": float(rsi(close, 14).iloc[-1]),
        "macd": float(macd(close)["histogram"].iloc[-1]),
        "rvol": float(relative_volume(frame).iloc[-1]),
        "supertrend": (
            "BULLISH" if float(trend["direction"].iloc[-1]) > 0 else "BEARISH"
        ),
        "supports": supports,
        "resistances": resistances,
    }


def _record_nse_alert(result, current_time: datetime, journal: SignalJournal) -> None:
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
    target_2_r = (
        abs(risk.target_2 - risk.entry) / risk_amount
        if risk_amount
        else 0.0
    )
    journal.record(
        SignalRecord(
            signal_id=(
                f"nse-{result.symbol}-{action}-"
                f"{current_time.isoformat()}"
            ),
            timestamp=current_time.isoformat(),
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


def _update_nse_outcomes(
    symbol: str,
    price: float,
    current_time: datetime,
    journal: SignalJournal,
) -> None:
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
                current_time,
            )
        elif stop_hit:
            journal.resolve(
                record.signal_id,
                "STOP_LOSS_HIT",
                record.stop_loss,
                _outcome_r(record, record.stop_loss),
                current_time,
            )


@st.fragment(run_every=refresh_seconds if connected else None)
def selected_nse_intraday_panel() -> None:
    symbol = st.session_state.nse_intraday_selected
    service: LiveAnalysisService | None = st.session_state.live_service
    if service is None or not symbol:
        return
    if not service.builder.provider.is_market_open():
        st.warning("NSE regular session is closed. Live intraday analysis is paused.")
        return

    current_time = datetime.now(IST)
    journal = SignalJournal("reports/nse_signal_journal.csv")
    try:
        results = service.analyze([symbol], current_time)
        result = next((item for item in results if item.symbol == symbol), None)
        snapshot = _live_stock_snapshot(symbol, current_time)
        if result is not None:
            _record_nse_alert(result, current_time, journal)
        _update_nse_outcomes(symbol, float(snapshot["price"]), current_time, journal)
    except Exception as error:
        st.error(f"Unable to load live {symbol}: {error}")
        return

    records = [record for record in journal.records() if record.symbol == symbol]
    active = [record for record in records if record.status == "OPEN"]
    active_alert = active[-1] if active else None

    st.divider()
    st.subheader(f"📊 {symbol} — Live Intraday Analysis")
    st.caption(
        f"Live update: {current_time.strftime('%H:%M:%S IST')} · "
        f"automatic refresh every {refresh_seconds} seconds"
    )

    cols = st.columns(7)
    cols[0].metric("Current Price", f"₹{snapshot['price']:.2f}")
    cols[1].metric("EMA 9", f"₹{snapshot['ema9']:.2f}")
    cols[2].metric("EMA 20", f"₹{snapshot['ema20']:.2f}")
    cols[3].metric("RSI", f"{snapshot['rsi']:.1f}")
    cols[4].metric("MACD Hist", f"{snapshot['macd']:.4f}")
    cols[5].metric("RVOL", f"{snapshot['rvol']:.2f}x")
    cols[6].metric("Supertrend", str(snapshot["supertrend"]))

    level_cols = st.columns(2)
    with level_cols[0]:
        st.markdown("#### 🟢 Support — maximum 3")
        if snapshot["supports"]:
            for index, level in enumerate(snapshot["supports"], 1):
                st.write(f"S{index}: **₹{level:.2f}**")
        else:
            st.info("No confirmed support below current price.")
    with level_cols[1]:
        st.markdown("#### 🔴 Resistance — maximum 3")
        if snapshot["resistances"]:
            for index, level in enumerate(snapshot["resistances"], 1):
                st.write(f"R{index}: **₹{level:.2f}**")
        else:
            st.info("No confirmed resistance above current price.")

    st.markdown("#### 🚨 Live Trading Alert")
    if active_alert is not None:
        if active_alert.direction == "BUY":
            st.success(
                f"🟢 LIVE BUY ALERT — {symbol} at ₹{active_alert.entry:.2f}"
            )
        else:
            st.error(
                f"🔴 LIVE SELL ALERT — {symbol} at ₹{active_alert.entry:.2f}"
            )
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
        st.info("Signal detected; the first persisted alert price will remain fixed.")
    else:
        st.warning("🟡 LIVE WATCH — no confirmed BUY/SELL alert at this moment.")

    if active_alert is not None:
        if active_alert.target_2_achieved:
            st.success(f"🎯 Target 2 achieved at ₹{active_alert.target_2:.2f}")
        elif active_alert.target_1_achieved:
            st.success(f"🎯 Target 1 achieved at ₹{active_alert.target_1:.2f}")
        elif active_alert.stop_loss_hit:
            st.error(f"🛑 Stop loss hit at ₹{active_alert.stop_loss:.2f}")
        else:
            st.info("Trade is OPEN. Target and stop-loss status are tracked live.")

    st.markdown("#### 📒 Alert History for this Stock")
    history = []
    for record in reversed(records[-20:]):
        if record.target_2_achieved:
            outcome = "TARGET 2 ACHIEVED"
        elif record.target_1_achieved:
            outcome = "TARGET 1 ACHIEVED"
        elif record.stop_loss_hit:
            outcome = "STOP LOSS HIT"
        else:
            outcome = "OPEN"
        comparison_price = record.sell_price or float(snapshot["price"])
        pnl = _pnl_percent(record.direction, record.entry, comparison_price)
        history.append(
            {
                "Time": record.timestamp,
                "Alert": record.direction,
                "Alert Price": f"₹{record.entry:.2f}",
                "Stop Loss": f"₹{record.stop_loss:.2f}",
                "Target 1": f"₹{record.target_1:.2f}",
                "Target 2": f"₹{record.target_2:.2f}",
                "Sell Price": (
                    f"₹{record.sell_price:.2f}" if record.sell_price else "—"
                ),
                "Outcome": outcome,
                "P/L": f"{pnl:+.2f}%",
                "R": (
                    f"{record.outcome_r:+.2f}R"
                    if record.outcome_r is not None
                    else "OPEN"
                ),
            }
        )
    if history:
        st.dataframe(history, use_container_width=True, hide_index=True)
    else:
        st.info("No BUY/SELL alerts recorded for this stock yet.")


if connected and st.session_state.nse_intraday_selected:
    selected_nse_intraday_panel()

st.subheader("Selected stocks to monitor")
if symbols:
    remove_cols = st.columns(min(len(symbols), 5))
    for index, item in enumerate(symbols):
        with remove_cols[index % len(remove_cols)]:
            st.button(
                f"{item}  ×",
                key=f"remove_{item}",
                on_click=app.remove_symbol,
                args=(item,),
                use_container_width=True,
            )
else:
    st.info("No stocks selected yet. Use the scanner above or add a stock to the watchlist.")


@st.fragment(run_every=refresh_seconds if st.session_state.monitoring else None)
def live_panel() -> None:
    service: LiveAnalysisService | None = st.session_state.live_service
    if service is None or not symbols:
        return
    if not service.builder.provider.is_market_open():
        st.warning("NSE regular session is closed. Live intraday analysis is paused.")
        return

    current_time = datetime.now(IST)
    with st.spinner("Running detailed multi-timeframe intraday analysis..."):
        results = service.analyze(symbols, current_time)
    st.session_state.results = results
    app.set_results(results)

    if service.errors:
        with st.expander(f"Data warnings ({len(service.errors)})"):
            for failed_symbol, error in service.errors.items():
                st.warning(f"{failed_symbol}: {error}")
    if not results:
        st.info("No qualifying intraday setup detected in the selected stocks.")
        return

    st.subheader("📢 Live Intraday Signals")
    st.caption(f"Last analysis: {current_time.strftime('%H:%M:%S IST')}")
    for result in results:
        decision = result.decision.action.value
        score = result.decision.score
        risk = result.risk_plan
        with st.container(border=True):
            title_col, score_col = st.columns([4, 1])
            with title_col:
                st.markdown(f"### {result.symbol} · {decision}")
                st.caption(
                    f"Setup: {result.setup.setup_type.value} · "
                    f"Timeframe: {result.timeframe.alignment.value}"
                )
            with score_col:
                st.metric("Score", f"{score:.0f}/100")
            reason_col, risk_col = st.columns(2)
            with reason_col:
                st.markdown("**Why this signal**")
                st.write(result.explanation.why_this_decision)
                st.markdown("**Confirmation**")
                for reason in result.decision.reasons:
                    st.write(f"• {reason}")
            with risk_col:
                st.markdown("**Risk plan**")
                if risk is None:
                    st.warning("No valid risk plan for this setup.")
                else:
                    metric_cols = st.columns(4)
                    metric_cols[0].metric("Entry", f"₹{risk.entry:.2f}")
                    metric_cols[1].metric("Stop", f"₹{risk.stop_loss:.2f}")
                    metric_cols[2].metric("Target 1", f"₹{risk.target_1:.2f}")
                    metric_cols[3].metric("Target 2", f"₹{risk.target_2:.2f}")
                    st.caption(
                        f"R:R to Target 1 = {risk.risk_reward_1:.2f} · "
                        f"Invalidation: {result.explanation.invalidation}"
                    )
            st.progress(min(max(score / 100.0, 0.0), 1.0), text="Decision confidence")

    if st.session_state.notifier.sent:
        st.subheader("Latest Alerts")
        for alert in st.session_state.notifier.sent[-5:][::-1]:
            st.info(f"{alert.sent_at.strftime('%H:%M:%S')} — {alert.message}")


live_panel()

st.divider()
st.subheader("How to use this tool")
steps = (
    "Connect the broker.",
    "Choose Intraday Scanner or Swing Scanner depending on your trading horizon.",
    "Let the tool rank stocks from the liquid NSE universe "
    "instead of entering a stock manually.",
    "Select a scanned intraday stock to open its live analysis panel.",
    "Review live indicators, support/resistance and fixed alert trade plans.",
    "Record signal outcomes before considering real-money trading.",
)
for index, step in enumerate(steps, 1):
    st.write(f"{index}. {step}")

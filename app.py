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
from trading_assistant.ui.theme import apply_theme, page_header, section_header


st.set_page_config(
    page_title="Trading Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


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


page_header(
    "📈 Trading Assistant",
    "Indian equities decision-support · intraday scanner · swing ideas · live monitoring",
    accent="gold",
)
st.caption(
    "Scan the market, rank opportunities and monitor selected setups. "
    "The application never places orders."
)


with st.sidebar:
    st.markdown("## ⚙️ Control Center")
    st.caption("Broker connection and live refresh settings")
    st.markdown("### 🔌 Connection")
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
    st.markdown("### ⏱️ Monitoring")
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

section_header("📊 Market Command Center")
status_cols = st.columns(4)
status_cols[0].metric("Broker", "Connected" if connected else "Disconnected")
status_cols[1].metric("NSE Market", "OPEN" if market_open else "CLOSED")
status_cols[2].metric("Watchlist", len(symbols))
status_cols[3].metric("Active Signals", len(st.session_state.results))

connect_col, refresh_col = st.columns([3, 1])
with connect_col:
    if st.button(
        f"🔌 Connect {broker_name.title()}",
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
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()


if not connected:
    st.info(
        "Connect Groww or Upstox to activate NSE scanning, live monitoring and swing analysis."
    )
else:
    section_header("⚡ Intraday Market Scanner")
    st.write(
        "Scan the liquid NSE universe, review the strongest current setups and "
        "choose the stock you want to monitor intraday."
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
        section_header("🔥 Best NSE Intraday Opportunities")
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

    if not candidates and not market_open:
        st.warning("NSE regular session is closed. Intraday scanner is paused.")

    intraday_live_slot = st.empty()


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
    section_header(f"📊 {symbol} Live Intraday Terminal")
    st.caption(
        f"Live update: {current_time.strftime('%H:%M:%S IST')} · "
        f"auto-refresh every {refresh_seconds}s"
    )

    metric_cols = st.columns(7)
    metric_cols[0].metric("Current Price", f"₹{snapshot['price']:.2f}")
    metric_cols[1].metric("EMA 9", f"₹{snapshot['ema9']:.2f}")
    metric_cols[2].metric("EMA 20", f"₹{snapshot['ema20']:.2f}")
    metric_cols[3].metric("RSI", f"{snapshot['rsi']:.1f}")
    metric_cols[4].metric("MACD Hist", f"{snapshot['macd']:.4f}")
    metric_cols[5].metric("RVOL", f"{snapshot['rvol']:.2f}x")
    metric_cols[6].metric("Supertrend", str(snapshot["supertrend"]))

    level_cols = st.columns(2)
    with level_cols[0]:
        section_header("🟢 Support")
        supports = snapshot["supports"]
        if supports:
            for index, level in enumerate(supports, 1):
                st.write(f"S{index}: **₹{level:.2f}**")
        else:
            st.info("No confirmed support below current price.")
    with level_cols[1]:
        section_header("🔴 Resistance")
        resistances = snapshot["resistances"]
        if resistances:
            for index, level in enumerate(resistances, 1):
                st.write(f"R{index}: **₹{level:.2f}**")
        else:
            st.info("No confirmed resistance above current price.")

    section_header("🚨 Active Trading Alert")
    if active_alert is not None:
        alert_text = "BUY" if active_alert.direction == "BUY" else "SELL"
        if active_alert.direction == "BUY":
            st.success(
                f"🟢 LIVE {alert_text} ALERT — {symbol} · "
                f"locked entry ₹{active_alert.entry:.2f}"
            )
        else:
            st.error(
                f"🔴 LIVE {alert_text} ALERT — {symbol} · "
                f"locked entry ₹{active_alert.entry:.2f}"
            )
        st.caption(
            "Entry, stop and targets remain fixed to the alert. "
            "Only current price and P/L update live."
        )
        st.write(active_alert.reason)
        plan_cols = st.columns(6)
        plan_cols[0].metric("Signal", alert_text)
        plan_cols[1].metric("Locked Entry", f"₹{active_alert.entry:.2f}")
        plan_cols[2].metric("Stop Loss", f"₹{active_alert.stop_loss:.2f}")
        plan_cols[3].metric("Target 1", f"₹{active_alert.target_1:.2f}")
        plan_cols[4].metric("Target 2", f"₹{active_alert.target_2:.2f}")
        pnl = _pnl_percent(
            active_alert.direction,
            active_alert.entry,
            float(snapshot["price"]),
        )
        plan_cols[5].metric("Live P/L", f"{pnl:+.2f}%")
    else:
        st.info("No active BUY/SELL alert is locked for this stock yet.")

    if records:
        section_header("📒 Alert History")
        st.dataframe(
            [
                {
                    "Time": record.timestamp,
                    "Alert": record.direction,
                    "Alert Price": f"₹{record.entry:.2f}",
                    "Stop Loss": f"₹{record.stop_loss:.2f}",
                    "Target 1": f"₹{record.target_1:.2f}",
                    "Target 2": f"₹{record.target_2:.2f}",
                    "Status": record.status,
                    "Score": f"{record.score:.0f}/100",
                }
                for record in reversed(records)
            ],
            use_container_width=True,
            hide_index=True,
        )


if connected:
    selected_nse_intraday_panel()


if connected:
    st.divider()
    section_header("📅 Swing Opportunities")
    st.caption(
        "Scan the broader NSE universe for multi-day opportunities. "
        "Swing ideas are separate from live intraday alerts."
    )
    swing_col, swing_limit_col = st.columns([3, 1])
    with swing_col:
        swing_clicked = st.button(
            "🔎 Scan swing opportunities",
            use_container_width=True,
        )
    with swing_limit_col:
        swing_limit = st.selectbox(
            "Swing candidates",
            [5, 10, 15],
            index=1,
        )
    if swing_clicked:
        swing_scanner: SwingScanner = st.session_state.swing_scanner
        with st.spinner("Scanning NSE stocks for swing opportunities..."):
            st.session_state.swing_candidates = swing_scanner.scan(
                now,
                limit=swing_limit,
            )

    swing_candidates = st.session_state.swing_candidates
    if swing_candidates:
        st.dataframe(
            [
                {
                    "Rank": index,
                    "Symbol": item.symbol,
                    "Signal": item.direction,
                    "Score": f"{item.score:.0f}/100",
                    "Price": f"₹{item.price:.2f}",
                    "Why": item.reason,
                }
                for index, item in enumerate(swing_candidates, 1)
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Run the swing scanner to populate multi-day opportunities.")

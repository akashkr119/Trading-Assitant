"""Streamlit dashboard for the Trading Assistant V1."""

# isort: skip_file

from datetime import datetime
import os

import streamlit as st

from trading_assistant.application import TradingAssistantApplication
from trading_assistant.application.live_analysis import LiveAnalysisService
from trading_assistant.brokers.connection import BrokerName
from trading_assistant.brokers.facade import BrokerFacade
from trading_assistant.brokers.factory import build_broker_connection_service
from trading_assistant.data.market_calendar import IST
from trading_assistant.data.provider_factory import build_market_data_provider
from trading_assistant.monitoring.cap_universe import current_cap_classification
from trading_assistant.monitoring.market_scanner import MarketScanner
from trading_assistant.monitoring.notifier import ConsoleNotifier, NotificationDispatcher
from trading_assistant.monitoring.signal_dispatch import SignalDispatcher
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
        options=[30, 60, 120, 300],
        value=60,
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
        "then choose the stocks you want to monitor intraday."
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
        st.markdown("#### Ranked intraday candidates")
        rows = [
            {
                "Rank": index,
                "Symbol": item.symbol,
                "Bias": item.direction,
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
        chosen = st.multiselect(
            "Choose which candidates to monitor",
            candidate_symbols,
            default=[item.symbol for item in candidates[:3]],
        )
        if st.button("✅ Add selected intraday candidates", type="primary"):
            for item in chosen:
                app.add_symbol(item, now.isoformat())
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
    st.info("No stocks selected yet. Use one of the scanners above.")


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
    "Review the shortlist and choose the stocks you want to monitor.",
    "Use detailed intraday analysis for same-day trades; "
    "use the daily swing setup for multi-day ideas.",
    "Record signal outcomes before considering real-money trading.",
)
for index, step in enumerate(steps, 1):
    st.write(f"{index}. {step}")

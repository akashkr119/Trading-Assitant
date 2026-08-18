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
from trading_assistant.monitoring.notifier import ConsoleNotifier, NotificationDispatcher
from trading_assistant.monitoring.signal_dispatch import SignalDispatcher
from trading_assistant.monitoring.state import MonitorStateMachine


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

if "monitoring" not in st.session_state:
    st.session_state.monitoring = False
if "results" not in st.session_state:
    st.session_state.results = ()
if "live_service" not in st.session_state:
    st.session_state.live_service = None
if "notifier" not in st.session_state:
    st.session_state.notifier = ConsoleNotifier(sent=[])


st.title("📈 Trading Assistant")
st.caption(
    "Intraday decision-support for Indian equities — analysis and alerts only; "
    "this interface never places orders."
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
    st.caption("Use 60 seconds for normal intraday monitoring.")

    if st.button("Disconnect broker", use_container_width=True):
        try:
            state = app.disconnect_broker()
            st.session_state.monitoring = False
            st.session_state.live_service = None
            st.info(state.message)
        except RuntimeError as error:
            st.warning(str(error))


now = datetime.now(IST)
snapshot = app.dashboard(now)


# Top status row
status_col, market_col, watch_col, signal_col = st.columns(4)
with status_col:
    connected = st.session_state.live_service is not None
    st.metric("Broker", "Connected" if connected else "Disconnected")
with market_col:
    market_open = (
        st.session_state.live_service.builder.provider.is_market_open()
        if connected
        else False
    )
    st.metric("NSE Market", "OPEN" if market_open else "CLOSED")
with watch_col:
    st.metric("Watchlist", len(snapshot.watchlist.symbols()))
with signal_col:
    st.metric("Active Signals", len(st.session_state.results))


# Connection controls
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
                st.session_state.live_service = LiveAnalysisService(
                    provider,
                    dispatcher,
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
    st.info(
        "Connect a broker to start live market analysis. "
        "The app is read-only and does not place trades."
    )


# Watchlist
st.subheader("Watchlist")
watch_col, add_col = st.columns([5, 1])
with watch_col:
    symbol = st.text_input(
        "NSE symbol",
        placeholder="RELIANCE",
        label_visibility="collapsed",
    )
with add_col:
    if st.button("Add symbol", use_container_width=True) and symbol.strip():
        app.add_symbol(symbol.strip().upper(), now.isoformat())
        st.rerun()

symbols = snapshot.watchlist.symbols()
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
    st.warning("Your watchlist is empty. Add NSE symbols above.")


@st.fragment(run_every=refresh_seconds if st.session_state.monitoring else None)
def live_panel() -> None:
    service: LiveAnalysisService | None = st.session_state.live_service
    if service is None or not symbols:
        return

    if not service.builder.provider.is_market_open():
        st.warning("NSE regular session is closed. Live analysis is paused.")
        return

    current_time = datetime.now(IST)
    with st.spinner("Refreshing market analysis..."):
        results = service.analyze(symbols, current_time)
    st.session_state.results = results
    app.set_results(results)

    if service.errors:
        with st.expander(f"Data warnings ({len(service.errors)})"):
            for failed_symbol, error in service.errors.items():
                st.warning(f"{failed_symbol}: {error}")

    if not results:
        st.info("No qualifying setup detected in the selected watchlist.")
        return

    st.subheader("Live Signals")
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
                    entry, stop = risk.entry, risk.stop_loss
                    target_1, target_2 = risk.target_1, risk.target_2
                    metric_cols = st.columns(4)
                    metric_cols[0].metric("Entry", f"₹{entry:.2f}")
                    metric_cols[1].metric("Stop", f"₹{stop:.2f}")
                    metric_cols[2].metric("Target 1", f"₹{target_1:.2f}")
                    metric_cols[3].metric("Target 2", f"₹{target_2:.2f}")
                    st.caption(
                        f"R:R to Target 1 = {risk.risk_reward_1:.2f} · "
                        f"Invalidation: {result.explanation.invalidation}"
                    )

            st.progress(min(max(score / 100.0, 0.0), 1.0), text="Decision confidence")

    if st.session_state.notifier.sent:
        st.subheader("Latest Alerts")
        for alert in st.session_state.notifier.sent[-5:][::-1]:
            st.info(f"{alert.symbol}: {alert.alert_type.value} — {alert.message}")


if connected and symbols:
    st.session_state.monitoring = st.toggle(
        "Enable live monitoring",
        value=st.session_state.monitoring,
        help="When enabled, the dashboard rechecks the watchlist automatically.",
    )

live_panel()


# Decision-support summary
st.divider()
st.subheader("How to use today's test")
steps = [
    "Connect Groww and confirm the account connection.",
    "Add 3–10 liquid NSE stocks to the watchlist.",
    "Enable live monitoring during the regular NSE session.",
    "Record every BUY/SELL/WATCH alert with its signal price and time.",
    "After 5/15/30/60 minutes, compare price movement with the signal direction.",
    "Do not trade real money until the 2–3 day observation results are reviewed.",
]
for number, step in enumerate(steps, 1):
    st.write(f"**{number}.** {step}")

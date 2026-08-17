"""Streamlit entry point for the Trading Assistant V1."""

from datetime import datetime

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


st.set_page_config(page_title="Trading Assistant", layout="wide")


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

st.title("Trading Assistant")
st.caption("Decision-support only — no orders are placed by this interface.")

broker_name = st.selectbox(
    "Broker",
    [item.value for item in app.broker.available_brokers()],
)
col1, col2 = st.columns(2)
with col1:
    if st.button("Connect broker", use_container_width=True):
        state = app.connect_broker(
            BrokerName(broker_name),
            datetime.now(IST),
        )
        if state.status.value == "connected":
            provider = build_market_data_provider(BrokerName(broker_name))
            dispatcher = SignalDispatcher(
                MonitorStateMachine(),
                NotificationDispatcher(st.session_state.notifier),
            )
            st.session_state.live_service = LiveAnalysisService(provider, dispatcher)
            st.success(state.message)
        else:
            st.error(state.message)
with col2:
    if st.button("Disconnect", use_container_width=True):
        try:
            state = app.disconnect_broker()
            st.session_state.monitoring = False
            st.session_state.live_service = None
            st.info(state.message)
        except RuntimeError as error:
            st.warning(str(error))

st.subheader("Watchlist")
symbol = st.text_input("Add NSE symbol", placeholder="RELIANCE")
if st.button("Add symbol") and symbol.strip():
    app.add_symbol(symbol, datetime.now(IST).isoformat())

snapshot = app.dashboard(datetime.now(IST))
st.write("Selected stocks:", ", ".join(snapshot.watchlist.symbols()) or "None")

connected = st.session_state.live_service is not None
if connected and snapshot.watchlist.symbols():
    st.session_state.monitoring = st.toggle(
        "Live monitoring (checks every minute)",
        value=st.session_state.monitoring,
    )
else:
    st.session_state.monitoring = False

run_every = 60 if st.session_state.monitoring else None


@st.fragment(run_every=run_every)
def live_panel() -> None:
    service: LiveAnalysisService | None = st.session_state.live_service
    if service is None:
        st.info("Connect Groww or Upstox to start market analysis.")
        return

    provider = service.builder.provider
    now = datetime.now(IST)
    if not provider.is_market_open():
        st.warning("NSE regular session is closed. Live analysis is paused.")
        return

    with st.spinner("Refreshing market analysis..."):
        results = service.analyze(snapshot.watchlist.symbols(), now)
    st.session_state.results = results

    if service.errors:
        for failed_symbol, error in service.errors.items():
            st.warning(f"{failed_symbol}: {error}")

    if not results:
        st.info("No qualifying setup detected in the selected watchlist.")
        return

    st.subheader("Live Signals")
    for result in results:
        card = result.explanation
        with st.container(border=True):
            st.write(
                f"**{result.symbol} — {result.decision.action.value}** "
                f"({result.decision.score:.1f}/100)"
            )
            st.write(f"Setup: {result.setup.setup_type.value}")
            st.write(card.why_this_decision)
            st.write(card.risk_summary)
            st.caption(f"Invalidation: {card.invalidation}")
            st.caption(
                "Timeframe: "
                f"{result.timeframe.reason}"
            )

    st.caption(f"Last refresh: {now.strftime('%H:%M:%S IST')}")


live_panel()

if st.session_state.notifier.sent:
    st.subheader("Latest Alerts")
    for alert in st.session_state.notifier.sent[-5:]:
        st.info(f"{alert.symbol}: {alert.alert_type.value} — {alert.message}")

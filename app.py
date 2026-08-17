"""Streamlit entry point for the Trading Assistant V1."""

from datetime import datetime

import streamlit as st

from trading_assistant.brokers.connection import BrokerName
from trading_assistant.brokers.facade import BrokerFacade
from trading_assistant.brokers.factory import build_broker_connection_service
from trading_assistant.application import TradingAssistantApplication


@st.cache_resource
def build_application() -> TradingAssistantApplication:
    service = build_broker_connection_service()
    return TradingAssistantApplication(BrokerFacade(service))


app = build_application()
st.set_page_config(page_title="Trading Assistant", layout="wide")
st.title("Trading Assistant")
st.caption("Decision-support only — no orders are placed by this interface.")

broker_name = st.selectbox("Broker", [item.value for item in app.broker.available_brokers()])
col1, col2 = st.columns(2)
with col1:
    if st.button("Connect broker", use_container_width=True):
        state = app.connect_broker(BrokerName(broker_name), datetime.now())
        if state.status.value == "connected":
            st.success(state.message)
        else:
            st.error(state.message)
with col2:
    if st.button("Disconnect", use_container_width=True):
        try:
            state = app.disconnect_broker()
            st.info(state.message)
        except RuntimeError as error:
            st.warning(str(error))

st.subheader("Watchlist")
symbol = st.text_input("Add NSE symbol", placeholder="RELIANCE")
if st.button("Add symbol") and symbol.strip():
    app.add_symbol(symbol, datetime.now().isoformat())

snapshot = app.dashboard(datetime.now())
st.write("Selected stocks:", ", ".join(snapshot.watchlist.symbols()) or "None")

st.subheader("Signals")
if not snapshot.signals:
    st.info("No analysis result is available yet.")
else:
    for card in snapshot.signals:
        with st.container(border=True):
            st.write(f"**{card.symbol} — {card.decision}** ({card.score:.1f}/100)")
            st.write(f"Setup: {card.setup}")
            st.write(card.reason)
            st.caption(card.risk_summary)
            st.caption(f"Invalidation: {card.invalidation}")

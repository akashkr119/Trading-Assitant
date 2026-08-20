"""Application setup for long-term investment research."""

from __future__ import annotations

from trading_assistant.data.nse_universe import nse_long_term_universe
from trading_assistant.data.yfinance_fundamentals import YFinanceFundamentalsProvider


def build_long_term_research() -> tuple[YFinanceFundamentalsProvider, list[str]]:
    """Build the default NSE research provider and normalized universe."""
    return YFinanceFundamentalsProvider(), nse_long_term_universe()

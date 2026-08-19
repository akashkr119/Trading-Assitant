from datetime import datetime

import pandas as pd

from trading_assistant.analysis.pipeline import StockAnalysisInput, analyze_stock
from trading_assistant.analysis.timeframe import TimeframeTrend


def _frame() -> pd.DataFrame:
    rows = []
    for index in range(35):
        close = 100.0 + index * 0.5
        rows.append(
            {
                "timestamp": datetime(2026, 8, 17, 9, 15 + index),
                "open": close - 0.2,
                "high": close + 0.4,
                "low": close - 0.4,
                "close": close,
                "volume": 1000.0,
            }
        )
    rows[-1]["close"] = 120.0
    rows[-1]["high"] = 121.0
    rows[-1]["volume"] = 3000.0
    return pd.DataFrame(rows)


def test_pipeline_connects_setup_timeframe_risk_decision_and_explanation() -> None:
    result = analyze_stock(
        StockAnalysisInput(
            symbol="RELIANCE",
            sector="Energy",
            frame=_frame(),
            market_score=85,
            sector_score=90,
            stock_score=88,
            confirmation_score=85,
            timeframe_trends=(
                TimeframeTrend("1m", "bullish"),
                TimeframeTrend("5m", "bullish"),
                TimeframeTrend("15m", "bullish"),
                TimeframeTrend("1h", "bullish"),
            ),
            entry=120,
            stop_loss=118,
            target_1=124,
            target_2=126,
        )
    )

    assert result is not None
    assert result.risk_plan is not None
    assert result.timeframe.alignment.value == "aligned"
    assert result.decision.action.value in {"BUY", "SELL", "WATCH", "NO_TRADE"}
    assert "RELIANCE" in result.explanation.why_this_stock


def test_pipeline_returns_none_without_a_setup() -> None:
    frame = _frame()
    frame["close"] = 100.0
    frame["high"] = 100.2
    frame["low"] = 99.8

    result = analyze_stock(
        StockAnalysisInput(
            symbol="TCS",
            sector="IT",
            frame=frame,
            market_score=50,
            sector_score=50,
            stock_score=50,
            confirmation_score=50,
            timeframe_trends=(TimeframeTrend("1m", "neutral"),),
            entry=100,
            stop_loss=99,
            target_1=102,
            target_2=103,
        )
    )

    assert result is None

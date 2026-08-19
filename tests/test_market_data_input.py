from datetime import datetime, timedelta

from trading_assistant.analysis.timeframe import TimeframeTrend
from trading_assistant.data.interfaces import OHLCVBar, Timeframe
from trading_assistant.monitoring.market_data_input import (
    AnalysisMetadata,
    MarketDataInputBuilder,
)


class FakeMarketDataProvider:
    def __init__(self, bars: list[OHLCVBar]) -> None:
        self.bars = bars
        self.request = None

    def get_ohlcv(self, symbol, timeframe, start, end):
        self.request = (symbol, timeframe, start, end)
        return self.bars

    def get_latest_bar(self, symbol, timeframe):
        return self.bars[-1]

    def is_market_open(self):
        return True


def _bars(count: int) -> list[OHLCVBar]:
    start = datetime(2026, 8, 18, 9, 15)
    return [
        OHLCVBar(
            timestamp=start + timedelta(minutes=index),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100.5 + index,
            volume=1000 + index,
        )
        for index in range(count)
    ]


def _metadata(symbol: str, timestamp: datetime) -> AnalysisMetadata:
    return AnalysisMetadata(
        sector="IT",
        market_score=80,
        sector_score=75,
        stock_score=85,
        confirmation_score=80,
        timeframe_trends=(TimeframeTrend("5m", "bullish"),),
        stop_loss=95,
        target_1=110,
        target_2=115,
    )


def test_market_data_builder_creates_analysis_input() -> None:
    provider = FakeMarketDataProvider(_bars(5))
    builder = MarketDataInputBuilder(provider, _metadata, lookback_bars=5)
    timestamp = datetime(2026, 8, 18, 9, 20)

    result = builder.build("RELIANCE", timestamp)

    assert result.symbol == "RELIANCE"
    assert result.sector == "IT"
    assert len(result.frame) == 5
    assert result.entry == 104.5
    assert provider.request[1] == Timeframe.ONE_MINUTE


def test_market_data_builder_rejects_insufficient_candles() -> None:
    provider = FakeMarketDataProvider(_bars(2))
    builder = MarketDataInputBuilder(provider, _metadata, lookback_bars=5)

    try:
        builder.build("RELIANCE", datetime(2026, 8, 18, 9, 20))
    except ValueError as error:
        assert "Insufficient market data" in str(error)
    else:
        raise AssertionError("Expected insufficient market data to fail")

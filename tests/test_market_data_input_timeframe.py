from datetime import datetime, timedelta, timezone

from trading_assistant.data.interfaces import OHLCVBar, Timeframe
from trading_assistant.monitoring.market_data_input import (
    AnalysisMetadata,
    MarketDataInputBuilder,
)


class FakeProvider:
    def __init__(self, bars: list[OHLCVBar]) -> None:
        self.bars = bars
        self.requested_timeframe = None

    def get_ohlcv(self, symbol, timeframe, start, end):
        self.requested_timeframe = timeframe
        return self.bars

    def get_latest_bar(self, symbol, timeframe):
        return self.bars[-1]

    def is_market_open(self):
        return True


def test_builder_uses_metadata_analysis_timeframe():
    start = datetime(2026, 8, 21, 9, 15, tzinfo=timezone.utc)
    bars = [
        OHLCVBar(
            timestamp=start + timedelta(minutes=5 * index),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100.5 + index,
            volume=1000,
        )
        for index in range(30)
    ]
    provider = FakeProvider(bars)
    metadata = AnalysisMetadata(
        sector="Chemicals",
        market_score=50,
        sector_score=50,
        stock_score=90,
        confirmation_score=80,
        timeframe_trends=(),
        stop_loss=120,
        target_1=130,
        target_2=140,
        analysis_timeframe=Timeframe.FIVE_MINUTES,
    )
    builder = MarketDataInputBuilder(
        provider,
        lambda _symbol, _timestamp: metadata,
        lookback_bars=100,
    )

    result = builder.build("FCL", bars[-1].timestamp)

    assert provider.requested_timeframe == Timeframe.FIVE_MINUTES
    assert result.frame["close"].iloc[-1] == bars[-1].close

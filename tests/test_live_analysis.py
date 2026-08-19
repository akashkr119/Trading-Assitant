from datetime import datetime, timedelta

from trading_assistant.application.live_analysis import TechnicalMetadataLoader
from trading_assistant.data.interfaces import OHLCVBar, Timeframe


class FakeProvider:
    def get_ohlcv(self, symbol, timeframe, start, end):
        count = {
            Timeframe.ONE_MINUTE: 250,
            Timeframe.FIVE_MINUTES: 100,
            Timeframe.FIFTEEN_MINUTES: 60,
            Timeframe.ONE_HOUR: 40,
        }[timeframe]
        step = {
            Timeframe.ONE_MINUTE: 1,
            Timeframe.FIVE_MINUTES: 5,
            Timeframe.FIFTEEN_MINUTES: 15,
            Timeframe.ONE_HOUR: 60,
        }[timeframe]
        base = datetime(2026, 8, 17, 9, 15)
        return [
            OHLCVBar(
                timestamp=base + timedelta(minutes=step * index),
                open=100 + index * 0.01,
                high=100.2 + index * 0.01,
                low=99.8 + index * 0.01,
                close=100.1 + index * 0.01,
                volume=1000 + index,
            )
            for index in range(count)
        ]


def test_technical_metadata_loader_builds_transparent_defaults() -> None:
    metadata = TechnicalMetadataLoader(FakeProvider()).load(
        "RELIANCE",
        datetime(2026, 8, 18, 10, 0),
    )

    assert metadata.sector == "Technical-only mode"
    assert metadata.market_score == 50.0
    assert metadata.sector_score == 50.0
    assert len(metadata.timeframe_trends) == 4
    assert metadata.stop_loss < metadata.target_1 < metadata.target_2

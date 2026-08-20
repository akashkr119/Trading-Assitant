"""Robust crypto intraday scanner that ranks near-setups as well as alerts."""

from __future__ import annotations

import pandas as pd

from trading_assistant.data.interfaces import OHLCVBar
from trading_assistant.indicators import ema, macd, relative_volume, rsi
from trading_assistant.monitoring.crypto_scanner import (
    CRYPTO_UNIVERSE,
    CryptoCandidate,
    CryptoIntradayScanner,
)


class RobustCryptoIntradayScanner(CryptoIntradayScanner):
    """Return ranked near-setups instead of an empty scan during quiet markets."""

    @staticmethod
    def _score(
        symbol: str,
        bars_5m: list[OHLCVBar],
        bars_15m: list[OHLCVBar],
    ) -> CryptoCandidate | None:
        candidate = CryptoIntradayScanner._score(symbol, bars_5m, bars_15m)
        if candidate is not None:
            return candidate

        frame_5m = CryptoIntradayScanner._frame(bars_5m)
        frame_15m = CryptoIntradayScanner._frame(bars_15m)
        close = frame_5m["close"]
        latest = float(close.iloc[-1])
        ema9 = float(ema(close, 9).iloc[-1])
        ema20 = float(ema(close, 20).iloc[-1])
        rsi_value = float(rsi(close, 14).iloc[-1])
        macd_histogram = float(macd(close)["histogram"].iloc[-1])
        rvol = float(relative_volume(frame_5m).iloc[-1])
        trend_5m = CryptoIntradayScanner._trend_direction(frame_5m)
        trend_15m = CryptoIntradayScanner._trend_direction(frame_15m)

        bullish_points = sum(
            (
                ema9 > ema20,
                macd_histogram > 0,
                trend_5m > 0,
                trend_15m > 0,
                45 <= rsi_value <= 70,
                rvol >= 1.0,
            )
        )
        bearish_points = sum(
            (
                ema9 < ema20,
                macd_histogram < 0,
                trend_5m < 0,
                trend_15m < 0,
                30 <= rsi_value <= 55,
                rvol >= 1.0,
            )
        )
        if bullish_points == 0 and bearish_points == 0:
            return None

        bullish = bullish_points >= bearish_points
        points = bullish_points if bullish else bearish_points
        direction = "LONG" if bullish else "SHORT"
        score = min(74.0, 40.0 + points * 5.0)
        recent_range = frame_5m["high"] - frame_5m["low"]
        risk = max(float(recent_range.iloc[-20:].median()), latest * 0.002)
        if bullish:
            stop = latest - risk
            target_1 = latest + risk * 2
            target_2 = latest + risk * 4
        else:
            stop = latest + risk
            target_1 = latest - risk * 2
            target_2 = latest - risk * 4

        reason = (
            f"Near-setup: {points}/6 conditions aligned; "
            f"EMA9/20 {'bullish' if bullish else 'bearish'}, "
            f"5m/15m trend {'aligned' if trend_5m == trend_15m else 'mixed'}, "
            f"RSI {rsi_value:.1f}, RVOL {rvol:.2f}x"
        )
        return CryptoCandidate(
            symbol=symbol,
            direction=direction,
            score=score,
            price=latest,
            entry=latest,
            stop_loss=stop,
            target_1=target_1,
            target_2=target_2,
            risk_reward=4.0,
            reason=reason,
        )


__all__ = ["CRYPTO_UNIVERSE", "RobustCryptoIntradayScanner"]

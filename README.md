# Trading Assistant

A decision-support tool for Indian intraday equities. It connects to supported broker market-data APIs, validates OHLCV data, analyzes selected stocks, and produces explainable BUY / SELL / WATCH / NO-TRADE decisions.

> **Safety:** V1 does not place orders. It is for decision support and live/paper testing, not a guaranteed-profit system.

## Features

- Groww and Upstox market-data adapters
- Broker connection/session layer
- 1-minute monitoring during NSE regular hours
- 1m / 5m / 15m / 1h technical confirmation
- EMA, MACD, RSI, Supertrend, VWAP and volume analysis
- Breakout, pullback, cross and VWAP setup detection
- Risk/reward, stop-loss, target and invalidation calculation
- Explainable signals and duplicate-alert suppression
- User-controlled watchlist
- Streamlit live dashboard
- Market-data validation and retry/failure isolation
- No automatic order placement

## How It Works

```text
Broker
  ↓
Market Data
  ↓
Validation
  ↓
Watchlist
  ↓
Multi-timeframe Analysis
  ↓
Setup Detection
  ↓
Trade Decision
  ↓
Risk / Reward
  ↓
Explanation + Alert
  ↓
Dashboard
```

## Current V1 Status

The tested core, broker adapters, market-data pipeline, validation, monitoring, dashboard, and live technical-analysis path are implemented.

The current live mode is intentionally conservative: market and sector scores remain neutral until dedicated breadth/sector data sources are connected. Broker authentication currently uses runtime access tokens; a polished browser-based OAuth connection flow is still future work.

## Quick Start

1. Install Python 3.11+.
2. Install the project and development dependencies.
3. Set the required broker access token as an environment variable.
4. For Upstox, also configure `UPSTOX_INSTRUMENT_KEYS`.
5. Start the dashboard:

```bash
streamlit run app.py
```

6. Connect the broker, add symbols such as `RELIANCE` or `TCS`, and enable **Live monitoring**.

The dashboard refreshes the analysis every minute while the session is active and the NSE regular session is open.

## Development

Development follows:

```text
Build → Test → Ruff → CI Green → Continue
```

## What Remains

- Browser-based broker OAuth / token acquisition
- Dedicated market breadth and sector-ranking data
- Live charts and richer market overview
- Backtesting and paper-trading validation
- Trade journal/performance analytics
- Optional order execution only after the above are validated


# Trading Assistant

A Python-based trading decision-support tool for the Indian stock market. The product is designed to help users identify tradable opportunities, understand **why** a stock is selected, monitor user-selected stocks continuously during market hours, and receive explainable BUY/SELL alerts.

> **Educational and decision-support only:** The system must never claim guaranteed profits or guaranteed winning trades. Signals are technical-analysis decisions and must be validated through backtesting and paper trading before real-money use.

## Product Vision

The core idea is:

> **Market → Strong Sector → Strong Stocks → User Selects Stocks → 1-Minute Monitoring → Pattern/Setup Detection → BUY/SELL/WATCH/NO TRADE → Detailed Explanation → Alert → Trade Record**

The assistant should support multiple trading styles over time. V1 focuses on **intraday trading**, while the architecture also supports the planned swing-trading engine and future positional trading.

## Core Principles

1. **Market first:** understand the overall market before ranking stocks.
2. **Sector first:** identify where relative strength and participation are concentrated.
3. **Stock selection:** find the best tradable stocks inside stronger sectors.
4. **User control:** the engine suggests candidates; the user selects which stocks enter live monitoring.
5. **1-minute monitoring:** selected intraday stocks are refreshed and analyzed every minute during market hours.
6. **Multi-timeframe analysis:** use higher timeframes for context and lower timeframes for entries.
7. **No single-indicator signals:** indicators are supporting evidence, not standalone BUY/SELL triggers.
8. **Explain every decision:** every BUY, SELL, WATCH, and NO TRADE result must explain the evidence.
9. **Risk before reward:** calculate entry, stop loss, targets, and risk/reward before issuing a trade signal.
10. **WAIT is valid:** the engine must be able to reject a trade or wait for confirmation.
11. **No alert spam:** refreshing every minute must not produce the same alert every minute.
12. **Record outcomes:** signals and trade outcomes must be stored for objective performance analysis.

---

# V1 End-to-End Workflow

```text
                         MARKET
                            ↓
                     MARKET ANALYSIS
                            ↓
                     SECTOR RANKING
                            ↓
                      STOCK RANKING
                            ↓
                   USER SELECTS STOCKS
                            ↓
                    1-MINUTE MONITORING
                            ↓
                 MULTI-TIMEFRAME ANALYSIS
                            ↓
              INDICATOR + PRICE ACTION ENGINE
                            ↓
                     SETUP DETECTION
                            ↓
                    CONFIRMATION CHECK
                            ↓
                     RISK / REWARD CHECK
                            ↓
              ┌─────────────┼─────────────┐
              ↓             ↓             ↓
             BUY          WATCH          SELL
              │             │             │
              └─────────────┼─────────────┘
                            ↓
                    EXPLANATION ENGINE
                            ↓
                    DASHBOARD + ALERT
                            ↓
                       TRADE RECORD
                            ↓
                  PERFORMANCE / BACKTEST
```

---

# Technology Stack

The initial implementation is planned around:

### Backend

- Python 3.13+
- Pandas
- NumPy
- Requests

### Technical Analysis

- `pandas-ta` or `ta`

### Dashboard

- Streamlit
- Plotly

### Database

- SQLite initially
- PostgreSQL as a future option

### Alerts

- Telegram Bot API

### Configuration

- YAML or JSON configuration

The data-provider implementation is intentionally separated from the strategy engine so a provider can be changed later without rewriting the analysis logic.

---

# Application Structure

The initial architecture is planned as:

```text
trading_assistant/
│
├── app.py
│
├── config/
│   └── config.yaml
│
├── data/
│   └── market_data.py
│
├── indicators/
│   ├── ema.py
│   ├── rsi.py
│   ├── vwap.py
│   ├── macd.py
│   └── supertrend.py
│
├── scanners/
│   ├── intraday_scanner.py
│   ├── swing_scanner.py
│   └── sector_scanner.py
│
├── scoring/
│   └── confidence_engine.py
│
├── patterns/
│   └── setup_engine.py
│
├── risk/
│   └── risk_engine.py
│
├── explanations/
│   └── explanation_engine.py
│
├── alerts/
│   └── telegram_alert.py
│
├── backtest/
│   └── backtester.py
│
├── database/
│   └── trades.db
│
└── reports/
    └── daily_report.py
```

The exact file structure may evolve during implementation, but responsibilities should remain separated: data, indicators, scanning, setup detection, scoring, risk, explanations, alerts, storage, and reporting.

---

# Module 1 — Market Data Engine

Create a reusable market-data layer supporting:

- Live quotes
- Historical data
- User watchlist data
- 1-minute candles
- 5-minute candles
- 15-minute candles
- Hourly candles
- Daily candles

Initial logical functions:

```python
get_live_quote()
get_historical_data()
get_watchlist_data()
```

The data engine must normalize incoming data into a consistent format so the rest of the application does not depend on a specific provider.

The provider must support reliable intraday refreshes and historical data sufficient for backtesting. The exact production data provider is a separate implementation decision and must not be hard-coded into the strategy design.

---

# Module 2 — Market Analysis / Sentiment Engine

Before stock selection, evaluate:

- NIFTY 50
- BANKNIFTY
- India VIX / volatility
- Advance/Decline ratio
- Market momentum

Output:

- Bullish
- Bearish
- Neutral
- Market Sentiment Score (0–100)

Initial classification:

| Score | Classification |
|---|---|
| 80–100 | Strong Bullish |
| 65–79 | Bullish |
| 45–64 | Neutral |
| 30–44 | Bearish |
| 0–29 | Strong Bearish |

The score describes the current technical environment. It is **not** a probability of profit.

---

# Module 3 — Sector Strength Engine

Initial sectors:

- IT
- Banking
- Auto
- Pharma
- FMCG
- Energy
- Metals
- Realty
- PSU

The engine ranks sectors from strongest to weakest.

### Sector Strength Score

| Factor | Points |
|---|---:|
| Sector trend | 25 |
| Relative performance vs NIFTY | 25 |
| Volume participation | 20 |
| Sector breadth | 20 |
| Momentum | 10 |
| **Total** | **100** |

The analysis should consider the performance of constituent stocks, sector benchmark/ETF performance where reliable data is available, volume participation, and breadth.

Example output:

```text
1. Banking   91
2. IT        87
3. Auto      82
4. Pharma    74
```

Strong sectors become the first filter for stock discovery.

---

# Module 4 — Best Stock Finder

Within stronger sectors, rank the most tradable stocks.

Example:

```text
BANKING

1. HDFCBANK    93
2. ICICIBANK   89
3. SBIN        85
4. AXISBANK    81
```

Ranking considers:

- Trend strength/alignment
- Relative strength
- RSI
- Volume
- VWAP
- Price action
- Breakout/setup conditions
- Sector strength
- Market context

The tool must answer:

> **Why this stock instead of another stock in the same sector?**

A score without an explanation is not considered a complete recommendation.

---

# Module 5 — User-Controlled Watchlist

The system should suggest candidate stocks, but **the user decides which stocks to monitor**.

Example:

```text
BANKING

☑ HDFCBANK
☑ ICICIBANK
☐ SBIN
☑ AXISBANK

[ START MONITORING ]
```

Only selected stocks enter the active intraday monitoring engine.

---

# Module 6 — Intraday Scanner

The intraday scanner runs every **1 minute** during market hours.

It should monitor:

- NIFTY 50
- BANKNIFTY context
- Selected user watchlist
- Relevant sector context

Calculate/update:

- EMA 9
- EMA 20
- EMA 50
- EMA 200
- RSI(14)
- VWAP
- MACD
- Supertrend
- Relative Volume
- Support/resistance
- Price structure
- Setup/pattern state

### Critical alert rule

> **1-minute refresh does not mean a new alert every minute.**

A monitored stock maintains a setup state. The engine only generates a new alert when a meaningful setup, trigger, invalidation, or trade state changes.

---

# Multi-Timeframe Analysis

V1 uses different timeframes for different jobs:

| Timeframe | Purpose |
|---|---|
| 1-minute | Entry/trigger monitoring |
| 5-minute | Primary intraday setup and structure |
| 15-minute | Direction confirmation |
| 1-hour | Larger market/stock context |

Conceptually:

```text
1H  → Context
15m → Direction confirmation
5m  → Setup
1m  → Entry trigger
```

The engine should not blindly require every timeframe to be identical. Conflicting timeframes should reduce confidence or produce WATCH/NO TRADE when appropriate.

---

# Technical Analysis Engine

## EMA

Use:

- EMA 9
- EMA 20
- EMA 50
- EMA 200

Strong bullish structure:

```text
Price > EMA 9 > EMA 20 > EMA 50 > EMA 200
```

Strong bearish structure:

```text
Price < EMA 9 < EMA 20 < EMA 50 < EMA 200
```

EMA conditions are trend evidence, not standalone signals.

## VWAP

Bullish intraday evidence:

- Price above VWAP
- Preferably VWAP rising
- Pullbacks respecting VWAP strengthen the setup

Bearish intraday evidence:

- Price below VWAP
- Preferably VWAP falling
- Retests rejecting VWAP strengthen the setup

## RSI(14)

RSI is momentum context rather than a standalone BUY/SELL trigger.

- 55–70: healthy bullish momentum
- 60–70: strong bullish momentum
- >70: strong momentum but possible late-entry risk
- 30–45: bearish momentum
- <30: extreme weakness; does not automatically mean BUY

## MACD

Bullish confirmation:

- MACD above signal
- Positive/increasing histogram
- Stronger when aligned with the broader trend

Bearish confirmation:

- MACD below signal
- Negative/increasing bearish histogram
- Stronger when aligned with the broader trend

## Supertrend

- Bullish Supertrend supports BUY setups
- Bearish Supertrend supports SELL setups
- Conflicting Supertrend reduces setup confidence

## Relative Volume

Initial classification:

| Relative Volume | Interpretation |
|---|---|
| <0.8x | Weak |
| 0.8–1.2x | Normal |
| 1.2–1.5x | Elevated |
| 1.5–2.0x | Strong |
| >2.0x | Very Strong |

For breakout setups, approximately **1.5x or higher** is preferred as volume confirmation. The final implementation should use a session-aware baseline so early-session and late-session volume are compared fairly.

---

# Module 7 — Pattern / Setup Engine

V1 intentionally starts with a small set of understandable setups.

## A. Breakout — BUY

Typical confirmation:

1. Clear resistance exists.
2. Price approaches resistance.
3. Candle closes above resistance.
4. Volume expands.
5. 5-minute structure supports the move.
6. Market and sector context are not strongly against the trade.
7. The 1-minute trigger confirms the entry.

## B. Breakdown — SELL

Typical confirmation:

1. Clear support exists.
2. Price approaches support.
3. Candle closes below support.
4. Volume expands.
5. 5-minute structure confirms weakness.
6. Market and sector context are not strongly against the trade.
7. The 1-minute trigger confirms the entry.

## C. Bullish Pullback — BUY

Typical confirmation:

1. Strong bullish trend exists.
2. Price pulls back toward EMA20, VWAP, or support.
3. Selling pressure decreases.
4. Bullish reversal candle/structure appears.
5. Volume confirms recovery.
6. 1-minute trigger confirms the entry.

## D. Bearish Pullback — SELL

Typical confirmation:

1. Strong bearish trend exists.
2. Price rallies toward EMA20, VWAP, or resistance.
3. Buying pressure weakens.
4. Bearish rejection appears.
5. Volume confirms weakness.
6. 1-minute trigger confirms the entry.

## E. Consolidation — WATCH / NO TRADE

If price is moving sideways without a meaningful confirmed breakout or breakdown, the engine should not force a trade.

---

# Module 8 — Decision Engine

V1 has four primary user-facing states:

| State | Meaning |
|---|---|
| 🟢 **BUY** | Confirmed bullish trade setup |
| 🔴 **SELL** | Confirmed bearish trade setup |
| 🟡 **WATCH** | Interesting setup, but entry trigger is not confirmed |
| ⚪ **NO TRADE** | Conditions are insufficient or risk is unacceptable |

**WAIT is a valid decision.**

## BUY Logic

A BUY requires a confirmed setup, not a single indicator.

Required areas:

- Acceptable/strong sector context
- Market not strongly bearish against the setup
- Bullish 5-minute structure/setup
- Confirmed 1-minute trigger
- Supporting price action
- Acceptable risk/reward

Supporting evidence can include:

- Price above VWAP
- Bullish EMA structure
- RSI 55–70
- Bullish MACD
- Bullish Supertrend
- Elevated/strong relative volume
- Confirmed breakout or bullish pullback

## SELL Logic

A SELL requires a confirmed bearish setup.

Required areas:

- Acceptable/weakening sector context
- Market not strongly bullish against the setup
- Bearish 5-minute structure/setup
- Confirmed 1-minute trigger
- Supporting bearish price action
- Acceptable risk/reward

Supporting evidence can include:

- Price below VWAP
- Bearish EMA structure
- RSI 30–45
- Bearish MACD
- Bearish Supertrend
- Elevated/strong relative volume
- Confirmed breakdown or bearish pullback

---

# Setup / Confidence Score

The score represents **setup quality**, not probability of winning.

### V1 Operational Score

| Component | Points |
|---|---:|
| Trend alignment | 20 |
| VWAP | 10 |
| RSI | 10 |
| MACD | 10 |
| Supertrend | 10 |
| Volume | 15 |
| Price action | 10 |
| Breakout/setup | 10 |
| Sector strength | 3 |
| Market context | 2 |
| **Total** | **100** |

Initial interpretation:

| Score | Interpretation |
|---|---|
| 0–60 | NO TRADE / Avoid |
| 61–75 | WATCH / Moderate |
| 76–85 | Good Setup |
| 86–92 | High Quality |
| 93–100 | Very High Quality |

**Score alone must never trigger a trade.** A high-scoring stock remains WATCH until the actual entry trigger is confirmed.

The original project specification also defined a confidence model using Trend Alignment 20, VWAP 10, RSI 10, MACD 10, Supertrend 10, Volume Spike 15, Breakout 15, Sector Strength 5, and Market Sentiment 5. The V1 operational model above refines that allocation to give explicit weight to price action and to keep setup quality separate from market/sector context. This can be revised after backtesting.

---

# Risk Engine

Risk is evaluated before a BUY/SELL alert is issued.

## Entry

Entry must come from the specific setup and confirmed trigger. There is no fixed percentage entry rule.

## Stop Loss

Stop loss should be structure-based:

- Breakout: below the breakout level/retest low or relevant swing low
- Bullish pullback: below pullback low/support
- Breakdown: above breakdown level/retest high or relevant swing high
- Bearish pullback: above rejection high/resistance

ATR should be used as a sanity check so a stop is not unrealistically tight for the current volatility.

## Targets

Targets should consider:

- Risk/reward
- Nearby resistance/support
- ATR
- Previous swing levels

Initial preference:

- Target 1: approximately **1.5R or better**
- Target 2: approximately **2R or better** when structure supports it

If a reasonable target cannot be identified, return **NO TRADE** rather than forcing an entry.

---

# Explanation Engine — Mandatory

Every recommendation must explain the decision.

The engine must answer:

1. **Why this stock?**
2. **Why BUY / SELL / WATCH / NO TRADE?**
3. **What confirms the setup?**
4. **What is the entry?**
5. **Where is the stop loss?**
6. **What are the targets?**
7. **What is the risk/reward?**
8. **What invalidates the setup?**

The explanation must be generated from the actual conditions that caused the decision. It must not be a generic template that claims confirmations that did not occur.

### Example BUY Alert

```text
🔔 BUY SETUP

Stock: HDFCBANK
Setup Score: 89/100
Setup Type: Breakout

WHY THIS STOCK?
✓ Banking is one of today's strongest sectors
✓ HDFCBANK is outperforming the sector
✓ 5m trend is bullish
✓ Price is above VWAP
✓ EMA structure is bullish
✓ RSI is in a healthy bullish range
✓ MACD is bullish
✓ Relative volume is elevated
✓ Resistance breakout is confirmed

WHY BUY NOW?
The resistance level has been broken with a confirmed
1-minute close and supporting volume.

TRADE PLAN
Entry: ₹X
Stop Loss: ₹X
Target 1: ₹X
Target 2: ₹X
Risk/Reward: 1:2.0

INVALIDATION
The BUY setup is invalid if the breakout fails and price
moves back below the defined invalidation level.
```

### Example WATCH

```text
INFY — WATCH

Score: 84/100

✓ IT sector strong
✓ Trend bullish
✓ Above VWAP
✓ RSI healthy
✓ Volume increasing

⚠ Resistance has not been broken.

ACTION: WAIT

Trigger:
Break above the defined resistance with confirmation.
```

### Example NO TRADE

```text
AXISBANK — NO TRADE

Score: 58/100

✓ Banking sector strong
✓ Price above EMA20
✗ Below VWAP
✗ MACD bearish
✗ Weak volume
✗ No clear setup
✗ Risk/reward poor

ACTION: NO TRADE
```

The engine must be able to explain why it **rejected** a stock, not only why it selected one.

---

# Signal State Machine

Each monitored stock maintains a state:

```text
NO_SETUP
   ↓
WATCH
   ↓
SETUP_FORMING
   ↓
TRIGGER_NEAR
   ↓
BUY / SELL
   ↓
ACTIVE
   ↓
TARGET / STOP / EXIT
```

If a setup becomes invalid before entry:

```text
SETUP_FORMING
      ↓
INVALIDATED
      ↓
NO_SETUP
```

This prevents duplicate alerts and makes the monitoring engine stateful.

---

# Module 9 — Telegram Alerts

Telegram alerts should be sent when a meaningful event occurs, such as:

- New BUY signal
- New SELL signal
- Setup reaches its configured alert threshold
- Existing setup materially changes
- Trade reaches target
- Trade reaches stop loss
- Setup becomes invalid

Initial alert preference from the project specification:

> Confidence above approximately **85** is a preferred threshold for high-priority BUY/SELL alerts, but the final alert threshold must also respect the mandatory setup/trigger/risk rules.

### Example

```text
BUY ALERT

Stock: INFY
Price: ₹1650
Confidence: 94

Reasons:
✅ Above VWAP
✅ Strong sector
✅ Volume spike
✅ Breakout
✅ RSI strong

Target: ₹1685
Stop Loss: ₹1628
```

The production alert should include the richer explanation defined by the Explanation Engine.

---

# Module 10 — Streamlit Dashboard

The dashboard should provide a professional, clear view of the entire workflow.

## Required sections

### 1. Market Overview

- NIFTY
- BANKNIFTY
- India VIX
- Market sentiment
- Advance/Decline

### 2. Strongest Sectors

- Sector ranking
- Sector score
- Relative strength
- Participation/breadth

### 3. Top Intraday Opportunities

- Rank
- Stock
- Sector
- Score
- Setup
- State
- Entry/SL/targets when applicable
- Explanation

### 4. User Watchlist / Live Monitoring

- Selected stocks
- Current price
- Trend
- Setup state
- Latest analysis
- Last update time

### 5. Live Alerts

- Recent BUY/SELL alerts
- Reason summary
- Entry/SL/targets
- Invalidation

### 6. Swing Opportunities

- Top swing candidates
- Setup
- Score
- Entry
- Stop Loss
- Targets

### 7. Recent Trades

- Signal
- Entry
- Exit
- Result
- Reason

### 8. Performance Statistics

- Win rate
- Profit factor
- Average profit
- Average loss
- Maximum drawdown
- Sharpe ratio

### 9. Backtest Results

- Strategy
- Date range
- Total trades
- Performance metrics
- Downloadable report

Plotly should be used for interactive charts.

---

# Module 11 — Swing Trading Engine

Swing trading is part of the planned product scope but is secondary to the initial intraday implementation.

Higher timeframes:

- 1-hour
- 4-hour
- Daily
- Weekly

Indicators:

- EMA20
- EMA50
- EMA200
- RSI
- MACD
- Supertrend

Generate:

- Entry
- Stop Loss
- Target 1
- Target 2
- Setup/Confidence Score
- Explanation

Initial holding period:

**3–30 days**

The swing engine should use the same principles as intraday: market/sector context, setup confirmation, risk/reward, explanation, and state management.

---

# Module 12 — Backtesting and Performance Analysis

The system must support historical strategy testing before real-money use.

Required metrics:

- Total trades
- Win rate
- Profit factor
- Average profit
- Average loss
- Maximum drawdown
- Sharpe ratio

Generate a downloadable performance report.

Backtesting should eventually support:

- Strategy selection
- Date range
- Timeframe
- Entry/exit rules
- Slippage
- Brokerage/transaction costs
- Position sizing
- Performance by setup type
- Performance by sector
- Performance by time of day

The system should store the reasoning behind historical signals so that the user can determine **which setups actually work**, rather than optimizing blindly.

---

# Trade Recording and Learning Loop

Every generated setup and trade should be recordable:

```text
Signal Generated
      ↓
Entry
      ↓
Price Movement
      ↓
Target / Stop / Manual Exit
      ↓
Trade Closed
      ↓
Result Stored
      ↓
Performance Analysis
```

Future analysis should answer:

- Which setups work best?
- Which sectors work best?
- Which timeframes work best?
- Breakout vs pullback performance
- Long vs short performance
- Time-of-day performance
- False breakout rate
- Average R multiple
- Drawdown

No strategy should be declared successful without sufficient historical and paper-trading evidence.

---

# Development Approach

Development should happen **module-by-module**, while keeping the architecture coherent.

For each implementation module:

1. Define the purpose and inputs/outputs.
2. Implement production-quality code.
3. Add logging.
4. Add error handling.
5. Add tests.
6. Verify expected output.
7. Update documentation.
8. Commit changes to GitHub.

The first implementation module should be the **Market Data Engine**, but application code should only begin after the product/strategy specification is agreed.

---

# V1 Scope vs Future Scope

## V1

- Market analysis
- Sector strength ranking
- Stock ranking
- User-selected watchlist
- 1-minute intraday monitoring
- 1m / 5m / 15m / 1h analysis
- EMA, RSI, VWAP, MACD, Supertrend, relative volume
- Breakout/breakdown setups
- Bullish/bearish pullbacks
- BUY / SELL / WATCH / NO TRADE
- Setup quality scoring
- Entry / SL / targets / risk-reward
- Mandatory explanations
- Signal state management
- Telegram alerts
- Streamlit dashboard foundation
- SQLite trade records
- Backtesting foundation

## Later

- Additional pattern types
- More trading styles
- Advanced market breadth
- More data providers
- PostgreSQL
- Advanced backtesting/walk-forward optimization
- Paper trading integration
- Strategy optimization based on recorded results
- Additional notification channels
- Advanced performance analytics
- Additional risk-management models

---

# Safety, Risk and Validation

This tool is for **educational and decision-support purposes only**.

It must not:

- Claim guaranteed profits
- Claim guaranteed winning trades
- Present a setup score as a win probability
- Force a trade when evidence is insufficient

Before real-money use, strategies must be evaluated using:

- Historical backtesting
- Walk-forward testing
- Realistic slippage
- Brokerage/transaction costs
- Paper trading
- Drawdown analysis
- Sufficient sample size

A strong score means **strong alignment with the defined technical criteria**, not a guarantee that price will move in the expected direction.

---

# Current Status

**Phase:** Product and V1 strategy specification

**Implementation status:** Strategy and product requirements are being finalized before application development.

**Development rule:** Do not add application code simply to demonstrate progress. First make sure the behavior is understood and documented, then implement it module-by-module and validate each module.

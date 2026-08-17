# Trading Assistant

A trading decision-support tool designed to help users identify tradable opportunities, monitor selected stocks in real time, and receive explainable BUY/SELL alerts.

> **V1 scope:** The first version focuses on market and sector strength, stock selection, user-controlled monitoring, 1-minute intraday monitoring, explainable setups, risk/reward, and alert state management. Advanced capabilities can be added later.

## Product Goal

The core workflow is:

```text
Market
  ↓
Market Analysis
  ↓
Sector Ranking
  ↓
Stock Ranking
  ↓
User Selects Stocks
  ↓
1-Minute Monitoring
  ↓
Multi-Timeframe Analysis
  ↓
Pattern + Indicator Analysis
  ↓
Setup Detection
  ↓
Confirmation + Risk/Reward
  ↓
BUY / SELL / WATCH / NO TRADE
  ↓
Detailed Explanation
  ↓
Alert + Trade Record
```

The tool is intended to support different trading styles over time, beginning with intraday trading and allowing swing/positional modes to be added later.

## V1 Workflow

### 1. Market Analysis

During market hours the engine evaluates the overall market using:

- NIFTY
- BANKNIFTY
- India VIX / volatility conditions
- Market breadth (Advance/Decline)
- Market momentum

Initial market classification:

| Score | Classification |
|---|---|
| 80–100 | Strong Bullish |
| 65–79 | Bullish |
| 45–64 | Neutral |
| 30–44 | Bearish |
| 0–29 | Strong Bearish |

The market score represents the current technical environment; it is not a prediction or guaranteed probability of profit.

### 2. Sector Ranking

The engine first identifies where the strongest market activity is occurring. Initial sectors include:

- IT
- Banking
- Auto
- Pharma
- FMCG
- Energy
- Metals
- Realty
- PSU

Initial sector strength score:

| Factor | Points |
|---|---:|
| Sector trend | 25 |
| Relative performance vs NIFTY | 25 |
| Volume participation | 20 |
| Sector breadth | 20 |
| Momentum | 10 |
| **Total** | **100** |

The strongest sectors become the first filter for stock discovery.

### 3. Stock Ranking

Stocks inside the stronger sectors are ranked using:

| Factor | Points |
|---|---:|
| Trend alignment | 20 |
| Relative strength | 15 |
| Price vs VWAP | 10 |
| RSI | 10 |
| MACD | 10 |
| Volume | 15 |
| Price action | 10 |
| Breakout/setup | 10 |
| **Total** | **100** |

The tool must explain **why a stock was selected** rather than simply displaying a score.

### 4. User-Controlled Watchlist

The engine may suggest stocks, but the user selects which stocks to monitor.

Once selected, those stocks enter the live monitoring engine.

### 5. One-Minute Intraday Monitoring

Selected stocks are refreshed and analyzed every **1 minute** during market hours.

Important rule:

> **1-minute refresh does not mean a new alert every minute.**

The engine maintains the state of each setup and only sends a new alert when a meaningful setup or signal state changes.

## Multi-Timeframe Analysis

V1 uses multiple timeframes for different purposes:

| Timeframe | Purpose |
|---|---|
| 1-minute | Entry/trigger monitoring |
| 5-minute | Primary intraday setup and structure |
| 15-minute | Trend confirmation |
| 1-hour | Larger market/stock context |

Conceptually:

```text
1H  → Context
15m → Direction confirmation
5m  → Setup
1m  → Entry trigger
```

## Technical Analysis Engine

V1 uses the following indicators as supporting evidence rather than isolated BUY/SELL triggers:

### EMA

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

### VWAP

Bullish intraday environment:

- Price above VWAP
- Preferably VWAP rising
- Pullbacks respecting VWAP strengthen the setup

Bearish intraday environment:

- Price below VWAP
- Preferably VWAP falling
- Retests rejecting VWAP strengthen the setup

### RSI

RSI is used as momentum context, not as a standalone signal.

- 55–70: healthy bullish momentum
- 60–70: strong bullish momentum
- Above 70: strong momentum but possible late-entry risk
- 30–45: bearish momentum
- Below 30: extreme weakness; does not automatically mean BUY

### MACD

Bullish confirmation:

- MACD above signal
- Positive/increasing histogram
- Stronger when aligned with the broader trend

Bearish confirmation:

- MACD below signal
- Negative/increasing bearish histogram
- Stronger when aligned with the broader trend

### Supertrend

- Bullish Supertrend supports BUY setups
- Bearish Supertrend supports SELL setups
- Conflicting Supertrend reduces setup confidence

### Relative Volume

Initial classification:

| Relative Volume | Interpretation |
|---|---|
| < 0.8x | Weak |
| 0.8–1.2x | Normal |
| 1.2–1.5x | Elevated |
| 1.5–2.0x | Strong |
| > 2.0x | Very strong |

For breakout setups, volume of approximately **1.5x or higher** is preferred as confirmation. The final implementation should make the volume baseline session-aware.

## V1 Setup / Pattern Engine

The first version focuses on a small number of understandable setups.

### Breakout — BUY

Typical confirmation:

1. Clear resistance exists.
2. Price approaches the resistance.
3. Candle closes above resistance.
4. Volume expands.
5. 5-minute structure supports the move.
6. Market and sector context are not strongly against the trade.

### Breakdown — SELL

Typical confirmation:

1. Clear support exists.
2. Price approaches the support.
3. Candle closes below support.
4. Volume expands.
5. 5-minute structure confirms weakness.
6. Market and sector context are not strongly against the trade.

### Bullish Pullback — BUY

Typical confirmation:

1. Strong bullish trend exists.
2. Price pulls back toward EMA20, VWAP, or support.
3. Selling pressure decreases.
4. Bullish reversal candle/structure appears.
5. Volume confirms recovery.

### Bearish Pullback — SELL

Typical confirmation:

1. Strong bearish trend exists.
2. Price rallies toward EMA20, VWAP, or resistance.
3. Buying pressure weakens.
4. Bearish rejection appears.
5. Volume confirms weakness.

### Consolidation — WATCH / NO TRADE

If price is moving sideways without a meaningful confirmed breakout or breakdown, the engine should not force a trade.

## Decision States

V1 has four primary user-facing states:

| State | Meaning |
|---|---|
| 🟢 **BUY** | Confirmed bullish trade setup |
| 🔴 **SELL** | Confirmed bearish trade setup |
| 🟡 **WATCH** | Interesting setup, but entry trigger is not confirmed |
| ⚪ **NO TRADE** | Conditions are insufficient or risk is unacceptable |

**WAIT is a valid decision.** The system should never be forced to generate a trade.

## BUY Decision Rules

A BUY should require a confirmed setup rather than one indicator crossing a threshold.

Required areas include:

- Acceptable/strong sector context
- Market not strongly bearish against the setup
- Bullish 5-minute structure/setup
- Confirmed 1-minute trigger
- Supporting price action
- Acceptable risk/reward

Supporting evidence may include:

- Price above VWAP
- Bullish EMA structure
- RSI in a healthy bullish range
- Bullish MACD
- Bullish Supertrend
- Elevated/strong relative volume
- Confirmed breakout or bullish pullback

## SELL Decision Rules

A SELL should require a confirmed bearish setup.

Required areas include:

- Acceptable/weakening sector context
- Market not strongly bullish against the setup
- Bearish 5-minute structure/setup
- Confirmed 1-minute trigger
- Supporting bearish price action
- Acceptable risk/reward

Supporting evidence may include:

- Price below VWAP
- Bearish EMA structure
- RSI in a bearish range
- Bearish MACD
- Bearish Supertrend
- Elevated/strong relative volume
- Confirmed breakdown or bearish pullback

## Setup Score

The V1 setup score is a **quality score**, not a probability of winning.

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

| Score | State |
|---|---|
| 0–60 | NO TRADE |
| 61–75 | WATCH / Moderate |
| 76–85 | Good Setup |
| 86–92 | High Quality |
| 93–100 | Very High Quality |

**Score alone must never trigger a trade.** A high-scoring stock remains WATCH until its actual entry trigger is confirmed.

## Entry, Stop Loss and Targets

### Entry

The entry is based on the specific setup and confirmed trigger, not a fixed percentage or a single indicator.

### Stop Loss

Stop loss should be structure-based:

- Breakout: below the breakout level/retest low or relevant structural swing low
- Pullback: below the pullback low/support
- SELL setups: the equivalent structural level above the setup

ATR should be used as a sanity check so stops are not unrealistically tight.

### Targets

Targets should consider:

- Risk/reward
- Nearby resistance/support
- ATR
- Previous swing levels

Initial preference:

- Target 1: at least approximately 1.5R
- Target 2: approximately 2R or better when market structure supports it

If a reasonable target cannot be identified, the engine should return **NO TRADE** rather than force an entry.

## Explanation Engine — Mandatory

Every BUY, SELL, WATCH, and NO TRADE recommendation must explain the decision.

The engine must answer:

1. **Why this stock?**
2. **Why BUY/SELL/WATCH/NO TRADE?**
3. **What confirms the setup?**
4. **What is the entry?**
5. **Where is the stop loss?**
6. **What are the targets?**
7. **What is the risk/reward?**
8. **What invalidates the setup?**

Example BUY explanation:

```text
HDFCBANK — BUY

Setup Score: 89/100
Setup Type: Breakout

WHY THIS STOCK?
✓ Strong banking sector
✓ Stock outperforming its sector
✓ Bullish 5m structure
✓ Price above VWAP
✓ EMA alignment bullish
✓ RSI healthy
✓ MACD bullish
✓ Relative volume elevated
✓ Resistance breakout confirmed

WHY BUY NOW?
The resistance level has been broken with a confirmed
1-minute close and supporting volume.

RISK
Entry: ₹X
Stop Loss: ₹X
Target 1: ₹X
Target 2: ₹X
Risk/Reward: 1:2.0

INVALIDATION
The BUY setup is invalidated if the breakout fails and
price moves back below the defined invalidation level.
```

The explanation should be generated from the actual conditions that caused the decision. It must not use a generic explanation that does not match the detected setup.

## WATCH Example

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

## NO TRADE Example

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

The engine must be able to explain why it rejected a stock, not only why it selected one.

## Signal State Machine

To prevent repeated alerts and noisy signals, each monitored stock maintains a setup state:

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

The system must not send the same BUY/SELL alert every minute. A new alert should be generated only when a meaningful signal state or trade condition changes.

## V1 Monitoring Architecture

```text
                    MARKET
                       ↓
                MARKET ANALYSIS
                       ↓
                SECTOR RANKING
                       ↓
                 STOCK RANKING
                       ↓
              USER SELECTS STOCK
                       ↓
               1-MIN MONITORING
                       ↓
              MULTI-TIMEFRAME DATA
                       ↓
               INDICATOR ENGINE
                       ↓
                PATTERN ENGINE
                       ↓
                 SETUP ENGINE
                       ↓
               CONFIRMATION
                       ↓
                 RISK ENGINE
                       ↓
             ┌─────────┼─────────┐
             ↓         ↓         ↓
           BUY       WATCH      SELL
             │         │         │
             └─────────┼─────────┘
                       ↓
             EXPLANATION ENGINE
                       ↓
              DASHBOARD + ALERT
                       ↓
                 TRADE RECORD
```

## Future Expansion

The architecture should allow additional trading modes and capabilities later, including:

- Swing trading
- Positional trading
- More pattern types
- Backtesting
- Walk-forward testing
- Paper trading
- Trade performance analytics
- Strategy optimization based on recorded outcomes
- Additional data sources and market analytics
- More notification channels

These are **future additions**, not requirements for V1.

## Risk and Validation

This tool is a decision-support system, not a guarantee of profitable trades. Before real-money use, strategies should be validated through historical backtesting, walk-forward testing, realistic transaction costs/slippage, and paper trading.

The engine should record signals and outcomes so that performance can be measured objectively over time.

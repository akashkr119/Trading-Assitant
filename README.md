# Trading Assistant

A decision-support platform for Indian markets covering intraday equities, crypto intraday research, long-term fundamental research, IPO intelligence, and live/paper monitoring. It connects to supported market-data providers, validates data, analyzes opportunities, and produces explainable BUY / SELL / WATCH / NO-TRADE decisions.

> **Safety:** V1 does not place orders. It is for decision support, research, live/paper testing, and education—not a guaranteed-profit system.

## V1 Features

### 📈 NSE Intraday
- Groww and Upstox market-data adapters
- Broker connection/session layer
- 1-minute monitoring during NSE regular hours
- 1m / 5m / 15m / 1h technical confirmation
- EMA, MACD, RSI, Supertrend, VWAP and volume analysis
- Breakout, pullback, cross and VWAP setup detection
- Risk/reward, stop-loss, target and invalidation calculation
- Explainable signals and duplicate-alert suppression
- Locked entry / stop / target trade plans
- Live price and P/L monitoring
- Alert history and outcome tracking

### 🪙 Crypto Intraday
- Crypto opportunity scanner
- Ranked intraday setups
- Multi-timeframe confirmation
- Confluence-based signal presentation
- Locked trade-plan display so live price changes do not rewrite the original entry/SL/targets

### 🏆 Long-Term Investment
- Verified-fundamental research workflow
- Sector-relative scoring
- Top 10 opportunities independently ranked within each sector
- Growth, profitability, debt, cash-flow and valuation analysis
- Confidence scoring when data is incomplete
- Investment thesis, risks and thesis-break conditions
- Missing financial data is shown as N/A rather than treated as zero

### 🆕 IPO Center
- Current IPO discovery feed with safe fallback behavior
- Mainboard / SME opportunity board
- Issue structure and fresh-issue vs OFS analysis
- Valuation and fundamental assessment
- Company Intelligence section covering:
  - What the company does
  - Business model
  - Goals
  - Future plans
  - Growth drivers
  - IPO fund usage
  - Critical risks
  - Research/source basis

### 🎨 Product UI
- Shared premium dark fintech visual system
- Responsive desktop, tablet and mobile layouts
- Adaptive typography and spacing
- Overflow-safe metrics and long text
- Consistent BUY / SELL / warning visual hierarchy

## V1 Architecture

```text
Market / Broker / Public Data
          ↓
     Data Providers
          ↓
       Validation
          ↓
   Scanner / Fundamentals
          ↓
 Multi-Timeframe / Sector Analysis
          ↓
      Decision Engine
          ↓
 Risk / Reward / Explanation
          ↓
 Alert / Journal / Dashboard
```

## Current V1 Status

The V1 application is operational and the repository is maintained through a **Build → Test → Ruff → CI Green → Continue** workflow. The application intentionally separates live market information from locked trade-plan values so a changing market price does not silently rewrite an already-generated trading plan.

The system remains conservative around missing data. Market/sector intelligence is not treated as authoritative until dedicated data sources are connected, and long-term scoring does not convert unavailable fundamentals into zero values.

## 🚀 V2 Roadmap

V2 will evolve Trading Assistant from a collection of scanners into a complete **market-intelligence → decision → validation → learning** platform.

### Phase 1 — Market Intelligence

#### 🧠 Market Brain
A daily market command center that explains the current environment:
- NIFTY / BANKNIFTY trend
- India VIX and volatility regime
- Advance / Decline breadth
- Volume regime
- FII / DII activity where reliable data is available
- Global-market context
- Important events
- Bullish / Neutral / Bearish / High-Volatility market regime
- Plain-language explanation of why the regime was assigned

#### 🏭 Sector Rotation Engine
- Sector momentum score
- Relative strength
- Trend and volume participation
- Strongest / weakest sectors
- Sector → strongest stocks workflow

#### 🚦 WAIT / NO-TRADE Engine
Signals will not be forced into BUY or SELL.
- 🟢 BUY
- 🔴 SELL
- 🟡 WAIT / setup forming
- ⚪ NO TRADE
- Explicit reasons for every WAIT / NO-TRADE decision

#### 🎯 Setup Lifecycle
Track an opportunity from:

```text
WATCH → FORMING → NEAR TRIGGER → CONFIRMED → ACTIVE → TARGET / EXIT
```

### Phase 2 — Validation & Learning

#### 📊 Backtesting Lab
- Strategy configuration
- Historical testing
- Win rate
- Profit factor
- Expectancy
- Average win / loss
- Maximum drawdown
- Sharpe-style risk metrics
- Long vs short analysis
- Sector performance
- Market-regime performance

#### 🧪 Paper Trading
- Virtual capital
- Position tracking
- Real-time simulated P/L
- Entry / SL / target tracking
- Portfolio statistics
- No real order placement

#### 📔 Trade Journal & Performance Analytics
Automatically record:
- Symbol and sector
- Market regime
- Setup and indicators
- Entry / stop / targets
- Score and confidence
- Outcome and R multiple
- Holding time

Then identify which setups actually work best.

### Phase 3 — Risk Intelligence

#### 🛡️ Position Sizing
- Account-based risk per trade
- Risk/share
- Recommended quantity
- Maximum loss
- Risk/reward constraints

#### 📉 Portfolio Risk
- Sector concentration
- Correlated positions
- Maximum simultaneous risk
- Daily loss limits
- Drawdown protection
- Trading halt / kill-switch controls

#### 🔬 Market-Regime Analytics
Measure every strategy under:
- Bull trend
- Bear trend
- Sideways market
- High-volatility conditions

The objective is to know **when a strategy should not be used**, not just its average win rate.

### Phase 4 — AI & Research Intelligence

#### 🤖 Explainable Trade Intelligence
Every signal should answer:
- Why this stock?
- Why this direction?
- Which indicators confirm it?
- Which indicators disagree?
- What is the risk?
- What would invalidate the thesis?

#### 📰 News & Event Intelligence
- Results
- Dividends
- Corporate actions
- Regulatory announcements
- Major company news
- Event-risk warnings around setups

#### 🧠 Personal Trading Coach
Use the journal to identify recurring strengths, weaknesses and setup-specific performance.

#### 🧪 Strategy Builder
Convert rules such as:

```text
EMA 9 > EMA 20
AND RSI > 50
AND MACD histogram > 0
AND RVOL > 1.5
```

into testable strategies that can move through:

```text
Build → Backtest → Paper Trade → Evaluate
```

### Phase 5 — Alerts & Controlled Execution

#### 🔔 Alert Center
Centralize:
- BUY confirmations
- SELL confirmations
- Setup-forming alerts
- Target hits
- Stop-loss events
- Invalidated setups

Potential future delivery channels include browser notifications, email and Telegram.

#### 🤝 Controlled Broker Execution
Real order execution is deliberately last. If introduced, it should require:
- Explicit user confirmation
- Position/risk checks
- Full audit logging
- Kill switch
- Safe failure behavior
- Compliance review

## V2 Design Principle

The goal is **not** to build a tool that always generates a trade.

The goal is to build a system that can say:

> **What is happening → where opportunity is strongest → why the setup qualifies → what the risk is → when to wait → what happened afterward.**

That makes the system useful for research, disciplined paper trading, and measurable strategy development rather than blindly following signals.

## Quick Start

1. Install Python 3.11+.
2. Install the project and development dependencies.
3. Set the required broker access token as an environment variable.
4. For Upstox, also configure `UPSTOX_INSTRUMENT_KEYS`.
5. Start the dashboard:

```bash
streamlit run app.py
```

6. Connect the broker and use the relevant scanner/research page.

## Development

Development follows:

```text
Build → Test → Ruff → CI Green → Continue
```

Before merging a feature:

```bash
ruff check .
pytest -q
```

## V2 Priorities

| Priority | Feature | Goal |
|---|---|---|
| 1 | Market Brain | Understand the market before selecting stocks |
| 2 | Sector Rotation | Find where strength is concentrated |
| 3 | WAIT / NO-TRADE | Prevent forced signals |
| 4 | Setup Lifecycle | Track setups from formation to outcome |
| 5 | Backtesting Lab | Validate strategies before deployment |
| 6 | Paper Trading | Validate live behavior without capital risk |
| 7 | Trade Journal | Learn which setups actually work |
| 8 | Risk Engine | Control position and portfolio risk |
| 9 | AI / News Intelligence | Improve explanation and context |
| 10 | Controlled Execution | Only after validation and safety controls |

## What V1 Does Not Promise

- No guaranteed returns
- No prediction certainty
- No automatic order placement
- No replacement for investor due diligence
- No assumption that missing data is zero

**V2 should make the system more explainable, measurable and risk-aware—not simply more aggressive.**

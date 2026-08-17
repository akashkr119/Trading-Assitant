# Trading Assistant

A decision-support tool for Indian stock-market trading, focused initially on **intraday trading**.

The goal is simple: when the market is open, the tool identifies strong market/sector conditions, finds the most promising stocks, lets the user choose which stocks to monitor, analyzes them every minute, and produces explainable BUY/SELL/WATCH/NO-TRADE signals.

> **Important:** This is a trading decision-support system, not a guaranteed-profit system. Signals must be validated with backtesting and paper trading before real-money use.

## What the Tool Does

### 1. Finds strong sectors

The tool evaluates the market and compares sectors to determine where trading strength and participation are concentrated.

### 2. Finds strong stocks inside those sectors

Stocks are ranked using technical and market-context factors such as:

- Trend
- Relative strength
- Volume
- VWAP
- EMA structure
- RSI
- MACD
- Supertrend
- Price action
- Breakout/pullback conditions
- Sector and market context

The tool must explain **why a stock was selected instead of simply giving a stock name**.

### 3. User selects the stocks

The engine suggests candidates, but the user remains in control of which stocks are placed into the active watchlist.

### 4. Monitors selected stocks every minute

During market hours, selected stocks are refreshed and analyzed on a 1-minute cycle.

The monitoring system is designed to avoid repeatedly sending the same signal every minute. A new alert is generated when the trading state meaningfully changes.

### 5. Uses multiple timeframes

The system combines timeframes for different purposes:

```text
1 Hour  → Larger context
15 Min  → Direction confirmation
5 Min   → Setup / structure
1 Min   → Entry trigger / monitoring
```

### 6. Generates trade decisions

The current decision states are:

- 🟢 **BUY** — confirmed bullish setup
- 🔴 **SELL** — confirmed bearish setup
- 🟡 **WATCH** — setup is developing but not confirmed
- ⚪ **NO TRADE** — conditions are insufficient or risk is unacceptable

### 7. Explains every actionable signal

A signal should explain:

- Why this stock
- Why this sector
- Why BUY or SELL
- Market condition
- Detected setup/pattern
- Indicator confirmations
- Entry
- Stop loss
- Targets
- Risk/reward
- Invalidation condition

### 8. Alerts the user

The alert system is separated from the trading logic so notification channels can be added independently, such as dashboard notifications, Telegram, email, or mobile notifications.

### 9. Supports multiple brokers

The architecture is broker-independent. The current direction is to support:

- **Groww**
- **Upstox**
- **Zerodha** (planned)
- Additional brokers later

Users should ultimately be able to choose **Connect Broker** instead of manually dealing with internal API configuration.

## How It Works

```text
Market Open
    ↓
Market Analysis
    ↓
Sector Ranking
    ↓
Stock Ranking
    ↓
Candidate Suggestions
    ↓
User Selects Stocks
    ↓
Active Watchlist
    ↓
1-Minute Monitoring
    ↓
Multi-Timeframe Analysis
    ↓
Indicator + Price Action Analysis
    ↓
Setup Detection
    ↓
Trade Decision
    ↓
Risk / Reward Check
    ↓
Detailed Explanation
    ↓
Alert
    ↓
Notification
```

## Current Development Status

Development is being done **incrementally**, one module at a time.

Each step is implemented in the GitHub repository, tests are added, Ruff/lint issues are fixed, and GitHub Actions must turn **green** before the step is considered complete.

### Implemented and validated

- Market-analysis foundation
- Sector-strength analysis
- Stock ranking
- Setup/pattern detection
- Candidate selection
- User watchlist
- 1-minute monitoring loop
- Alert model and alert types
- Full signal explanations
- Notification abstraction
- Signal → Alert → Notification integration
- Duplicate-alert suppression
- Analysis execution runner
- Provider-neutral market-data interface
- Upstox market-data adapter
- Environment-based runtime configuration
- Broker-independent connection architecture
- Groww broker connection foundation
- Automated tests and CI validation for the implemented modules

### Current development position

**Step 26 — Broker Connection Service** is implemented and currently awaiting final CI confirmation.

## What Is Left

The major remaining work is to turn the tested core into a complete user-facing trading application.

### 1. Complete broker authentication

Build the actual user flow:

```text
Connect Broker
      ↓
User authenticates with broker
      ↓
Authorization / token handling
      ↓
Connection verified
      ↓
Market data available
```

This should hide technical token/configuration details from normal users.

### 2. Complete real-time market-data integration

Connect the selected broker to the complete monitoring pipeline and verify real 1-minute Indian-market data in live market conditions.

### 3. Dashboard / user interface

Build the interface where users can see:

- Market condition
- Strong sectors
- Recommended stocks
- Stock analysis/reason
- Watchlist
- Live charts
- Indicators
- Current signal
- Entry / SL / targets
- Risk/reward
- Alert history

### 4. Live chart and monitoring experience

Show selected stocks with their live intraday charts and continuously updated analysis.

### 5. Backtesting

Before relying on signals with real money, test the strategies against historical data and measure:

- Win rate
- Profit/loss
- Drawdown
- Risk/reward
- Maximum consecutive losses
- Setup performance
- Sector performance
- Time-of-day performance

### 6. Paper trading

Run the complete system in simulated trading before enabling real order execution.

### 7. Trade journal and performance reporting

Store signals and outcomes so the system can learn which setups actually perform well.

### 8. Optional order execution

Only after the analysis, alerts, backtesting, and paper-trading layers are reliable, add optional broker order execution.

The initial product should remain **alert/decision-support first**, not automatically place trades.

### 9. Additional trading styles

After the intraday system is stable:

- Swing trading
- Positional trading
- Additional setups/patterns
- More brokers
- More advanced risk management

## Development Philosophy

The project is being built in small, testable stages rather than attempting the entire application at once.

The important rule is:

> **Build → Test → Fix → CI Green → Confirm → Continue**

This keeps the trading engine modular and makes it easier to validate each part before connecting it to real market data.

## Repository

GitHub: https://github.com/akashkr119/Trading-Assitant

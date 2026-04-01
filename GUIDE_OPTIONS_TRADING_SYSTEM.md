# Options Trading Decision Platform — Complete Guide for Beginners

> **Author:** Built for Sachin's personal use
> **Purpose:** A data-driven system to help make disciplined, profitable options trading decisions
> **Philosophy:** "Don't predict the market. React to what the data tells you."

---

## PART 1: THINGS YOU MUST UNDERSTAND BEFORE YOU TRADE

### 1.1 What Is an Option (Really)?

An option gives you the **right** (not obligation) to buy or sell a stock at a specific price before a specific date.

- **Call Option (CE):** You profit when the stock/index goes UP
- **Put Option (PE):** You profit when the stock/index goes DOWN
- **Strike Price:** The price at which you can buy/sell
- **Expiry:** The date the option expires (worthless if not in profit)
- **Premium:** The price you pay to buy the option — this is your maximum loss as a buyer

**Example:** Nifty is at 22,500. You buy a 22,600 CE (Call) for ₹100 premium. If Nifty goes to 22,800 before expiry, your option is worth ~₹200. You doubled your money. If Nifty stays below 22,600, you lose your ₹100 premium.

### 1.2 The Greeks — Why Options Prices Move

| Greek | What It Measures | Why You Care |
|-------|-----------------|--------------|
| **Delta** | How much option price moves per ₹1 move in stock | Higher delta = more responsive to stock movement |
| **Theta** | How much value the option loses per day | Options LOSE value every day — time is your enemy as a buyer |
| **Vega** | Sensitivity to volatility changes | High volatility = expensive options |
| **Gamma** | Rate of change of delta | Important near expiry — moves become extreme |

**Key Takeaway:** As an option buyer, **time decay (theta) works against you every single day**. You need the stock to move fast and in your direction.

### 1.3 The #1 Mistake Beginners Make

Buying far out-of-the-money (OTM) options because they're "cheap." They're cheap because they almost never become profitable. Start with at-the-money (ATM) or slightly OTM options.

---

## PART 2: CRITICAL RISK MANAGEMENT RULES

> **These rules are MORE important than any trading signal. Burn them into your system.**

### Rule 1: Fixed Capital Per Trade
- Never risk more than **2% of your total capital** on a single trade
- If you have ₹1,00,000 → max risk per trade = ₹2,000
- This means if your option costs ₹100, buy only 1 lot (or the quantity that keeps loss ≤ ₹2,000)

### Rule 2: Daily Loss Limit
- Set a maximum daily loss of **5% of capital**
- If you hit it, STOP trading for the day. No revenge trading.
- Your system should enforce this automatically

### Rule 3: Always Have a Stop Loss
- Before entering ANY trade, decide your exit price if it goes wrong
- Typical stop loss for options: **30-40% of premium paid**
- Example: Bought at ₹100 → stop loss at ₹60-70

### Rule 4: Book Profits Systematically
- Don't get greedy. Use target levels:
  - Target 1: 30-50% profit → exit half position
  - Target 2: 80-100% profit → exit remaining
- Trailing stop loss: once in 50%+ profit, move stop loss to entry price (risk-free trade)

### Rule 5: Position Sizing
- Never go "all in" on one trade
- Maximum 3 open positions at a time when starting out
- Diversify across different setups (trend, breakout, reversal)

### Rule 6: Paper Trade First
- Run your system in paper trading mode for at least 2-4 weeks
- Track every signal, every trade, every outcome
- Only go live when you see consistent results

---

## PART 3: TECHNICAL INDICATORS YOUR SYSTEM WILL USE

### 3.1 Trend Indicators

**Moving Averages (EMA 9, 21, 50, 200)**
- Price above EMA 21 → short-term bullish
- EMA 9 crosses above EMA 21 → buy signal
- Price below EMA 200 → long-term bearish (avoid buying calls)

**SuperTrend**
- Green = uptrend (buy calls)
- Red = downtrend (buy puts)
- Very reliable for trend-following

### 3.2 Momentum Indicators

**RSI (Relative Strength Index)**
- Below 30 → oversold (potential reversal up)
- Above 70 → overbought (potential reversal down)
- Best used with trend confirmation, not alone

**MACD (Moving Average Convergence Divergence)**
- MACD line crosses above signal line → bullish momentum
- Histogram growing → momentum strengthening

### 3.3 Volatility Indicators

**Bollinger Bands**
- Price touching lower band + RSI < 30 → potential buy
- Price touching upper band + RSI > 70 → potential sell
- Bands squeezing → big move coming (breakout setup)

**ATR (Average True Range)**
- Measures how much a stock typically moves
- Use for setting stop losses (e.g., stop loss = 1.5x ATR)

### 3.4 Volume Analysis

**VWAP (Volume Weighted Average Price)**
- Price above VWAP → buyers in control (bullish)
- Price below VWAP → sellers in control (bearish)
- Most important indicator for intraday trading

**OBV (On Balance Volume)**
- Rising OBV + rising price → trend confirmed
- Rising OBV + flat price → accumulation (breakout coming)

---

## PART 4: SIGNAL GENERATION STRATEGIES

### Strategy 1: Trend Following (Safest for beginners)
```
BUY CALL when:
  ✓ Price above EMA 21 AND EMA 50
  ✓ SuperTrend is green
  ✓ RSI between 40-65 (trending, not overbought)
  ✓ Volume above average

BUY PUT when:
  ✓ Price below EMA 21 AND EMA 50
  ✓ SuperTrend is red
  ✓ RSI between 35-60 (trending down, not oversold)
  ✓ Volume above average
```

### Strategy 2: Breakout Trading
```
BUY CALL when:
  ✓ Price breaks above resistance with high volume
  ✓ Bollinger Bands were squeezing (low volatility → expansion)
  ✓ RSI crossing above 60
  ✓ MACD histogram turning positive

BUY PUT when:
  ✓ Price breaks below support with high volume
  ✓ RSI crossing below 40
  ✓ MACD histogram turning negative
```

### Strategy 3: Reversal Trading (Advanced — use after experience)
```
BUY CALL when:
  ✓ RSI < 30 (oversold)
  ✓ Price at strong support level
  ✓ Bullish candlestick pattern (hammer, engulfing)
  ✓ Volume spike on the reversal candle

BUY PUT when:
  ✓ RSI > 70 (overbought)
  ✓ Price at strong resistance level
  ✓ Bearish candlestick pattern (shooting star, engulfing)
  ✓ Volume spike on the reversal candle
```

### Signal Confidence Scoring
Each signal gets a score out of 100 based on how many conditions are met:
- **80-100:** Strong signal → full position size
- **60-79:** Moderate signal → half position size
- **40-59:** Weak signal → skip or very small position
- **Below 40:** No trade

---

## PART 5: MARKET SENTIMENT ANALYSIS

### 5.1 India VIX (Fear Index)
- VIX < 13 → Low fear, good for option selling
- VIX 13-18 → Normal, good for option buying
- VIX > 20 → High fear, options very expensive, be cautious
- VIX > 25 → Panic, avoid buying options (premiums too high)

### 5.2 FII/DII Data
- FII buying + DII buying → strong bullish sentiment
- FII selling + DII buying → mixed (market may consolidate)
- FII selling + DII selling → bearish

### 5.3 Put-Call Ratio (PCR)
- PCR > 1.2 → Too many puts, market may bounce up (contrarian bullish)
- PCR < 0.7 → Too many calls, market may fall (contrarian bearish)
- PCR 0.8-1.0 → Neutral

### 5.4 News Sentiment
- Track financial news headlines for keywords
- Positive sentiment + technical buy signal → stronger conviction
- Negative news + technical sell signal → stronger conviction
- Conflicting signals → reduce position size or skip

---

## PART 6: SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                  OPTIONS TRADING PLATFORM                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  Market   │  │  News &  │  │  FII/DII │              │
│  │  Data     │  │ Sentiment│  │  & VIX   │              │
│  │ (Yahoo/   │  │ (RSS/    │  │  Data    │              │
│  │  NSE API) │  │  News)   │  │          │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       │              │              │                     │
│       ▼              ▼              ▼                     │
│  ┌──────────────────────────────────────┐               │
│  │        DATA PROCESSING ENGINE         │               │
│  │  • Clean & normalize data             │               │
│  │  • Calculate indicators (RSI, EMA...) │               │
│  │  • Detect patterns & levels           │               │
│  └──────────────────┬───────────────────┘               │
│                     │                                    │
│                     ▼                                    │
│  ┌──────────────────────────────────────┐               │
│  │        SIGNAL GENERATION ENGINE       │               │
│  │  • Apply strategies (trend/breakout)  │               │
│  │  • Score signals (0-100)              │               │
│  │  • Filter by market sentiment         │               │
│  └──────────────────┬───────────────────┘               │
│                     │                                    │
│                     ▼                                    │
│  ┌──────────────────────────────────────┐               │
│  │         RISK MANAGEMENT ENGINE        │               │
│  │  • Position sizing                    │               │
│  │  • Stop loss calculation              │               │
│  │  • Daily P&L tracking                 │               │
│  │  • Max loss enforcement               │               │
│  └──────────────────┬───────────────────┘               │
│                     │                                    │
│                     ▼                                    │
│  ┌──────────────────────────────────────┐               │
│  │            OUTPUT LAYER               │               │
│  │  • Dashboard (charts + signals)       │               │
│  │  • Telegram/Email alerts              │               │
│  │  • Trade journal (auto-logged)        │               │
│  └──────────────────────────────────────┘               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## PART 7: TECHNOLOGY STACK

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python | Best for data analysis, huge library ecosystem |
| Data Source | yfinance, NSE APIs | Free, reliable market data |
| Indicators | pandas-ta, ta-lib | Pre-built technical indicator calculations |
| Dashboard | Streamlit | Easy to build, Python-native, looks good |
| Charts | Plotly | Interactive, professional charts |
| Alerts | Telegram Bot API | Free, instant notifications on phone |
| Database | SQLite | Simple, no setup needed, stores trade history |
| Scheduling | APScheduler / cron | Run scans at market open, during session |

---

## PART 8: DEVELOPMENT PHASES

### Phase 1: Foundation (Week 1-2) ← START HERE
- Set up Python project
- Fetch market data (OHLCV) from yfinance
- Calculate basic indicators (EMA, RSI, MACD, Bollinger)
- Display a simple chart with indicators

### Phase 2: Signal Engine (Week 3-4)
- Implement Strategy 1 (Trend Following)
- Build signal scoring system
- Backtest on historical data
- Paper trading mode

### Phase 3: Risk Management (Week 5)
- Position sizing calculator
- Stop loss / take profit automation
- Daily P&L tracker
- Trade journal

### Phase 4: Sentiment & Alerts (Week 6-7)
- Add VIX, PCR, FII/DII data
- Basic news sentiment analysis
- Telegram alert bot
- Dashboard with Streamlit

### Phase 5: Advanced (Week 8+)
- Add more strategies (breakout, reversal)
- Machine learning signal enhancement
- Options chain analysis (OI, IV)
- Performance analytics & optimization

---

## PART 9: COMMON MISTAKES TO AVOID

1. **Over-optimization:** Don't tweak your strategy until it looks perfect on past data — it won't work in real markets (called "curve fitting")
2. **Ignoring theta:** As an option buyer, every day costs you money. Don't hold losing options hoping they'll recover
3. **Trading without a plan:** Every trade should have: entry price, stop loss, target, and position size BEFORE you enter
4. **Revenge trading:** Lost money? Don't try to "make it back" immediately. Walk away.
5. **Ignoring the trend:** "The trend is your friend." Don't buy calls in a falling market just because it "looks cheap"
6. **Too many indicators:** More indicators ≠ better signals. They often contradict each other. Pick 3-4 that complement each other
7. **No trade journal:** If you don't record your trades, you can't learn from them

---

## PART 10: DAILY WORKFLOW (How You'll Use This System)

```
8:30 AM  → System fetches pre-market data, VIX, global cues
9:15 AM  → Market opens. System starts scanning
9:30 AM  → First signals generated (wait 15 min for market to settle)
           → Check signal score, sentiment alignment
           → If score > 70 → evaluate trade
           → Calculate position size, set stop loss
           → Enter trade (manually on broker app)
Throughout → System monitors open positions
           → Alerts if stop loss hit or target reached
3:15 PM  → Market close. System logs all trades
           → Daily P&L summary
           → Journal entry auto-created
Weekend  → Review weekly performance
           → Adjust parameters if needed
```

---

*Remember: The goal is not to win every trade. The goal is to win MORE than you lose, and to lose SMALL when you're wrong. A 55% win rate with proper risk management can be very profitable.*

# Strategy Documentation

## Strategy v2 (Current — Optimized)

### Overview

The signal engine generates BUY_CALL or BUY_PUT signals using multiple strategies,
applies safety filters, and scores each signal 0-100. Only signals scoring >= 40 are shown.

**Performance (1-year backtest, 8 stocks):**
- Win Rate: **54.6%**
- Total P&L: **+66,461** on 1L capital
- 7 out of 8 stocks profitable

### Signal Pipeline

```
Raw Signal Generation (3 strategies)
    |
    v
Trend Filter (block counter-trend)
    |
    v
Volume Confirmation (+10 or -15)
    |
    v
RSI Safety Filter (penalize extremes)
    |
    v
VIX Modifier (warn on expensive options)
    |
    v
Confluence Scoring (+23 or -10)
    |
    v
Final Score Filter (>= 40 to show)
```

### Strategy 1: Trend Following

Trades in the direction of the established trend. Safest strategy.

| Condition | Points | Direction |
|-----------|--------|-----------|
| Price above EMA 21 | +15 | CALL |
| Price above EMA 50 | +15 | CALL |
| SuperTrend bullish | +17 | CALL |
| RSI in 45-65 zone | +15 | CALL |
| EMA 9/21 bullish crossover | +23 | CALL |
| MACD rising | +10 | CALL |
| (Inverse conditions) | (same) | PUT |

**Max possible score: 95**

### Strategy 2: Breakout Trading

Looks for price breaking out of consolidation with volume confirmation.

| Condition | Points | Direction |
|-----------|--------|-----------|
| Bollinger Band squeeze | +10 | Both |
| Breaking upper BB + volume | +25 | CALL |
| Breaking upper BB, no volume | +10 | CALL |
| RSI > 60 | +10 | CALL |
| MACD positive | +10 | CALL |
| Volume confirms | +15 | CALL |
| (Inverse conditions) | (same) | PUT |

**Max possible score: 70**

### Strategy 3: OI Analysis

Uses options chain data (PCR, OI buildup, max pain, IV skew).

| Condition | Points | Direction |
|-----------|--------|-----------|
| PCR > 1.2 | +25 | CALL |
| PCR > 1.0 | +15 | CALL |
| Fresh put writing | +20 | CALL |
| Call unwinding | +10 | CALL |
| Below max pain | +15 | CALL |
| Near OI support | +15 | CALL |
| Reverse IV skew | +10 | CALL |
| (Inverse conditions) | (same) | PUT |

**Max possible score: 95** (requires options chain data)

### Filters

#### 1. Trend Filter (most impactful)
- CALL signals **blocked** when price is below EMA 21 (downtrend)
- PUT signals **blocked** when price is above EMA 21 (uptrend)
- This single filter improved win rate from 35.8% to 54.6%

#### 2. Volume Confirmation
- Volume > 1.5x 20-day average: **+10 bonus**
- Volume > average: no change
- Volume below average: **-15 penalty**

#### 3. RSI Safety
- PUT when RSI < 30: **-25** (oversold bounce risk)
- PUT when RSI < 35: **-15** (near oversold)
- CALL when RSI > 70: **-25** (overbought reversal risk)
- CALL when RSI > 65: **-15** (near overbought)

#### 4. VIX Modifier
- VIX > 30: **-10** + warning (prefer selling strategies)
- VIX > 25: **-5** + warning (smaller positions)
- VIX > 20: warning only (wider stop losses)
- VIX < 13: **+5** bonus (options cheap)

#### 5. Confluence Scoring
- 2+ strategies agree on direction: **+23 bonus** each
- Only 1 strategy signal: **-10 penalty**

### Score Interpretation

| Score | Strength | Action |
|-------|----------|--------|
| 80-100 | STRONG | Full position size |
| 60-79 | MODERATE | Half position |
| 40-59 | WEAK | Quarter position or skip |
| < 40 | NO_TRADE | Signal filtered out |

### Exit Parameters (Optimized)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Stop Loss | 3% underlying move | Wide enough to avoid daily noise |
| Target | 2.3% underlying move | Small targets hit more frequently |
| R:R | 1:1.2 | Lower per-trade gain but 55%+ hit rate |
| Trailing SL | Disabled | Was cutting winners short |
| Max Hold | Disabled | Let SL/target do the work |

### Optimization History

**5-iteration walk-forward optimization:**
- Training: last 6 months, Validation: previous 6 months
- Each iteration analyzed trade failures and adjusted parameters

| Iteration | Train WR | Val WR | Val P&L | Key Change |
|-----------|----------|--------|---------|------------|
| 1 | 62.9% | 45.9% | -28,084 | Baseline |
| 2 | 62.8% | 48.4% | -24,416 | Lowered target |
| 3 | 65.0% | 53.7% | -20,976 | Reduced SuperTrend weight |
| 4 | 67.0% | 58.1% | -14,609 | Lowered target further |
| 5 | 66.9% | 59.7% | -13,700 | Tightened trail activation |

**Final parameter changes from optimization:**
- SuperTrend weight: 20 -> 17
- EMA cross weight: 20 -> 23
- Confluence bonus: 15 -> 23
- Target: 4.5% -> 2.3%
- Target R:R: 1.5 -> 1.2
- Trailing SL: Enabled -> Disabled

### Per-Stock Performance (1 year)

| Stock | Trades | Win Rate | P&L | Profit Factor | Verdict |
|-------|--------|----------|-----|---------------|---------|
| SBI | 25 | 64.0% | +21,400 | 2.31 | BEST |
| Reliance | 23 | 60.9% | +16,561 | 2.01 | GREAT |
| ITC | 22 | 59.1% | +13,769 | 1.81 | GREAT |
| TCS | 22 | 59.1% | +13,143 | 1.75 | GOOD |
| HDFC Bank | 16 | 62.5% | +11,360 | 1.93 | GOOD |
| BankNifty | 12 | 50.0% | +1,920 | 1.16 | OK |
| Nifty | 11 | 45.5% | +420 | 1.04 | BORDERLINE |
| Infosys | 32 | 37.5% | -12,113 | 0.70 | AVOID |

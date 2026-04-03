# Research: Parameters Used by Profitable Option Traders

Research conducted April 2026 from trading communities, research papers,
algo trading platforms (AlgoTest, Tradetron, Sensibull, Quantsapp), and
professional trader blogs.

---

## TIER 1: HIGH IMPACT (Must Implement)

### 1. IV Percentile Filter

**What:** Only buy options when Implied Volatility is in the lower percentile
of its historical range. IV is mean-reverting — cheap options tend to expand,
expensive options tend to contract.

**Rules:**
- IV Percentile < 25%: BUY options (cheap, likely to expand)
- IV Percentile 25-75%: Normal, use other signals
- IV Percentile > 75%: AVOID buying (expensive, likely to contract). Consider selling instead.

**Edge:** IV mean reversion is one of the most consistent edges in options trading.
Buying low-IV options gives you "volatility tailwind" — even if direction is flat,
IV expansion can make your option profitable.

**Source:** Charles Schwab research, Option Samurai, Barchart IV analytics

**Implementation:** Calculate 30-day IV percentile for each stock. Add to signal
scoring — penalize signals when IV is high (similar to our VIX filter but per-stock).

**Status: NOT IMPLEMENTED**

---

### 2. VWAP (Volume Weighted Average Price)

**What:** VWAP is the average price weighted by volume. Institutional traders
use VWAP as a reference — buying above VWAP means you're paying more than
the average institutional buyer.

**Rules:**
- Price sustains above VWAP: Bullish bias (institutions are long)
- Price sustains below VWAP: Bearish bias
- VWAP works best on 5-minute and 15-minute charts
- Cross of price through VWAP = potential entry

**Edge:** On BankNifty, VWAP + SuperTrend combined strategy reported 65%+ accuracy.
VWAP is superior to EMA for intraday because it accounts for volume.

**Source:** Rupeezy, Waves Strategy, Medium (VWAP + SuperTrend study)

**Implementation:** Add VWAP calculation to technical.py. Use as additional
trend filter alongside EMA 21 for intraday signals.

**Status: NOT IMPLEMENTED** (have VWAP_ENABLED flag in settings but not calculating)

---

### 3. OI Change Tracking (not just static OI)

**What:** Static OI snapshots are misleading. What matters is the CHANGE in OI
combined with price direction:

| Price | OI Change | Interpretation |
|-------|-----------|---------------|
| Rising | OI Rising | **Long Buildup** (Bullish) |
| Falling | OI Rising | **Short Buildup** (Bearish) |
| Rising | OI Falling | **Short Covering** (Weak Bullish) |
| Falling | OI Falling | **Long Unwinding** (Weak Bearish) |

**Rules:**
- Long Buildup = strongest bullish signal
- Short Buildup = strongest bearish signal
- Short Covering/Long Unwinding = don't initiate new trades (existing positions exiting)
- High OI WITHOUT volume = stale positions, don't trust as support/resistance

**Edge:** Professional Indian market traders track OI change every 3 minutes
during market hours. Fresh buildup at a strike = real institutional defense level.

**Source:** PL India, Groww advanced options analysis, Quantsapp

**Implementation:** Enhance chain.py to track OI change patterns and classify
as buildup/unwinding. Add to OI signal scoring.

**Status: PARTIALLY DONE** (have oi_change but not classifying the 4 patterns)

---

### 4. Max Pain Near Expiry

**What:** Max pain is the strike where option writers lose the least money.
Empirically, the spot price gravitates toward max pain as expiry approaches.

**Rules:**
- Most expiries settle within 100 points of max pain on Nifty
- Effect strongest in last 1-2 days before weekly expiry
- Don't trade max pain alone — combine with technicals
- Use for option SELLING strategies near expiry

**Edge:** Widely observed in Indian indices. Useful for weekly Thursday expiry trades.

**Source:** Groww, Strike.money, PL India

**Implementation:** Already have max pain calculation. Need to:
- Add expiry-day awareness (is it expiry day? 1 day before?)
- Increase max pain weight in signals when close to expiry
- Recommend option selling near max pain on expiry day

**Status: HAVE IT** but not using for trade timing based on DTE

---

### 5. Opening Range Breakout (ORB)

**What:** Define the high and low of the first N minutes after market open.
Trade the breakout direction when price breaks above the high or below the low.

**Timeframes tested:**
| ORB Window | Win Rate | Profit Factor | Notes |
|-----------|----------|---------------|-------|
| 15 min | ~55% | ~1.1 | Too many false breakouts |
| 30 min | ~62% | ~1.3 | Good balance |
| 60 min | **89.4%** | **1.44** | Best performer |

**Rules:**
- Wait for first 30-60 min candle to form (9:15-10:15 IST)
- BUY CALL if price breaks above the high
- BUY PUT if price breaks below the low
- Stop loss = opposite end of the range
- Target = 1.5x the range
- Only one trade per day per symbol

**Edge:** One of the most backtested strategies. 400% return reported in one study.
Works because the opening range captures overnight sentiment and early institutional flow.

**Source:** Trade That Swing (400% study), Quantified Strategies, Option Alpha

**Implementation:** Add new strategy `generate_orb_signal()` to generator.py.
Requires intraday data (5min/15min candles).

**Status: NOT IMPLEMENTED**

---

## TIER 2: MEDIUM IMPACT (Strong Improvement)

### 6. PCR Extreme Values (Contrarian)

**What:** Extreme PCR values predict reversals, not continuation.

**Rules:**
- PCR > 1.6 on Nifty: Excessive fear = likely rally coming (contrarian bullish)
- PCR < 0.6 on Nifty: Excessive greed = correction likely (contrarian bearish)
- Research: Extreme PCR predicts reversal **68% of the time** within 1 month

**Source:** Billingsley & Chance (1988), Journal of Portfolio Management

**Implementation:** Add contrarian PCR signal. When PCR is extreme, generate
a signal OPPOSITE to what PCR suggests (contrarian).

**Status: HAVE PCR** but using it directionally, not as contrarian

---

### 7. Volume + OI Validation

**What:** OI levels without volume are stale and unreliable.

**Rules:**
- Only trust support/resistance levels where OI AND volume are both high
- High OI + low volume = old positions, may not be defended
- High OI + high volume = active defense, trust this level

**Implementation:** Modify chain.py OI level detection to require minimum volume.

**Status: NOT CHECKING** volume alongside OI

---

### 8. Multi-Timeframe Analysis

**What:** Use higher timeframe for direction, lower timeframe for entry.

**Rules:**
- Daily chart: Determine trend direction (EMA, SuperTrend)
- 15-min chart: Find precise entry point (breakout, VWAP cross)
- Signal valid only when both timeframes agree

**Edge:** Standard institutional approach. Reduces false signals by 30-40%.

**Implementation:** Generate signals on daily, confirm entry on 15-min.
Requires fetching two timeframes for each symbol.

**Status: NOT IMPLEMENTED** (single timeframe only)

---

### 9. ADX (Average Directional Index)

**What:** Measures trend STRENGTH (not direction). Tells you if the market
is trending or range-bound.

**Rules:**
- ADX > 25: Strong trend — trade breakouts and trend following
- ADX 20-25: Developing trend — wait for confirmation
- ADX < 20: No trend (choppy) — SKIP trend signals, consider mean reversion

**Edge:** Avoids the biggest source of losses — trading trend strategies
in range-bound markets. Simple but very effective filter.

**Implementation:** Add ADX to technical.py indicators. Use as a filter
in signal generator — skip trend signals when ADX < 20.

**Status: NOT IMPLEMENTED**

---

### 10. Time of Day Filter

**What:** Certain times of day have much higher signal reliability.

**Rules for IST:**
| Time | Quality | Action |
|------|---------|--------|
| 9:15-9:30 | AVOID | Too volatile, opening noise |
| 9:30-10:30 | BEST | First hour momentum |
| 10:30-12:00 | GOOD | Trend continuation |
| 12:00-13:30 | AVOID | Lunch hour, low volume |
| 13:30-14:30 | GOOD | Afternoon trend |
| 14:30-15:15 | BEST | Last hour momentum |
| 15:15-15:30 | AVOID | Closing volatility |

**Edge:** Simple filter but eliminates 30%+ of losing trades that happen
during low-quality periods.

**Implementation:** Add time check to signal generation when using
intraday intervals.

**Status: HAVE market hours in settings** but not filtering signals by time

---

## TIER 3: REFINEMENT

### 11. Days to Expiry (DTE) Awareness

**Rules:**
- Buy weekly options 2-5 days before expiry (optimal theta/gamma)
- Avoid buying on expiry day (theta eats everything)
- Monthly options: enter 7-14 DTE for best value
- Factor DTE into position sizing (less capital on shorter DTE)

**Status: NOT FILTERING by DTE**

---

### 12. OI-Based Stop Loss Placement

**Rules:**
- Instead of fixed % SL, use highest OI strike as SL level
- Put sellers defend their strike — so highest put OI = real support
- If that level breaks, the trade thesis is invalidated

**Status: HAVE OI levels** but using fixed % for SL

---

### 13. Sector Rotation

**Rules:**
- Identify which sector is trending (IT, Banking, FMCG)
- Only trade stocks from the trending sector
- Avoid stocks in sectors showing weakness

**Status: NOT IMPLEMENTED**

---

### 14. FII/DII Flow Integration

**Rules:**
- FII buying + DII buying = strongest bullish confirmation
- Both selling = strongest bearish
- FII selling + DII buying = choppy, avoid

**Status: HAVE DATA** but not integrating into signal scoring

---

## Implementation Priority

Based on expected impact and implementation effort:

| Priority | Feature | Expected Impact | Effort |
|----------|---------|----------------|--------|
| 1 | IV Percentile filter | HIGH — most consistent edge | Medium |
| 2 | VWAP indicator | HIGH — institutional reference | Low |
| 3 | ORB strategy | HIGH — 89% WR reported | Medium |
| 4 | ADX trend strength | MEDIUM — eliminates choppy trades | Low |
| 5 | Time of day filter | MEDIUM — simple, effective | Low |
| 6 | OI change classification | MEDIUM — 4-pattern analysis | Low |
| 7 | PCR contrarian signals | MEDIUM — 68% reversal accuracy | Low |
| 8 | Multi-timeframe | MEDIUM — institutional approach | High |
| 9 | DTE awareness | LOW — timing refinement | Low |
| 10 | Volume + OI validation | LOW — data quality | Low |

---

## References

- [Best Indicators for Option Trading - Choice India](https://choiceindia.com/blog/best-indicators-for-option-trading)
- [5 Powerful Indicators on Bank Nifty - Waves Strategy](https://www.wavesstrategy.com/technical-indicators-bank-nifty)
- [VWAP and SuperTrend Strategy - Medium](https://medium.com/@redsword_23261/vwap-and-super-trend-buy-sell-strategy-dd45ad7487f7)
- [IV Percentile Explained - Option Samurai](https://optionsamurai.com/blog/implied-volatility-percentile-iv-percentile/)
- [IV Rank and Percentile - Barchart](https://www.barchart.com/options/iv-rank-percentile)
- [IV Percentile Guide - Charles Schwab](https://www.schwab.com/learn/story/using-implied-volatility-percentiles)
- [Option Chain Analysis - PL India](https://www.plindia.com/blogs/option-chain-analysis-master-nse-reading-2025/)
- [Bank Nifty Option Chain Analysis - PL India](https://www.plindia.com/blogs/bank-nifty-option-chain-analysis-live-oi-interpretation-2025/)
- [Max Pain Theory - Groww](https://groww.in/blog/max-pain-theory)
- [Put-Call Ratio Analysis - Strike Money](https://www.strike.money/options/put-call-ratio)
- [PCR Research Paper - Billingsley & Chance 1988](https://www.researchgate.net/publication/344962171)
- [ORB Strategy 400% Returns - Trade That Swing](https://tradethatswing.com/opening-range-breakout-strategy-up-400-this-year/)
- [ORB Backtest Results - Quantified Strategies](https://www.quantifiedstrategies.com/opening-range-breakout-strategy/)
- [VWAP Strategy for Intraday - Rupeezy](https://rupeezy.in/blog/vwap-trading-strategy-intraday-options)
- [All-in-One Multi-Indicator Strategy - AlgoTest](https://docs.algotest.in/signals/famous-strategies/all-in-one/)
- [Algorithmic Options Trading 101 - OptionsTradingOrg](https://www.optionstrading.org/blog/algorithmic-options-trading-101/)
- [Top 7 Indicators for Algo Trading - uTrade](https://www.utradealgos.com/blog/top-7-technical-indicators-for-algorithmic-traders)
- [Best Indicators for Options - Tradetron](https://tradetron.tech/blog/best-indicators-for-options-trading)
- [Sensibull Live Options Charts](https://web.sensibull.com/live-options-charts)
- [Quantsapp OI Percentile](https://web.quantsapp.com/price-oi-percentile)

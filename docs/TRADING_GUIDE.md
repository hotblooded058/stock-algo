# Trading Guide

## How to Use This System

This is a **decision-support tool**. It helps you make informed trading decisions
but does NOT auto-execute trades. You make the final call.

---

## Daily Workflow

### Pre-Market (9:00 - 9:15 IST)

1. Start the system:
   ```bash
   ./run.sh
   ```
2. Open http://localhost:3000
3. Check **Dashboard** — look at VIX and system status

### Market Open (9:15 - 9:30 IST)

**DO NOT TRADE in first 15 minutes.** Wait for opening noise to settle.

### Signal Scan (9:30 - 10:00 IST)

1. Click **"Scan Watchlist"** on Dashboard
2. Look for signals with score >= 60 (MODERATE or STRONG)
3. Ignore WEAK signals (score 40-59) unless multiple strategies confirm

### Trade Decision (10:00 IST onwards)

If a good signal appears:

1. Go to **Signals** page → Select the stock → "Generate Signals"
   - Read all the reasons carefully
   - Check if trend filter, volume, and confluence are all positive

2. Go to **Options** page → Enter spot price
   - Click "Recommend CALL/PUT Strike"
   - Check delta (want 0.4-0.5 for ATM)
   - Check theta (how much you lose per day)
   - Check IV — if IV is very high, skip

3. Go to **Scanner** → Calculate position size
   - Enter the option premium
   - Note the SL, Target 1, Target 2, and max loss

4. **Place the trade on AngelOne app manually**

### During the Day

- Monitor open positions on your broker app
- The system will scan again if you refresh the dashboard
- Exit rules:
  - Hit SL? Exit immediately, no questions asked
  - Hit Target? Take profit
  - Unsure? Follow the plan you made at entry

### End of Day (15:30 IST)

- Close all intraday positions before market close
- Review your trades

---

## Rules to Follow

### Risk Management (NON-NEGOTIABLE)

| Rule | Value | Why |
|------|-------|-----|
| Max risk per trade | 2% of capital (₹2,000 on ₹1L) | Survive losing streaks |
| Max daily loss | 5% of capital (₹5,000 on ₹1L) | Prevent emotional trading |
| Max open positions | 3 at a time | Focus and manage |
| Stop loss | ALWAYS set before entry | Never hope |
| Position sizing | Based on SL distance, not conviction | Math, not feelings |

### Signal Rules

| Rule | Details |
|------|---------|
| Only trade MODERATE+ | Score >= 60 minimum for real trades |
| Trend filter must pass | Don't buy CALL in downtrend |
| Volume must confirm | Low volume signals are noise |
| Check VIX first | VIX > 25 = expensive options, smaller size |
| Max 1-2 trades per day | Quality over quantity |

### Stocks to Trade

Based on 1-year backtest results:

| Stock | Win Rate | Recommendation |
|-------|----------|---------------|
| SBI | 64% | Best performer — trade actively |
| Reliance | 61% | Consistent — trade regularly |
| ITC | 59% | Good — trade regularly |
| TCS | 59% | Good — trade selectively |
| HDFC Bank | 63% | Good — trade selectively |
| BankNifty | 50% | Borderline — only strong signals |
| Nifty | 46% | Skip unless very strong signal |
| Infosys | 38% | DO NOT TRADE with this algo |

---

## Position Sizing Example

**Capital: ₹1,00,000**

1. Signal: SBI BUY_CALL, Score 72 (MODERATE)
2. Option premium: ₹150
3. Stop loss: 30% of premium = ₹45 (exit at ₹105)
4. Risk per trade: 2% = ₹2,000
5. Quantity: ₹2,000 / ₹45 = 44 units
6. Round to lot size (750): Can't afford full lot
7. Trade 44 units: Total cost = ₹6,600
8. Target 1: +40% = ₹210 (profit = ₹2,640)
9. Target 2: +80% = ₹270 (profit = ₹5,280)

---

## What NOT to Do

1. **Don't trade every signal** — Most signals are WEAK. Wait for MODERATE+.
2. **Don't average down** — If SL hits, exit. Don't add to losing positions.
3. **Don't trade on expiry day** — Theta eats everything on expiry.
4. **Don't trade during lunch** (12:00-1:30) — Low volume, false signals.
5. **Don't ignore VIX** — VIX > 25 means options are expensive.
6. **Don't override your SL** — The SL exists for a reason.
7. **Don't trade Infosys** — The algo loses money on it consistently.
8. **Don't risk more than 2%** — Even if you're "sure" about the trade.

---

## Paper Trading First

Before using real money:

1. Use the **Backtest** page to validate on historical data
2. Paper trade for 30+ trades (2-4 weeks)
3. Track every trade in the journal
4. Only go live if paper trading shows profit factor > 1.2

---

## Glossary

| Term | Meaning |
|------|---------|
| ATM | At The Money — strike closest to current price |
| OTM | Out of The Money — strike away from price (cheaper, higher risk) |
| ITM | In The Money — strike past the price (more expensive, lower risk) |
| IV | Implied Volatility — how expensive options are |
| Delta | How much option price moves per ₹1 of underlying |
| Theta | How much option loses per day (time decay) |
| PCR | Put-Call Ratio — market sentiment indicator |
| OI | Open Interest — number of open option contracts |
| Max Pain | Strike where most options expire worthless |
| VIX | Volatility Index — market fear gauge |
| SL | Stop Loss — exit point to limit losses |
| R:R | Risk to Reward ratio |
| PF | Profit Factor = total wins / total losses |
| WR | Win Rate = winning trades / total trades |
| DTE | Days To Expiry |

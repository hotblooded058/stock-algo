# Changelog

## v2.1 — Strategy Optimization (April 3, 2026)

### Walk-Forward Optimization
- 5-iteration optimization: train on 6 months, validate on previous 6 months
- Validation win rate improved each iteration: 45.9% -> 59.7%

### Optimized Parameters
- SuperTrend weight: 20 -> 17 (less reliance on lagging indicator)
- EMA cross weight: 20 -> 23 (fresh crossovers more predictive)
- Confluence bonus: 15 -> 23 (multi-strategy agreement rewarded more)
- Target: 4.5% -> 2.3% (smaller targets hit more frequently)
- R:R: 1.5 -> 1.2 (lower per-trade gain but much higher hit rate)
- Trailing SL: disabled (was cutting winners short)

### Results
- **Before:** 151 trades, 35.8% WR, P&L = -5,799 (LOSING)
- **After:** 163 trades, 54.6% WR, P&L = +66,461 (PROFITABLE)
- 7 out of 8 stocks profitable (only Infosys losing)

---

## v2.0 — Strategy v2 (April 3, 2026)

### Signal Generator Rewrite
- **Trend filter:** CALL only above EMA 21, PUT only below. Eliminates counter-trend trades.
- **Volume confirmation:** +10 bonus for 1.5x volume, -15 penalty for low volume.
- **Confluence scoring:** +23 bonus when 2+ strategies agree, -10 for lone signals.
- **RSI filter reordered:** Fixed unreachable branch (was checking <35 before <30).
- **VIX modifier softened:** -5 at VIX>25 instead of -15. Show warnings, don't hide signals.

### Backtest Engine v2
- Trailing stop loss (later disabled after optimization)
- Fixed R:R model (transparent P&L calculation)
- 2-bar cooldown after losing trades
- Options-aware P&L with theta decay simulation

---

## v1.3 — Bug Fixes (April 3, 2026)

### Fixed
- numpy.bool_ JSON serialization crash when saving indicators to DB
- Scan and generate endpoint VIX inconsistency
- .gitignore `data/` rule catching `src/data/`
- .gitignore `*.json` rule catching frontend package.json

---

## v1.2 — Phase 3+4: Alerts, Backtest, Journal (April 3, 2026)

### New Modules
- **src/alerts/notifier.py** — Telegram + console alerts for signals, trades, risk
- **src/backtest/engine.py** — Backtest engine with equity curve and monthly returns
- **src/journal/tracker.py** — Trade analytics (by strategy, symbol, day, streaks)

### New API Routes
- GET /api/backtest/run
- GET /api/journal/report
- GET /api/alerts/test, /history, /status

### Frontend
- New /backtest page with equity curve and trade list
- Trade journal analytics tab with streaks and improvement suggestions

---

## v1.1 — Phase 2: Options Analysis (April 2, 2026)

### New Modules
- **src/options/greeks.py** — Black-Scholes Greeks (Delta, Gamma, Theta, Vega) + IV
- **src/options/chain.py** — PCR, Max Pain, OI support/resistance, IV skew, OI buildup
- **src/options/strike_selector.py** — Strike recommendation with scoring
- **src/data/market_context.py** — VIX interpretation, FII/DII, market regime

### Enhanced Signals
- New `generate_oi_signal()` strategy using options chain data
- VIX modifier for all signals

### New API Routes
- GET /api/options/greeks
- GET /api/options/recommend-strike
- GET /api/options/market-context
- POST /api/options/fetch-context

### Frontend
- Options page: 3 tabs (Chain, Analytics, Strike Selector)
- Delta column in chain table
- Support/Resistance/MaxPain markers

---

## v1.0 — Phase 1: Full Stack Foundation (April 2, 2026)

### Backend (FastAPI)
- 24 API endpoints across 5 route modules
- SQLite database with 7 tables
- AngelOne SmartAPI broker integration

### Frontend (Next.js)
- Dashboard, Signals, Options Chain, Trade Journal, Scanner pages
- Dark trading theme with Tailwind CSS
- API client with full TypeScript interfaces

### Core Python Modules
- Data fetcher (Yahoo + NSE + Google fallback)
- Technical indicators (EMA, RSI, MACD, BB, SuperTrend, ATR, OBV)
- Signal generator (trend + breakout strategies)
- Risk manager (position sizing, daily loss limits)
- AngelOne broker client (login, LTP, historical, orders)

### Infrastructure
- SQLite database auto-creation
- run.sh for starting both servers
- Config-driven (settings.py + secrets.py)
- .gitignore for DB, secrets, node_modules

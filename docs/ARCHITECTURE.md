# Architecture

## System Overview

```
AngelOne SmartAPI (live data + orders)
        |
        v
  +-----------+     +-----------+     +-----------+
  | Candles   |     | Options   |     | Market    |
  | (OHLCV)   |     | Chain     |     | Context   |
  +-----------+     +-----------+     +-----------+
        |                |                 |
        v                v                 v
  +--------------------------------------------+
  |            SQLite Database                  |
  |  candles | options_chain | signals | trades |
  |  daily_pnl | market_context | instruments  |
  +--------------------------------------------+
        |                |                 |
        v                v                 v
  +-----------+     +-----------+     +-----------+
  | Technical |     | OI/IV/PCR |     | VIX/FII   |
  | Indicators|     | Analysis  |     | Context   |
  +-----------+     +-----------+     +-----------+
        |                |                 |
        +--------+-------+---------+-------+
                 |                 |
                 v                 v
        +----------------+   +----------+
        | Signal Engine  |   | Strike   |
        | (v2 optimized) |   | Selector |
        +-------+--------+   +----+-----+
                |                  |
        +-------+------------------+
        |               |
        v               v
  +-----------+   +------------+   +-----------+
  | Next.js   |   | Telegram   |   | Backtest  |
  | Dashboard |   | Alerts     |   | Engine    |
  +-----------+   +------------+   +-----------+
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python 3.13) |
| Frontend | Next.js 15 + Tailwind CSS + TypeScript |
| Database | SQLite (via Python sqlite3) |
| Broker | AngelOne SmartAPI |
| Data Sources | AngelOne (live) > Yahoo Finance > NSE > Google Finance |
| Charts | Plotly (Streamlit), Lightweight Charts (Next.js) |
| Alerts | Telegram Bot API |
| Package Manager | pip / npm |

## Project Structure

```
Stock-algo/
  backend/                  # FastAPI application
    app.py                  # Main app, CORS, route registration
    routes/
      market.py             # /api/market/* — watchlist, candles, vix, scan
      signals.py            # /api/signals/* — generate, history
      trades.py             # /api/trades/* — CRUD, position sizing, stats
      options.py            # /api/options/* — chain, greeks, strike rec
      backtest.py           # /api/backtest/* — run backtests
      journal.py            # /api/journal/* — trade analytics
      alerts.py             # /api/alerts/* — test, history, status
      system.py             # /api/system/* — health, db stats, risk

  frontend/                 # Next.js application
    src/
      app/
        page.tsx            # Dashboard — metrics, scan, system status
        signals/page.tsx    # Signal generation + history
        options/page.tsx    # Options chain, analytics, strike selector
        trades/page.tsx     # Trade journal + analytics
        backtest/page.tsx   # Backtest runner + results
        scanner/page.tsx    # Stock scanner + position calculator
      components/
        Sidebar.tsx         # Navigation sidebar
      lib/
        api.ts              # API client + TypeScript interfaces

  src/                      # Core Python modules
    data/
      fetcher.py            # Multi-source OHLCV fetcher (Yahoo/NSE/Google)
      market_context.py     # VIX, FII/DII, market regime
    indicators/
      technical.py          # EMA, RSI, MACD, BB, SuperTrend, ATR, OBV
    signals/
      generator.py          # Signal engine v2 (trend, breakout, OI strategies)
    options/
      greeks.py             # Black-Scholes Greeks + IV calculation
      chain.py              # Options chain analyzer (PCR, max pain, OI levels)
      strike_selector.py    # Optimal strike recommendation
    risk/
      manager.py            # Position sizing, daily loss limits
    broker/
      angelone.py           # AngelOne SmartAPI client
    alerts/
      notifier.py           # Telegram + console alerts
    backtest/
      engine.py             # Backtesting engine v2
      optimizer.py          # Walk-forward strategy optimizer
    journal/
      tracker.py            # Trade journal analytics
    db/
      database.py           # SQLite wrapper + schema (7 tables)

  config/
    settings.py             # All configuration (capital, indicators, lots)
    secrets.py              # AngelOne credentials (gitignored)

  data/trading.db           # SQLite database (auto-created, gitignored)
  run.sh                    # Start both backend + frontend
```

## API Endpoints (34 total)

| Module | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| Market | GET | /api/market/watchlist | All watchlist symbols |
| Market | GET | /api/market/candles | OHLCV + indicators |
| Market | GET | /api/market/indicators | Latest indicator values |
| Market | GET | /api/market/vix | India VIX + mood |
| Market | GET | /api/market/scan | Scan all watchlist stocks |
| Signals | GET | /api/signals/generate | Generate + save signals |
| Signals | GET | /api/signals/history | Signal history from DB |
| Signals | GET | /api/signals/{id} | Single signal details |
| Trades | GET | /api/trades/ | List trades (filterable) |
| Trades | GET | /api/trades/open | Open positions |
| Trades | POST | /api/trades/ | Record new trade |
| Trades | POST | /api/trades/{id}/close | Close trade with P&L |
| Trades | GET | /api/trades/position-size | Position size calculator |
| Trades | GET | /api/trades/daily-pnl | Daily P&L history |
| Trades | GET | /api/trades/stats | Overall trade statistics |
| Options | GET | /api/options/chain | Options chain + analytics |
| Options | GET | /api/options/analytics | PCR, max pain, OI, IV skew |
| Options | GET | /api/options/greeks | Greeks for single option |
| Options | GET | /api/options/recommend-strike | Strike recommendation |
| Options | GET | /api/options/market-context | VIX, FII/DII, regime |
| Options | POST | /api/options/fetch-context | Refresh market data |
| Backtest | GET | /api/backtest/run | Run backtest |
| Journal | GET | /api/journal/report | Full trade analytics |
| Alerts | GET | /api/alerts/test | Test alert connectivity |
| Alerts | GET | /api/alerts/history | Recent alert history |
| Alerts | GET | /api/alerts/status | Telegram status |
| System | GET | /api/system/status | System overview |
| System | GET | /api/system/db-stats | Database row counts |
| System | GET | /api/system/risk-summary | Risk state |
| System | GET | /api/health | Health check |

## How to Run

```bash
# Both servers
./run.sh

# Or separately:
python3 -m uvicorn backend.app:app --reload --port 8000   # Backend
cd frontend && npm run dev                                  # Frontend

# Access:
# Frontend:  http://localhost:3000
# API docs:  http://localhost:8000/docs
```

## Database Schema

7 tables in `data/trading.db`:
- **candles** — OHLCV price cache
- **options_chain** — OI, IV, volume, Greeks snapshots
- **signals** — Every generated signal with indicator snapshot
- **trades** — Trade journal (entry, exit, P&L)
- **daily_pnl** — Daily performance tracking
- **market_context** — VIX, PCR, FII/DII
- **instruments** — AngelOne token mapping + lot sizes

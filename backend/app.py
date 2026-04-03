"""
FastAPI Backend — Main Application
Run with: uvicorn backend.app:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import market, signals, trades, options, system, backtest, journal, alerts, screener

app = FastAPI(
    title="Trading Engine API",
    description="Options trading decision-support backend",
    version="1.0.0",
)

# Allow Next.js frontend (dev on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(market.router, prefix="/api/market", tags=["Market Data"])
app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
app.include_router(trades.router, prefix="/api/trades", tags=["Trades"])
app.include_router(options.router, prefix="/api/options", tags=["Options Chain"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtest"])
app.include_router(journal.router, prefix="/api/journal", tags=["Journal"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(screener.router, prefix="/api/screener", tags=["Screener"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "trading-engine"}

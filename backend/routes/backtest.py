"""
Backtest API Routes
"""

from fastapi import APIRouter, Query
from src.backtest.engine import BacktestEngine

router = APIRouter()
engine = BacktestEngine()


@router.get("/run")
def run_backtest(
    symbol: str = Query(..., description="Stock symbol (e.g. ^NSEI, RELIANCE.NS)"),
    period: str = Query("1y", description="Data period: 3mo, 6mo, 1y, 2y"),
    interval: str = Query("1d", description="Candle interval: 1d, 1h, 15m"),
    strategy: str = Query("all", description="Strategy filter: all, trend, breakout"),
    min_score: int = Query(40, description="Minimum signal score to take trade"),
):
    """Run a backtest on historical data."""
    result = engine.run(
        symbol=symbol,
        period=period,
        interval=interval,
        strategy=strategy,
        min_score=min_score,
    )
    return engine.to_dict(result)

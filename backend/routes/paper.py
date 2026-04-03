"""
Paper Trading API Routes
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from src.broker.paper_trader import PaperTrader

router = APIRouter()
trader = PaperTrader()


class PaperTradeEntry(BaseModel):
    symbol: str
    direction: str  # BUY_CALL or BUY_PUT
    entry_premium: float
    quantity: Optional[int] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    instrument: Optional[str] = None
    signal_id: Optional[int] = None
    notes: Optional[str] = None


class PaperTradeExit(BaseModel):
    exit_price: float
    reason: str = "manual"


@router.post("/enter")
def enter_paper_trade(trade: PaperTradeEntry):
    """Enter a new paper trade."""
    return trader.enter_trade(
        symbol=trade.symbol,
        direction=trade.direction,
        entry_premium=trade.entry_premium,
        quantity=trade.quantity,
        stop_loss=trade.stop_loss,
        target_1=trade.target_1,
        target_2=trade.target_2,
        instrument=trade.instrument,
        signal_id=trade.signal_id,
        notes=trade.notes,
    )


@router.post("/{trade_id}/exit")
def exit_paper_trade(trade_id: int, exit: PaperTradeExit):
    """Exit a paper trade at given price."""
    return trader.exit_trade(trade_id, exit.exit_price, exit.reason)


@router.get("/positions")
def open_positions():
    """Get all open paper positions."""
    positions = trader.get_open_positions()
    return {"positions": positions, "count": len(positions)}


@router.get("/history")
def paper_history(limit: int = Query(50)):
    """Get paper trade history."""
    history = trader.get_history(limit)
    return {"trades": history, "count": len(history)}


@router.get("/stats")
def paper_stats():
    """Get paper trading statistics — shows if you're ready for live."""
    return trader.get_stats()


@router.post("/check")
def check_sl_target(prices: dict = None):
    """
    Check all open positions against SL/target.
    Pass live prices as JSON: {"NIFTY": 150, "SBIN": 45}
    """
    if not prices:
        return {"auto_closed": [], "message": "Pass prices dict to check SL/target"}
    closed = trader.check_positions(prices)
    return {"auto_closed": closed, "count": len(closed)}

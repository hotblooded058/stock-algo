"""
Trades API Routes
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from src.db.database import Database
from src.risk.manager import RiskManager
from datetime import datetime
from typing import Optional

router = APIRouter()
db = Database()


class TradeCreate(BaseModel):
    signal_id: Optional[int] = None
    symbol: str
    instrument: Optional[str] = None
    direction: str
    quantity: int
    entry_price: float
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None


class TradeClose(BaseModel):
    exit_price: float
    exit_reason: str = "manual"
    notes: Optional[str] = None


@router.get("/")
def list_trades(
    status: str = Query(None, description="Filter by status: OPEN, CLOSED, STOPPED_OUT, TARGET_HIT"),
    symbol: str = Query(None),
    limit: int = Query(100),
):
    """List trades with optional filters."""
    trades = db.get_trades(status=status, symbol=symbol, limit=limit)
    return {"trades": trades, "count": len(trades)}


@router.get("/open")
def open_trades():
    """Get all currently open trades."""
    trades = db.get_open_trades()
    return {"trades": trades, "count": len(trades)}


@router.post("/")
def create_trade(trade: TradeCreate):
    """Record a new trade (manual entry or from signal)."""
    rm = RiskManager()
    can_trade, msg = rm.can_trade()
    if not can_trade:
        return {"error": msg, "can_trade": False}

    trade_data = {
        "signal_id": trade.signal_id,
        "symbol": trade.symbol,
        "instrument": trade.instrument,
        "direction": trade.direction,
        "quantity": trade.quantity,
        "entry_price": trade.entry_price,
        "exit_price": None,
        "stop_loss": trade.stop_loss,
        "target_1": trade.target_1,
        "target_2": trade.target_2,
        "pnl": None,
        "status": "OPEN",
        "entry_time": datetime.now().isoformat(),
        "exit_time": None,
        "exit_reason": None,
        "broker_order_id": None,
        "notes": trade.notes,
        "tags": trade.tags or [],
    }

    trade_id = db.save_trade(trade_data)
    return {"id": trade_id, "status": "OPEN", "message": "Trade recorded"}


@router.post("/{trade_id}/close")
def close_trade(trade_id: int, close: TradeClose):
    """Close an open trade with exit price."""
    trades = db.get_trades()
    trade = next((t for t in trades if t["id"] == trade_id), None)
    if not trade:
        return {"error": "Trade not found"}
    if trade["status"] != "OPEN":
        return {"error": f"Trade is already {trade['status']}"}

    pnl = (close.exit_price - trade["entry_price"]) * trade["quantity"]
    if "PUT" in trade["direction"]:
        pnl = -pnl

    status = "CLOSED"
    if close.exit_reason == "stop_loss":
        status = "STOPPED_OUT"
    elif close.exit_reason in ("target_1", "target_2"):
        status = "TARGET_HIT"

    db.update_trade(trade_id, {
        "exit_price": close.exit_price,
        "exit_time": datetime.now().isoformat(),
        "exit_reason": close.exit_reason,
        "pnl": round(pnl, 2),
        "status": status,
        "notes": close.notes or trade.get("notes"),
    })

    return {
        "id": trade_id,
        "pnl": round(pnl, 2),
        "status": status,
        "message": f"Trade closed. P&L: {pnl:+.2f}",
    }


@router.get("/position-size")
def calculate_position_size(
    premium: float = Query(..., description="Option premium price"),
    strength: str = Query("MODERATE", description="Signal strength: STRONG, MODERATE, WEAK"),
    capital: float = Query(None, description="Override capital"),
):
    """Calculate position size based on risk rules."""
    rm = RiskManager(capital=capital) if capital else RiskManager()
    can_trade, msg = rm.can_trade()
    plan = rm.calculate_position_size(premium, strength)

    return {
        "can_trade": can_trade,
        "message": msg,
        "plan": plan,
    }


@router.get("/daily-pnl")
def daily_pnl(days: int = Query(30)):
    """Get daily P&L history."""
    pnl = db.get_daily_pnl(days=days)
    return {"daily_pnl": pnl, "count": len(pnl)}


@router.get("/stats")
def trade_stats():
    """Get overall trading statistics."""
    all_trades = db.get_trades(limit=1000)
    closed = [t for t in all_trades if t["status"] != "OPEN" and t.get("pnl") is not None]

    if not closed:
        return {
            "total_trades": len(all_trades),
            "open_trades": len([t for t in all_trades if t["status"] == "OPEN"]),
            "closed_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
        }

    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] <= 0]

    total_wins = sum(t["pnl"] for t in wins) if wins else 0
    total_losses = abs(sum(t["pnl"] for t in losses)) if losses else 0

    return {
        "total_trades": len(all_trades),
        "open_trades": len([t for t in all_trades if t["status"] == "OPEN"]),
        "closed_trades": len(closed),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
        "total_pnl": round(sum(t["pnl"] for t in closed), 2),
        "avg_win": round(total_wins / len(wins), 2) if wins else 0,
        "avg_loss": round(total_losses / len(losses), 2) if losses else 0,
        "profit_factor": round(total_wins / total_losses, 2) if total_losses > 0 else 0,
        "best_trade": round(max(t["pnl"] for t in closed), 2) if closed else 0,
        "worst_trade": round(min(t["pnl"] for t in closed), 2) if closed else 0,
    }

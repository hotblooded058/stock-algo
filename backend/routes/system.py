"""
System & Control API Routes
"""

from fastapi import APIRouter
from src.db.database import Database
from src.risk.manager import RiskManager
from config.settings import TOTAL_CAPITAL

router = APIRouter()
db = Database()


@router.get("/status")
def system_status():
    """Get system status — DB stats, risk state, broker connection."""
    stats = db.get_stats()
    rm = RiskManager()
    can_trade, msg = rm.can_trade()
    today_pnl = db.get_today_pnl()

    return {
        "db": stats,
        "risk": {
            "can_trade": can_trade,
            "message": msg,
            "capital": TOTAL_CAPITAL,
            "daily_pnl": today_pnl["realized_pnl"] if today_pnl else 0,
            "open_positions": len(db.get_open_trades()),
        },
        "broker": {
            "connected": False,
            "name": "AngelOne",
            "message": "Not connected. Set up credentials in config/secrets.py",
        },
    }


@router.get("/db-stats")
def db_stats():
    """Get database table row counts."""
    return db.get_stats()


@router.get("/risk-summary")
def risk_summary():
    """Get current risk status."""
    rm = RiskManager()
    can_trade, msg = rm.can_trade()

    open_trades = db.get_open_trades()
    today_pnl = db.get_today_pnl()

    return {
        "can_trade": can_trade,
        "message": msg,
        "capital": TOTAL_CAPITAL,
        "daily_pnl": today_pnl["realized_pnl"] if today_pnl else 0,
        "open_trades": len(open_trades),
        "max_open_positions": 3,
        "max_daily_loss_pct": 5,
        "max_risk_per_trade_pct": 2,
    }

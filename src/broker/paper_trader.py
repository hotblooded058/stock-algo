"""
Paper Trading System
Simulates trades with live market data — no real orders placed.
Tracks positions, monitors SL/target, records P&L.

Usage:
1. Enter a paper trade (symbol, strike, option_type, premium, qty)
2. System tracks live price via AngelOne or Yahoo
3. Auto-exits when SL or target hit
4. Records everything in the trades table (broker_order_id = 'PAPER_xxx')
"""

import sys
import os
from datetime import datetime
import random
import string

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.db.database import Database
from src.data.fno_stocks import FNO_STOCKS, get_lot_size
from config.settings import (
    STOP_LOSS_PERCENT, TARGET_1_PERCENT, TARGET_2_PERCENT,
    TOTAL_CAPITAL, MAX_RISK_PER_TRADE, MAX_OPEN_POSITIONS
)


class PaperTrader:
    """Paper trading with live price tracking."""

    def __init__(self, db: Database = None, capital: float = TOTAL_CAPITAL):
        self.db = db or Database()
        self.capital = capital

    def _paper_id(self) -> str:
        """Generate unique paper order ID."""
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"PAPER_{code}"

    # ========================================================
    # ENTER TRADE
    # ========================================================

    def enter_trade(
        self,
        symbol: str,
        direction: str,
        entry_premium: float,
        quantity: int = None,
        stop_loss: float = None,
        target_1: float = None,
        target_2: float = None,
        instrument: str = None,
        signal_id: int = None,
        notes: str = None,
    ) -> dict:
        """
        Enter a paper trade.

        Args:
            symbol: NSE symbol (e.g. NIFTY, SBIN, RELIANCE)
            direction: BUY_CALL or BUY_PUT
            entry_premium: Option premium at entry (e.g. 150)
            quantity: Number of units (defaults to 1 lot)
            stop_loss: SL price (defaults to 30% of premium)
            target_1: Target 1 price (defaults to 40% profit)
            target_2: Target 2 price (defaults to 80% profit)
            instrument: Full instrument name (e.g. NIFTY26APR22500CE)
            signal_id: Link to signal that triggered this
            notes: Trade notes
        """
        # Check risk limits
        open_trades = self.get_open_positions()
        if len(open_trades) >= MAX_OPEN_POSITIONS:
            return {"error": f"Max {MAX_OPEN_POSITIONS} positions allowed. Close one first."}

        # Default quantity to 1 lot
        if quantity is None:
            lot_size = get_lot_size(symbol)
            # Calculate quantity based on risk
            if stop_loss is None:
                sl_amount = entry_premium * STOP_LOSS_PERCENT
            else:
                sl_amount = entry_premium - stop_loss

            if sl_amount > 0:
                max_risk = self.capital * MAX_RISK_PER_TRADE
                quantity = int(max_risk / sl_amount)
                # Round to lot size
                if lot_size > 1:
                    quantity = max(lot_size, (quantity // lot_size) * lot_size)
            else:
                quantity = get_lot_size(symbol)

        # Default SL and targets
        if stop_loss is None:
            stop_loss = round(entry_premium * (1 - STOP_LOSS_PERCENT), 2)
        if target_1 is None:
            target_1 = round(entry_premium * (1 + TARGET_1_PERCENT), 2)
        if target_2 is None:
            target_2 = round(entry_premium * (1 + TARGET_2_PERCENT), 2)

        paper_id = self._paper_id()

        trade_data = {
            "signal_id": signal_id,
            "symbol": symbol,
            "instrument": instrument or f"{symbol}_PAPER",
            "direction": direction,
            "quantity": quantity,
            "entry_price": entry_premium,
            "exit_price": None,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "pnl": None,
            "status": "OPEN",
            "entry_time": datetime.now().isoformat(),
            "exit_time": None,
            "exit_reason": None,
            "broker_order_id": paper_id,
            "notes": notes or "Paper trade",
            "tags": ["paper"],
        }

        trade_id = self.db.save_trade(trade_data)

        total_cost = entry_premium * quantity
        max_loss = (entry_premium - stop_loss) * quantity

        return {
            "id": trade_id,
            "paper_id": paper_id,
            "symbol": symbol,
            "direction": direction,
            "quantity": quantity,
            "entry_premium": entry_premium,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "total_cost": round(total_cost, 2),
            "max_loss": round(max_loss, 2),
            "risk_pct": round((max_loss / self.capital) * 100, 2),
            "message": f"Paper trade entered: {direction} {symbol} x{quantity} @ ₹{entry_premium}",
        }

    # ========================================================
    # EXIT TRADE
    # ========================================================

    def exit_trade(self, trade_id: int, exit_price: float,
                   reason: str = "manual") -> dict:
        """Exit a paper trade at given price."""
        trades = self.db.get_trades()
        trade = next((t for t in trades if t["id"] == trade_id), None)

        if not trade:
            return {"error": "Trade not found"}
        if trade["status"] != "OPEN":
            return {"error": f"Trade already {trade['status']}"}

        # Calculate P&L
        if "CALL" in trade["direction"]:
            pnl_per_unit = exit_price - trade["entry_price"]
        else:
            pnl_per_unit = trade["entry_price"] - exit_price

        pnl = round(pnl_per_unit * trade["quantity"], 2)

        status = "CLOSED"
        if reason == "stop_loss":
            status = "STOPPED_OUT"
        elif reason in ("target_1", "target_2"):
            status = "TARGET_HIT"

        self.db.update_trade(trade_id, {
            "exit_price": exit_price,
            "exit_time": datetime.now().isoformat(),
            "exit_reason": reason,
            "pnl": pnl,
            "status": status,
        })

        return {
            "id": trade_id,
            "symbol": trade["symbol"],
            "pnl": pnl,
            "pnl_pct": round((pnl_per_unit / trade["entry_price"]) * 100, 2),
            "status": status,
            "reason": reason,
            "message": f"{'Profit' if pnl > 0 else 'Loss'}: ₹{pnl:+,.2f} ({reason})",
        }

    # ========================================================
    # CHECK POSITIONS (SL/TARGET monitoring)
    # ========================================================

    def check_positions(self, live_prices: dict = None) -> list[dict]:
        """
        Check all open paper positions against SL/target.
        live_prices: dict of {symbol: current_premium}

        Returns list of auto-closed trades.
        """
        open_trades = self.get_open_positions()
        auto_closed = []

        for trade in open_trades:
            symbol = trade["symbol"]

            # Get current price
            current_price = None
            if live_prices and symbol in live_prices:
                current_price = live_prices[symbol]

            if current_price is None:
                continue

            # Check SL
            if current_price <= trade.get("stop_loss", 0):
                result = self.exit_trade(trade["id"], current_price, "stop_loss")
                auto_closed.append(result)
                continue

            # Check Target 1
            if trade.get("target_1") and current_price >= trade["target_1"]:
                result = self.exit_trade(trade["id"], current_price, "target_1")
                auto_closed.append(result)
                continue

        return auto_closed

    # ========================================================
    # POSITIONS & HISTORY
    # ========================================================

    def get_open_positions(self) -> list[dict]:
        """Get all open paper trades."""
        all_trades = self.db.get_trades(status="OPEN")
        return [t for t in all_trades if t.get("broker_order_id", "").startswith("PAPER_")]

    def get_history(self, limit: int = 100) -> list[dict]:
        """Get closed paper trades."""
        all_trades = self.db.get_trades(limit=limit)
        return [t for t in all_trades if t.get("broker_order_id", "").startswith("PAPER_")]

    def get_stats(self) -> dict:
        """Get paper trading statistics."""
        all_paper = self.get_history(limit=1000)
        closed = [t for t in all_paper if t["status"] != "OPEN" and t.get("pnl") is not None]
        open_trades = [t for t in all_paper if t["status"] == "OPEN"]

        if not closed:
            return {
                "total_trades": len(all_paper),
                "open_trades": len(open_trades),
                "closed_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "ready_for_live": False,
                "message": "Need 30+ paper trades before going live",
            }

        wins = [t for t in closed if t["pnl"] > 0]
        losses = [t for t in closed if t["pnl"] <= 0]
        total_wins = sum(t["pnl"] for t in wins) if wins else 0
        total_losses = abs(sum(t["pnl"] for t in losses)) if losses else 0
        win_rate = len(wins) / len(closed) * 100

        pf = round(total_wins / total_losses, 2) if total_losses > 0 else 999

        # Ready for live?
        ready = len(closed) >= 30 and win_rate >= 50 and pf >= 1.2

        return {
            "total_trades": len(all_paper),
            "open_trades": len(open_trades),
            "closed_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 1),
            "total_pnl": round(sum(t["pnl"] for t in closed), 2),
            "avg_win": round(total_wins / len(wins), 2) if wins else 0,
            "avg_loss": round(total_losses / len(losses), 2) if losses else 0,
            "profit_factor": pf,
            "best_trade": round(max(t["pnl"] for t in closed), 2) if closed else 0,
            "worst_trade": round(min(t["pnl"] for t in closed), 2) if closed else 0,
            "ready_for_live": ready,
            "trades_needed": max(0, 30 - len(closed)),
            "message": "Ready for live trading!" if ready else f"Need {max(0, 30 - len(closed))} more trades (WR >= 50%, PF >= 1.2)",
        }

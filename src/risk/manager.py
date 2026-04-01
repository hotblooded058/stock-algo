"""
Risk Management Engine
Controls position sizing, stop losses, and daily P&L limits.
This is the MOST IMPORTANT module — it keeps you from losing big.
"""

import json
import os
from datetime import datetime, date
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import (
    TOTAL_CAPITAL, MAX_RISK_PER_TRADE, MAX_DAILY_LOSS,
    MAX_OPEN_POSITIONS, STOP_LOSS_PERCENT,
    TARGET_1_PERCENT, TARGET_2_PERCENT
)


class RiskManager:
    """Manages all risk-related calculations and limits."""

    def __init__(self, capital: float = TOTAL_CAPITAL):
        self.capital = capital
        self.daily_pnl = 0.0
        self.open_positions = []
        self.trade_history = []
        self.today = date.today().isoformat()

        # Load state if exists
        self.state_file = os.path.join(
            os.path.dirname(__file__), '..', '..', 'logs', 'risk_state.json'
        )
        self._load_state()

    def _load_state(self):
        """Load saved state from disk."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                # Reset daily P&L if new day
                if state.get('date') == self.today:
                    self.daily_pnl = state.get('daily_pnl', 0)
                    self.open_positions = state.get('open_positions', [])
                self.trade_history = state.get('trade_history', [])
        except Exception:
            pass

    def _save_state(self):
        """Save current state to disk."""
        try:
            state = {
                'date': self.today,
                'capital': self.capital,
                'daily_pnl': self.daily_pnl,
                'open_positions': self.open_positions,
                'trade_history': self.trade_history[-100:]  # Keep last 100
            }
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Could not save risk state: {e}")

    # ========================================================
    # PRE-TRADE CHECKS
    # ========================================================

    def can_trade(self) -> tuple[bool, str]:
        """Check if we're allowed to take a new trade."""

        # Check daily loss limit
        max_loss = self.capital * MAX_DAILY_LOSS
        if abs(self.daily_pnl) >= max_loss and self.daily_pnl < 0:
            return False, f"🛑 DAILY LOSS LIMIT HIT (₹{abs(self.daily_pnl):.0f} / ₹{max_loss:.0f}). Stop trading today."

        # Check max open positions
        if len(self.open_positions) >= MAX_OPEN_POSITIONS:
            return False, f"🛑 MAX POSITIONS REACHED ({len(self.open_positions)}/{MAX_OPEN_POSITIONS}). Close a trade first."

        return True, "✅ OK to trade"

    def calculate_position_size(self, option_premium: float,
                                 signal_strength: str = "MODERATE") -> dict:
        """
        Calculate how many lots/quantity to buy based on risk rules.

        Args:
            option_premium: Price of one unit of the option
            signal_strength: "STRONG", "MODERATE", or "WEAK"

        Returns:
            dict with quantity, risk amount, stop loss, targets
        """
        # Max risk per trade
        max_risk = self.capital * MAX_RISK_PER_TRADE

        # Adjust based on signal strength
        multipliers = {"STRONG": 1.0, "MODERATE": 0.5, "WEAK": 0.25}
        adjusted_risk = max_risk * multipliers.get(signal_strength, 0.5)

        # Stop loss amount per unit
        stop_loss_per_unit = option_premium * STOP_LOSS_PERCENT

        # Max quantity we can buy
        if stop_loss_per_unit > 0:
            max_quantity = int(adjusted_risk / stop_loss_per_unit)
        else:
            max_quantity = 0

        # Also check total cost doesn't exceed 10% of capital
        max_by_cost = int((self.capital * 0.10) / option_premium) if option_premium > 0 else 0
        quantity = min(max_quantity, max_by_cost)
        quantity = max(quantity, 0)  # Don't go negative

        # Calculate levels
        stop_loss_price = round(option_premium * (1 - STOP_LOSS_PERCENT), 2)
        target_1_price = round(option_premium * (1 + TARGET_1_PERCENT), 2)
        target_2_price = round(option_premium * (1 + TARGET_2_PERCENT), 2)
        total_cost = round(quantity * option_premium, 2)
        max_loss = round(quantity * stop_loss_per_unit, 2)

        return {
            'quantity': quantity,
            'entry_price': option_premium,
            'stop_loss': stop_loss_price,
            'target_1': target_1_price,
            'target_2': target_2_price,
            'total_cost': total_cost,
            'max_loss': max_loss,
            'risk_percent': round((max_loss / self.capital) * 100, 2),
            'signal_strength': signal_strength,
        }

    # ========================================================
    # TRADE TRACKING
    # ========================================================

    def open_trade(self, symbol: str, direction: str, quantity: int,
                   entry_price: float, stop_loss: float,
                   target_1: float, target_2: float):
        """Record a new open trade."""
        trade = {
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'opened_at': datetime.now().isoformat(),
            'status': 'OPEN'
        }
        self.open_positions.append(trade)
        self._save_state()
        print(f"📝 Trade opened: {symbol} {direction} x{quantity} @ ₹{entry_price}")

    def close_trade(self, symbol: str, exit_price: float, reason: str = "manual"):
        """Close an open trade and record P&L."""
        for i, trade in enumerate(self.open_positions):
            if trade['symbol'] == symbol and trade['status'] == 'OPEN':
                pnl = (exit_price - trade['entry_price']) * trade['quantity']
                if "PUT" in trade['direction']:
                    pnl = -pnl  # Reverse for puts (simplified)

                trade['exit_price'] = exit_price
                trade['pnl'] = round(pnl, 2)
                trade['closed_at'] = datetime.now().isoformat()
                trade['close_reason'] = reason
                trade['status'] = 'CLOSED'

                self.daily_pnl += pnl
                self.trade_history.append(trade)
                self.open_positions.pop(i)
                self._save_state()

                emoji = "💰" if pnl > 0 else "💸"
                print(f"{emoji} Trade closed: {symbol} | P&L: ₹{pnl:.0f} | Reason: {reason}")
                return trade

        print(f"⚠️ No open trade found for {symbol}")
        return None

    # ========================================================
    # REPORTING
    # ========================================================

    def get_daily_summary(self) -> str:
        """Get today's trading summary."""
        max_loss = self.capital * MAX_DAILY_LOSS
        pnl_emoji = "💰" if self.daily_pnl >= 0 else "💸"

        lines = [
            "=" * 50,
            "📊 DAILY RISK SUMMARY",
            "=" * 50,
            f"Capital: ₹{self.capital:,.0f}",
            f"Daily P&L: {pnl_emoji} ₹{self.daily_pnl:,.0f}",
            f"Daily Loss Limit: ₹{max_loss:,.0f} ({MAX_DAILY_LOSS*100:.0f}%)",
            f"Open Positions: {len(self.open_positions)}/{MAX_OPEN_POSITIONS}",
            "",
        ]

        if self.open_positions:
            lines.append("Open Trades:")
            for pos in self.open_positions:
                lines.append(
                    f"  • {pos['symbol']} {pos['direction']} "
                    f"x{pos['quantity']} @ ₹{pos['entry_price']}"
                    f" | SL: ₹{pos['stop_loss']} | T1: ₹{pos['target_1']}"
                )

        return "\n".join(lines)

    def format_position_plan(self, plan: dict) -> str:
        """Format a position sizing plan for display."""
        if plan['quantity'] == 0:
            return "⚠️ Cannot take this trade — position size would be 0 (risk too high or premium too expensive)."

        return (
            f"\n📋 TRADE PLAN\n"
            f"{'─' * 40}\n"
            f"  Quantity:      {plan['quantity']} units\n"
            f"  Entry Price:   ₹{plan['entry_price']:.2f}\n"
            f"  Stop Loss:     ₹{plan['stop_loss']:.2f} (-{STOP_LOSS_PERCENT*100:.0f}%)\n"
            f"  Target 1:      ₹{plan['target_1']:.2f} (+{TARGET_1_PERCENT*100:.0f}%) → exit half\n"
            f"  Target 2:      ₹{plan['target_2']:.2f} (+{TARGET_2_PERCENT*100:.0f}%) → exit rest\n"
            f"  Total Cost:    ₹{plan['total_cost']:,.2f}\n"
            f"  Max Loss:      ₹{plan['max_loss']:,.2f} ({plan['risk_percent']}% of capital)\n"
            f"  Signal:        {plan['signal_strength']}\n"
        )


# ---- Quick Test ----
if __name__ == "__main__":
    rm = RiskManager(capital=100000)

    print(rm.get_daily_summary())

    can, msg = rm.can_trade()
    print(f"\nCan trade? {msg}")

    plan = rm.calculate_position_size(option_premium=150, signal_strength="STRONG")
    print(rm.format_position_plan(plan))

    plan2 = rm.calculate_position_size(option_premium=150, signal_strength="MODERATE")
    print(rm.format_position_plan(plan2))

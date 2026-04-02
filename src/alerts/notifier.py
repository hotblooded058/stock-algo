"""
Alert Notification System
Sends alerts via Telegram and console for trading events.

Setup:
1. Create a Telegram bot via @BotFather
2. Get your chat ID via @userinfobot
3. Fill TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config/settings.py
"""

import sys
import os
import json
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import quote

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class Notifier:
    """Multi-channel notification system for trading alerts."""

    def __init__(self):
        self.telegram_enabled = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
        self._alert_history = []

    # ========================================================
    # CORE SEND
    # ========================================================

    def send(self, message: str, category: str = "info", urgent: bool = False):
        """Send alert to all enabled channels."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"

        # Console
        prefix = {"signal": "🎯", "risk": "🛡️", "trade": "💰", "system": "⚙️"}.get(category, "📢")
        print(f"{prefix} {full_msg}")

        # Telegram
        if self.telegram_enabled:
            self._send_telegram(full_msg)

        # History
        self._alert_history.append({
            "time": timestamp,
            "message": message,
            "category": category,
            "urgent": urgent,
        })

    def _send_telegram(self, message: str) -> bool:
        """Send message via Telegram Bot API."""
        try:
            encoded = quote(message)
            url = (
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
                f"/sendMessage?chat_id={TELEGRAM_CHAT_ID}"
                f"&text={encoded}&parse_mode=HTML"
            )
            req = Request(url, headers={"User-Agent": "TradingEngine/1.0"})
            resp = urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            return data.get("ok", False)
        except Exception as e:
            print(f"Telegram send failed: {e}")
            return False

    # ========================================================
    # SIGNAL ALERTS
    # ========================================================

    def alert_signal(self, signal_data: dict):
        """Alert when a trading signal is generated."""
        symbol = signal_data.get("name") or signal_data.get("symbol", "?")
        direction = signal_data.get("direction", "")
        score = signal_data.get("score", 0)
        strength = signal_data.get("strength", "")
        strategy = signal_data.get("strategy", "")

        icon = "🟢" if "CALL" in direction else "🔴"
        msg = (
            f"{icon} <b>Signal: {symbol}</b>\n"
            f"Direction: {direction.replace('BUY_', '')}\n"
            f"Score: {score}/100 ({strength})\n"
            f"Strategy: {strategy}"
        )

        # Add reasons
        reasons = signal_data.get("reasons", [])
        if reasons:
            msg += "\n\nReasons:"
            for r in reasons[:5]:
                msg += f"\n  + {r}"

        # Add strike recommendation if available
        strike_rec = signal_data.get("recommended_strike")
        if strike_rec:
            msg += (
                f"\n\n<b>Recommended:</b> {strike_rec.get('strike', '')} "
                f"{strike_rec.get('option_type', '')}\n"
                f"Premium: ₹{strike_rec.get('ltp', 0):.2f} | "
                f"Delta: {strike_rec.get('delta', 0):.2f}"
            )

        self.send(msg, category="signal", urgent=score >= 80)

    def alert_strong_signal(self, signal_data: dict):
        """Only alert for STRONG signals (score >= 80)."""
        if signal_data.get("score", 0) >= 80:
            self.alert_signal(signal_data)

    # ========================================================
    # TRADE ALERTS
    # ========================================================

    def alert_trade_opened(self, trade: dict):
        """Alert when a trade is opened."""
        symbol = trade.get("symbol", "?")
        direction = trade.get("direction", "")
        qty = trade.get("quantity", 0)
        price = trade.get("entry_price", 0)
        sl = trade.get("stop_loss", 0)
        t1 = trade.get("target_1", 0)

        msg = (
            f"📝 <b>Trade Opened: {symbol}</b>\n"
            f"{direction} x{qty} @ ₹{price}\n"
            f"SL: ₹{sl} | Target: ₹{t1}"
        )
        self.send(msg, category="trade")

    def alert_trade_closed(self, trade: dict):
        """Alert when a trade is closed."""
        symbol = trade.get("symbol", "?")
        pnl = trade.get("pnl", 0)
        reason = trade.get("exit_reason", "manual")

        icon = "💰" if pnl > 0 else "💸"
        msg = (
            f"{icon} <b>Trade Closed: {symbol}</b>\n"
            f"P&L: ₹{pnl:+,.2f}\n"
            f"Reason: {reason}"
        )
        self.send(msg, category="trade", urgent=abs(pnl) > 1000)

    # ========================================================
    # RISK ALERTS
    # ========================================================

    def alert_sl_approaching(self, symbol: str, current_price: float,
                              stop_loss: float, distance_pct: float):
        """Alert when price is approaching stop loss."""
        msg = (
            f"⚠️ <b>SL Alert: {symbol}</b>\n"
            f"Current: ₹{current_price:.2f}\n"
            f"Stop Loss: ₹{stop_loss:.2f}\n"
            f"Distance: {distance_pct:.1f}%"
        )
        self.send(msg, category="risk", urgent=True)

    def alert_target_approaching(self, symbol: str, current_price: float,
                                   target: float, distance_pct: float):
        """Alert when price is approaching target."""
        msg = (
            f"🎯 <b>Target Alert: {symbol}</b>\n"
            f"Current: ₹{current_price:.2f}\n"
            f"Target: ₹{target:.2f}\n"
            f"Distance: {distance_pct:.1f}%"
        )
        self.send(msg, category="trade")

    def alert_daily_loss_warning(self, daily_pnl: float, max_loss: float):
        """Alert when approaching daily loss limit."""
        pct_used = abs(daily_pnl) / max_loss * 100 if max_loss > 0 else 0
        msg = (
            f"🛑 <b>Daily Loss Warning</b>\n"
            f"Loss: ₹{abs(daily_pnl):,.2f} / ₹{max_loss:,.2f}\n"
            f"Used: {pct_used:.0f}% of daily limit\n"
            f"{'STOP TRADING!' if pct_used >= 100 else 'Reduce position sizes!'}"
        )
        self.send(msg, category="risk", urgent=True)

    # ========================================================
    # MARKET ALERTS
    # ========================================================

    def alert_vix_spike(self, vix: float, prev_vix: float):
        """Alert on significant VIX movement."""
        change = vix - prev_vix
        pct_change = (change / prev_vix) * 100 if prev_vix > 0 else 0

        if abs(pct_change) < 5:
            return  # Ignore small changes

        msg = (
            f"📊 <b>VIX Alert</b>\n"
            f"VIX: {vix:.2f} ({change:+.2f}, {pct_change:+.1f}%)\n"
            f"{'Options getting expensive!' if change > 0 else 'Options getting cheaper!'}"
        )
        self.send(msg, category="system")

    def alert_market_open(self, vix: float = None, nifty: float = None):
        """Morning market summary alert."""
        msg = "🔔 <b>Market Open</b>\n"
        if nifty:
            msg += f"Nifty: {nifty:,.2f}\n"
        if vix:
            msg += f"VIX: {vix:.2f}\n"
        msg += "Trading engine active."
        self.send(msg, category="system")

    # ========================================================
    # UTILITY
    # ========================================================

    def get_history(self, limit: int = 50) -> list[dict]:
        """Get recent alert history."""
        return self._alert_history[-limit:]

    def test(self) -> dict:
        """Send a test alert to verify connectivity."""
        success = True
        channels = ["console"]

        if self.telegram_enabled:
            ok = self._send_telegram("🧪 Trading Engine test alert — if you see this, Telegram is working!")
            if ok:
                channels.append("telegram")
            else:
                success = False

        return {
            "success": success,
            "channels": channels,
            "telegram_enabled": self.telegram_enabled,
        }


# Singleton
_notifier = None


def get_notifier() -> Notifier:
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier

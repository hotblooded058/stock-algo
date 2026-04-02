"""
Trade Journal Analytics
Analyzes trade history for patterns, performance, and improvement areas.
"""

import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.db.database import Database


class TradeJournal:
    """Analyzes trading history for performance insights."""

    def __init__(self, db: Database = None):
        self.db = db or Database()

    def full_report(self) -> dict:
        """Generate comprehensive trade journal analytics."""
        trades = self.db.get_trades(limit=10000)
        closed = [t for t in trades if t["status"] != "OPEN" and t.get("pnl") is not None]

        if not closed:
            return {"message": "No closed trades to analyze", "trade_count": 0}

        return {
            "overview": self._overview(closed),
            "by_strategy": self._by_strategy(closed),
            "by_symbol": self._by_symbol(closed),
            "by_day_of_week": self._by_day(closed),
            "by_hour": self._by_hour(closed),
            "streaks": self._streaks(closed),
            "drawdown": self._drawdown_analysis(closed),
            "recent_performance": self._recent_vs_overall(closed),
            "risk_metrics": self._risk_metrics(closed),
            "improvement_areas": self._improvement_suggestions(closed),
        }

    # ========================================================
    # OVERVIEW
    # ========================================================

    def _overview(self, trades: list[dict]) -> dict:
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]

        total_wins = sum(t["pnl"] for t in wins) if wins else 0
        total_losses = abs(sum(t["pnl"] for t in losses)) if losses else 0

        # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = total_wins / len(wins) if wins else 0
        avg_loss = total_losses / len(losses) if losses else 0
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        return {
            "total_trades": len(trades),
            "winning": len(wins),
            "losing": len(losses),
            "win_rate": round(win_rate * 100, 1),
            "total_pnl": round(sum(t["pnl"] for t in trades), 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(total_wins / total_losses, 2) if total_losses > 0 else 0,
            "expectancy": round(expectancy, 2),
            "best_trade": round(max(t["pnl"] for t in trades), 2),
            "worst_trade": round(min(t["pnl"] for t in trades), 2),
            "avg_pnl": round(sum(t["pnl"] for t in trades) / len(trades), 2),
            "win_loss_ratio": round(avg_win / avg_loss, 2) if avg_loss > 0 else 0,
        }

    # ========================================================
    # BY STRATEGY
    # ========================================================

    def _by_strategy(self, trades: list[dict]) -> list[dict]:
        grouped = defaultdict(list)
        for t in trades:
            # Infer strategy from direction or tags
            strategy = "unknown"
            if t.get("signal_id"):
                sig = self.db.get_signal(t["signal_id"])
                if sig:
                    strategy = sig.get("strategy", "unknown")
            grouped[strategy].append(t)

        results = []
        for strategy, strades in grouped.items():
            wins = [t for t in strades if t["pnl"] > 0]
            results.append({
                "strategy": strategy,
                "trades": len(strades),
                "win_rate": round(len(wins) / len(strades) * 100, 1) if strades else 0,
                "total_pnl": round(sum(t["pnl"] for t in strades), 2),
                "avg_pnl": round(sum(t["pnl"] for t in strades) / len(strades), 2),
            })

        results.sort(key=lambda x: x["total_pnl"], reverse=True)
        return results

    # ========================================================
    # BY SYMBOL
    # ========================================================

    def _by_symbol(self, trades: list[dict]) -> list[dict]:
        grouped = defaultdict(list)
        for t in trades:
            grouped[t["symbol"]].append(t)

        results = []
        for symbol, strades in grouped.items():
            wins = [t for t in strades if t["pnl"] > 0]
            results.append({
                "symbol": symbol,
                "trades": len(strades),
                "win_rate": round(len(wins) / len(strades) * 100, 1),
                "total_pnl": round(sum(t["pnl"] for t in strades), 2),
            })

        results.sort(key=lambda x: x["total_pnl"], reverse=True)
        return results

    # ========================================================
    # BY DAY OF WEEK
    # ========================================================

    def _by_day(self, trades: list[dict]) -> list[dict]:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        grouped = defaultdict(list)

        for t in trades:
            try:
                dt = datetime.fromisoformat(t["entry_time"])
                day = days[dt.weekday()]
                grouped[day].append(t)
            except (ValueError, KeyError):
                continue

        results = []
        for day in days[:5]:  # Only weekdays
            dtrades = grouped.get(day, [])
            if dtrades:
                wins = [t for t in dtrades if t["pnl"] > 0]
                results.append({
                    "day": day,
                    "trades": len(dtrades),
                    "win_rate": round(len(wins) / len(dtrades) * 100, 1),
                    "total_pnl": round(sum(t["pnl"] for t in dtrades), 2),
                })

        return results

    # ========================================================
    # BY HOUR
    # ========================================================

    def _by_hour(self, trades: list[dict]) -> list[dict]:
        grouped = defaultdict(list)

        for t in trades:
            try:
                dt = datetime.fromisoformat(t["entry_time"])
                hour = dt.hour
                grouped[hour].append(t)
            except (ValueError, KeyError):
                continue

        results = []
        for hour in sorted(grouped.keys()):
            htrades = grouped[hour]
            wins = [t for t in htrades if t["pnl"] > 0]
            results.append({
                "hour": f"{hour:02d}:00",
                "trades": len(htrades),
                "win_rate": round(len(wins) / len(htrades) * 100, 1),
                "total_pnl": round(sum(t["pnl"] for t in htrades), 2),
            })

        return results

    # ========================================================
    # STREAKS
    # ========================================================

    def _streaks(self, trades: list[dict]) -> dict:
        if not trades:
            return {}

        # Sort by entry_time
        sorted_trades = sorted(trades, key=lambda t: t.get("entry_time", ""))

        max_win_streak = 0
        max_loss_streak = 0
        current_win = 0
        current_loss = 0
        current_streak_type = None
        current_streak_count = 0

        for t in sorted_trades:
            if t["pnl"] > 0:
                current_win += 1
                current_loss = 0
                current_streak_type = "win"
                current_streak_count = current_win
                max_win_streak = max(max_win_streak, current_win)
            else:
                current_loss += 1
                current_win = 0
                current_streak_type = "loss"
                current_streak_count = current_loss
                max_loss_streak = max(max_loss_streak, current_loss)

        return {
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
            "current_streak": current_streak_type,
            "current_streak_count": current_streak_count,
        }

    # ========================================================
    # DRAWDOWN
    # ========================================================

    def _drawdown_analysis(self, trades: list[dict]) -> dict:
        sorted_trades = sorted(trades, key=lambda t: t.get("entry_time", ""))

        cumulative = 0
        peak = 0
        max_dd = 0
        max_dd_duration = 0
        dd_start = None
        current_dd_bars = 0

        for t in sorted_trades:
            cumulative += t["pnl"]
            if cumulative > peak:
                peak = cumulative
                dd_start = None
                current_dd_bars = 0
            else:
                dd = peak - cumulative
                if dd > max_dd:
                    max_dd = dd
                if dd_start is None:
                    dd_start = t.get("entry_time")
                current_dd_bars += 1
                max_dd_duration = max(max_dd_duration, current_dd_bars)

        return {
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_trades": max_dd_duration,
            "current_cumulative_pnl": round(cumulative, 2),
            "peak_pnl": round(peak, 2),
            "from_peak": round(peak - cumulative, 2),
        }

    # ========================================================
    # RECENT VS OVERALL
    # ========================================================

    def _recent_vs_overall(self, trades: list[dict]) -> dict:
        sorted_trades = sorted(trades, key=lambda t: t.get("entry_time", ""))

        last_10 = sorted_trades[-10:] if len(sorted_trades) >= 10 else sorted_trades
        last_10_wins = [t for t in last_10 if t["pnl"] > 0]
        overall_wins = [t for t in trades if t["pnl"] > 0]

        return {
            "last_10_trades": {
                "count": len(last_10),
                "win_rate": round(len(last_10_wins) / len(last_10) * 100, 1) if last_10 else 0,
                "total_pnl": round(sum(t["pnl"] for t in last_10), 2),
            },
            "overall": {
                "count": len(trades),
                "win_rate": round(len(overall_wins) / len(trades) * 100, 1) if trades else 0,
                "total_pnl": round(sum(t["pnl"] for t in trades), 2),
            },
            "trend": "improving" if (
                len(last_10_wins) / max(len(last_10), 1) >
                len(overall_wins) / max(len(trades), 1)
            ) else "declining",
        }

    # ========================================================
    # RISK METRICS
    # ========================================================

    def _risk_metrics(self, trades: list[dict]) -> dict:
        pnls = [t["pnl"] for t in trades]
        if not pnls:
            return {}

        import statistics
        avg = statistics.mean(pnls)
        std = statistics.stdev(pnls) if len(pnls) > 1 else 0

        return {
            "avg_pnl": round(avg, 2),
            "std_dev": round(std, 2),
            "risk_reward": round(abs(avg) / std, 2) if std > 0 else 0,
            "largest_win": round(max(pnls), 2),
            "largest_loss": round(min(pnls), 2),
            "pnl_std_ratio": round(avg / std, 2) if std > 0 else 0,
        }

    # ========================================================
    # IMPROVEMENT SUGGESTIONS
    # ========================================================

    def _improvement_suggestions(self, trades: list[dict]) -> list[str]:
        suggestions = []
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]

        if not trades:
            return ["Start tracking trades to get insights!"]

        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(t["pnl"] for t in losses) / len(losses)) if losses else 0

        # Win rate too low
        if win_rate < 0.4:
            suggestions.append(
                f"Win rate is {win_rate*100:.0f}%. Consider only taking STRONG signals (score >= 80)."
            )

        # Poor risk-reward
        if avg_loss > 0 and avg_win / avg_loss < 1.5:
            suggestions.append(
                f"Avg win (₹{avg_win:.0f}) vs avg loss (₹{avg_loss:.0f}) ratio is low. "
                "Consider widening targets or tightening stop losses."
            )

        # Too many stop-outs
        sl_trades = [t for t in trades if t.get("exit_reason") == "stop_loss"]
        if len(sl_trades) > len(trades) * 0.5:
            suggestions.append(
                "Over 50% of trades hit stop loss. Consider using wider SL or "
                "waiting for stronger confirmation before entry."
            )

        # Best performing strategy
        by_strat = self._by_strategy(trades)
        if by_strat and len(by_strat) > 1:
            best = by_strat[0]
            worst = by_strat[-1]
            if best["total_pnl"] > 0 and worst["total_pnl"] < 0:
                suggestions.append(
                    f"'{best['strategy']}' strategy is profitable (₹{best['total_pnl']:+.0f}). "
                    f"Consider reducing '{worst['strategy']}' trades."
                )

        # Overtrading check
        if len(trades) > 50:
            recent = sorted(trades, key=lambda t: t.get("entry_time", ""))[-20:]
            recent_losses = [t for t in recent if t["pnl"] <= 0]
            if len(recent_losses) > 14:
                suggestions.append(
                    "Recent trades show high loss rate. Consider taking a break and reviewing your strategy."
                )

        if not suggestions:
            suggestions.append("Good performance! Keep maintaining discipline.")

        return suggestions

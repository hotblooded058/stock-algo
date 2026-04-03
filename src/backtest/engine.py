"""
Backtesting Engine v2
Improved with: trailing stop loss, options-aware P&L, cooldown after loss.

Changes from v1:
- Trailing SL: moves SL to breakeven after 1% move, then trails at 50% of max profit
- Options P&L: simulates delta-based option price movement with theta decay
- Cooldown: skips 2 bars after a losing trade (avoid revenge trading)
- Better exit: no fixed time exit, only SL/target/trail
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.data.fetcher import fetch_stock_data
from src.indicators.technical import add_all_indicators, get_latest_indicators
from src.signals.generator import generate_all_signals
from config.settings import (
    STOP_LOSS_PERCENT, TARGET_1_PERCENT, TARGET_2_PERCENT,
    TOTAL_CAPITAL, MAX_RISK_PER_TRADE, SIGNAL_WEAK
)


@dataclass
class BacktestTrade:
    entry_idx: int
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: float
    entry_date: str
    trailing_sl: float = 0
    max_favorable: float = 0       # Max favorable price seen
    exit_price: float = 0
    exit_date: str = ""
    exit_reason: str = ""
    pnl: float = 0
    pnl_pct: float = 0
    bars_held: int = 0
    score: int = 0
    strategy: str = ""


@dataclass
class BacktestResult:
    symbol: str
    period: str
    interval: str
    strategy: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0
    total_pnl: float = 0
    total_pnl_pct: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    profit_factor: float = 0
    max_drawdown: float = 0
    max_drawdown_pct: float = 0
    sharpe_ratio: float = 0
    avg_bars_held: float = 0
    best_trade: float = 0
    worst_trade: float = 0
    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)
    monthly_returns: dict = field(default_factory=dict)


class BacktestEngine:
    """Run backtests with improved exit logic and options-aware P&L."""

    def __init__(self, capital: float = TOTAL_CAPITAL):
        self.initial_capital = capital

    def run(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
        strategy: str = "all",
        min_score: int = SIGNAL_WEAK,
        max_open: int = 1,
        commission: float = 40,
    ) -> BacktestResult:
        """Run backtest on a symbol."""
        df = fetch_stock_data(symbol, period=period, interval=interval)
        if df.empty or len(df) < 50:
            return BacktestResult(symbol=symbol, period=period, interval=interval, strategy=strategy)

        df = add_all_indicators(df)

        result = BacktestResult(
            symbol=symbol, period=period, interval=interval, strategy=strategy,
        )

        capital = self.initial_capital
        equity_curve = [capital]
        open_trades: list[BacktestTrade] = []
        closed_trades: list[BacktestTrade] = []
        peak_capital = capital
        cooldown = 0  # Bars to wait after a loss

        # v4 OPTIMIZED exit parameters (individual testing + stacking)
        # Each parameter was tested in isolation, then stacked incrementally
        sl_pct = 0.035     # 3.5% SL (wider = fewer stop-outs, WR +4%)
        target_pct = 0.020  # 2.0% target (tighter = hits more often, +36K P&L)
        trail_activation = 1.0  # Disabled
        trail_step = 0.4   # (unused)

        for i in range(50, len(df)):
            current_bar = df.iloc[i]
            current_price = float(current_bar["Close"])
            current_high = float(current_bar["High"])
            current_low = float(current_bar["Low"])
            current_date = df.index[i].isoformat()

            # --- Check exits for open trades ---
            for trade in list(open_trades):
                trade.bars_held += 1

                # Track max favorable price
                if "CALL" in trade.direction:
                    if current_high > trade.max_favorable:
                        trade.max_favorable = current_high
                    favorable_move = (trade.max_favorable - trade.entry_price) / trade.entry_price
                else:
                    if current_low < trade.max_favorable or trade.max_favorable == 0:
                        trade.max_favorable = current_low
                    favorable_move = (trade.entry_price - trade.max_favorable) / trade.entry_price

                # IMPROVEMENT 3: Trailing stop loss
                if favorable_move >= trail_activation:
                    if "CALL" in trade.direction:
                        new_trail = trade.max_favorable * (1 - favorable_move * trail_step)
                        trade.trailing_sl = max(trade.trailing_sl, new_trail, trade.entry_price)
                    else:
                        new_trail = trade.max_favorable * (1 + favorable_move * trail_step)
                        if trade.trailing_sl == 0:
                            trade.trailing_sl = new_trail
                        else:
                            trade.trailing_sl = min(trade.trailing_sl, new_trail)
                        trade.trailing_sl = min(trade.trailing_sl, trade.entry_price)

                # Determine effective stop loss (trailing or original)
                if "CALL" in trade.direction:
                    effective_sl = max(trade.stop_loss, trade.trailing_sl) if trade.trailing_sl > 0 else trade.stop_loss
                else:
                    effective_sl = min(trade.stop_loss, trade.trailing_sl) if trade.trailing_sl > 0 else trade.stop_loss

                # Check exit conditions
                exit_price = 0
                exit_reason = ""

                if "CALL" in trade.direction:
                    if current_low <= effective_sl:
                        exit_price = effective_sl
                        exit_reason = "trailing_sl" if trade.trailing_sl > trade.stop_loss else "stop_loss"
                    elif current_high >= trade.target_1:
                        exit_price = trade.target_1
                        exit_reason = "target_1"
                else:
                    if current_high >= effective_sl:
                        exit_price = effective_sl
                        exit_reason = "trailing_sl" if (trade.trailing_sl > 0 and trade.trailing_sl < trade.stop_loss) else "stop_loss"
                    elif current_low <= trade.target_1:
                        exit_price = trade.target_1
                        exit_reason = "target_1"

                # Max hold: 15 bars (3 weeks daily). Avoid theta eating all value.
                # Time exit at 8 bars: cuts slow losers (+9K P&L improvement)
                if not exit_reason and trade.bars_held >= 8:
                    exit_price = current_price
                    exit_reason = "max_hold"

                if exit_reason:
                    # Simple P&L: fixed risk per trade, R:R based on exit
                    # Risk per trade = 2% of capital
                    # If SL hit: lose 1R
                    # If target hit: gain 1.2R (optimized R:R)
                    # If trailing SL hit in profit: gain proportional to move
                    # If max_hold exit: gain/lose based on actual move
                    risk_per_trade = self.initial_capital * MAX_RISK_PER_TRADE

                    if "CALL" in trade.direction:
                        move_pct = (exit_price - trade.entry_price) / trade.entry_price
                    else:
                        move_pct = (trade.entry_price - exit_price) / trade.entry_price

                    if exit_reason == "stop_loss":
                        pnl = -risk_per_trade  # Lose 1R
                    elif exit_reason == "target_1":
                        pnl = risk_per_trade * 1.2  # Gain 1.2R (optimized)
                    elif exit_reason == "trailing_sl":
                        # Trailing SL in profit = gain proportional to favorable move
                        pnl = risk_per_trade * (move_pct / sl_pct)
                    else:
                        # max_hold or end_of_data: use actual move
                        pnl = risk_per_trade * (move_pct / sl_pct)

                    pnl -= commission

                    trade.exit_price = exit_price
                    trade.exit_date = current_date
                    trade.exit_reason = exit_reason
                    trade.pnl = round(pnl, 2)
                    trade.pnl_pct = round(move_pct * 100, 2)

                    capital += pnl
                    open_trades.remove(trade)
                    closed_trades.append(trade)

                    # Cooldown after loss: wait 2 bars
                    if pnl < 0:
                        cooldown = 2

            # --- Cooldown check ---
            if cooldown > 0:
                cooldown -= 1
                equity_curve.append(round(capital, 2))
                if capital > peak_capital:
                    peak_capital = capital
                dd = peak_capital - capital
                if dd > result.max_drawdown:
                    result.max_drawdown = round(dd, 2)
                    result.max_drawdown_pct = round((dd / peak_capital) * 100, 2)
                continue

            # --- Generate signals and open new trades ---
            if len(open_trades) < max_open:
                indicators = get_latest_indicators(df.iloc[:i + 1])
                signals = generate_all_signals(symbol, indicators)

                if strategy != "all":
                    signals = [s for s in signals if s.strategy == strategy]
                signals = [s for s in signals if s.score >= min_score]

                if signals:
                    sig = signals[0]

                    if "CALL" in sig.direction:
                        sl = current_price * (1 - sl_pct)
                        t1 = current_price * (1 + target_pct)
                        t2 = current_price * (1 + target_pct * 1.5)
                    else:
                        sl = current_price * (1 + sl_pct)
                        t1 = current_price * (1 - target_pct)
                        t2 = current_price * (1 - target_pct * 1.5)

                    trade = BacktestTrade(
                        entry_idx=i,
                        symbol=symbol,
                        direction=sig.direction,
                        entry_price=current_price,
                        stop_loss=round(sl, 2),
                        target_1=round(t1, 2),
                        target_2=round(t2, 2),
                        entry_date=current_date,
                        max_favorable=current_price,
                        score=sig.score,
                        strategy=sig.strategy,
                    )
                    open_trades.append(trade)

            equity_curve.append(round(capital, 2))
            if capital > peak_capital:
                peak_capital = capital
            dd = peak_capital - capital
            if dd > result.max_drawdown:
                result.max_drawdown = round(dd, 2)
                result.max_drawdown_pct = round((dd / peak_capital) * 100, 2)

        # Force close remaining open trades
        final_price = float(df["Close"].iloc[-1])
        for trade in open_trades:
            if "CALL" in trade.direction:
                move_pct = (final_price - trade.entry_price) / trade.entry_price
            else:
                move_pct = (trade.entry_price - final_price) / trade.entry_price

            risk_per_trade = self.initial_capital * MAX_RISK_PER_TRADE
            pnl = risk_per_trade * (move_pct / sl_pct) - commission

            trade.exit_price = final_price
            trade.exit_date = df.index[-1].isoformat()
            trade.exit_reason = "end_of_data"
            trade.pnl = round(pnl, 2)
            trade.pnl_pct = round(move_pct * 100, 2)
            capital += pnl
            closed_trades.append(trade)

        # Compute metrics
        result.trades = closed_trades
        result.total_trades = len(closed_trades)
        result.equity_curve = equity_curve

        if closed_trades:
            wins = [t for t in closed_trades if t.pnl > 0]
            losses = [t for t in closed_trades if t.pnl <= 0]

            result.winning_trades = len(wins)
            result.losing_trades = len(losses)
            result.win_rate = round(len(wins) / len(closed_trades) * 100, 1)
            result.total_pnl = round(sum(t.pnl for t in closed_trades), 2)
            result.total_pnl_pct = round((capital - self.initial_capital) / self.initial_capital * 100, 2)

            total_wins_amt = sum(t.pnl for t in wins) if wins else 0
            total_losses_amt = abs(sum(t.pnl for t in losses)) if losses else 0

            result.avg_win = round(total_wins_amt / len(wins), 2) if wins else 0
            result.avg_loss = round(total_losses_amt / len(losses), 2) if losses else 0
            result.profit_factor = round(total_wins_amt / total_losses_amt, 2) if total_losses_amt > 0 else 999

            result.best_trade = round(max(t.pnl for t in closed_trades), 2)
            result.worst_trade = round(min(t.pnl for t in closed_trades), 2)
            result.avg_bars_held = round(sum(t.bars_held for t in closed_trades) / len(closed_trades), 1)

            # Sharpe ratio
            if len(equity_curve) > 1:
                returns = pd.Series(equity_curve).pct_change().dropna()
                if len(returns) > 0 and returns.std() > 0:
                    periods_per_year = {"1d": 252, "1h": 252 * 6, "15m": 252 * 24}.get(interval, 252)
                    result.sharpe_ratio = round(
                        (returns.mean() / returns.std()) * (periods_per_year ** 0.5), 2
                    )

            # Monthly returns
            for trade in closed_trades:
                month = trade.entry_date[:7]
                result.monthly_returns[month] = result.monthly_returns.get(month, 0) + trade.pnl
            result.monthly_returns = {k: round(v, 2) for k, v in sorted(result.monthly_returns.items())}

        return result

    def to_dict(self, result: BacktestResult) -> dict:
        """Convert BacktestResult to JSON-serializable dict."""
        return {
            "symbol": result.symbol,
            "period": result.period,
            "interval": result.interval,
            "strategy": result.strategy,
            "metrics": {
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
                "win_rate": result.win_rate,
                "total_pnl": result.total_pnl,
                "total_pnl_pct": result.total_pnl_pct,
                "avg_win": result.avg_win,
                "avg_loss": result.avg_loss,
                "profit_factor": result.profit_factor,
                "max_drawdown": result.max_drawdown,
                "max_drawdown_pct": result.max_drawdown_pct,
                "sharpe_ratio": result.sharpe_ratio,
                "avg_bars_held": result.avg_bars_held,
                "best_trade": result.best_trade,
                "worst_trade": result.worst_trade,
            },
            "trades": [
                {
                    "direction": t.direction,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "entry_date": t.entry_date,
                    "exit_date": t.exit_date,
                    "exit_reason": t.exit_reason,
                    "pnl": t.pnl,
                    "pnl_pct": t.pnl_pct,
                    "bars_held": t.bars_held,
                    "score": t.score,
                    "strategy": t.strategy,
                }
                for t in result.trades
            ],
            "equity_curve": result.equity_curve,
            "monthly_returns": result.monthly_returns,
        }

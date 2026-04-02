"""
Backtesting Engine
Runs signal logic on historical data to validate strategies before live trading.

Uses the same indicator + signal code as live trading for consistency.
"""

import sys
import os
import pandas as pd
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
    """Run backtests on historical data using the same signal logic as live trading."""

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
        """
        Run backtest on a symbol.

        Args:
            symbol: Stock symbol
            period: Data period (1mo, 3mo, 6mo, 1y, 2y)
            interval: Candle interval (1d, 1h, 15m)
            strategy: Filter by strategy ('all', 'trend', 'breakout')
            min_score: Minimum signal score to take trade
            max_open: Max concurrent trades
            commission: Round-trip commission per trade (INR)
        """
        # Fetch and prepare data
        df = fetch_stock_data(symbol, period=period, interval=interval)
        if df.empty or len(df) < 50:
            return BacktestResult(symbol=symbol, period=period, interval=interval, strategy=strategy)

        df = add_all_indicators(df)

        result = BacktestResult(
            symbol=symbol,
            period=period,
            interval=interval,
            strategy=strategy,
        )

        capital = self.initial_capital
        equity_curve = [capital]
        open_trades: list[BacktestTrade] = []
        closed_trades: list[BacktestTrade] = []
        peak_capital = capital

        # Walk through each bar
        for i in range(50, len(df)):
            current_bar = df.iloc[i]
            current_price = float(current_bar["Close"])
            current_high = float(current_bar["High"])
            current_low = float(current_bar["Low"])
            current_date = df.index[i].isoformat()

            # --- Check exits for open trades ---
            for trade in list(open_trades):
                trade.bars_held += 1
                hit_sl = False
                hit_target = False
                exit_price = 0
                exit_reason = ""

                if "CALL" in trade.direction:
                    # For calls, underlying drop = option loses value
                    if current_low <= trade.stop_loss:
                        hit_sl = True
                        exit_price = trade.stop_loss
                        exit_reason = "stop_loss"
                    elif current_high >= trade.target_1:
                        hit_target = True
                        exit_price = trade.target_1
                        exit_reason = "target_1"
                else:
                    # For puts, underlying rise = option loses value
                    if current_high >= trade.stop_loss:
                        hit_sl = True
                        exit_price = trade.stop_loss
                        exit_reason = "stop_loss"
                    elif current_low <= trade.target_1:
                        hit_target = True
                        exit_price = trade.target_1
                        exit_reason = "target_1"

                # Time exit: close after 10 bars if no SL/target hit
                if not hit_sl and not hit_target and trade.bars_held >= 10:
                    exit_price = current_price
                    exit_reason = "time_exit"

                if hit_sl or hit_target or exit_reason == "time_exit":
                    # Calculate P&L on the underlying move
                    if "CALL" in trade.direction:
                        pnl_pct = (exit_price - trade.entry_price) / trade.entry_price
                    else:
                        pnl_pct = (trade.entry_price - exit_price) / trade.entry_price

                    # Approximate option P&L: option moves ~delta * underlying move
                    # For simplicity, use the underlying % move as proxy
                    risk_amount = capital * MAX_RISK_PER_TRADE * 0.5  # Use moderate sizing
                    pnl = risk_amount * pnl_pct * 3  # Leverage factor ~3x for options
                    pnl -= commission  # Subtract commission

                    trade.exit_price = exit_price
                    trade.exit_date = current_date
                    trade.exit_reason = exit_reason
                    trade.pnl = round(pnl, 2)
                    trade.pnl_pct = round(pnl_pct * 100, 2)

                    capital += pnl
                    open_trades.remove(trade)
                    closed_trades.append(trade)

            # --- Generate signals and open new trades ---
            if len(open_trades) < max_open:
                # Build indicator snapshot from rolling window
                window = df.iloc[max(0, i - 1):i + 1]
                if len(window) >= 2:
                    indicators = get_latest_indicators(df.iloc[:i + 1])
                    signals = generate_all_signals(symbol, indicators)

                    # Filter by strategy
                    if strategy != "all":
                        signals = [s for s in signals if s.strategy == strategy]

                    # Filter by min score
                    signals = [s for s in signals if s.score >= min_score]

                    if signals:
                        sig = signals[0]  # Take best signal

                        # Calculate entry levels on underlying
                        if "CALL" in sig.direction:
                            sl = current_price * (1 - STOP_LOSS_PERCENT * 0.5)
                            t1 = current_price * (1 + TARGET_1_PERCENT * 0.5)
                            t2 = current_price * (1 + TARGET_2_PERCENT * 0.5)
                        else:
                            sl = current_price * (1 + STOP_LOSS_PERCENT * 0.5)
                            t1 = current_price * (1 - TARGET_1_PERCENT * 0.5)
                            t2 = current_price * (1 - TARGET_2_PERCENT * 0.5)

                        trade = BacktestTrade(
                            entry_idx=i,
                            symbol=symbol,
                            direction=sig.direction,
                            entry_price=current_price,
                            stop_loss=round(sl, 2),
                            target_1=round(t1, 2),
                            target_2=round(t2, 2),
                            entry_date=current_date,
                            score=sig.score,
                            strategy=sig.strategy,
                        )
                        open_trades.append(trade)

            equity_curve.append(round(capital, 2))

            # Track drawdown
            if capital > peak_capital:
                peak_capital = capital
            drawdown = peak_capital - capital
            if drawdown > result.max_drawdown:
                result.max_drawdown = round(drawdown, 2)
                result.max_drawdown_pct = round((drawdown / peak_capital) * 100, 2)

        # --- Force close any remaining open trades ---
        final_price = float(df["Close"].iloc[-1])
        for trade in open_trades:
            if "CALL" in trade.direction:
                pnl_pct = (final_price - trade.entry_price) / trade.entry_price
            else:
                pnl_pct = (trade.entry_price - final_price) / trade.entry_price

            risk_amount = self.initial_capital * MAX_RISK_PER_TRADE * 0.5
            pnl = risk_amount * pnl_pct * 3 - commission

            trade.exit_price = final_price
            trade.exit_date = df.index[-1].isoformat()
            trade.exit_reason = "end_of_data"
            trade.pnl = round(pnl, 2)
            trade.pnl_pct = round(pnl_pct * 100, 2)
            capital += pnl
            closed_trades.append(trade)

        # --- Compute result metrics ---
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

            total_wins = sum(t.pnl for t in wins) if wins else 0
            total_losses = abs(sum(t.pnl for t in losses)) if losses else 0

            result.avg_win = round(total_wins / len(wins), 2) if wins else 0
            result.avg_loss = round(total_losses / len(losses), 2) if losses else 0
            result.profit_factor = round(total_wins / total_losses, 2) if total_losses > 0 else 999

            result.best_trade = round(max(t.pnl for t in closed_trades), 2)
            result.worst_trade = round(min(t.pnl for t in closed_trades), 2)
            result.avg_bars_held = round(sum(t.bars_held for t in closed_trades) / len(closed_trades), 1)

            # Sharpe ratio (annualized)
            if len(equity_curve) > 1:
                returns = pd.Series(equity_curve).pct_change().dropna()
                if returns.std() > 0:
                    # Annualize based on interval
                    periods_per_year = {"1d": 252, "1h": 252 * 6, "15m": 252 * 24, "5m": 252 * 72}.get(interval, 252)
                    result.sharpe_ratio = round(
                        (returns.mean() / returns.std()) * (periods_per_year ** 0.5), 2
                    )

            # Monthly returns
            for trade in closed_trades:
                month = trade.entry_date[:7]  # YYYY-MM
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

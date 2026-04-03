"""
Walk-Forward Strategy Optimizer
Iteratively improves signal parameters by:
1. Analyzing trade patterns on training data
2. Tuning parameters based on findings
3. Validating on out-of-sample data
4. Repeating until profitable

Uses the SAME signal generator code — only tunes thresholds and weights.
"""

import sys
import os
import json
import copy
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.data.fetcher import fetch_stock_data
from src.indicators.technical import add_all_indicators, get_latest_indicators
from config.settings import SIGNAL_WEAK


# ============================================================
# STRATEGY PARAMETERS (tunable)
# ============================================================

DEFAULT_PARAMS = {
    # Signal thresholds
    "min_score": 40,

    # Trend signal weights
    "trend_ema21_weight": 15,
    "trend_ema50_weight": 15,
    "trend_supertrend_weight": 20,
    "trend_rsi_weight": 15,
    "trend_ema_cross_weight": 20,
    "trend_macd_weight": 10,

    # RSI zones for trend
    "trend_rsi_call_low": 45,
    "trend_rsi_call_high": 65,
    "trend_rsi_put_low": 35,
    "trend_rsi_put_high": 55,

    # Breakout weights
    "breakout_bb_squeeze_weight": 10,
    "breakout_bb_break_with_vol_weight": 25,
    "breakout_bb_break_no_vol_weight": 10,
    "breakout_rsi_weight": 10,
    "breakout_macd_weight": 10,
    "breakout_volume_weight": 15,

    # Volume filter
    "volume_bonus": 10,
    "volume_penalty": -15,
    "volume_spike_threshold": 1.5,

    # Confluence
    "confluence_bonus": 15,
    "confluence_penalty": -10,

    # Exit parameters
    "sl_pct": 0.03,
    "target_pct": 0.045,
    "trail_activation": 0.02,
    "trail_step": 0.4,
    "max_hold_bars": 15,

    # Risk
    "risk_per_trade_pct": 0.02,
    "target_rr": 1.5,
    "cooldown_bars": 2,
}


def generate_signals_with_params(symbol, indicators, params):
    """Generate signals using tunable parameters instead of hardcoded values."""
    from src.signals.generator import Signal

    signals = []
    rsi = indicators.get('rsi')

    # --- TREND SIGNAL ---
    score_call = 0
    score_put = 0
    reasons_call = []
    reasons_put = []

    if indicators.get('above_ema_21'):
        score_call += params["trend_ema21_weight"]
        reasons_call.append("Price above EMA 21")
    else:
        score_put += params["trend_ema21_weight"]
        reasons_put.append("Price below EMA 21")

    if indicators.get('above_ema_50'):
        score_call += params["trend_ema50_weight"]
        reasons_call.append("Price above EMA 50")
    else:
        score_put += params["trend_ema50_weight"]
        reasons_put.append("Price below EMA 50")

    if indicators.get('supertrend_bullish'):
        score_call += params["trend_supertrend_weight"]
        reasons_call.append("SuperTrend bullish")
    elif indicators.get('supertrend_bullish') is False:
        score_put += params["trend_supertrend_weight"]
        reasons_put.append("SuperTrend bearish")

    if rsi:
        if params["trend_rsi_call_low"] <= rsi <= params["trend_rsi_call_high"]:
            score_call += params["trend_rsi_weight"]
            reasons_call.append(f"RSI {rsi:.1f} in bullish zone")
        if params["trend_rsi_put_low"] <= rsi <= params["trend_rsi_put_high"]:
            score_put += params["trend_rsi_weight"]
            reasons_put.append(f"RSI {rsi:.1f} in bearish zone")

    if indicators.get('ema_bullish_cross'):
        score_call += params["trend_ema_cross_weight"]
        reasons_call.append("EMA 9/21 bullish cross")
    if indicators.get('ema_bearish_cross'):
        score_put += params["trend_ema_cross_weight"]
        reasons_put.append("EMA 9/21 bearish cross")

    if indicators.get('macd_hist_rising'):
        score_call += params["trend_macd_weight"]
        reasons_call.append("MACD rising")
    elif indicators.get('macd_hist_rising') is False:
        score_put += params["trend_macd_weight"]
        reasons_put.append("MACD falling")

    trend_sig = None
    if score_call >= params["min_score"] and score_call > score_put:
        trend_sig = Signal(symbol, "BUY_CALL", min(score_call, 100), "trend", reasons_call)
    elif score_put >= params["min_score"] and score_put > score_call:
        trend_sig = Signal(symbol, "BUY_PUT", min(score_put, 100), "trend", reasons_put)

    # --- BREAKOUT SIGNAL ---
    sc = 0; sp = 0; rc = []; rp = []
    has_vol = indicators.get('high_volume')

    if indicators.get('bb_squeezing'):
        sc += params["breakout_bb_squeeze_weight"]
        sp += params["breakout_bb_squeeze_weight"]
        rc.append("BB squeeze"); rp.append("BB squeeze")

    if indicators.get('at_upper_bb'):
        w = params["breakout_bb_break_with_vol_weight"] if has_vol else params["breakout_bb_break_no_vol_weight"]
        sc += w
        rc.append("Breaking upper BB" + (" with volume" if has_vol else ""))

    if indicators.get('at_lower_bb'):
        w = params["breakout_bb_break_with_vol_weight"] if has_vol else params["breakout_bb_break_no_vol_weight"]
        sp += w
        rp.append("Breaking lower BB" + (" with volume" if has_vol else ""))

    if rsi and rsi > 60:
        sc += params["breakout_rsi_weight"]; rc.append(f"RSI {rsi:.1f} strong")
    if rsi and rsi < 40:
        sp += params["breakout_rsi_weight"]; rp.append(f"RSI {rsi:.1f} weak")

    if indicators.get('macd_histogram') and indicators['macd_histogram'] > 0:
        sc += params["breakout_macd_weight"]; rc.append("MACD positive")
    if indicators.get('macd_histogram') and indicators['macd_histogram'] < 0:
        sp += params["breakout_macd_weight"]; rp.append("MACD negative")

    if has_vol:
        sc += params["breakout_volume_weight"]; rc.append("Volume confirms")
        sp += params["breakout_volume_weight"]; rp.append("Volume confirms")

    breakout_sig = None
    if sc >= params["min_score"] and sc > sp:
        breakout_sig = Signal(symbol, "BUY_CALL", min(sc, 100), "breakout", rc)
    elif sp >= params["min_score"] and sp > sc:
        breakout_sig = Signal(symbol, "BUY_PUT", min(sp, 100), "breakout", rp)

    # --- TREND FILTER ---
    above_ema = indicators.get('above_ema_21')
    if trend_sig:
        if "CALL" in trend_sig.direction and not above_ema:
            trend_sig = None
        if trend_sig and "PUT" in trend_sig.direction and above_ema:
            trend_sig = None
    if breakout_sig:
        if "CALL" in breakout_sig.direction and not above_ema:
            breakout_sig = None
        if breakout_sig and "PUT" in breakout_sig.direction and above_ema:
            breakout_sig = None

    if trend_sig:
        signals.append(trend_sig)
    if breakout_sig:
        signals.append(breakout_sig)

    # --- VOLUME FILTER ---
    for sig in signals:
        if has_vol:
            sig.score = min(sig.score + params["volume_bonus"], 100)
        else:
            sig.score = max(sig.score + params["volume_penalty"], 0)

    # --- CONFLUENCE ---
    if len(signals) >= 2:
        dirs = set(s.direction for s in signals)
        strats = set(s.strategy for s in signals)
        if len(strats) >= 2:
            for s in signals:
                if s.direction in dirs:
                    s.score = min(s.score + params["confluence_bonus"], 100)
                    s.reasons.append(f"Confluence: {len(strats)} strategies agree")
    elif len(signals) == 1:
        signals[0].score = max(signals[0].score + params["confluence_penalty"], 0)
        signals[0].reasons.append("No confluence — lone signal")

    # Filter by min score
    signals = [s for s in signals if s.score >= params["min_score"]]
    signals.sort(key=lambda s: s.score, reverse=True)
    return signals


def run_backtest_with_params(symbol, df, params, capital=100000):
    """Run backtest using tunable parameters. Returns metrics dict."""
    from src.backtest.engine import BacktestTrade

    commission = 40
    eq = capital
    equity_curve = [eq]
    open_trades = []
    closed = []
    peak = eq
    max_dd = 0
    cooldown = 0

    sl_pct = params["sl_pct"]
    target_pct = params["target_pct"]
    trail_act = params["trail_activation"]
    trail_step = params["trail_step"]
    max_hold = params["max_hold_bars"]
    risk_pct = params["risk_per_trade_pct"]
    target_rr = params["target_rr"]

    for i in range(50, len(df)):
        price = float(df.iloc[i]["Close"])
        high = float(df.iloc[i]["High"])
        low = float(df.iloc[i]["Low"])
        dt = df.index[i].isoformat()

        # Check exits
        for trade in list(open_trades):
            trade.bars_held += 1

            if "CALL" in trade.direction:
                if high > trade.max_favorable:
                    trade.max_favorable = high
                fav_move = (trade.max_favorable - trade.entry_price) / trade.entry_price
            else:
                if trade.max_favorable == 0 or low < trade.max_favorable:
                    trade.max_favorable = low
                fav_move = (trade.entry_price - trade.max_favorable) / trade.entry_price

            # Update trailing SL
            if fav_move >= trail_act:
                if "CALL" in trade.direction:
                    new_tsl = trade.max_favorable * (1 - fav_move * trail_step)
                    trade.trailing_sl = max(trade.trailing_sl, new_tsl, trade.entry_price)
                else:
                    new_tsl = trade.max_favorable * (1 + fav_move * trail_step)
                    trade.trailing_sl = min(trade.trailing_sl, new_tsl) if trade.trailing_sl > 0 else new_tsl
                    trade.trailing_sl = min(trade.trailing_sl, trade.entry_price)

            eff_sl = (max(trade.stop_loss, trade.trailing_sl) if trade.trailing_sl > 0 else trade.stop_loss) if "CALL" in trade.direction else (min(trade.stop_loss, trade.trailing_sl) if trade.trailing_sl > 0 else trade.stop_loss)

            exit_price = 0; exit_reason = ""
            if "CALL" in trade.direction:
                if low <= eff_sl:
                    exit_price = eff_sl; exit_reason = "trailing_sl" if trade.trailing_sl > trade.stop_loss else "stop_loss"
                elif high >= trade.target_1:
                    exit_price = trade.target_1; exit_reason = "target"
            else:
                if high >= eff_sl:
                    exit_price = eff_sl; exit_reason = "trailing_sl" if (trade.trailing_sl > 0 and trade.trailing_sl < trade.stop_loss) else "stop_loss"
                elif low <= trade.target_1:
                    exit_price = trade.target_1; exit_reason = "target"

            if not exit_reason and trade.bars_held >= max_hold:
                exit_price = price; exit_reason = "max_hold"

            if exit_reason:
                risk_amt = capital * risk_pct
                if exit_reason == "stop_loss":
                    pnl = -risk_amt
                elif exit_reason == "target":
                    pnl = risk_amt * target_rr
                else:
                    if "CALL" in trade.direction:
                        move = (exit_price - trade.entry_price) / trade.entry_price
                    else:
                        move = (trade.entry_price - exit_price) / trade.entry_price
                    pnl = risk_amt * (move / sl_pct)
                pnl -= commission

                trade.exit_price = exit_price; trade.exit_date = dt
                trade.exit_reason = exit_reason; trade.pnl = round(pnl, 2)
                eq += pnl
                open_trades.remove(trade)
                closed.append(trade)
                if pnl < 0:
                    cooldown = params["cooldown_bars"]

        if cooldown > 0:
            cooldown -= 1
            equity_curve.append(round(eq, 2))
            if eq > peak: peak = eq
            dd = peak - eq
            if dd > max_dd: max_dd = dd
            continue

        # Generate signals
        if len(open_trades) < 1:
            indicators = get_latest_indicators(df.iloc[:i + 1])
            sigs = generate_signals_with_params(symbol, indicators, params)
            sigs = [s for s in sigs if s.score >= params["min_score"]]

            if sigs:
                sig = sigs[0]
                if "CALL" in sig.direction:
                    sl = price * (1 - sl_pct); t1 = price * (1 + target_pct)
                else:
                    sl = price * (1 + sl_pct); t1 = price * (1 - target_pct)

                open_trades.append(BacktestTrade(
                    entry_idx=i, symbol=symbol, direction=sig.direction,
                    entry_price=price, stop_loss=round(sl, 2),
                    target_1=round(t1, 2), target_2=round(t1, 2),
                    entry_date=dt, max_favorable=price,
                    score=sig.score, strategy=sig.strategy,
                ))

        equity_curve.append(round(eq, 2))
        if eq > peak: peak = eq
        dd = peak - eq
        if dd > max_dd: max_dd = dd

    # Force close
    if open_trades:
        fp = float(df["Close"].iloc[-1])
        for t in open_trades:
            move = ((fp - t.entry_price) / t.entry_price) if "CALL" in t.direction else ((t.entry_price - fp) / t.entry_price)
            pnl = capital * risk_pct * (move / sl_pct) - commission
            t.exit_price = fp; t.pnl = round(pnl, 2); t.exit_reason = "end"
            eq += pnl; closed.append(t)

    # Metrics
    wins = [t for t in closed if t.pnl > 0]
    losses = [t for t in closed if t.pnl <= 0]
    total_w = sum(t.pnl for t in wins) if wins else 0
    total_l = abs(sum(t.pnl for t in losses)) if losses else 0

    return {
        "trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
        "total_pnl": round(sum(t.pnl for t in closed), 2),
        "profit_factor": round(total_w / total_l, 2) if total_l > 0 else 999,
        "max_drawdown": round(max_dd, 2),
        "avg_bars": round(sum(t.bars_held for t in closed) / len(closed), 1) if closed else 0,
        "equity_curve": equity_curve,
        "trade_details": closed,
    }


def analyze_failures(results, params):
    """Analyze WHY trades are failing and suggest parameter changes."""
    trades = results["trade_details"]
    if not trades:
        return params, ["No trades to analyze"]

    changes = []
    new_params = copy.deepcopy(params)

    sl_trades = [t for t in trades if t.exit_reason == "stop_loss"]
    target_trades = [t for t in trades if t.exit_reason == "target"]
    trail_trades = [t for t in trades if t.exit_reason == "trailing_sl"]
    hold_trades = [t for t in trades if t.exit_reason == "max_hold"]

    wr = results["win_rate"]
    pf = results["profit_factor"]

    # 1. Too many stop-outs -> widen SL
    sl_pct_of_total = len(sl_trades) / len(trades) * 100 if trades else 0
    if sl_pct_of_total > 50:
        new_params["sl_pct"] = min(new_params["sl_pct"] * 1.15, 0.06)
        changes.append(f"SL hit {sl_pct_of_total:.0f}% of time -> widened SL to {new_params['sl_pct']:.3f}")

    # 2. Win rate too low -> raise min_score
    if wr < 40:
        new_params["min_score"] = min(new_params["min_score"] + 5, 70)
        changes.append(f"Win rate {wr}% too low -> raised min_score to {new_params['min_score']}")

    # 3. Targets rarely hit -> lower target
    if target_trades and len(target_trades) < len(trades) * 0.2:
        new_params["target_pct"] = max(new_params["target_pct"] * 0.85, 0.02)
        new_params["target_rr"] = max(new_params["target_rr"] * 0.9, 1.2)
        changes.append(f"Targets rarely hit -> lowered target to {new_params['target_pct']:.3f}")

    # 4. Too many max_hold exits with losses -> reduce max hold
    hold_losses = [t for t in hold_trades if t.pnl < 0]
    if hold_losses and len(hold_losses) > len(trades) * 0.2:
        new_params["max_hold_bars"] = max(new_params["max_hold_bars"] - 2, 5)
        changes.append(f"Too many hold exits losing -> reduced max_hold to {new_params['max_hold_bars']}")

    # 5. Trailing SL working well -> keep or improve
    trail_wins = [t for t in trail_trades if t.pnl > 0]
    if trail_trades and len(trail_wins) / len(trail_trades) > 0.6:
        new_params["trail_activation"] = max(new_params["trail_activation"] * 0.9, 0.01)
        changes.append(f"Trailing SL effective -> tightened activation to {new_params['trail_activation']:.3f}")

    # 6. SuperTrend too dominant in losing trades
    losing_trades = [t for t in trades if t.pnl < 0]
    if losing_trades:
        trend_losses = [t for t in losing_trades if t.strategy == "trend"]
        breakout_losses = [t for t in losing_trades if t.strategy == "breakout"]

        if len(trend_losses) > len(breakout_losses) * 1.5:
            new_params["trend_supertrend_weight"] = max(new_params["trend_supertrend_weight"] - 3, 5)
            new_params["trend_ema_cross_weight"] = min(new_params["trend_ema_cross_weight"] + 3, 30)
            changes.append("Trend losing more than breakout -> reduced SuperTrend weight, increased EMA cross")

    # 7. If profitable, increase confluence bonus
    if pf > 1.2:
        new_params["confluence_bonus"] = min(new_params["confluence_bonus"] + 2, 25)
        changes.append(f"Strategy profitable -> increased confluence bonus to {new_params['confluence_bonus']}")

    # 8. RSI zone too wide for the trend -> tighten
    if wr < 45:
        new_params["trend_rsi_call_low"] = min(new_params["trend_rsi_call_low"] + 2, 50)
        new_params["trend_rsi_put_high"] = max(new_params["trend_rsi_put_high"] - 2, 50)
        changes.append("Tightened RSI zones for stronger confirmation")

    if not changes:
        changes.append("No changes needed — parameters are optimal for this data")

    return new_params, changes


def run_optimization(symbols, num_iterations=5, capital=100000):
    """
    Run walk-forward optimization:
    - Train on recent 6 months
    - Validate on previous 6 months
    - Iterate and improve
    """
    params = copy.deepcopy(DEFAULT_PARAMS)

    print("=" * 100)
    print("WALK-FORWARD STRATEGY OPTIMIZATION")
    print("=" * 100)

    for iteration in range(1, num_iterations + 1):
        print(f"\n{'='*100}")
        print(f"ITERATION {iteration}")
        print(f"{'='*100}")

        # Fetch data for all symbols
        print(f"\nParameters: min_score={params['min_score']}, sl={params['sl_pct']:.3f}, "
              f"target={params['target_pct']:.3f}, trail_act={params['trail_activation']:.3f}, "
              f"max_hold={params['max_hold_bars']}, target_rr={params['target_rr']:.2f}")

        # --- TRAINING: Last 6 months ---
        print(f"\n--- Training (last 6 months) ---")
        train_total_t = 0; train_total_w = 0; train_total_p = 0
        all_train_trades = []

        print(f"{'Symbol':<12} {'Trades':>6} {'WR':>6} {'P&L':>9} {'PF':>6}")
        print("-" * 45)

        for sym, name in symbols:
            df = fetch_stock_data(sym, period="6mo", interval="1d")
            if df.empty or len(df) < 50:
                continue
            df = add_all_indicators(df)
            r = run_backtest_with_params(sym, df, params, capital)

            train_total_t += r["trades"]
            train_total_w += r["wins"]
            train_total_p += r["total_pnl"]
            all_train_trades.extend(r["trade_details"])
            print(f"{name:<12} {r['trades']:>6} {r['win_rate']:>5.1f}% {r['total_pnl']:>8.0f} {r['profit_factor']:>6.2f}")

        train_wr = (train_total_w / train_total_t * 100) if train_total_t else 0
        print(f"{'TRAIN TOTAL':<12} {train_total_t:>6} {train_wr:>5.1f}% {train_total_p:>8.0f}")

        # --- VALIDATION: Previous 6 months ---
        print(f"\n--- Validation (previous 6 months) ---")
        val_total_t = 0; val_total_w = 0; val_total_p = 0

        print(f"{'Symbol':<12} {'Trades':>6} {'WR':>6} {'P&L':>9} {'PF':>6}")
        print("-" * 45)

        for sym, name in symbols:
            df = fetch_stock_data(sym, period="1y", interval="1d")
            if df.empty or len(df) < 100:
                continue
            df = add_all_indicators(df)
            # Use first half (previous 6 months)
            half = len(df) // 2
            df_val = df.iloc[:half]
            if len(df_val) < 50:
                continue

            r = run_backtest_with_params(sym, df_val, params, capital)
            val_total_t += r["trades"]
            val_total_w += r["wins"]
            val_total_p += r["total_pnl"]
            print(f"{name:<12} {r['trades']:>6} {r['win_rate']:>5.1f}% {r['total_pnl']:>8.0f} {r['profit_factor']:>6.2f}")

        val_wr = (val_total_w / val_total_t * 100) if val_total_t else 0
        print(f"{'VAL TOTAL':<12} {val_total_t:>6} {val_wr:>5.1f}% {val_total_p:>8.0f}")

        # --- ANALYZE & IMPROVE ---
        train_results = {
            "trades": train_total_t,
            "wins": train_total_w,
            "win_rate": train_wr,
            "total_pnl": train_total_p,
            "profit_factor": round(sum(t.pnl for t in all_train_trades if t.pnl > 0) / abs(sum(t.pnl for t in all_train_trades if t.pnl <= 0)), 2) if any(t.pnl <= 0 for t in all_train_trades) else 999,
            "trade_details": all_train_trades,
        }

        new_params, changes = analyze_failures(train_results, params)

        print(f"\n--- Changes for next iteration ---")
        for c in changes:
            print(f"  * {c}")

        params = new_params

    # Final summary
    print(f"\n{'='*100}")
    print("FINAL OPTIMIZED PARAMETERS")
    print(f"{'='*100}")
    for k, v in params.items():
        if v != DEFAULT_PARAMS.get(k):
            print(f"  {k}: {DEFAULT_PARAMS[k]} -> {v}")

    return params


if __name__ == "__main__":
    symbols = [
        ('^NSEI', 'Nifty'),
        ('^NSEBANK', 'BankNifty'),
        ('RELIANCE.NS', 'Reliance'),
        ('SBIN.NS', 'SBI'),
        ('HDFCBANK.NS', 'HDFC'),
        ('INFY.NS', 'Infosys'),
        ('TCS.NS', 'TCS'),
        ('ITC.NS', 'ITC'),
    ]

    final_params = run_optimization(symbols, num_iterations=5)

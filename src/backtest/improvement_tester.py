"""
Individual Improvement Tester
Tests each proposed improvement in isolation against v3 baseline.
Then stacks the winners.
"""

import sys
import os
import copy
import pandas as pd
from collections import Counter
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.data.fetcher import fetch_stock_data
from src.indicators.technical import add_all_indicators, get_latest_indicators
from src.signals.generator import generate_all_signals
from config.settings import TOTAL_CAPITAL, MAX_RISK_PER_TRADE, SIGNAL_WEAK


SYMBOLS = [
    ('^NSEI', 'Nifty'), ('^NSEBANK', 'BankNifty'), ('RELIANCE.NS', 'Reliance'),
    ('TCS.NS', 'TCS'), ('HDFCBANK.NS', 'HDFC'), ('INFY.NS', 'Infosys'),
    ('SBIN.NS', 'SBI'), ('ITC.NS', 'ITC'),
]

CAPITAL = 100000
COMMISSION = 40


def load_data():
    """Load and cache all stock data."""
    data = {}
    for sym, name in SYMBOLS:
        df = fetch_stock_data(sym, period='1y', interval='1d')
        if not df.empty and len(df) >= 50:
            df = add_all_indicators(df)
            data[sym] = (name, df)
    return data


def run_backtest(data, config):
    """
    Run backtest with configurable exit parameters.

    config dict:
        sl_pct: float          - SL as % of price
        target_pct: float      - Target as % of price
        target_rr: float       - R:R for target hit P&L
        use_atr_sl: bool       - Use ATR-based SL
        atr_multiplier: float  - ATR multiplier for SL
        time_exit_bars: int    - Force exit after N bars (0=disabled)
        partial_exit: bool     - Take 50% at half-target
        use_ema200: bool       - Only trade in direction of EMA 200
        use_prev_day_hl: bool  - Use previous day H/L for SL
        min_score: int         - Min signal score
    """
    sl_pct = config.get('sl_pct', 0.03)
    target_pct = config.get('target_pct', 0.023)
    target_rr = config.get('target_rr', 1.2)
    use_atr_sl = config.get('use_atr_sl', False)
    atr_mult = config.get('atr_multiplier', 2.0)
    time_exit = config.get('time_exit_bars', 0)
    partial_exit = config.get('partial_exit', False)
    use_ema200 = config.get('use_ema200', False)
    use_prev_hl = config.get('use_prev_day_hl', False)
    min_score = config.get('min_score', SIGNAL_WEAK)

    total_trades = 0
    total_wins = 0
    total_pnl = 0.0

    for sym, (name, df) in data.items():
        eq = CAPITAL
        open_trade = None
        risk = CAPITAL * MAX_RISK_PER_TRADE

        for i in range(50, len(df)):
            price = float(df.iloc[i]['Close'])
            high = float(df.iloc[i]['High'])
            low = float(df.iloc[i]['Low'])
            atr = float(df.iloc[i].get('ATR', price * 0.02)) if 'ATR' in df.columns else price * 0.02

            # --- Check exit ---
            if open_trade:
                open_trade['bars'] += 1
                direction = open_trade['direction']

                # Determine SL level
                if use_atr_sl:
                    effective_sl_dist = atr * atr_mult / open_trade['entry']
                else:
                    effective_sl_dist = sl_pct

                # Previous day H/L based SL
                if use_prev_hl and i > 0:
                    prev_low = float(df.iloc[i-1]['Low'])
                    prev_high = float(df.iloc[i-1]['High'])
                    if "CALL" in direction:
                        prev_sl_dist = (open_trade['entry'] - prev_low) / open_trade['entry']
                        effective_sl_dist = max(effective_sl_dist, prev_sl_dist)
                    else:
                        prev_sl_dist = (prev_high - open_trade['entry']) / open_trade['entry']
                        effective_sl_dist = max(effective_sl_dist, prev_sl_dist)

                exit_price = 0
                exit_reason = ""
                pnl = 0

                if "CALL" in direction:
                    sl_level = open_trade['entry'] * (1 - effective_sl_dist)
                    tgt_level = open_trade['entry'] * (1 + target_pct)

                    if low <= sl_level:
                        exit_reason = "stop_loss"
                        pnl = -risk
                    elif high >= tgt_level:
                        exit_reason = "target"
                        if partial_exit:
                            pnl = risk * target_rr * 0.5  # Take half
                            # Let other half run... simplified: add half of remaining move
                            remaining_move = (price - tgt_level) / open_trade['entry']
                            pnl += risk * 0.5 * (remaining_move / sl_pct) if remaining_move > 0 else 0
                        else:
                            pnl = risk * target_rr
                else:
                    sl_level = open_trade['entry'] * (1 + effective_sl_dist)
                    tgt_level = open_trade['entry'] * (1 - target_pct)

                    if high >= sl_level:
                        exit_reason = "stop_loss"
                        pnl = -risk
                    elif low <= tgt_level:
                        exit_reason = "target"
                        if partial_exit:
                            pnl = risk * target_rr * 0.5
                            remaining_move = (tgt_level - price) / open_trade['entry']
                            pnl += risk * 0.5 * (remaining_move / sl_pct) if remaining_move > 0 else 0
                        else:
                            pnl = risk * target_rr

                # Time-based exit
                if not exit_reason and time_exit > 0 and open_trade['bars'] >= time_exit:
                    exit_reason = "time_exit"
                    if "CALL" in direction:
                        move = (price - open_trade['entry']) / open_trade['entry']
                    else:
                        move = (open_trade['entry'] - price) / open_trade['entry']
                    pnl = risk * (move / sl_pct)

                if exit_reason:
                    pnl -= COMMISSION
                    eq += pnl
                    total_trades += 1
                    if pnl > 0:
                        total_wins += 1
                    total_pnl += pnl
                    open_trade = None
                    continue

            # --- Generate signals ---
            if open_trade is None:
                indicators = get_latest_indicators(df.iloc[:i+1])

                # EMA 200 filter
                if use_ema200:
                    above_200 = indicators.get('above_ema_200')
                    if above_200 is not None:
                        # Will filter signals after generation
                        pass

                signals = generate_all_signals(sym, indicators)
                signals = [s for s in signals if s.score >= min_score]

                # EMA 200 macro filter
                if use_ema200 and signals:
                    above_200 = indicators.get('above_ema_200')
                    if above_200 is True:
                        signals = [s for s in signals if "CALL" in s.direction]
                    elif above_200 is False:
                        signals = [s for s in signals if "PUT" in s.direction]

                if signals:
                    sig = signals[0]
                    open_trade = {
                        'entry': price,
                        'direction': sig.direction,
                        'bars': 0,
                        'score': sig.score,
                        'strategy': sig.strategy,
                    }

    wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
    return {
        'trades': total_trades,
        'wins': total_wins,
        'win_rate': round(wr, 1),
        'total_pnl': round(total_pnl, 0),
        'pf': round(total_pnl / abs(total_pnl - total_pnl) if total_pnl == 0 else 0, 2),
    }


def main():
    print("Loading data for all 8 stocks...")
    data = load_data()
    print(f"Loaded {len(data)} stocks\n")

    # ============================================================
    # BASELINE: v3 current settings
    # ============================================================
    baseline_config = {
        'sl_pct': 0.03,
        'target_pct': 0.023,
        'target_rr': 1.2,
        'use_atr_sl': False,
        'time_exit_bars': 0,
        'partial_exit': False,
        'use_ema200': False,
        'use_prev_day_hl': False,
        'min_score': 40,
    }

    print("=" * 80)
    print("INDIVIDUAL IMPROVEMENT TESTING")
    print("Each improvement tested in isolation vs v3 baseline")
    print("=" * 80)

    baseline = run_backtest(data, baseline_config)
    print(f"\nBASELINE (v3): {baseline['trades']} trades, {baseline['win_rate']}% WR, P&L = {baseline['total_pnl']:+,.0f}")
    print("-" * 80)

    # ============================================================
    # TEST EACH IMPROVEMENT
    # ============================================================
    improvements = [
        (
            "1. ATR-based SL (2x ATR)",
            {**baseline_config, 'use_atr_sl': True, 'atr_multiplier': 2.0}
        ),
        (
            "1b. ATR-based SL (1.5x ATR)",
            {**baseline_config, 'use_atr_sl': True, 'atr_multiplier': 1.5}
        ),
        (
            "2. Time exit at 8 bars",
            {**baseline_config, 'time_exit_bars': 8}
        ),
        (
            "2b. Time exit at 10 bars",
            {**baseline_config, 'time_exit_bars': 10}
        ),
        (
            "2c. Time exit at 6 bars",
            {**baseline_config, 'time_exit_bars': 6}
        ),
        (
            "3. EMA 200 macro filter",
            {**baseline_config, 'use_ema200': True}
        ),
        (
            "4. Partial exit (50% at target)",
            {**baseline_config, 'partial_exit': True}
        ),
        (
            "5. Previous day H/L for SL",
            {**baseline_config, 'use_prev_day_hl': True}
        ),
        (
            "6. Higher min_score (50)",
            {**baseline_config, 'min_score': 50}
        ),
        (
            "6b. Higher min_score (60)",
            {**baseline_config, 'min_score': 60}
        ),
        (
            "7. Tighter target (2.0%)",
            {**baseline_config, 'target_pct': 0.020}
        ),
        (
            "7b. Wider target (3.0%)",
            {**baseline_config, 'target_pct': 0.030, 'target_rr': 1.5}
        ),
        (
            "8. Tighter SL (2.5%)",
            {**baseline_config, 'sl_pct': 0.025}
        ),
        (
            "8b. Wider SL (3.5%)",
            {**baseline_config, 'sl_pct': 0.035}
        ),
    ]

    results = []
    for name, config in improvements:
        r = run_backtest(data, config)
        diff_pnl = r['total_pnl'] - baseline['total_pnl']
        diff_wr = r['win_rate'] - baseline['win_rate']

        status = "BETTER" if diff_pnl > 0 else "WORSE"
        results.append((name, r, diff_pnl, diff_wr, status))

        print(f"{name:<35} {r['trades']:>4} trades, {r['win_rate']:>5.1f}% WR, P&L={r['total_pnl']:>+9,.0f}  ({diff_pnl:>+8,.0f}) {status}")

    # ============================================================
    # RANK BY IMPACT
    # ============================================================
    print("\n" + "=" * 80)
    print("RANKED BY P&L IMPACT (best to worst)")
    print("=" * 80)

    results.sort(key=lambda x: x[2], reverse=True)
    for name, r, diff_pnl, diff_wr, status in results:
        marker = "***" if diff_pnl > 5000 else "  *" if diff_pnl > 0 else "   "
        print(f"  {marker} {name:<35} P&L={r['total_pnl']:>+9,.0f} ({diff_pnl:>+8,.0f}) WR={r['win_rate']}%")

    # ============================================================
    # STACK THE WINNERS
    # ============================================================
    print("\n" + "=" * 80)
    print("STACKING THE WINNERS")
    print("=" * 80)

    # Take the top improvements that showed positive impact
    winners = [r for r in results if r[2] > 0]
    print(f"\n{len(winners)} improvements showed positive impact\n")

    # Stack incrementally: add one at a time, keep if it helps
    stacked_config = copy.deepcopy(baseline_config)
    stacked_result = baseline
    print(f"Start: {stacked_result['trades']} trades, {stacked_result['win_rate']}% WR, P&L = {stacked_result['total_pnl']:+,.0f}")

    # Test: ATR SL (whichever variant was best)
    atr_results = [(n,r,d) for n,r,d,_,_ in results if 'ATR' in n and d > 0]
    if atr_results:
        best_atr = max(atr_results, key=lambda x: x[2])
        mult = 1.5 if '1.5' in best_atr[0] else 2.0
        stacked_config['use_atr_sl'] = True
        stacked_config['atr_multiplier'] = mult
        r = run_backtest(data, stacked_config)
        if r['total_pnl'] > stacked_result['total_pnl']:
            stacked_result = r
            print(f"  + ATR SL ({mult}x): {r['trades']} trades, {r['win_rate']}% WR, P&L = {r['total_pnl']:+,.0f}")
        else:
            stacked_config['use_atr_sl'] = False
            print(f"  - ATR SL: doesn't help when stacked, skipping")

    # Test: Time exit
    time_results = [(n,r,d) for n,r,d,_,_ in results if 'Time exit' in n and d > 0]
    if time_results:
        best_time = max(time_results, key=lambda x: x[2])
        bars = int(''.join(c for c in best_time[0] if c.isdigit()))
        stacked_config['time_exit_bars'] = bars
        r = run_backtest(data, stacked_config)
        if r['total_pnl'] > stacked_result['total_pnl']:
            stacked_result = r
            print(f"  + Time exit ({bars} bars): {r['trades']} trades, {r['win_rate']}% WR, P&L = {r['total_pnl']:+,.0f}")
        else:
            stacked_config['time_exit_bars'] = 0
            print(f"  - Time exit: doesn't help when stacked, skipping")

    # Test: EMA 200
    ema200_results = [(n,r,d) for n,r,d,_,_ in results if 'EMA 200' in n and d > 0]
    if ema200_results:
        stacked_config['use_ema200'] = True
        r = run_backtest(data, stacked_config)
        if r['total_pnl'] > stacked_result['total_pnl']:
            stacked_result = r
            print(f"  + EMA 200 filter: {r['trades']} trades, {r['win_rate']}% WR, P&L = {r['total_pnl']:+,.0f}")
        else:
            stacked_config['use_ema200'] = False
            print(f"  - EMA 200: doesn't help when stacked, skipping")

    # Test: Partial exit
    partial_results = [(n,r,d) for n,r,d,_,_ in results if 'Partial' in n and d > 0]
    if partial_results:
        stacked_config['partial_exit'] = True
        r = run_backtest(data, stacked_config)
        if r['total_pnl'] > stacked_result['total_pnl']:
            stacked_result = r
            print(f"  + Partial exit: {r['trades']} trades, {r['win_rate']}% WR, P&L = {r['total_pnl']:+,.0f}")
        else:
            stacked_config['partial_exit'] = False
            print(f"  - Partial exit: doesn't help when stacked, skipping")

    # Test: Prev day H/L
    prev_results = [(n,r,d) for n,r,d,_,_ in results if 'Previous' in n and d > 0]
    if prev_results:
        stacked_config['use_prev_day_hl'] = True
        r = run_backtest(data, stacked_config)
        if r['total_pnl'] > stacked_result['total_pnl']:
            stacked_result = r
            print(f"  + Prev day H/L SL: {r['trades']} trades, {r['win_rate']}% WR, P&L = {r['total_pnl']:+,.0f}")
        else:
            stacked_config['use_prev_day_hl'] = False
            print(f"  - Prev day H/L: doesn't help when stacked, skipping")

    # Test: Min score
    score_results = [(n,r,d) for n,r,d,_,_ in results if 'min_score' in n and d > 0]
    if score_results:
        best_score = max(score_results, key=lambda x: x[2])
        score = int(''.join(c for c in best_score[0].split('(')[1] if c.isdigit()))
        stacked_config['min_score'] = score
        r = run_backtest(data, stacked_config)
        if r['total_pnl'] > stacked_result['total_pnl']:
            stacked_result = r
            print(f"  + Min score {score}: {r['trades']} trades, {r['win_rate']}% WR, P&L = {r['total_pnl']:+,.0f}")
        else:
            stacked_config['min_score'] = 40
            print(f"  - Min score: doesn't help when stacked, skipping")

    # Test best target
    tgt_results = [(n,r,d) for n,r,d,_,_ in results if 'target' in n.lower() and 'Tighter' in n or 'Wider' in n and d > 0]
    for name, r, d, _, _ in [(n,r,d,w,s) for n,r,d,w,s in results if 'target' in n.lower() and d > 0]:
        if '2.0' in name:
            stacked_config['target_pct'] = 0.020
        elif '3.0' in name:
            stacked_config['target_pct'] = 0.030
            stacked_config['target_rr'] = 1.5
        r = run_backtest(data, stacked_config)
        if r['total_pnl'] > stacked_result['total_pnl']:
            stacked_result = r
            print(f"  + {name}: {r['trades']} trades, {r['win_rate']}% WR, P&L = {r['total_pnl']:+,.0f}")
            break
        else:
            stacked_config['target_pct'] = 0.023
            stacked_config['target_rr'] = 1.2

    # ============================================================
    # FINAL RESULT
    # ============================================================
    print("\n" + "=" * 80)
    print("FINAL STACKED RESULT")
    print("=" * 80)
    print(f"\n  Baseline (v3):  {baseline['trades']} trades, {baseline['win_rate']}% WR, P&L = {baseline['total_pnl']:+,.0f}")
    print(f"  Stacked (v4):   {stacked_result['trades']} trades, {stacked_result['win_rate']}% WR, P&L = {stacked_result['total_pnl']:+,.0f}")
    improvement = stacked_result['total_pnl'] - baseline['total_pnl']
    print(f"  Improvement:    {improvement:+,.0f} ({improvement/max(abs(baseline['total_pnl']),1)*100:+.1f}%)")

    print(f"\n  Final config:")
    for k, v in stacked_config.items():
        if v != baseline_config.get(k):
            print(f"    {k}: {baseline_config[k]} -> {v}")

    return stacked_config


if __name__ == "__main__":
    main()

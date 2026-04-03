"""
Signal Generator v2
Enhanced with: trend filter, volume confirmation, confluence requirement,
options-aware filtering, and VIX modifier.

Changes from v1:
- Trend filter: CALL only above EMA20, PUT only below EMA20
- Volume: Require 1.2x+ volume for full score, penalize low volume
- Confluence: Bonus when multiple strategies agree, penalty for lone signals
- RSI safety zones tightened
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import (
    RSI_OVERSOLD, RSI_OVERBOUGHT,
    SIGNAL_STRONG, SIGNAL_MODERATE, SIGNAL_WEAK,
    SYMBOL_NAMES
)


class Signal:
    """Represents a trading signal."""

    def __init__(self, symbol: str, direction: str, score: int,
                 strategy: str, reasons: list):
        self.symbol = symbol
        self.direction = direction    # "BUY_CALL" or "BUY_PUT"
        self.score = score            # 0-100
        self.strategy = strategy      # "trend", "breakout", "oi_analysis"
        self.reasons = reasons        # list of strings explaining why

    @property
    def strength(self) -> str:
        if self.score >= SIGNAL_STRONG:
            return "STRONG"
        elif self.score >= SIGNAL_MODERATE:
            return "MODERATE"
        elif self.score >= SIGNAL_WEAK:
            return "WEAK"
        return "NO_TRADE"

    def __repr__(self):
        return (f"Signal({self.symbol} | {self.direction} | "
                f"Score: {self.score} | {self.strength} | {self.strategy})")


# ============================================================
# IMPROVEMENT 1: TREND FILTER
# ============================================================

def _passes_trend_filter(direction: str, indicators: dict) -> tuple[bool, str]:
    """
    Only allow CALL when price is above EMA 21 (uptrend).
    Only allow PUT when price is below EMA 21 (downtrend).
    This is the single biggest improvement — eliminates counter-trend trades.
    """
    above_ema_21 = indicators.get('above_ema_21')

    if "CALL" in direction and not above_ema_21:
        return False, "Blocked: CALL signal but price below EMA 21 (downtrend)"
    if "PUT" in direction and above_ema_21:
        return False, "Blocked: PUT signal but price above EMA 21 (uptrend)"

    return True, ""


# ============================================================
# IMPROVEMENT 2: VOLUME CONFIRMATION
# ============================================================

def _apply_volume_filter(signal: Signal, indicators: dict) -> Signal:
    """
    Require volume confirmation. Signals without volume support are unreliable.
    - Volume > 1.5x avg: +10 bonus (strong confirmation)
    - Volume > 1.0x avg: no change (normal)
    - Volume < 1.0x avg: -15 penalty (no conviction)
    """
    if signal is None:
        return signal

    high_volume = indicators.get('high_volume')
    volume = indicators.get('volume', 0)
    vol_ma = indicators.get('vol_ma_20', 0)

    if high_volume:
        # Check if volume is significantly above average
        if vol_ma and vol_ma > 0 and volume > vol_ma * 1.5:
            signal.score = min(signal.score + 10, 100)
            signal.reasons.append("Strong volume confirmation (>1.5x average)")
        else:
            signal.reasons.append("Volume above average")
    else:
        signal.score = max(signal.score - 15, 0)
        signal.reasons.append("Low volume — weak conviction, score reduced")

    return signal


# ============================================================
# STRATEGY 1: TREND FOLLOWING (IMPROVED)
# ============================================================

def generate_trend_signal(symbol: str, indicators: dict) -> Signal | None:
    """
    Trend Following — trades in the direction of the established trend.
    Improved: higher bar for entry, requires more confirmations.
    """
    score_call = 0
    score_put = 0
    reasons_call = []
    reasons_put = []

    rsi = indicators.get('rsi')

    # --- CALL conditions ---
    if indicators.get('above_ema_21'):
        score_call += 15
        reasons_call.append("Price above EMA 21")

    if indicators.get('above_ema_50'):
        score_call += 15
        reasons_call.append("Price above EMA 50")

    if indicators.get('supertrend_bullish'):
        score_call += 20
        reasons_call.append("SuperTrend bullish")

    if rsi and 45 <= rsi <= 65:
        score_call += 15
        reasons_call.append(f"RSI {rsi:.1f} — healthy trending zone")
    elif rsi and 40 <= rsi < 45:
        score_call += 5
        reasons_call.append(f"RSI {rsi:.1f} — borderline, watch closely")

    if indicators.get('ema_bullish_cross'):
        score_call += 20
        reasons_call.append("EMA 9/21 bullish crossover (fresh signal)")

    if indicators.get('macd_hist_rising'):
        score_call += 10
        reasons_call.append("MACD momentum increasing")

    # --- PUT conditions ---
    if not indicators.get('above_ema_21'):
        score_put += 15
        reasons_put.append("Price below EMA 21")

    if not indicators.get('above_ema_50'):
        score_put += 15
        reasons_put.append("Price below EMA 50")

    if indicators.get('supertrend_bullish') is False:
        score_put += 20
        reasons_put.append("SuperTrend bearish")

    if rsi and 35 <= rsi <= 55:
        score_put += 15
        reasons_put.append(f"RSI {rsi:.1f} — healthy downtrend zone")
    elif rsi and 55 < rsi <= 60:
        score_put += 5
        reasons_put.append(f"RSI {rsi:.1f} — borderline, watch closely")

    if indicators.get('ema_bearish_cross'):
        score_put += 20
        reasons_put.append("EMA 9/21 bearish crossover (fresh signal)")

    if indicators.get('macd_hist_rising') is False:
        score_put += 10
        reasons_put.append("MACD momentum decreasing")

    # Return the stronger signal (only if above threshold)
    if score_call >= SIGNAL_WEAK and score_call > score_put:
        return Signal(symbol, "BUY_CALL", min(score_call, 100), "trend", reasons_call)
    elif score_put >= SIGNAL_WEAK and score_put > score_call:
        return Signal(symbol, "BUY_PUT", min(score_put, 100), "trend", reasons_put)

    return None


# ============================================================
# STRATEGY 2: BREAKOUT (IMPROVED)
# ============================================================

def generate_breakout_signal(symbol: str, indicators: dict) -> Signal | None:
    """
    Breakout Trading — price breaking out of consolidation.
    Improved: requires volume confirmation for breakouts.
    """
    score_call = 0
    score_put = 0
    reasons_call = []
    reasons_put = []

    rsi = indicators.get('rsi')
    has_volume = indicators.get('high_volume')

    # Bollinger squeeze is key for breakouts
    if indicators.get('bb_squeezing'):
        score_call += 10
        score_put += 10
        reasons_call.append("Bollinger squeeze (expansion coming)")
        reasons_put.append("Bollinger squeeze (expansion coming)")

    # Bullish breakout — MUST have volume
    if indicators.get('at_upper_bb'):
        if has_volume:
            score_call += 25
            reasons_call.append("Breaking above upper BB with volume")
        else:
            score_call += 10
            reasons_call.append("At upper BB but low volume (weak breakout)")

    if rsi and rsi > 60:
        score_call += 10
        reasons_call.append(f"RSI {rsi:.1f} — strong momentum")

    if indicators.get('macd_histogram') and indicators['macd_histogram'] > 0:
        score_call += 10
        reasons_call.append("MACD positive")

    if has_volume:
        score_call += 15
        reasons_call.append("Volume confirms move")

    # Bearish breakdown — MUST have volume
    if indicators.get('at_lower_bb'):
        if has_volume:
            score_put += 25
            reasons_put.append("Breaking below lower BB with volume")
        else:
            score_put += 10
            reasons_put.append("At lower BB but low volume (weak breakdown)")

    if rsi and rsi < 40:
        score_put += 10
        reasons_put.append(f"RSI {rsi:.1f} — weak momentum")

    if indicators.get('macd_histogram') and indicators['macd_histogram'] < 0:
        score_put += 10
        reasons_put.append("MACD negative")

    if has_volume:
        score_put += 15
        reasons_put.append("Volume confirms move")

    if score_call >= SIGNAL_WEAK and score_call > score_put:
        return Signal(symbol, "BUY_CALL", min(score_call, 100), "breakout", reasons_call)
    elif score_put >= SIGNAL_WEAK and score_put > score_call:
        return Signal(symbol, "BUY_PUT", min(score_put, 100), "breakout", reasons_put)

    return None


# ============================================================
# STRATEGY 3: OI-BASED (unchanged from before)
# ============================================================

def generate_oi_signal(symbol: str, indicators: dict,
                       options_data: dict = None) -> Signal | None:
    """OI-Based Signal using PCR, OI buildup, max pain, IV skew."""
    if not options_data:
        return None

    score_call = 0
    score_put = 0
    reasons_call = []
    reasons_put = []

    pcr = options_data.get("pcr", {})
    oi_pcr = pcr.get("oi_pcr", 0)

    if oi_pcr > 1.2:
        score_call += 25
        reasons_call.append(f"PCR {oi_pcr} — heavy put writing, bullish")
    elif oi_pcr > 1.0:
        score_call += 15
        reasons_call.append(f"PCR {oi_pcr} — moderate bullish")

    if oi_pcr < 0.7:
        score_put += 25
        reasons_put.append(f"PCR {oi_pcr} — heavy call writing, bearish")
    elif oi_pcr < 1.0:
        score_put += 15
        reasons_put.append(f"PCR {oi_pcr} — moderate bearish")

    oi_buildup = options_data.get("oi_buildup", {})
    put_oi_chg = oi_buildup.get("total_put_oi_change", 0)
    call_oi_chg = oi_buildup.get("total_call_oi_change", 0)

    if put_oi_chg > 0 and put_oi_chg > abs(call_oi_chg):
        score_call += 20
        reasons_call.append("Fresh put writing — support building")
    if call_oi_chg > 0 and call_oi_chg > abs(put_oi_chg):
        score_put += 20
        reasons_put.append("Fresh call writing — resistance building")
    if call_oi_chg < 0:
        score_call += 10
        reasons_call.append("Call unwinding — resistance weakening")
    if put_oi_chg < 0:
        score_put += 10
        reasons_put.append("Put unwinding — support weakening")

    max_pain = options_data.get("max_pain", {})
    mp_strike = max_pain.get("strike")
    close = indicators.get("close", 0)

    if mp_strike and close:
        if close < mp_strike * 0.99:
            score_call += 15
            reasons_call.append(f"Below max pain {mp_strike} — pull upward")
        elif close > mp_strike * 1.01:
            score_put += 15
            reasons_put.append(f"Above max pain {mp_strike} — pull downward")

    oi_levels = options_data.get("oi_levels", {})
    support = oi_levels.get("support")
    resistance = oi_levels.get("resistance")

    if support and close and close > support:
        if ((close - support) / close) * 100 < 2:
            score_call += 15
            reasons_call.append(f"Near OI support at {support}")
    if resistance and close and close < resistance:
        if ((resistance - close) / close) * 100 < 2:
            score_put += 15
            reasons_put.append(f"Near OI resistance at {resistance}")

    iv_skew = options_data.get("iv_skew", {})
    skew_type = iv_skew.get("skew_type", "")
    if "Reverse" in skew_type:
        score_call += 10
        reasons_call.append("Reverse IV skew — institutional upside demand")
    elif "Normal" in skew_type:
        score_put += 5
        reasons_put.append("Normal IV skew — downside protection demand")

    if score_call >= SIGNAL_WEAK and score_call > score_put:
        return Signal(symbol, "BUY_CALL", min(score_call, 100), "oi_analysis", reasons_call)
    elif score_put >= SIGNAL_WEAK and score_put > score_call:
        return Signal(symbol, "BUY_PUT", min(score_put, 100), "oi_analysis", reasons_put)

    return None


# ============================================================
# FILTERS
# ============================================================

def _apply_rsi_filter(signal: Signal, rsi: float | None) -> Signal:
    """Penalize signals in RSI extreme zones."""
    if signal is None or rsi is None:
        return signal

    penalty = 0
    warning = None

    if "PUT" in signal.direction and rsi < 30:
        penalty = 25
        warning = f"RSI {rsi:.1f} oversold — high bounce risk"
    elif "PUT" in signal.direction and rsi < 35:
        penalty = 15
        warning = f"RSI {rsi:.1f} near oversold — bounce likely"
    elif "CALL" in signal.direction and rsi > 70:
        penalty = 25
        warning = f"RSI {rsi:.1f} overbought — reversal risk"
    elif "CALL" in signal.direction and rsi > 65:
        penalty = 15
        warning = f"RSI {rsi:.1f} near overbought — caution"

    if penalty > 0:
        signal.score = max(signal.score - penalty, 0)
        signal.reasons.append(f"⚠️ {warning}, score -{penalty}")

    return signal


def _apply_vix_modifier(signal: Signal, vix: float = None) -> Signal:
    """VIX-based adjustment. Warn but don't aggressively hide signals."""
    if signal is None or vix is None:
        return signal

    if vix > 30:
        signal.score = max(signal.score - 10, 0)
        signal.reasons.append(f"⚠️ VIX {vix:.1f} very high — prefer selling strategies")
    elif vix > 25:
        signal.score = max(signal.score - 5, 0)
        signal.reasons.append(f"⚠️ VIX {vix:.1f} high — use smaller positions")
    elif vix > 20:
        signal.reasons.append(f"VIX {vix:.1f} elevated — wider stop losses")
    elif vix < 13:
        signal.score = min(signal.score + 5, 100)
        signal.reasons.append(f"VIX {vix:.1f} low — options cheap, good for buying")

    return signal


# ============================================================
# IMPROVEMENT 5: CONFLUENCE SCORING
# ============================================================

def _apply_confluence_bonus(signals: list[Signal]) -> list[Signal]:
    """
    Reward when multiple strategies agree on the same direction.
    Penalize lone signals that have no confirmation.

    - 2+ strategies agree: +15 bonus to each
    - Only 1 strategy: -10 penalty (no confirmation)
    """
    if not signals:
        return signals

    # Group by direction
    call_signals = [s for s in signals if "CALL" in s.direction]
    put_signals = [s for s in signals if "PUT" in s.direction]

    # Check confluence for calls
    if len(call_signals) >= 2:
        strategies = set(s.strategy for s in call_signals)
        if len(strategies) >= 2:
            for s in call_signals:
                s.score = min(s.score + 15, 100)
                s.reasons.append(f"Confluence bonus: {len(strategies)} strategies agree on CALL")
    elif len(call_signals) == 1 and not put_signals:
        call_signals[0].score = max(call_signals[0].score - 10, 0)
        call_signals[0].reasons.append("No confluence — single strategy signal, score -10")

    # Check confluence for puts
    if len(put_signals) >= 2:
        strategies = set(s.strategy for s in put_signals)
        if len(strategies) >= 2:
            for s in put_signals:
                s.score = min(s.score + 15, 100)
                s.reasons.append(f"Confluence bonus: {len(strategies)} strategies agree on PUT")
    elif len(put_signals) == 1 and not call_signals:
        put_signals[0].score = max(put_signals[0].score - 10, 0)
        put_signals[0].reasons.append("No confluence — single strategy signal, score -10")

    return signals


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def generate_all_signals(symbol: str, indicators: dict,
                         options_data: dict = None,
                         vix: float = None) -> list[Signal]:
    """
    Run all strategies with full filtering pipeline:
    1. Generate raw signals from each strategy
    2. Apply trend filter (block counter-trend)
    3. Apply volume filter (penalize low volume)
    4. Apply RSI safety filter
    5. Apply VIX modifier
    6. Apply confluence bonus/penalty
    7. Filter out below-threshold signals
    """
    raw_signals = []
    rsi = indicators.get('rsi')

    # Generate from each strategy
    trend = generate_trend_signal(symbol, indicators)
    if trend:
        raw_signals.append(trend)

    breakout = generate_breakout_signal(symbol, indicators)
    if breakout:
        raw_signals.append(breakout)

    if options_data:
        oi_signal = generate_oi_signal(symbol, indicators, options_data)
        if oi_signal:
            raw_signals.append(oi_signal)

    # FILTER 1: Trend filter — block counter-trend signals
    filtered = []
    for sig in raw_signals:
        passes, reason = _passes_trend_filter(sig.direction, indicators)
        if passes:
            filtered.append(sig)
        # Counter-trend signals are silently dropped
    signals = filtered

    # FILTER 2: Volume confirmation
    signals = [_apply_volume_filter(s, indicators) for s in signals]

    # FILTER 3: RSI safety
    signals = [_apply_rsi_filter(s, rsi) for s in signals]

    # FILTER 4: VIX modifier
    if vix:
        signals = [_apply_vix_modifier(s, vix) for s in signals]

    # FILTER 5: Confluence bonus/penalty
    signals = _apply_confluence_bonus(signals)

    # Final: remove below-threshold signals
    signals = [s for s in signals if s.score >= SIGNAL_WEAK]

    # Sort by score (highest first)
    signals.sort(key=lambda s: s.score, reverse=True)
    return signals


def format_signal_report(signals: list[Signal]) -> str:
    """Create a readable report of all signals."""
    if not signals:
        return "No trading signals at this time.\n"

    lines = ["=" * 60, "TRADING SIGNALS REPORT", "=" * 60, ""]

    for sig in signals:
        emoji = "+" if "CALL" in sig.direction else "-"
        name = SYMBOL_NAMES.get(sig.symbol, sig.symbol)
        lines.append(f"[{emoji}] {name} -> {sig.direction}")
        lines.append(f"   Score: {sig.score}/100 {sig.strength}")
        lines.append(f"   Strategy: {sig.strategy.upper()}")
        lines.append(f"   Reasons:")
        for reason in sig.reasons:
            lines.append(f"     * {reason}")
        lines.append("")

    return "\n".join(lines)

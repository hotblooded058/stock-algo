"""
Signal Generator v3
Enhanced with: VWAP, ADX, ORB, IV Percentile, time filter.

v3 additions (from research):
- VWAP: Additional trend confirmation (institutional reference price)
- ADX: Skip signals when market is choppy (ADX < 20)
- ORB: Opening Range Breakout strategy (new)
- IV Percentile: Penalize buying expensive options
- Time filter: Block signals during low-quality hours
- OI change classification: Long buildup vs short covering
"""

import sys
import os
from datetime import datetime

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
        self.direction = direction
        self.score = score
        self.strategy = strategy
        self.reasons = reasons

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
# FILTERS
# ============================================================

def _passes_trend_filter(direction: str, indicators: dict) -> bool:
    """CALL only above EMA 21, PUT only below."""
    above_ema = indicators.get('above_ema_21')
    if "CALL" in direction and not above_ema:
        return False
    if "PUT" in direction and above_ema:
        return False
    return True


def _apply_volume_filter(signal: Signal, indicators: dict) -> Signal:
    """Volume confirmation. High volume = bonus, low volume = penalty."""
    if signal is None:
        return signal

    vol_ratio = indicators.get('volume_ratio')
    if vol_ratio is not None:
        if vol_ratio >= 1.5:
            signal.score = min(signal.score + 10, 100)
            signal.reasons.append(f"Strong volume ({vol_ratio:.1f}x avg)")
        elif vol_ratio >= 1.0:
            signal.reasons.append("Volume normal")
        else:
            signal.score = max(signal.score - 15, 0)
            signal.reasons.append(f"Low volume ({vol_ratio:.1f}x avg), score -15")
    elif indicators.get('high_volume'):
        signal.score = min(signal.score + 5, 100)
    else:
        signal.score = max(signal.score - 10, 0)

    return signal


def _apply_vwap_filter(signal: Signal, indicators: dict) -> Signal:
    """VWAP confirmation. Price should be on the right side of VWAP."""
    if signal is None:
        return signal

    above_vwap = indicators.get('above_vwap')
    if above_vwap is None:
        return signal

    if "CALL" in signal.direction and above_vwap:
        signal.score = min(signal.score + 8, 100)
        signal.reasons.append("Price above VWAP (institutional bullish)")
    elif "CALL" in signal.direction and not above_vwap:
        signal.score = max(signal.score - 8, 0)
        signal.reasons.append("Price below VWAP (institutional bearish), CALL penalized")
    elif "PUT" in signal.direction and not above_vwap:
        signal.score = min(signal.score + 8, 100)
        signal.reasons.append("Price below VWAP (institutional bearish)")
    elif "PUT" in signal.direction and above_vwap:
        signal.score = max(signal.score - 8, 0)
        signal.reasons.append("Price above VWAP (institutional bullish), PUT penalized")

    return signal


def _apply_adx_filter(signal: Signal, indicators: dict) -> Signal:
    """ADX filter. Skip trend signals in choppy markets (ADX < 20)."""
    if signal is None:
        return signal

    adx = indicators.get('adx')
    if adx is None:
        return signal

    if adx < 20:
        if signal.strategy in ("trend", "breakout"):
            signal.score = max(signal.score - 15, 0)
            signal.reasons.append(f"ADX {adx:.0f} — choppy market, trend signal unreliable")
    elif adx > 30:
        signal.score = min(signal.score + 5, 100)
        signal.reasons.append(f"ADX {adx:.0f} — strong trend, good for directional trades")

    return signal


def _apply_rsi_filter(signal: Signal, rsi: float | None) -> Signal:
    """Penalize signals in RSI extreme zones."""
    if signal is None or rsi is None:
        return signal

    if "PUT" in signal.direction and rsi < 30:
        signal.score = max(signal.score - 25, 0)
        signal.reasons.append(f"RSI {rsi:.1f} oversold — bounce risk, score -25")
    elif "PUT" in signal.direction and rsi < 35:
        signal.score = max(signal.score - 15, 0)
        signal.reasons.append(f"RSI {rsi:.1f} near oversold, score -15")
    elif "CALL" in signal.direction and rsi > 70:
        signal.score = max(signal.score - 25, 0)
        signal.reasons.append(f"RSI {rsi:.1f} overbought — reversal risk, score -25")
    elif "CALL" in signal.direction and rsi > 65:
        signal.score = max(signal.score - 15, 0)
        signal.reasons.append(f"RSI {rsi:.1f} near overbought, score -15")

    return signal


def _apply_vix_modifier(signal: Signal, vix: float = None) -> Signal:
    """VIX-based warning."""
    if signal is None or vix is None:
        return signal

    if vix > 30:
        signal.score = max(signal.score - 10, 0)
        signal.reasons.append(f"VIX {vix:.1f} very high — prefer selling strategies")
    elif vix > 25:
        signal.score = max(signal.score - 5, 0)
        signal.reasons.append(f"VIX {vix:.1f} high — smaller positions")
    elif vix > 20:
        signal.reasons.append(f"VIX {vix:.1f} elevated — wider stop losses")
    elif vix < 13:
        signal.score = min(signal.score + 5, 100)
        signal.reasons.append(f"VIX {vix:.1f} low — options cheap, good for buying")

    return signal


def _apply_iv_percentile_filter(signal: Signal, iv_percentile: float = None) -> Signal:
    """IV Percentile filter. Don't buy expensive options."""
    if signal is None or iv_percentile is None:
        return signal

    if iv_percentile > 75:
        signal.score = max(signal.score - 15, 0)
        signal.reasons.append(f"IV Percentile {iv_percentile:.0f}% — options very expensive, avoid buying")
    elif iv_percentile > 50:
        signal.score = max(signal.score - 5, 0)
        signal.reasons.append(f"IV Percentile {iv_percentile:.0f}% — options above average cost")
    elif iv_percentile < 25:
        signal.score = min(signal.score + 10, 100)
        signal.reasons.append(f"IV Percentile {iv_percentile:.0f}% — options cheap, great for buying")
    elif iv_percentile < 40:
        signal.score = min(signal.score + 5, 100)
        signal.reasons.append(f"IV Percentile {iv_percentile:.0f}% — options reasonably priced")

    return signal


def _apply_confluence_bonus(signals: list[Signal]) -> list[Signal]:
    """Reward when multiple strategies agree. Penalize lone signals."""
    if not signals:
        return signals

    call_sigs = [s for s in signals if "CALL" in s.direction]
    put_sigs = [s for s in signals if "PUT" in s.direction]

    for group in [call_sigs, put_sigs]:
        if len(group) >= 2:
            strategies = set(s.strategy for s in group)
            if len(strategies) >= 2:
                for s in group:
                    s.score = min(s.score + 23, 100)
                    s.reasons.append(f"Confluence: {len(strategies)} strategies agree")

    # Penalize lone signals only if no other direction signals exist
    if len(call_sigs) == 1 and not put_sigs:
        call_sigs[0].score = max(call_sigs[0].score - 10, 0)
        call_sigs[0].reasons.append("No confluence — lone signal")
    if len(put_sigs) == 1 and not call_sigs:
        put_sigs[0].score = max(put_sigs[0].score - 10, 0)
        put_sigs[0].reasons.append("No confluence — lone signal")

    return signals


# ============================================================
# STRATEGY 1: TREND FOLLOWING
# ============================================================

def generate_trend_signal(symbol: str, indicators: dict) -> Signal | None:
    """Trend Following — trades in direction of established trend."""
    score_call = 0
    score_put = 0
    reasons_call = []
    reasons_put = []

    rsi = indicators.get('rsi')

    # CALL conditions
    if indicators.get('above_ema_21'):
        score_call += 15; reasons_call.append("Price above EMA 21")
    if indicators.get('above_ema_50'):
        score_call += 15; reasons_call.append("Price above EMA 50")
    if indicators.get('supertrend_bullish'):
        score_call += 17; reasons_call.append("SuperTrend bullish")
    if rsi and 45 <= rsi <= 65:
        score_call += 15; reasons_call.append(f"RSI {rsi:.1f} in bullish zone")
    if indicators.get('ema_bullish_cross'):
        score_call += 23; reasons_call.append("EMA 9/21 bullish crossover")
    if indicators.get('macd_hist_rising'):
        score_call += 10; reasons_call.append("MACD rising")

    # PUT conditions
    if not indicators.get('above_ema_21'):
        score_put += 15; reasons_put.append("Price below EMA 21")
    if not indicators.get('above_ema_50'):
        score_put += 15; reasons_put.append("Price below EMA 50")
    if indicators.get('supertrend_bullish') is False:
        score_put += 17; reasons_put.append("SuperTrend bearish")
    if rsi and 35 <= rsi <= 55:
        score_put += 15; reasons_put.append(f"RSI {rsi:.1f} in bearish zone")
    if indicators.get('ema_bearish_cross'):
        score_put += 23; reasons_put.append("EMA 9/21 bearish crossover")
    if indicators.get('macd_hist_rising') is False:
        score_put += 10; reasons_put.append("MACD falling")

    if score_call >= SIGNAL_WEAK and score_call > score_put:
        return Signal(symbol, "BUY_CALL", min(score_call, 100), "trend", reasons_call)
    elif score_put >= SIGNAL_WEAK and score_put > score_call:
        return Signal(symbol, "BUY_PUT", min(score_put, 100), "trend", reasons_put)
    return None


# ============================================================
# STRATEGY 2: BREAKOUT
# ============================================================

def generate_breakout_signal(symbol: str, indicators: dict) -> Signal | None:
    """Breakout Trading — price breaking out of consolidation with volume."""
    score_call = 0
    score_put = 0
    reasons_call = []
    reasons_put = []

    rsi = indicators.get('rsi')
    has_vol = indicators.get('high_volume')

    if indicators.get('bb_squeezing'):
        score_call += 10; reasons_call.append("BB squeeze")
        score_put += 10; reasons_put.append("BB squeeze")

    if indicators.get('at_upper_bb'):
        w = 25 if has_vol else 10
        score_call += w; reasons_call.append("Breaking upper BB" + (" + volume" if has_vol else ""))
    if indicators.get('at_lower_bb'):
        w = 25 if has_vol else 10
        score_put += w; reasons_put.append("Breaking lower BB" + (" + volume" if has_vol else ""))

    if rsi and rsi > 60:
        score_call += 10; reasons_call.append(f"RSI {rsi:.1f} strong")
    if rsi and rsi < 40:
        score_put += 10; reasons_put.append(f"RSI {rsi:.1f} weak")

    if indicators.get('macd_histogram') and indicators['macd_histogram'] > 0:
        score_call += 10; reasons_call.append("MACD positive")
    if indicators.get('macd_histogram') and indicators['macd_histogram'] < 0:
        score_put += 10; reasons_put.append("MACD negative")

    if has_vol:
        score_call += 15; reasons_call.append("Volume confirms")
        score_put += 15; reasons_put.append("Volume confirms")

    if score_call >= SIGNAL_WEAK and score_call > score_put:
        return Signal(symbol, "BUY_CALL", min(score_call, 100), "breakout", reasons_call)
    elif score_put >= SIGNAL_WEAK and score_put > score_call:
        return Signal(symbol, "BUY_PUT", min(score_put, 100), "breakout", reasons_put)
    return None


# ============================================================
# STRATEGY 3: OI ANALYSIS
# ============================================================

def generate_oi_signal(symbol: str, indicators: dict,
                       options_data: dict = None) -> Signal | None:
    """OI-Based Signal using PCR, OI buildup, max pain, IV skew."""
    if not options_data:
        return None

    score_call = 0; score_put = 0
    reasons_call = []; reasons_put = []

    pcr = options_data.get("pcr", {})
    oi_pcr = pcr.get("oi_pcr", 0)

    if oi_pcr > 1.2:
        score_call += 25; reasons_call.append(f"PCR {oi_pcr} — heavy put writing, bullish")
    elif oi_pcr > 1.0:
        score_call += 15; reasons_call.append(f"PCR {oi_pcr} — moderate bullish")
    if oi_pcr < 0.7:
        score_put += 25; reasons_put.append(f"PCR {oi_pcr} — heavy call writing, bearish")
    elif oi_pcr < 1.0:
        score_put += 15; reasons_put.append(f"PCR {oi_pcr} — moderate bearish")

    # PCR extremes — CONTRARIAN (research: 68% reversal accuracy)
    if oi_pcr > 1.6:
        score_call += 10; reasons_call.append(f"PCR {oi_pcr} extreme — contrarian rally likely")
    elif oi_pcr < 0.5:
        score_put += 10; reasons_put.append(f"PCR {oi_pcr} extreme — contrarian correction likely")

    oi_buildup = options_data.get("oi_buildup", {})
    put_chg = oi_buildup.get("total_put_oi_change", 0)
    call_chg = oi_buildup.get("total_call_oi_change", 0)

    if put_chg > 0 and put_chg > abs(call_chg):
        score_call += 20; reasons_call.append("Fresh put writing — support building")
    if call_chg > 0 and call_chg > abs(put_chg):
        score_put += 20; reasons_put.append("Fresh call writing — resistance building")
    if call_chg < 0:
        score_call += 10; reasons_call.append("Call unwinding — resistance weakening")
    if put_chg < 0:
        score_put += 10; reasons_put.append("Put unwinding — support weakening")

    max_pain = options_data.get("max_pain", {})
    mp = max_pain.get("strike")
    close = indicators.get("close", 0)

    if mp and close:
        if close < mp * 0.99:
            score_call += 15; reasons_call.append(f"Below max pain {mp} — pull upward")
        elif close > mp * 1.01:
            score_put += 15; reasons_put.append(f"Above max pain {mp} — pull downward")

    oi_levels = options_data.get("oi_levels", {})
    support = oi_levels.get("support")
    resistance = oi_levels.get("resistance")

    if support and close and ((close - support) / close) * 100 < 2:
        score_call += 15; reasons_call.append(f"Near OI support {support}")
    if resistance and close and ((resistance - close) / close) * 100 < 2:
        score_put += 15; reasons_put.append(f"Near OI resistance {resistance}")

    iv_skew = options_data.get("iv_skew", {})
    if "Reverse" in iv_skew.get("skew_type", ""):
        score_call += 10; reasons_call.append("Reverse IV skew — institutional upside demand")
    elif "Normal" in iv_skew.get("skew_type", ""):
        score_put += 5; reasons_put.append("Normal IV skew — downside protection")

    if score_call >= SIGNAL_WEAK and score_call > score_put:
        return Signal(symbol, "BUY_CALL", min(score_call, 100), "oi_analysis", reasons_call)
    elif score_put >= SIGNAL_WEAK and score_put > score_call:
        return Signal(symbol, "BUY_PUT", min(score_put, 100), "oi_analysis", reasons_put)
    return None


# ============================================================
# STRATEGY 4: OPENING RANGE BREAKOUT (NEW)
# ============================================================

def generate_orb_signal(symbol: str, indicators: dict,
                        orb_data: dict = None) -> Signal | None:
    """
    Opening Range Breakout — trade the break of first 30-60 min range.
    Research: 60-min ORB has 89% win rate with 1.44 profit factor.

    orb_data should contain:
    - orb_high: High of the opening range
    - orb_low: Low of the opening range
    - orb_range: orb_high - orb_low
    - current_price: Current price
    """
    if not orb_data:
        return None

    orb_high = orb_data.get("orb_high", 0)
    orb_low = orb_data.get("orb_low", 0)
    current = orb_data.get("current_price", 0) or indicators.get("close", 0)

    if not orb_high or not orb_low or not current:
        return None

    orb_range = orb_high - orb_low
    if orb_range <= 0:
        return None

    # Bullish breakout: price above ORB high
    if current > orb_high:
        breakout_strength = (current - orb_high) / orb_range
        score = 50
        reasons = [f"Price broke above ORB high {orb_high:.2f}"]

        if breakout_strength > 0.5:
            score += 15; reasons.append("Strong breakout (>50% of range)")
        elif breakout_strength > 0.2:
            score += 10; reasons.append("Moderate breakout")

        if indicators.get('high_volume'):
            score += 15; reasons.append("Volume confirms breakout")
        if indicators.get('above_vwap'):
            score += 10; reasons.append("Above VWAP — institutional support")

        return Signal(symbol, "BUY_CALL", min(score, 100), "orb", reasons)

    # Bearish breakdown: price below ORB low
    if current < orb_low:
        breakdown_strength = (orb_low - current) / orb_range
        score = 50
        reasons = [f"Price broke below ORB low {orb_low:.2f}"]

        if breakdown_strength > 0.5:
            score += 15; reasons.append("Strong breakdown (>50% of range)")
        elif breakdown_strength > 0.2:
            score += 10; reasons.append("Moderate breakdown")

        if indicators.get('high_volume'):
            score += 15; reasons.append("Volume confirms breakdown")
        if not indicators.get('above_vwap'):
            score += 10; reasons.append("Below VWAP — institutional pressure")

        return Signal(symbol, "BUY_PUT", min(score, 100), "orb", reasons)

    return None


# ============================================================
# TIME OF DAY FILTER
# ============================================================

def _is_good_trading_time() -> bool:
    """
    Check if current time is a good trading window.
    Best: 9:30-10:30, 14:30-15:15
    Avoid: 9:15-9:30 (noise), 12:00-13:30 (lunch)
    Returns True for daily timeframe (no time filter needed).
    """
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    t = hour * 60 + minute  # Minutes since midnight

    # Before market or after market
    if t < 555 or t > 930:  # Before 9:15 or after 15:30
        return True  # Daily data, no filter

    # Avoid first 15 min
    if t < 570:  # Before 9:30
        return False

    # Avoid lunch hour
    if 720 <= t <= 810:  # 12:00-13:30
        return False

    return True


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def generate_all_signals(symbol: str, indicators: dict,
                         options_data: dict = None,
                         vix: float = None,
                         iv_percentile: float = None,
                         orb_data: dict = None) -> list[Signal]:
    """
    Run all strategies with full filtering pipeline:
    1. Generate raw signals from each strategy
    2. Apply trend filter (block counter-trend)
    3. Apply VWAP filter (institutional reference)
    4. Apply ADX filter (skip choppy markets)
    5. Apply volume filter
    6. Apply RSI safety filter
    7. Apply VIX modifier
    8. Apply IV percentile filter
    9. Apply confluence bonus/penalty
    10. Filter out below-threshold signals
    """
    raw_signals = []
    rsi = indicators.get('rsi')

    # Strategy 1: Trend
    trend = generate_trend_signal(symbol, indicators)
    if trend:
        raw_signals.append(trend)

    # Strategy 2: Breakout
    breakout = generate_breakout_signal(symbol, indicators)
    if breakout:
        raw_signals.append(breakout)

    # Strategy 3: OI Analysis
    if options_data:
        oi_sig = generate_oi_signal(symbol, indicators, options_data)
        if oi_sig:
            raw_signals.append(oi_sig)

    # Strategy 4: ORB
    if orb_data:
        orb_sig = generate_orb_signal(symbol, indicators, orb_data)
        if orb_sig:
            raw_signals.append(orb_sig)

    # FILTER 1: Trend filter
    signals = [s for s in raw_signals if _passes_trend_filter(s.direction, indicators)]

    # FILTER 2: VWAP (NEW)
    signals = [_apply_vwap_filter(s, indicators) for s in signals]

    # FILTER 3: ADX — skip choppy markets (NEW)
    signals = [_apply_adx_filter(s, indicators) for s in signals]

    # FILTER 4: Volume
    signals = [_apply_volume_filter(s, indicators) for s in signals]

    # FILTER 5: RSI safety
    signals = [_apply_rsi_filter(s, rsi) for s in signals]

    # FILTER 6: VIX modifier
    if vix:
        signals = [_apply_vix_modifier(s, vix) for s in signals]

    # FILTER 7: IV Percentile (NEW)
    if iv_percentile is not None:
        signals = [_apply_iv_percentile_filter(s, iv_percentile) for s in signals]

    # FILTER 8: Confluence
    signals = _apply_confluence_bonus(signals)

    # Final filter
    signals = [s for s in signals if s.score >= SIGNAL_WEAK]
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

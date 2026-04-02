"""
Signal Generator
Analyzes indicators and generates BUY CALL / BUY PUT signals with confidence scores.
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
        self.strategy = strategy      # "trend", "breakout", "reversal"
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


def generate_trend_signal(symbol: str, indicators: dict) -> Signal | None:
    """
    Strategy 1: Trend Following
    Safest strategy for beginners — trades in the direction of the trend.
    """
    score_call = 0
    score_put = 0
    reasons_call = []
    reasons_put = []

    # --- CALL conditions ---
    if indicators.get('above_ema_21'):
        score_call += 20
        reasons_call.append("Price above EMA 21")

    if indicators.get('above_ema_50'):
        score_call += 15
        reasons_call.append("Price above EMA 50")

    if indicators.get('supertrend_bullish'):
        score_call += 25
        reasons_call.append("SuperTrend is bullish (green)")

    rsi = indicators.get('rsi')
    if rsi and 40 <= rsi <= 65:
        score_call += 15
        reasons_call.append(f"RSI at {rsi:.1f} — trending, not overbought")

    if indicators.get('high_volume'):
        score_call += 10
        reasons_call.append("Volume above 20-day average")

    if indicators.get('ema_bullish_cross'):
        score_call += 15
        reasons_call.append("EMA 9 crossed above EMA 21 (bullish)")

    if indicators.get('macd_hist_rising'):
        score_call += 10
        reasons_call.append("MACD momentum increasing")

    # --- PUT conditions ---
    if not indicators.get('above_ema_21'):
        score_put += 20
        reasons_put.append("Price below EMA 21")

    if not indicators.get('above_ema_50'):
        score_put += 15
        reasons_put.append("Price below EMA 50")

    if indicators.get('supertrend_bullish') is False:
        score_put += 25
        reasons_put.append("SuperTrend is bearish (red)")

    if rsi and 35 <= rsi <= 60:
        score_put += 15
        reasons_put.append(f"RSI at {rsi:.1f} — trending down, not oversold")

    if indicators.get('high_volume'):
        score_put += 10
        reasons_put.append("Volume above 20-day average")

    if indicators.get('ema_bearish_cross'):
        score_put += 15
        reasons_put.append("EMA 9 crossed below EMA 21 (bearish)")

    if indicators.get('macd_hist_rising') is False:
        score_put += 10
        reasons_put.append("MACD momentum decreasing")

    # Return the stronger signal
    if score_call >= SIGNAL_WEAK and score_call > score_put:
        return Signal(symbol, "BUY_CALL", min(score_call, 100), "trend", reasons_call)
    elif score_put >= SIGNAL_WEAK and score_put > score_call:
        return Signal(symbol, "BUY_PUT", min(score_put, 100), "trend", reasons_put)

    return None


def generate_breakout_signal(symbol: str, indicators: dict) -> Signal | None:
    """
    Strategy 2: Breakout Trading
    Looks for price breaking out of consolidation with volume.
    """
    score_call = 0
    score_put = 0
    reasons_call = []
    reasons_put = []

    rsi = indicators.get('rsi')

    # Bollinger squeeze is key for breakouts
    if indicators.get('bb_squeezing'):
        score_call += 15
        score_put += 15
        reasons_call.append("Bollinger Bands squeezing (volatility expansion coming)")
        reasons_put.append("Bollinger Bands squeezing (volatility expansion coming)")

    # Bullish breakout
    if indicators.get('at_upper_bb'):
        score_call += 20
        reasons_call.append("Price breaking above upper Bollinger Band")

    if rsi and rsi > 60:
        score_call += 15
        reasons_call.append(f"RSI at {rsi:.1f} — strong momentum")

    if indicators.get('macd_histogram') and indicators['macd_histogram'] > 0:
        score_call += 15
        reasons_call.append("MACD histogram positive")

    if indicators.get('high_volume'):
        score_call += 20
        reasons_call.append("High volume confirms breakout")

    # Bearish breakdown
    if indicators.get('at_lower_bb'):
        score_put += 20
        reasons_put.append("Price breaking below lower Bollinger Band")

    if rsi and rsi < 40:
        score_put += 15
        reasons_put.append(f"RSI at {rsi:.1f} — weak momentum")

    if indicators.get('macd_histogram') and indicators['macd_histogram'] < 0:
        score_put += 15
        reasons_put.append("MACD histogram negative")

    if indicators.get('high_volume'):
        score_put += 20
        reasons_put.append("High volume confirms breakdown")

    if score_call >= SIGNAL_WEAK and score_call > score_put:
        return Signal(symbol, "BUY_CALL", min(score_call, 100), "breakout", reasons_call)
    elif score_put >= SIGNAL_WEAK and score_put > score_call:
        return Signal(symbol, "BUY_PUT", min(score_put, 100), "breakout", reasons_put)

    return None


def _apply_rsi_filter(signal: Signal, rsi: float | None) -> Signal:
    """
    Downgrade signals when RSI suggests a bounce/reversal is likely.

    - BUY PUT when RSI < 35 → likely oversold bounce coming, reduce score
    - BUY CALL when RSI > 65 → likely overbought reversal, reduce score
    """
    if signal is None or rsi is None:
        return signal

    penalty = 0
    warning = None

    if "PUT" in signal.direction and rsi < 35:
        penalty = 20
        warning = f"⚠️ RSI at {rsi:.1f} is near oversold — bounce likely, score reduced by {penalty}"
    elif "PUT" in signal.direction and rsi < 30:
        penalty = 30
        warning = f"⚠️ RSI at {rsi:.1f} is oversold — high bounce risk, score reduced by {penalty}"
    elif "CALL" in signal.direction and rsi > 65:
        penalty = 20
        warning = f"⚠️ RSI at {rsi:.1f} is near overbought — reversal likely, score reduced by {penalty}"
    elif "CALL" in signal.direction and rsi > 70:
        penalty = 30
        warning = f"⚠️ RSI at {rsi:.1f} is overbought — high reversal risk, score reduced by {penalty}"

    if penalty > 0:
        signal.score = max(signal.score - penalty, 0)
        signal.reasons.append(warning)

    return signal


def generate_oi_signal(symbol: str, indicators: dict,
                       options_data: dict = None) -> Signal | None:
    """
    Strategy 3: OI-Based Signal
    Uses options chain analytics (PCR, OI buildup, max pain) for direction.
    """
    if not options_data:
        return None

    score_call = 0
    score_put = 0
    reasons_call = []
    reasons_put = []

    # --- PCR Signal ---
    pcr = options_data.get("pcr", {})
    oi_pcr = pcr.get("oi_pcr", 0)

    if oi_pcr > 1.2:
        score_call += 25
        reasons_call.append(f"PCR {oi_pcr} — heavy put writing, strong bullish support")
    elif oi_pcr > 1.0:
        score_call += 15
        reasons_call.append(f"PCR {oi_pcr} — moderate bullish sentiment")

    if oi_pcr < 0.7:
        score_put += 25
        reasons_put.append(f"PCR {oi_pcr} — heavy call writing, strong bearish resistance")
    elif oi_pcr < 1.0:
        score_put += 15
        reasons_put.append(f"PCR {oi_pcr} — moderate bearish sentiment")

    # --- OI Buildup ---
    oi_buildup = options_data.get("oi_buildup", {})
    total_put_oi_change = oi_buildup.get("total_put_oi_change", 0)
    total_call_oi_change = oi_buildup.get("total_call_oi_change", 0)

    if total_put_oi_change > 0 and total_put_oi_change > abs(total_call_oi_change):
        score_call += 20
        reasons_call.append("Fresh put writing — support building")
    if total_call_oi_change > 0 and total_call_oi_change > abs(total_put_oi_change):
        score_put += 20
        reasons_put.append("Fresh call writing — resistance building")
    if total_call_oi_change < 0:
        score_call += 10
        reasons_call.append("Call unwinding — resistance weakening, bullish")
    if total_put_oi_change < 0:
        score_put += 10
        reasons_put.append("Put unwinding — support weakening, bearish")

    # --- Max Pain Gravity ---
    max_pain = options_data.get("max_pain", {})
    mp_strike = max_pain.get("strike")
    close = indicators.get("close", 0)

    if mp_strike and close:
        if close < mp_strike * 0.99:
            score_call += 15
            reasons_call.append(f"Spot below max pain {mp_strike} — gravitational pull upward")
        elif close > mp_strike * 1.01:
            score_put += 15
            reasons_put.append(f"Spot above max pain {mp_strike} — gravitational pull downward")

    # --- OI Support/Resistance ---
    oi_levels = options_data.get("oi_levels", {})
    support = oi_levels.get("support")
    resistance = oi_levels.get("resistance")

    if support and close and close > support:
        dist_pct = ((close - support) / close) * 100
        if dist_pct < 2:
            score_call += 15
            reasons_call.append(f"Near strong OI support at {support}")

    if resistance and close and close < resistance:
        dist_pct = ((resistance - close) / close) * 100
        if dist_pct < 2:
            score_put += 15
            reasons_put.append(f"Near strong OI resistance at {resistance}")

    # --- IV Skew ---
    iv_skew = options_data.get("iv_skew", {})
    skew_type = iv_skew.get("skew_type", "")
    if "Reverse" in skew_type:
        score_call += 10
        reasons_call.append("Reverse IV skew — upside demand from institutions")
    elif "Normal" in skew_type:
        score_put += 5
        reasons_put.append("Normal IV skew — downside protection demand")

    if score_call >= SIGNAL_WEAK and score_call > score_put:
        return Signal(symbol, "BUY_CALL", min(score_call, 100), "oi_analysis", reasons_call)
    elif score_put >= SIGNAL_WEAK and score_put > score_call:
        return Signal(symbol, "BUY_PUT", min(score_put, 100), "oi_analysis", reasons_put)

    return None


def _apply_vix_modifier(signal: Signal, vix: float = None) -> Signal:
    """
    Adjust signal score based on VIX level.
    High VIX = options expensive = penalize buy signals.
    """
    if signal is None or vix is None:
        return signal

    if vix > 25:
        signal.score = max(signal.score - 15, 0)
        signal.reasons.append(f"VIX {vix:.1f} very high — options expensive, score reduced")
    elif vix > 20:
        signal.score = max(signal.score - 8, 0)
        signal.reasons.append(f"VIX {vix:.1f} elevated — slight penalty")
    elif vix < 13:
        signal.score = min(signal.score + 5, 100)
        signal.reasons.append(f"VIX {vix:.1f} low — options cheap, bonus")

    return signal


def generate_all_signals(symbol: str, indicators: dict,
                         options_data: dict = None,
                         vix: float = None) -> list[Signal]:
    """
    Run all strategies, apply safety filters, and return valid signals.

    Args:
        symbol: Stock symbol
        indicators: Technical indicator values
        options_data: Options chain analytics (from OptionsChainAnalyzer)
        vix: Current India VIX value
    """
    signals = []
    rsi = indicators.get('rsi')

    trend = generate_trend_signal(symbol, indicators)
    if trend:
        trend = _apply_rsi_filter(trend, rsi)
        signals.append(trend)

    breakout = generate_breakout_signal(symbol, indicators)
    if breakout:
        breakout = _apply_rsi_filter(breakout, rsi)
        signals.append(breakout)

    # OI-based signal (if chain data available)
    if options_data:
        oi_signal = generate_oi_signal(symbol, indicators, options_data)
        if oi_signal:
            signals.append(oi_signal)

    # Apply VIX modifier to all signals
    if vix:
        signals = [_apply_vix_modifier(s, vix) for s in signals]

    # Filter out signals that dropped below threshold after filters
    signals = [s for s in signals if s.score >= SIGNAL_WEAK]

    # Sort by score (highest first)
    signals.sort(key=lambda s: s.score, reverse=True)
    return signals


def format_signal_report(signals: list[Signal]) -> str:
    """Create a readable report of all signals."""
    if not signals:
        return "📭 No trading signals at this time.\n"

    lines = ["=" * 60, "📊 TRADING SIGNALS REPORT", "=" * 60, ""]

    for sig in signals:
        emoji = "🟢" if "CALL" in sig.direction else "🔴"
        strength_emoji = {"STRONG": "🔥", "MODERATE": "⚡", "WEAK": "💤"}.get(sig.strength, "")

        name = SYMBOL_NAMES.get(sig.symbol, sig.symbol)
        lines.append(f"{emoji} {name} → {sig.direction}")
        lines.append(f"   Score: {sig.score}/100 {strength_emoji} {sig.strength}")
        lines.append(f"   Strategy: {sig.strategy.upper()}")
        lines.append(f"   Reasons:")
        for reason in sig.reasons:
            lines.append(f"     ✓ {reason}")
        lines.append("")

    return "\n".join(lines)

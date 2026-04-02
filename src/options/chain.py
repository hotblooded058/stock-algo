"""
Options Chain Analyzer
Computes OI analytics, PCR, Max Pain, IV skew, and support/resistance from chain data.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.db.database import Database
from src.options.greeks import calculate_greeks, time_to_expiry


class OptionsChainAnalyzer:
    """Analyzes options chain data for trading decisions."""

    def __init__(self, db: Database = None):
        self.db = db or Database()

    def analyze(self, underlying: str, expiry: str = None, spot_price: float = None) -> dict:
        """
        Full analysis of an options chain.
        Returns PCR, max pain, OI support/resistance, IV skew, and enriched chain.
        """
        chain = self.db.get_options_chain(underlying, expiry)
        if not chain:
            return {"error": "No chain data available", "underlying": underlying}

        calls = [c for c in chain if c["option_type"] == "CE"]
        puts = [c for c in chain if c["option_type"] == "PE"]

        # Determine expiry from data if not provided
        if not expiry and chain:
            expiry = chain[0].get("expiry", "")

        # Enrich with Greeks if spot price available
        if spot_price and expiry:
            calls = self._enrich_greeks(calls, spot_price, expiry)
            puts = self._enrich_greeks(puts, spot_price, expiry)

        pcr = self._compute_pcr(calls, puts)
        max_pain = self._compute_max_pain(calls, puts)
        oi_levels = self._compute_oi_levels(calls, puts)
        iv_skew = self._compute_iv_skew(calls, puts, spot_price)
        oi_buildup = self._compute_oi_buildup(calls, puts)

        return {
            "underlying": underlying,
            "expiry": expiry,
            "spot_price": spot_price,
            "pcr": pcr,
            "max_pain": max_pain,
            "oi_levels": oi_levels,
            "iv_skew": iv_skew,
            "oi_buildup": oi_buildup,
            "chain": {"calls": calls, "puts": puts},
            "summary": self._generate_summary(pcr, max_pain, oi_levels, iv_skew, spot_price),
        }

    # ========================================================
    # PCR (Put-Call Ratio)
    # ========================================================

    def _compute_pcr(self, calls: list[dict], puts: list[dict]) -> dict:
        """
        Compute Put-Call Ratio from OI and volume.
        PCR > 1.0 = Bullish (more put writing = support)
        PCR < 0.7 = Bearish (more call writing = resistance)
        """
        total_call_oi = sum(c.get("oi") or 0 for c in calls)
        total_put_oi = sum(p.get("oi") or 0 for p in puts)
        total_call_vol = sum(c.get("volume") or 0 for c in calls)
        total_put_vol = sum(p.get("volume") or 0 for p in puts)

        oi_pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0
        vol_pcr = round(total_put_vol / total_call_vol, 3) if total_call_vol > 0 else 0

        if oi_pcr > 1.2:
            sentiment = "Strong Bullish"
        elif oi_pcr > 1.0:
            sentiment = "Bullish"
        elif oi_pcr > 0.7:
            sentiment = "Neutral"
        elif oi_pcr > 0.5:
            sentiment = "Bearish"
        else:
            sentiment = "Strong Bearish"

        return {
            "oi_pcr": oi_pcr,
            "volume_pcr": vol_pcr,
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
            "total_call_volume": total_call_vol,
            "total_put_volume": total_put_vol,
            "sentiment": sentiment,
        }

    # ========================================================
    # MAX PAIN
    # ========================================================

    def _compute_max_pain(self, calls: list[dict], puts: list[dict]) -> dict:
        """
        Max Pain — the strike where total option buyer loss is maximized.
        Market tends to gravitate toward max pain near expiry.
        """
        if not calls or not puts:
            return {"strike": None, "interpretation": "Insufficient data"}

        strikes = sorted(set(c["strike"] for c in calls) | set(p["strike"] for p in puts))
        call_oi_map = {c["strike"]: c.get("oi") or 0 for c in calls}
        put_oi_map = {p["strike"]: p.get("oi") or 0 for p in puts}

        min_pain = float("inf")
        max_pain_strike = None
        pain_by_strike = {}

        for settlement in strikes:
            call_pain = sum(
                max(0, settlement - strike) * oi
                for strike, oi in call_oi_map.items()
            )
            put_pain = sum(
                max(0, strike - settlement) * oi
                for strike, oi in put_oi_map.items()
            )
            total_pain = call_pain + put_pain
            pain_by_strike[settlement] = total_pain

            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = settlement

        return {
            "strike": max_pain_strike,
            "total_pain_value": min_pain,
            "interpretation": f"Market likely to gravitate toward {max_pain_strike} near expiry",
        }

    # ========================================================
    # OI-BASED SUPPORT / RESISTANCE
    # ========================================================

    def _compute_oi_levels(self, calls: list[dict], puts: list[dict]) -> dict:
        """
        Identify support and resistance from OI concentration.
        - Highest Put OI strike = Strong Support (put sellers defend this)
        - Highest Call OI strike = Strong Resistance (call sellers defend this)
        """
        # Top 5 call OI strikes (resistance)
        sorted_calls = sorted(calls, key=lambda c: c.get("oi") or 0, reverse=True)
        top_call_oi = [
            {"strike": c["strike"], "oi": c.get("oi") or 0, "oi_change": c.get("oi_change") or 0}
            for c in sorted_calls[:5]
        ]

        # Top 5 put OI strikes (support)
        sorted_puts = sorted(puts, key=lambda p: p.get("oi") or 0, reverse=True)
        top_put_oi = [
            {"strike": p["strike"], "oi": p.get("oi") or 0, "oi_change": p.get("oi_change") or 0}
            for p in sorted_puts[:5]
        ]

        resistance = top_call_oi[0]["strike"] if top_call_oi else None
        support = top_put_oi[0]["strike"] if top_put_oi else None

        return {
            "resistance": resistance,
            "support": support,
            "resistance_levels": top_call_oi,
            "support_levels": top_put_oi,
            "range": f"{support} - {resistance}" if support and resistance else None,
        }

    # ========================================================
    # IV SKEW
    # ========================================================

    def _compute_iv_skew(self, calls: list[dict], puts: list[dict],
                          spot_price: float = None) -> dict:
        """
        Analyze IV skew across strikes.
        - Normal skew: OTM puts have higher IV (fear premium)
        - Reverse skew: OTM calls have higher IV (bullish pressure)
        - Flat: Uniform IV
        """
        call_ivs = [(c["strike"], c.get("iv") or 0) for c in calls if c.get("iv")]
        put_ivs = [(p["strike"], p.get("iv") or 0) for p in puts if p.get("iv")]

        if not call_ivs and not put_ivs:
            return {"skew_type": "Unknown", "message": "No IV data available"}

        # ATM IV (closest to spot)
        atm_iv = None
        if spot_price and call_ivs:
            atm_call = min(call_ivs, key=lambda x: abs(x[0] - spot_price))
            atm_iv = atm_call[1]

        # OTM put IV average (strikes below spot)
        otm_put_ivs = [iv for strike, iv in put_ivs if spot_price and strike < spot_price]
        avg_otm_put_iv = sum(otm_put_ivs) / len(otm_put_ivs) if otm_put_ivs else 0

        # OTM call IV average (strikes above spot)
        otm_call_ivs = [iv for strike, iv in call_ivs if spot_price and strike > spot_price]
        avg_otm_call_iv = sum(otm_call_ivs) / len(otm_call_ivs) if otm_call_ivs else 0

        # Determine skew
        if avg_otm_put_iv > avg_otm_call_iv * 1.1:
            skew_type = "Normal (Put Skew)"
            interpretation = "Fear premium — OTM puts are expensive. Market cautious on downside."
        elif avg_otm_call_iv > avg_otm_put_iv * 1.1:
            skew_type = "Reverse (Call Skew)"
            interpretation = "Bullish pressure — OTM calls are expensive. Upside demand high."
        else:
            skew_type = "Flat"
            interpretation = "No significant directional pressure in IV."

        return {
            "skew_type": skew_type,
            "atm_iv": round(atm_iv, 2) if atm_iv else None,
            "avg_otm_put_iv": round(avg_otm_put_iv, 2),
            "avg_otm_call_iv": round(avg_otm_call_iv, 2),
            "interpretation": interpretation,
        }

    # ========================================================
    # OI BUILDUP ANALYSIS
    # ========================================================

    def _compute_oi_buildup(self, calls: list[dict], puts: list[dict]) -> dict:
        """
        Analyze OI change patterns to detect buildup or unwinding.

        Key patterns:
        - Long buildup: Price up + OI up (Bullish)
        - Short buildup: Price down + OI up (Bearish)
        - Short covering: Price up + OI down (Bullish exit)
        - Long unwinding: Price down + OI down (Bearish exit)
        """
        # Significant OI additions (positive oi_change)
        call_additions = [
            {"strike": c["strike"], "oi_change": c.get("oi_change") or 0, "oi": c.get("oi") or 0}
            for c in calls if (c.get("oi_change") or 0) > 0
        ]
        put_additions = [
            {"strike": p["strike"], "oi_change": p.get("oi_change") or 0, "oi": p.get("oi") or 0}
            for p in puts if (p.get("oi_change") or 0) > 0
        ]

        # Significant OI reductions (negative oi_change)
        call_unwinding = [
            {"strike": c["strike"], "oi_change": c.get("oi_change") or 0}
            for c in calls if (c.get("oi_change") or 0) < 0
        ]
        put_unwinding = [
            {"strike": p["strike"], "oi_change": p.get("oi_change") or 0}
            for p in puts if (p.get("oi_change") or 0) < 0
        ]

        # Sort by magnitude
        call_additions.sort(key=lambda x: x["oi_change"], reverse=True)
        put_additions.sort(key=lambda x: x["oi_change"], reverse=True)

        total_call_oi_change = sum(c.get("oi_change") or 0 for c in calls)
        total_put_oi_change = sum(p.get("oi_change") or 0 for p in puts)

        # Interpret
        signals = []
        if total_put_oi_change > 0 and total_put_oi_change > total_call_oi_change:
            signals.append("Put writing increasing — Bullish support building")
        if total_call_oi_change > 0 and total_call_oi_change > total_put_oi_change:
            signals.append("Call writing increasing — Bearish resistance building")
        if total_put_oi_change < 0:
            signals.append("Put unwinding — Support weakening")
        if total_call_oi_change < 0:
            signals.append("Call unwinding — Resistance weakening")

        return {
            "total_call_oi_change": total_call_oi_change,
            "total_put_oi_change": total_put_oi_change,
            "top_call_additions": call_additions[:3],
            "top_put_additions": put_additions[:3],
            "call_unwinding_strikes": len(call_unwinding),
            "put_unwinding_strikes": len(put_unwinding),
            "signals": signals,
        }

    # ========================================================
    # GREEKS ENRICHMENT
    # ========================================================

    def _enrich_greeks(self, options: list[dict], spot: float, expiry: str) -> list[dict]:
        """Add calculated Greeks to each option in the chain."""
        for opt in options:
            strike = opt["strike"]
            option_type = opt["option_type"]
            ltp = opt.get("ltp") or 0

            if ltp > 0 and spot > 0:
                greeks = calculate_greeks(
                    spot=spot,
                    strike=strike,
                    expiry=expiry,
                    option_type=option_type,
                    market_price=ltp,
                )
                opt["iv"] = greeks["iv"]
                opt["delta"] = greeks["delta"]
                opt["gamma"] = greeks["gamma"]
                opt["theta"] = greeks["theta"]
                opt["vega"] = greeks["vega"]
                opt["moneyness"] = greeks["moneyness"]

        return options

    # ========================================================
    # SUMMARY
    # ========================================================

    def _generate_summary(self, pcr: dict, max_pain: dict, oi_levels: dict,
                           iv_skew: dict, spot_price: float = None) -> dict:
        """Generate a human-readable trading summary from all analytics."""
        bias_points = 0
        reasons = []

        # PCR signal
        if pcr["oi_pcr"] > 1.2:
            bias_points += 2
            reasons.append(f"PCR {pcr['oi_pcr']} — strong put writing, bullish")
        elif pcr["oi_pcr"] > 1.0:
            bias_points += 1
            reasons.append(f"PCR {pcr['oi_pcr']} — moderate bullish")
        elif pcr["oi_pcr"] < 0.7:
            bias_points -= 2
            reasons.append(f"PCR {pcr['oi_pcr']} — heavy call writing, bearish")
        elif pcr["oi_pcr"] < 1.0:
            bias_points -= 1
            reasons.append(f"PCR {pcr['oi_pcr']} — moderate bearish")

        # Max pain vs spot
        if spot_price and max_pain["strike"]:
            mp = max_pain["strike"]
            if spot_price > mp * 1.01:
                bias_points -= 1
                reasons.append(f"Spot above max pain {mp} — may pull down")
            elif spot_price < mp * 0.99:
                bias_points += 1
                reasons.append(f"Spot below max pain {mp} — may pull up")

        # OI levels
        if spot_price and oi_levels["support"] and oi_levels["resistance"]:
            dist_to_support = spot_price - oi_levels["support"]
            dist_to_resistance = oi_levels["resistance"] - spot_price
            if dist_to_support < dist_to_resistance:
                reasons.append(f"Closer to OI support {oi_levels['support']}")
            else:
                reasons.append(f"Closer to OI resistance {oi_levels['resistance']}")

        # IV skew
        if iv_skew.get("skew_type") == "Normal (Put Skew)":
            reasons.append("Put skew — market pricing downside risk")
        elif iv_skew.get("skew_type") == "Reverse (Call Skew)":
            reasons.append("Call skew — upside demand")

        if bias_points >= 2:
            overall = "Bullish"
        elif bias_points >= 1:
            overall = "Mildly Bullish"
        elif bias_points <= -2:
            overall = "Bearish"
        elif bias_points <= -1:
            overall = "Mildly Bearish"
        else:
            overall = "Neutral"

        return {
            "bias": overall,
            "bias_score": bias_points,
            "reasons": reasons,
        }

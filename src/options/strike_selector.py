"""
Strike Selector
Recommends the optimal option strike based on signal, Greeks, IV, and risk profile.
"""

import sys
import os
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.options.greeks import calculate_greeks, time_to_expiry
from src.db.database import Database
from config.settings import LOT_SIZES


class StrikeSelector:
    """Selects optimal option strike for a trading signal."""

    def __init__(self, db: Database = None):
        self.db = db or Database()

    def recommend(
        self,
        underlying: str,
        spot_price: float,
        direction: str,
        expiry: str,
        chain: list[dict] = None,
        risk_profile: str = "moderate",
    ) -> dict:
        """
        Recommend the best strike for a given trade setup.

        Args:
            underlying: NIFTY, BANKNIFTY, RELIANCE, etc.
            spot_price: Current price of underlying
            direction: BUY_CALL or BUY_PUT
            expiry: Expiry date (YYYY-MM-DD)
            chain: Options chain data (if available)
            risk_profile: "conservative", "moderate", "aggressive"

        Returns:
            dict with recommended strike, reasons, and alternatives
        """
        option_type = "CE" if "CALL" in direction else "PE"
        lot_size = LOT_SIZES.get(underlying, 1)
        dte = time_to_expiry(expiry)
        dte_days = round(dte * 365)

        # Target delta based on risk profile
        delta_targets = {
            "conservative": 0.55,   # Slight ITM — higher probability
            "moderate": 0.45,       # ATM — balanced risk/reward
            "aggressive": 0.30,     # OTM — cheaper, higher leverage
        }
        target_delta = delta_targets.get(risk_profile, 0.45)

        # Determine strike interval
        if underlying in ("NIFTY", "FINNIFTY"):
            strike_interval = 50
        elif underlying == "BANKNIFTY":
            strike_interval = 100
        else:
            strike_interval = _guess_strike_interval(spot_price)

        # ATM strike
        atm_strike = round(spot_price / strike_interval) * strike_interval

        # Generate candidate strikes
        candidates = []
        for offset in range(-5, 6):
            strike = atm_strike + (offset * strike_interval)
            if strike <= 0:
                continue

            greeks = calculate_greeks(
                spot=spot_price,
                strike=strike,
                expiry=expiry,
                option_type=option_type,
            )

            # Get market data from chain if available
            market_ltp = None
            market_oi = None
            market_iv = None
            if chain:
                match = next(
                    (c for c in chain if c["strike"] == strike and c["option_type"] == option_type),
                    None
                )
                if match:
                    market_ltp = match.get("ltp")
                    market_oi = match.get("oi")
                    market_iv = match.get("iv")

                    # Recalculate Greeks with market price for better IV
                    if market_ltp and market_ltp > 0:
                        greeks = calculate_greeks(
                            spot=spot_price,
                            strike=strike,
                            expiry=expiry,
                            option_type=option_type,
                            market_price=market_ltp,
                        )

            # Score this strike
            score, reasons = self._score_strike(
                strike=strike,
                spot=spot_price,
                option_type=option_type,
                greeks=greeks,
                target_delta=target_delta,
                dte_days=dte_days,
                market_ltp=market_ltp,
                market_oi=market_oi,
                market_iv=market_iv,
                lot_size=lot_size,
            )

            candidates.append({
                "strike": strike,
                "option_type": option_type,
                "ltp": market_ltp or greeks["theoretical_price"],
                "iv": market_iv or greeks["iv"],
                "delta": greeks["delta"],
                "gamma": greeks["gamma"],
                "theta": greeks["theta"],
                "vega": greeks["vega"],
                "moneyness": greeks["moneyness"],
                "oi": market_oi,
                "score": score,
                "reasons": reasons,
                "lot_size": lot_size,
                "lot_value": round((market_ltp or greeks["theoretical_price"]) * lot_size, 2),
            })

        # Sort by score
        candidates.sort(key=lambda x: x["score"], reverse=True)

        recommended = candidates[0] if candidates else None
        alternatives = candidates[1:3] if len(candidates) > 1 else []

        return {
            "underlying": underlying,
            "direction": direction,
            "expiry": expiry,
            "dte_days": dte_days,
            "spot_price": spot_price,
            "atm_strike": atm_strike,
            "risk_profile": risk_profile,
            "recommended": recommended,
            "alternatives": alternatives,
            "all_strikes": candidates,
        }

    def _score_strike(
        self,
        strike: float,
        spot: float,
        option_type: str,
        greeks: dict,
        target_delta: float,
        dte_days: int,
        market_ltp: float = None,
        market_oi: float = None,
        market_iv: float = None,
        lot_size: int = 1,
    ) -> tuple[float, list[str]]:
        """Score a strike candidate. Higher = better."""
        score = 50.0  # Start at neutral
        reasons = []

        abs_delta = abs(greeks["delta"])

        # 1. Delta proximity to target (max 25 points)
        delta_diff = abs(abs_delta - target_delta)
        delta_score = max(0, 25 - (delta_diff * 100))
        score += delta_score
        if delta_diff < 0.05:
            reasons.append(f"Delta {greeks['delta']:.2f} matches target {target_delta:.2f}")

        # 2. Liquidity — prefer strikes with higher OI (max 15 points)
        if market_oi and market_oi > 0:
            if market_oi > 100000:
                score += 15
                reasons.append(f"High liquidity (OI: {market_oi:,})")
            elif market_oi > 50000:
                score += 10
                reasons.append(f"Good liquidity (OI: {market_oi:,})")
            elif market_oi > 10000:
                score += 5

        # 3. Bid-ask spread — avoid illiquid strikes
        # (Approximated: if OI is very low, penalize)
        if market_oi is not None and market_oi < 1000:
            score -= 10
            reasons.append("Low OI — may have wide bid-ask spread")

        # 4. IV — avoid overpaying (max 10 points)
        iv = market_iv or greeks.get("iv", 0)
        if iv > 0:
            if iv < 20:
                score += 10
                reasons.append(f"IV {iv:.1f}% — options reasonably priced")
            elif iv < 30:
                score += 5
            elif iv > 40:
                score -= 5
                reasons.append(f"IV {iv:.1f}% — options expensive")
            elif iv > 50:
                score -= 10
                reasons.append(f"IV {iv:.1f}% — very expensive, high theta decay")

        # 5. Theta — avoid excessive time decay for short DTE (max 10 points)
        if dte_days <= 2:
            score -= 15
            reasons.append(f"Only {dte_days} DTE — extreme theta decay")
        elif dte_days <= 5:
            if abs(greeks["theta"]) > 20:
                score -= 5
                reasons.append(f"High theta decay ({greeks['theta']:.1f}/day) with {dte_days} DTE")
        elif dte_days >= 7:
            score += 5

        # 6. Affordability — premium shouldn't be too high or too low
        premium = market_ltp or greeks["theoretical_price"]
        lot_cost = premium * lot_size
        if premium < 5:
            score -= 10
            reasons.append("Premium too low — likely deep OTM, low probability")
        elif premium > 500 and option_type == "CE":
            score -= 5
            reasons.append(f"High premium ₹{premium:.0f} — large capital at risk")

        # 7. Moneyness preference
        moneyness = greeks.get("moneyness", "")
        if moneyness == "ATM":
            score += 5
            reasons.append("ATM — highest gamma, best for directional moves")
        elif moneyness == "ITM":
            score += 3
            reasons.append("ITM — higher delta, lower risk of expiring worthless")

        return round(score, 1), reasons

    def quick_recommend(
        self,
        underlying: str,
        spot_price: float,
        direction: str,
        dte_days: int = 7,
    ) -> dict:
        """
        Quick strike recommendation without chain data.
        Uses theoretical pricing only.
        """
        from datetime import date, timedelta
        expiry = (date.today() + timedelta(days=dte_days)).isoformat()
        return self.recommend(underlying, spot_price, direction, expiry)


def _guess_strike_interval(price: float) -> float:
    """Guess strike interval based on stock price."""
    if price > 5000:
        return 100
    elif price > 1000:
        return 50
    elif price > 500:
        return 20
    elif price > 100:
        return 10
    return 5

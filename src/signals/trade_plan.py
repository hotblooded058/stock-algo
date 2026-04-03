"""
Trade Plan Generator
Creates a complete actionable trade plan for a stock including:
- Direction (CALL/PUT) with confidence
- Recommended strike + premium
- Stop loss + target levels
- Position sizing
- Strategy checklist
- Risk warnings
"""

import sys
import os
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.data.fetcher import fetch_stock_data
from src.indicators.technical import add_all_indicators, get_latest_indicators
from src.signals.generator import generate_all_signals
from src.options.strike_selector import StrikeSelector
from src.options.greeks import calculate_greeks, time_to_expiry
from src.data.fno_stocks import FNO_STOCKS, get_lot_size
from config.settings import (
    TOTAL_CAPITAL, MAX_RISK_PER_TRADE, STOP_LOSS_PERCENT,
    TARGET_1_PERCENT, TARGET_2_PERCENT, MAX_OPEN_POSITIONS
)


class TradePlanGenerator:

    def __init__(self, capital: float = TOTAL_CAPITAL):
        self.capital = capital
        self.strike_selector = StrikeSelector()

    def generate(self, symbol: str) -> dict:
        """
        Generate complete trade plan for a symbol.
        Returns everything needed to make a trading decision.
        """
        info = FNO_STOCKS.get(symbol, {})
        yahoo = info.get("yahoo", f"{symbol}.NS")
        lot_size = info.get("lot", 1)
        sector = info.get("sector", "Other")

        # Use same data source as screener (Yahoo) for consistency
        # AngelOne historical has rate limits and gives slightly different
        # candle data, causing screener/trade-plan signal mismatch
        import pandas as pd

        df = fetch_stock_data(yahoo, period="3mo", interval="1d")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty or len(df) < 30:
            return {"error": f"Could not fetch data for {symbol}"}

        df = add_all_indicators(df)
        indicators = get_latest_indicators(df)
        spot = float(df["Close"].iloc[-1])

        # Generate signals
        signals = generate_all_signals(yahoo, indicators)

        # Market condition assessment
        market = self._assess_market(indicators)

        # No signal case
        if not signals:
            return {
                "symbol": symbol,
                "sector": sector,
                "spot_price": round(spot, 2),
                "verdict": "NO TRADE",
                "confidence": 0,
                "market": market,
                "message": "No trading signal. The algo doesn't see a high-probability setup right now.",
                "reasons_to_skip": self._reasons_to_skip(indicators),
                "wait_for": self._what_to_wait_for(indicators),
            }

        # Best signal
        best = signals[0]
        direction = best.direction
        option_type = "CE" if "CALL" in direction else "PE"

        # Get strike recommendation
        expiry = self._next_weekly_expiry()
        dte = (datetime.strptime(expiry, "%Y-%m-%d").date() - date.today()).days

        strike_rec = self.strike_selector.quick_recommend(
            symbol, spot, direction, dte_days=max(dte, 3)
        )
        recommended = strike_rec.get("recommended", {})

        # Build trade plan
        premium = recommended.get("ltp", 0)
        if premium <= 0:
            premium = self._estimate_premium(spot, option_type, dte)

        sl_premium = round(premium * (1 - STOP_LOSS_PERCENT), 2)
        target1_premium = round(premium * (1 + TARGET_1_PERCENT), 2)
        target2_premium = round(premium * (1 + TARGET_2_PERCENT), 2)
        risk_per_unit = premium - sl_premium

        # Position sizing
        max_risk = self.capital * MAX_RISK_PER_TRADE
        if risk_per_unit > 0:
            raw_qty = int(max_risk / risk_per_unit)
            quantity = max(lot_size, (raw_qty // lot_size) * lot_size)
        else:
            quantity = lot_size

        total_cost = round(premium * quantity, 2)
        max_loss = round(risk_per_unit * quantity, 2)
        target1_profit = round((target1_premium - premium) * quantity, 2)
        target2_profit = round((target2_premium - premium) * quantity, 2)

        # Risk-reward ratio
        rr_ratio = round(target1_profit / max_loss, 2) if max_loss > 0 else 0

        # Confidence assessment
        confidence = self._calculate_confidence(best, indicators, market)

        # Strategy checklist
        checklist = self._build_checklist(best, indicators, market)

        # Warnings
        warnings = self._build_warnings(indicators, market, dte, premium, spot)

        return {
            "symbol": symbol,
            "sector": sector,
            "spot_price": round(spot, 2),

            # Verdict
            "verdict": direction.replace("BUY_", "BUY "),
            "confidence": confidence,
            "confidence_label": "HIGH" if confidence >= 80 else "MEDIUM" if confidence >= 60 else "LOW",
            "signal_score": best.score,
            "signal_strength": best.strength,
            "strategy": best.strategy,
            "reasons": best.reasons,

            # Market assessment
            "market": market,

            # Option recommendation
            "option": {
                "type": option_type,
                "strike": recommended.get("strike", round(spot)),
                "expiry": expiry,
                "dte": dte,
                "estimated_premium": round(premium, 2),
                "delta": recommended.get("delta", 0),
                "theta": recommended.get("theta", 0),
                "iv": recommended.get("iv", 0),
                "moneyness": recommended.get("moneyness", "ATM"),
            },

            # Trade plan
            "plan": {
                "entry_premium": round(premium, 2),
                "stop_loss": sl_premium,
                "target_1": target1_premium,
                "target_2": target2_premium,
                "quantity": quantity,
                "lot_size": lot_size,
                "total_cost": total_cost,
                "max_loss": max_loss,
                "target_1_profit": target1_profit,
                "target_2_profit": target2_profit,
                "risk_reward": rr_ratio,
                "risk_pct_of_capital": round((max_loss / self.capital) * 100, 2),
            },

            # Strategy advice
            "checklist": checklist,

            # Warnings
            "warnings": warnings,

            # When to exit
            "exit_rules": [
                f"STOP LOSS: Exit immediately if premium drops to ₹{sl_premium} (-{STOP_LOSS_PERCENT*100:.0f}%)",
                f"TARGET 1: Book 50% at ₹{target1_premium} (+{TARGET_1_PERCENT*100:.0f}%)",
                f"TARGET 2: Book remaining at ₹{target2_premium} (+{TARGET_2_PERCENT*100:.0f}%)",
                f"TIME EXIT: Close by 3:15 PM if intraday, or {dte-1} days before expiry",
                "NEVER hold overnight if VIX > 25",
                "If underlying reverses trend (SuperTrend flips) — exit regardless of premium",
            ],

            # When NOT to take this trade
            "avoid_if": self._avoid_conditions(indicators, market, dte),
        }

    def _assess_market(self, indicators: dict) -> dict:
        """Assess overall market conditions."""
        rsi = indicators.get("rsi", 50)
        adx = indicators.get("adx", 20)
        above_vwap = indicators.get("above_vwap")
        supertrend = indicators.get("supertrend_bullish")
        volume_ratio = indicators.get("volume_ratio", 1)
        above_ema21 = indicators.get("above_ema_21")
        above_ema50 = indicators.get("above_ema_50")

        # Market regime
        if adx and adx > 30:
            regime = "Strong Trend"
        elif adx and adx > 20:
            regime = "Moderate Trend"
        else:
            regime = "Choppy / Sideways"

        # Direction
        bullish_points = 0
        if above_ema21: bullish_points += 1
        if above_ema50: bullish_points += 1
        if supertrend: bullish_points += 1
        if above_vwap: bullish_points += 1
        if rsi and rsi > 50: bullish_points += 1

        if bullish_points >= 4:
            direction = "Bullish"
        elif bullish_points >= 3:
            direction = "Mildly Bullish"
        elif bullish_points <= 1:
            direction = "Bearish"
        elif bullish_points <= 2:
            direction = "Mildly Bearish"
        else:
            direction = "Neutral"

        return {
            "regime": regime,
            "direction": direction,
            "adx": round(adx, 1) if adx else None,
            "rsi": round(rsi, 1) if rsi else None,
            "above_vwap": above_vwap,
            "supertrend": "Bullish" if supertrend else "Bearish" if supertrend is False else None,
            "volume": "High" if volume_ratio and volume_ratio > 1.5 else "Normal" if volume_ratio and volume_ratio >= 0.8 else "Low",
            "volume_ratio": round(volume_ratio, 2) if volume_ratio else None,
        }

    def _calculate_confidence(self, signal, indicators: dict, market: dict) -> int:
        """Calculate overall confidence 0-100."""
        conf = signal.score

        # ADX bonus/penalty
        adx = market.get("adx", 20)
        if adx and adx > 30:
            conf = min(conf + 5, 100)
        elif adx and adx < 20:
            conf = max(conf - 10, 0)

        # VWAP alignment
        if market.get("above_vwap") is not None:
            if ("CALL" in signal.direction and market["above_vwap"]) or \
               ("PUT" in signal.direction and not market["above_vwap"]):
                conf = min(conf + 5, 100)
            else:
                conf = max(conf - 5, 0)

        # Volume
        if market.get("volume") == "High":
            conf = min(conf + 5, 100)
        elif market.get("volume") == "Low":
            conf = max(conf - 10, 0)

        return conf

    def _build_checklist(self, signal, indicators: dict, market: dict) -> list[dict]:
        """Build a strategy checklist — what to verify before entering."""
        checks = []
        direction = signal.direction

        # 1. Trend alignment
        if "CALL" in direction:
            passed = indicators.get("above_ema_21", False)
            checks.append({"check": "Price above EMA 21 (uptrend)", "passed": bool(passed), "critical": True})
        else:
            passed = not indicators.get("above_ema_21", True)
            checks.append({"check": "Price below EMA 21 (downtrend)", "passed": bool(passed), "critical": True})

        # 2. SuperTrend
        st = indicators.get("supertrend_bullish")
        if "CALL" in direction:
            checks.append({"check": "SuperTrend is Bullish", "passed": bool(st), "critical": True})
        else:
            checks.append({"check": "SuperTrend is Bearish", "passed": st is False, "critical": True})

        # 3. VWAP
        vwap = indicators.get("above_vwap")
        if "CALL" in direction:
            checks.append({"check": "Price above VWAP", "passed": bool(vwap), "critical": False})
        else:
            checks.append({"check": "Price below VWAP", "passed": vwap is False, "critical": False})

        # 4. ADX
        adx = indicators.get("adx", 0)
        checks.append({
            "check": f"ADX > 25 (trending market) — current: {adx:.0f}" if adx else "ADX > 25",
            "passed": bool(adx and adx > 25),
            "critical": True,
        })

        # 5. RSI
        rsi = indicators.get("rsi", 50)
        if "CALL" in direction:
            ok = rsi and 40 <= rsi <= 70
            checks.append({"check": f"RSI 40-70 (not overbought) — current: {rsi:.0f}", "passed": bool(ok), "critical": False})
        else:
            ok = rsi and 30 <= rsi <= 60
            checks.append({"check": f"RSI 30-60 (not oversold) — current: {rsi:.0f}", "passed": bool(ok), "critical": False})

        # 6. Volume
        vr = indicators.get("volume_ratio", 1)
        checks.append({
            "check": f"Volume > average — current: {vr:.1f}x" if vr else "Volume above average",
            "passed": bool(vr and vr >= 1.0),
            "critical": False,
        })

        # 7. Time of day
        now = datetime.now()
        good_time = (9 <= now.hour < 12) or (13 <= now.hour < 15)
        checks.append({
            "check": "Good trading hours (avoid 9:15-9:30 and lunch)",
            "passed": good_time,
            "critical": False,
        })

        return checks

    def _build_warnings(self, indicators, market, dte, premium, spot) -> list[str]:
        """Generate risk warnings."""
        warnings = []

        adx = market.get("adx", 20)
        if adx and adx < 20:
            warnings.append("Market is CHOPPY (ADX < 20). Trend signals are less reliable. Consider skipping.")

        rsi = indicators.get("rsi", 50)
        if rsi and (rsi > 70 or rsi < 30):
            warnings.append(f"RSI at extreme ({rsi:.0f}). Reversal risk is high.")

        if market.get("volume") == "Low":
            warnings.append("LOW VOLUME today. Moves may not sustain. Use smaller position.")

        if dte <= 2:
            warnings.append(f"Only {dte} days to expiry! Theta decay will be extreme. Avoid buying.")

        if premium > 0 and premium * get_lot_size(indicators.get("symbol", "")) > self.capital * 0.1:
            warnings.append("Position cost > 10% of capital. Consider smaller quantity.")

        vwap_mismatch = False
        if market.get("above_vwap") is False and market.get("direction", "").startswith("Bull"):
            vwap_mismatch = True
        if market.get("above_vwap") is True and market.get("direction", "").startswith("Bear"):
            vwap_mismatch = True
        if vwap_mismatch:
            warnings.append("VWAP conflicts with signal direction. Institutional flow may be against you.")

        return warnings

    def _reasons_to_skip(self, indicators) -> list[str]:
        """Why there's no trade signal."""
        reasons = []
        adx = indicators.get("adx", 20)
        if adx and adx < 20:
            reasons.append(f"Market is choppy (ADX {adx:.0f}). No clear trend.")
        if indicators.get("above_ema_21") and indicators.get("supertrend_bullish") is False:
            reasons.append("Mixed signals: Price above EMA but SuperTrend bearish.")
        if not indicators.get("above_ema_21") and indicators.get("supertrend_bullish"):
            reasons.append("Mixed signals: Price below EMA but SuperTrend bullish.")
        vr = indicators.get("volume_ratio", 1)
        if vr and vr < 0.8:
            reasons.append(f"Low volume ({vr:.1f}x avg). No institutional activity.")
        if not reasons:
            reasons.append("Indicators are mixed — no clear directional bias.")
        return reasons

    def _what_to_wait_for(self, indicators) -> list[str]:
        """What conditions to wait for before trading."""
        wait = []
        if indicators.get("adx") and indicators["adx"] < 25:
            wait.append("Wait for ADX to cross above 25 (trend emerging)")
        if indicators.get("rsi") and 45 <= indicators["rsi"] <= 55:
            wait.append("RSI is neutral. Wait for it to break above 60 (bullish) or below 40 (bearish)")
        wait.append("Wait for EMA 9/21 crossover for fresh trend signal")
        wait.append("Wait for volume spike (1.5x+ average) to confirm move")
        return wait

    def _avoid_conditions(self, indicators, market, dte) -> list[str]:
        """Conditions under which to NOT take this trade."""
        avoid = []
        if dte <= 1:
            avoid.append("Expiry day — theta will eat your premium")
        if market.get("regime") == "Choppy / Sideways":
            avoid.append("Market is choppy — trend signals fail in sideways markets")
        if market.get("volume") == "Low":
            avoid.append("No volume — the move may not sustain")

        checks = self._build_checklist(type('S', (), {'direction': 'BUY_CALL', 'score': 0})(), indicators, market)
        critical_fails = [c for c in checks if c["critical"] and not c["passed"]]
        if len(critical_fails) >= 2:
            avoid.append(f"{len(critical_fails)} critical checks failed — too many red flags")

        avoid.append("If you already have 3 open positions — max limit reached")
        avoid.append("If daily loss already > ₹2,000 — stop trading for today")
        return avoid

    def _next_weekly_expiry(self) -> str:
        """Get next Thursday (weekly expiry)."""
        today = date.today()
        days_ahead = 3 - today.weekday()  # Thursday = 3
        if days_ahead <= 0:
            days_ahead += 7
        next_thu = today + timedelta(days=days_ahead)
        return next_thu.isoformat()

    def _estimate_premium(self, spot: float, option_type: str, dte: int) -> float:
        """Rough premium estimate when no chain data."""
        atm_strike = round(spot / 50) * 50
        greeks = calculate_greeks(
            spot=spot, strike=atm_strike,
            expiry=dte / 365, option_type=option_type,
        )
        return max(greeks.get("theoretical_price", spot * 0.01), 5)

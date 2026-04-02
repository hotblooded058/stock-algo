"""
Market Context Module
Fetches and stores VIX, PCR, FII/DII data, and advance-decline ratio.
Provides the broader market picture for trading decisions.
"""

import sys
import os
import re
from datetime import datetime, date
from urllib.request import Request, urlopen
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.db.database import Database
from src.data.fetcher import fetch_vix


class MarketContext:
    """Gathers and stores broader market context for trading decisions."""

    def __init__(self, db: Database = None):
        self.db = db or Database()

    def fetch_all(self) -> dict:
        """Fetch all market context data and store in DB."""
        vix = self._fetch_vix()
        fii_dii = self._fetch_fii_dii()
        nifty = self._fetch_index_level("^NSEI")
        banknifty = self._fetch_index_level("^NSEBANK")

        context = {
            "date": date.today().isoformat(),
            "time": datetime.now().strftime("%H:%M"),
            "vix": vix,
            "pcr": None,  # Filled from options chain analysis
            "nifty_level": nifty,
            "banknifty_level": banknifty,
            "fii_net": fii_dii.get("fii_net") if fii_dii else None,
            "dii_net": fii_dii.get("dii_net") if fii_dii else None,
            "advance_decline_ratio": None,
        }

        # Save to DB
        self.db.save_market_context(context)

        # Add interpretations
        context["vix_mood"] = self._interpret_vix(vix)
        context["fii_dii_signal"] = self._interpret_fii_dii(fii_dii)
        context["market_regime"] = self._detect_regime(vix, nifty)

        return context

    def get_latest(self) -> dict:
        """Get the most recent market context from DB."""
        rows = self.db.get_market_context()
        if rows:
            ctx = rows[0]
            ctx["vix_mood"] = self._interpret_vix(ctx.get("vix"))
            ctx["market_regime"] = self._detect_regime(ctx.get("vix"), ctx.get("nifty_level"))
            return ctx
        return {}

    # ========================================================
    # DATA FETCHERS
    # ========================================================

    def _fetch_vix(self) -> float | None:
        """Get India VIX value."""
        try:
            vix_df = fetch_vix()
            if not vix_df.empty:
                return round(float(vix_df["Close"].iloc[-1]), 2)
        except Exception as e:
            print(f"VIX fetch error: {e}")
        return None

    def _fetch_index_level(self, symbol: str) -> float | None:
        """Get current level of an index."""
        try:
            from src.data.fetcher import fetch_stock_data
            df = fetch_stock_data(symbol, period="5d", interval="1d")
            if not df.empty:
                return round(float(df["Close"].iloc[-1]), 2)
        except Exception as e:
            print(f"Index fetch error for {symbol}: {e}")
        return None

    def _fetch_fii_dii(self) -> dict | None:
        """
        Fetch FII/DII activity data.
        Tries multiple sources for reliability.
        """
        # Source 1: MoneyControl
        try:
            url = "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/home.php"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            }
            req = Request(url, headers=headers)
            resp = urlopen(req, timeout=10)
            html = resp.read().decode("utf-8", errors="ignore")

            # Try to extract FII and DII net values
            fii_match = re.search(r'FII/FPI.*?Net.*?([+-]?\d[\d,.]+)', html, re.DOTALL | re.IGNORECASE)
            dii_match = re.search(r'DII.*?Net.*?([+-]?\d[\d,.]+)', html, re.DOTALL | re.IGNORECASE)

            if fii_match or dii_match:
                fii_net = float(fii_match.group(1).replace(",", "")) if fii_match else None
                dii_net = float(dii_match.group(1).replace(",", "")) if dii_match else None
                return {"fii_net": fii_net, "dii_net": dii_net}

        except Exception as e:
            print(f"FII/DII fetch error: {e}")

        return None

    # ========================================================
    # INTERPRETATIONS
    # ========================================================

    def _interpret_vix(self, vix: float | None) -> dict:
        """Interpret VIX level for trading decisions."""
        if vix is None:
            return {"level": "Unknown", "action": "Check manually"}

        if vix > 25:
            return {
                "level": "Very High",
                "action": "Options expensive. Reduce position sizes. Consider selling instead of buying.",
                "impact_on_buying": "Negative — high premium, fast theta decay",
                "impact_on_selling": "Positive — collect high premiums",
            }
        elif vix > 20:
            return {
                "level": "Elevated",
                "action": "Use wider stop losses. Reduce quantity slightly.",
                "impact_on_buying": "Moderate — premiums above average",
                "impact_on_selling": "Good — decent premiums to collect",
            }
        elif vix > 15:
            return {
                "level": "Normal",
                "action": "Standard trading. Good for option buying.",
                "impact_on_buying": "Favorable — reasonable premiums",
                "impact_on_selling": "Average — moderate premiums",
            }
        else:
            return {
                "level": "Low",
                "action": "Options are cheap. Good for buying. Avoid selling — low premium collected.",
                "impact_on_buying": "Very favorable — cheap options",
                "impact_on_selling": "Poor — low premiums",
            }

    def _interpret_fii_dii(self, data: dict | None) -> dict:
        """Interpret FII/DII activity."""
        if not data:
            return {"signal": "Unknown"}

        fii = data.get("fii_net")
        dii = data.get("dii_net")

        if fii is None:
            return {"signal": "No data"}

        signals = []
        if fii and fii > 500:
            signals.append("FII buying heavily — Bullish institutional flow")
        elif fii and fii < -500:
            signals.append("FII selling heavily — Bearish institutional flow")

        if dii and dii > 500:
            signals.append("DII buying — Domestic support")
        elif dii and dii < -500:
            signals.append("DII selling — Unusual domestic selling")

        overall = "Neutral"
        if fii and fii > 0 and dii and dii > 0:
            overall = "Bullish — Both FII and DII buying"
        elif fii and fii < 0 and dii and dii < 0:
            overall = "Bearish — Both FII and DII selling"
        elif fii and fii > 0:
            overall = "Mildly Bullish — FII buying"
        elif fii and fii < -500:
            overall = "Bearish — FII selling"

        return {
            "signal": overall,
            "details": signals,
            "fii_net_crores": fii,
            "dii_net_crores": dii,
        }

    def _detect_regime(self, vix: float | None, nifty: float | None) -> dict:
        """
        Detect current market regime.
        Helps decide between buying and selling strategies.
        """
        if vix is None:
            return {"regime": "Unknown"}

        if vix > 25:
            return {
                "regime": "High Volatility",
                "strategy_bias": "Sell options / Iron condors / Strangles",
                "avoid": "Naked option buying with large size",
            }
        elif vix > 18:
            return {
                "regime": "Normal Trending",
                "strategy_bias": "Directional option buying / Debit spreads",
                "avoid": "Very short expiry options",
            }
        elif vix < 13:
            return {
                "regime": "Low Volatility",
                "strategy_bias": "Buy options (cheap). Expect volatility expansion.",
                "avoid": "Option selling — premiums too low",
            }
        else:
            return {
                "regime": "Normal Range-bound",
                "strategy_bias": "ATM option buying / Bull/Bear spreads",
                "avoid": "Deep OTM options",
            }

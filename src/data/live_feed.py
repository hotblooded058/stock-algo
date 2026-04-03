"""
Live Data Feed via AngelOne
Fetches real-time LTP, OHLC, and change% for multiple stocks at once.
Much faster than Yahoo Finance — can do 171 stocks in ~20 seconds.
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from SmartApi import SmartConnect
    import pyotp
    SMARTAPI_AVAILABLE = True
except ImportError:
    SMARTAPI_AVAILABLE = False


# In-memory cache
_session = None
_session_time = None
_instrument_map = None  # {NSE_SYMBOL: token}


def _get_session():
    """Get or create AngelOne session. Reuses session for 30 min."""
    global _session, _session_time

    if _session and _session_time and (datetime.now() - _session_time).seconds < 1800:
        return _session

    if not SMARTAPI_AVAILABLE:
        return None

    try:
        from config.secrets import (
            ANGELONE_API_KEY, ANGELONE_CLIENT_ID,
            ANGELONE_PASSWORD, ANGELONE_TOTP_SECRET
        )
        if not all([ANGELONE_API_KEY, ANGELONE_CLIENT_ID, ANGELONE_PASSWORD, ANGELONE_TOTP_SECRET]):
            return None

        obj = SmartConnect(api_key=ANGELONE_API_KEY)
        totp = pyotp.TOTP(ANGELONE_TOTP_SECRET).now()
        data = obj.generateSession(ANGELONE_CLIENT_ID, ANGELONE_PASSWORD, totp)

        if data and data.get("status"):
            _session = obj
            _session_time = datetime.now()
            return obj
    except Exception as e:
        print(f"AngelOne session error: {e}")

    return None


def _load_instrument_map():
    """Load NSE symbol -> token mapping from AngelOne master file."""
    global _instrument_map

    if _instrument_map:
        return _instrument_map

    try:
        import urllib.request
        import json

        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())

        _instrument_map = {}
        for inst in data:
            if inst.get("exch_seg") == "NSE" and inst.get("symbol", "").endswith("-EQ"):
                name = inst.get("name", "")
                _instrument_map[name] = inst.get("token", "")

        # Add indices
        _instrument_map["NIFTY"] = "99926000"
        _instrument_map["BANKNIFTY"] = "99926009"
        _instrument_map["FINNIFTY"] = "99926037"

        print(f"Loaded {len(_instrument_map)} instrument tokens")
        return _instrument_map

    except Exception as e:
        print(f"Instrument map load error: {e}")
        return {}


def get_live_quotes(symbols: list[str]) -> dict:
    """
    Fetch live LTP for multiple NSE symbols using AngelOne.
    Returns: {symbol: {"ltp": price, "open": o, "high": h, "low": l, "close": c, "change_pct": pct}}

    Much faster than Yahoo — ~0.1 sec per stock.
    """
    session = _get_session()
    if not session:
        return {}

    token_map = _load_instrument_map()
    if not token_map:
        return {}

    quotes = {}
    for sym in symbols:
        token = token_map.get(sym)
        if not token:
            continue

        try:
            # Determine exchange
            exchange = "NSE"

            data = session.ltpData(exchange, sym + "-EQ" if sym not in ("NIFTY", "BANKNIFTY", "FINNIFTY") else sym, token)
            if data and data.get("data"):
                d = data["data"]
                ltp = d.get("ltp", 0)
                open_price = d.get("open", ltp)
                close_price = d.get("close", ltp)
                change_pct = ((ltp - close_price) / close_price * 100) if close_price > 0 else 0

                quotes[sym] = {
                    "ltp": ltp,
                    "open": open_price,
                    "high": d.get("high", ltp),
                    "low": d.get("low", ltp),
                    "close": close_price,
                    "change_pct": round(change_pct, 2),
                }

            # Small delay to respect rate limits
            time.sleep(0.05)

        except Exception as e:
            continue

    return quotes


def get_live_ltp(symbol: str) -> float | None:
    """Get single stock LTP."""
    quotes = get_live_quotes([symbol])
    if symbol in quotes:
        return quotes[symbol]["ltp"]
    return None

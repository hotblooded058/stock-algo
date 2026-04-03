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


def get_historical_candles(symbol: str, token: str = None, days: int = 90,
                           interval: str = "ONE_DAY") -> list[dict]:
    """
    Fetch historical candles from AngelOne.
    Returns list of {timestamp, open, high, low, close, volume}.
    """
    session = _get_session()
    if not session:
        return []

    if not token:
        token_map = _load_instrument_map()
        token = token_map.get(symbol)
    if not token:
        return []

    try:
        from datetime import timedelta
        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": interval,
            "fromdate": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d 09:15"),
            "todate": datetime.now().strftime("%Y-%m-%d 15:30"),
        }
        data = session.getCandleData(params)
        if data and data.get("data"):
            return [
                {
                    "timestamp": c[0],
                    "open": c[1],
                    "high": c[2],
                    "low": c[3],
                    "close": c[4],
                    "volume": c[5],
                }
                for c in data["data"]
            ]
    except Exception as e:
        print(f"AngelOne historical error for {symbol}: {e}")

    return []


def get_fresh_dataframe(symbol: str, token: str = None, days: int = 90):
    """
    Get a pandas DataFrame with fresh data from AngelOne.
    Includes today's live candle if market is open.
    Falls back to Yahoo Finance if AngelOne fails.

    This is the KEY function — gives indicators based on LIVE data,
    not yesterday's stale Yahoo data.
    """
    import pandas as pd

    candles = get_historical_candles(symbol, token, days)

    if candles:
        # Convert AngelOne candles to DataFrame
        df = pd.DataFrame(candles)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")
        df.columns = ["Open", "High", "Low", "Close", "Volume"]
        df.index.name = "Datetime"

        # Append live quote as today's candle if market is open
        quotes = get_live_quotes([symbol])
        if symbol in quotes:
            q = quotes[symbol]
            today = pd.Timestamp(datetime.now().date())
            if today not in df.index:
                live_row = pd.DataFrame({
                    "Open": [q["open"]],
                    "High": [q["high"]],
                    "Low": [q["low"]],
                    "Close": [q["ltp"]],
                    "Volume": [0],
                }, index=pd.DatetimeIndex([today], name="Datetime"))
                df = pd.concat([df, live_row])

        return df

    # Fallback to Yahoo
    from src.data.fetcher import fetch_stock_data
    from src.data.fno_stocks import FNO_STOCKS
    info = FNO_STOCKS.get(symbol, {})
    yahoo = info.get("yahoo", f"{symbol}.NS")
    df = fetch_stock_data(yahoo, period="3mo", interval="1d")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df

"""
Market Data Fetcher
Fetches OHLCV data from Yahoo Finance with NSE fallback for Indian markets.
"""

import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import WATCHLIST, DEFAULT_PERIOD, DEFAULT_INTERVAL, DAILY_INTERVAL


# ============================================================
# NSE DIRECT FETCH (Backup when Yahoo is delayed)
# ============================================================

# Map Yahoo symbols to NSE symbols
_NSE_SYMBOL_MAP = {
    "^NSEI": "NIFTY 50",
    "^NSEBANK": "NIFTY BANK",
    "^INDIAVIX": "INDIA VIX",
    "RELIANCE.NS": "RELIANCE",
    "TCS.NS": "TCS",
    "HDFCBANK.NS": "HDFCBANK",
    "INFY.NS": "INFY",
    "ICICIBANK.NS": "ICICIBANK",
    "SBIN.NS": "SBIN",
    "BHARTIARTL.NS": "BHARTIARTL",
    "ITC.NS": "ITC",
}


def _fetch_nse_quote(symbol: str) -> dict | None:
    """
    Fetch latest quote directly from NSE India website.
    Returns dict with Open, High, Low, Close, Volume or None on failure.
    """
    nse_symbol = _NSE_SYMBOL_MAP.get(symbol)
    if not nse_symbol:
        return None

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/",
        }

        # First hit NSE homepage to get cookies
        req = Request("https://www.nseindia.com/", headers=headers)
        resp = urlopen(req, timeout=5)
        cookies = resp.headers.get("Set-Cookie", "")

        # Determine endpoint based on symbol type
        if nse_symbol in ("NIFTY 50", "NIFTY BANK", "INDIA VIX"):
            url = f"https://www.nseindia.com/api/equity-stockIndices?index={nse_symbol.replace(' ', '%20')}"
        else:
            url = f"https://www.nseindia.com/api/quote-equity?symbol={nse_symbol}"

        headers["Cookie"] = cookies
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())

        # Parse based on type
        if nse_symbol in ("NIFTY 50", "NIFTY BANK"):
            info = data.get("metadata", {})
            return {
                "open": float(info.get("open", 0)),
                "high": float(info.get("high", 0)),
                "low": float(info.get("low", 0)),
                "close": float(info.get("last", info.get("previousClose", 0))),
                "prev_close": float(info.get("previousClose", 0)),
                "volume": 0,  # Index doesn't have volume in this API
            }
        elif nse_symbol == "INDIA VIX":
            info = data.get("metadata", {})
            return {
                "close": float(info.get("last", info.get("previousClose", 0))),
                "prev_close": float(info.get("previousClose", 0)),
            }
        else:
            info = data.get("priceInfo", {})
            return {
                "open": float(info.get("open", 0)),
                "high": float(info.get("intraDayHighLow", {}).get("max", 0)),
                "low": float(info.get("intraDayHighLow", {}).get("min", 0)),
                "close": float(info.get("lastPrice", info.get("previousClose", 0))),
                "prev_close": float(info.get("previousClose", 0)),
                "volume": int(data.get("securityWiseDP", {}).get("quantityTraded", 0)),
            }

    except Exception as e:
        print(f"   NSE fallback failed for {symbol}: {e}")
        return None


# ============================================================
# PRIMARY FETCH (Yahoo Finance)
# ============================================================

def fetch_stock_data(symbol: str, period: str = DEFAULT_PERIOD,
                     interval: str = DEFAULT_INTERVAL) -> pd.DataFrame:
    """
    Fetch OHLCV data for a single stock/index.
    Uses Yahoo Finance as primary source.
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            print(f"⚠️  No data found for {symbol}")
            return pd.DataFrame()

        # Clean up columns
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.index.name = 'Datetime'

        # Check if data is stale (more than 1 trading day old)
        last_date = df.index[-1].date() if hasattr(df.index[-1], 'date') else df.index[-1]
        today = datetime.now().date()
        days_old = (today - last_date).days if hasattr(last_date, 'day') else 0

        if days_old > 1 and interval == "1d":
            print(f"⚠️  Yahoo data for {symbol} is {days_old} days old. Trying NSE for latest price...")
            nse_quote = _fetch_nse_quote(symbol)
            if nse_quote and nse_quote.get("close", 0) > 0:
                # Append today's data from NSE as a new row
                new_row = pd.DataFrame({
                    'Open': [nse_quote.get('open', nse_quote['close'])],
                    'High': [nse_quote.get('high', nse_quote['close'])],
                    'Low': [nse_quote.get('low', nse_quote['close'])],
                    'Close': [nse_quote['close']],
                    'Volume': [nse_quote.get('volume', 0)],
                }, index=pd.DatetimeIndex([pd.Timestamp(today)], name='Datetime'))

                df = pd.concat([df, new_row])
                print(f"   ✅ Patched with NSE live price: ₹{nse_quote['close']:,.2f}")

        print(f"✅ Fetched {len(df)} candles for {symbol} ({interval})")
        return df

    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return pd.DataFrame()


def fetch_watchlist_data(symbols: list = None, period: str = DEFAULT_PERIOD,
                         interval: str = DEFAULT_INTERVAL) -> dict:
    """Fetch data for all stocks in the watchlist."""
    if symbols is None:
        symbols = WATCHLIST

    data = {}
    for symbol in symbols:
        df = fetch_stock_data(symbol, period, interval)
        if not df.empty:
            data[symbol] = df

    print(f"\n📊 Fetched data for {len(data)}/{len(symbols)} symbols")
    return data


def fetch_vix() -> pd.DataFrame:
    """Fetch India VIX data."""
    return fetch_stock_data("^INDIAVIX", period="3mo", interval="1d")


def fetch_nifty_daily() -> pd.DataFrame:
    """Fetch Nifty 50 daily data for trend analysis."""
    return fetch_stock_data("^NSEI", period="1y", interval=DAILY_INTERVAL)


# ---- Quick Test ----
if __name__ == "__main__":
    print("=" * 50)
    print("Testing Data Fetcher")
    print("=" * 50)

    # Test single stock
    df = fetch_stock_data("^NSEI", period="1mo", interval="1d")
    if not df.empty:
        print(f"\nNifty 50 — Last 5 candles:")
        print(df.tail())

    # Test VIX
    vix = fetch_vix()
    if not vix.empty:
        print(f"\nIndia VIX — Current: {vix['Close'].iloc[-1]:.2f}")

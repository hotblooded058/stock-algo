"""
Market Data Fetcher
Fetches OHLCV data with multiple fallback sources to ensure fresh data.
Priority: yf.download() → yf.Ticker.history() → Google Finance scrape
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
# PERIOD TO DATES HELPER
# ============================================================

def _period_to_dates(period: str):
    """Convert period string like '3mo' to (start_date, end_date)."""
    end = datetime.now()
    mappings = {
        '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180, '1y': 365, '2y': 730
    }
    days = mappings.get(period, 90)
    start = end - timedelta(days=days)
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')


# ============================================================
# NSE DIRECT FETCH (Backup for local machine)
# ============================================================

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
    """Fetch latest quote directly from NSE India website."""
    nse_symbol = _NSE_SYMBOL_MAP.get(symbol)
    if not nse_symbol:
        return None

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/",
        }

        req = Request("https://www.nseindia.com/", headers=headers)
        resp = urlopen(req, timeout=5)
        cookies = resp.headers.get("Set-Cookie", "")

        if nse_symbol in ("NIFTY 50", "NIFTY BANK", "INDIA VIX"):
            url = f"https://www.nseindia.com/api/equity-stockIndices?index={nse_symbol.replace(' ', '%20')}"
        else:
            url = f"https://www.nseindia.com/api/quote-equity?symbol={nse_symbol}"

        headers["Cookie"] = cookies
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())

        if nse_symbol in ("NIFTY 50", "NIFTY BANK"):
            info = data.get("metadata", {})
            return {
                "open": float(info.get("open", 0)),
                "high": float(info.get("high", 0)),
                "low": float(info.get("low", 0)),
                "close": float(info.get("last", info.get("previousClose", 0))),
                "prev_close": float(info.get("previousClose", 0)),
                "volume": 0,
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
# GOOGLE FINANCE FALLBACK (Works from cloud servers)
# ============================================================

# Map Yahoo symbols to Google Finance tickers
_GOOGLE_SYMBOL_MAP = {
    "^NSEI": "NIFTY_50:INDEXNSE",
    "^NSEBANK": "NIFTY_BANK:INDEXNSE",
    "^INDIAVIX": "INDIAVIX:INDEXNSE",
    "RELIANCE.NS": "RELIANCE:NSE",
    "TCS.NS": "TCS:NSE",
    "HDFCBANK.NS": "HDFCBANK:NSE",
    "INFY.NS": "INFY:NSE",
    "ICICIBANK.NS": "ICICIBANK:NSE",
    "SBIN.NS": "SBIN:NSE",
    "BHARTIARTL.NS": "BHARTIARTL:NSE",
    "ITC.NS": "ITC:NSE",
}


def _fetch_google_finance_quote(symbol: str) -> dict | None:
    """
    Scrape latest price from Google Finance.
    Works from cloud servers where NSE blocks requests.
    """
    google_symbol = _GOOGLE_SYMBOL_MAP.get(symbol)
    if not google_symbol:
        return None

    try:
        url = f"https://www.google.com/finance/quote/{google_symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=10)
        html = resp.read().decode('utf-8')

        # Extract price from the page using simple string parsing
        # Google Finance puts the price in a specific data attribute
        import re

        # Try to find price in the HTML — Google puts it after "data-last-price"
        price_match = re.search(r'data-last-price="([0-9,.]+)"', html)
        if price_match:
            price = float(price_match.group(1).replace(',', ''))
            print(f"   ✅ Google Finance price for {symbol}: ₹{price:,.2f}")
            return {"close": price}

        # Alternative pattern
        price_match = re.search(r'class="YMlKec fxKbKc"[^>]*>([0-9,]+\.?\d*)', html)
        if price_match:
            price = float(price_match.group(1).replace(',', ''))
            print(f"   ✅ Google Finance price for {symbol}: ₹{price:,.2f}")
            return {"close": price}

    except Exception as e:
        print(f"   Google Finance fallback failed for {symbol}: {e}")

    return None


# ============================================================
# PRIMARY FETCH
# ============================================================

def fetch_stock_data(symbol: str, period: str = DEFAULT_PERIOD,
                     interval: str = DEFAULT_INTERVAL) -> pd.DataFrame:
    """
    Fetch OHLCV data for a single stock/index.
    Uses yf.download() as primary (more reliable than Ticker.history).
    Falls back to NSE → Google Finance if data is stale.
    """
    df = pd.DataFrame()

    # --- Method 1: yf.download (most reliable) ---
    try:
        start_date, end_date = _period_to_dates(period)
        df = yf.download(
            symbol,
            start=start_date,
            end=end_date,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
        # yf.download can return MultiIndex columns for single ticker
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
    except Exception as e:
        print(f"   yf.download failed for {symbol}: {e}")

    # --- Method 2: yf.Ticker.history (fallback) ---
    if df.empty:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
        except Exception as e:
            print(f"   yf.Ticker.history also failed for {symbol}: {e}")

    if df.empty:
        print(f"⚠️  No data found for {symbol}")
        return pd.DataFrame()

    # Clean up columns — keep only what we need
    available_cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in df.columns]
    df = df[available_cols]
    df.index.name = 'Datetime'

    # --- Check freshness and patch if stale ---
    if interval in ("1d", "1D") and len(df) > 0:
        last_date = df.index[-1]
        if hasattr(last_date, 'date'):
            last_date = last_date.date()
        elif hasattr(last_date, 'to_pydatetime'):
            last_date = last_date.to_pydatetime().date()

        today = datetime.now().date()
        # Allow 1 day gap (weekends, holidays) but flag 2+ days
        days_old = (today - last_date).days

        if days_old > 1:
            print(f"⚠️  Data for {symbol} is {days_old} days old. Trying fallback sources...")

            # Try NSE first (works on local machine)
            quote = _fetch_nse_quote(symbol)

            # Try Google Finance (works on cloud)
            if not quote or quote.get("close", 0) == 0:
                quote = _fetch_google_finance_quote(symbol)

            if quote and quote.get("close", 0) > 0:
                new_row = pd.DataFrame({
                    'Open': [quote.get('open', quote['close'])],
                    'High': [quote.get('high', quote['close'])],
                    'Low': [quote.get('low', quote['close'])],
                    'Close': [quote['close']],
                    'Volume': [quote.get('volume', 0)],
                }, index=pd.DatetimeIndex([pd.Timestamp(today)], name='Datetime'))

                df = pd.concat([df, new_row])
                print(f"   ✅ Patched with live price: ₹{quote['close']:,.2f}")
            else:
                print(f"   ⚠️  All fallback sources failed. Using stale Yahoo data.")

    print(f"✅ Fetched {len(df)} candles for {symbol} ({interval})")
    return df


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

    df = fetch_stock_data("^NSEI", period="1mo", interval="1d")
    if not df.empty:
        print(f"\nNifty 50 — Last 5 candles:")
        print(df.tail())

    vix = fetch_vix()
    if not vix.empty:
        print(f"\nIndia VIX — Current: {vix['Close'].iloc[-1]:.2f}")

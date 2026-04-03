"""
Market Data API Routes
"""

from fastapi import APIRouter, Query
from src.data.fetcher import fetch_stock_data, fetch_vix
from src.indicators.technical import add_all_indicators, get_latest_indicators
from src.db.database import Database
from config.settings import WATCHLIST_MAP, SYMBOL_NAMES

router = APIRouter()
db = Database()


@router.get("/watchlist")
def get_watchlist():
    """Get all watchlist symbols with display names."""
    return [
        {"symbol": symbol, "name": name}
        for name, symbol in WATCHLIST_MAP.items()
    ]


@router.get("/candles")
def get_candles(
    symbol: str = Query(..., description="Stock symbol (e.g. ^NSEI, RELIANCE.NS)"),
    period: str = Query("3mo", description="Data period"),
    interval: str = Query("1d", description="Candle interval"),
):
    """Fetch OHLCV candle data for a symbol."""
    df = fetch_stock_data(symbol, period=period, interval=interval)
    if df.empty:
        return {"symbol": symbol, "candles": [], "error": "No data found"}

    df = add_all_indicators(df)

    candles = []
    for idx, row in df.iterrows():
        candle = {
            "timestamp": idx.isoformat(),
            "open": round(row["Open"], 2),
            "high": round(row["High"], 2),
            "low": round(row["Low"], 2),
            "close": round(row["Close"], 2),
            "volume": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
        }
        # Add indicators if available
        for col in ["EMA_9", "EMA_21", "EMA_50", "EMA_200", "RSI", "MACD",
                     "MACD_signal", "MACD_histogram", "BB_upper", "BB_lower",
                     "BB_middle", "SuperTrend", "SuperTrend_dir", "ATR", "Vol_MA_20"]:
            if col in df.columns:
                val = row[col]
                candle[col.lower()] = round(float(val), 4) if val == val else None
        candles.append(candle)

    return {
        "symbol": symbol,
        "name": SYMBOL_NAMES.get(symbol, symbol),
        "interval": interval,
        "count": len(candles),
        "candles": candles,
    }


@router.get("/indicators")
def get_indicators(
    symbol: str = Query(...),
    period: str = Query("3mo"),
    interval: str = Query("1d"),
):
    """Get latest indicator values for a symbol."""
    df = fetch_stock_data(symbol, period=period, interval=interval)
    if df.empty:
        return {"error": "No data found"}

    df = add_all_indicators(df)
    indicators = get_latest_indicators(df)

    # Convert numpy types to native Python
    clean = {}
    for k, v in indicators.items():
        if v is None:
            clean[k] = None
        elif isinstance(v, bool):
            clean[k] = v
        elif isinstance(v, (int, float)):
            clean[k] = round(float(v), 4)
        else:
            clean[k] = v

    return {
        "symbol": symbol,
        "name": SYMBOL_NAMES.get(symbol, symbol),
        "indicators": clean,
    }


@router.get("/vix")
def get_vix():
    """Get current India VIX value."""
    vix_df = fetch_vix()
    if vix_df.empty:
        return {"vix": None, "error": "Could not fetch VIX"}

    current = float(vix_df["Close"].iloc[-1])
    prev = float(vix_df["Close"].iloc[-2]) if len(vix_df) > 1 else current
    change = current - prev

    if current > 25:
        mood = "Very High - Options expensive, be cautious"
    elif current > 20:
        mood = "Elevated - Wider stop losses recommended"
    elif current < 13:
        mood = "Low - Consider option selling strategies"
    else:
        mood = "Normal - Good for option buying"

    return {
        "vix": round(current, 2),
        "change": round(change, 2),
        "mood": mood,
        "timestamp": vix_df.index[-1].isoformat(),
    }


@router.get("/scan")
def scan_watchlist():
    """Scan all watchlist stocks and return signals sorted by score."""
    from src.signals.generator import generate_all_signals

    # Get VIX for consistent signal scoring
    vix_val = None
    try:
        vix_df = fetch_vix()
        if not vix_df.empty:
            vix_val = float(vix_df["Close"].iloc[-1])
    except Exception:
        pass

    results = []
    for name, symbol in WATCHLIST_MAP.items():
        try:
            df = fetch_stock_data(symbol, period="3mo", interval="1d")
            if df.empty:
                continue
            df = add_all_indicators(df)
            indicators = get_latest_indicators(df)
            sigs = generate_all_signals(symbol, indicators, vix=vix_val)

            price = float(df["Close"].iloc[-1])
            prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else price
            pct_change = ((price - prev_close) / prev_close) * 100

            for sig in sigs:
                results.append({
                    "symbol": symbol,
                    "name": name,
                    "price": round(price, 2),
                    "change_pct": round(pct_change, 2),
                    "direction": sig.direction,
                    "score": sig.score,
                    "strength": sig.strength,
                    "strategy": sig.strategy,
                    "reasons": sig.reasons,
                })
        except Exception as e:
            print(f"Scan error for {symbol}: {e}")
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"signals": results, "count": len(results), "vix": vix_val}

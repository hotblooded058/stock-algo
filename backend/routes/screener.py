"""
F&O Stock Screener API — Powered by AngelOne Live Data
Scans F&O stocks with real-time prices and caches results for fast refresh.
"""

from fastapi import APIRouter, Query
from datetime import datetime
import threading
import pandas as pd

from src.data.fno_stocks import FNO_STOCKS, get_sectors
from src.data.live_feed import get_live_quotes, get_fresh_dataframe
from src.data.fetcher import fetch_stock_data
from src.indicators.technical import add_all_indicators, get_latest_indicators
from src.signals.generator import generate_all_signals


def _fix_df(df):
    """Fix MultiIndex columns from yfinance."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

from src.signals.trade_plan import TradePlanGenerator

router = APIRouter()
plan_generator = TradePlanGenerator()

# In-memory caches
_scan_cache = {
    "results": [],
    "last_updated": None,
    "sector": None,
    "scanning": False,
}

# User's watchlist — persisted in memory, editable via API
_watchlist: list[str] = [
    "SBIN", "RELIANCE", "HDFCBANK", "ICICIBANK", "TCS",
    "INFY", "BAJFINANCE", "ITC", "BHARTIARTL", "HCLTECH",
]


@router.get("/stocks")
def list_fno_stocks(sector: str = Query(None)):
    """List all F&O stocks with sector and lot size."""
    stocks = []
    for sym, info in FNO_STOCKS.items():
        if sector and info["sector"] != sector:
            continue
        stocks.append({
            "symbol": sym,
            "yahoo": info["yahoo"],
            "lot_size": info["lot"],
            "sector": info["sector"],
        })
    return {"stocks": stocks, "count": len(stocks)}


@router.get("/sectors")
def list_sectors():
    """List all sectors with stock counts."""
    sectors = {}
    for info in FNO_STOCKS.values():
        s = info["sector"]
        sectors[s] = sectors.get(s, 0) + 1
    return {"sectors": [{"name": k, "count": v} for k, v in sorted(sectors.items())]}


@router.get("/scan")
def scan_stocks(
    sector: str = Query(None, description="Filter by sector"),
    min_score: int = Query(50, description="Minimum signal score to show"),
    limit: int = Query(100, description="Max results"),
    use_cache: bool = Query(True, description="Use cached results if available"),
):
    """
    Scan F&O stocks for trading signals.
    Uses AngelOne for live prices, falls back to Yahoo Finance.
    Results are cached — subsequent calls return instantly.
    """
    # Return cache if available and same sector
    if use_cache and _scan_cache["results"] and _scan_cache["sector"] == sector and _scan_cache["last_updated"]:
        age = (datetime.now() - _scan_cache["last_updated"]).seconds
        cached = _scan_cache["results"]
        filtered = [r for r in cached if r["score"] >= min_score][:limit]
        return {
            "signals": filtered,
            "count": len(filtered),
            "scanned": len(cached),
            "errors": 0,
            "cached": True,
            "age_seconds": age,
            "last_updated": _scan_cache["last_updated"].isoformat(),
            "source": "cache",
        }

    # Build target list
    targets = []
    if sector:
        for sym, info in FNO_STOCKS.items():
            if info["sector"] == sector:
                targets.append((sym, info))
    else:
        targets = list(FNO_STOCKS.items())

    # Try AngelOne for live prices first
    symbols_to_fetch = [sym for sym, _ in targets if sym not in ("NIFTY", "BANKNIFTY", "FINNIFTY")]
    live_quotes = get_live_quotes(symbols_to_fetch[:50])  # Limit to 50 for speed
    source = "angelone" if live_quotes else "yahoo"

    results = []
    scanned = 0
    errors = 0

    for sym, info in targets:
        try:
            # Get historical data for indicators (need 50+ candles)
            df = _fix_df(fetch_stock_data(info["yahoo"], period="3mo", interval="1d"))
            if df.empty or len(df) < 30:
                errors += 1
                continue

            df = add_all_indicators(df)
            indicators = get_latest_indicators(df)

            # Override price with live AngelOne data if available
            if sym in live_quotes:
                lq = live_quotes[sym]
                price = lq["ltp"]
                change_pct = lq["change_pct"]
            else:
                price = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-2]) if len(df) > 1 else price
                change_pct = ((price - prev) / prev) * 100

            signals = generate_all_signals(info["yahoo"], indicators)
            scanned += 1

            rsi = indicators.get("rsi")
            adx = indicators.get("adx")
            above_vwap = indicators.get("above_vwap")
            supertrend = indicators.get("supertrend_bullish")
            volume_ratio = indicators.get("volume_ratio")

            # Always add the stock (even without signals) so we show all stocks
            if signals:
                for sig in signals:
                    results.append({
                        "symbol": sym,
                        "yahoo": info["yahoo"],
                        "sector": info["sector"],
                        "lot_size": info["lot"],
                        "price": round(price, 2),
                        "change_pct": round(change_pct, 2),
                        "direction": sig.direction,
                        "score": sig.score,
                        "strength": sig.strength,
                        "strategy": sig.strategy,
                        "reasons": sig.reasons,
                        "rsi": round(rsi, 1) if rsi else None,
                        "adx": round(adx, 1) if adx else None,
                        "above_vwap": above_vwap,
                        "supertrend": "Bullish" if supertrend else "Bearish" if supertrend is False else None,
                        "volume_ratio": round(volume_ratio, 2) if volume_ratio else None,
                        "live": sym in live_quotes,
                    })
            else:
                # No signal but still show stock data
                results.append({
                    "symbol": sym,
                    "yahoo": info["yahoo"],
                    "sector": info["sector"],
                    "lot_size": info["lot"],
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 2),
                    "direction": "NONE",
                    "score": 0,
                    "strength": "NO_SIGNAL",
                    "strategy": "-",
                    "reasons": [],
                    "rsi": round(rsi, 1) if rsi else None,
                    "adx": round(adx, 1) if adx else None,
                    "above_vwap": above_vwap,
                    "supertrend": "Bullish" if supertrend else "Bearish" if supertrend is False else None,
                    "volume_ratio": round(volume_ratio, 2) if volume_ratio else None,
                    "live": sym in live_quotes,
                })

        except Exception:
            errors += 1
            continue

    results.sort(key=lambda x: x["score"], reverse=True)

    # Cache the results
    _scan_cache["results"] = results
    _scan_cache["last_updated"] = datetime.now()
    _scan_cache["sector"] = sector

    filtered = [r for r in results if r["score"] >= min_score][:limit]

    return {
        "signals": filtered,
        "count": len(filtered),
        "scanned": scanned,
        "errors": errors,
        "total_fno_stocks": len(targets),
        "cached": False,
        "source": source,
        "last_updated": _scan_cache["last_updated"].isoformat(),
    }


@router.get("/prices")
def live_prices(sector: str = Query(None)):
    """
    Get ONLY live prices for stocks (fast — no indicators).
    For quick price refresh between full scans.
    """
    targets = []
    if sector:
        for sym, info in FNO_STOCKS.items():
            if info["sector"] == sector:
                targets.append(sym)
    else:
        targets = [sym for sym in FNO_STOCKS.keys() if sym not in ("NIFTY", "BANKNIFTY", "FINNIFTY")]

    # Limit to 50 for speed
    quotes = get_live_quotes(targets[:50])

    prices = []
    for sym in targets[:50]:
        if sym in quotes:
            q = quotes[sym]
            prices.append({
                "symbol": sym,
                "price": q["ltp"],
                "change_pct": q["change_pct"],
                "high": q["high"],
                "low": q["low"],
            })

    return {
        "prices": prices,
        "count": len(prices),
        "source": "angelone",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/cache")
def get_cache_status():
    """Check cache status."""
    return {
        "has_cache": bool(_scan_cache["results"]),
        "count": len(_scan_cache["results"]),
        "sector": _scan_cache["sector"],
        "last_updated": _scan_cache["last_updated"].isoformat() if _scan_cache["last_updated"] else None,
        "age_seconds": (datetime.now() - _scan_cache["last_updated"]).seconds if _scan_cache["last_updated"] else None,
    }


@router.delete("/cache")
def clear_cache():
    """Clear scan cache to force fresh data."""
    _scan_cache["results"] = []
    _scan_cache["last_updated"] = None
    _scan_cache["sector"] = None
    return {"message": "Cache cleared"}


# ============================================================
# WATCHLIST — User's selected stocks with fast 15-sec refresh
# ============================================================

@router.get("/trade-plan")
def get_trade_plan(symbol: str = Query(..., description="NSE symbol e.g. SBIN, RELIANCE")):
    """Generate complete trade plan for a stock."""
    return plan_generator.generate(symbol.upper())


@router.get("/watchlist")
def get_watchlist():
    """Get current watchlist symbols."""
    items = []
    for sym in _watchlist:
        info = FNO_STOCKS.get(sym, {})
        items.append({
            "symbol": sym,
            "sector": info.get("sector", "Other"),
            "lot_size": info.get("lot", 1),
        })
    return {"watchlist": items, "count": len(items)}


@router.post("/watchlist/add")
def add_to_watchlist(symbol: str = Query(...)):
    """Add a stock to watchlist."""
    sym = symbol.upper()
    if sym not in FNO_STOCKS:
        return {"error": f"{sym} not in F&O stock list"}
    if sym in _watchlist:
        return {"message": f"{sym} already in watchlist"}
    _watchlist.append(sym)
    return {"message": f"{sym} added", "watchlist": _watchlist}


@router.post("/watchlist/remove")
def remove_from_watchlist(symbol: str = Query(...)):
    """Remove a stock from watchlist."""
    sym = symbol.upper()
    if sym in _watchlist:
        _watchlist.remove(sym)
        return {"message": f"{sym} removed", "watchlist": _watchlist}
    return {"error": f"{sym} not in watchlist"}


@router.get("/watchlist/scan")
def scan_watchlist():
    """
    Fast scan of watchlist stocks only (10-15 stocks).
    Uses AngelOne live data. Designed for 15-second refresh.
    """
    live_quotes = get_live_quotes(_watchlist)
    source = "angelone" if live_quotes else "yahoo"

    results = []
    for sym in _watchlist:
        info = FNO_STOCKS.get(sym, {})
        yahoo = info.get("yahoo", f"{sym}.NS")

        try:
            # Use AngelOne for fresh data (indicators calculated on LIVE data)
            df = get_fresh_dataframe(sym)
            if df.empty or len(df) < 30:
                # Fallback to Yahoo
                df = _fix_df(fetch_stock_data(yahoo, period="3mo", interval="1d"))
            if df.empty or len(df) < 30:
                continue

            df = add_all_indicators(df)
            indicators = get_latest_indicators(df)

            # Live price from AngelOne
            if sym in live_quotes:
                price = live_quotes[sym]["ltp"]
                change_pct = live_quotes[sym]["change_pct"]
            else:
                price = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-2]) if len(df) > 1 else price
                change_pct = ((price - prev) / prev) * 100

            signals = generate_all_signals(yahoo, indicators)
            best_signal = signals[0] if signals else None

            rsi = indicators.get("rsi")
            adx = indicators.get("adx")

            results.append({
                "symbol": sym,
                "sector": info.get("sector", ""),
                "lot_size": info.get("lot", 1),
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "direction": best_signal.direction if best_signal else "NONE",
                "score": best_signal.score if best_signal else 0,
                "strength": best_signal.strength if best_signal else "NO_SIGNAL",
                "strategy": best_signal.strategy if best_signal else "-",
                "reasons": best_signal.reasons if best_signal else [],
                "rsi": round(rsi, 1) if rsi else None,
                "adx": round(adx, 1) if adx else None,
                "above_vwap": indicators.get("above_vwap"),
                "supertrend": "Bullish" if indicators.get("supertrend_bullish") else "Bearish" if indicators.get("supertrend_bullish") is False else None,
                "volume_ratio": round(indicators.get("volume_ratio", 0) or 0, 2) or None,
                "live": sym in live_quotes,
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "signals": results,
        "count": len(results),
        "source": source,
        "timestamp": datetime.now().isoformat(),
    }

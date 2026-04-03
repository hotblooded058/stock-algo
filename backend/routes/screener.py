"""
F&O Stock Screener API
Scans 200+ F&O eligible stocks and ranks by signal strength.
"""

from fastapi import APIRouter, Query
from src.data.fno_stocks import FNO_STOCKS, get_sectors, get_by_sector
from src.data.fetcher import fetch_stock_data
from src.indicators.technical import add_all_indicators, get_latest_indicators
from src.signals.generator import generate_all_signals

router = APIRouter()


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
    limit: int = Query(50, description="Max results"),
):
    """
    Scan F&O stocks for trading signals.
    Returns stocks with active signals sorted by score.
    Scans sector by sector for speed — pass sector param for faster results.
    """
    targets = []
    if sector:
        for sym, info in FNO_STOCKS.items():
            if info["sector"] == sector:
                targets.append((sym, info))
    else:
        targets = list(FNO_STOCKS.items())

    results = []
    scanned = 0
    errors = 0

    for sym, info in targets:
        try:
            df = fetch_stock_data(info["yahoo"], period="3mo", interval="1d")
            if df.empty or len(df) < 30:
                errors += 1
                continue

            df = add_all_indicators(df)
            indicators = get_latest_indicators(df)
            signals = generate_all_signals(info["yahoo"], indicators)

            scanned += 1

            price = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2]) if len(df) > 1 else price
            change_pct = ((price - prev) / prev) * 100

            # Get key indicators for display
            rsi = indicators.get("rsi")
            adx = indicators.get("adx")
            above_vwap = indicators.get("above_vwap")
            supertrend = indicators.get("supertrend_bullish")
            volume_ratio = indicators.get("volume_ratio")

            for sig in signals:
                if sig.score >= min_score:
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
                    })

        except Exception as e:
            errors += 1
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:limit]

    return {
        "signals": results,
        "count": len(results),
        "scanned": scanned,
        "errors": errors,
        "total_fno_stocks": len(targets),
    }


@router.get("/top-movers")
def top_movers(limit: int = Query(20)):
    """Get top gainers and losers from F&O stocks."""
    movers = []

    for sym, info in FNO_STOCKS.items():
        try:
            df = fetch_stock_data(info["yahoo"], period="5d", interval="1d")
            if df.empty or len(df) < 2:
                continue

            price = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            change_pct = ((price - prev) / prev) * 100

            movers.append({
                "symbol": sym,
                "sector": info["sector"],
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
            })
        except Exception:
            continue

    gainers = sorted(movers, key=lambda x: x["change_pct"], reverse=True)[:limit]
    losers = sorted(movers, key=lambda x: x["change_pct"])[:limit]

    return {"gainers": gainers, "losers": losers}

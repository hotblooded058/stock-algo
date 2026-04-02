"""
Signals API Routes
"""

from fastapi import APIRouter, Query
from src.data.fetcher import fetch_stock_data
from src.indicators.technical import add_all_indicators, get_latest_indicators
from src.signals.generator import generate_all_signals
from src.db.database import Database
from config.settings import SYMBOL_NAMES
from datetime import datetime

router = APIRouter()
db = Database()


@router.get("/generate")
def generate_signals(
    symbol: str = Query(...),
    period: str = Query("3mo"),
    interval: str = Query("1d"),
    save: bool = Query(True, description="Save signals to database"),
):
    """Generate trading signals for a symbol and optionally save to DB."""
    df = fetch_stock_data(symbol, period=period, interval=interval)
    if df.empty:
        return {"error": "No data found", "signals": []}

    df = add_all_indicators(df)
    indicators = get_latest_indicators(df)

    # Try to get options chain analytics for enhanced signals
    options_data = None
    try:
        from src.options.chain import OptionsChainAnalyzer
        oca = OptionsChainAnalyzer(db)
        # Map Yahoo symbols to underlying names
        underlying_map = {
            "^NSEI": "NIFTY", "^NSEBANK": "BANKNIFTY",
            "RELIANCE.NS": "RELIANCE", "TCS.NS": "TCS",
            "HDFCBANK.NS": "HDFCBANK", "INFY.NS": "INFY",
        }
        underlying = underlying_map.get(symbol)
        if underlying:
            analysis = oca.analyze(underlying, spot_price=indicators.get("close"))
            if "error" not in analysis:
                options_data = analysis
    except Exception:
        pass

    # Try to get VIX
    vix_val = None
    try:
        from src.data.fetcher import fetch_vix
        vix_df = fetch_vix()
        if not vix_df.empty:
            vix_val = float(vix_df["Close"].iloc[-1])
    except Exception:
        pass

    signals = generate_all_signals(symbol, indicators, options_data=options_data, vix=vix_val)

    result = []
    for sig in signals:
        sig_data = {
            "symbol": sig.symbol,
            "name": SYMBOL_NAMES.get(sig.symbol, sig.symbol),
            "direction": sig.direction,
            "score": sig.score,
            "strength": sig.strength,
            "strategy": sig.strategy,
            "reasons": sig.reasons,
        }

        if save:
            signal_id = db.save_signal({
                "symbol": sig.symbol,
                "direction": sig.direction,
                "score": sig.score,
                "strength": sig.strength,
                "strategy": sig.strategy,
                "reasons": sig.reasons,
                "indicators": indicators,
                "created_at": datetime.now().isoformat(),
            })
            sig_data["id"] = signal_id

        result.append(sig_data)

    return {"signals": result, "count": len(result)}


@router.get("/history")
def signal_history(
    symbol: str = Query(None),
    limit: int = Query(50),
):
    """Get historical signals from database."""
    signals = db.get_signals(symbol=symbol, limit=limit)
    return {"signals": signals, "count": len(signals)}


@router.get("/{signal_id}")
def get_signal(signal_id: int):
    """Get a specific signal by ID."""
    signal = db.get_signal(signal_id)
    if not signal:
        return {"error": "Signal not found"}
    return signal

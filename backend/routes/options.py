"""
Options Chain API Routes
"""

from fastapi import APIRouter, Query
from src.db.database import Database

router = APIRouter()
db = Database()


@router.get("/chain")
def get_options_chain(
    underlying: str = Query(..., description="e.g. NIFTY, BANKNIFTY, RELIANCE"),
    expiry: str = Query(None, description="Expiry date YYYY-MM-DD"),
):
    """
    Get options chain data.
    Returns latest snapshot from DB. Use /options/fetch to refresh from broker.
    """
    chain = db.get_options_chain(underlying, expiry)
    if not chain:
        return {
            "underlying": underlying,
            "chain": [],
            "message": "No options chain data. Connect AngelOne and fetch first.",
        }

    # Compute PCR and max pain from chain data
    calls = [c for c in chain if c["option_type"] == "CE"]
    puts = [c for c in chain if c["option_type"] == "PE"]

    total_call_oi = sum(c.get("oi", 0) or 0 for c in calls)
    total_put_oi = sum(p.get("oi", 0) or 0 for p in puts)
    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0

    # Max pain calculation
    max_pain = _calculate_max_pain(calls, puts)

    # OI-based support/resistance
    top_put_oi = max(puts, key=lambda p: p.get("oi", 0) or 0) if puts else None
    top_call_oi = max(calls, key=lambda c: c.get("oi", 0) or 0) if calls else None

    return {
        "underlying": underlying,
        "expiry": expiry,
        "chain": chain,
        "analytics": {
            "pcr": pcr,
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
            "max_pain": max_pain,
            "support": top_put_oi["strike"] if top_put_oi else None,
            "resistance": top_call_oi["strike"] if top_call_oi else None,
            "pcr_sentiment": "Bullish" if pcr > 1.0 else "Bearish" if pcr < 0.7 else "Neutral",
        },
        "count": len(chain),
    }


@router.get("/analytics")
def options_analytics(
    underlying: str = Query(...),
    expiry: str = Query(None),
):
    """Get computed options analytics: PCR, Max Pain, OI support/resistance."""
    chain = db.get_options_chain(underlying, expiry)
    if not chain:
        return {"error": "No chain data available"}

    calls = [c for c in chain if c["option_type"] == "CE"]
    puts = [c for c in chain if c["option_type"] == "PE"]

    total_call_oi = sum(c.get("oi", 0) or 0 for c in calls)
    total_put_oi = sum(p.get("oi", 0) or 0 for p in puts)
    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0

    # Top 5 OI strikes
    top_call_strikes = sorted(calls, key=lambda c: c.get("oi", 0) or 0, reverse=True)[:5]
    top_put_strikes = sorted(puts, key=lambda p: p.get("oi", 0) or 0, reverse=True)[:5]

    # IV analysis
    atm_calls = sorted(calls, key=lambda c: c.get("ltp", 0) or 0, reverse=True)[:3]
    avg_iv = sum(c.get("iv", 0) or 0 for c in atm_calls) / len(atm_calls) if atm_calls else 0

    return {
        "underlying": underlying,
        "pcr": pcr,
        "pcr_sentiment": "Bullish" if pcr > 1.0 else "Bearish" if pcr < 0.7 else "Neutral",
        "max_pain": _calculate_max_pain(calls, puts),
        "avg_iv": round(avg_iv, 2),
        "total_call_oi": total_call_oi,
        "total_put_oi": total_put_oi,
        "top_call_oi_strikes": [
            {"strike": c["strike"], "oi": c.get("oi", 0)} for c in top_call_strikes
        ],
        "top_put_oi_strikes": [
            {"strike": p["strike"], "oi": p.get("oi", 0)} for p in top_put_strikes
        ],
    }


def _calculate_max_pain(calls: list[dict], puts: list[dict]) -> float | None:
    """Calculate max pain strike — the price at which total option buyer loss is maximized."""
    if not calls or not puts:
        return None

    strikes = sorted(set(c["strike"] for c in calls) | set(p["strike"] for p in puts))
    call_oi_map = {c["strike"]: c.get("oi", 0) or 0 for c in calls}
    put_oi_map = {p["strike"]: p.get("oi", 0) or 0 for p in puts}

    min_pain = float("inf")
    max_pain_strike = None

    for settlement in strikes:
        total_pain = 0
        # Call buyer loss
        for strike, oi in call_oi_map.items():
            if settlement > strike:
                total_pain += (settlement - strike) * oi
        # Put buyer loss
        for strike, oi in put_oi_map.items():
            if settlement < strike:
                total_pain += (strike - settlement) * oi

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = settlement

    return max_pain_strike

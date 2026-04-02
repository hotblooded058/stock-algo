"""
Options Chain API Routes
Now powered by OptionsChainAnalyzer, Greeks calculator, and StrikeSelector.
"""

from fastapi import APIRouter, Query
from src.db.database import Database
from src.options.chain import OptionsChainAnalyzer
from src.options.greeks import calculate_greeks, time_to_expiry
from src.options.strike_selector import StrikeSelector

router = APIRouter()
db = Database()
analyzer = OptionsChainAnalyzer(db)
selector = StrikeSelector(db)


@router.get("/chain")
def get_options_chain(
    underlying: str = Query(..., description="e.g. NIFTY, BANKNIFTY, RELIANCE"),
    expiry: str = Query(None, description="Expiry date YYYY-MM-DD"),
    spot_price: float = Query(None, description="Current spot price for Greeks calculation"),
):
    """
    Get options chain with full analytics.
    Returns chain data + PCR, Max Pain, OI levels, IV skew, OI buildup, and summary.
    """
    result = analyzer.analyze(underlying, expiry, spot_price)

    if "error" in result:
        return result

    # Flatten for frontend
    chain_flat = []
    for c in result["chain"].get("calls", []):
        chain_flat.append(c)
    for p in result["chain"].get("puts", []):
        chain_flat.append(p)

    return {
        "underlying": underlying,
        "expiry": result.get("expiry"),
        "spot_price": spot_price,
        "chain": chain_flat,
        "analytics": {
            "pcr": result["pcr"],
            "max_pain": result["max_pain"],
            "oi_levels": result["oi_levels"],
            "iv_skew": result["iv_skew"],
            "oi_buildup": result["oi_buildup"],
            "summary": result["summary"],
        },
        "count": len(chain_flat),
    }


@router.get("/analytics")
def options_analytics(
    underlying: str = Query(...),
    expiry: str = Query(None),
    spot_price: float = Query(None),
):
    """Get full options analytics: PCR, Max Pain, OI levels, IV skew, buildup signals."""
    result = analyzer.analyze(underlying, expiry, spot_price)
    if "error" in result:
        return result

    return {
        "underlying": underlying,
        "pcr": result["pcr"],
        "max_pain": result["max_pain"],
        "oi_levels": result["oi_levels"],
        "iv_skew": result["iv_skew"],
        "oi_buildup": result["oi_buildup"],
        "summary": result["summary"],
    }


@router.get("/greeks")
def compute_greeks(
    spot: float = Query(..., description="Underlying spot price"),
    strike: float = Query(..., description="Option strike price"),
    expiry: str = Query(..., description="Expiry date YYYY-MM-DD"),
    option_type: str = Query("CE", description="CE or PE"),
    premium: float = Query(None, description="Market premium for IV calculation"),
):
    """Calculate Greeks for a single option."""
    greeks = calculate_greeks(
        spot=spot,
        strike=strike,
        expiry=expiry,
        option_type=option_type,
        market_price=premium,
    )
    return {
        "spot": spot,
        "strike": strike,
        "expiry": expiry,
        "option_type": option_type,
        "premium": premium,
        **greeks,
    }


@router.get("/recommend-strike")
def recommend_strike(
    underlying: str = Query(..., description="e.g. NIFTY, BANKNIFTY"),
    spot_price: float = Query(..., description="Current spot price"),
    direction: str = Query(..., description="BUY_CALL or BUY_PUT"),
    expiry: str = Query(None, description="Expiry YYYY-MM-DD (defaults to 7 days)"),
    risk_profile: str = Query("moderate", description="conservative, moderate, aggressive"),
):
    """
    Get strike recommendation based on Greeks, liquidity, IV, and risk profile.
    """
    if not expiry:
        from datetime import date, timedelta
        expiry = (date.today() + timedelta(days=7)).isoformat()

    # Try to use chain data from DB
    chain = db.get_options_chain(underlying, expiry)
    result = selector.recommend(
        underlying=underlying,
        spot_price=spot_price,
        direction=direction,
        expiry=expiry,
        chain=chain or None,
        risk_profile=risk_profile,
    )

    return result


@router.get("/market-context")
def get_market_context():
    """Get current market context: VIX, FII/DII, regime."""
    from src.data.market_context import MarketContext
    mc = MarketContext(db)
    return mc.get_latest() or {"message": "No market context data. Fetch first."}


@router.post("/fetch-context")
def fetch_market_context():
    """Fetch fresh market context data (VIX, FII/DII, etc.)."""
    from src.data.market_context import MarketContext
    mc = MarketContext(db)
    return mc.fetch_all()

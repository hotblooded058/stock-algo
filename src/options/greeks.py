"""
Black-Scholes Greeks Calculator
Computes option Greeks (Delta, Gamma, Theta, Vega) and Implied Volatility.

Nifty/BankNifty options are European-style, so Black-Scholes applies directly.
"""

import math
from scipy.stats import norm
from datetime import datetime, date


def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate d1 in Black-Scholes formula."""
    if T <= 0 or sigma <= 0:
        return 0.0
    return (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))


def _d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate d2 in Black-Scholes formula."""
    return _d1(S, K, T, r, sigma) - sigma * math.sqrt(T)


def bs_call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Black-Scholes call option price.
    S: Spot price, K: Strike, T: Time to expiry (years),
    r: Risk-free rate, sigma: Volatility (annualized)
    """
    if T <= 0:
        return max(S - K, 0)
    d1 = _d1(S, K, T, r, sigma)
    d2 = d1 - sigma * math.sqrt(T)
    return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)


def bs_put_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes put option price."""
    if T <= 0:
        return max(K - S, 0)
    d1 = _d1(S, K, T, r, sigma)
    d2 = d1 - sigma * math.sqrt(T)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


# ============================================================
# GREEKS
# ============================================================

def delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "CE") -> float:
    """
    Delta — rate of change of option price w.r.t. underlying price.
    CE: 0 to 1, PE: -1 to 0
    """
    if T <= 0 or sigma <= 0:
        if option_type == "CE":
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0

    d1 = _d1(S, K, T, r, sigma)
    if option_type == "CE":
        return norm.cdf(d1)
    return norm.cdf(d1) - 1


def gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Gamma — rate of change of delta. Same for calls and puts.
    Higher gamma = delta changes faster.
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma)
    return norm.pdf(d1) / (S * sigma * math.sqrt(T))


def theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "CE") -> float:
    """
    Theta — time decay per day (negative = loses value daily).
    Returns theta per calendar day.
    """
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma)
    d2 = d1 - sigma * math.sqrt(T)

    term1 = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))

    if option_type == "CE":
        term2 = -r * K * math.exp(-r * T) * norm.cdf(d2)
    else:
        term2 = r * K * math.exp(-r * T) * norm.cdf(-d2)

    # Convert from per-year to per-day
    return (term1 + term2) / 365


def vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Vega — sensitivity to 1% change in IV.
    Same for calls and puts.
    """
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma)
    # Return vega per 1% IV change (not per 1.0)
    return S * norm.pdf(d1) * math.sqrt(T) / 100


# ============================================================
# IMPLIED VOLATILITY
# ============================================================

def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "CE",
    max_iterations: int = 100,
    tolerance: float = 1e-5,
) -> float | None:
    """
    Calculate implied volatility using Newton-Raphson method.
    Returns annualized IV as a decimal (e.g., 0.25 = 25%).
    Returns None if convergence fails.
    """
    if T <= 0 or market_price <= 0:
        return None

    # Initial guess: use a simple approximation
    sigma = 0.3  # Start at 30% IV

    for _ in range(max_iterations):
        if option_type == "CE":
            price = bs_call_price(S, K, T, r, sigma)
        else:
            price = bs_put_price(S, K, T, r, sigma)

        diff = price - market_price

        # Vega for Newton-Raphson step (per 1.0, not per 1%)
        d1 = _d1(S, K, T, r, sigma)
        v = S * norm.pdf(d1) * math.sqrt(T)

        if v < 1e-10:
            break

        sigma -= diff / v

        # Clamp to reasonable range
        sigma = max(sigma, 0.01)
        sigma = min(sigma, 5.0)

        if abs(diff) < tolerance:
            return sigma

    return sigma if abs(diff) < 1.0 else None


# ============================================================
# TIME TO EXPIRY
# ============================================================

def time_to_expiry(expiry_date: str | date, from_date: date = None) -> float:
    """
    Calculate time to expiry in years.
    expiry_date: 'YYYY-MM-DD' string or date object
    """
    if from_date is None:
        from_date = date.today()

    if isinstance(expiry_date, str):
        expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()

    days = (expiry_date - from_date).days
    if days < 0:
        return 0.0
    return days / 365.0


# ============================================================
# ALL GREEKS AT ONCE
# ============================================================

def calculate_greeks(
    spot: float,
    strike: float,
    expiry: str | date,
    option_type: str = "CE",
    market_price: float = None,
    risk_free_rate: float = 0.07,  # India 10Y yield ~7%
    volatility: float = None,
) -> dict:
    """
    Calculate all Greeks for an option.
    If market_price is provided, computes IV first, then uses it for Greeks.
    If volatility is provided directly, uses that.

    Returns dict with: iv, delta, gamma, theta, vega, theoretical_price
    """
    T = time_to_expiry(expiry) if isinstance(expiry, (str, date)) else expiry
    r = risk_free_rate

    # Determine volatility
    iv = volatility
    if iv is None and market_price is not None:
        iv = implied_volatility(market_price, spot, strike, T, r, option_type)
    if iv is None:
        iv = 0.20  # Default 20% if all else fails

    # Calculate Greeks
    d = delta(spot, strike, T, r, iv, option_type)
    g = gamma(spot, strike, T, r, iv)
    t = theta(spot, strike, T, r, iv, option_type)
    v = vega(spot, strike, T, r, iv)

    # Theoretical price
    if option_type == "CE":
        theo_price = bs_call_price(spot, strike, T, r, iv)
    else:
        theo_price = bs_put_price(spot, strike, T, r, iv)

    return {
        "iv": round(iv * 100, 2),           # As percentage
        "delta": round(d, 4),
        "gamma": round(g, 6),
        "theta": round(t, 2),               # Per day in rupees
        "vega": round(v, 2),                 # Per 1% IV change
        "theoretical_price": round(theo_price, 2),
        "time_to_expiry_days": round(T * 365, 1),
        "option_type": option_type,
        "moneyness": "ITM" if (option_type == "CE" and spot > strike) or
                              (option_type == "PE" and spot < strike)
                     else "ATM" if abs(spot - strike) / spot < 0.005
                     else "OTM",
    }


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Greeks Calculator Test")
    print("=" * 50)

    # Example: NIFTY at 22500, CE strike 22500, 7 days to expiry
    spot = 22500
    strike = 22500
    T = 7 / 365  # 7 days

    result = calculate_greeks(
        spot=spot,
        strike=strike,
        expiry=T,
        option_type="CE",
        market_price=200,
    )

    print(f"\nNIFTY {strike} CE (7 DTE)")
    print(f"  Spot: {spot}")
    for k, v in result.items():
        print(f"  {k}: {v}")

    # Put option
    result_put = calculate_greeks(
        spot=spot,
        strike=strike,
        expiry=T,
        option_type="PE",
        market_price=180,
    )

    print(f"\nNIFTY {strike} PE (7 DTE)")
    for k, v in result_put.items():
        print(f"  {k}: {v}")

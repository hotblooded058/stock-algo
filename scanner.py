"""
Market Scanner — Main Entry Point
Scans all watchlist stocks and generates trading signals.

Usage:
    python scanner.py              # Scan all stocks
    python scanner.py RELIANCE.NS  # Scan single stock
"""

import sys
import os

# Ensure imports work
sys.path.insert(0, os.path.dirname(__file__))

from src.data.fetcher import fetch_stock_data, fetch_vix
from src.indicators.technical import add_all_indicators, get_latest_indicators
from src.signals.generator import generate_all_signals, format_signal_report, Signal
from src.risk.manager import RiskManager
from config.settings import WATCHLIST, SYMBOL_NAMES, DEFAULT_PERIOD, DAILY_INTERVAL


def scan_stock(symbol: str, period: str = DEFAULT_PERIOD,
               interval: str = DAILY_INTERVAL) -> list[Signal]:
    """Scan a single stock and return signals."""
    df = fetch_stock_data(symbol, period=period, interval=interval)
    if df.empty:
        return []

    df = add_all_indicators(df)
    indicators = get_latest_indicators(df)
    signals = generate_all_signals(symbol, indicators)
    return signals


def scan_watchlist(symbols: list = None) -> list[Signal]:
    """Scan all watchlist stocks and collect signals."""
    if symbols is None:
        symbols = WATCHLIST

    all_signals = []
    print("\n🔍 Scanning market...\n")

    for symbol in symbols:
        signals = scan_stock(symbol)
        all_signals.extend(signals)

    # Sort all signals by score
    all_signals.sort(key=lambda s: s.score, reverse=True)
    return all_signals


def main():
    # Check if specific symbol provided
    if len(sys.argv) > 1:
        symbols = sys.argv[1:]
    else:
        symbols = WATCHLIST

    # Check VIX
    print("📈 Checking India VIX...")
    vix_df = fetch_vix()
    if not vix_df.empty:
        vix = vix_df['Close'].iloc[-1]
        print(f"   India VIX: {vix:.2f}")
        if vix > 25:
            print("   ⚠️  VIX very high — options are expensive. Be extra cautious!")
        elif vix > 20:
            print("   ⚡ VIX elevated — wider stop losses recommended")
        elif vix < 13:
            print("   😴 VIX low — consider option selling strategies")
        else:
            print("   ✅ VIX normal — good for option buying")
    print()

    # Scan stocks
    signals = scan_watchlist(symbols)

    # Print report
    print(format_signal_report(signals))

    # Risk check
    rm = RiskManager()
    can_trade, msg = rm.can_trade()
    print(f"\n{msg}")
    print(rm.get_daily_summary())

    # Show position sizing for top signal
    if signals and can_trade:
        top = signals[0]
        print(f"\n💡 Top Signal: {top}")
        print("\nExample position sizing (if option premium is ₹150):")
        plan = rm.calculate_position_size(150, top.strength)
        print(rm.format_position_plan(plan))

    return signals


if __name__ == "__main__":
    main()

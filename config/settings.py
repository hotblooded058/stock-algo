"""
Configuration settings for the Options Trading Platform.
Adjust these values to match your trading style and risk tolerance.
"""

# ============================================================
# CAPITAL & RISK MANAGEMENT
# ============================================================
TOTAL_CAPITAL = 100000          # Your total trading capital (INR)
MAX_RISK_PER_TRADE = 0.02       # 2% of capital per trade
MAX_DAILY_LOSS = 0.05           # 5% max daily loss — stop trading after this
MAX_OPEN_POSITIONS = 3          # Don't hold more than 3 trades at once
STOP_LOSS_PERCENT = 0.30        # 30% of premium paid
TARGET_1_PERCENT = 0.40         # First target: 40% profit (exit half)
TARGET_2_PERCENT = 0.80         # Second target: 80% profit (exit rest)

# ============================================================
# STOCKS / INDICES TO WATCH
# ============================================================
# Indian market symbols (use .NS suffix for NSE)
# Format: { "Display Name": "Yahoo Finance Symbol" }
WATCHLIST_MAP = {
    "Nifty 50":       "^NSEI",
    "Bank Nifty":     "^NSEBANK",
    "Reliance":       "RELIANCE.NS",
    "TCS":            "TCS.NS",
    "HDFC Bank":      "HDFCBANK.NS",
    "Infosys":        "INFY.NS",
    "ICICI Bank":     "ICICIBANK.NS",
    "SBI":            "SBIN.NS",
    "Bharti Airtel":  "BHARTIARTL.NS",
    "ITC":            "ITC.NS",
}

# List of symbols (for backward compatibility)
WATCHLIST = list(WATCHLIST_MAP.values())

# Reverse lookup: symbol → display name
SYMBOL_NAMES = {v: k for k, v in WATCHLIST_MAP.items()}

# ============================================================
# INDICATOR SETTINGS
# ============================================================
EMA_SHORT = 9
EMA_MEDIUM = 21
EMA_LONG = 50
EMA_TREND = 200

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2

SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3

ATR_PERIOD = 14
VWAP_ENABLED = True

# ============================================================
# SIGNAL SCORING THRESHOLDS
# ============================================================
SIGNAL_STRONG = 80      # Score >= 80 → take full position
SIGNAL_MODERATE = 60    # Score 60-79 → take half position
SIGNAL_WEAK = 40        # Score 40-59 → skip or tiny position
# Below 40 → no trade

# ============================================================
# MARKET HOURS (IST)
# ============================================================
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"
FIRST_SIGNAL_AFTER = "09:30"    # Wait 15 min after open

# ============================================================
# ALERTS (Telegram)
# ============================================================
TELEGRAM_BOT_TOKEN = ""         # Get from @BotFather on Telegram
TELEGRAM_CHAT_ID = ""           # Your chat/group ID

# ============================================================
# DATA SETTINGS
# ============================================================
DEFAULT_PERIOD = "3mo"          # How much historical data to fetch
DEFAULT_INTERVAL = "15m"        # Candle interval (1m, 5m, 15m, 1h, 1d)
DAILY_INTERVAL = "1d"           # For daily analysis

# ============================================================
# DATABASE
# ============================================================
import os
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'trading.db')

# ============================================================
# BROKER (AngelOne SmartAPI)
# ============================================================
BROKER_NAME = "angelone"
DATA_SOURCE_PRIORITY = ["angelone", "yahoo", "nse", "google"]
TRADING_MODE = "paper"          # "paper" or "live" — paper first!

# ============================================================
# OPTIONS SETTINGS
# ============================================================
LOT_SIZES = {
    "NIFTY": 25,
    "BANKNIFTY": 15,
    "FINNIFTY": 25,
    "RELIANCE": 250,
    "TCS": 150,
    "HDFCBANK": 550,
    "INFY": 300,
    "ICICIBANK": 700,
    "SBIN": 750,
    "BHARTIARTL": 450,
    "ITC": 1600,
}

# Options chain fetch settings
OPTIONS_STRIKE_RANGE = 15       # ATM +/- 15 strikes
DEFAULT_EXPIRY = "weekly"       # "weekly" or "monthly"

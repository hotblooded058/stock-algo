# 📈 Options Trading Decision Platform

A personal, data-driven trading system that analyzes market data, technical indicators, and sentiment to generate high-probability trading signals.

## Quick Start (using uv)

This project uses [uv](https://docs.astral.sh/uv/) — an ultra-fast Python package manager written in Rust.

### 1. Install uv (one-time setup)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Set up the project
```bash
cd Stock-algo
uv sync
```
This automatically creates a virtual environment, installs Python 3.13 if needed, and installs all dependencies. That's it — one command.

### 3. Run the Scanner (Terminal)
```bash
# Scan all watchlist stocks
uv run python scanner.py

# Scan a specific stock
uv run python scanner.py RELIANCE.NS
```

### 4. Run the Dashboard (Web UI)
```bash
uv run streamlit run dashboard.py
```
Opens a browser with interactive charts, signals, and risk calculator.

### Adding new packages
```bash
uv add <package-name>          # adds to pyproject.toml and installs
uv add --optional alerts <pkg> # adds to optional "alerts" group
```

## Project Structure

```
Stock-algo/
├── config/
│   └── settings.py          ← All your settings (capital, risk, indicators)
├── src/
│   ├── data/
│   │   └── fetcher.py       ← Fetches market data from Yahoo Finance
│   ├── indicators/
│   │   └── technical.py     ← Calculates RSI, EMA, MACD, Bollinger, etc.
│   ├── signals/
│   │   └── generator.py     ← Generates BUY CALL / BUY PUT signals
│   ├── risk/
│   │   └── manager.py       ← Position sizing, stop loss, daily limits
│   └── sentiment/           ← (Coming soon) News & VIX analysis
├── dashboard/               ← (Future) Dashboard components
├── logs/                    ← Trade logs and risk state
├── journal/                 ← Trade journal entries
├── scanner.py               ← Main scanner script
├── dashboard.py             ← Streamlit web dashboard
├── pyproject.toml           ← Project config & dependencies (uv)
├── .python-version          ← Pinned Python version (3.13)
├── uv.lock                  ← Auto-generated lockfile (committed to git)
├── requirements.txt         ← Legacy fallback (pip users)
└── GUIDE_OPTIONS_TRADING_SYSTEM.md  ← MUST READ — complete guide
```

## What Each Module Does

| Module | Purpose |
|--------|---------|
| **fetcher.py** | Gets price data (OHLCV) from Yahoo Finance |
| **technical.py** | Computes 15+ indicators (EMA, RSI, MACD, SuperTrend, etc.) |
| **generator.py** | Applies strategies and scores signals 0-100 |
| **manager.py** | Enforces risk rules — position sizing, stop loss, daily limits |
| **scanner.py** | Ties everything together — scan → analyze → signal |
| **dashboard.py** | Visual web interface with charts and controls |

## Learning Path

1. **Read the Guide** → `GUIDE_OPTIONS_TRADING_SYSTEM.md` (understand everything first)
2. **Explore settings** → `config/settings.py` (see what you can customize)
3. **Run the scanner** → `uv run python scanner.py` (see signals in terminal)
4. **Launch dashboard** → `uv run streamlit run dashboard.py` (visual interface)
5. **Paper trade** → Follow signals WITHOUT real money for 2-4 weeks
6. **Go live** → Start with minimum capital after consistent paper trading results

## Customization

Edit `config/settings.py` to change:
- Your capital amount
- Risk per trade (default 2%)
- Which stocks to watch
- Indicator parameters
- Signal thresholds
- Telegram alerts (add your bot token)

## Important Disclaimer

This is a personal decision-support tool, not financial advice. Options trading involves significant risk. Always paper trade first and never risk money you can't afford to lose.

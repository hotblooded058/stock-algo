"""
Trading Dashboard — Streamlit Web App
Run with: streamlit run dashboard.py
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.data.fetcher import fetch_stock_data, fetch_vix
from src.indicators.technical import add_all_indicators, get_latest_indicators
from src.signals.generator import generate_all_signals
from src.risk.manager import RiskManager
from config.settings import WATCHLIST, WATCHLIST_MAP, SYMBOL_NAMES, TOTAL_CAPITAL

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Options Trading Platform",
    page_icon="📈",
    layout="wide"
)

# ============================================================
# AUTO-REFRESH: Fetches fresh data every few minutes
# ============================================================
# Cache data for a short time so it refreshes automatically
@st.cache_data(ttl=180)  # Cache expires every 3 minutes
def cached_fetch(symbol, period, interval):
    """Fetch stock data with 3-minute cache — ensures fresh data."""
    return fetch_stock_data(symbol, period=period, interval=interval)

@st.cache_data(ttl=300)  # VIX refreshes every 5 minutes
def cached_fetch_vix():
    return fetch_vix()

st.title("📈 Options Trading Decision Platform")

# Top bar: last updated time + manual refresh button
top_col1, top_col2 = st.columns([4, 1])
top_col1.caption("Data-driven signals for smarter options trading")
if top_col2.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Helper: get display name for any symbol
def display_name(symbol: str) -> str:
    return SYMBOL_NAMES.get(symbol, symbol)


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.header("⚙️ Settings")

    # Dropdown shows friendly names like "Reliance", "Nifty 50"
    stock_names = list(WATCHLIST_MAP.keys())
    selected_name = st.selectbox("Select Stock / Index", stock_names)
    selected_symbol = WATCHLIST_MAP[selected_name]

    interval = st.selectbox("Timeframe", ["1d", "1h", "15m", "5m"], index=0)
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1)

    st.divider()
    st.header("💰 Risk Calculator")
    capital = st.number_input("Your Capital (₹)", value=TOTAL_CAPITAL, step=10000)
    premium = st.number_input("Option Premium (₹)", value=150.0, step=10.0)
    strength = st.selectbox("Signal Strength", ["STRONG", "MODERATE", "WEAK"])


# ============================================================
# FETCH DATA
# ============================================================
with st.spinner(f"Fetching data for {selected_name}..."):
    df = cached_fetch(selected_symbol, period, interval)

if df.empty:
    st.error(f"Could not fetch data for {selected_name}. Try a different stock or timeframe.")
    st.stop()

df = add_all_indicators(df)
indicators = get_latest_indicators(df)

# Show data freshness — warn if stale
from datetime import datetime, timedelta
import pytz

last_candle_time = df.index[-1]
try:
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    last_candle_aware = last_candle_time.tz_localize(ist) if last_candle_time.tzinfo is None else last_candle_time
    days_old = (now_ist.date() - last_candle_aware.date()).days
except Exception:
    days_old = 0

if days_old > 1:
    st.warning(
        f"⚠️ Data is **{days_old} days old** (last candle: {last_candle_time.strftime('%d %b %Y')}). "
        f"Yahoo Finance may be delayed. Signals are based on this older data — verify prices on your broker app before trading."
    )
else:
    st.caption(f"📡 Last data: {last_candle_time.strftime('%d %b %Y, %I:%M %p')}  ·  Auto-refreshes every 3 min")

# ============================================================
# TOP METRICS
# ============================================================
col_vix, col_price, col_rsi, col_trend = st.columns(4)

vix_df = cached_fetch_vix()
if not vix_df.empty:
    vix_val = vix_df['Close'].iloc[-1]
    vix_change = vix_df['Close'].iloc[-1] - vix_df['Close'].iloc[-2]
    col_vix.metric("India VIX", f"{vix_val:.2f}", f"{vix_change:+.2f}")

# Calculate % change — use previous candle's close if open == close (patched data)
current_close = indicators['close']
current_open = indicators['open']
if len(df) >= 2 and abs(current_close - current_open) < 0.01:
    prev_close = df['Close'].iloc[-2]
    pct_change = ((current_close - prev_close) / prev_close * 100)
else:
    pct_change = ((current_close - current_open) / current_open * 100)

col_price.metric(
    selected_name,
    f"₹{current_close:,.2f}",
    f"{pct_change:+.2f}%"
)

rsi_val = indicators.get('rsi')
if rsi_val:
    col_rsi.metric("RSI", f"{rsi_val:.1f}",
                    "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Normal")

trend = "Bullish 🟢" if indicators.get('supertrend_bullish') else "Bearish 🔴"
col_trend.metric("SuperTrend", trend)

st.divider()

# ============================================================
# CHART WITH INDICATOR SELECTOR
# ============================================================
st.subheader(f"📊 {selected_name} Chart")

# --- Indicator Picker ---
OVERLAY_INDICATORS = {
    "EMA 9":            {"col": "EMA_9",       "color": "orange",    "type": "overlay"},
    "EMA 21":           {"col": "EMA_21",      "color": "dodgerblue","type": "overlay"},
    "EMA 50":           {"col": "EMA_50",      "color": "mediumpurple","type": "overlay"},
    "EMA 200":          {"col": "EMA_200",     "color": "crimson",   "type": "overlay"},
    "Bollinger Bands":  {"col": "BB",          "color": "gray",      "type": "overlay"},
    "SuperTrend":       {"col": "SuperTrend",  "color": "limegreen", "type": "overlay"},
}

PANEL_INDICATORS = {
    "RSI":              {"col": "RSI",              "color": "purple",  "type": "panel"},
    "MACD":             {"col": "MACD",             "color": "cyan",    "type": "panel"},
    "Volume":           {"col": "Volume",           "color": "gray",    "type": "panel"},
}

col_overlay, col_panel = st.columns(2)

with col_overlay:
    selected_overlays = st.multiselect(
        "📌 Overlays (on price chart)",
        options=list(OVERLAY_INDICATORS.keys()),
        default=["EMA 21", "EMA 50"],
        help="These appear on top of the candlestick chart"
    )

with col_panel:
    selected_panels = st.multiselect(
        "📊 Panels (below chart)",
        options=list(PANEL_INDICATORS.keys()),
        default=["RSI", "Volume"],
        help="These show as separate panels below the price chart"
    )

# --- Build Chart ---
num_panels = 1 + len(selected_panels)  # 1 for price + selected panels
row_heights = [0.6] + [0.2] * len(selected_panels) if selected_panels else [1.0]

# Normalize heights
total = sum(row_heights)
row_heights = [h / total for h in row_heights]

panel_titles = [f"{selected_name}"] + selected_panels

fig = make_subplots(
    rows=num_panels, cols=1, shared_xaxes=True,
    vertical_spacing=0.04,
    row_heights=row_heights,
    subplot_titles=panel_titles
)

# --- Candlestick ---
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'],
    low=df['Low'], close=df['Close'], name="Price"
), row=1, col=1)

# --- Overlay Indicators ---
for name in selected_overlays:
    info = OVERLAY_INDICATORS[name]

    if name == "Bollinger Bands":
        if 'BB_upper' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['BB_upper'], name="BB Upper",
                line=dict(width=1, color='rgba(150,150,150,0.5)', dash='dot')
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df.index, y=df['BB_lower'], name="BB Lower",
                line=dict(width=1, color='rgba(150,150,150,0.5)', dash='dot'),
                fill='tonexty', fillcolor='rgba(150,150,150,0.08)'
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df.index, y=df['BB_middle'], name="BB Mid",
                line=dict(width=1, color='rgba(150,150,150,0.4)', dash='dash')
            ), row=1, col=1)

    elif name == "SuperTrend":
        if 'SuperTrend' in df.columns and 'SuperTrend_dir' in df.columns:
            colors = ['limegreen' if d == 1 else 'red' for d in df['SuperTrend_dir']]
            fig.add_trace(go.Scatter(
                x=df.index, y=df['SuperTrend'], name="SuperTrend",
                mode='markers+lines',
                marker=dict(color=colors, size=3),
                line=dict(width=1, color='gray')
            ), row=1, col=1)
    else:
        col_name = info['col']
        if col_name in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_name], name=name,
                line=dict(width=1.5, color=info['color'])
            ), row=1, col=1)

# --- Panel Indicators ---
for i, panel_name in enumerate(selected_panels):
    row = i + 2  # row 1 is price chart

    if panel_name == "RSI" and 'RSI' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['RSI'], name="RSI",
            line=dict(color='mediumpurple', width=1.5)
        ), row=row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red",
                      annotation_text="70", row=row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green",
                      annotation_text="30", row=row, col=1)
        fig.update_yaxes(range=[0, 100], row=row, col=1)

    elif panel_name == "MACD" and 'MACD' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['MACD'], name="MACD Line",
            line=dict(color='cyan', width=1.5)
        ), row=row, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['MACD_signal'], name="Signal Line",
            line=dict(color='orange', width=1)
        ), row=row, col=1)
        hist_colors = ['green' if v >= 0 else 'red' for v in df['MACD_histogram']]
        fig.add_trace(go.Bar(
            x=df.index, y=df['MACD_histogram'], name="MACD Histogram",
            marker_color=hist_colors, opacity=0.6
        ), row=row, col=1)

    elif panel_name == "Volume":
        vol_colors = ['green' if c >= o else 'red'
                      for c, o in zip(df['Close'], df['Open'])]
        fig.add_trace(go.Bar(
            x=df.index, y=df['Volume'], name="Volume",
            marker_color=vol_colors, opacity=0.6
        ), row=row, col=1)
        if 'Vol_MA_20' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['Vol_MA_20'], name="Vol Avg (20)",
                line=dict(color='yellow', width=1, dash='dash')
            ), row=row, col=1)

chart_height = 500 + (len(selected_panels) * 150)
fig.update_layout(
    height=chart_height,
    xaxis_rangeslider_visible=False,
    template="plotly_dark",
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    margin=dict(t=60, b=30),
)
st.plotly_chart(fig, width="stretch")

# ============================================================
# SIGNALS
# ============================================================
st.divider()
st.subheader("🎯 Trading Signals")

signals = generate_all_signals(selected_symbol, indicators)

if signals:
    for sig in signals:
        icon = "🟢" if "CALL" in sig.direction else "🔴"
        strength_icon = {"STRONG": "🔥", "MODERATE": "⚡", "WEAK": "💤"}.get(sig.strength, "")

        with st.expander(
            f"{icon} {display_name(sig.symbol)} → {sig.direction} | "
            f"Score: {sig.score}/100 {strength_icon} {sig.strength} | "
            f"Strategy: {sig.strategy}",
            expanded=True
        ):
            st.progress(sig.score / 100)
            for reason in sig.reasons:
                st.markdown(f"- ✓ {reason}")
else:
    st.info(f"📭 No trading signals for {selected_name} right now. Check other stocks or wait for setups.")

# ============================================================
# POSITION SIZING
# ============================================================
st.divider()
st.subheader("📋 Position Size Calculator")

rm = RiskManager(capital=capital)
can_trade, trade_msg = rm.can_trade()

if can_trade:
    plan = rm.calculate_position_size(premium, strength)
    col1, col2, col3 = st.columns(3)

    col1.metric("Quantity", f"{plan['quantity']} units")
    col1.metric("Total Cost", f"₹{plan['total_cost']:,.2f}")

    col2.metric("Stop Loss", f"₹{plan['stop_loss']:.2f}")
    col2.metric("Max Loss", f"₹{plan['max_loss']:,.2f}")

    col3.metric("Target 1", f"₹{plan['target_1']:.2f}")
    col3.metric("Target 2", f"₹{plan['target_2']:.2f}")

    st.caption(f"Risk: {plan['risk_percent']}% of capital | Signal: {strength}")
else:
    st.error(trade_msg)

# ============================================================
# FULL WATCHLIST SCAN
# ============================================================
st.divider()
st.subheader("🔍 Watchlist Quick Scan")

if st.button("Scan All Stocks", type="primary"):
    all_signals = []
    progress = st.progress(0)

    for i, symbol in enumerate(WATCHLIST):
        try:
            sdf = fetch_stock_data(symbol, period="3mo", interval="1d")
            if not sdf.empty:
                sdf = add_all_indicators(sdf)
                ind = get_latest_indicators(sdf)
                sigs = generate_all_signals(symbol, ind)
                all_signals.extend(sigs)
        except Exception:
            pass
        progress.progress((i + 1) / len(WATCHLIST))

    if all_signals:
        all_signals.sort(key=lambda s: s.score, reverse=True)
        scan_data = []
        for s in all_signals:
            scan_data.append({
                'Stock': display_name(s.symbol),
                'Signal': s.direction,
                'Score': s.score,
                'Strength': s.strength,
                'Strategy': s.strategy,
            })
        st.dataframe(pd.DataFrame(scan_data), width="stretch")
    else:
        st.info("No signals found across the watchlist.")

# Footer
st.divider()
st.caption("⚠️ This is a decision-support tool, not financial advice. Always do your own analysis. Paper trade first!")

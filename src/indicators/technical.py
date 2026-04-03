"""
Technical Indicators Calculator
Computes all the indicators needed for signal generation.
Uses the 'ta' library (Technical Analysis Library in Python).
"""

import pandas as pd
import ta
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import (
    EMA_SHORT, EMA_MEDIUM, EMA_LONG, EMA_TREND,
    RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BOLLINGER_PERIOD, BOLLINGER_STD,
    SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER,
    ATR_PERIOD
)


def _supertrend(df, period=10, multiplier=3):
    """Calculate SuperTrend indicator manually."""
    hl2 = (df['High'] + df['Low']) / 2
    atr = ta.volatility.AverageTrueRange(
        high=df['High'], low=df['Low'], close=df['Close'], window=period
    ).average_true_range()

    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)

    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)

    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = -1

    for i in range(1, len(df)):
        if df['Close'].iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif df['Close'].iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

        if direction.iloc[i] == 1:
            supertrend.iloc[i] = max(lower_band.iloc[i],
                                      supertrend.iloc[i - 1] if direction.iloc[i - 1] == 1
                                      else lower_band.iloc[i])
        else:
            supertrend.iloc[i] = min(upper_band.iloc[i],
                                      supertrend.iloc[i - 1] if direction.iloc[i - 1] == -1
                                      else upper_band.iloc[i])

    return supertrend, direction


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical indicators to a price DataFrame.
    """
    if df.empty or len(df) < 30:
        return df

    df = df.copy()

    # ---- Moving Averages (EMA) ----
    df['EMA_9'] = ta.trend.EMAIndicator(close=df['Close'], window=EMA_SHORT).ema_indicator()
    df['EMA_21'] = ta.trend.EMAIndicator(close=df['Close'], window=EMA_MEDIUM).ema_indicator()
    df['EMA_50'] = ta.trend.EMAIndicator(close=df['Close'], window=EMA_LONG).ema_indicator()
    if len(df) >= EMA_TREND:
        df['EMA_200'] = ta.trend.EMAIndicator(close=df['Close'], window=EMA_TREND).ema_indicator()

    # ---- RSI ----
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=RSI_PERIOD).rsi()

    # ---- MACD ----
    macd_ind = ta.trend.MACD(close=df['Close'], window_slow=MACD_SLOW,
                              window_fast=MACD_FAST, window_sign=MACD_SIGNAL)
    df['MACD'] = macd_ind.macd()
    df['MACD_signal'] = macd_ind.macd_signal()
    df['MACD_histogram'] = macd_ind.macd_diff()

    # ---- Bollinger Bands ----
    bb = ta.volatility.BollingerBands(close=df['Close'], window=BOLLINGER_PERIOD,
                                       window_dev=BOLLINGER_STD)
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    df['BB_middle'] = bb.bollinger_mavg()
    df['BB_width'] = bb.bollinger_wband()

    # ---- SuperTrend ----
    try:
        st_val, st_dir = _supertrend(df, SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER)
        df['SuperTrend'] = st_val
        df['SuperTrend_dir'] = st_dir  # 1 = bullish, -1 = bearish
    except Exception:
        pass

    # ---- ATR ----
    df['ATR'] = ta.volatility.AverageTrueRange(
        high=df['High'], low=df['Low'], close=df['Close'], window=ATR_PERIOD
    ).average_true_range()

    # ---- OBV ----
    df['OBV'] = ta.volume.OnBalanceVolumeIndicator(
        close=df['Close'], volume=df['Volume']
    ).on_balance_volume()

    # ---- Volume Moving Average ----
    df['Vol_MA_20'] = df['Volume'].rolling(window=20).mean()

    # ---- VWAP ----
    try:
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        cumulative_tp_vol = (typical_price * df['Volume']).cumsum()
        cumulative_vol = df['Volume'].cumsum()
        df['VWAP'] = cumulative_tp_vol / cumulative_vol
    except Exception:
        pass

    # ---- ADX (Average Directional Index) ----
    try:
        adx_ind = ta.trend.ADXIndicator(
            high=df['High'], low=df['Low'], close=df['Close'], window=14
        )
        df['ADX'] = adx_ind.adx()
        df['DI_plus'] = adx_ind.adx_pos()
        df['DI_minus'] = adx_ind.adx_neg()
    except Exception:
        pass

    # ---- Derived Signals ----
    df['EMA_9_above_21'] = (df['EMA_9'] > df['EMA_21']).astype(int)
    df['EMA_9_cross_21'] = df['EMA_9_above_21'].diff().fillna(0)

    df['Above_EMA_21'] = (df['Close'] > df['EMA_21']).astype(int)
    df['Above_EMA_50'] = (df['Close'] > df['EMA_50']).astype(int)
    if 'EMA_200' in df.columns:
        df['Above_EMA_200'] = (df['Close'] > df['EMA_200']).astype(int)

    df['High_Volume'] = (df['Volume'] > df['Vol_MA_20']).astype(int)

    return df


def get_latest_indicators(df: pd.DataFrame) -> dict:
    """Extract the latest indicator values as a dictionary."""
    if df.empty:
        return {}

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    result = {
        'close': latest['Close'],
        'open': latest['Open'],
        'high': latest['High'],
        'low': latest['Low'],
        'volume': latest['Volume'],

        'ema_9': latest.get('EMA_9'),
        'ema_21': latest.get('EMA_21'),
        'ema_50': latest.get('EMA_50'),
        'ema_200': latest.get('EMA_200'),

        'rsi': latest.get('RSI'),
        'atr': latest.get('ATR'),

        'above_ema_21': bool(latest.get('Above_EMA_21', 0)),
        'above_ema_50': bool(latest.get('Above_EMA_50', 0)),
        'above_ema_200': bool(latest.get('Above_EMA_200', 0)) if 'Above_EMA_200' in df.columns else None,
        'ema_bullish_cross': latest.get('EMA_9_cross_21', 0) > 0,
        'ema_bearish_cross': latest.get('EMA_9_cross_21', 0) < 0,
        'high_volume': bool(latest.get('High_Volume', 0)),
    }

    # VWAP
    if 'VWAP' in df.columns:
        result['vwap'] = latest.get('VWAP')
        result['above_vwap'] = bool(latest['Close'] > latest['VWAP']) if latest.get('VWAP') else None

    # ADX
    if 'ADX' in df.columns:
        result['adx'] = latest.get('ADX')
        result['di_plus'] = latest.get('DI_plus')
        result['di_minus'] = latest.get('DI_minus')
        adx_val = latest.get('ADX')
        if adx_val is not None:
            result['trending'] = bool(adx_val > 25)
            result['strong_trend'] = bool(adx_val > 30)
            result['choppy'] = bool(adx_val < 20)
        else:
            result['trending'] = None
            result['strong_trend'] = None
            result['choppy'] = None

    # Volume ratio
    if 'Vol_MA_20' in df.columns and latest.get('Vol_MA_20') and latest['Vol_MA_20'] > 0:
        result['vol_ma_20'] = latest['Vol_MA_20']
        result['volume_ratio'] = latest['Volume'] / latest['Vol_MA_20']
    else:
        result['vol_ma_20'] = None
        result['volume_ratio'] = None

    # SuperTrend
    if 'SuperTrend_dir' in df.columns:
        result['supertrend_bullish'] = latest['SuperTrend_dir'] == 1
    else:
        result['supertrend_bullish'] = None

    # MACD
    if 'MACD_histogram' in df.columns:
        result['macd_histogram'] = latest['MACD_histogram']
        result['macd_hist_rising'] = latest['MACD_histogram'] > prev['MACD_histogram']
    else:
        result['macd_histogram'] = None
        result['macd_hist_rising'] = None

    # Bollinger
    if 'BB_lower' in df.columns and 'BB_upper' in df.columns:
        result['at_lower_bb'] = latest['Close'] <= latest['BB_lower']
        result['at_upper_bb'] = latest['Close'] >= latest['BB_upper']
        result['bb_squeezing'] = latest['BB_width'] < prev['BB_width']
    else:
        result['at_lower_bb'] = None
        result['at_upper_bb'] = None
        result['bb_squeezing'] = None

    return result


# ---- Quick Test ----
if __name__ == "__main__":
    from src.data.fetcher import fetch_stock_data

    print("=" * 50)
    print("Testing Technical Indicators")
    print("=" * 50)

    df = fetch_stock_data("^NSEI", period="3mo", interval="1d")
    if not df.empty:
        df = add_all_indicators(df)
        print(f"\nColumns: {list(df.columns)}")

        indicators = get_latest_indicators(df)
        print(f"\nLatest Nifty Indicators:")
        for key, val in indicators.items():
            if val is not None:
                if isinstance(val, float):
                    print(f"  {key}: {val:.2f}")
                else:
                    print(f"  {key}: {val}")

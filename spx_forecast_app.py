# ═══════════════════════════════════════════════════════════════════════════════
# SPX PROPHET V4 - Institutional 0DTE Trading Analytics
# 3-Pillar Methodology | Dynamic Structure | 5-Min Reversal Detection
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import pytz
import json
import os
import time as time_module
import requests
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Tuple
from functools import wraps

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="SPX Prophet V4", page_icon="🔮", layout="wide", initial_sidebar_state="expanded")

CT = pytz.timezone("America/Chicago")
CONE_SLOPE = 0.475
POLYGON_API_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
SAVE_FILE = "spx_prophet_v4_inputs.json"

VIX_ZONES = {"EXTREME_LOW": (0, 12), "LOW": (12, 16), "NORMAL": (16, 20), "ELEVATED": (20, 25), "HIGH": (25, 35), "EXTREME": (35, 100)}

# ═══════════════════════════════════════════════════════════════════════════════
# CSS STYLES
# ═══════════════════════════════════════════════════════════════════════════════

STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=DM+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root{--bg-primary:#0a0a0f;--bg-secondary:#12121a;--bg-card:rgba(255,255,255,0.03);--border:rgba(255,255,255,0.08);--text-primary:#fff;--text-secondary:rgba(255,255,255,0.6);--green:#00d4aa;--red:#ff4757;--amber:#ffa502;--purple:#a855f7;--cyan:#22d3ee;--blue:#3b82f6}
.stApp{background:linear-gradient(135deg,var(--bg-primary) 0%,var(--bg-secondary) 100%);font-family:'DM Sans',sans-serif}
.stApp>header{background:transparent!important}
[data-testid="stSidebar"]{background:rgba(10,10,15,0.95)!important;border-right:1px solid var(--border)}
[data-testid="stSidebar"] *{color:var(--text-primary)!important}
.hero-header{background:linear-gradient(135deg,rgba(168,85,247,0.15),rgba(34,211,238,0.15));border:1px solid var(--border);border-radius:20px;padding:24px 32px;margin-bottom:24px;text-align:center;backdrop-filter:blur(20px)}
.hero-title{font-family:'Space Grotesk',sans-serif;font-size:32px;font-weight:700;color:var(--text-primary);margin:0}
.hero-subtitle{font-size:14px;color:var(--text-secondary);margin-top:4px}
.hero-price{font-family:'IBM Plex Mono',monospace;font-size:48px;font-weight:700;color:var(--cyan);margin-top:12px}
.hero-time{font-family:'IBM Plex Mono',monospace;font-size:14px;color:var(--text-secondary)}
.card{background:var(--bg-card);border:1px solid var(--border);border-radius:16px;padding:20px;margin-bottom:16px;backdrop-filter:blur(10px)}
.card-header{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.card-icon{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px}
.card-icon.green{background:rgba(0,212,170,0.15)}.card-icon.red{background:rgba(255,71,87,0.15)}.card-icon.amber{background:rgba(255,165,2,0.15)}.card-icon.purple{background:rgba(168,85,247,0.15)}.card-icon.cyan{background:rgba(34,211,238,0.15)}.card-icon.blue{background:rgba(59,130,246,0.15)}
.card-title{font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:600;color:var(--text-primary)}
.card-subtitle{font-size:12px;color:var(--text-secondary)}
.signal-badge{display:inline-block;padding:8px 20px;border-radius:24px;font-size:14px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px}
.signal-badge.calls{background:rgba(0,212,170,0.2);color:var(--green);border:1px solid var(--green)}
.signal-badge.puts{background:rgba(255,71,87,0.2);color:var(--red);border:1px solid var(--red)}
.signal-badge.neutral{background:rgba(255,165,2,0.2);color:var(--amber);border:1px solid var(--amber)}
.signal-badge.wait{background:rgba(255,255,255,0.1);color:var(--text-secondary);border:1px solid var(--border)}
.metric-value{font-family:'IBM Plex Mono',monospace;font-size:24px;font-weight:600}
.metric-value.green{color:var(--green)}.metric-value.red{color:var(--red)}.metric-value.amber{color:var(--amber)}.metric-value.cyan{color:var(--cyan)}.metric-value.purple{color:var(--purple)}
.entry-alert{background:linear-gradient(135deg,rgba(0,212,170,0.2),rgba(34,211,238,0.2));border:2px solid var(--green);border-radius:16px;padding:24px;text-align:center;margin:16px 0;animation:pulse 2s infinite}
.entry-alert.puts{background:linear-gradient(135deg,rgba(255,71,87,0.2),rgba(168,85,247,0.2));border-color:var(--red)}
.entry-alert.wait{background:rgba(255,255,255,0.05);border-color:var(--border);animation:none}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(0,212,170,0.4)}50%{box-shadow:0 0 20px 10px rgba(0,212,170,0.1)}}
.alert-title{font-size:14px;color:var(--text-secondary);margin-bottom:8px}
.alert-action{font-family:'Space Grotesk',sans-serif;font-size:28px;font-weight:700}
.alert-action.buy{color:var(--green)}.alert-action.sell{color:var(--red)}.alert-action.wait{color:var(--text-secondary)}
.alert-details{font-family:'IBM Plex Mono',monospace;font-size:16px;margin-top:8px;color:var(--text-primary)}
.data-table{width:100%;border-collapse:collapse;font-size:13px}
.data-table th{text-align:left;padding:10px 12px;color:var(--text-secondary);font-weight:500;border-bottom:1px solid var(--border);font-size:11px;text-transform:uppercase;letter-spacing:0.5px}
.data-table td{padding:10px 12px;color:var(--text-primary);border-bottom:1px solid rgba(255,255,255,0.03);font-family:'IBM Plex Mono',monospace}
.table-up{color:var(--green)!important}.table-down{color:var(--red)!important}
.confidence-container{margin:16px 0}
.confidence-bar{height:12px;background:rgba(255,255,255,0.1);border-radius:6px;overflow:hidden}
.confidence-fill{height:100%;border-radius:6px;transition:width 0.5s ease}
.confidence-fill.a-plus{background:linear-gradient(90deg,#00d4aa,#22d3ee)}.confidence-fill.high{background:linear-gradient(90deg,#22d3ee,#3b82f6)}.confidence-fill.medium{background:linear-gradient(90deg,#ffa502,#ff6b35)}.confidence-fill.low{background:linear-gradient(90deg,#ff4757,#ff6b6b)}
.confidence-label{display:flex;justify-content:space-between;margin-top:8px;font-size:12px}
.confidence-score{font-family:'IBM Plex Mono',monospace;font-weight:600}
.pillar-item{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.03)}
.pillar-name{font-size:13px;color:var(--text-secondary)}.pillar-value{font-size:13px;font-weight:500}
.reversal-box{background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:12px;padding:16px;margin-top:12px}
.reversal-title{font-size:12px;color:var(--text-secondary);margin-bottom:8px}
.reversal-status{font-size:14px;font-weight:600}
.reversal-status.bullish{color:var(--green)}.reversal-status.bearish{color:var(--red)}.reversal-status.neutral{color:var(--amber)}
.app-footer{text-align:center;padding:20px;color:var(--text-secondary);font-size:12px;border-top:1px solid var(--border);margin-top:24px}
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def retry_with_backoff(max_retries=3, base_delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time_module.sleep(base_delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

def get_now_ct() -> datetime:
    return datetime.now(CT)

def is_maintenance_window(dt: datetime) -> bool:
    if dt.weekday() >= 4:
        return False
    t = dt.time()
    return time(16, 0) <= t <= time(17, 0)

def count_trading_minutes(start_dt: datetime, end_dt: datetime) -> int:
    if start_dt >= end_dt:
        return 0
    minutes = 0
    current = start_dt.replace(second=0, microsecond=0)
    while current < end_dt:
        if current.weekday() >= 5:
            current += timedelta(days=1)
            current = current.replace(hour=17, minute=0)
            continue
        if is_maintenance_window(current):
            current += timedelta(minutes=1)
            continue
        minutes += 1
        current += timedelta(minutes=1)
    return minutes

def count_30min_blocks(start_dt: datetime, end_dt: datetime) -> int:
    return count_trading_minutes(start_dt, end_dt) // 30

# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def fetch_es_30min_candles(days: int = 10) -> Optional[pd.DataFrame]:
    """Fetch ES 30-min candles - needs 200+ for MA calculation"""
    for attempt in range(3):
        try:
            es = yf.Ticker("ES=F")
            data = es.history(period=f"{days}d", interval="30m")
            if data is not None and not data.empty:
                return data
        except Exception:
            time_module.sleep(1 * (2 ** attempt))
    return None

@st.cache_data(ttl=60, show_spinner=False)
def fetch_spx_price() -> Optional[float]:
    """Fetch current SPX price"""
    for attempt in range(3):
        try:
            spx = yf.Ticker("^GSPC")
            data = spx.history(period="1d", interval="1m")
            if data is not None and not data.empty:
                return round(float(data['Close'].iloc[-1]), 2)
        except Exception:
            time_module.sleep(1 * (2 ** attempt))
    return None

def fetch_spx_5min_candles(periods: int = 20) -> Optional[pd.DataFrame]:
    """NO CACHE - real-time for reversal detection"""
    for attempt in range(3):
        try:
            spx = yf.Ticker("^GSPC")
            data = spx.history(period="1d", interval="5m")
            if data is not None and not data.empty:
                return data.tail(periods)
        except Exception:
            time_module.sleep(1 * (2 ** attempt))
    return None

@st.cache_data(ttl=60, show_spinner=False)
def fetch_vix_price() -> Optional[float]:
    """Fetch current VIX"""
    for attempt in range(3):
        try:
            vix = yf.Ticker("^VIX")
            data = vix.history(period="1d", interval="1m")
            if data is not None and not data.empty:
                return round(float(data['Close'].iloc[-1]), 2)
        except Exception:
            time_module.sleep(1 * (2 ** attempt))
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# PILLAR 1: MA BIAS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_ma_bias(es_candles: Optional[pd.DataFrame]) -> Dict:
    candle_count = len(es_candles) if es_candles is not None else 0
    
    # Need minimum candles for calculation
    if es_candles is None or candle_count < 50:
        return {"signal": "NEUTRAL", "reason": "Insufficient data - use manual override", "ema_50": None, "sma_200": None, "diff_pct": None, "score": 0, "candle_count": candle_count, "data_status": "NO_DATA"}
    
    close = es_candles['Close']
    ema_50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    
    # Use available data for SMA (200 or less)
    sma_period = min(200, candle_count)
    sma_200 = close.rolling(window=sma_period).mean().iloc[-1]
    diff_pct = ((ema_50 - sma_200) / sma_200) * 100
    
    # Determine data quality
    data_status = "FULL" if candle_count >= 200 else "PARTIAL"
    
    if ema_50 > sma_200:
        signal, score, reason = "LONG", min(25, int(abs(diff_pct) * 10)), f"EMA > SMA by {diff_pct:+.2f}%"
    elif ema_50 < sma_200:
        signal, score, reason = "SHORT", min(25, int(abs(diff_pct) * 10)), f"EMA < SMA by {diff_pct:+.2f}%"
    else:
        signal, score, reason = "NEUTRAL", 0, "MAs converging"
    
    # Reduce score if partial data
    if data_status == "PARTIAL":
        score = int(score * 0.7)
        reason += f" (partial: {candle_count} candles)"
    
    return {"signal": signal, "reason": reason, "ema_50": round(ema_50, 2), "sma_200": round(sma_200, 2), "diff_pct": round(diff_pct, 4), "score": score, "candle_count": candle_count, "data_status": data_status}

# ═══════════════════════════════════════════════════════════════════════════════
# PILLAR 2: DAY STRUCTURE (DYNAMIC PROJECTION)
# ═══════════════════════════════════════════════════════════════════════════════

def project_trendline(anchor1_price: float, anchor1_time: datetime, anchor2_price: float, anchor2_time: datetime, target_time: datetime) -> float:
    minutes_between = count_trading_minutes(anchor1_time, anchor2_time)
    if minutes_between == 0:
        return anchor2_price
    slope_per_min = (anchor2_price - anchor1_price) / minutes_between
    minutes_to_target = count_trading_minutes(anchor1_time, target_time)
    return round(anchor1_price + (slope_per_min * minutes_to_target), 2)

def calculate_day_structure(ceiling_anchors: List[Tuple[float, datetime]], floor_anchors: List[Tuple[float, datetime]], target_time: datetime, current_price: float) -> Dict:
    now = get_now_ct()
    
    if len(ceiling_anchors) >= 2:
        ceiling_9am = project_trendline(ceiling_anchors[0][0], ceiling_anchors[0][1], ceiling_anchors[1][0], ceiling_anchors[1][1], target_time)
        ceiling_now = project_trendline(ceiling_anchors[0][0], ceiling_anchors[0][1], ceiling_anchors[1][0], ceiling_anchors[1][1], now)
    else:
        ceiling_9am = ceiling_now = current_price + 20
    
    if len(floor_anchors) >= 2:
        floor_9am = project_trendline(floor_anchors[0][0], floor_anchors[0][1], floor_anchors[1][0], floor_anchors[1][1], target_time)
        floor_now = project_trendline(floor_anchors[0][0], floor_anchors[0][1], floor_anchors[1][0], floor_anchors[1][1], now)
    else:
        floor_9am = floor_now = current_price - 20
    
    dist_to_ceiling = ceiling_now - current_price
    dist_to_floor = current_price - floor_now
    range_size = ceiling_now - floor_now
    position_pct = ((current_price - floor_now) / range_size * 100) if range_size > 0 else 50
    
    if current_price > ceiling_now:
        signal, score, reason = "BULLISH_BREAKOUT", 30, f"Above ceiling by {current_price - ceiling_now:.2f}"
    elif current_price < floor_now:
        signal, score, reason = "BEARISH_BREAKDOWN", 30, f"Below floor by {floor_now - current_price:.2f}"
    elif position_pct > 70:
        signal, score, reason = "BULLISH_LEAN", 20, f"Upper 30% ({position_pct:.0f}%)"
    elif position_pct < 30:
        signal, score, reason = "BEARISH_LEAN", 20, f"Lower 30% ({position_pct:.0f}%)"
    else:
        signal, score, reason = "NEUTRAL", 10, f"Mid-range ({position_pct:.0f}%)"
    
    return {"signal": signal, "reason": reason, "score": score, "ceiling_9am": ceiling_9am, "floor_9am": floor_9am, "ceiling_now": ceiling_now, "floor_now": floor_now, "dist_to_ceiling": round(dist_to_ceiling, 2), "dist_to_floor": round(dist_to_floor, 2), "range": round(range_size, 2), "position_pct": round(position_pct, 1)}

# ═══════════════════════════════════════════════════════════════════════════════
# PILLAR 3: VIX ZONE
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_vix_zone(vix_current: float, vix_overnight_high: float, vix_overnight_low: float) -> Dict:
    zone_name = "NORMAL"
    for name, (low, high) in VIX_ZONES.items():
        if low <= vix_current < high:
            zone_name = name
            break
    
    vix_range = vix_overnight_high - vix_overnight_low
    vix_position = (vix_current - vix_overnight_low) / vix_range * 100 if vix_range > 0 else 50
    
    if vix_current > vix_overnight_high:
        springboard, signal, score, reason = "ABOVE_CEILING", "CALLS", 20, "VIX above overnight high"
    elif vix_current < vix_overnight_low:
        springboard, signal, score, reason = "BELOW_FLOOR", "PUTS", 20, "VIX below overnight low"
    elif vix_position > 75:
        springboard, signal, score, reason = "NEAR_CEILING", "CALLS", 15, f"VIX near ceiling ({vix_position:.0f}%)"
    elif vix_position < 25:
        springboard, signal, score, reason = "NEAR_FLOOR", "PUTS", 15, f"VIX near floor ({vix_position:.0f}%)"
    else:
        springboard, signal, score, reason = "MID_RANGE", "WAIT", 5, f"VIX mid-range ({vix_position:.0f}%)"
    
    return {"signal": signal, "reason": reason, "score": score, "zone": zone_name, "springboard": springboard, "current": vix_current, "overnight_high": vix_overnight_high, "overnight_low": vix_overnight_low, "position_pct": round(vix_position, 1)}

# ═══════════════════════════════════════════════════════════════════════════════
# 30-MIN MOMENTUM SUITE
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else 50

def calculate_macd(prices: pd.Series) -> Dict:
    ema_12 = prices.ewm(span=12, adjust=False).mean()
    ema_26 = prices.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    hist_current = histogram.iloc[-1]
    hist_prev = histogram.iloc[-2] if len(histogram) > 1 else 0
    
    if hist_current > 0:
        direction, expanding = "BULLISH", hist_current > hist_prev
    elif hist_current < 0:
        direction, expanding = "BEARISH", hist_current < hist_prev
    else:
        direction, expanding = "NEUTRAL", False
    
    return {"macd": round(macd_line.iloc[-1], 4), "signal": round(signal_line.iloc[-1], 4), "histogram": round(hist_current, 4), "direction": direction, "expanding": expanding}

def analyze_price_structure(candles: pd.DataFrame) -> str:
    if len(candles) < 4:
        return "NEUTRAL"
    highs, lows = candles['High'].tail(4).values, candles['Low'].tail(4).values
    hh = highs[-1] > highs[-2] and highs[-2] > highs[-3]
    hl = lows[-1] > lows[-2] and lows[-2] > lows[-3]
    lh = highs[-1] < highs[-2] and highs[-2] < highs[-3]
    ll = lows[-1] < lows[-2] and lows[-2] < lows[-3]
    if hh and hl:
        return "BULLISH"
    elif lh and ll:
        return "BEARISH"
    return "NEUTRAL"

def calculate_30min_momentum(es_candles: Optional[pd.DataFrame]) -> Dict:
    if es_candles is None or len(es_candles) < 26:
        return {"signal": "NEUTRAL", "reason": "Insufficient data", "score": 0, "rsi": 50, "macd": {}, "structure": "NEUTRAL"}
    
    close = es_candles['Close']
    rsi = calculate_rsi(close)
    macd = calculate_macd(close)
    structure = analyze_price_structure(es_candles)
    
    bullish_count = bearish_count = 0
    if rsi > 55: bullish_count += 1
    elif rsi < 45: bearish_count += 1
    if macd["direction"] == "BULLISH" and macd["expanding"]: bullish_count += 1
    elif macd["direction"] == "BEARISH" and macd["expanding"]: bearish_count += 1
    if structure == "BULLISH": bullish_count += 1
    elif structure == "BEARISH": bearish_count += 1
    
    if bullish_count >= 2:
        signal, score, reason = "BULLISH", 15, f"RSI {rsi}, MACD {macd['direction']}, {structure}"
    elif bearish_count >= 2:
        signal, score, reason = "BEARISH", 15, f"RSI {rsi}, MACD {macd['direction']}, {structure}"
    else:
        signal, score, reason = "NEUTRAL", 5, "Mixed signals"
    
    return {"signal": signal, "reason": reason, "score": score, "rsi": rsi, "macd": macd, "structure": structure}

# ═══════════════════════════════════════════════════════════════════════════════
# 5-MIN REVERSAL DETECTOR (NEW IN V4)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_5min_reversal(candles_5m: Optional[pd.DataFrame], direction: str, trigger_price: float, current_price: float) -> Dict:
    if candles_5m is None or len(candles_5m) < 5:
        return {"status": "NO_DATA", "signal": "WAIT", "message": "Insufficient 5-min data", "ready": False, "rsi": None, "macd_direction": None, "candle_pattern": None}
    
    close = candles_5m['Close']
    rsi_5m = calculate_rsi(close, period=14)
    macd_5m = calculate_macd(close)
    last_candle = candles_5m.iloc[-1]
    is_green = last_candle['Close'] > last_candle['Open']
    is_red = last_candle['Close'] < last_candle['Open']
    
    if direction == "LONG":
        at_level = current_price <= trigger_price * 1.002
        rsi_oversold = rsi_5m < 35
        if at_level and is_green and rsi_oversold:
            status, signal, ready, message = "REVERSAL_CONFIRMED", "BUY_CALLS", True, "✅ Bullish reversal at floor - ENTER CALLS"
        elif at_level:
            status, signal, ready, message = "AT_LEVEL", "WATCH", False, "At floor - waiting for green candle"
        elif current_price < trigger_price:
            status, signal, ready, message = "BELOW_LEVEL", "CAUTION", False, f"Below floor by {trigger_price - current_price:.2f} pts"
        else:
            dist = current_price - trigger_price
            status, signal, ready, message = "APPROACHING", "WAIT", False, f"Waiting for pullback ({dist:.2f} pts to floor)"
    elif direction == "SHORT":
        at_level = current_price >= trigger_price * 0.998
        rsi_overbought = rsi_5m > 65
        if at_level and is_red and rsi_overbought:
            status, signal, ready, message = "REVERSAL_CONFIRMED", "BUY_PUTS", True, "✅ Bearish reversal at ceiling - ENTER PUTS"
        elif at_level:
            status, signal, ready, message = "AT_LEVEL", "WATCH", False, "At ceiling - waiting for red candle"
        elif current_price > trigger_price:
            status, signal, ready, message = "ABOVE_LEVEL", "CAUTION", False, f"Above ceiling by {current_price - trigger_price:.2f} pts"
        else:
            dist = trigger_price - current_price
            status, signal, ready, message = "APPROACHING", "WAIT", False, f"Waiting for rally ({dist:.2f} pts to ceiling)"
    else:
        status, signal, ready, message = "NO_DIRECTION", "WAIT", False, "No directional bias"
    
    return {"status": status, "signal": signal, "message": message, "ready": ready, "rsi": rsi_5m, "macd_direction": macd_5m["direction"], "candle_pattern": "GREEN" if is_green else "RED" if is_red else "DOJI"}

# ═══════════════════════════════════════════════════════════════════════════════
# CONE RAILS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_cone_rails(prior_high: float, high_time: datetime, prior_low: float, low_time: datetime, prior_close: float, close_time: datetime, target_time: datetime) -> Dict:
    cones = {}
    for name, price, anchor_time in [("HIGH", prior_high, high_time), ("LOW", prior_low, low_time), ("CLOSE", prior_close, close_time)]:
        blocks = count_30min_blocks(anchor_time, target_time)
        expansion = CONE_SLOPE * blocks
        cones[name] = {"anchor": price, "anchor_time": anchor_time.strftime("%I:%M %p") if anchor_time else "N/A", "asc": round(price + expansion, 2), "desc": round(price - expansion, 2), "blocks": blocks, "expansion": round(expansion, 2)}
    return cones

def calculate_cone_confluence(cones: Dict, current_price: float) -> Dict:
    confluence_points = []
    threshold = 5
    for name, cone in cones.items():
        for rail_type, rail_price in [("ASC", cone["asc"]), ("DESC", cone["desc"])]:
            distance = abs(current_price - rail_price)
            if distance <= threshold:
                confluence_points.append({"cone": name, "rail": rail_type, "price": rail_price, "distance": round(distance, 2)})
    return {"confluences": confluence_points, "count": len(confluence_points), "score": min(10, len(confluence_points) * 5)}

# ═══════════════════════════════════════════════════════════════════════════════
# STRIKE SELECTION & STOPS
# ═══════════════════════════════════════════════════════════════════════════════

def select_strike(entry_price: float, target_price: float, direction: str, method: str = "gamma_optimal") -> Dict:
    expected_move = abs(target_price - entry_price)
    if direction == "LONG":
        if method == "gamma_optimal": raw_strike = entry_price - (expected_move * 0.35)
        elif method == "conservative": raw_strike = entry_price - 15
        elif method == "aggressive": raw_strike = entry_price - 5
        else: raw_strike = entry_price - 10
        strike = round(raw_strike / 5) * 5
        option_type = "CALL"
        otm_distance = entry_price - strike
    else:
        if method == "gamma_optimal": raw_strike = entry_price + (expected_move * 0.35)
        elif method == "conservative": raw_strike = entry_price + 15
        elif method == "aggressive": raw_strike = entry_price + 5
        else: raw_strike = entry_price + 10
        strike = round(raw_strike / 5) * 5
        option_type = "PUT"
        otm_distance = strike - entry_price
    return {"strike": int(strike), "option_type": option_type, "otm_distance": round(otm_distance, 2), "method": method, "expected_move": round(expected_move, 2)}

def calculate_dynamic_stop(es_candles: Optional[pd.DataFrame], premium: float, vix_current: float) -> Dict:
    if es_candles is None or len(es_candles) < 14 or premium <= 0:
        return {"stop_pct": 50, "stop_price": round(premium * 0.5, 2), "atr": None, "vix_multiplier": 1.0}
    high, low, close = es_candles['High'], es_candles['Low'], es_candles['Close']
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean().iloc[-1]
    vix_mult = 0.85 if vix_current < 15 else 1.0 if vix_current < 20 else 1.15 if vix_current < 25 else 1.3
    stop_amount = atr * 0.5 * 0.30 * vix_mult
    stop_pct = max(35, min(65, (stop_amount / premium) * 100))
    return {"stop_pct": round(stop_pct, 1), "stop_price": round(premium * (1 - stop_pct / 100), 2), "atr": round(atr, 2), "vix_multiplier": vix_mult}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE SCORING
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_confidence(ma_bias: Dict, structure: Dict, vix_zone: Dict, momentum: Dict, cone_confluence: Dict) -> Dict:
    scores = {"MA Bias": ma_bias.get("score", 0), "Structure": structure.get("score", 0), "VIX Zone": vix_zone.get("score", 0), "Momentum": momentum.get("score", 0), "Cone Confluence": cone_confluence.get("score", 0)}
    total = sum(scores.values())
    
    if total >= 85: grade, action = "A+", "STRONG_ENTRY"
    elif total >= 75: grade, action = "HIGH", "ENTRY"
    elif total >= 60: grade, action = "MEDIUM", "CAUTIOUS"
    elif total >= 45: grade, action = "LOW", "WAIT"
    else: grade, action = "NO_TRADE", "AVOID"
    
    calls_signals = puts_signals = 0
    for result in [ma_bias, structure, vix_zone, momentum]:
        sig = result.get("signal", "").upper()
        if sig in ["LONG", "BULLISH", "BULLISH_LEAN", "BULLISH_BREAKOUT", "CALLS"]: calls_signals += 1
        elif sig in ["SHORT", "BEARISH", "BEARISH_LEAN", "BEARISH_BREAKDOWN", "PUTS"]: puts_signals += 1
    
    if calls_signals > puts_signals and total >= 60: final_signal, direction = "CALLS", "LONG"
    elif puts_signals > calls_signals and total >= 60: final_signal, direction = "PUTS", "SHORT"
    else: final_signal, direction = "WAIT", "NONE"
    
    return {"total": total, "grade": grade, "action": action, "breakdown": scores, "final_signal": final_signal, "direction": direction, "calls_signals": calls_signals, "puts_signals": puts_signals}

# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

def save_inputs(inputs: Dict):
    try:
        serializable = {}
        for k, v in inputs.items():
            if isinstance(v, datetime): serializable[k] = v.isoformat()
            elif isinstance(v, date): serializable[k] = v.isoformat()
            elif isinstance(v, time): serializable[k] = v.strftime("%H:%M")
            else: serializable[k] = v
        with open(SAVE_FILE, 'w') as f:
            json.dump(serializable, f, indent=2)
    except Exception as e:
        st.warning(f"Save error: {e}")

def load_inputs() -> Dict:
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.warning(f"Load error: {e}")
    return {}

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

def render_sidebar() -> Dict:
    saved = load_inputs()
    
    with st.sidebar:
        st.markdown("## ⚙️ SPX Prophet V4")
        trading_date = st.date_input("📅 Trading Date", value=date.today())
        
        st.markdown("---")
        st.markdown("### 📈 SPX Price")
        use_manual_spx = st.checkbox("Manual SPX", value=False)
        spx_price = st.number_input("SPX Price", value=float(saved.get("spx_price", 6050.0)), step=1.0) if use_manual_spx else None
        
        st.markdown("---")
        st.markdown("### 📊 Pillar 1: MA Bias")
        ma_override = st.selectbox("Override MA Bias", ["AUTO", "LONG", "SHORT", "NEUTRAL"], index=0)
        
        st.markdown("---")
        st.markdown("### 📐 Pillar 2: Structure")
        
        # Time options for dropdowns (30-min intervals)
        HOUR_OPTIONS = list(range(0, 24))
        MINUTE_OPTIONS = [0, 30]
        
        def format_time_display(h, m):
            """Format hour:minute for display"""
            period = "AM" if h < 12 else "PM"
            display_h = h if h <= 12 else h - 12
            if display_h == 0: display_h = 12
            return f"{display_h}:{m:02d} {period}"
        
        st.markdown("**CEILING Anchors (Overnight Highs)**")
        c1, c2, c3 = st.columns([2, 1, 1])
        ceil1_price = c1.number_input("C1 Price", value=float(saved.get("ceil1_price", 6065.0)), step=0.5, key="c1p")
        ceil1_hour = c2.selectbox("Hr", HOUR_OPTIONS, index=int(saved.get("ceil1_hour", 22)), key="c1h")
        ceil1_min = c3.selectbox("Min", MINUTE_OPTIONS, index=MINUTE_OPTIONS.index(int(saved.get("ceil1_min", 30))), key="c1m")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        ceil2_price = c1.number_input("C2 Price", value=float(saved.get("ceil2_price", 6060.0)), step=0.5, key="c2p")
        ceil2_hour = c2.selectbox("Hr", HOUR_OPTIONS, index=int(saved.get("ceil2_hour", 2)), key="c2h")
        ceil2_min = c3.selectbox("Min", MINUTE_OPTIONS, index=MINUTE_OPTIONS.index(int(saved.get("ceil2_min", 0))), key="c2m")
        
        st.markdown("**FLOOR Anchors (Overnight Lows)**")
        c1, c2, c3 = st.columns([2, 1, 1])
        floor1_price = c1.number_input("F1 Price", value=float(saved.get("floor1_price", 6035.0)), step=0.5, key="f1p")
        floor1_hour = c2.selectbox("Hr", HOUR_OPTIONS, index=int(saved.get("floor1_hour", 20)), key="f1h")
        floor1_min = c3.selectbox("Min", MINUTE_OPTIONS, index=MINUTE_OPTIONS.index(int(saved.get("floor1_min", 0))), key="f1m")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        floor2_price = c1.number_input("F2 Price", value=float(saved.get("floor2_price", 6040.0)), step=0.5, key="f2p")
        floor2_hour = c2.selectbox("Hr", HOUR_OPTIONS, index=int(saved.get("floor2_hour", 5)), key="f2h")
        floor2_min = c3.selectbox("Min", MINUTE_OPTIONS, index=MINUTE_OPTIONS.index(int(saved.get("floor2_min", 30))), key="f2m")
        
        st.markdown("---")
        st.markdown("### ⚡ Pillar 3: VIX Zone")
        vix_overnight_high = st.number_input("VIX O/N High", value=float(saved.get("vix_overnight_high", 18.0)), step=0.1)
        vix_overnight_low = st.number_input("VIX O/N Low", value=float(saved.get("vix_overnight_low", 15.0)), step=0.1)
        use_manual_vix = st.checkbox("Manual VIX", value=False)
        vix_current = st.number_input("Current VIX", value=float(saved.get("vix_current", 16.5)), step=0.1) if use_manual_vix else None
        
        st.markdown("---")
        st.markdown("### 📊 Prior Day (Cones)")
        c1, c2, c3 = st.columns([2, 1, 1])
        prior_high = c1.number_input("Prior High", value=float(saved.get("prior_high", 6070.0)), step=0.5)
        prior_high_hour = c2.selectbox("Hr", HOUR_OPTIONS, index=int(saved.get("prior_high_hour", 10)), key="phh")
        prior_high_min = c3.selectbox("Min", MINUTE_OPTIONS, index=MINUTE_OPTIONS.index(int(saved.get("prior_high_min", 0))), key="phm")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        prior_low = c1.number_input("Prior Low", value=float(saved.get("prior_low", 6020.0)), step=0.5)
        prior_low_hour = c2.selectbox("Hr", HOUR_OPTIONS, index=int(saved.get("prior_low_hour", 14)), key="plh")
        prior_low_min = c3.selectbox("Min", MINUTE_OPTIONS, index=MINUTE_OPTIONS.index(int(saved.get("prior_low_min", 0))), key="plm")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        prior_close = c1.number_input("Prior Close", value=float(saved.get("prior_close", 6050.0)), step=0.5)
        prior_close_hour = c2.selectbox("Hr", HOUR_OPTIONS, index=int(saved.get("prior_close_hour", 15)), key="pch")
        prior_close_min = c3.selectbox("Min", MINUTE_OPTIONS, index=MINUTE_OPTIONS.index(int(saved.get("prior_close_min", 0))), key="pcm")
        
        st.markdown("---")
        st.markdown("### 🎯 Strike Selection")
        strike_method = st.selectbox("Method", ["gamma_optimal", "conservative", "aggressive", "round_number"], index=0)
        
        st.markdown("---")
        st.markdown("### 🔄 Auto-Refresh")
        auto_refresh = st.checkbox("Enable Auto-Refresh", value=False)
        refresh_interval = st.slider("Interval (sec)", 15, 120, 30) if auto_refresh else 30
        
        st.markdown("---")
        show_debug = st.checkbox("Show Debug Panel", value=False)
        
        if st.button("💾 Save Inputs", use_container_width=True):
            save_inputs({"spx_price": spx_price, "ceil1_price": ceil1_price, "ceil1_hour": ceil1_hour, "ceil1_min": ceil1_min, "ceil2_price": ceil2_price, "ceil2_hour": ceil2_hour, "ceil2_min": ceil2_min, "floor1_price": floor1_price, "floor1_hour": floor1_hour, "floor1_min": floor1_min, "floor2_price": floor2_price, "floor2_hour": floor2_hour, "floor2_min": floor2_min, "vix_overnight_high": vix_overnight_high, "vix_overnight_low": vix_overnight_low, "vix_current": vix_current, "prior_high": prior_high, "prior_high_hour": prior_high_hour, "prior_high_min": prior_high_min, "prior_low": prior_low, "prior_low_hour": prior_low_hour, "prior_low_min": prior_low_min, "prior_close": prior_close, "prior_close_hour": prior_close_hour, "prior_close_min": prior_close_min})
            st.success("✅ Saved!")
    
    prev_day = trading_date - timedelta(days=1)
    def make_anchor_time(hour, minute, base_date):
        anchor_date = base_date if hour >= 17 else trading_date
        return CT.localize(datetime.combine(anchor_date, time(hour, minute)))
    
    ceiling_anchors = [(ceil1_price, make_anchor_time(ceil1_hour, ceil1_min, prev_day)), (ceil2_price, make_anchor_time(ceil2_hour, ceil2_min, prev_day))]
    floor_anchors = [(floor1_price, make_anchor_time(floor1_hour, floor1_min, prev_day)), (floor2_price, make_anchor_time(floor2_hour, floor2_min, prev_day))]
    prior_high_time = CT.localize(datetime.combine(prev_day, time(prior_high_hour, prior_high_min)))
    prior_low_time = CT.localize(datetime.combine(prev_day, time(prior_low_hour, prior_low_min)))
    prior_close_time = CT.localize(datetime.combine(prev_day, time(prior_close_hour, prior_close_min)))
    
    return {"trading_date": trading_date, "spx_price": spx_price, "ma_override": ma_override, "ceiling_anchors": ceiling_anchors, "floor_anchors": floor_anchors, "vix_overnight_high": vix_overnight_high, "vix_overnight_low": vix_overnight_low, "vix_current": vix_current, "prior_high": prior_high, "prior_high_time": prior_high_time, "prior_low": prior_low, "prior_low_time": prior_low_time, "prior_close": prior_close, "prior_close_time": prior_close_time, "strike_method": strike_method, "auto_refresh": auto_refresh, "refresh_interval": refresh_interval, "show_debug": show_debug}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    st.markdown(STYLES, unsafe_allow_html=True)
    inputs = render_sidebar()
    now_ct = get_now_ct()
    target_9am = CT.localize(datetime.combine(inputs["trading_date"], time(9, 0)))
    
    with st.spinner("Loading market data..."):
        # Track data sources
        data_sources = {}
        
        # SPX Price
        if inputs["spx_price"]:
            current_price = inputs["spx_price"]
            data_sources["spx"] = "MANUAL"
        else:
            fetched_spx = fetch_spx_price()
            if fetched_spx:
                current_price = fetched_spx
                data_sources["spx"] = "LIVE"
            else:
                current_price = None  # Will show error
                data_sources["spx"] = "FAILED"
        
        # VIX
        if inputs["vix_current"]:
            vix_current = inputs["vix_current"]
            data_sources["vix"] = "MANUAL"
        else:
            fetched_vix = fetch_vix_price()
            if fetched_vix:
                vix_current = fetched_vix
                data_sources["vix"] = "LIVE"
            else:
                vix_current = None
                data_sources["vix"] = "FAILED"
        
        # ES Candles
        es_candles = fetch_es_30min_candles()
        data_sources["es"] = "LIVE" if es_candles is not None and len(es_candles) >= 50 else "PARTIAL" if es_candles is not None else "FAILED"
        
        # SPX 5-min
        spx_5min = fetch_spx_5min_candles()
        data_sources["5min"] = "LIVE" if spx_5min is not None else "FAILED"
    
    # CRITICAL DATA CHECK - Stop if SPX or VIX missing
    if current_price is None or vix_current is None:
        st.error("❌ **CRITICAL DATA MISSING** - Cannot proceed without SPX price and VIX. Enable Manual Input in sidebar.")
        st.stop()
    
    # HERO HEADER
    st.markdown(f'<div class="hero-header"><div class="hero-title">🔮 SPX PROPHET V4</div><div class="hero-subtitle">Institutional 0DTE Analytics | 3-Pillar Methodology</div><div class="hero-price">{current_price:,.2f}</div><div class="hero-time">{now_ct.strftime("%I:%M:%S %p CT")} | {inputs["trading_date"].strftime("%A, %B %d, %Y")}</div></div>', unsafe_allow_html=True)
    
    # DATA STATUS BAR (shows source of each data point)
    def status_icon(status):
        return "🟢" if status == "LIVE" else "🟡" if status == "MANUAL" else "🟠" if status == "PARTIAL" else "🔴"
    
    es_count = len(es_candles) if es_candles is not None else 0
    data_msg = f"SPX {status_icon(data_sources['spx'])} {data_sources['spx']} | ES {status_icon(data_sources['es'])} ({es_count}) | VIX {status_icon(data_sources['vix'])} {data_sources['vix']}"
    
    if data_sources["es"] in ["FAILED", "PARTIAL"]:
        data_msg += " | ⚠️ Set MA Bias manually"
    
    st.markdown(f'<div style="text-align:center;font-size:11px;color:var(--text-secondary);margin-bottom:16px;padding:8px;background:rgba(255,255,255,0.02);border-radius:8px">{data_msg}</div>', unsafe_allow_html=True)
    
    # ANALYSIS
    ma_bias = {"signal": inputs["ma_override"], "reason": "Manual override", "score": 25 if inputs["ma_override"] != "NEUTRAL" else 0, "ema_50": None, "sma_200": None, "diff_pct": None} if inputs["ma_override"] != "AUTO" else calculate_ma_bias(es_candles)
    structure = calculate_day_structure(inputs["ceiling_anchors"], inputs["floor_anchors"], target_9am, current_price)
    vix_zone = calculate_vix_zone(vix_current, inputs["vix_overnight_high"], inputs["vix_overnight_low"])
    momentum = calculate_30min_momentum(es_candles)
    cones = calculate_cone_rails(inputs["prior_high"], inputs["prior_high_time"], inputs["prior_low"], inputs["prior_low_time"], inputs["prior_close"], inputs["prior_close_time"], target_9am)
    cone_confluence = calculate_cone_confluence(cones, current_price)
    confidence = calculate_confidence(ma_bias, structure, vix_zone, momentum, cone_confluence)
    
    # ENTRY TRIGGER - ONLY RELEVANT DURING INSTITUTIONAL WINDOW (8:30-11:30 AM CT)
    now_time = now_ct.time()
    entry_window_start = time(8, 30)
    entry_window_end = time(11, 30)
    in_entry_window = entry_window_start <= now_time <= entry_window_end
    
    # Structure at 9 AM (planned entry) - this is what matters
    trigger_price_9am = structure["floor_9am"] if confidence["direction"] == "LONG" else structure["ceiling_9am"] if confidence["direction"] == "SHORT" else current_price
    target_price_9am = structure["ceiling_9am"] if confidence["direction"] == "LONG" else structure["floor_9am"] if confidence["direction"] == "SHORT" else current_price
    
    # Strike based on 9 AM structure
    strike_info = select_strike(trigger_price_9am, target_price_9am, confidence["direction"], inputs["strike_method"])
    
    # Reversal detection only matters during entry window
    if in_entry_window:
        reversal = detect_5min_reversal(spx_5min, confidence["direction"], trigger_price_9am, current_price)
    else:
        reversal = {"status": "OUTSIDE_WINDOW", "signal": "WAIT", "message": "Entry window: 8:30-11:30 AM CT", "ready": False, "rsi": None, "macd_direction": None, "candle_pattern": None}
    
    stop_info = calculate_dynamic_stop(es_candles, 5.0, vix_current)
    
    # ENTRY TRIGGER ALERT - Shows 9 AM planned entry
    if not in_entry_window:
        # Outside entry window - show countdown/preview
        alert_class = "wait"
        action_class = "wait"
        if confidence["direction"] == "LONG":
            action_text = f"📅 9 AM PLAN: Buy {strike_info['strike']} CALL at {trigger_price_9am:,.2f}"
        elif confidence["direction"] == "SHORT":
            action_text = f"📅 9 AM PLAN: Buy {strike_info['strike']} PUT at {trigger_price_9am:,.2f}"
        else:
            action_text = "⏸️ NO SETUP - Awaiting direction"
        details_text = f"Entry Window: 8:30-11:30 AM CT | Floor: {structure['floor_9am']:,.2f} | Ceiling: {structure['ceiling_9am']:,.2f}"
    elif reversal["ready"] and confidence["total"] >= 60:
        alert_class = "" if confidence["direction"] == "LONG" else "puts"
        action_class = "buy"
        action_text = f"🟢 BUY NOW: {strike_info['strike']} {strike_info['option_type']}"
        details_text = f"Trigger: {trigger_price_9am:,.2f} | Current: {current_price:,.2f} | Distance: {abs(current_price - trigger_price_9am):.2f} pts"
    elif reversal["status"] == "AT_LEVEL":
        alert_class = "" if confidence["direction"] == "LONG" else "puts"
        action_class = "wait"
        action_text = "⏳ AT LEVEL - WATCH FOR 5m REVERSAL"
        details_text = f"Trigger: {trigger_price_9am:,.2f} | Current: {current_price:,.2f} | {reversal['message']}"
    else:
        alert_class = "wait"
        action_class = "wait"
        if confidence["direction"] == "LONG":
            action_text = f"⏳ WAITING: Need pullback to {trigger_price_9am:,.2f}"
        elif confidence["direction"] == "SHORT":
            action_text = f"⏳ WAITING: Need rally to {trigger_price_9am:,.2f}"
        else:
            action_text = "⏸️ NO DIRECTIONAL BIAS"
        details_text = f"Floor: {structure['floor_9am']:,.2f} | Ceiling: {structure['ceiling_9am']:,.2f} | Current: {current_price:,.2f}"
    
    st.markdown(f'<div class="entry-alert {alert_class}"><div class="alert-title">ENTRY TRIGGER {"🟢 LIVE" if in_entry_window else "📋 PREVIEW"}</div><div class="alert-action {action_class}">{action_text}</div><div class="alert-details">{details_text}</div></div>', unsafe_allow_html=True)
    
    # THREE PILLARS
    st.markdown("### Three Pillars")
    p1, p2, p3 = st.columns(3)
    
    with p1:
        ma_class = "calls" if ma_bias["signal"] == "LONG" else "puts" if ma_bias["signal"] == "SHORT" else "neutral"
        data_status = ma_bias.get("data_status", "UNKNOWN")
        status_color = "var(--green)" if data_status == "FULL" else "var(--amber)" if data_status == "PARTIAL" else "var(--red)"
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon blue">📊</div><div><div class="card-title">Pillar 1: MA Bias</div><div class="card-subtitle">ES 30-min | <span style="color:{status_color}">{ma_bias.get("candle_count", 0)} candles</span></div></div></div><span class="signal-badge {ma_class}">{ma_bias["signal"]}</span><div class="pillar-item" style="margin-top:12px"><span class="pillar-name">50 EMA</span><span class="pillar-value">{ma_bias.get("ema_50") or "—"}</span></div><div class="pillar-item"><span class="pillar-name">200 SMA</span><span class="pillar-value">{ma_bias.get("sma_200") or "—"}</span></div><div class="pillar-item"><span class="pillar-name">Diff %</span><span class="pillar-value">{f"{ma_bias.get('diff_pct')}%" if ma_bias.get("diff_pct") else "—"}</span></div><div class="pillar-item"><span class="pillar-name">Score</span><span class="pillar-value">{ma_bias["score"]}/25</span></div></div>', unsafe_allow_html=True)
    
    with p2:
        struct_class = "calls" if "BULLISH" in structure["signal"] else "puts" if "BEARISH" in structure["signal"] else "neutral"
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon amber">📐</div><div><div class="card-title">Pillar 2: Structure</div><div class="card-subtitle">9 AM CT Entry Levels</div></div></div><span class="signal-badge {struct_class}">{structure["signal"]}</span><div class="pillar-item" style="margin-top:12px"><span class="pillar-name">Ceiling @ 9 AM</span><span class="pillar-value table-down">{structure["ceiling_9am"]:,.2f}</span></div><div class="pillar-item"><span class="pillar-name">Floor @ 9 AM</span><span class="pillar-value table-up">{structure["floor_9am"]:,.2f}</span></div><div class="pillar-item"><span class="pillar-name">Range</span><span class="pillar-value">{structure["ceiling_9am"] - structure["floor_9am"]:.1f} pts</span></div><div class="pillar-item"><span class="pillar-name">Current Price</span><span class="pillar-value">{current_price:,.2f}</span></div><div class="pillar-item"><span class="pillar-name">Score</span><span class="pillar-value">{structure["score"]}/30</span></div></div>', unsafe_allow_html=True)
    
    with p3:
        vix_class = "calls" if vix_zone["signal"] == "CALLS" else "puts" if vix_zone["signal"] == "PUTS" else "neutral"
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon green">⚡</div><div><div class="card-title">Pillar 3: VIX Zone</div><div class="card-subtitle">{vix_zone["zone"]}</div></div></div><span class="signal-badge {vix_class}">{vix_zone["signal"]}</span><div class="pillar-item" style="margin-top:12px"><span class="pillar-name">Current VIX</span><span class="pillar-value">{vix_zone["current"]:.2f}</span></div><div class="pillar-item"><span class="pillar-name">O/N High</span><span class="pillar-value">{vix_zone["overnight_high"]:.2f}</span></div><div class="pillar-item"><span class="pillar-name">O/N Low</span><span class="pillar-value">{vix_zone["overnight_low"]:.2f}</span></div><div class="pillar-item"><span class="pillar-name">Springboard</span><span class="pillar-value">{vix_zone["springboard"]}</span></div><div class="pillar-item"><span class="pillar-name">Score</span><span class="pillar-value">{vix_zone["score"]}/20</span></div></div>', unsafe_allow_html=True)
    
    # CONFIDENCE & REVERSAL
    c1, c2 = st.columns(2)
    with c1:
        fill_class = "a-plus" if confidence["grade"] == "A+" else "high" if confidence["grade"] == "HIGH" else "medium" if confidence["grade"] == "MEDIUM" else "low"
        breakdown_html = "".join([f'<div class="pillar-item"><span class="pillar-name">{name}</span><span class="pillar-value">+{score}</span></div>' for name, score in confidence["breakdown"].items()])
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon purple">📋</div><div><div class="card-title">Confidence Score</div><div class="card-subtitle">{confidence["grade"]} Setup</div></div></div><div class="confidence-container"><div class="confidence-bar"><div class="confidence-fill {fill_class}" style="width:{confidence["total"]}%"></div></div><div class="confidence-label"><span class="confidence-score">{confidence["total"]}/100</span><span style="color:{"var(--green)" if confidence["total"] >= 75 else "var(--amber)" if confidence["total"] >= 60 else "var(--red)"}">{confidence["grade"]}</span></div></div>{breakdown_html}</div>', unsafe_allow_html=True)
    
    with c2:
        if in_entry_window:
            rev_class = "bullish" if reversal["signal"] in ["BUY_CALLS", "WATCH"] and confidence["direction"] == "LONG" else "bearish" if reversal["signal"] in ["BUY_PUTS", "WATCH"] and confidence["direction"] == "SHORT" else "neutral"
            window_status = "🟢 ENTRY WINDOW ACTIVE"
        else:
            rev_class = "neutral"
            window_status = "⏳ Outside Entry Window"
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon cyan">🔄</div><div><div class="card-title">5-Min Reversal</div><div class="card-subtitle">{window_status}</div></div></div><div class="reversal-box"><div class="reversal-status {rev_class}">{reversal["message"]}</div></div><div class="pillar-item" style="margin-top:12px"><span class="pillar-name">5m RSI</span><span class="pillar-value">{reversal.get("rsi") or "—"}</span></div><div class="pillar-item"><span class="pillar-name">5m MACD</span><span class="pillar-value">{reversal.get("macd_direction") or "—"}</span></div><div class="pillar-item"><span class="pillar-name">Last Candle</span><span class="pillar-value">{reversal.get("candle_pattern") or "—"}</span></div></div>', unsafe_allow_html=True)
    
    # STRIKE & MOMENTUM
    s1, s2 = st.columns(2)
    with s1:
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon purple">🎯</div><div><div class="card-title">Strike Selection</div><div class="card-subtitle">{strike_info["method"].replace("_", " ").title()} @ 9 AM Entry</div></div></div><div class="metric-value purple" style="font-size:32px">{strike_info["strike"]} {strike_info["option_type"]}</div><div class="pillar-item" style="margin-top:12px"><span class="pillar-name">Entry Price (9 AM)</span><span class="pillar-value">{trigger_price_9am:,.2f}</span></div><div class="pillar-item"><span class="pillar-name">OTM Distance</span><span class="pillar-value">{strike_info["otm_distance"]:.1f} pts</span></div><div class="pillar-item"><span class="pillar-name">Target</span><span class="pillar-value">{target_price_9am:,.2f}</span></div><div class="pillar-item"><span class="pillar-name">Expected Move</span><span class="pillar-value">{strike_info["expected_move"]:.1f} pts</span></div><div class="pillar-item"><span class="pillar-name">Stop %</span><span class="pillar-value">{stop_info["stop_pct"]:.0f}%</span></div></div>', unsafe_allow_html=True)
    
    with s2:
        mom_class = "calls" if momentum["signal"] == "BULLISH" else "puts" if momentum["signal"] == "BEARISH" else "neutral"
        macd_info = momentum.get("macd", {})
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon blue">📈</div><div><div class="card-title">30-Min Momentum</div><div class="card-subtitle">{momentum["signal"]}</div></div></div><span class="signal-badge {mom_class}">{momentum["signal"]}</span><div class="pillar-item" style="margin-top:12px"><span class="pillar-name">RSI (14)</span><span class="pillar-value">{momentum.get("rsi", "N/A")}</span></div><div class="pillar-item"><span class="pillar-name">MACD</span><span class="pillar-value">{macd_info.get("direction", "N/A")} {"📈" if macd_info.get("expanding") else "📉"}</span></div><div class="pillar-item"><span class="pillar-name">Structure</span><span class="pillar-value">{momentum.get("structure", "N/A")}</span></div><div class="pillar-item"><span class="pillar-name">Score</span><span class="pillar-value">{momentum["score"]}/15</span></div></div>', unsafe_allow_html=True)
    
    # CONE RAILS
    st.markdown("### Cone Rails")
    cone_rows = "".join([f'<tr><td>{name}</td><td>{cone["anchor"]:,.2f}</td><td>{cone["anchor_time"]}</td><td class="table-up">{cone["asc"]:,.2f}</td><td class="table-down">{cone["desc"]:,.2f}</td><td>±{cone["expansion"]:.1f}</td><td>{cone["blocks"]}</td></tr>' for name, cone in cones.items()])
    st.markdown(f'<div class="card"><table class="data-table"><thead><tr><th>Cone</th><th>Anchor</th><th>Time</th><th>Ascending</th><th>Descending</th><th>Expansion</th><th>Blocks</th></tr></thead><tbody>{cone_rows}</tbody></table></div>', unsafe_allow_html=True)
    
    if cone_confluence["count"] > 0:
        conf_items = ", ".join([f'{c["cone"]} {c["rail"]} ({c["distance"]} pts)' for c in cone_confluence["confluences"]])
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon green">✨</div><div><div class="card-title">Cone Confluence</div><div class="card-subtitle">{cone_confluence["count"]} active</div></div></div><div style="color:var(--text-primary)">{conf_items}</div></div>', unsafe_allow_html=True)
    
    # DEBUG
    if inputs["show_debug"]:
        st.markdown("### 🔧 Debug Panel")
        st.markdown(f'<div class="card"><div class="pillar-item"><span class="pillar-name">ES Candle Count</span><span class="pillar-value">{len(es_candles) if es_candles is not None else 0}</span></div><div class="pillar-item"><span class="pillar-name">First Candle</span><span class="pillar-value">{es_candles.index[0] if es_candles is not None and len(es_candles) > 0 else "N/A"}</span></div><div class="pillar-item"><span class="pillar-name">Last Candle</span><span class="pillar-value">{es_candles.index[-1] if es_candles is not None and len(es_candles) > 0 else "N/A"}</span></div><div class="pillar-item"><span class="pillar-name">5m Candles</span><span class="pillar-value">{len(spx_5min) if spx_5min is not None else 0}</span></div><div class="pillar-item"><span class="pillar-name">Auto-Refresh</span><span class="pillar-value">{"ON" if inputs["auto_refresh"] else "OFF"}</span></div></div>', unsafe_allow_html=True)
    
    # FOOTER
    st.markdown(f'<div class="app-footer">SPX PROPHET V4 | {now_ct.strftime("%H:%M:%S CT")} | Auto-Refresh: {"ON" if inputs["auto_refresh"] else "OFF"} ({inputs["refresh_interval"]}s)</div>', unsafe_allow_html=True)
    
    # AUTO-REFRESH
    if inputs["auto_refresh"]:
        time_module.sleep(inputs["refresh_interval"])
        st.rerun()

if __name__ == "__main__":
    main()

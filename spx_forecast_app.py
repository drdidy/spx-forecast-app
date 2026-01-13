# ═══════════════════════════════════════════════════════════════════════════════
# SPX PROPHET V5 - Institutional 0DTE Trading Analytics
# 3-Pillar Methodology | 4-Line Day Structure | Confluence Detection
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import pytz
import json
import os
import time as time_module
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Tuple
from functools import wraps

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="SPX Prophet V5", page_icon="🔮", layout="wide", initial_sidebar_state="expanded")

CT = pytz.timezone("America/Chicago")
STRUCTURE_SLOPE = 0.475  # Points per 30-min block for day structure
CONE_SLOPE = 0.475       # Points per 30-min block for cone rails
GAP_THRESHOLD = 6.0      # Points beyond structure line to trigger gap logic
CONFLUENCE_THRESHOLD = 5.0  # Points for structure/cone confluence
SAVE_FILE = "spx_prophet_v5_inputs.json"

VIX_ZONES = {
    "EXTREME_LOW": (0, 12), 
    "LOW": (12, 16), 
    "NORMAL": (16, 20), 
    "ELEVATED": (20, 25), 
    "HIGH": (25, 35), 
    "EXTREME": (35, 100)
}

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
.signal-badge.confluence{background:rgba(168,85,247,0.2);color:var(--purple);border:1px solid var(--purple)}
.metric-value{font-family:'IBM Plex Mono',monospace;font-size:24px;font-weight:600}
.metric-value.green{color:var(--green)}.metric-value.red{color:var(--red)}.metric-value.amber{color:var(--amber)}.metric-value.cyan{color:var(--cyan)}.metric-value.purple{color:var(--purple)}
.entry-alert{background:linear-gradient(135deg,rgba(0,212,170,0.2),rgba(34,211,238,0.2));border:2px solid var(--green);border-radius:16px;padding:24px;text-align:center;margin:16px 0;animation:pulse 2s infinite}
.entry-alert.puts{background:linear-gradient(135deg,rgba(255,71,87,0.2),rgba(168,85,247,0.2));border-color:var(--red)}
.entry-alert.wait{background:rgba(255,255,255,0.05);border-color:var(--border);animation:none}
.entry-alert.gap{background:linear-gradient(135deg,rgba(255,165,2,0.2),rgba(255,107,53,0.2));border-color:var(--amber)}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(0,212,170,0.4)}50%{box-shadow:0 0 20px 10px rgba(0,212,170,0.1)}}
.alert-title{font-size:14px;color:var(--text-secondary);margin-bottom:8px}
.alert-action{font-family:'Space Grotesk',sans-serif;font-size:28px;font-weight:700}
.alert-action.buy{color:var(--green)}.alert-action.sell{color:var(--red)}.alert-action.wait{color:var(--text-secondary)}.alert-action.gap{color:var(--amber)}
.alert-details{font-family:'IBM Plex Mono',monospace;font-size:16px;margin-top:8px;color:var(--text-primary)}
.structure-line{padding:8px 12px;border-radius:8px;margin:4px 0;font-family:'IBM Plex Mono',monospace;font-size:13px}
.structure-line.rising{background:rgba(0,212,170,0.1);border-left:3px solid var(--green)}
.structure-line.falling{background:rgba(255,71,87,0.1);border-left:3px solid var(--red)}
.structure-line.active{box-shadow:0 0 10px rgba(34,211,238,0.3);border:1px solid var(--cyan)}
.confluence-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;background:var(--purple);color:white;margin-left:8px}
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
.reversal-status{font-size:14px;font-weight:600}
.reversal-status.bullish{color:var(--green)}.reversal-status.bearish{color:var(--red)}.reversal-status.neutral{color:var(--amber)}
.app-footer{text-align:center;padding:20px;color:var(--text-secondary);font-size:12px;border-top:1px solid var(--border);margin-top:24px}
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def get_now_ct() -> datetime:
    return datetime.now(CT)

def is_trading_time(dt: datetime) -> bool:
    weekday = dt.weekday()
    t = dt.time()
    if weekday == 5:
        return False
    if weekday == 6 and t < time(17, 0):
        return False
    if weekday == 6 and t >= time(17, 0):
        return True
    if weekday == 4 and t >= time(16, 0):
        return False
    if weekday in [0, 1, 2, 3] and time(16, 0) <= t < time(17, 0):
        return False
    return True

def count_trading_minutes(start_dt: datetime, end_dt: datetime) -> int:
    if start_dt >= end_dt:
        return 0
    minutes = 0
    current = start_dt.replace(second=0, microsecond=0)
    max_iterations = 10080
    iterations = 0
    while current < end_dt and iterations < max_iterations:
        if is_trading_time(current):
            minutes += 1
        current += timedelta(minutes=1)
        iterations += 1
    return minutes

def count_30min_blocks(start_dt: datetime, end_dt: datetime) -> int:
    return count_trading_minutes(start_dt, end_dt) // 30

# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def fetch_es_30min_candles(days: int = 10) -> Optional[pd.DataFrame]:
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
    if es_candles is None or candle_count < 50:
        return {"signal": "NEUTRAL", "reason": "Insufficient data", "ema_50": None, "sma_200": None, "diff_pct": None, "score": 0, "candle_count": candle_count, "data_status": "NO_DATA"}
    
    close = es_candles['Close']
    ema_50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    sma_period = min(200, candle_count)
    sma_200 = close.rolling(window=sma_period).mean().iloc[-1]
    diff_pct = ((ema_50 - sma_200) / sma_200) * 100
    data_status = "FULL" if candle_count >= 200 else "PARTIAL"
    
    if ema_50 > sma_200:
        signal, score, reason = "LONG", min(30, int(abs(diff_pct) * 12)), f"EMA > SMA by {diff_pct:+.2f}%"
    elif ema_50 < sma_200:
        signal, score, reason = "SHORT", min(30, int(abs(diff_pct) * 12)), f"EMA < SMA by {diff_pct:+.2f}%"
    else:
        signal, score, reason = "NEUTRAL", 0, "MAs converging"
    
    if data_status == "PARTIAL":
        score = int(score * 0.7)
    
    return {"signal": signal, "reason": reason, "ema_50": round(ema_50, 2), "sma_200": round(sma_200, 2), "diff_pct": round(diff_pct, 4), "score": score, "candle_count": candle_count, "data_status": data_status}

# ═══════════════════════════════════════════════════════════════════════════════
# PILLAR 2: DAY STRUCTURE (4-Line Projection)
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_day_structure(overnight_high: float, overnight_high_time: datetime, overnight_low: float, overnight_low_time: datetime, target_time: datetime, current_price: float, premarket_high: Optional[float] = None, premarket_low: Optional[float] = None) -> Dict:
    effective_high = premarket_high if premarket_high and premarket_high > overnight_high else overnight_high
    effective_low = premarket_low if premarket_low and premarket_low < overnight_low else overnight_low
    
    blocks_from_high = count_30min_blocks(overnight_high_time, target_time)
    blocks_from_low = count_30min_blocks(overnight_low_time, target_time)
    
    high_expansion = STRUCTURE_SLOPE * blocks_from_high
    low_expansion = STRUCTURE_SLOPE * blocks_from_low
    
    ceiling_rising = round(effective_high + high_expansion, 2)
    ceiling_falling = round(effective_high - high_expansion, 2)
    floor_rising = round(effective_low + low_expansion, 2)
    floor_falling = round(effective_low - low_expansion, 2)
    
    now = get_now_ct()
    blocks_from_high_now = count_30min_blocks(overnight_high_time, now)
    blocks_from_low_now = count_30min_blocks(overnight_low_time, now)
    
    high_expansion_now = STRUCTURE_SLOPE * blocks_from_high_now
    low_expansion_now = STRUCTURE_SLOPE * blocks_from_low_now
    
    ceiling_rising_now = round(effective_high + high_expansion_now, 2)
    ceiling_falling_now = round(effective_high - high_expansion_now, 2)
    floor_rising_now = round(effective_low + low_expansion_now, 2)
    floor_falling_now = round(effective_low - low_expansion_now, 2)
    
    lines = {
        "ceiling_rising": {"name": "Ceiling Rising", "short": "C↑", "anchor": effective_high, "at_9am": ceiling_rising, "current": ceiling_rising_now, "direction": "rising", "blocks": blocks_from_high, "expansion": high_expansion, "entry_type": "PUTS", "gap_entry_type": "CALLS"},
        "ceiling_falling": {"name": "Ceiling Falling", "short": "C↓", "anchor": effective_high, "at_9am": ceiling_falling, "current": ceiling_falling_now, "direction": "falling", "blocks": blocks_from_high, "expansion": high_expansion, "entry_type": "CALLS", "gap_entry_type": "PUTS"},
        "floor_rising": {"name": "Floor Rising", "short": "F↑", "anchor": effective_low, "at_9am": floor_rising, "current": floor_rising_now, "direction": "rising", "blocks": blocks_from_low, "expansion": low_expansion, "entry_type": "PUTS", "gap_entry_type": "CALLS"},
        "floor_falling": {"name": "Floor Falling", "short": "F↓", "anchor": effective_low, "at_9am": floor_falling, "current": floor_falling_now, "direction": "falling", "blocks": blocks_from_low, "expansion": low_expansion, "entry_type": "CALLS", "gap_entry_type": "PUTS"}
    }
    
    distances = {}
    for key, line in lines.items():
        dist = current_price - line["current"]
        distances[key] = {"distance": round(dist, 2), "abs_distance": round(abs(dist), 2), "above": dist > 0}
    
    nearest_line = min(distances.keys(), key=lambda k: distances[k]["abs_distance"])
    nearest_distance = distances[nearest_line]["abs_distance"]
    
    if nearest_distance <= 3:
        proximity_score = 35
    elif nearest_distance <= 8:
        proximity_score = 28
    elif nearest_distance <= 15:
        proximity_score = 20
    else:
        proximity_score = 10
    
    return {"lines": lines, "distances": distances, "nearest_line": nearest_line, "nearest_distance": nearest_distance, "effective_high": effective_high, "effective_low": effective_low, "premarket_override_high": premarket_high is not None and premarket_high > overnight_high, "premarket_override_low": premarket_low is not None and premarket_low < overnight_low, "score": proximity_score}

# ═══════════════════════════════════════════════════════════════════════════════
# PILLAR 3: MOMENTUM
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

def calculate_momentum(es_candles: Optional[pd.DataFrame]) -> Dict:
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
        signal, score, reason = "BULLISH", 20 + (bullish_count * 5), f"RSI {rsi}, MACD {macd['direction']}, {structure}"
    elif bearish_count >= 2:
        signal, score, reason = "BEARISH", 20 + (bearish_count * 5), f"RSI {rsi}, MACD {macd['direction']}, {structure}"
    else:
        signal, score, reason = "NEUTRAL", 10, "Mixed signals"
    
    return {"signal": signal, "reason": reason, "score": min(35, score), "rsi": rsi, "macd": macd, "structure": structure}

# ═══════════════════════════════════════════════════════════════════════════════
# CONE RAILS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_cone_rails(prior_high: float, prior_high_time: datetime, prior_low: float, prior_low_time: datetime, prior_close: float, prior_close_time: datetime, target_time: datetime) -> Dict:
    cones = {}
    for name, price, anchor_time in [("HIGH", prior_high, prior_high_time), ("LOW", prior_low, prior_low_time), ("CLOSE", prior_close, prior_close_time)]:
        blocks = count_30min_blocks(anchor_time, target_time)
        expansion = CONE_SLOPE * blocks
        cones[name] = {"anchor": price, "anchor_time": anchor_time.strftime("%I:%M %p") if anchor_time else "N/A", "asc": round(price + expansion, 2), "desc": round(price - expansion, 2), "blocks": blocks, "expansion": round(expansion, 2)}
    return cones

def detect_confluence(structure: Dict, cones: Dict, current_price: float) -> Dict:
    confluences = []
    structure_values = [{"type": "structure", "name": line["name"], "key": key, "price": line["current"], "direction": line["direction"]} for key, line in structure["lines"].items()]
    cone_values = []
    for cone_name, cone in cones.items():
        cone_values.append({"type": "cone", "name": f"{cone_name} Asc", "price": cone["asc"], "direction": "rising"})
        cone_values.append({"type": "cone", "name": f"{cone_name} Desc", "price": cone["desc"], "direction": "falling"})
    
    for sv in structure_values:
        for cv in cone_values:
            distance = abs(sv["price"] - cv["price"])
            if distance <= CONFLUENCE_THRESHOLD:
                avg_price = (sv["price"] + cv["price"]) / 2
                dist_from_current = abs(current_price - avg_price)
                confluences.append({"structure_line": sv["name"], "structure_key": sv["key"], "cone_rail": cv["name"], "structure_price": sv["price"], "cone_price": cv["price"], "avg_price": round(avg_price, 2), "distance_between": round(distance, 2), "dist_from_current": round(dist_from_current, 2), "strength": "HEAVY" if distance <= 2 else "MODERATE"})
    
    confluences.sort(key=lambda x: x["dist_from_current"])
    score = 0 if len(confluences) == 0 else (15 + len(confluences) * 3) if confluences[0]["dist_from_current"] <= 5 else (5 + len(confluences) * 2)
    
    return {"confluences": confluences, "count": len(confluences), "score": min(20, score), "nearest": confluences[0] if confluences else None}

# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

def determine_entry(structure: Dict, ma_bias: str, current_price: float, confluence: Dict) -> Dict:
    lines = structure["lines"]
    distances = structure["distances"]
    nearest = structure["nearest_line"]
    nearest_line = lines[nearest]
    nearest_dist = distances[nearest]
    
    gap_detected = False
    gap_type = None
    gap_line = None
    
    for key, line in lines.items():
        dist = distances[key]
        if line["direction"] == "rising" and dist["above"] and dist["abs_distance"] >= GAP_THRESHOLD:
            gap_detected, gap_type, gap_line = True, "GAP_UP", key
            break
        if line["direction"] == "falling" and not dist["above"] and dist["abs_distance"] >= GAP_THRESHOLD:
            gap_detected, gap_type, gap_line = True, "GAP_DOWN", key
            break
    
    if gap_detected:
        target_line = lines[gap_line]
        if gap_type == "GAP_UP":
            entry_type, entry_price, action = "CALLS", target_line["current"], "WAIT_PULLBACK"
            reason = f"Gap UP through {target_line['name']} - wait for pullback to {entry_price:.2f}"
        else:
            entry_type, entry_price, action = "PUTS", target_line["current"], "WAIT_BOUNCE"
            reason = f"Gap DOWN through {target_line['name']} - wait for bounce to {entry_price:.2f}"
        
        return {"action": action, "entry_type": entry_type, "entry_price": entry_price, "target_line": gap_line, "target_line_name": target_line["name"], "reason": reason, "gap_detected": True, "gap_type": gap_type, "gap_distance": distances[gap_line]["abs_distance"], "ready": False, "confluence_at_entry": any(c["structure_key"] == gap_line for c in confluence["confluences"])}
    
    nearest_entry_type = nearest_line["entry_type"]
    ma_aligns = (ma_bias == "LONG" and nearest_entry_type == "CALLS") or (ma_bias == "SHORT" and nearest_entry_type == "PUTS") or ma_bias == "NEUTRAL"
    
    if nearest_line["direction"] == "rising":
        approaching = not nearest_dist["above"]
    else:
        approaching = nearest_dist["above"]
    
    entry_price = nearest_line["current"]
    distance_to_entry = nearest_dist["abs_distance"]
    
    if distance_to_entry <= 3:
        action, ready = ("READY" if ma_aligns else "READY_NO_BIAS"), ma_aligns
    elif distance_to_entry <= 10 and approaching:
        action, ready = "APPROACHING", False
    else:
        action, ready = "WAITING", False
    
    return {"action": action, "entry_type": nearest_entry_type, "entry_price": entry_price, "target_line": nearest, "target_line_name": nearest_line["name"], "reason": f"{nearest_line['name']} at {entry_price:.2f} ({distance_to_entry:.1f} pts away)", "gap_detected": False, "gap_type": None, "gap_distance": 0, "ready": ready, "ma_aligns": ma_aligns, "approaching": approaching, "distance_to_entry": distance_to_entry, "confluence_at_entry": any(c["structure_key"] == nearest for c in confluence["confluences"])}

def select_strike(entry_price: float, entry_type: str, method: str = "gamma_optimal") -> Dict:
    if entry_type == "CALLS":
        offset = 20 if method == "gamma_optimal" else 25 if method == "conservative" else 15
        raw_strike = entry_price + offset
        strike = round(raw_strike / 5) * 5
        otm_distance = strike - entry_price
    elif entry_type == "PUTS":
        offset = 20 if method == "gamma_optimal" else 25 if method == "conservative" else 15
        raw_strike = entry_price - offset
        strike = round(raw_strike / 5) * 5
        otm_distance = entry_price - strike
    else:
        return {"strike": 0, "option_type": "N/A", "otm_distance": 0, "method": method}
    
    return {"strike": int(strike), "option_type": "CALL" if entry_type == "CALLS" else "PUT", "otm_distance": round(otm_distance, 2), "method": method, "entry_price": entry_price}

# ═══════════════════════════════════════════════════════════════════════════════
# 5-MIN REVERSAL
# ═══════════════════════════════════════════════════════════════════════════════

def detect_5min_reversal(candles_5m: Optional[pd.DataFrame], entry_type: str, entry_price: float, current_price: float) -> Dict:
    if candles_5m is None or len(candles_5m) < 5:
        return {"status": "NO_DATA", "signal": "WAIT", "message": "Insufficient 5-min data", "ready": False, "rsi": None, "candle_pattern": None}
    
    close = candles_5m['Close']
    rsi_5m = calculate_rsi(close, period=14)
    last_candle = candles_5m.iloc[-1]
    is_green = last_candle['Close'] > last_candle['Open']
    is_red = last_candle['Close'] < last_candle['Open']
    candle_pattern = "GREEN" if is_green else "RED" if is_red else "DOJI"
    
    dist_to_entry = abs(current_price - entry_price)
    at_level = dist_to_entry <= 3
    
    if entry_type == "CALLS":
        rsi_oversold = rsi_5m < 40
        if at_level and is_green and rsi_oversold:
            status, signal, message, ready = "REVERSAL_CONFIRMED", "BUY_CALLS", "✅ Bullish reversal - ENTER CALLS", True
        elif at_level and is_green:
            status, signal, message, ready = "CANDLE_CONFIRMED", "WATCH", "Green candle at level", False
        elif at_level:
            status, signal, message, ready = "AT_LEVEL", "WATCH", "Waiting for green candle", False
        else:
            status, signal, message, ready = "APPROACHING", "WAIT", f"Approaching ({dist_to_entry:.1f} pts)", False
    elif entry_type == "PUTS":
        rsi_overbought = rsi_5m > 60
        if at_level and is_red and rsi_overbought:
            status, signal, message, ready = "REVERSAL_CONFIRMED", "BUY_PUTS", "✅ Bearish reversal - ENTER PUTS", True
        elif at_level and is_red:
            status, signal, message, ready = "CANDLE_CONFIRMED", "WATCH", "Red candle at level", False
        elif at_level:
            status, signal, message, ready = "AT_LEVEL", "WATCH", "Waiting for red candle", False
        else:
            status, signal, message, ready = "APPROACHING", "WAIT", f"Approaching ({dist_to_entry:.1f} pts)", False
    else:
        status, signal, message, ready = "NO_ENTRY", "WAIT", "No entry type", False
    
    return {"status": status, "signal": signal, "message": message, "ready": ready, "rsi": rsi_5m, "candle_pattern": candle_pattern, "dist_to_entry": round(dist_to_entry, 2)}

# ═══════════════════════════════════════════════════════════════════════════════
# VIX & CONFIDENCE
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_vix(vix_current: float, vix_overnight_high: float, vix_overnight_low: float) -> Dict:
    zone_name = "NORMAL"
    for name, (low, high) in VIX_ZONES.items():
        if low <= vix_current < high:
            zone_name = name
            break
    
    vix_range = vix_overnight_high - vix_overnight_low
    vix_position = (vix_current - vix_overnight_low) / vix_range * 100 if vix_range > 0 else 50
    
    if vix_current > vix_overnight_high:
        springboard, bias = "ABOVE_CEILING", "CALLS"
    elif vix_current < vix_overnight_low:
        springboard, bias = "BELOW_FLOOR", "PUTS"
    elif vix_position > 75:
        springboard, bias = "NEAR_CEILING", "CALLS"
    elif vix_position < 25:
        springboard, bias = "NEAR_FLOOR", "PUTS"
    else:
        springboard, bias = "MID_RANGE", "NEUTRAL"
    
    return {"current": vix_current, "overnight_high": vix_overnight_high, "overnight_low": vix_overnight_low, "zone": zone_name, "springboard": springboard, "bias": bias, "position_pct": round(vix_position, 1)}

def calculate_confidence(ma_bias: Dict, structure: Dict, momentum: Dict, confluence: Dict, entry: Dict, vix: Dict) -> Dict:
    raw_scores = {"MA Bias": ma_bias.get("score", 0), "Structure": structure.get("score", 0), "Momentum": momentum.get("score", 0), "Confluence": confluence.get("score", 0)}
    raw_total = sum(raw_scores.values())
    normalized_total = min(100, int(raw_total * 100 / 120))
    
    ma_signal = ma_bias.get("signal", "NEUTRAL")
    entry_type = entry.get("entry_type", "")
    momentum_signal = momentum.get("signal", "NEUTRAL")
    
    ma_aligns = (ma_signal == "LONG" and entry_type == "CALLS") or (ma_signal == "SHORT" and entry_type == "PUTS")
    momentum_aligns = (momentum_signal == "BULLISH" and entry_type == "CALLS") or (momentum_signal == "BEARISH" and entry_type == "PUTS")
    vix_aligns = (vix.get("bias") == "CALLS" and entry_type == "CALLS") or (vix.get("bias") == "PUTS" and entry_type == "PUTS")
    alignment_count = sum([ma_aligns, momentum_aligns, vix_aligns])
    
    if normalized_total >= 85 and alignment_count >= 2:
        grade, action = "A+", "STRONG_ENTRY"
    elif normalized_total >= 75 and alignment_count >= 2:
        grade, action = "A", "ENTRY"
    elif normalized_total >= 65:
        grade, action = "B", "CAUTIOUS"
    elif normalized_total >= 50:
        grade, action = "C", "WAIT"
    else:
        grade, action = "D", "NO_TRADE"
    
    return {"total": normalized_total, "raw_total": raw_total, "grade": grade, "action": action, "breakdown": raw_scores, "alignment": {"ma_aligns": ma_aligns, "momentum_aligns": momentum_aligns, "vix_aligns": vix_aligns, "count": alignment_count}}

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
        st.markdown("## 🔮 SPX Prophet V5")
        st.markdown("*4-Line Day Structure*")
        
        trading_date = st.date_input("📅 Trading Date", value=date.today())
        
        st.markdown("---")
        st.markdown("### 📈 SPX Price")
        use_manual_spx = st.checkbox("Manual SPX", value=False)
        spx_price = st.number_input("SPX Price", value=float(saved.get("spx_price", 6050.0)), step=1.0) if use_manual_spx else None
        
        st.markdown("---")
        st.markdown("### 📊 Pillar 1: MA Bias")
        ma_override = st.selectbox("Override MA Bias", ["AUTO", "LONG", "SHORT", "NEUTRAL"], index=0)
        
        st.markdown("---")
        st.markdown("### 📐 Pillar 2: Day Structure")
        st.markdown("*Overnight: 5 PM → 8:30 AM CT*")
        
        HOUR_OPTIONS = list(range(0, 24))
        MINUTE_OPTIONS = [0, 15, 30, 45]
        
        st.markdown("**Overnight HIGH**")
        c1, c2, c3 = st.columns([2, 1, 1])
        on_high_price = c1.number_input("Price", value=float(saved.get("on_high_price", 6070.0)), step=0.5, key="onh_p")
        on_high_hour = c2.selectbox("Hr", HOUR_OPTIONS, index=int(saved.get("on_high_hour", 2)), key="onh_h")
        on_high_min = c3.selectbox("Min", MINUTE_OPTIONS, index=MINUTE_OPTIONS.index(int(saved.get("on_high_min", 0))) if int(saved.get("on_high_min", 0)) in MINUTE_OPTIONS else 0, key="onh_m")
        
        st.markdown("**Overnight LOW**")
        c1, c2, c3 = st.columns([2, 1, 1])
        on_low_price = c1.number_input("Price", value=float(saved.get("on_low_price", 6020.0)), step=0.5, key="onl_p")
        on_low_hour = c2.selectbox("Hr", HOUR_OPTIONS, index=int(saved.get("on_low_hour", 22)), key="onl_h")
        on_low_min = c3.selectbox("Min", MINUTE_OPTIONS, index=MINUTE_OPTIONS.index(int(saved.get("on_low_min", 0))) if int(saved.get("on_low_min", 0)) in MINUTE_OPTIONS else 0, key="onl_m")
        
        st.markdown("**Pre-Market Override (7:30-8:30 AM)**")
        use_premarket = st.checkbox("Enable Pre-Market Override", value=False)
        pm_high = st.number_input("Pre-Mkt High", value=float(saved.get("pm_high", 6075.0)), step=0.5) if use_premarket else None
        pm_low = st.number_input("Pre-Mkt Low", value=float(saved.get("pm_low", 6015.0)), step=0.5) if use_premarket else None
        
        st.markdown("---")
        st.markdown("### ⚡ VIX")
        vix_overnight_high = st.number_input("VIX O/N High", value=float(saved.get("vix_overnight_high", 18.0)), step=0.1)
        vix_overnight_low = st.number_input("VIX O/N Low", value=float(saved.get("vix_overnight_low", 15.0)), step=0.1)
        use_manual_vix = st.checkbox("Manual VIX", value=False)
        vix_current = st.number_input("Current VIX", value=float(saved.get("vix_current", 16.5)), step=0.1) if use_manual_vix else None
        
        st.markdown("---")
        st.markdown("### 📊 Prior Day (Cones)")
        c1, c2, c3 = st.columns([2, 1, 1])
        prior_high = c1.number_input("Prior High", value=float(saved.get("prior_high", 6075.0)), step=0.5)
        prior_high_hour = c2.selectbox("Hr", HOUR_OPTIONS, index=int(saved.get("prior_high_hour", 10)), key="ph_h")
        prior_high_min = c3.selectbox("Min", MINUTE_OPTIONS, index=MINUTE_OPTIONS.index(int(saved.get("prior_high_min", 0))) if int(saved.get("prior_high_min", 0)) in MINUTE_OPTIONS else 0, key="ph_m")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        prior_low = c1.number_input("Prior Low", value=float(saved.get("prior_low", 6010.0)), step=0.5)
        prior_low_hour = c2.selectbox("Hr", HOUR_OPTIONS, index=int(saved.get("prior_low_hour", 14)), key="pl_h")
        prior_low_min = c3.selectbox("Min", MINUTE_OPTIONS, index=MINUTE_OPTIONS.index(int(saved.get("prior_low_min", 0))) if int(saved.get("prior_low_min", 0)) in MINUTE_OPTIONS else 0, key="pl_m")
        
        prior_close = st.number_input("Prior Close (3 PM)", value=float(saved.get("prior_close", 6045.0)), step=0.5)
        
        st.markdown("---")
        st.markdown("### 🎯 Strike Method")
        strike_method = st.selectbox("OTM Distance", ["gamma_optimal", "conservative", "aggressive"], index=0)
        
        st.markdown("---")
        st.markdown("### 🔄 Auto-Refresh")
        auto_refresh = st.checkbox("Enable Auto-Refresh", value=False)
        refresh_interval = st.slider("Interval (sec)", 15, 120, 30) if auto_refresh else 30
        
        st.markdown("---")
        show_debug = st.checkbox("Show Debug Panel", value=False)
        
        if st.button("💾 Save Inputs", use_container_width=True):
            save_inputs({"spx_price": spx_price, "on_high_price": on_high_price, "on_high_hour": on_high_hour, "on_high_min": on_high_min, "on_low_price": on_low_price, "on_low_hour": on_low_hour, "on_low_min": on_low_min, "pm_high": pm_high, "pm_low": pm_low, "vix_overnight_high": vix_overnight_high, "vix_overnight_low": vix_overnight_low, "vix_current": vix_current, "prior_high": prior_high, "prior_high_hour": prior_high_hour, "prior_high_min": prior_high_min, "prior_low": prior_low, "prior_low_hour": prior_low_hour, "prior_low_min": prior_low_min, "prior_close": prior_close})
            st.success("✅ Saved!")
    
    prev_day = trading_date - timedelta(days=1)
    
    def make_overnight_time(hour: int, minute: int, trading_date: date) -> datetime:
        if hour >= 17:
            return CT.localize(datetime.combine(prev_day, time(hour, minute)))
        else:
            return CT.localize(datetime.combine(trading_date, time(hour, minute)))
    
    on_high_time = make_overnight_time(on_high_hour, on_high_min, trading_date)
    on_low_time = make_overnight_time(on_low_hour, on_low_min, trading_date)
    prior_high_time = CT.localize(datetime.combine(prev_day, time(prior_high_hour, prior_high_min)))
    prior_low_time = CT.localize(datetime.combine(prev_day, time(prior_low_hour, prior_low_min)))
    prior_close_time = CT.localize(datetime.combine(prev_day, time(15, 0)))
    
    return {"trading_date": trading_date, "spx_price": spx_price, "ma_override": ma_override, "on_high_price": on_high_price, "on_high_time": on_high_time, "on_low_price": on_low_price, "on_low_time": on_low_time, "pm_high": pm_high, "pm_low": pm_low, "vix_overnight_high": vix_overnight_high, "vix_overnight_low": vix_overnight_low, "vix_current": vix_current, "prior_high": prior_high, "prior_high_time": prior_high_time, "prior_low": prior_low, "prior_low_time": prior_low_time, "prior_close": prior_close, "prior_close_time": prior_close_time, "strike_method": strike_method, "auto_refresh": auto_refresh, "refresh_interval": refresh_interval, "show_debug": show_debug}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    st.markdown(STYLES, unsafe_allow_html=True)
    inputs = render_sidebar()
    now_ct = get_now_ct()
    target_9am = CT.localize(datetime.combine(inputs["trading_date"], time(9, 0)))
    
    # Data Loading
    with st.spinner("Loading market data..."):
        data_sources = {}
        
        if inputs["spx_price"]:
            current_price, data_sources["spx"] = inputs["spx_price"], "MANUAL"
        else:
            fetched_spx = fetch_spx_price()
            current_price, data_sources["spx"] = (fetched_spx, "LIVE") if fetched_spx else (None, "FAILED")
        
        if inputs["vix_current"]:
            vix_current, data_sources["vix"] = inputs["vix_current"], "MANUAL"
        else:
            fetched_vix = fetch_vix_price()
            vix_current, data_sources["vix"] = (fetched_vix, "LIVE") if fetched_vix else (16.0, "DEFAULT")
        
        es_candles = fetch_es_30min_candles()
        es_count = len(es_candles) if es_candles is not None else 0
        data_sources["es"] = "LIVE" if es_count >= 50 else "PARTIAL" if es_count > 0 else "FAILED"
        
        spx_5min = fetch_spx_5min_candles()
        data_sources["5min"] = "LIVE" if spx_5min is not None else "FAILED"
    
    if current_price is None:
        st.error("❌ **SPX PRICE UNAVAILABLE** - Enable Manual SPX in sidebar")
        st.stop()
    
    # Hero Header
    st.markdown(f'<div class="hero-header"><div class="hero-title">🔮 SPX PROPHET V5</div><div class="hero-subtitle">4-Line Day Structure | Confluence Detection | 3-Pillar Methodology</div><div class="hero-price">{current_price:,.2f}</div><div class="hero-time">{now_ct.strftime("%I:%M:%S %p CT")} | {inputs["trading_date"].strftime("%A, %B %d, %Y")}</div></div>', unsafe_allow_html=True)
    
    def status_icon(status):
        return "🟢" if status == "LIVE" else "🟡" if status in ["MANUAL", "DEFAULT"] else "🟠" if status == "PARTIAL" else "🔴"
    
    data_msg = f"SPX {status_icon(data_sources['spx'])} | ES {status_icon(data_sources['es'])} ({es_count}) | VIX {status_icon(data_sources['vix'])} | 5m {status_icon(data_sources['5min'])}"
    st.markdown(f'<div style="text-align:center;font-size:11px;color:var(--text-secondary);margin-bottom:16px;padding:8px;background:rgba(255,255,255,0.02);border-radius:8px">{data_msg}</div>', unsafe_allow_html=True)
    
    # Analysis
    ma_bias = {"signal": inputs["ma_override"], "reason": "Manual override", "score": 25 if inputs["ma_override"] != "NEUTRAL" else 0, "ema_50": None, "sma_200": None, "diff_pct": None, "candle_count": 0, "data_status": "OVERRIDE"} if inputs["ma_override"] != "AUTO" else calculate_ma_bias(es_candles)
    
    structure = calculate_day_structure(inputs["on_high_price"], inputs["on_high_time"], inputs["on_low_price"], inputs["on_low_time"], target_9am, current_price, inputs["pm_high"], inputs["pm_low"])
    momentum = calculate_momentum(es_candles)
    cones = calculate_cone_rails(inputs["prior_high"], inputs["prior_high_time"], inputs["prior_low"], inputs["prior_low_time"], inputs["prior_close"], inputs["prior_close_time"], target_9am)
    confluence = detect_confluence(structure, cones, current_price)
    vix = analyze_vix(vix_current, inputs["vix_overnight_high"], inputs["vix_overnight_low"])
    entry = determine_entry(structure, ma_bias["signal"], current_price, confluence)
    strike_info = select_strike(entry["entry_price"], entry["entry_type"], inputs["strike_method"])
    
    now_time = now_ct.time()
    in_entry_window = time(8, 30) <= now_time <= time(11, 30)
    reversal = detect_5min_reversal(spx_5min, entry["entry_type"], entry["entry_price"], current_price) if in_entry_window else {"status": "OUTSIDE_WINDOW", "signal": "WAIT", "message": "Entry window: 8:30-11:30 AM CT", "ready": False, "rsi": None, "candle_pattern": None}
    
    confidence = calculate_confidence(ma_bias, structure, momentum, confluence, entry, vix)
    
    # Entry Alert
    if entry["gap_detected"]:
        alert_class, action_class = "gap", "gap"
        action_text = f"⚠️ GAP {entry['gap_type'].replace('_', ' ')} - Wait for Retracement"
        details_text = f"Target: {entry['entry_price']:.2f} ({entry['target_line_name']}) | {entry['entry_type']} on pullback"
    elif reversal["ready"] and confidence["total"] >= 60:
        alert_class = "" if entry["entry_type"] == "CALLS" else "puts"
        action_class = "buy"
        action_text = f"🟢 BUY NOW: {strike_info['strike']} {strike_info['option_type']}"
        details_text = f"Entry: {entry['entry_price']:.2f} | Current: {current_price:.2f}" + (" | 🟣 CONFLUENCE" if entry["confluence_at_entry"] else "")
    elif entry["action"] in ["READY", "READY_NO_BIAS"]:
        alert_class, action_class = "wait", "wait"
        action_text = f"⏳ AT LEVEL - Watch for {entry['entry_type']} Entry"
        details_text = f"{entry['target_line_name']} at {entry['entry_price']:.2f}"
    elif not in_entry_window:
        alert_class, action_class = "wait", "wait"
        action_text = f"📅 PLAN: {entry['entry_type']} at {entry['target_line_name']}"
        details_text = f"Entry: {entry['entry_price']:.2f} | Strike: {strike_info['strike']} {strike_info['option_type']}"
    else:
        alert_class, action_class = "wait", "wait"
        action_text = f"⏳ WAITING: {entry['entry_type']} at {entry['target_line_name']}"
        details_text = f"Entry: {entry['entry_price']:.2f} | Distance: {entry.get('distance_to_entry', structure['nearest_distance']):.1f} pts"
    
    st.markdown(f'<div class="entry-alert {alert_class}"><div class="alert-title">ENTRY STATUS {"🟢 LIVE" if in_entry_window else "📋 PREVIEW"}</div><div class="alert-action {action_class}">{action_text}</div><div class="alert-details">{details_text}</div></div>', unsafe_allow_html=True)
    
    # Three Pillars
    st.markdown("### Three Pillars")
    p1, p2, p3 = st.columns(3)
    
    with p1:
        ma_class = "calls" if ma_bias["signal"] == "LONG" else "puts" if ma_bias["signal"] == "SHORT" else "neutral"
        status_color = "var(--green)" if ma_bias.get("data_status") in ["FULL", "OVERRIDE"] else "var(--amber)" if ma_bias.get("data_status") == "PARTIAL" else "var(--red)"
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon blue">📊</div><div><div class="card-title">Pillar 1: MA Bias</div><div class="card-subtitle">Direction | <span style="color:{status_color}">{ma_bias.get("candle_count", 0)} candles</span></div></div></div><span class="signal-badge {ma_class}">{ma_bias["signal"]}</span><div class="pillar-item" style="margin-top:12px"><span class="pillar-name">50 EMA</span><span class="pillar-value">{ma_bias.get("ema_50") or "—"}</span></div><div class="pillar-item"><span class="pillar-name">200 SMA</span><span class="pillar-value">{ma_bias.get("sma_200") or "—"}</span></div><div class="pillar-item"><span class="pillar-name">Score</span><span class="pillar-value">{ma_bias["score"]}/30</span></div></div>', unsafe_allow_html=True)
    
    with p2:
        lines = structure["lines"]
        nearest = structure["nearest_line"]
        lines_html = ""
        for key in ["ceiling_rising", "ceiling_falling", "floor_rising", "floor_falling"]:
            line = lines[key]
            is_active = key == nearest
            direction_class = "rising" if line["direction"] == "rising" else "falling"
            active_class = " active" if is_active else ""
            has_confluence = any(c["structure_key"] == key for c in confluence["confluences"])
            confluence_badge = '<span class="confluence-badge">CONFLUENCE</span>' if has_confluence else ""
            dist = structure["distances"][key]
            dist_str = f"+{dist['distance']:.1f}" if dist['above'] else f"{dist['distance']:.1f}"
            lines_html += f'<div class="structure-line {direction_class}{active_class}"><strong>{line["short"]}</strong> {line["current"]:.2f} ({dist_str}){confluence_badge}</div>'
        
        pm_override = '<div style="color:var(--amber);font-size:11px;margin-top:8px">⚠️ Pre-market override</div>' if structure["premarket_override_high"] or structure["premarket_override_low"] else ""
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon amber">📐</div><div><div class="card-title">Pillar 2: Structure</div><div class="card-subtitle">4-Line Projection</div></div></div>{lines_html}<div class="pillar-item" style="margin-top:12px"><span class="pillar-name">O/N High</span><span class="pillar-value">{structure["effective_high"]:.2f}</span></div><div class="pillar-item"><span class="pillar-name">O/N Low</span><span class="pillar-value">{structure["effective_low"]:.2f}</span></div><div class="pillar-item"><span class="pillar-name">Score</span><span class="pillar-value">{structure["score"]}/35</span></div>{pm_override}</div>', unsafe_allow_html=True)
    
    with p3:
        mom_class = "calls" if momentum["signal"] == "BULLISH" else "puts" if momentum["signal"] == "BEARISH" else "neutral"
        macd_info = momentum.get("macd", {})
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon green">📈</div><div><div class="card-title">Pillar 3: Momentum</div><div class="card-subtitle">ES Confirmation</div></div></div><span class="signal-badge {mom_class}">{momentum["signal"]}</span><div class="pillar-item" style="margin-top:12px"><span class="pillar-name">RSI (14)</span><span class="pillar-value">{momentum.get("rsi", "—")}</span></div><div class="pillar-item"><span class="pillar-name">MACD</span><span class="pillar-value">{macd_info.get("direction", "—")} {"📈" if macd_info.get("expanding") else "📉"}</span></div><div class="pillar-item"><span class="pillar-name">Structure</span><span class="pillar-value">{momentum.get("structure", "—")}</span></div><div class="pillar-item"><span class="pillar-name">Score</span><span class="pillar-value">{momentum["score"]}/35</span></div></div>', unsafe_allow_html=True)
    
    # Confidence & Reversal
    c1, c2 = st.columns(2)
    
    with c1:
        fill_class = "a-plus" if confidence["grade"] == "A+" else "high" if confidence["grade"] in ["A", "B"] else "medium" if confidence["grade"] == "C" else "low"
        breakdown_html = "".join([f'<div class="pillar-item"><span class="pillar-name">{name}</span><span class="pillar-value">+{score}</span></div>' for name, score in confidence["breakdown"].items()])
        align = confidence["alignment"]
        align_html = f'<div class="pillar-item"><span class="pillar-name">MA Aligns</span><span class="pillar-value">{"✅" if align["ma_aligns"] else "❌"}</span></div><div class="pillar-item"><span class="pillar-name">Momentum Aligns</span><span class="pillar-value">{"✅" if align["momentum_aligns"] else "❌"}</span></div><div class="pillar-item"><span class="pillar-name">VIX Aligns</span><span class="pillar-value">{"✅" if align["vix_aligns"] else "❌"}</span></div>'
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon purple">📋</div><div><div class="card-title">Confidence Score</div><div class="card-subtitle">{confidence["grade"]} Setup | {confidence["action"]}</div></div></div><div class="confidence-container"><div class="confidence-bar"><div class="confidence-fill {fill_class}" style="width:{confidence["total"]}%"></div></div><div class="confidence-label"><span class="confidence-score">{confidence["total"]}/100</span><span style="color:{"var(--green)" if confidence["total"] >= 75 else "var(--amber)" if confidence["total"] >= 60 else "var(--red)"}">{confidence["grade"]}</span></div></div>{align_html}<div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">{breakdown_html}</div></div>', unsafe_allow_html=True)
    
    with c2:
        rev_class = "bullish" if reversal.get("ready") and entry["entry_type"] == "CALLS" else "bearish" if reversal.get("ready") and entry["entry_type"] == "PUTS" else "neutral"
        window_status = "🟢 ENTRY WINDOW" if in_entry_window else "⏳ Outside Window"
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon cyan">🔄</div><div><div class="card-title">5-Min Reversal</div><div class="card-subtitle">{window_status}</div></div></div><div class="reversal-box"><div class="reversal-status {rev_class}">{reversal["message"]}</div></div><div class="pillar-item" style="margin-top:12px"><span class="pillar-name">5m RSI</span><span class="pillar-value">{reversal.get("rsi") or "—"}</span></div><div class="pillar-item"><span class="pillar-name">Last Candle</span><span class="pillar-value">{reversal.get("candle_pattern") or "—"}</span></div><div class="pillar-item"><span class="pillar-name">Dist to Entry</span><span class="pillar-value">{reversal.get("dist_to_entry", "—")} pts</span></div></div>', unsafe_allow_html=True)
    
    # Strike & VIX
    s1, s2 = st.columns(2)
    
    with s1:
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon purple">🎯</div><div><div class="card-title">Strike Selection</div><div class="card-subtitle">{strike_info["method"].replace("_", " ").title()}</div></div></div><div class="metric-value purple" style="font-size:32px">{strike_info["strike"]} {strike_info["option_type"]}</div><div class="pillar-item" style="margin-top:12px"><span class="pillar-name">Entry Level</span><span class="pillar-value">{entry["entry_price"]:.2f}</span></div><div class="pillar-item"><span class="pillar-name">OTM Distance</span><span class="pillar-value">{strike_info["otm_distance"]:.1f} pts</span></div><div class="pillar-item"><span class="pillar-name">Target Line</span><span class="pillar-value">{entry["target_line_name"]}</span></div><div class="pillar-item"><span class="pillar-name">Confluence</span><span class="pillar-value">{"🟣 YES" if entry["confluence_at_entry"] else "—"}</span></div></div>', unsafe_allow_html=True)
    
    with s2:
        vix_class = "calls" if vix["bias"] == "CALLS" else "puts" if vix["bias"] == "PUTS" else "neutral"
        st.markdown(f'<div class="card"><div class="card-header"><div class="card-icon red">⚡</div><div><div class="card-title">VIX Analysis</div><div class="card-subtitle">{vix["zone"]} Zone</div></div></div><span class="signal-badge {vix_class}">{vix["bias"]}</span><div class="pillar-item" style="margin-top:12px"><span class="pillar-name">Current VIX</span><span class="pillar-value">{vix["current"]:.2f}</span></div><div class="pillar-item"><span class="pillar-name">O/N High</span><span class="pillar-value">{vix["overnight_high"]:.2f}</span></div><div class="pillar-item"><span class="pillar-name">O/N Low</span><span class="pillar-value">{vix["overnight_low"]:.2f}</span></div><div class="pillar-item"><span class="pillar-name">Springboard</span><span class="pillar-value">{vix["springboard"]}</span></div></div>', unsafe_allow_html=True)
    
    # Cone Rails
    st.markdown("### Cone Rails (Prior Day)")
    cone_rows = "".join([f'<tr><td>{name}</td><td>{cone["anchor"]:,.2f}</td><td>{cone["anchor_time"]}</td><td class="table-up">{cone["asc"]:,.2f}</td><td class="table-down">{cone["desc"]:,.2f}</td><td>±{cone["expansion"]:.1f}</td><td>{cone["blocks"]}</td></tr>' for name, cone in cones.items()])
    st.markdown(f'<div class="card"><table class="data-table"><thead><tr><th>Cone</th><th>Anchor</th><th>Time</th><th>Ascending</th><th>Descending</th><th>Expansion</th><th>Blocks</th></tr></thead><tbody>{cone_rows}</tbody></table></div>', unsafe_allow_html=True)
    
    # Confluence Zones
    if confluence["count"] > 0:
        st.markdown("### 🟣 Confluence Zones (Heavy S/R)")
        conf_rows = ""
        for c in confluence["confluences"]:
            strength_color = "var(--purple)" if c["strength"] == "HEAVY" else "var(--amber)"
            conf_rows += f'<tr><td>{c["structure_line"]}</td><td>{c["structure_price"]:.2f}</td><td>{c["cone_rail"]}</td><td>{c["cone_price"]:.2f}</td><td style="color:{strength_color};font-weight:600">{c["avg_price"]:.2f}</td><td>{c["dist_from_current"]:.1f}</td><td style="color:{strength_color}">{c["strength"]}</td></tr>'
        st.markdown(f'<div class="card"><table class="data-table"><thead><tr><th>Structure</th><th>Price</th><th>Cone</th><th>Price</th><th>Avg Level</th><th>Dist</th><th>Strength</th></tr></thead><tbody>{conf_rows}</tbody></table></div>', unsafe_allow_html=True)
    
    # Structure at 9 AM Reference
    with st.expander("📐 Structure Levels at 9:00 AM CT"):
        struct_9am_rows = ""
        for key in ["ceiling_rising", "ceiling_falling", "floor_rising", "floor_falling"]:
            line = structure["lines"][key]
            entry_color = "var(--green)" if line["entry_type"] == "CALLS" else "var(--red)"
            struct_9am_rows += f'<tr><td>{line["name"]}</td><td>{line["anchor"]:.2f}</td><td>{line["at_9am"]:.2f}</td><td>±{line["expansion"]:.1f}</td><td>{line["blocks"]}</td><td style="color:{entry_color}">{line["entry_type"]}</td><td style="color:var(--amber)">{line["gap_entry_type"]}</td></tr>'
        st.markdown(f'<div class="card"><table class="data-table"><thead><tr><th>Line</th><th>Anchor</th><th>@ 9 AM</th><th>Expansion</th><th>Blocks</th><th>Normal</th><th>Gap</th></tr></thead><tbody>{struct_9am_rows}</tbody></table></div>', unsafe_allow_html=True)
    
    # Debug
    if inputs["show_debug"]:
        st.markdown("### 🔧 Debug Panel")
        d1, d2 = st.columns(2)
        with d1:
            st.markdown(f'<div class="card"><div class="card-title">Data Status</div><div class="pillar-item"><span class="pillar-name">ES Candles</span><span class="pillar-value">{es_count}</span></div><div class="pillar-item"><span class="pillar-name">5m Candles</span><span class="pillar-value">{len(spx_5min) if spx_5min is not None else 0}</span></div><div class="pillar-item"><span class="pillar-name">Current Time</span><span class="pillar-value">{now_ct.strftime("%H:%M:%S")}</span></div></div>', unsafe_allow_html=True)
        with d2:
            st.markdown(f'<div class="card"><div class="card-title">Structure Calc</div><div class="pillar-item"><span class="pillar-name">O/N High Time</span><span class="pillar-value">{inputs["on_high_time"].strftime("%m/%d %I:%M %p")}</span></div><div class="pillar-item"><span class="pillar-name">O/N Low Time</span><span class="pillar-value">{inputs["on_low_time"].strftime("%m/%d %I:%M %p")}</span></div><div class="pillar-item"><span class="pillar-name">Gap Threshold</span><span class="pillar-value">{GAP_THRESHOLD} pts</span></div></div>', unsafe_allow_html=True)
        st.json(entry)
    
    # Footer
    st.markdown(f'<div class="app-footer">SPX PROPHET V5 | 4-Line Day Structure | {now_ct.strftime("%H:%M:%S CT")} | Auto-Refresh: {"ON" if inputs["auto_refresh"] else "OFF"}</div>', unsafe_allow_html=True)
    
    if inputs["auto_refresh"]:
        time_module.sleep(inputs["refresh_interval"])
        st.rerun()

if __name__ == "__main__":
    main()

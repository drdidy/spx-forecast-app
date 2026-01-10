"""
🔮 SPX PROPHET V2
Where Structure Becomes Foresight

Complete 3-Pillar Trading System for SPX 0DTE Options
All inputs in SPX - ES only used internally for MA calculation
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta, time as dt_time
import pytz
import json
import os

# ============================================================================
# CONSTANTS
# ============================================================================
CT = pytz.timezone('America/Chicago')
CONE_SLOPE = 0.475  # Points per 30-min block
OTM_DISTANCE = 20   # Points from entry level

POLYGON_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
INPUTS_FILE = "spx_prophet_inputs.json"

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="SPX Prophet V2",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# PREMIUM LIGHT-MODE GLASSMORPHISM CSS
# ============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    :root {
        --bg-gradient-start: #f0f4ff;
        --bg-gradient-mid: #e8f0fe;
        --bg-gradient-end: #faf0ff;
        --glass-bg: rgba(255, 255, 255, 0.6);
        --glass-bg-strong: rgba(255, 255, 255, 0.85);
        --glass-border: rgba(255, 255, 255, 0.8);
        --glass-shadow: rgba(100, 100, 150, 0.1);
        --text-primary: #1a1a2e;
        --text-secondary: #64648c;
        --text-muted: #9494b8;
        --accent-green: #10b981;
        --accent-green-light: #d1fae5;
        --accent-red: #ef4444;
        --accent-red-light: #fee2e2;
        --accent-amber: #f59e0b;
        --accent-amber-light: #fef3c7;
        --accent-purple: #8b5cf6;
        --accent-purple-light: #ede9fe;
        --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --gradient-success: linear-gradient(135deg, #10b981 0%, #059669 100%);
        --gradient-danger: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        --gradient-warning: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }
    
    .stApp {
        background: linear-gradient(135deg, var(--bg-gradient-start) 0%, var(--bg-gradient-mid) 50%, var(--bg-gradient-end) 100%);
        background-attachment: fixed;
    }
    
    .stApp::before {
        content: '';
        position: fixed;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: 
            radial-gradient(circle at 20% 80%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(59, 130, 246, 0.08) 0%, transparent 50%);
        animation: float 20s ease-in-out infinite;
        pointer-events: none;
        z-index: 0;
    }
    
    @keyframes float {
        0%, 100% { transform: translate(0, 0); }
        50% { transform: translate(1%, 1%); }
    }
    
    .main .block-container { padding-top: 2rem; max-width: 1400px; position: relative; z-index: 1; }
    
    .glass-card {
        background: var(--glass-bg-strong);
        backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 20px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 24px var(--glass-shadow);
    }
    
    .hero-container {
        text-align: center;
        padding: 2rem;
        margin-bottom: 2rem;
        background: var(--glass-bg-strong);
        backdrop-filter: blur(30px);
        border-radius: 28px;
        border: 1px solid rgba(255, 255, 255, 0.9);
        box-shadow: 0 8px 32px rgba(100, 100, 150, 0.12);
        position: relative;
    }
    
    .hero-container::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        background: var(--gradient-primary);
        border-radius: 28px 28px 0 0;
    }
    
    .hero-icon { font-size: 3rem; margin-bottom: 0.5rem; animation: pulse-glow 3s ease-in-out infinite; }
    
    @keyframes pulse-glow {
        0%, 100% { transform: scale(1); filter: drop-shadow(0 0 8px rgba(139, 92, 246, 0.3)); }
        50% { transform: scale(1.05); filter: drop-shadow(0 0 20px rgba(139, 92, 246, 0.5)); }
    }
    
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.75rem;
        font-weight: 800;
        background: var(--gradient-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .hero-tagline {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        color: var(--text-secondary);
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }
    
    .hero-price-box {
        display: inline-flex;
        align-items: center;
        gap: 0.75rem;
        background: var(--glass-bg);
        padding: 0.75rem 1.5rem;
        border-radius: 14px;
        border: 1px solid var(--glass-border);
    }
    
    .hero-price-label { font-family: 'Inter'; font-size: 1rem; font-weight: 600; color: var(--text-secondary); }
    .hero-price { font-family: 'JetBrains Mono'; font-size: 2rem; font-weight: 600; color: var(--text-primary); }
    
    .hero-time {
        font-family: 'JetBrains Mono';
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-top: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }
    
    .live-dot { width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%; animation: blink 2s infinite; }
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(139, 92, 246, 0.1);
    }
    
    .section-icon {
        width: 32px; height: 32px;
        display: flex; align-items: center; justify-content: center;
        background: var(--gradient-primary);
        border-radius: 8px;
        font-size: 1rem;
    }
    
    .section-title { font-family: 'Inter'; font-size: 1rem; font-weight: 700; color: var(--text-primary); }
    
    .pillar-card {
        background: var(--glass-bg-strong);
        backdrop-filter: blur(20px);
        border-radius: 18px;
        padding: 1.25rem;
        height: 100%;
        border: 1px solid var(--glass-border);
        box-shadow: 0 4px 20px var(--glass-shadow);
        position: relative;
        overflow: hidden;
        transition: transform 0.3s ease;
    }
    
    .pillar-card:hover { transform: translateY(-3px); }
    
    .pillar-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
    .pillar-card.bullish::before { background: var(--gradient-success); }
    .pillar-card.bearish::before { background: var(--gradient-danger); }
    .pillar-card.neutral::before { background: var(--gradient-warning); }
    
    .pillar-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.6rem; }
    
    .pillar-icon {
        width: 38px; height: 38px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 10px;
        font-size: 1.2rem;
    }
    
    .pillar-icon.bullish { background: var(--accent-green-light); }
    .pillar-icon.bearish { background: var(--accent-red-light); }
    .pillar-icon.neutral { background: var(--accent-amber-light); }
    
    .pillar-number { font-family: 'JetBrains Mono'; font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
    .pillar-name { font-family: 'Inter'; font-size: 0.9rem; font-weight: 700; color: var(--text-primary); }
    .pillar-question { font-family: 'Inter'; font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.75rem; }
    
    .pillar-answer { font-family: 'Inter'; font-size: 1.6rem; font-weight: 800; margin-bottom: 0.3rem; }
    .pillar-answer.bullish { color: var(--accent-green); }
    .pillar-answer.bearish { color: var(--accent-red); }
    .pillar-answer.neutral { color: var(--accent-amber); }
    
    .pillar-detail {
        font-family: 'JetBrains Mono';
        font-size: 0.65rem;
        color: var(--text-muted);
        background: rgba(0,0,0,0.03);
        padding: 0.3rem 0.5rem;
        border-radius: 5px;
        display: inline-block;
    }
    
    .signal-card {
        background: var(--glass-bg-strong);
        backdrop-filter: blur(30px);
        border-radius: 24px;
        padding: 1.75rem;
        text-align: center;
        border: 2px solid;
        margin: 1.25rem 0;
    }
    
    .signal-card.calls { border-color: var(--accent-green); box-shadow: 0 8px 32px rgba(16, 185, 129, 0.15); }
    .signal-card.puts { border-color: var(--accent-red); box-shadow: 0 8px 32px rgba(239, 68, 68, 0.15); }
    .signal-card.wait { border-color: var(--accent-amber); box-shadow: 0 8px 32px rgba(245, 158, 11, 0.15); }
    .signal-card.notrade { border-color: var(--text-muted); }
    
    .signal-icon { font-size: 3rem; margin-bottom: 0.5rem; animation: signal-bounce 2s ease-in-out infinite; }
    @keyframes signal-bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
    
    .signal-action { font-family: 'Inter'; font-size: 2.5rem; font-weight: 800; letter-spacing: 2px; }
    .signal-action.calls { color: var(--accent-green); }
    .signal-action.puts { color: var(--accent-red); }
    .signal-action.wait { color: var(--accent-amber); }
    .signal-action.notrade { color: var(--text-muted); }
    
    .signal-reason { font-family: 'Inter'; font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.4rem; }
    
    .signal-details { display: flex; justify-content: center; gap: 1.25rem; margin-top: 1.25rem; flex-wrap: wrap; }
    
    .signal-detail-item {
        background: var(--glass-bg);
        padding: 0.875rem 1.25rem;
        border-radius: 12px;
        border: 1px solid var(--glass-border);
        min-width: 100px;
    }
    
    .signal-detail-icon { font-size: 1.1rem; margin-bottom: 0.25rem; }
    .signal-detail-label { font-family: 'Inter'; font-size: 0.6rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); }
    .signal-detail-value { font-family: 'JetBrains Mono'; font-size: 1.2rem; font-weight: 600; color: var(--text-primary); }
    
    .structure-visual { background: var(--glass-bg); border-radius: 14px; padding: 1.25rem; margin: 0.75rem 0; }
    
    .structure-level { display: flex; align-items: center; padding: 0.6rem 0; border-bottom: 1px dashed rgba(0,0,0,0.08); }
    .structure-level:last-child { border-bottom: none; }
    .structure-label { font-family: 'Inter'; font-size: 0.75rem; font-weight: 600; width: 100px; color: var(--text-secondary); }
    .structure-value { font-family: 'JetBrains Mono'; font-size: 1rem; font-weight: 600; flex: 1; }
    .structure-value.ceiling { color: var(--accent-red); }
    .structure-value.floor { color: var(--accent-green); }
    .structure-value.current { color: var(--accent-purple); }
    .structure-distance { font-family: 'JetBrains Mono'; font-size: 0.7rem; color: var(--text-muted); background: rgba(0,0,0,0.04); padding: 0.2rem 0.4rem; border-radius: 4px; }
    
    .vix-zone-visual { background: var(--glass-bg); border-radius: 14px; padding: 1rem; }
    .vix-zone-bar { height: 10px; background: linear-gradient(to right, var(--accent-red), var(--accent-amber), var(--accent-green)); border-radius: 5px; position: relative; margin: 0.75rem 0; }
    .vix-marker { position: absolute; top: -3px; width: 16px; height: 16px; background: var(--text-primary); border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.2); transform: translateX(-50%); }
    .vix-labels { display: flex; justify-content: space-between; font-family: 'JetBrains Mono'; font-size: 0.7rem; color: var(--text-muted); }
    
    .cone-table-container { background: var(--glass-bg-strong); border-radius: 14px; padding: 1rem; border: 1px solid var(--glass-border); }
    .cone-table { width: 100%; border-collapse: separate; border-spacing: 0 5px; font-family: 'JetBrains Mono'; }
    .cone-table th { padding: 0.5rem; text-align: center; font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
    .cone-table td { padding: 0.6rem; text-align: center; background: var(--glass-bg); font-size: 0.85rem; }
    .cone-table tr td:first-child { border-radius: 8px 0 0 8px; }
    .cone-table tr td:last-child { border-radius: 0 8px 8px 0; }
    .cone-label { font-weight: 600; color: var(--text-secondary); }
    .cone-up { color: var(--accent-green); font-weight: 600; }
    .cone-down { color: var(--accent-red); font-weight: 600; }
    .cone-footer { text-align: center; margin-top: 0.6rem; font-size: 0.7rem; color: var(--text-muted); }
    
    .options-container { background: var(--glass-bg-strong); border-radius: 14px; padding: 1rem; border: 1px solid var(--glass-border); }
    .options-ticker { text-align: center; margin-bottom: 0.75rem; padding-bottom: 0.6rem; border-bottom: 1px solid rgba(0,0,0,0.05); }
    .options-ticker-symbol { font-family: 'JetBrains Mono'; font-size: 0.8rem; color: var(--accent-purple); font-weight: 600; background: var(--accent-purple-light); padding: 0.35rem 0.7rem; border-radius: 5px; display: inline-block; }
    .options-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; }
    .options-item { text-align: center; padding: 0.6rem; background: var(--glass-bg); border-radius: 8px; }
    .options-item-icon { font-size: 1rem; margin-bottom: 0.2rem; }
    .options-label { font-family: 'Inter'; font-size: 0.55rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); }
    .options-value { font-family: 'JetBrains Mono'; font-size: 0.95rem; font-weight: 600; color: var(--text-primary); }
    
    .pillar-status { display: flex; align-items: center; gap: 0.4rem; padding: 0.4rem 0; border-bottom: 1px solid rgba(0,0,0,0.05); }
    .pillar-status:last-child { border-bottom: none; }
    .pillar-status-icon { font-size: 1rem; }
    .pillar-status-name { font-family: 'Inter'; font-size: 0.75rem; color: var(--text-secondary); flex: 1; }
    .pillar-status-value { font-family: 'JetBrains Mono'; font-size: 0.75rem; font-weight: 600; padding: 0.15rem 0.4rem; border-radius: 4px; }
    .pillar-status-value.ok { background: var(--accent-green-light); color: var(--accent-green); }
    .pillar-status-value.wait { background: var(--accent-amber-light); color: var(--accent-amber); }
    .pillar-status-value.no { background: var(--accent-red-light); color: var(--accent-red); }
    
    .app-footer { text-align: center; padding: 1.25rem; margin-top: 1.5rem; color: var(--text-muted); font-size: 0.75rem; border-top: 1px solid rgba(0,0,0,0.05); }
    
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #f8faff 0%, #f0f4ff 100%); }
    .sidebar-header { text-align: center; padding: 1rem; margin-bottom: 0.5rem; background: var(--glass-bg-strong); border-radius: 12px; }
    .sidebar-logo { font-size: 1.75rem; }
    .sidebar-title { font-family: 'Inter'; font-size: 1rem; font-weight: 700; background: var(--gradient-primary); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    
    .sidebar-section { background: var(--glass-bg-strong); border-radius: 12px; padding: 0.875rem; margin-bottom: 0.6rem; border: 1px solid var(--glass-border); }
    .sidebar-section-header { display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.6rem; padding-bottom: 0.4rem; border-bottom: 1px solid rgba(0,0,0,0.05); }
    .sidebar-section-icon { font-size: 0.9rem; }
    .sidebar-section-title { font-family: 'Inter'; font-size: 0.75rem; font-weight: 600; color: var(--text-primary); text-transform: uppercase; }
    
    .stNumberInput > div > div > input { background: white !important; border: 1px solid rgba(139, 92, 246, 0.2) !important; border-radius: 6px !important; font-family: 'JetBrains Mono' !important; font-size: 0.9rem !important; }
    .stButton > button { background: var(--gradient-primary) !important; color: white !important; border: none !important; border-radius: 8px !important; font-family: 'Inter' !important; font-weight: 600 !important; }
    
    section[data-testid="stSidebar"] { width: 300px !important; min-width: 300px !important; }
    [data-testid="collapsedControl"] { display: none; }
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_next_trading_day(from_date):
    """Get next trading day (skip weekends)"""
    next_day = from_date
    # If it's Friday after 4pm, Saturday, or Sunday, go to Monday
    if next_day.weekday() >= 5:  # Saturday or Sunday
        days_ahead = 7 - next_day.weekday()  # Monday
        next_day = next_day + timedelta(days=days_ahead)
    return next_day

def get_prior_trading_day(from_date):
    """Get prior trading day (skip weekends)"""
    prior = from_date - timedelta(days=1)
    while prior.weekday() >= 5:
        prior -= timedelta(days=1)
    return prior

# ============================================================================
# PERSISTENCE
# ============================================================================
DEFAULT_INPUTS = {
    # Trading Date (for next day preview or historical backtest)
    "use_custom_date": False,
    "custom_date": None,  # Will be set to date string "YYYY-MM-DD"
    
    # VIX Zone (from TradingView)
    "vix_overnight_high": 0.0,
    "vix_overnight_low": 0.0,
    "vix_current": 0.0,
    
    # ES/SPX Offset (for MA calculation only)
    "es_spx_offset": 7.0,
    
    # Current SPX (manual input option)
    "spx_manual": 0.0,
    "use_manual_spx": False,
    
    # Day Structure - CEILING anchors (SPX)
    "ceiling_anchor1_price": 0.0,
    "ceiling_anchor1_hour": 17,
    "ceiling_anchor1_minute": 0,
    "ceiling_anchor2_price": 0.0,
    "ceiling_anchor2_hour": 2,
    "ceiling_anchor2_minute": 0,
    
    # Day Structure - FLOOR anchors (SPX)
    "floor_anchor1_price": 0.0,
    "floor_anchor1_hour": 17,
    "floor_anchor1_minute": 0,
    "floor_anchor2_price": 0.0,
    "floor_anchor2_hour": 2,
    "floor_anchor2_minute": 0,
    
    # Prior Day for Cones (SPX)
    "prior_high": 0.0,
    "prior_high_hour": 10,
    "prior_high_minute": 0,
    "prior_low": 0.0,
    "prior_low_hour": 14,
    "prior_low_minute": 0,
    "prior_close": 0.0,  # Always 3pm CT
    
    "last_updated": ""
}

def save_inputs(inputs):
    inputs["last_updated"] = datetime.now(CT).strftime("%Y-%m-%d %H:%M:%S CT")
    with open(INPUTS_FILE, "w") as f:
        json.dump(inputs, f, indent=2)

def load_inputs():
    if os.path.exists(INPUTS_FILE):
        try:
            with open(INPUTS_FILE, "r") as f:
                return {**DEFAULT_INPUTS, **json.load(f)}
        except:
            pass
    return DEFAULT_INPUTS.copy()

# ============================================================================
# DATA FETCHING (ES only for MAs)
# ============================================================================
def get_es_30min_candles(days=15):
    """Fetch ES 30-min candles for MA calculation only"""
    try:
        es = yf.Ticker("ES=F")
        return es.history(period=f"{days}d", interval="30m")
    except:
        return None

def get_spx_price():
    """Try to fetch current SPX price during RTH"""
    try:
        spx = yf.Ticker("^GSPC")
        data = spx.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except:
        pass
    return None

def fetch_option_data(strike, is_call, trade_date):
    """Fetch option data from Polygon"""
    try:
        date_str = trade_date.strftime("%y%m%d")
        option_type = "C" if is_call else "P"
        strike_str = f"{int(strike * 1000):08d}"
        ticker = f"O:SPXW{date_str}{option_type}{strike_str}"
        
        url = f"https://api.polygon.io/v3/snapshot/options/SPXW/{ticker}?apiKey={POLYGON_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                return data['results'], ticker
    except:
        pass
    return None, None

# ============================================================================
# PILLAR 1: MA BIAS (Uses ES internally, converts to SPX)
# ============================================================================
def analyze_ma_bias(es_candles, offset):
    """Calculate 50 EMA vs 200 SMA from ES 30-min candles, convert to SPX"""
    if es_candles is None or len(es_candles) < 200:
        return "NEUTRAL", "Insufficient data", None, None
    
    # Convert ES to SPX using user-provided offset
    spx_close = es_candles['Close'] - offset
    
    ema_50 = spx_close.ewm(span=50, adjust=False).mean().iloc[-1]
    sma_200 = spx_close.rolling(window=200).mean().iloc[-1]
    
    diff_pct = (ema_50 - sma_200) / sma_200 * 100
    
    if diff_pct > 0.1:
        return "LONG", f"50 EMA ({ema_50:,.1f}) > 200 SMA ({sma_200:,.1f})", ema_50, sma_200
    elif diff_pct < -0.1:
        return "SHORT", f"50 EMA ({ema_50:,.1f}) < 200 SMA ({sma_200:,.1f})", ema_50, sma_200
    else:
        return "NEUTRAL", f"MAs crossing ({diff_pct:+.2f}%)", ema_50, sma_200

# ============================================================================
# PILLAR 2: DAY STRUCTURE (All SPX inputs)
# ============================================================================
def build_anchor_datetime(base_date, hour, minute):
    """Build datetime for overnight anchor point"""
    if hour >= 17:  # Evening = prior day
        anchor_date = base_date
    else:  # Early morning = current day
        anchor_date = base_date + timedelta(days=1)
    return CT.localize(datetime.combine(anchor_date, dt_time(hour, minute)))

def calculate_trendline(a1_price, a1_time, a2_price, a2_time, target_time):
    """Calculate projected trendline value at target time"""
    minutes_between = (a2_time - a1_time).total_seconds() / 60
    if minutes_between == 0:
        return a1_price, 0
    
    slope_per_min = (a2_price - a1_price) / minutes_between
    minutes_to_target = (target_time - a1_time).total_seconds() / 60
    projected = a1_price + (slope_per_min * minutes_to_target)
    
    return projected, slope_per_min * 30  # Return slope per 30-min block

def get_day_structure(inputs, trade_date):
    """Calculate CEILING and FLOOR from anchor points, projected to 9:00 AM CT entry"""
    c1 = inputs.get("ceiling_anchor1_price", 0)
    c2 = inputs.get("ceiling_anchor2_price", 0)
    f1 = inputs.get("floor_anchor1_price", 0)
    f2 = inputs.get("floor_anchor2_price", 0)
    
    if c1 <= 0 or c2 <= 0 or f1 <= 0 or f2 <= 0:
        return None, None, None, None, "Enter anchor points"
    
    # trade_date is the date we're trading (entry day)
    # prior_day is the day before for overnight anchors
    prior_day = get_prior_trading_day(trade_date)
    
    # Build anchor datetimes
    c1_time = build_anchor_datetime(prior_day, inputs.get("ceiling_anchor1_hour", 17), inputs.get("ceiling_anchor1_minute", 0))
    c2_time = build_anchor_datetime(prior_day, inputs.get("ceiling_anchor2_hour", 2), inputs.get("ceiling_anchor2_minute", 0))
    f1_time = build_anchor_datetime(prior_day, inputs.get("floor_anchor1_hour", 17), inputs.get("floor_anchor1_minute", 0))
    f2_time = build_anchor_datetime(prior_day, inputs.get("floor_anchor2_hour", 2), inputs.get("floor_anchor2_minute", 0))
    
    # Project to 9:00 AM CT entry time on trade_date
    entry_time = CT.localize(datetime.combine(trade_date, dt_time(9, 0)))
    
    ceiling, c_slope = calculate_trendline(c1, c1_time, c2, c2_time, entry_time)
    floor, f_slope = calculate_trendline(f1, f1_time, f2, f2_time, entry_time)
    
    return ceiling, floor, c_slope, f_slope, f"@ 9AM | C: {c_slope:+.2f}/30m | F: {f_slope:+.2f}/30m"

# ============================================================================
# PILLAR 3: VIX ZONE (Inverse to SPX)
# ============================================================================
def analyze_vix_zone(vix_high, vix_low, vix_current):
    """
    VIX Zone with springboard logic - VIX is INVERSE to SPX
    
    VIX at CEILING (high fear) → SPX is low → CALLS timing (buy the dip)
    VIX at FLOOR (low fear) → SPX is high → PUTS timing (sell the top)
    """
    if vix_high <= 0 or vix_low <= 0 or vix_current <= 0:
        return {'timing_signal': "WAIT", 'zone_position': "Enter VIX", 'detail': "Missing data", 'zone_size': 0, 'range_pct': 0.5, 'puts_springboard': 0, 'calls_springboard': 0}
    
    zone_size = vix_high - vix_low
    if zone_size <= 0:
        return {'timing_signal': "WAIT", 'zone_position': "Invalid", 'detail': "High > Low required", 'zone_size': 0, 'range_pct': 0.5, 'puts_springboard': vix_low, 'calls_springboard': vix_high}
    
    # Springboards (VIX levels that trigger SPX trades)
    calls_springboard = vix_high   # VIX at ceiling → buy CALLS on SPX
    puts_springboard = vix_low     # VIX at floor → buy PUTS on SPX
    
    if vix_current > vix_high:
        # VIX above range (high fear)
        zones_above = (vix_current - vix_high) / zone_size
        pos = f"ABOVE (+{zones_above:.1f})"
        # Extended ceiling springboard
        calls_springboard = vix_high + (int(zones_above) + 1) * zone_size
        if abs(vix_current - vix_high) <= zone_size * 0.30:
            sig, detail = "CALLS", f"VIX elevated → SPX dip"
        else:
            sig, detail = "WAIT", f"Wait for VIX → {vix_high:.2f}"
        range_pct = 1.0
        
    elif vix_current < vix_low:
        # VIX below range (low fear/complacency)
        zones_below = (vix_low - vix_current) / zone_size
        pos = f"BELOW (-{zones_below:.1f})"
        # Extended floor springboard
        puts_springboard = vix_low - (int(zones_below) + 1) * zone_size
        if abs(vix_current - vix_low) <= zone_size * 0.30:
            sig, detail = "PUTS", f"VIX compressed → SPX top"
        else:
            sig, detail = "WAIT", f"Wait for VIX → {vix_low:.2f}"
        range_pct = 0.0
        
    else:
        # VIX inside range
        range_pct = (vix_current - vix_low) / zone_size
        pos = f"INSIDE ({range_pct:.0%})"
        
        if range_pct >= 0.70:
            # VIX near ceiling (high) → CALLS on SPX
            sig, detail = "CALLS", f"VIX high ({range_pct:.0%}) → CALLS"
        elif range_pct <= 0.30:
            # VIX near floor (low) → PUTS on SPX
            sig, detail = "PUTS", f"VIX low ({range_pct:.0%}) → PUTS"
        else:
            sig, detail = "WAIT", f"VIX mid-range ({range_pct:.0%})"
    
    return {
        'timing_signal': sig, 
        'zone_position': pos, 
        'detail': detail, 
        'zone_size': zone_size, 
        'range_pct': range_pct, 
        'puts_springboard': puts_springboard, 
        'calls_springboard': calls_springboard
    }

# ============================================================================
# CONE RAILS (All SPX inputs) - with proper trading hours calculation
# ============================================================================

def calculate_trading_minutes(from_dt, to_dt):
    """
    Calculate trading minutes between two datetimes, excluding maintenance breaks.
    
    ES Schedule (CT):
    - Week: Sunday 5:00 PM → Friday 4:00 PM
    - Daily maintenance: 4:00 PM → 5:00 PM (Mon-Thu)
    - Friday 4:00 PM = week close (no 5 PM reopen)
    - Weekend: Friday 4:00 PM → Sunday 5:00 PM (no trading)
    """
    if from_dt.tzinfo is None:
        from_dt = CT.localize(from_dt)
    if to_dt.tzinfo is None:
        to_dt = CT.localize(to_dt)
    
    if from_dt >= to_dt:
        return 0
    
    total_minutes = 0
    current = from_dt
    
    # Iterate minute by minute would be slow, so we do it in chunks
    while current < to_dt:
        weekday = current.weekday()  # 0=Mon, 4=Fri, 5=Sat, 6=Sun
        hour = current.hour
        minute = current.minute
        
        # Saturday - skip to Sunday 5 PM
        if weekday == 5:
            next_sunday = current.date() + timedelta(days=1)
            current = CT.localize(datetime.combine(next_sunday, dt_time(17, 0)))
            continue
        
        # Sunday before 5 PM - skip to 5 PM
        if weekday == 6 and hour < 17:
            current = CT.localize(datetime.combine(current.date(), dt_time(17, 0)))
            continue
        
        # Friday after 4 PM - skip to Sunday 5 PM
        if weekday == 4 and hour >= 16:
            next_sunday = current.date() + timedelta(days=2)
            current = CT.localize(datetime.combine(next_sunday, dt_time(17, 0)))
            continue
        
        # Mon-Thu maintenance (4 PM - 5 PM) - skip to 5 PM
        if weekday in [0, 1, 2, 3] and 16 <= hour < 17:
            current = CT.localize(datetime.combine(current.date(), dt_time(17, 0)))
            continue
        
        # We're in a trading period - find end of this segment
        if weekday == 6:  # Sunday after 5 PM
            # Trade until midnight
            segment_end = CT.localize(datetime.combine(current.date() + timedelta(days=1), dt_time(0, 0)))
        elif weekday == 4:  # Friday before 4 PM
            # Trade until 4 PM (week close)
            segment_end = CT.localize(datetime.combine(current.date(), dt_time(16, 0)))
        elif hour >= 17:  # Mon-Thu evening (after 5 PM)
            # Trade until midnight
            segment_end = CT.localize(datetime.combine(current.date() + timedelta(days=1), dt_time(0, 0)))
        else:  # Mon-Thu/Fri daytime (before 4 PM)
            # Trade until 4 PM maintenance
            segment_end = CT.localize(datetime.combine(current.date(), dt_time(16, 0)))
        
        # Calculate trading minutes in this segment
        actual_end = min(segment_end, to_dt)
        if actual_end > current:
            total_minutes += (actual_end - current).total_seconds() / 60
        
        current = segment_end
    
    return total_minutes


def calculate_cone_rails(inputs, trade_date):
    """Calculate cones from prior day SPX levels, projected to 9:00 AM CT entry"""
    ph = inputs.get("prior_high", 0)
    pl = inputs.get("prior_low", 0)
    pc = inputs.get("prior_close", 0)
    
    if ph <= 0 or pl <= 0 or pc <= 0:
        return None
    
    # trade_date is the entry day, prior_day is where the cone anchors come from
    prior_day = get_prior_trading_day(trade_date)
    
    # Build anchor times
    high_anchor = CT.localize(datetime.combine(prior_day, dt_time(inputs.get("prior_high_hour", 10), inputs.get("prior_high_minute", 0))))
    low_anchor = CT.localize(datetime.combine(prior_day, dt_time(inputs.get("prior_low_hour", 14), inputs.get("prior_low_minute", 0))))
    close_anchor = CT.localize(datetime.combine(prior_day, dt_time(15, 0)))
    
    # Project to 9:00 AM CT entry time on trade_date
    entry_time = CT.localize(datetime.combine(trade_date, dt_time(9, 0)))
    
    def calc_expansion(anchor_dt):
        trading_mins = calculate_trading_minutes(anchor_dt, entry_time)
        blocks = trading_mins / 30
        return blocks, blocks * CONE_SLOPE
    
    h_blocks, h_exp = calc_expansion(high_anchor)
    l_blocks, l_exp = calc_expansion(low_anchor)
    c_blocks, c_exp = calc_expansion(close_anchor)
    
    return {
        'C1': {'name': 'HIGH', 'anchor': ph, 'asc': ph + h_exp, 'desc': ph - h_exp, 'blocks': h_blocks, 'exp': h_exp, 'time': high_anchor.strftime('%I:%M %p')},
        'C2': {'name': 'LOW', 'anchor': pl, 'asc': pl + l_exp, 'desc': pl - l_exp, 'blocks': l_blocks, 'exp': l_exp, 'time': low_anchor.strftime('%I:%M %p')},
        'C3': {'name': 'CLOSE', 'anchor': pc, 'asc': pc + c_exp, 'desc': pc - c_exp, 'blocks': c_blocks, 'exp': c_exp, 'time': '03:00 PM'},
    }

# ============================================================================
# TRADE DECISION
# ============================================================================
def generate_trade_decision(ma_bias, ceiling, floor, vix_zone, spx_price):
    """Combine pillars into trade signal - always set entry/strike based on MA+Structure"""
    result = {'signal': 'NO TRADE', 'reason': '', 'entry_level': None, 'strike': None, 'direction': None, 'aligned': False}
    
    if ma_bias == "NEUTRAL":
        result['reason'] = "MA Bias NEUTRAL"
        return result
    
    if ceiling is None or floor is None:
        result['reason'] = "Structure not set"
        return result
    
    # Always set entry/strike/direction based on MA Bias (for options display)
    if ma_bias == "LONG":
        result['direction'] = "CALLS"
        result['entry_level'] = floor
        result['strike'] = round((floor + OTM_DISTANCE) / 5) * 5
    elif ma_bias == "SHORT":
        result['direction'] = "PUTS"
        result['entry_level'] = ceiling
        result['strike'] = round((ceiling - OTM_DISTANCE) / 5) * 5
    
    # Now check VIX timing for final signal
    vix_sig = vix_zone.get('timing_signal', 'WAIT')
    
    if vix_sig == "WAIT":
        result['signal'] = "WAIT"
        result['reason'] = f"VIX: {vix_zone.get('detail', 'waiting')}"
        return result
    
    # Check full alignment
    if ma_bias == "LONG" and vix_sig == "CALLS":
        result['signal'] = "CALLS"
        result['reason'] = "All pillars BULLISH"
        result['aligned'] = True
    elif ma_bias == "SHORT" and vix_sig == "PUTS":
        result['signal'] = "PUTS"
        result['reason'] = "All pillars BEARISH"
        result['aligned'] = True
    else:
        result['signal'] = "NO TRADE"
        result['reason'] = f"Conflict: MA={ma_bias}, VIX={vix_sig}"
    
    return result

# ============================================================================
# MAIN APP
# ============================================================================
def main():
    now_ct = datetime.now(CT)
    
    if 'inputs' not in st.session_state:
        st.session_state.inputs = load_inputs()
    inputs = st.session_state.inputs
    
    # ========== SIDEBAR ==========
    with st.sidebar:
        st.markdown('<div class="sidebar-header"><div class="sidebar-logo">🔮</div><div class="sidebar-title">SPX Prophet V2</div></div>', unsafe_allow_html=True)
        
        # Trading Date (for next day preview or historical backtest)
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">📅</span><span class="sidebar-section-title">Trading Date</span></div></div>', unsafe_allow_html=True)
        
        # Default to next trading day
        default_trade_date = get_next_trading_day(now_ct.date())
        
        inputs["use_custom_date"] = st.checkbox("Custom Date", value=inputs.get("use_custom_date", False))
        if inputs["use_custom_date"]:
            # Parse saved date or use default
            saved_date = inputs.get("custom_date")
            if saved_date:
                try:
                    default_val = datetime.strptime(saved_date, "%Y-%m-%d").date()
                except:
                    default_val = default_trade_date
            else:
                default_val = default_trade_date
            
            selected_date = st.date_input("Select Date", value=default_val)
            inputs["custom_date"] = selected_date.strftime("%Y-%m-%d")
            trade_date = selected_date
            is_historical = trade_date < now_ct.date()
        else:
            trade_date = default_trade_date
            is_historical = False
        
        # Show what date we're using
        date_label = "📆 Historical" if is_historical else "📅 Next Trading Day" if trade_date != now_ct.date() else "📅 Today"
        st.caption(f"{date_label}: {trade_date.strftime('%a %b %d, %Y')}")
        
        # Current SPX
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">💹</span><span class="sidebar-section-title">Current SPX</span></div></div>', unsafe_allow_html=True)
        inputs["use_manual_spx"] = st.checkbox("Manual Input", value=inputs.get("use_manual_spx", False))
        if inputs["use_manual_spx"]:
            inputs["spx_manual"] = st.number_input("SPX Price", value=float(inputs.get("spx_manual", 0)), step=0.25, format="%.2f")
        
        # ES/SPX Offset (for MA calculation)
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">🔢</span><span class="sidebar-section-title">ES−SPX Offset (MAs)</span></div></div>', unsafe_allow_html=True)
        inputs["es_spx_offset"] = st.number_input("Offset (ES minus SPX)", value=float(inputs.get("es_spx_offset", 7.0)), step=0.1, format="%.1f")
        
        # VIX Zone
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">📊</span><span class="sidebar-section-title">VIX Zone (TradingView)</span></div></div>', unsafe_allow_html=True)
        inputs["vix_overnight_high"] = st.number_input("Overnight High", value=float(inputs.get("vix_overnight_high", 0)), step=0.01, format="%.2f")
        inputs["vix_overnight_low"] = st.number_input("Overnight Low", value=float(inputs.get("vix_overnight_low", 0)), step=0.01, format="%.2f")
        inputs["vix_current"] = st.number_input("Current VIX", value=float(inputs.get("vix_current", 0)), step=0.01, format="%.2f")
        
        # CEILING
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">🔴</span><span class="sidebar-section-title">CEILING (SPX Highs)</span></div></div>', unsafe_allow_html=True)
        st.caption("Anchor 1")
        c1a, c1b, c1c = st.columns([2,1,1])
        with c1a: inputs["ceiling_anchor1_price"] = st.number_input("Price", value=float(inputs.get("ceiling_anchor1_price", 0)), step=0.25, format="%.2f", key="c1p")
        with c1b: inputs["ceiling_anchor1_hour"] = st.number_input("Hr", value=int(inputs.get("ceiling_anchor1_hour", 17)), min_value=0, max_value=23, key="c1h")
        with c1c: inputs["ceiling_anchor1_minute"] = st.number_input("Min", value=int(inputs.get("ceiling_anchor1_minute", 0)), min_value=0, max_value=59, key="c1m")
        st.caption("Anchor 2")
        c2a, c2b, c2c = st.columns([2,1,1])
        with c2a: inputs["ceiling_anchor2_price"] = st.number_input("Price", value=float(inputs.get("ceiling_anchor2_price", 0)), step=0.25, format="%.2f", key="c2p")
        with c2b: inputs["ceiling_anchor2_hour"] = st.number_input("Hr", value=int(inputs.get("ceiling_anchor2_hour", 2)), min_value=0, max_value=23, key="c2h")
        with c2c: inputs["ceiling_anchor2_minute"] = st.number_input("Min", value=int(inputs.get("ceiling_anchor2_minute", 0)), min_value=0, max_value=59, key="c2m")
        
        # FLOOR
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">🟢</span><span class="sidebar-section-title">FLOOR (SPX Lows)</span></div></div>', unsafe_allow_html=True)
        st.caption("Anchor 1")
        f1a, f1b, f1c = st.columns([2,1,1])
        with f1a: inputs["floor_anchor1_price"] = st.number_input("Price", value=float(inputs.get("floor_anchor1_price", 0)), step=0.25, format="%.2f", key="f1p")
        with f1b: inputs["floor_anchor1_hour"] = st.number_input("Hr", value=int(inputs.get("floor_anchor1_hour", 17)), min_value=0, max_value=23, key="f1h")
        with f1c: inputs["floor_anchor1_minute"] = st.number_input("Min", value=int(inputs.get("floor_anchor1_minute", 0)), min_value=0, max_value=59, key="f1m")
        st.caption("Anchor 2")
        f2a, f2b, f2c = st.columns([2,1,1])
        with f2a: inputs["floor_anchor2_price"] = st.number_input("Price", value=float(inputs.get("floor_anchor2_price", 0)), step=0.25, format="%.2f", key="f2p")
        with f2b: inputs["floor_anchor2_hour"] = st.number_input("Hr", value=int(inputs.get("floor_anchor2_hour", 2)), min_value=0, max_value=23, key="f2h")
        with f2c: inputs["floor_anchor2_minute"] = st.number_input("Min", value=int(inputs.get("floor_anchor2_minute", 0)), min_value=0, max_value=59, key="f2m")
        
        # Prior Day (Cones)
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">📐</span><span class="sidebar-section-title">Prior Day (Cones SPX)</span></div></div>', unsafe_allow_html=True)
        st.caption("Prior High (C1)")
        ph1, ph2, ph3 = st.columns([2,1,1])
        with ph1: inputs["prior_high"] = st.number_input("Price", value=float(inputs.get("prior_high", 0)), step=0.25, format="%.2f", key="php")
        with ph2: inputs["prior_high_hour"] = st.number_input("Hr", value=int(inputs.get("prior_high_hour", 10)), min_value=0, max_value=23, key="phh")
        with ph3: inputs["prior_high_minute"] = st.number_input("Min", value=int(inputs.get("prior_high_minute", 0)), min_value=0, max_value=59, key="phm")
        st.caption("Prior Low (C2)")
        pl1, pl2, pl3 = st.columns([2,1,1])
        with pl1: inputs["prior_low"] = st.number_input("Price", value=float(inputs.get("prior_low", 0)), step=0.25, format="%.2f", key="plp")
        with pl2: inputs["prior_low_hour"] = st.number_input("Hr", value=int(inputs.get("prior_low_hour", 14)), min_value=0, max_value=23, key="plh")
        with pl3: inputs["prior_low_minute"] = st.number_input("Min", value=int(inputs.get("prior_low_minute", 0)), min_value=0, max_value=59, key="plm")
        st.caption("Prior Close (C3) @ 3pm")
        inputs["prior_close"] = st.number_input("Close", value=float(inputs.get("prior_close", 0)), step=0.25, format="%.2f", key="pcp")
        
        # Buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", use_container_width=True):
                save_inputs(inputs)
                st.success("Saved!")
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        if inputs.get("last_updated"):
            st.caption(f"Saved: {inputs['last_updated']}")
    
    # ========== DATA ==========
    es_candles = get_es_30min_candles()
    
    if inputs.get("use_manual_spx") and inputs.get("spx_manual", 0) > 0:
        spx_price = inputs["spx_manual"]
    else:
        spx_price = get_spx_price()
    
    # ========== PILLARS ==========
    ma_bias, ma_detail, ema_50, sma_200 = analyze_ma_bias(es_candles, inputs.get("es_spx_offset", 7.0))
    ceiling, floor, c_slope, f_slope, struct_status = get_day_structure(inputs, trade_date)
    vix_zone = analyze_vix_zone(inputs.get("vix_overnight_high", 0), inputs.get("vix_overnight_low", 0), inputs.get("vix_current", 0))
    cones = calculate_cone_rails(inputs, trade_date)
    trade = generate_trade_decision(ma_bias, ceiling, floor, vix_zone, spx_price)
    
    # ========== HERO ==========
    spx_display = f"{spx_price:,.2f}" if spx_price else "---"
    mode_badge = "📆 BACKTEST" if is_historical else "🔮 PREVIEW" if trade_date > now_ct.date() else ""
    
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-icon">🔮</div>
        <div class="hero-title">SPX PROPHET</div>
        <div class="hero-tagline">Where Structure Becomes Foresight</div>
        <div class="hero-price-box">
            <span class="hero-price-label">SPX</span>
            <span class="hero-price">{spx_display}</span>
        </div>
        <div class="hero-time"><span class="live-dot"></span>{now_ct.strftime('%I:%M:%S %p CT')} • <strong>{trade_date.strftime('%b %d, %Y')}</strong> {mode_badge}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== PILLARS DISPLAY ==========
    st.markdown('<div class="section-header"><div class="section-icon">⚡</div><div class="section-title">The Three Pillars</div></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        bias_class = "bullish" if ma_bias == "LONG" else "bearish" if ma_bias == "SHORT" else "neutral"
        bias_icon = "📈" if ma_bias == "LONG" else "📉" if ma_bias == "SHORT" else "⏸️"
        allowed = "CALLS only" if ma_bias == "LONG" else "PUTS only" if ma_bias == "SHORT" else "No trades"
        st.markdown(f"""
        <div class="pillar-card {bias_class}">
            <div class="pillar-header"><div class="pillar-icon {bias_class}">{bias_icon}</div><div><div class="pillar-number">Pillar 1 • Filter</div><div class="pillar-name">MA Bias</div></div></div>
            <div class="pillar-question">Can I trade CALLS or PUTS?</div>
            <div class="pillar-answer {bias_class}">{ma_bias}</div>
            <div class="pillar-detail">{allowed}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if ceiling and floor:
            s_class = "bullish" if ma_bias == "LONG" else "bearish" if ma_bias == "SHORT" else "neutral"
            entry_type = "FLOOR" if ma_bias == "LONG" else "CEILING" if ma_bias == "SHORT" else "N/A"
            s_icon = "🎯"
        else:
            s_class, entry_type, s_icon = "neutral", "PENDING", "⏳"
        c_disp = f"{ceiling:,.1f}" if ceiling else "---"
        f_disp = f"{floor:,.1f}" if floor else "---"
        st.markdown(f"""
        <div class="pillar-card {s_class}">
            <div class="pillar-header"><div class="pillar-icon {s_class}">{s_icon}</div><div><div class="pillar-number">Pillar 2 • Primary</div><div class="pillar-name">Day Structure</div></div></div>
            <div class="pillar-question">Where do I enter?</div>
            <div class="pillar-answer {s_class}">{entry_type}</div>
            <div class="pillar-detail">C: {c_disp} | F: {f_disp}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        v_sig = vix_zone.get('timing_signal', 'WAIT')
        v_class = "bullish" if v_sig == "CALLS" else "bearish" if v_sig == "PUTS" else "neutral"
        v_icon = "🟢" if v_sig == "CALLS" else "🔴" if v_sig == "PUTS" else "🟡"
        st.markdown(f"""
        <div class="pillar-card {v_class}">
            <div class="pillar-header"><div class="pillar-icon {v_class}">{v_icon}</div><div><div class="pillar-number">Pillar 3 • Timing</div><div class="pillar-name">VIX Zone</div></div></div>
            <div class="pillar-question">Is NOW the right time?</div>
            <div class="pillar-answer {v_class}">{v_sig}</div>
            <div class="pillar-detail">{vix_zone.get('zone_position', '---')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========== SIGNAL ==========
    sig = trade['signal']
    sig_class = sig.lower().replace(" ", "")
    sig_icon = "🚀" if sig == "CALLS" else "🔻" if sig == "PUTS" else "⏳" if sig == "WAIT" else "🚫"
    entry_disp = f"{trade['entry_level']:,.1f}" if trade['entry_level'] else "---"
    strike_disp = str(int(trade['strike'])) if trade['strike'] else "---"
    dist_disp = f"{abs(spx_price - trade['entry_level']):,.1f} pts" if trade['entry_level'] and spx_price else "---"
    
    st.markdown(f"""
    <div class="signal-card {sig_class}">
        <div class="signal-icon">{sig_icon}</div>
        <div class="signal-action {sig_class}">{sig}</div>
        <div class="signal-reason">{trade['reason']}</div>
        <div class="signal-details">
            <div class="signal-detail-item"><div class="signal-detail-icon">📍</div><div class="signal-detail-label">Entry</div><div class="signal-detail-value">{entry_disp}</div></div>
            <div class="signal-detail-item"><div class="signal-detail-icon">🎯</div><div class="signal-detail-label">Strike</div><div class="signal-detail-value">{strike_disp}</div></div>
            <div class="signal-detail-item"><div class="signal-detail-icon">📏</div><div class="signal-detail-label">Distance</div><div class="signal-detail-value">{dist_disp}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== STRUCTURE / VIX / STATUS ==========
    col_l, col_m, col_r = st.columns(3)
    
    with col_l:
        st.markdown('<div class="section-header"><div class="section-icon">🏗️</div><div class="section-title">Structure</div></div>', unsafe_allow_html=True)
        if ceiling and floor and spx_price:
            st.markdown(f"""
            <div class="structure-visual">
                <div class="structure-level"><div class="structure-label">🔴 CEILING</div><div class="structure-value ceiling">{ceiling:,.1f}</div><div class="structure-distance">↑ {ceiling - spx_price:,.1f}</div></div>
                <div class="structure-level"><div class="structure-label">🟣 CURRENT</div><div class="structure-value current">{spx_price:,.1f}</div><div class="structure-distance">SPX</div></div>
                <div class="structure-level"><div class="structure-label">🟢 FLOOR</div><div class="structure-value floor">{floor:,.1f}</div><div class="structure-distance">↓ {spx_price - floor:,.1f}</div></div>
            </div>
            <div style="font-size:0.65rem; color:var(--text-muted); text-align:center;">{struct_status}</div>
            """, unsafe_allow_html=True)
        else:
            st.info("Enter anchor points")
    
    with col_m:
        st.markdown('<div class="section-header"><div class="section-icon">📊</div><div class="section-title">VIX Zone (↔ SPX)</div></div>', unsafe_allow_html=True)
        vh, vl, vc = inputs.get("vix_overnight_high", 0), inputs.get("vix_overnight_low", 0), inputs.get("vix_current", 0)
        if vh > 0 and vl > 0 and vc > 0:
            pct = max(0, min(100, vix_zone.get('range_pct', 0.5) * 100))
            st.markdown(f"""
            <div class="vix-zone-visual">
                <div style="text-align:center; font-family:'JetBrains Mono'; font-size:1.3rem; font-weight:600;">VIX {vc:.2f}</div>
                <div class="vix-zone-bar"><div class="vix-marker" style="left:{pct}%;"></div></div>
                <div class="vix-labels"><span>🔴 {vl:.2f} PUTS</span><span>🟢 {vh:.2f} CALLS</span></div>
                <div style="text-align:center; font-size:0.7rem; color:var(--text-muted); margin-top:0.5rem;">{vix_zone.get('detail', '')}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Enter VIX values")
    
    with col_r:
        st.markdown('<div class="section-header"><div class="section-icon">✅</div><div class="section-title">Status</div></div>', unsafe_allow_html=True)
        ma_st = "ok" if ma_bias in ["LONG", "SHORT"] else "no"
        str_st = "ok" if ceiling and floor else "wait"
        vix_st = "ok" if v_sig in ["CALLS", "PUTS"] else "wait"
        all_st = "ok" if trade.get('aligned') else "wait" if sig == "WAIT" else "no"
        st.markdown(f"""
        <div class="glass-card">
            <div class="pillar-status"><div class="pillar-status-icon">①</div><div class="pillar-status-name">MA Bias</div><div class="pillar-status-value {ma_st}">{ma_bias}</div></div>
            <div class="pillar-status"><div class="pillar-status-icon">②</div><div class="pillar-status-name">Structure</div><div class="pillar-status-value {str_st}">{"READY" if ceiling else "PENDING"}</div></div>
            <div class="pillar-status"><div class="pillar-status-icon">③</div><div class="pillar-status-name">VIX Zone</div><div class="pillar-status-value {vix_st}">{v_sig}</div></div>
            <div style="border-top:2px solid rgba(0,0,0,0.1); margin-top:0.5rem; padding-top:0.5rem;">
                <div class="pillar-status"><div class="pillar-status-icon">🎯</div><div class="pillar-status-name" style="font-weight:700;">ALIGNED</div><div class="pillar-status-value {all_st}">{"YES" if trade.get('aligned') else "NO"}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========== CONES / OPTIONS ==========
    col_cones, col_opts = st.columns(2)
    
    with col_cones:
        st.markdown('<div class="section-header"><div class="section-icon">📐</div><div class="section-title">Cone Rails</div></div>', unsafe_allow_html=True)
        if cones:
            st.markdown(f"""
            <div class="cone-table-container">
                <table class="cone-table">
                    <thead><tr><th>Cone</th><th>Anchor</th><th>▲ Asc</th><th>▼ Desc</th><th>Time</th></tr></thead>
                    <tbody>
                        <tr><td class="cone-label">C1 {cones['C1']['name']}</td><td>{cones['C1']['anchor']:,.1f}</td><td class="cone-up">{cones['C1']['asc']:,.1f}</td><td class="cone-down">{cones['C1']['desc']:,.1f}</td><td style="font-size:0.65rem;">{cones['C1']['time']}</td></tr>
                        <tr><td class="cone-label">C2 {cones['C2']['name']}</td><td>{cones['C2']['anchor']:,.1f}</td><td class="cone-up">{cones['C2']['asc']:,.1f}</td><td class="cone-down">{cones['C2']['desc']:,.1f}</td><td style="font-size:0.65rem;">{cones['C2']['time']}</td></tr>
                        <tr><td class="cone-label">C3 {cones['C3']['name']}</td><td>{cones['C3']['anchor']:,.1f}</td><td class="cone-up">{cones['C3']['asc']:,.1f}</td><td class="cone-down">{cones['C3']['desc']:,.1f}</td><td style="font-size:0.65rem;">{cones['C3']['time']}</td></tr>
                    </tbody>
                </table>
                <div class="cone-footer">±{CONE_SLOPE}/30m | C1: ±{cones['C1']['exp']:.1f} | C2: ±{cones['C2']['exp']:.1f} | C3: ±{cones['C3']['exp']:.1f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Enter Prior Day values")
    
    with col_opts:
        st.markdown('<div class="section-header"><div class="section-icon">💹</div><div class="section-title">0DTE Options</div></div>', unsafe_allow_html=True)
        if trade['strike'] and trade['direction']:
            opt_data, ticker = fetch_option_data(trade['strike'], trade['direction'] == "CALLS", trade_date)
            if opt_data:
                day = opt_data.get('day', {})
                lq = opt_data.get('last_quote', {})
                last = day.get('close', day.get('last', 0))
                stop = last / 2
                st.markdown(f"""
                <div class="options-container">
                    <div class="options-ticker"><div class="options-ticker-symbol">{ticker}</div><div style="font-size:0.7rem; color:var(--text-muted);">{int(trade['strike'])} {"Call" if trade['direction']=="CALLS" else "Put"}</div></div>
                    <div class="options-grid">
                        <div class="options-item"><div class="options-item-icon">💵</div><div class="options-label">Last</div><div class="options-value">${last:.2f}</div></div>
                        <div class="options-item"><div class="options-item-icon">🟢</div><div class="options-label">Bid</div><div class="options-value">${lq.get('bid', 0):.2f}</div></div>
                        <div class="options-item"><div class="options-item-icon">🔴</div><div class="options-label">Ask</div><div class="options-value">${lq.get('ask', 0):.2f}</div></div>
                        <div class="options-item"><div class="options-item-icon">📊</div><div class="options-label">Vol</div><div class="options-value">{day.get('volume', 0):,}</div></div>
                        <div class="options-item"><div class="options-item-icon">📈</div><div class="options-label">OI</div><div class="options-value">{opt_data.get('open_interest', 0):,}</div></div>
                        <div class="options-item"><div class="options-item-icon">🛑</div><div class="options-label">50% Stop</div><div class="options-value">${stop:.2f}</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info(f"Awaiting data for {ticker}" if ticker else "Generate signal first")
        else:
            st.info("Generate signal to view options")
    
    # ========== FOOTER ==========
    st.markdown(f'<div class="app-footer">🕐 {now_ct.strftime("%I:%M:%S %p CT")} • ⏰ Entry: 8:30-11:30 AM • 🛑 Stop: 50% • All SPX</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()

"""
🔮 SPX PROPHET
Where Structure Becomes Foresight

A sophisticated 0DTE SPX options trading application using:
- MA Bias (50 EMA vs 200 SMA direction filter)
- Day Structure (Floor/Ceiling entry levels)
- VIX Zone (Timing signal from overnight range)
- Cone Rails (±0.475 slope projections)
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta, time
import pytz
import json
from pathlib import Path

# ============================================================================
# CONSTANTS
# ============================================================================
SLOPE = 0.475           # Points per 30-min block
BLOCKS = 36             # 3pm to 9am (18 hours × 2)
OTM_DISTANCE = 15       # Strike offset from entry
ENTRY_TIME = "9:00 AM CT"
POLYGON_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
DEFAULT_OFFSET = 7.0    # ES - SPX difference
CT = pytz.timezone('America/Chicago')

# ============================================================================
# PAGE CONFIG & STYLING
# ============================================================================
st.set_page_config(
    page_title="SPX Prophet",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium glassmorphism styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    :root {
        --bg-primary: #0a0a0f;
        --bg-card: rgba(20, 20, 30, 0.7);
        --glass-border: rgba(255, 255, 255, 0.08);
        --text-primary: #ffffff;
        --text-secondary: rgba(255, 255, 255, 0.6);
        --accent-green: #00ff88;
        --accent-red: #ff4757;
        --accent-amber: #ffa502;
        --accent-blue: #3b82f6;
        --accent-purple: #8b5cf6;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    .main .block-container {
        padding-top: 2rem;
        max-width: 1400px;
    }
    
    /* Glass card effect */
    .glass-card {
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    /* Hero header */
    .hero-header {
        text-align: center;
        padding: 2rem 1rem;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(59, 130, 246, 0.1) 100%);
        border-radius: 20px;
        border: 1px solid rgba(139, 92, 246, 0.2);
    }
    
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 50%, #00ff88 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }
    
    .hero-tagline {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        color: var(--text-secondary);
        font-weight: 300;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    
    .hero-price {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.5rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-top: 1rem;
    }
    
    .hero-time {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        color: var(--text-secondary);
    }
    
    /* Pillar cards */
    .pillar-card {
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        border-radius: 16px;
        padding: 1.5rem;
        height: 100%;
        border: 1px solid var(--glass-border);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .pillar-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
    }
    
    .pillar-title {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: var(--text-secondary);
        margin-bottom: 0.75rem;
    }
    
    .pillar-question {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: var(--text-secondary);
        margin-bottom: 1rem;
    }
    
    .pillar-answer {
        font-family: 'Inter', sans-serif;
        font-size: 1.75rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .pillar-detail {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }
    
    .bullish { color: var(--accent-green); }
    .bearish { color: var(--accent-red); }
    .neutral { color: var(--accent-amber); }
    
    /* Signal card */
    .signal-card {
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        border: 2px solid;
        margin: 1.5rem 0;
    }
    
    .signal-card.calls {
        border-color: var(--accent-green);
        box-shadow: 0 0 40px rgba(0, 255, 136, 0.15);
    }
    
    .signal-card.puts {
        border-color: var(--accent-red);
        box-shadow: 0 0 40px rgba(255, 71, 87, 0.15);
    }
    
    .signal-card.wait {
        border-color: var(--accent-amber);
        box-shadow: 0 0 40px rgba(255, 165, 2, 0.15);
    }
    
    .signal-card.notrade {
        border-color: rgba(255, 255, 255, 0.2);
    }
    
    .signal-action {
        font-family: 'Inter', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        letter-spacing: 4px;
    }
    
    .signal-reason {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: var(--text-secondary);
        margin-top: 0.5rem;
    }
    
    .signal-details {
        display: flex;
        justify-content: center;
        gap: 3rem;
        margin-top: 1.5rem;
        flex-wrap: wrap;
    }
    
    .signal-detail-item {
        text-align: center;
    }
    
    .signal-detail-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-secondary);
    }
    
    .signal-detail-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    /* Cone table */
    .cone-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .cone-table th {
        background: rgba(139, 92, 246, 0.2);
        padding: 0.75rem 1rem;
        text-align: center;
        font-weight: 500;
        font-size: 0.85rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .cone-table th:first-child {
        border-radius: 8px 0 0 0;
    }
    
    .cone-table th:last-child {
        border-radius: 0 8px 0 0;
    }
    
    .cone-table td {
        padding: 0.75rem 1rem;
        text-align: center;
        border-bottom: 1px solid var(--glass-border);
    }
    
    .cone-table tr:last-child td:first-child {
        border-radius: 0 0 0 8px;
    }
    
    .cone-table tr:last-child td:last-child {
        border-radius: 0 0 8px 0;
    }
    
    .cone-label {
        font-weight: 500;
        color: var(--text-secondary);
    }
    
    .cone-up { color: var(--accent-green); }
    .cone-down { color: var(--accent-red); }
    
    /* Options panel */
    .options-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 1rem;
    }
    
    .options-item {
        text-align: center;
        padding: 1rem;
        background: rgba(59, 130, 246, 0.1);
        border-radius: 12px;
        border: 1px solid rgba(59, 130, 246, 0.2);
    }
    
    .options-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-secondary);
        margin-bottom: 0.5rem;
    }
    
    .options-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 1.5rem;
        margin-top: 2rem;
        color: var(--text-secondary);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        border-top: 1px solid var(--glass-border);
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a0f 0%, #1a1a2e 100%);
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: var(--text-primary);
    }
    
    /* Input styling */
    .stNumberInput input, .stDateInput input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }
    
    .stCheckbox label {
        color: var(--text-primary) !important;
    }
    
    /* Metric override */
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Hide Streamlit branding but keep sidebar functional */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Force sidebar to always be visible */
    section[data-testid="stSidebar"] {
        width: 320px !important;
        min-width: 320px !important;
    }
    
    [data-testid="collapsedControl"] {
        display: none;
    }
    
    section[data-testid="stSidebar"] > div {
        width: 320px !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_es_price():
    """Fetch current ES futures price from Yahoo Finance."""
    try:
        es = yf.Ticker("ES=F")
        data = es.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        st.error(f"Error fetching ES price: {e}")
    return None

def get_es_history(days=300):
    """Fetch ES futures history for MA calculations."""
    try:
        es = yf.Ticker("ES=F")
        data = es.history(period=f"{days}d", interval="1d")
        return data
    except Exception as e:
        st.error(f"Error fetching ES history: {e}")
    return None

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average."""
    return prices.ewm(span=period, adjust=False).mean()

def calculate_sma(prices, period):
    """Calculate Simple Moving Average."""
    return prices.rolling(window=period).mean()

def analyze_ma_bias(es_history, offset):
    """Pillar 1: Determine MA Bias (direction filter)."""
    if es_history is None or len(es_history) < 200:
        return "NEUTRAL", "Insufficient data", None, None
    
    # Convert ES to SPX
    spx_close = es_history['Close'] - offset
    
    ema_50 = calculate_ema(spx_close, 50)
    sma_200 = calculate_sma(spx_close, 200)
    
    current_ema = ema_50.iloc[-1]
    current_sma = sma_200.iloc[-1]
    
    if current_ema > current_sma:
        return "LONG", f"50 EMA ({current_ema:.1f}) > 200 SMA ({current_sma:.1f})", current_ema, current_sma
    elif current_ema < current_sma:
        return "SHORT", f"50 EMA ({current_ema:.1f}) < 200 SMA ({current_sma:.1f})", current_ema, current_sma
    else:
        return "NEUTRAL", "50 EMA = 200 SMA", current_ema, current_sma

def analyze_vix_zone(vix_high, vix_low, vix_current):
    """Pillar 3: Determine VIX Zone (timing signal)."""
    if vix_high <= 0 or vix_low <= 0 or vix_current <= 0:
        return "WAIT", "Invalid VIX values"
    
    vix_range = (vix_high - vix_low) / vix_high * 100
    midpoint = (vix_high + vix_low) / 2
    
    if vix_range > 7:
        return "WAIT", f"Range {vix_range:.1f}% > 7% threshold"
    
    if vix_current < midpoint:
        return "CALLS", f"VIX in lower half (range {vix_range:.1f}%)"
    else:
        return "PUTS", f"VIX in upper half (range {vix_range:.1f}%)"

def calculate_cone_rails(high, low, close):
    """Calculate the three cone rails with ±17.1 expansion."""
    expansion = BLOCKS * SLOPE  # 36 × 0.475 = 17.1
    
    cones = {
        'HIGH': {'anchor': high, 'upper': high + expansion, 'lower': high - expansion},
        'LOW': {'anchor': low, 'upper': low + expansion, 'lower': low - expansion},
        'CLOSE': {'anchor': close, 'upper': close + expansion, 'lower': close - expansion}
    }
    
    return cones, expansion

def get_structure_levels(cones):
    """Determine floor and ceiling from cone rails."""
    # Floor = lowest descending rail
    floor = min(cones['HIGH']['lower'], cones['LOW']['lower'], cones['CLOSE']['lower'])
    # Ceiling = highest ascending rail
    ceiling = max(cones['HIGH']['upper'], cones['LOW']['upper'], cones['CLOSE']['upper'])
    
    return floor, ceiling

def calculate_strike(entry_level, direction):
    """Calculate strike price based on entry level and direction."""
    if direction == "CALLS":
        raw_strike = entry_level + OTM_DISTANCE
    else:  # PUTS
        raw_strike = entry_level - OTM_DISTANCE
    
    # Round to nearest 5
    return round(raw_strike / 5) * 5

def format_option_ticker(strike, is_call, trade_date):
    """Format the SPXW option ticker for Polygon API."""
    date_str = trade_date.strftime("%y%m%d")
    option_type = "C" if is_call else "P"
    strike_str = f"{int(strike * 1000):08d}"
    return f"O:SPXW{date_str}{option_type}{strike_str}"

def fetch_option_data(ticker):
    """Fetch option data from Polygon.io."""
    try:
        url = f"https://api.polygon.io/v3/snapshot/options/SPXW/{ticker}?apiKey={POLYGON_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                return data['results']
    except Exception as e:
        st.warning(f"Could not fetch option data: {e}")
    return None

def generate_signal(ma_bias, vix_signal):
    """Generate trade signal from pillar alignment."""
    if ma_bias == "NEUTRAL":
        return "NO TRADE", "MA bias is neutral"
    
    if vix_signal == "WAIT":
        return "WAIT", "VIX range too wide (>7%)"
    
    if ma_bias == "LONG" and vix_signal == "CALLS":
        return "CALLS", "All pillars aligned bullish"
    elif ma_bias == "SHORT" and vix_signal == "PUTS":
        return "PUTS", "All pillars aligned bearish"
    else:
        return "NO TRADE", f"Conflict: MA {ma_bias} vs VIX {vix_signal}"

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # Get current time in CT
    now_ct = datetime.now(CT)
    
    # ========================================================================
    # SIDEBAR - User Inputs
    # ========================================================================
    with st.sidebar:
        st.markdown("### 🔮 SPX Prophet")
        st.markdown("---")
        
        # Trading Date
        st.markdown("#### 📅 Trading Date")
        trade_date = st.date_input(
            "Select Date",
            value=now_ct.date(),
            min_value=datetime(2024, 1, 1).date(),
            max_value=datetime(2027, 12, 31).date(),
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # VIX Zone Inputs
        st.markdown("#### 📊 VIX Zone")
        vix_high = st.number_input("Overnight High", value=0.0, step=0.01, format="%.2f")
        vix_low = st.number_input("Overnight Low", value=0.0, step=0.01, format="%.2f")
        vix_current = st.number_input("Current VIX", value=0.0, step=0.01, format="%.2f")
        
        st.markdown("---")
        
        # Prior Day SPX
        st.markdown("#### 📈 Prior Day SPX (3pm CT)")
        prior_high = st.number_input("High", value=0.0, step=0.01, format="%.2f", key="prior_high")
        prior_low = st.number_input("Low", value=0.0, step=0.01, format="%.2f", key="prior_low")
        prior_close = st.number_input("Close", value=0.0, step=0.01, format="%.2f", key="prior_close")
        
        st.markdown("---")
        
        # Structure Override
        st.markdown("#### 🔧 Structure Override")
        use_override = st.checkbox("Enable Manual Override")
        
        if use_override:
            manual_ceiling = st.number_input("Manual Ceiling", value=0.0, step=0.01, format="%.2f")
            manual_floor = st.number_input("Manual Floor", value=0.0, step=0.01, format="%.2f")
        else:
            manual_ceiling = None
            manual_floor = None
        
        st.markdown("---")
        
        # Advanced Settings
        with st.expander("⚙️ Advanced Settings"):
            es_offset = st.number_input("ES-SPX Offset", value=DEFAULT_OFFSET, step=0.1, format="%.1f")
        
        # Refresh button
        st.markdown("---")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
    
    # ========================================================================
    # FETCH MARKET DATA
    # ========================================================================
    es_price = get_es_price()
    es_history = get_es_history()
    
    spx_price = es_price - es_offset if es_price else None
    
    # ========================================================================
    # HERO HEADER
    # ========================================================================
    spx_display = f"{spx_price:.2f}" if spx_price else "---"
    
    st.markdown(f"""
    <div class="hero-header">
        <div class="hero-title">🔮 SPX PROPHET</div>
        <div class="hero-tagline">Where Structure Becomes Foresight</div>
        <div class="hero-price">SPX {spx_display}</div>
        <div class="hero-time">{now_ct.strftime('%I:%M:%S %p CT')} • {trade_date.strftime('%B %d, %Y')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================================================
    # THREE PILLARS
    # ========================================================================
    st.markdown("### The Three Pillars")
    
    # Analyze pillars
    ma_bias, ma_detail, ema_val, sma_val = analyze_ma_bias(es_history, es_offset)
    vix_signal, vix_detail = analyze_vix_zone(vix_high, vix_low, vix_current)
    
    # Pillar 2: Day Structure
    if prior_high > 0 and prior_low > 0 and prior_close > 0:
        cones, expansion = calculate_cone_rails(prior_high, prior_low, prior_close)
        calc_floor, calc_ceiling = get_structure_levels(cones)
        
        if use_override and manual_floor and manual_ceiling:
            floor, ceiling = manual_floor, manual_ceiling
            structure_detail = f"Manual: Floor {floor:.1f}, Ceiling {ceiling:.1f}"
        else:
            floor, ceiling = calc_floor, calc_ceiling
            structure_detail = f"Floor {floor:.1f}, Ceiling {ceiling:.1f}"
        
        if ma_bias == "LONG":
            entry_level = floor
            structure_answer = "FLOOR"
        elif ma_bias == "SHORT":
            entry_level = ceiling
            structure_answer = "CEILING"
        else:
            entry_level = None
            structure_answer = "N/A"
    else:
        cones = None
        floor = ceiling = entry_level = None
        structure_answer = "PENDING"
        structure_detail = "Enter prior day SPX values"
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        bias_class = "bullish" if ma_bias == "LONG" else "bearish" if ma_bias == "SHORT" else "neutral"
        st.markdown(f"""
        <div class="pillar-card">
            <div class="pillar-title">Pillar 1 • MA Bias</div>
            <div class="pillar-question">Which direction are we trading?</div>
            <div class="pillar-answer {bias_class}">{ma_bias}</div>
            <div class="pillar-detail">{ma_detail}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        struct_class = "bullish" if structure_answer == "FLOOR" else "bearish" if structure_answer == "CEILING" else "neutral"
        st.markdown(f"""
        <div class="pillar-card">
            <div class="pillar-title">Pillar 2 • Day Structure</div>
            <div class="pillar-question">Where is our entry level?</div>
            <div class="pillar-answer {struct_class}">{structure_answer}</div>
            <div class="pillar-detail">{structure_detail}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        vix_class = "bullish" if vix_signal == "CALLS" else "bearish" if vix_signal == "PUTS" else "neutral"
        st.markdown(f"""
        <div class="pillar-card">
            <div class="pillar-title">Pillar 3 • VIX Zone</div>
            <div class="pillar-question">What's the timing signal?</div>
            <div class="pillar-answer {vix_class}">{vix_signal}</div>
            <div class="pillar-detail">{vix_detail}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # SIGNAL CARD
    # ========================================================================
    signal, signal_reason = generate_signal(ma_bias, vix_signal)
    
    signal_class = signal.lower().replace(" ", "")
    if signal == "CALLS":
        signal_color = "#00ff88"
    elif signal == "PUTS":
        signal_color = "#ff4757"
    elif signal == "WAIT":
        signal_color = "#ffa502"
    else:
        signal_color = "rgba(255, 255, 255, 0.5)"
    
    # Calculate strike if we have a valid signal
    strike = None
    option_data = None
    option_ticker = None
    
    if signal in ["CALLS", "PUTS"] and entry_level:
        strike = calculate_strike(entry_level, signal)
        option_ticker = format_option_ticker(strike, signal == "CALLS", trade_date)
        option_data = fetch_option_data(option_ticker)
    
    entry_display = f"{entry_level:.1f}" if entry_level else "---"
    strike_display = str(strike) if strike else "---"
    
    st.markdown(f"""
    <div class="signal-card {signal_class}">
        <div class="signal-action" style="color: {signal_color};">{signal}</div>
        <div class="signal-reason">{signal_reason}</div>
        <div class="signal-details">
            <div class="signal-detail-item">
                <div class="signal-detail-label">Entry Level</div>
                <div class="signal-detail-value">{entry_display}</div>
            </div>
            <div class="signal-detail-item">
                <div class="signal-detail-label">Strike</div>
                <div class="signal-detail-value">{strike_display}</div>
            </div>
            <div class="signal-detail-item">
                <div class="signal-detail-label">Entry Time</div>
                <div class="signal-detail-value">{ENTRY_TIME}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================================================
    # CONE RAILS TABLE & OPTIONS PANEL
    # ========================================================================
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("### 📐 Cone Rails")
        
        if cones:
            st.markdown(f"""
            <div class="glass-card">
                <table class="cone-table">
                    <thead>
                        <tr>
                            <th>Anchor</th>
                            <th>Level</th>
                            <th class="cone-up">Ascending (+)</th>
                            <th class="cone-down">Descending (-)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="cone-label">HIGH</td>
                            <td>{cones['HIGH']['anchor']:.1f}</td>
                            <td class="cone-up">{cones['HIGH']['upper']:.1f}</td>
                            <td class="cone-down">{cones['HIGH']['lower']:.1f}</td>
                        </tr>
                        <tr>
                            <td class="cone-label">LOW</td>
                            <td>{cones['LOW']['anchor']:.1f}</td>
                            <td class="cone-up">{cones['LOW']['upper']:.1f}</td>
                            <td class="cone-down">{cones['LOW']['lower']:.1f}</td>
                        </tr>
                        <tr>
                            <td class="cone-label">CLOSE</td>
                            <td>{cones['CLOSE']['anchor']:.1f}</td>
                            <td class="cone-up">{cones['CLOSE']['upper']:.1f}</td>
                            <td class="cone-down">{cones['CLOSE']['lower']:.1f}</td>
                        </tr>
                    </tbody>
                </table>
                <div style="text-align: center; margin-top: 1rem; color: var(--text-secondary); font-size: 0.8rem;">
                    {BLOCKS} blocks • ±{expansion:.1f} pts • Slope {SLOPE}/block
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Enter prior day SPX values to calculate cone rails")
    
    with col_right:
        st.markdown("### 📊 Options Data")
        
        if option_data:
            day = option_data.get('day', {})
            greeks = option_data.get('greeks', {})
            details = option_data.get('details', {})
            
            last_quote = option_data.get('last_quote', {})
            
            st.markdown(f"""
            <div class="glass-card">
                <div style="text-align: center; margin-bottom: 1rem;">
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; color: var(--accent-blue);">
                        {option_ticker}
                    </div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">
                        {strike} {signal[:-1] if signal in ['CALLS', 'PUTS'] else ''} • Exp {trade_date.strftime('%m/%d/%y')}
                    </div>
                </div>
                <div class="options-grid">
                    <div class="options-item">
                        <div class="options-label">Last</div>
                        <div class="options-value">${day.get('close', day.get('last', 0)):.2f}</div>
                    </div>
                    <div class="options-item">
                        <div class="options-label">Bid</div>
                        <div class="options-value">${last_quote.get('bid', 0):.2f}</div>
                    </div>
                    <div class="options-item">
                        <div class="options-label">Ask</div>
                        <div class="options-value">${last_quote.get('ask', 0):.2f}</div>
                    </div>
                    <div class="options-item">
                        <div class="options-label">Volume</div>
                        <div class="options-value">{day.get('volume', 0):,}</div>
                    </div>
                    <div class="options-item">
                        <div class="options-label">Open Int</div>
                        <div class="options-value">{option_data.get('open_interest', 0):,}</div>
                    </div>
                    <div class="options-item">
                        <div class="options-label">50% Stop</div>
                        <div class="options-value">${day.get('close', day.get('last', 0)) / 2:.2f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif option_ticker:
            st.markdown(f"""
            <div class="glass-card">
                <div style="text-align: center; color: var(--text-secondary);">
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; margin-bottom: 0.5rem;">
                        {option_ticker}
                    </div>
                    <div>Waiting for market data...</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Generate a signal to view options data")
    
    # ========================================================================
    # FOOTER
    # ========================================================================
    st.markdown(f"""
    <div class="footer">
        Last refresh: {now_ct.strftime('%I:%M:%S %p CT')} • Entry: {ENTRY_TIME} • All values in SPX
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

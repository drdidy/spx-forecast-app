"""
SPX PROPHET™
Where Structure Becomes Foresight

Professional 0DTE SPX Options Trading System
All values displayed in SPX - ES conversion handled internally
"""

import streamlit as st
import requests
import json
import os
from datetime import datetime, timedelta, date
from dataclasses import dataclass, field
from typing import Optional, List, Dict
import calendar
import pytz

# ============================================================
# CONFIGURATION - ALL SPX FOCUSED
# ============================================================

CT = pytz.timezone("America/Chicago")
POLYGON_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
SETTINGS_FILE = "prophet_settings.json"

# Trading System Constants
SLOPE_PER_BLOCK = 0.475      # Points per 30-min block
BLOCKS_OVERNIGHT = 36         # 3pm to 9am = 36 blocks
OTM_DISTANCE = 15            # Strike is 15 points OTM from entry
ENTRY_TIME = "9:00 AM CT"

# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class Settings:
    """User settings - persisted between sessions"""
    # Trading date
    trade_year: int = 2026
    trade_month: int = 1
    trade_day: int = 10
    
    # VIX inputs (from TradingView)
    vix_high: float = 0.0
    vix_low: float = 0.0
    vix_now: float = 0.0
    
    # Prior day SPX levels (user enters these)
    prior_high: float = 0.0
    prior_low: float = 0.0
    prior_close: float = 0.0
    
    # Structure override
    use_manual: bool = False
    ceiling: float = 0.0
    floor: float = 0.0
    
    # ES to SPX offset (for internal conversion)
    offset: float = 7.0

@dataclass
class Pillar1:
    """MA Bias - Direction Filter"""
    ema50: float = 0.0
    sma200: float = 0.0
    direction: str = "NEUTRAL"  # LONG, SHORT, NEUTRAL
    
    @property
    def is_valid(self) -> bool:
        return self.direction in ["LONG", "SHORT"]

@dataclass
class Pillar2:
    """Day Structure - Entry Level"""
    ceiling: float = 0.0
    floor: float = 0.0
    entry_type: str = "NONE"  # CEILING, FLOOR, NONE
    entry_level: float = 0.0
    is_manual: bool = False
    
    @property
    def is_valid(self) -> bool:
        return self.entry_level > 0

@dataclass
class Pillar3:
    """VIX Zone - Timing Signal"""
    high: float = 0.0
    low: float = 0.0
    current: float = 0.0
    range_pct: float = 0.0
    zone: str = "UNKNOWN"  # LOWER, UPPER, OUTSIDE
    signal: str = "WAIT"   # CALLS, PUTS, WAIT
    
    @property
    def is_valid(self) -> bool:
        return self.signal in ["CALLS", "PUTS"]

@dataclass
class ConeData:
    """Cone Rails Projection"""
    high_up: float = 0.0
    high_down: float = 0.0
    low_up: float = 0.0
    low_down: float = 0.0
    close_up: float = 0.0
    close_down: float = 0.0
    expansion: float = 0.0

@dataclass
class Signal:
    """Final Trade Signal"""
    action: str = "NO TRADE"  # CALLS, PUTS, WAIT, NO TRADE
    entry: float = 0.0
    strike: int = 0
    reason: str = ""
    all_aligned: bool = False

@dataclass
class OptionQuote:
    """Options Data"""
    ticker: str = ""
    strike: int = 0
    type: str = ""
    last: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    volume: int = 0
    oi: int = 0

# ============================================================
# PERSISTENCE
# ============================================================

def load_settings() -> Settings:
    """Load saved settings"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                return Settings(**data)
    except:
        pass
    return Settings()

def save_settings(s: Settings):
    """Save settings to file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(s.__dict__, f)
    except:
        pass

# ============================================================
# MARKET DATA APIs
# ============================================================

def fetch_spx_price(offset: float) -> float:
    """Fetch current SPX price (via ES conversion)"""
    try:
        import yfinance as yf
        es = yf.Ticker("ES=F").history(period="1d")
        if not es.empty:
            return float(es['Close'].iloc[-1]) - offset
    except:
        pass
    return 0.0

def fetch_spx_history(offset: float) -> List[float]:
    """Fetch SPX closing prices for MA calculation"""
    try:
        import yfinance as yf
        es = yf.Ticker("ES=F").history(period="250d", interval="1d")
        if not es.empty:
            return [float(row["Close"]) - offset for _, row in es.iterrows()]
    except:
        pass
    return []

def fetch_option_quote(strike: int, opt_type: str, exp_date: date) -> Optional[OptionQuote]:
    """Fetch SPXW option quote from Polygon"""
    try:
        exp_str = exp_date.strftime("%y%m%d")
        t = "C" if opt_type == "CALL" else "P"
        strike_fmt = str(int(strike * 1000)).zfill(8)
        ticker = f"O:SPXW{exp_str}{t}{strike_fmt}"
        
        url = f"https://api.polygon.io/v3/snapshot/options/SPXW/{ticker}?apiKey={POLYGON_KEY}"
        r = requests.get(url, timeout=10)
        
        if r.status_code == 200 and "results" in r.json():
            res = r.json()["results"]
            day = res.get("day", {})
            quote = res.get("last_quote", {})
            return OptionQuote(
                ticker=ticker,
                strike=strike,
                type=opt_type,
                last=float(day.get("close", 0) or 0),
                bid=float(quote.get("bid", 0) or 0),
                ask=float(quote.get("ask", 0) or 0),
                volume=int(day.get("volume", 0) or 0),
                oi=int(res.get("open_interest", 0) or 0)
            )
    except:
        pass
    return None

# ============================================================
# CALCULATION ENGINE - ALL VALUES IN SPX
# ============================================================

def calc_ema(prices: List[float], n: int) -> float:
    """Exponential Moving Average"""
    if len(prices) < n:
        return prices[-1] if prices else 0.0
    k = 2 / (n + 1)
    ema = sum(prices[:n]) / n
    for p in prices[n:]:
        ema = p * k + ema * (1 - k)
    return ema

def calc_sma(prices: List[float], n: int) -> float:
    """Simple Moving Average"""
    if not prices:
        return 0.0
    if len(prices) < n:
        return sum(prices) / len(prices)
    return sum(prices[-n:]) / n

def analyze_pillar1(spx_prices: List[float]) -> Pillar1:
    """
    PILLAR 1: MA Bias
    Determines if we're looking for CALLS or PUTS
    50 EMA > 200 SMA = LONG (CALLS)
    50 EMA < 200 SMA = SHORT (PUTS)
    """
    if len(spx_prices) < 50:
        return Pillar1(0, 0, "NEUTRAL")
    
    ema50 = calc_ema(spx_prices, 50)
    sma200 = calc_sma(spx_prices, 200)
    
    if ema50 > sma200:
        direction = "LONG"
    elif ema50 < sma200:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"
    
    return Pillar1(round(ema50, 2), round(sma200, 2), direction)

def analyze_pillar2(p1: Pillar1, ceiling: float, floor: float, is_manual: bool) -> Pillar2:
    """
    PILLAR 2: Day Structure
    Determines entry level based on MA direction
    LONG = Enter at FLOOR (support)
    SHORT = Enter at CEILING (resistance)
    """
    if p1.direction == "LONG":
        return Pillar2(ceiling, floor, "FLOOR", floor, is_manual)
    elif p1.direction == "SHORT":
        return Pillar2(ceiling, floor, "CEILING", ceiling, is_manual)
    else:
        return Pillar2(ceiling, floor, "NONE", 0, is_manual)

def analyze_pillar3(vix_high: float, vix_low: float, vix_now: float) -> Pillar3:
    """
    PILLAR 3: VIX Zone
    Timing signal based on VIX position in overnight range
    Range <= 7%: Lower half = CALLS, Upper half = PUTS
    Range > 7%: WAIT
    """
    if vix_high <= vix_low or vix_high == 0:
        return Pillar3(vix_high, vix_low, vix_now, 0, "UNKNOWN", "WAIT")
    
    range_pct = ((vix_high - vix_low) / vix_high) * 100
    midpoint = (vix_high + vix_low) / 2
    
    if range_pct > 7:
        return Pillar3(vix_high, vix_low, vix_now, round(range_pct, 1), "OUTSIDE", "WAIT")
    
    if vix_now <= midpoint:
        return Pillar3(vix_high, vix_low, vix_now, round(range_pct, 1), "LOWER", "CALLS")
    else:
        return Pillar3(vix_high, vix_low, vix_now, round(range_pct, 1), "UPPER", "PUTS")

def calc_cones(prior_high: float, prior_low: float, prior_close: float) -> ConeData:
    """
    Calculate Cone Rails from 3pm close to 9am entry
    All values in SPX
    """
    exp = BLOCKS_OVERNIGHT * SLOPE_PER_BLOCK  # 36 * 0.475 = 17.1
    
    return ConeData(
        high_up=round(prior_high + exp, 0),
        high_down=round(prior_high - exp, 0),
        low_up=round(prior_low + exp, 0),
        low_down=round(prior_low - exp, 0),
        close_up=round(prior_close + exp, 0),
        close_down=round(prior_close - exp, 0),
        expansion=round(exp, 1)
    )

def generate_signal(p1: Pillar1, p2: Pillar2, p3: Pillar3) -> Signal:
    """
    Generate final trade signal
    All 3 pillars must align for a trade
    """
    # No direction = no trade
    if p1.direction == "NEUTRAL":
        return Signal("NO TRADE", 0, 0, "MA Bias is neutral - no directional edge", False)
    
    # Calculate strike (15 points OTM from entry)
    if p1.direction == "LONG":
        entry = p2.floor
        strike = int(round((entry + OTM_DISTANCE) / 5) * 5)
        needed_signal = "CALLS"
    else:
        entry = p2.ceiling
        strike = int(round((entry - OTM_DISTANCE) / 5) * 5)
        needed_signal = "PUTS"
    
    # Check alignment
    if p3.signal == needed_signal:
        return Signal(needed_signal, entry, strike, 
                     f"✓ All 3 pillars aligned for {needed_signal}", True)
    elif p3.signal == "WAIT":
        return Signal("WAIT", entry, strike,
                     f"MA says {p1.direction} - waiting for VIX {needed_signal} signal", False)
    else:
        return Signal("NO TRADE", entry, 0,
                     f"Conflict: MA={p1.direction} but VIX={p3.signal}", False)

# ============================================================
# DESIGN SYSTEM - MODERN DASHBOARD
# ============================================================

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

* { box-sizing: border-box; }

:root {
    --black: #000000;
    --bg: #050508;
    --surface: #0c0c10;
    --card: #111116;
    --border: #1c1c24;
    --hover: #18181f;
    --white: #ffffff;
    --gray: #888899;
    --muted: #444455;
    --green: #22c55e;
    --green-bg: #22c55e15;
    --red: #ef4444;
    --red-bg: #ef444415;
    --amber: #f59e0b;
    --amber-bg: #f59e0b15;
    --blue: #3b82f6;
}

html, body, .stApp {
    background: var(--bg) !important;
    color: var(--white);
    font-family: 'Space Grotesk', system-ui, sans-serif;
}

/* Hide Streamlit stuff */
#MainMenu, footer, header, .stDeployButton, [data-testid="stToolbar"] { 
    display: none !important; 
}

.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
    width: 320px !important;
}

section[data-testid="stSidebar"] > div {
    padding: 1.5rem !important;
}

/* Form inputs */
.stNumberInput input, .stTextInput input, .stSelectbox > div > div {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--white) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 14px !important;
}

.stNumberInput input:focus, .stTextInput input:focus {
    border-color: var(--green) !important;
    box-shadow: 0 0 0 3px var(--green-bg) !important;
}

.stButton button {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--white) !important;
    font-weight: 600 !important;
    padding: 0.6rem 1rem !important;
    transition: all 0.15s !important;
}

.stButton button:hover {
    background: var(--hover) !important;
    border-color: var(--gray) !important;
}

.stButton button[kind="primary"] {
    background: var(--green) !important;
    border-color: var(--green) !important;
    color: var(--black) !important;
}

.stCheckbox label { color: var(--gray) !important; }
hr { border-color: var(--border) !important; margin: 1.5rem 0 !important; }

/* ===== CUSTOM COMPONENTS ===== */

.top-bar {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.brand-icon {
    font-size: 28px;
}

.brand-text {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
}

.brand-tag {
    font-size: 10px;
    color: var(--green);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-left: 12px;
    padding: 4px 8px;
    background: var(--green-bg);
    border-radius: 4px;
}

.price-box {
    text-align: right;
}

.price-label {
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
}

.price-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 32px;
    font-weight: 700;
}

.price-meta {
    font-size: 12px;
    color: var(--gray);
}

/* Main content */
.content {
    padding: 2rem;
}

/* Section titles */
.section-title {
    font-size: 11px;
    font-weight: 700;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
}

/* Pillar cards - NEW DESIGN */
.pillar-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 2rem;
}

.pillar {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    position: relative;
    overflow: hidden;
}

.pillar.active { border-color: var(--green); }
.pillar.active::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--green);
}

.pillar.waiting { border-color: var(--amber); }
.pillar.waiting::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--amber);
}

.pillar.inactive { border-color: var(--red); }
.pillar.inactive::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--red);
}

.pillar-num {
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.5rem;
}

.pillar-name {
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 0.25rem;
}

.pillar-q {
    font-size: 13px;
    color: var(--gray);
    margin-bottom: 1rem;
}

.pillar-answer {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 28px;
    font-weight: 700;
}

.pillar-answer.green { color: var(--green); }
.pillar-answer.red { color: var(--red); }
.pillar-answer.amber { color: var(--amber); }

.pillar-detail {
    font-size: 12px;
    color: var(--gray);
    margin-top: 0.5rem;
}

/* Signal card - BIG AND BOLD */
.signal-box {
    background: var(--card);
    border: 2px solid var(--border);
    border-radius: 16px;
    padding: 2.5rem;
    text-align: center;
    margin-bottom: 2rem;
}

.signal-box.calls {
    border-color: var(--green);
    background: linear-gradient(180deg, var(--green-bg) 0%, var(--card) 100%);
}

.signal-box.puts {
    border-color: var(--red);
    background: linear-gradient(180deg, var(--red-bg) 0%, var(--card) 100%);
}

.signal-box.wait {
    border-color: var(--amber);
    background: linear-gradient(180deg, var(--amber-bg) 0%, var(--card) 100%);
}

.signal-action {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 64px;
    font-weight: 700;
    letter-spacing: -2px;
}

.signal-action.green { color: var(--green); }
.signal-action.red { color: var(--red); }
.signal-action.amber { color: var(--amber); }
.signal-action.muted { color: var(--muted); }

.signal-reason {
    font-size: 14px;
    color: var(--gray);
    margin-top: 0.5rem;
}

.signal-metrics {
    display: flex;
    justify-content: center;
    gap: 4rem;
    margin-top: 2rem;
}

.metric {
    text-align: center;
}

.metric-label {
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.5rem;
}

.metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 24px;
    font-weight: 700;
}

.metric-value.red { color: var(--red); }

/* Bottom grid */
.bottom-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
}

.data-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
}

.data-card-title {
    font-size: 11px;
    font-weight: 700;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 1rem;
}

/* Cone table */
.cone-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0;
}

.cone-cell {
    padding: 0.75rem;
    text-align: center;
    border-bottom: 1px solid var(--border);
}

.cone-cell.header {
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
}

.cone-cell.label {
    text-align: left;
    font-size: 13px;
    color: var(--gray);
}

.cone-cell.up {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 15px;
    font-weight: 600;
    color: var(--green);
}

.cone-cell.down {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 15px;
    font-weight: 600;
    color: var(--red);
}

.cone-footer {
    font-size: 11px;
    color: var(--muted);
    text-align: center;
    margin-top: 1rem;
}

/* Options grid */
.opt-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
}

.opt-cell {
    background: var(--surface);
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}

.opt-label {
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.5rem;
}

.opt-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 18px;
    font-weight: 600;
}

.opt-value.green { color: var(--green); }
.opt-value.muted { color: var(--muted); }

.opt-footer {
    font-size: 11px;
    color: var(--muted);
    text-align: center;
    margin-top: 1rem;
    grid-column: span 2;
}

/* Sidebar components */
.sidebar-brand {
    text-align: center;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.5rem;
}

.sidebar-icon {
    font-size: 36px;
    margin-bottom: 0.5rem;
}

.sidebar-title {
    font-size: 20px;
    font-weight: 700;
}

.sidebar-tag {
    font-size: 9px;
    color: var(--green);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 0.25rem;
}

.sidebar-section {
    margin-bottom: 1.5rem;
}

.sidebar-section-title {
    font-size: 12px;
    font-weight: 700;
    color: var(--white);
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Date selector */
.date-selector {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
}

.date-selected {
    background: var(--green-bg);
    border: 1px solid var(--green);
    border-radius: 8px;
    padding: 0.75rem;
    text-align: center;
    margin-top: 0.75rem;
}

.date-day {
    font-size: 15px;
    font-weight: 700;
    color: var(--green);
}

.date-full {
    font-size: 12px;
    color: var(--gray);
}

.date-weekend {
    background: var(--red-bg);
    border: 1px solid var(--red);
    border-radius: 8px;
    padding: 0.75rem;
    text-align: center;
    margin-top: 0.75rem;
}

.date-weekend-text {
    font-size: 13px;
    color: var(--red);
    font-weight: 600;
}

/* Footer */
.app-footer {
    padding: 1rem 2rem;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: var(--muted);
}
</style>
"""

# ============================================================
# MAIN APPLICATION
# ============================================================

def app():
    # Page config
    st.set_page_config(
        page_title="SPX Prophet",
        page_icon="🔮",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inject CSS
    st.markdown(CSS, unsafe_allow_html=True)
    
    # Session state
    if "settings" not in st.session_state:
        st.session_state.settings = load_settings()
    if "spx_price" not in st.session_state:
        st.session_state.spx_price = 0.0
    if "spx_history" not in st.session_state:
        st.session_state.spx_history = []
    if "last_fetch" not in st.session_state:
        st.session_state.last_fetch = None
    if "option" not in st.session_state:
        st.session_state.option = None
    
    s = st.session_state.settings
    
    # ============================================================
    # SIDEBAR
    # ============================================================
    with st.sidebar:
        # Brand
        st.markdown("""
        <div class="sidebar-brand">
            <div class="sidebar-icon">🔮</div>
            <div class="sidebar-title">SPX Prophet</div>
            <div class="sidebar-tag">Structure → Foresight</div>
        </div>
        """, unsafe_allow_html=True)
        
        # === DATE SELECTION ===
        st.markdown('<div class="sidebar-section-title">📅 Trading Date</div>', unsafe_allow_html=True)
        
        today = datetime.now(CT).date()
        
        # Quick buttons
        qc1, qc2, qc3 = st.columns(3)
        with qc1:
            if st.button("Today", key="d_today", use_container_width=True):
                s.trade_year, s.trade_month, s.trade_day = today.year, today.month, today.day
                st.session_state.option = None
                st.rerun()
        with qc2:
            yday = today - timedelta(days=1)
            if st.button("Yest", key="d_yest", use_container_width=True):
                s.trade_year, s.trade_month, s.trade_day = yday.year, yday.month, yday.day
                st.session_state.option = None
                st.rerun()
        with qc3:
            # Last Friday
            diff = (today.weekday() - 4) % 7 or 7
            fri = today - timedelta(days=diff)
            if st.button("Fri", key="d_fri", use_container_width=True):
                s.trade_year, s.trade_month, s.trade_day = fri.year, fri.month, fri.day
                st.session_state.option = None
                st.rerun()
        
        # Date dropdowns in a clean card
        st.markdown('<div class="date-selector">', unsafe_allow_html=True)
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            years = list(range(2024, 2028))
            idx = years.index(s.trade_year) if s.trade_year in years else 2
            s.trade_year = st.selectbox("Year", years, index=idx, key="sel_y", label_visibility="collapsed")
        with dc2:
            mos = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            s.trade_month = st.selectbox("Month", range(1,13), index=s.trade_month-1, 
                                          format_func=lambda x: mos[x-1], key="sel_m", label_visibility="collapsed")
        with dc3:
            max_d = calendar.monthrange(s.trade_year, s.trade_month)[1]
            s.trade_day = min(s.trade_day, max_d)
            s.trade_day = st.selectbox("Day", range(1, max_d+1), index=s.trade_day-1, key="sel_d", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Show selected date
        sel_date = date(s.trade_year, s.trade_month, s.trade_day)
        if sel_date.weekday() >= 5:
            st.markdown(f"""
            <div class="date-weekend">
                <div class="date-weekend-text">⚠️ {sel_date.strftime('%A')} - Weekend</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="date-selected">
                <div class="date-day">{sel_date.strftime('%A')}</div>
                <div class="date-full">{sel_date.strftime('%B %d, %Y')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # === VIX INPUTS ===
        st.markdown('<div class="sidebar-section-title">📊 VIX Zone</div>', unsafe_allow_html=True)
        st.caption("From TradingView overnight")
        vc1, vc2 = st.columns(2)
        s.vix_high = vc1.number_input("High", value=s.vix_high, format="%.2f", step=0.01, key="vix_h")
        s.vix_low = vc2.number_input("Low", value=s.vix_low, format="%.2f", step=0.01, key="vix_l")
        s.vix_now = st.number_input("Current", value=s.vix_now, format="%.2f", step=0.01, key="vix_c")
        
        st.markdown("---")
        
        # === PRIOR DAY SPX ===
        st.markdown('<div class="sidebar-section-title">📈 Prior Day (SPX)</div>', unsafe_allow_html=True)
        st.caption("Enter SPX values from 3pm close")
        pc1, pc2, pc3 = st.columns(3)
        s.prior_high = pc1.number_input("High", value=s.prior_high, format="%.0f", step=1.0, key="p_h")
        s.prior_low = pc2.number_input("Low", value=s.prior_low, format="%.0f", step=1.0, key="p_l")
        s.prior_close = pc3.number_input("Close", value=s.prior_close, format="%.0f", step=1.0, key="p_c")
        
        st.markdown("---")
        
        # === STRUCTURE OVERRIDE ===
        st.markdown('<div class="sidebar-section-title">🎯 Structure Override</div>', unsafe_allow_html=True)
        s.use_manual = st.checkbox("Use manual levels", value=s.use_manual, key="man_chk")
        if s.use_manual:
            mc1, mc2 = st.columns(2)
            s.ceiling = mc1.number_input("Ceiling", value=s.ceiling, format="%.0f", step=1.0, key="man_c")
            s.floor = mc2.number_input("Floor", value=s.floor, format="%.0f", step=1.0, key="man_f")
        
        st.markdown("---")
        
        # === ES OFFSET (hidden complexity) ===
        with st.expander("⚙️ Advanced"):
            s.offset = st.number_input("ES-SPX Offset", value=s.offset, format="%.1f", step=0.5, key="off")
            st.caption("Used internally to convert ES data to SPX")
        
        st.markdown("---")
        
        # === BUTTONS ===
        if st.button("💾 SAVE", key="btn_save", use_container_width=True, type="primary"):
            save_settings(s)
            st.session_state.option = None
            st.success("✓ Saved!")
        
        if st.button("🔄 Refresh", key="btn_ref", use_container_width=True):
            st.session_state.last_fetch = None
            st.session_state.option = None
            st.rerun()

    # ============================================================
    # DATA FETCHING
    # ============================================================
    need_fetch = (
        st.session_state.last_fetch is None or
        (datetime.now() - st.session_state.last_fetch).seconds > 900
    )
    
    if need_fetch:
        with st.spinner("Loading SPX data..."):
            st.session_state.spx_price = fetch_spx_price(s.offset)
            st.session_state.spx_history = fetch_spx_history(s.offset)
            st.session_state.last_fetch = datetime.now()
    
    spx = st.session_state.spx_price
    history = st.session_state.spx_history
    
    # ============================================================
    # CALCULATIONS
    # ============================================================
    p1 = analyze_pillar1(history)
    
    # For pillar 2, use manual if set, otherwise derive from history
    if s.use_manual and s.ceiling > 0 and s.floor > 0:
        p2 = analyze_pillar2(p1, s.ceiling, s.floor, True)
    else:
        # Use prior day levels as structure
        p2 = analyze_pillar2(p1, s.prior_high, s.prior_low, False)
    
    p3 = analyze_pillar3(s.vix_high, s.vix_low, s.vix_now)
    cones = calc_cones(s.prior_high, s.prior_low, s.prior_close)
    sig = generate_signal(p1, p2, p3)
    
    # Fetch option quote
    sel_date = date(s.trade_year, s.trade_month, s.trade_day)
    if sig.strike > 0 and st.session_state.option is None:
        opt_type = "CALL" if p1.direction == "LONG" else "PUT"
        st.session_state.option = fetch_option_quote(sig.strike, opt_type, sel_date)
    
    opt = st.session_state.option
    now = datetime.now(CT)
    
    # ============================================================
    # TOP BAR
    # ============================================================
    st.markdown(f"""
    <div class="top-bar">
        <div class="brand">
            <span class="brand-icon">🔮</span>
            <span class="brand-text">SPX Prophet</span>
            <span class="brand-tag">Structure → Foresight</span>
        </div>
        <div class="price-box">
            <div class="price-label">SPX</div>
            <div class="price-value">{spx:,.2f}</div>
            <div class="price-meta">{now.strftime('%I:%M %p CT')} • {sel_date.strftime('%b %d, %Y')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ============================================================
    # MAIN CONTENT
    # ============================================================
    st.markdown('<div class="content">', unsafe_allow_html=True)
    
    # Section: Three Pillars
    st.markdown('<div class="section-title">The Three Pillars</div>', unsafe_allow_html=True)
    
    # Pillar statuses
    p1_status = "active" if p1.is_valid else "waiting"
    p1_color = "green" if p1.direction == "LONG" else ("red" if p1.direction == "SHORT" else "amber")
    
    p2_status = "active" if p2.is_valid else "waiting"
    p2_color = "green" if p1.direction == "LONG" else ("red" if p1.direction == "SHORT" else "amber")
    
    p3_status = "active" if p3.is_valid else "waiting"
    p3_color = "green" if p3.signal == "CALLS" else ("red" if p3.signal == "PUTS" else "amber")
    
    manual_tag = " [Manual]" if p2.is_manual else ""
    cmp = ">" if p1.ema50 > p1.sma200 else "<"
    
    st.markdown(f"""
    <div class="pillar-row">
        <div class="pillar {p1_status}">
            <div class="pillar-num">Pillar 1</div>
            <div class="pillar-name">MA Bias</div>
            <div class="pillar-q">CALLS or PUTS today?</div>
            <div class="pillar-answer {p1_color}">{p1.direction}</div>
            <div class="pillar-detail">50 EMA {cmp} 200 SMA</div>
        </div>
        <div class="pillar {p2_status}">
            <div class="pillar-num">Pillar 2</div>
            <div class="pillar-name">Structure</div>
            <div class="pillar-q">Entry @ 9:00 AM CT?</div>
            <div class="pillar-answer {p2_color}">{p2.entry_type}</div>
            <div class="pillar-detail">{p2.entry_level:,.0f} SPX{manual_tag}</div>
        </div>
        <div class="pillar {p3_status}">
            <div class="pillar-num">Pillar 3</div>
            <div class="pillar-name">VIX Zone</div>
            <div class="pillar-q">Pull the trigger?</div>
            <div class="pillar-answer {p3_color}">{p3.signal}</div>
            <div class="pillar-detail">{p3.zone} • {p3.range_pct}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # SIGNAL CARD
    # ============================================================
    sig_class = "calls" if sig.action == "CALLS" else ("puts" if sig.action == "PUTS" else ("wait" if sig.action == "WAIT" else ""))
    sig_color = "green" if sig.action == "CALLS" else ("red" if sig.action == "PUTS" else ("amber" if sig.action == "WAIT" else "muted"))
    
    stop_val = f"${opt.last * 0.5:.2f}" if opt and opt.last > 0 else "—"
    
    st.markdown(f"""
    <div class="section-title">Trade Decision</div>
    <div class="signal-box {sig_class}">
        <div class="signal-action {sig_color}">{sig.action}</div>
        <div class="signal-reason">{sig.reason}</div>
        <div class="signal-metrics">
            <div class="metric">
                <div class="metric-label">Entry</div>
                <div class="metric-value">{sig.entry:,.0f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Strike</div>
                <div class="metric-value">{sig.strike if sig.strike > 0 else '—'}</div>
            </div>
            <div class="metric">
                <div class="metric-label">50% Stop</div>
                <div class="metric-value red">{stop_val}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ============================================================
    # BOTTOM GRID: CONES & OPTIONS
    # ============================================================
    st.markdown('<div class="bottom-grid">', unsafe_allow_html=True)
    
    # Left: Cone Rails
    st.markdown(f"""
    <div class="data-card">
        <div class="data-card-title">Cone Rails @ 9:00 AM</div>
        <div class="cone-grid">
            <div class="cone-cell header">Anchor</div>
            <div class="cone-cell header" style="color: var(--green);">↗ Up</div>
            <div class="cone-cell header" style="color: var(--red);">↘ Down</div>
            
            <div class="cone-cell label">High ({s.prior_high:,.0f})</div>
            <div class="cone-cell up">{cones.high_up:,.0f}</div>
            <div class="cone-cell down">{cones.high_down:,.0f}</div>
            
            <div class="cone-cell label">Low ({s.prior_low:,.0f})</div>
            <div class="cone-cell up">{cones.low_up:,.0f}</div>
            <div class="cone-cell down">{cones.low_down:,.0f}</div>
            
            <div class="cone-cell label">Close ({s.prior_close:,.0f})</div>
            <div class="cone-cell up">{cones.close_up:,.0f}</div>
            <div class="cone-cell down">{cones.close_down:,.0f}</div>
        </div>
        <div class="cone-footer">3pm→9am • 36 blocks • ±{cones.expansion} pts</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Right: Options
    if opt:
        t_disp = "C" if opt.type == "CALL" else "P"
        st.markdown(f"""
        <div class="data-card">
            <div class="data-card-title">0DTE Option</div>
            <div style="font-size: 11px; color: var(--muted); margin-bottom: 1rem; text-align: center;">{opt.ticker}</div>
            <div class="opt-grid">
                <div class="opt-cell">
                    <div class="opt-label">Strike</div>
                    <div class="opt-value green">{opt.strike} {t_disp}</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Last</div>
                    <div class="opt-value">${opt.last:.2f}</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Bid</div>
                    <div class="opt-value">${opt.bid:.2f}</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Ask</div>
                    <div class="opt-value">${opt.ask:.2f}</div>
                </div>
                <div class="opt-footer">Vol: {opt.volume:,} • OI: {opt.oi:,}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        strike_disp = f"{sig.strike} {'C' if p1.direction == 'LONG' else 'P'}" if sig.strike > 0 else "—"
        st.markdown(f"""
        <div class="data-card">
            <div class="data-card-title">0DTE Option</div>
            <div class="opt-grid">
                <div class="opt-cell">
                    <div class="opt-label">Strike</div>
                    <div class="opt-value green">{strike_disp}</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Last</div>
                    <div class="opt-value muted">—</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Bid</div>
                    <div class="opt-value muted">—</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Ask</div>
                    <div class="opt-value muted">—</div>
                </div>
                <div class="opt-footer">Waiting for data...</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # close bottom-grid
    st.markdown('</div>', unsafe_allow_html=True)  # close content
    
    # ============================================================
    # FOOTER
    # ============================================================
    last_str = st.session_state.last_fetch.strftime("%I:%M %p") if st.session_state.last_fetch else "Never"
    st.markdown(f"""
    <div class="app-footer">
        <span>🔄 Refreshed: {last_str}</span>
        <span>Entry Window: 9:00 AM CT • All values in SPX</span>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    app()

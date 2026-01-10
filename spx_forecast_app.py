"""
SPX Prophet Pro - 0DTE Trading System
Where Structure Becomes Foresight™

Professional-grade options trading decision support.
"""

import streamlit as st
import requests
import json
import os
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import calendar
import pytz

# ============================================================
# CONFIGURATION
# ============================================================

CT = pytz.timezone("America/Chicago")
POLYGON_API_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
INPUTS_FILE = "spx_prophet_inputs.json"
CONE_SLOPE = 0.475
BLOCKS_3PM_TO_9AM = 36  # 18 hours = 36 half-hour blocks

# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class ManualInputs:
    vix_overnight_high: float = 0.0
    vix_overnight_low: float = 0.0
    vix_current: float = 0.0
    es_spx_offset: float = 7.0
    prior_high: float = 0.0
    prior_low: float = 0.0
    prior_close: float = 0.0
    manual_ceiling: float = 0.0
    manual_floor: float = 0.0
    use_manual_structure: bool = False
    trading_date: str = ""

@dataclass
class MABias:
    ema_50: float
    sma_200: float
    bias: str  # LONG, SHORT, NEUTRAL

@dataclass
class VIXZone:
    high: float
    low: float
    current: float
    range_pct: float
    position: str
    signal: str  # CALLS, PUTS, WAIT

@dataclass
class DayStructure:
    ceiling: float
    floor: float
    is_manual: bool

@dataclass
class ConeRails:
    c1_asc: float
    c1_desc: float
    c2_asc: float
    c2_desc: float
    c3_asc: float
    c3_desc: float
    blocks: int
    expansion: float

@dataclass
class TradeSignal:
    direction: str  # CALLS, PUTS, WAIT, NO TRADE
    entry: float
    strike: int
    reason: str
    ready: bool

@dataclass
class OptionsData:
    ticker: str
    strike: int
    opt_type: str
    last: float
    bid: float
    ask: float
    volume: int
    open_interest: int

# ============================================================
# PERSISTENCE
# ============================================================

def load_inputs() -> ManualInputs:
    try:
        if os.path.exists(INPUTS_FILE):
            with open(INPUTS_FILE, 'r') as f:
                data = json.load(f)
                fields = {}
                for k in ManualInputs.__dataclass_fields__:
                    default = getattr(ManualInputs, k, None)
                    if hasattr(ManualInputs.__dataclass_fields__[k], 'default'):
                        default = ManualInputs.__dataclass_fields__[k].default
                    fields[k] = data.get(k, default)
                return ManualInputs(**fields)
    except Exception:
        pass
    return ManualInputs()

def save_inputs(inputs: ManualInputs) -> None:
    try:
        with open(INPUTS_FILE, 'w') as f:
            json.dump(inputs.__dict__, f, indent=2)
    except Exception:
        pass

# ============================================================
# DATA FETCHING
# ============================================================

def fetch_es_price() -> Optional[float]:
    """Fetch current ES futures price"""
    try:
        import yfinance as yf
        ticker = yf.Ticker("ES=F")
        data = ticker.history(period="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception:
        pass
    return None

def fetch_es_candles() -> Optional[List[Dict]]:
    """Fetch ES daily candles for MA calculation"""
    try:
        import yfinance as yf
        ticker = yf.Ticker("ES=F")
        data = ticker.history(period="250d", interval="1d")
        if not data.empty:
            candles = []
            for _, row in data.iterrows():
                candles.append({
                    "o": float(row["Open"]),
                    "h": float(row["High"]),
                    "l": float(row["Low"]),
                    "c": float(row["Close"])
                })
            return candles
    except Exception:
        pass
    return None

def fetch_options_data(strike: int, opt_type: str, exp_date: str) -> Optional[OptionsData]:
    """Fetch SPXW options data from Polygon"""
    try:
        exp_dt = datetime.strptime(exp_date, "%Y-%m-%d")
        exp_str = exp_dt.strftime("%y%m%d")
        ot = "C" if opt_type.lower() == "call" else "P"
        strike_padded = str(int(strike * 1000)).zfill(8)
        ticker = f"O:SPXW{exp_str}{ot}{strike_padded}"
        
        url = f"https://api.polygon.io/v3/snapshot/options/SPXW/{ticker}?apiKey={POLYGON_API_KEY}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "results" in data:
                res = data["results"]
                day = res.get("day", {})
                quote = res.get("last_quote", {})
                return OptionsData(
                    ticker=ticker,
                    strike=strike,
                    opt_type=opt_type,
                    last=float(day.get("close", day.get("last", 0)) or 0),
                    bid=float(quote.get("bid", 0) or 0),
                    ask=float(quote.get("ask", 0) or 0),
                    volume=int(day.get("volume", 0) or 0),
                    open_interest=int(res.get("open_interest", 0) or 0)
                )
    except Exception:
        pass
    return None

# ============================================================
# CALCULATIONS
# ============================================================

def calc_ema(prices: List[float], period: int) -> float:
    """Calculate Exponential Moving Average"""
    if not prices:
        return 0.0
    if len(prices) < period:
        return prices[-1]
    
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    
    return ema

def calc_sma(prices: List[float], period: int) -> float:
    """Calculate Simple Moving Average"""
    if not prices:
        return 0.0
    if len(prices) < period:
        return sum(prices) / len(prices)
    return sum(prices[-period:]) / period

def calculate_ma_bias(candles: List[Dict]) -> MABias:
    """
    Pillar 1: MA Bias - Determines trade direction
    50 EMA > 200 SMA = LONG (look for CALLS)
    50 EMA < 200 SMA = SHORT (look for PUTS)
    """
    if not candles or len(candles) < 50:
        return MABias(0, 0, "NEUTRAL")
    
    closes = [c["c"] for c in candles]
    ema_50 = calc_ema(closes, 50)
    sma_200 = calc_sma(closes, 200) if len(closes) >= 200 else calc_sma(closes, len(closes))
    
    if ema_50 > sma_200:
        bias = "LONG"
    elif ema_50 < sma_200:
        bias = "SHORT"
    else:
        bias = "NEUTRAL"
    
    return MABias(round(ema_50, 2), round(sma_200, 2), bias)

def calculate_vix_zone(high: float, low: float, current: float) -> VIXZone:
    """
    Pillar 3: VIX Zone - Timing signal
    If overnight range <= 7%:
        Current in lower half = CALLS
        Current in upper half = PUTS
    If range > 7% = WAIT
    """
    if high <= low or high == 0:
        return VIXZone(high, low, current, 0, "UNKNOWN", "WAIT")
    
    range_pct = ((high - low) / high) * 100
    midpoint = (high + low) / 2
    
    if range_pct <= 7:
        if current <= midpoint:
            return VIXZone(high, low, current, round(range_pct, 2), "LOWER HALF", "CALLS")
        else:
            return VIXZone(high, low, current, round(range_pct, 2), "UPPER HALF", "PUTS")
    
    return VIXZone(high, low, current, round(range_pct, 2), "OUTSIDE 7%", "WAIT")

def calculate_structure(candles: List[Dict], offset: float, 
                        man_ceiling: float, man_floor: float, 
                        use_manual: bool) -> DayStructure:
    """
    Pillar 2: Day Structure - Entry levels
    CEILING = resistance (entry for PUTS)
    FLOOR = support (entry for CALLS)
    """
    if use_manual and man_ceiling > 0 and man_floor > 0:
        return DayStructure(man_ceiling, man_floor, True)
    
    if not candles or len(candles) < 2:
        return DayStructure(0, 0, False)
    
    # Use recent candles for structure
    recent = candles[-10:] if len(candles) >= 10 else candles
    high_es = max(c.get("h", c.get("c", 0)) for c in recent)
    low_es = min(c.get("l", c.get("c", 0)) for c in recent)
    
    # Convert to SPX
    ceiling_spx = high_es - offset
    floor_spx = low_es - offset
    
    return DayStructure(round(ceiling_spx, 2), round(floor_spx, 2), False)

def calculate_cones(prior_high: float, prior_low: float, 
                    prior_close: float, offset: float) -> ConeRails:
    """
    Calculate cone rails from 3pm close to 9am entry
    3pm -> 9am = 18 hours = 36 half-hour blocks
    Expansion = blocks * 0.475 points per block
    """
    expansion = BLOCKS_3PM_TO_9AM * CONE_SLOPE
    
    return ConeRails(
        c1_asc=round(prior_high + expansion - offset, 0),
        c1_desc=round(prior_high - expansion - offset, 0),
        c2_asc=round(prior_low + expansion - offset, 0),
        c2_desc=round(prior_low - expansion - offset, 0),
        c3_asc=round(prior_close + expansion - offset, 0),
        c3_desc=round(prior_close - expansion - offset, 0),
        blocks=BLOCKS_3PM_TO_9AM,
        expansion=round(expansion, 1)
    )

def calculate_signal(ma: MABias, structure: DayStructure, 
                     vix: VIXZone, current_price: float) -> TradeSignal:
    """
    Combine all 3 pillars to generate trade signal
    All must align for a valid trade
    """
    if ma.bias == "NEUTRAL":
        return TradeSignal("NO TRADE", 0, 0, "MA Bias is NEUTRAL - no directional edge", False)
    
    if ma.bias == "LONG":
        entry = structure.floor
        strike = int(round((entry + 15) / 5) * 5)  # 15 points OTM, round to 5
        
        if vix.signal == "CALLS":
            return TradeSignal("CALLS", entry, strike, 
                             "✓ All 3 pillars aligned for CALLS", True)
        elif vix.signal == "PUTS":
            return TradeSignal("NO TRADE", entry, 0,
                             "MA says LONG but VIX says PUTS - conflicting signals", False)
        else:
            return TradeSignal("WAIT", entry, strike,
                             "MA LONG - waiting for VIX to enter CALLS zone", False)
    
    else:  # SHORT
        entry = structure.ceiling
        strike = int(round((entry - 15) / 5) * 5)  # 15 points OTM, round to 5
        
        if vix.signal == "PUTS":
            return TradeSignal("PUTS", entry, strike,
                             "✓ All 3 pillars aligned for PUTS", True)
        elif vix.signal == "CALLS":
            return TradeSignal("NO TRADE", entry, 0,
                             "MA says SHORT but VIX says CALLS - conflicting signals", False)
        else:
            return TradeSignal("WAIT", entry, strike,
                             "MA SHORT - waiting for VIX to enter PUTS zone", False)

# ============================================================
# STYLES
# ============================================================

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    :root {
        --bg-primary: #0a0a0f;
        --bg-secondary: #0f0f15;
        --bg-card: #151520;
        --bg-elevated: #1a1a28;
        --bg-hover: #202030;
        --border: #252535;
        --border-bright: #353545;
        --text-primary: #ffffff;
        --text-secondary: #9090a0;
        --text-muted: #505065;
        --accent-green: #00e5a0;
        --accent-green-dim: rgba(0, 229, 160, 0.12);
        --accent-red: #ff5068;
        --accent-red-dim: rgba(255, 80, 104, 0.12);
        --accent-gold: #ffb020;
        --accent-gold-dim: rgba(255, 176, 32, 0.12);
        --accent-blue: #4090ff;
        --accent-purple: #9060ff;
        --gradient-hero: linear-gradient(135deg, #101018 0%, #151525 50%, #0f1525 100%);
        --gradient-green: linear-gradient(135deg, #00e5a0 0%, #00c890 100%);
        --gradient-red: linear-gradient(135deg, #ff5068 0%, #ff7080 100%);
        --gradient-gold: linear-gradient(135deg, #ffb020 0%, #ffc040 100%);
    }
    
    /* Base App */
    .stApp {
        background: var(--bg-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hide Streamlit Elements */
    #MainMenu, footer, header, .stDeployButton, 
    [data-testid="stToolbar"], [data-testid="stDecoration"] {
        visibility: hidden !important;
        display: none !important;
    }
    
    /* Main Container */
    .main .block-container {
        padding: 1.5rem 2.5rem 3rem 2.5rem;
        max-width: 100%;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: var(--text-primary);
    }
    
    /* Input Fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 14px !important;
        padding: 10px 14px !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--accent-green) !important;
        box-shadow: 0 0 0 2px var(--accent-green-dim) !important;
    }
    
    /* Select Boxes */
    .stSelectbox > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }
    
    .stSelectbox > div > div > div {
        color: var(--text-primary) !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 10px 20px !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background: var(--bg-hover) !important;
        border-color: var(--border-bright) !important;
        transform: translateY(-1px);
    }
    
    .stButton > button[kind="primary"] {
        background: var(--gradient-green) !important;
        border: none !important;
        color: #000 !important;
        font-weight: 700 !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        opacity: 0.9;
        transform: translateY(-1px);
    }
    
    /* Checkbox */
    .stCheckbox label {
        color: var(--text-secondary) !important;
        font-size: 14px !important;
    }
    
    /* Dividers */
    hr {
        border-color: var(--border) !important;
        margin: 1.5rem 0 !important;
    }
    
    /* Captions */
    .stCaption {
        color: var(--text-muted) !important;
    }
    
    /* Alerts */
    .stAlert {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }
    
    /* Custom Components */
    .hero-banner {
        background: var(--gradient-hero);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 36px 44px;
        margin-bottom: 28px;
        position: relative;
        overflow: hidden;
    }
    
    .hero-banner::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--accent-green), var(--accent-blue), var(--accent-purple), var(--accent-red));
    }
    
    .logo-container {
        display: flex;
        align-items: center;
        gap: 20px;
    }
    
    .logo-icon {
        font-size: 56px;
        filter: drop-shadow(0 4px 12px rgba(0, 229, 160, 0.3));
    }
    
    .logo-text {
        font-family: 'Inter', sans-serif;
        font-size: 44px;
        font-weight: 900;
        background: linear-gradient(135deg, #ffffff 0%, #a0a0b0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -1.5px;
        line-height: 1.1;
    }
    
    .tagline {
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 700;
        color: var(--accent-green);
        letter-spacing: 4px;
        text-transform: uppercase;
        margin-top: 6px;
    }
    
    .price-display {
        text-align: right;
    }
    
    .price-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 42px;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -1px;
    }
    
    .price-meta {
        font-size: 13px;
        color: var(--text-secondary);
        margin-top: 4px;
    }
    
    .section-header {
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        font-weight: 800;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 3px;
        margin: 32px 0 20px 0;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border);
    }
    
    .pillar-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 24px;
        transition: all 0.25s ease;
    }
    
    .pillar-card.active {
        border-color: var(--accent-green);
        background: linear-gradient(135deg, var(--accent-green-dim), transparent);
    }
    
    .pillar-card.inactive {
        border-color: var(--accent-red);
        background: linear-gradient(135deg, var(--accent-red-dim), transparent);
    }
    
    .pillar-card.waiting {
        border-color: var(--accent-gold);
        background: linear-gradient(135deg, var(--accent-gold-dim), transparent);
    }
    
    .pillar-icon {
        width: 64px;
        height: 64px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        flex-shrink: 0;
    }
    
    .pillar-icon.green { background: var(--accent-green-dim); }
    .pillar-icon.red { background: var(--accent-red-dim); }
    .pillar-icon.gold { background: var(--accent-gold-dim); }
    
    .pillar-content {
        flex: 1;
    }
    
    .pillar-title {
        font-family: 'Inter', sans-serif;
        font-size: 18px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 4px;
    }
    
    .pillar-subtitle {
        font-size: 13px;
        color: var(--text-muted);
    }
    
    .pillar-value-container {
        text-align: right;
    }
    
    .pillar-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 24px;
        font-weight: 700;
    }
    
    .pillar-value.green { color: var(--accent-green); }
    .pillar-value.red { color: var(--accent-red); }
    .pillar-value.gold { color: var(--accent-gold); }
    .pillar-value.white { color: var(--text-primary); }
    
    .pillar-detail {
        font-size: 12px;
        color: var(--text-secondary);
        margin-top: 4px;
    }
    
    .signal-card {
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        margin: 28px 0;
        position: relative;
        overflow: hidden;
    }
    
    .signal-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }
    
    .signal-card.calls {
        background: linear-gradient(180deg, var(--accent-green-dim), var(--bg-card));
        border: 2px solid var(--accent-green);
    }
    .signal-card.calls::before { background: var(--gradient-green); }
    
    .signal-card.puts {
        background: linear-gradient(180deg, var(--accent-red-dim), var(--bg-card));
        border: 2px solid var(--accent-red);
    }
    .signal-card.puts::before { background: var(--gradient-red); }
    
    .signal-card.wait {
        background: linear-gradient(180deg, var(--accent-gold-dim), var(--bg-card));
        border: 2px solid var(--accent-gold);
    }
    .signal-card.wait::before { background: var(--gradient-gold); }
    
    .signal-card.notrade {
        background: var(--bg-card);
        border: 2px solid var(--border);
    }
    
    .signal-direction {
        font-family: 'JetBrains Mono', monospace;
        font-size: 56px;
        font-weight: 800;
        letter-spacing: -2px;
    }
    
    .signal-direction.green { color: var(--accent-green); }
    .signal-direction.red { color: var(--accent-red); }
    .signal-direction.gold { color: var(--accent-gold); }
    .signal-direction.muted { color: var(--text-muted); }
    
    .signal-reason {
        font-size: 15px;
        color: var(--text-secondary);
        margin-top: 8px;
    }
    
    .signal-metrics {
        display: flex;
        justify-content: center;
        gap: 60px;
        margin-top: 32px;
    }
    
    .signal-metric {
        text-align: center;
    }
    
    .signal-metric-label {
        font-size: 11px;
        font-weight: 700;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }
    
    .signal-metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .signal-metric-value.red {
        color: var(--accent-red);
    }
    
    .data-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 24px;
    }
    
    .data-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }
    
    .data-cell {
        background: var(--bg-elevated);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    
    .data-label {
        font-size: 10px;
        font-weight: 700;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    
    .data-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 20px;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    .data-value.green { color: var(--accent-green); }
    .data-value.red { color: var(--accent-red); }
    .data-value.muted { color: var(--text-muted); }
    
    .cone-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
    }
    
    .cone-table th {
        font-size: 10px;
        font-weight: 700;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 12px 16px;
        text-align: center;
        border-bottom: 1px solid var(--border);
    }
    
    .cone-table td {
        font-family: 'JetBrains Mono', monospace;
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
        padding: 14px 16px;
        text-align: center;
        border-bottom: 1px solid var(--border);
    }
    
    .cone-table tr:last-child td {
        border-bottom: none;
    }
    
    .cone-table .asc { color: var(--accent-green); }
    .cone-table .desc { color: var(--accent-red); }
    
    .data-footer {
        margin-top: 16px;
        font-size: 11px;
        color: var(--text-muted);
        text-align: center;
    }
    
    .sidebar-header {
        text-align: center;
        padding: 24px 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 24px;
    }
    
    .sidebar-icon {
        font-size: 48px;
        margin-bottom: 12px;
        filter: drop-shadow(0 2px 8px rgba(0, 229, 160, 0.3));
    }
    
    .sidebar-title {
        font-family: 'Inter', sans-serif;
        font-size: 24px;
        font-weight: 800;
        color: var(--text-primary);
        letter-spacing: -0.5px;
    }
    
    .sidebar-tagline {
        font-size: 9px;
        font-weight: 700;
        color: var(--accent-green);
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-top: 6px;
    }
    
    .date-badge {
        background: var(--bg-elevated);
        border: 1px solid var(--accent-green);
        border-radius: 12px;
        padding: 14px 18px;
        text-align: center;
        margin: 16px 0;
    }
    
    .date-badge-day {
        font-family: 'Inter', sans-serif;
        font-size: 16px;
        font-weight: 700;
        color: var(--accent-green);
    }
    
    .date-badge-full {
        font-size: 12px;
        color: var(--text-secondary);
        margin-top: 4px;
    }
    
    .sidebar-section {
        margin-bottom: 20px;
    }
    
    .sidebar-section-title {
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
</style>
"""

# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    st.set_page_config(
        page_title="SPX Prophet Pro",
        page_icon="🔮",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply custom styles
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    
    # Initialize session state
    if "inputs" not in st.session_state:
        st.session_state.inputs = load_inputs()
    if "es_price" not in st.session_state:
        st.session_state.es_price = None
    if "es_candles" not in st.session_state:
        st.session_state.es_candles = None
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = None
    if "options_data" not in st.session_state:
        st.session_state.options_data = None
    
    # ========================================
    # SIDEBAR
    # ========================================
    with st.sidebar:
        # Header
        st.markdown("""
        <div class="sidebar-header">
            <div class="sidebar-icon">🔮</div>
            <div class="sidebar-title">SPX Prophet</div>
            <div class="sidebar-tagline">Structure → Foresight</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Trading Date Section
        st.markdown('<div class="sidebar-section-title">📅 Trading Date</div>', unsafe_allow_html=True)
        
        today = datetime.now(CT).date()
        default_date = today
        if st.session_state.inputs.trading_date:
            try:
                default_date = datetime.strptime(st.session_state.inputs.trading_date, "%Y-%m-%d").date()
            except:
                pass
        
        # Quick date buttons
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            if st.button("Today", use_container_width=True, key="btn_today"):
                st.session_state.inputs.trading_date = today.strftime("%Y-%m-%d")
                st.session_state.options_data = None
                st.rerun()
        with btn_col2:
            yesterday = today - timedelta(days=1)
            if st.button("Yest", use_container_width=True, key="btn_yest"):
                st.session_state.inputs.trading_date = yesterday.strftime("%Y-%m-%d")
                st.session_state.options_data = None
                st.rerun()
        with btn_col3:
            # Find last Friday
            days_back = (today.weekday() - 4) % 7
            if days_back == 0:
                days_back = 7
            last_friday = today - timedelta(days=days_back)
            if st.button("Fri", use_container_width=True, key="btn_fri"):
                st.session_state.inputs.trading_date = last_friday.strftime("%Y-%m-%d")
                st.session_state.options_data = None
                st.rerun()
        
        # Date dropdowns
        date_col1, date_col2, date_col3 = st.columns(3)
        with date_col1:
            years = [2024, 2025, 2026, 2027]
            default_year_idx = years.index(default_date.year) if default_date.year in years else 2
            sel_year = st.selectbox("Year", years, index=default_year_idx, 
                                    key="sel_year", label_visibility="collapsed")
        with date_col2:
            months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            sel_month = st.selectbox("Month", range(1, 13), 
                                     format_func=lambda x: months[x-1],
                                     index=default_date.month - 1,
                                     key="sel_month", label_visibility="collapsed")
        with date_col3:
            max_days = calendar.monthrange(sel_year, sel_month)[1]
            default_day = min(default_date.day, max_days)
            sel_day = st.selectbox("Day", range(1, max_days + 1),
                                   index=default_day - 1,
                                   key="sel_day", label_visibility="collapsed")
        
        # Build trading date
        trading_date = date(sel_year, sel_month, sel_day)
        trading_date_str = trading_date.strftime("%Y-%m-%d")
        day_name = trading_date.strftime("%A")
        is_weekend = trading_date.weekday() >= 5
        
        # Display selected date
        if is_weekend:
            st.error(f"⚠️ {day_name} - Weekend (No Trading)")
        else:
            st.markdown(f"""
            <div class="date-badge">
                <div class="date-badge-day">{day_name}</div>
                <div class="date-badge-full">{trading_date.strftime('%B %d, %Y')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # VIX Zone Inputs
        st.markdown('<div class="sidebar-section-title">📊 VIX Zone</div>', unsafe_allow_html=True)
        st.caption("Enter from TradingView overnight session")
        
        vix_col1, vix_col2 = st.columns(2)
        vix_high = vix_col1.number_input("ON High", value=st.session_state.inputs.vix_overnight_high,
                                          format="%.2f", step=0.01, key="vix_high")
        vix_low = vix_col2.number_input("ON Low", value=st.session_state.inputs.vix_overnight_low,
                                         format="%.2f", step=0.01, key="vix_low")
        vix_current = st.number_input("VIX Current", value=st.session_state.inputs.vix_current,
                                       format="%.2f", step=0.01, key="vix_current")
        
        st.markdown("---")
        
        # Prior Day Inputs
        st.markdown('<div class="sidebar-section-title">📈 Prior Day (ES)</div>', unsafe_allow_html=True)
        st.caption("From 2:30pm candle close at 3pm CT")
        
        prior_col1, prior_col2, prior_col3 = st.columns(3)
        prior_high = prior_col1.number_input("High", value=st.session_state.inputs.prior_high,
                                              format="%.0f", step=1.0, key="prior_high")
        prior_low = prior_col2.number_input("Low", value=st.session_state.inputs.prior_low,
                                             format="%.0f", step=1.0, key="prior_low")
        prior_close = prior_col3.number_input("Close", value=st.session_state.inputs.prior_close,
                                               format="%.0f", step=1.0, key="prior_close")
        
        st.markdown("---")
        
        # ES/SPX Offset
        st.markdown('<div class="sidebar-section-title">⚖️ ES/SPX Offset</div>', unsafe_allow_html=True)
        offset = st.number_input("Offset (ES - SPX)", value=st.session_state.inputs.es_spx_offset,
                                  format="%.1f", step=0.5, key="offset", label_visibility="collapsed")
        
        st.markdown("---")
        
        # Manual Structure Override
        st.markdown('<div class="sidebar-section-title">🎯 Manual Structure</div>', unsafe_allow_html=True)
        use_manual = st.checkbox("Override auto CEILING/FLOOR", 
                                  value=st.session_state.inputs.use_manual_structure,
                                  key="use_manual")
        
        if use_manual:
            man_col1, man_col2 = st.columns(2)
            man_ceiling = man_col1.number_input("CEILING (SPX)", 
                                                 value=st.session_state.inputs.manual_ceiling,
                                                 format="%.0f", step=1.0, key="man_ceiling")
            man_floor = man_col2.number_input("FLOOR (SPX)",
                                               value=st.session_state.inputs.manual_floor,
                                               format="%.0f", step=1.0, key="man_floor")
        else:
            man_ceiling = 0.0
            man_floor = 0.0
        
        st.markdown("---")
        
        # Action Buttons
        if st.button("💾 SAVE ALL INPUTS", use_container_width=True, type="primary", key="btn_save"):
            st.session_state.inputs = ManualInputs(
                vix_overnight_high=vix_high,
                vix_overnight_low=vix_low,
                vix_current=vix_current,
                es_spx_offset=offset,
                prior_high=prior_high,
                prior_low=prior_low,
                prior_close=prior_close,
                manual_ceiling=man_ceiling,
                manual_floor=man_floor,
                use_manual_structure=use_manual,
                trading_date=trading_date_str
            )
            save_inputs(st.session_state.inputs)
            st.session_state.options_data = None
            st.success("✓ All inputs saved!")
        
        if st.button("🔄 Refresh Market Data", use_container_width=True, key="btn_refresh"):
            st.session_state.last_refresh = None
            st.session_state.es_price = None
            st.session_state.es_candles = None
            st.session_state.options_data = None
            st.rerun()

    # ========================================
    # MAIN CONTENT AREA
    # ========================================
    
    # Build current inputs object
    inputs = ManualInputs(
        vix_overnight_high=vix_high,
        vix_overnight_low=vix_low,
        vix_current=vix_current,
        es_spx_offset=offset,
        prior_high=prior_high,
        prior_low=prior_low,
        prior_close=prior_close,
        manual_ceiling=man_ceiling if use_manual else 0,
        manual_floor=man_floor if use_manual else 0,
        use_manual_structure=use_manual,
        trading_date=trading_date_str
    )
    
    # Fetch market data if needed
    should_refresh = (
        st.session_state.last_refresh is None or 
        (datetime.now() - st.session_state.last_refresh).seconds > 900
    )
    
    if should_refresh:
        with st.spinner("Loading market data..."):
            st.session_state.es_price = fetch_es_price()
            st.session_state.es_candles = fetch_es_candles()
            st.session_state.last_refresh = datetime.now()
    
    # Get data from session state
    es_price = st.session_state.es_price or 0
    es_candles = st.session_state.es_candles or []
    spx_price = (es_price - inputs.es_spx_offset) if es_price else 0
    
    # Perform calculations
    ma_bias = calculate_ma_bias(es_candles) if es_candles else MABias(0, 0, "NEUTRAL")
    vix_zone = calculate_vix_zone(inputs.vix_overnight_high, inputs.vix_overnight_low, inputs.vix_current)
    structure = calculate_structure(es_candles, inputs.es_spx_offset, 
                                    inputs.manual_ceiling, inputs.manual_floor, 
                                    inputs.use_manual_structure)
    cones = calculate_cones(inputs.prior_high, inputs.prior_low, inputs.prior_close, inputs.es_spx_offset)
    signal = calculate_signal(ma_bias, structure, vix_zone, spx_price)
    
    # Fetch options data if we have a strike
    if signal.strike > 0 and st.session_state.options_data is None:
        opt_type = "call" if ma_bias.bias == "LONG" else "put"
        st.session_state.options_data = fetch_options_data(signal.strike, opt_type, trading_date_str)
    
    options = st.session_state.options_data
    
    # Current time
    now = datetime.now(CT)
    
    # ========================================
    # HERO BANNER
    # ========================================
    st.markdown(f"""
    <div class="hero-banner">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div class="logo-container">
                <span class="logo-icon">🔮</span>
                <div>
                    <div class="logo-text">SPX Prophet</div>
                    <div class="tagline">Where Structure Becomes Foresight</div>
                </div>
            </div>
            <div class="price-display">
                <div class="price-value">{spx_price:,.2f}</div>
                <div class="price-meta">SPX • {now.strftime('%I:%M %p CT')} • {trading_date.strftime('%b %d, %Y')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================
    # THREE PILLARS
    # ========================================
    st.markdown('<div class="section-header">The Three Pillars</div>', unsafe_allow_html=True)
    
    # Pillar 1: MA Bias
    p1_status = "active" if ma_bias.bias in ["LONG", "SHORT"] else "waiting"
    p1_icon_color = "green" if ma_bias.bias == "LONG" else ("red" if ma_bias.bias == "SHORT" else "gold")
    p1_value_color = "green" if ma_bias.bias == "LONG" else ("red" if ma_bias.bias == "SHORT" else "gold")
    p1_compare = ">" if ma_bias.ema_50 > ma_bias.sma_200 else "<"
    
    st.markdown(f"""
    <div class="pillar-card {p1_status}">
        <div class="pillar-icon {p1_icon_color}">📊</div>
        <div class="pillar-content">
            <div class="pillar-title">Pillar 1: MA Bias</div>
            <div class="pillar-subtitle">Can I trade CALLS or PUTS today?</div>
        </div>
        <div class="pillar-value-container">
            <div class="pillar-value {p1_value_color}">{ma_bias.bias}</div>
            <div class="pillar-detail">50 EMA {p1_compare} 200 SMA</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Pillar 2: Day Structure
    entry_type = "FLOOR" if ma_bias.bias == "LONG" else ("CEILING" if ma_bias.bias == "SHORT" else "—")
    entry_level = structure.floor if ma_bias.bias == "LONG" else (structure.ceiling if ma_bias.bias == "SHORT" else 0)
    p2_status = "active" if entry_level > 0 else "waiting"
    p2_icon_color = "green" if ma_bias.bias == "LONG" else ("red" if ma_bias.bias == "SHORT" else "gold")
    manual_tag = " [Manual]" if structure.is_manual else ""
    
    st.markdown(f"""
    <div class="pillar-card {p2_status}">
        <div class="pillar-icon {p2_icon_color}">🎯</div>
        <div class="pillar-content">
            <div class="pillar-title">Pillar 2: Day Structure</div>
            <div class="pillar-subtitle">Where is my entry level @ 9:00 AM CT?</div>
        </div>
        <div class="pillar-value-container">
            <div class="pillar-value white">{entry_type}</div>
            <div class="pillar-detail">{entry_level:,.0f} SPX{manual_tag}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Pillar 3: VIX Zone
    p3_status = "active" if vix_zone.signal in ["CALLS", "PUTS"] else "waiting"
    p3_icon_color = "green" if vix_zone.signal == "CALLS" else ("red" if vix_zone.signal == "PUTS" else "gold")
    p3_value_color = "green" if vix_zone.signal == "CALLS" else ("red" if vix_zone.signal == "PUTS" else "gold")
    
    st.markdown(f"""
    <div class="pillar-card {p3_status}">
        <div class="pillar-icon {p3_icon_color}">⚡</div>
        <div class="pillar-content">
            <div class="pillar-title">Pillar 3: VIX Zone</div>
            <div class="pillar-subtitle">When do I pull the trigger?</div>
        </div>
        <div class="pillar-value-container">
            <div class="pillar-value {p3_value_color}">{vix_zone.signal}</div>
            <div class="pillar-detail">{vix_zone.position} • Range: {vix_zone.range_pct:.1f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========================================
    # TRADE SIGNAL CARD
    # ========================================
    st.markdown('<div class="section-header">Trade Decision</div>', unsafe_allow_html=True)
    
    # Determine signal styling
    if signal.direction == "CALLS":
        sig_card_class = "calls"
        sig_text_class = "green"
    elif signal.direction == "PUTS":
        sig_card_class = "puts"
        sig_text_class = "red"
    elif signal.direction == "WAIT":
        sig_card_class = "wait"
        sig_text_class = "gold"
    else:
        sig_card_class = "notrade"
        sig_text_class = "muted"
    
    # Calculate 50% stop
    stop_price = "—"
    if options and options.last > 0:
        stop_price = f"${options.last * 0.5:.2f}"
    
    st.markdown(f"""
    <div class="signal-card {sig_card_class}">
        <div class="signal-direction {sig_text_class}">{signal.direction}</div>
        <div class="signal-reason">{signal.reason}</div>
        <div class="signal-metrics">
            <div class="signal-metric">
                <div class="signal-metric-label">Entry Level</div>
                <div class="signal-metric-value">{signal.entry:,.0f}</div>
            </div>
            <div class="signal-metric">
                <div class="signal-metric-label">Strike</div>
                <div class="signal-metric-value">{signal.strike if signal.strike > 0 else '—'}</div>
            </div>
            <div class="signal-metric">
                <div class="signal-metric-label">50% Stop</div>
                <div class="signal-metric-value red">{stop_price}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================
    # BOTTOM PANELS: CONES & OPTIONS
    # ========================================
    col_left, col_right = st.columns(2)
    
    # Left Column: Cone Rails
    with col_left:
        st.markdown('<div class="section-header">Cone Rails @ 9:00 AM CT</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="data-card">
            <table class="cone-table">
                <thead>
                    <tr>
                        <th>Anchor Point</th>
                        <th>↗ Ascending</th>
                        <th>↘ Descending</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>C1 (High {inputs.prior_high:,.0f})</td>
                        <td class="asc">{cones.c1_asc:,.0f}</td>
                        <td class="desc">{cones.c1_desc:,.0f}</td>
                    </tr>
                    <tr>
                        <td>C2 (Low {inputs.prior_low:,.0f})</td>
                        <td class="asc">{cones.c2_asc:,.0f}</td>
                        <td class="desc">{cones.c2_desc:,.0f}</td>
                    </tr>
                    <tr>
                        <td>C3 (Close {inputs.prior_close:,.0f})</td>
                        <td class="asc">{cones.c3_asc:,.0f}</td>
                        <td class="desc">{cones.c3_desc:,.0f}</td>
                    </tr>
                </tbody>
            </table>
            <div class="data-footer">
                3pm → 9am: {cones.blocks} blocks • ±{cones.expansion} pts expansion
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Right Column: Options Data
    with col_right:
        st.markdown('<div class="section-header">0DTE Options</div>', unsafe_allow_html=True)
        
        if options:
            opt_type_display = "C" if options.opt_type == "call" else "P"
            st.markdown(f"""
            <div class="data-card">
                <div class="data-footer" style="margin-top: 0; margin-bottom: 16px;">{options.ticker}</div>
                <div class="data-grid">
                    <div class="data-cell">
                        <div class="data-label">Strike</div>
                        <div class="data-value green">{options.strike} {opt_type_display}</div>
                    </div>
                    <div class="data-cell">
                        <div class="data-label">Last</div>
                        <div class="data-value">${options.last:.2f}</div>
                    </div>
                    <div class="data-cell">
                        <div class="data-label">Bid</div>
                        <div class="data-value">${options.bid:.2f}</div>
                    </div>
                    <div class="data-cell">
                        <div class="data-label">Ask</div>
                        <div class="data-value">${options.ask:.2f}</div>
                    </div>
                </div>
                <div class="data-footer">
                    Vol: {options.volume:,} • OI: {options.open_interest:,}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # No options data
            strike_display = f"{signal.strike} {'C' if ma_bias.bias == 'LONG' else 'P'}" if signal.strike > 0 else "—"
            st.markdown(f"""
            <div class="data-card">
                <div class="data-grid">
                    <div class="data-cell">
                        <div class="data-label">Strike</div>
                        <div class="data-value green">{strike_display}</div>
                    </div>
                    <div class="data-cell">
                        <div class="data-label">Last</div>
                        <div class="data-value muted">—</div>
                    </div>
                    <div class="data-cell">
                        <div class="data-label">Bid</div>
                        <div class="data-value muted">—</div>
                    </div>
                    <div class="data-cell">
                        <div class="data-label">Ask</div>
                        <div class="data-value muted">—</div>
                    </div>
                </div>
                <div class="data-footer">
                    {'Waiting for market data...' if signal.strike > 0 else 'Enter inputs to calculate strike'}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # ========================================
    # FOOTER
    # ========================================
    st.markdown("---")
    footer_col1, footer_col2 = st.columns(2)
    
    with footer_col1:
        last_refresh_str = st.session_state.last_refresh.strftime("%I:%M %p") if st.session_state.last_refresh else "Never"
        st.caption(f"🔄 Last refresh: {last_refresh_str} • Auto-refresh: 15 min")
    
    with footer_col2:
        st.caption(f"📊 ES: {es_price:,.2f} • Offset: {offset:.1f} • Entry Window: 9:00 AM CT")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()

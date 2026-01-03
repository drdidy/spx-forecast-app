"""
Stock Prophet Elite - Premium Trading Dashboard
Stunning glassmorphism design with animations and visual effects
"""

import streamlit as st
import requests
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum

# ============================================================================
# CONFIGURATION
# ============================================================================

POLYGON_API_KEY = "DCWuTS1R_fukpfjgf7QnXrLTEOS_giq6"
POLYGON_BASE_URL = "https://api.polygon.io"

STOCK_UNIVERSE = ["AAPL", "NVDA", "MSFT"]

STOCK_INFO = {
    "AAPL": {"name": "Apple Inc.", "icon": "🍎", "color": "#00d4aa"},
    "NVDA": {"name": "NVIDIA Corp.", "icon": "💚", "color": "#76b900"},
    "MSFT": {"name": "Microsoft", "icon": "🪟", "color": "#00a4ef"},
}

STOP_BUFFER_PERCENT = 0.002

# ============================================================================
# DATA MODELS
# ============================================================================

class MABias(Enum):
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"

class TradeDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO TRADE"

@dataclass
class StockData:
    symbol: str
    current_price: Optional[float] = None
    ema_50: Optional[float] = None
    sma_200: Optional[float] = None
    ma_bias: MABias = MABias.NEUTRAL
    high_point_1: Optional[float] = None
    high_time_1: str = ""
    high_point_2: Optional[float] = None
    high_time_2: str = ""
    low_point_1: Optional[float] = None
    low_time_1: str = ""
    low_point_2: Optional[float] = None
    low_time_2: str = ""
    ceiling: Optional[float] = None
    floor: Optional[float] = None
    polygon_connected: bool = False

@dataclass
class TradeSetup:
    direction: TradeDirection
    entry: Optional[float] = None
    exit_target: Optional[float] = None
    stop_loss: Optional[float] = None
    reward: Optional[float] = None
    risk: Optional[float] = None
    rr_ratio: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    is_valid: bool = False

# ============================================================================
# POLYGON API
# ============================================================================

@st.cache_data(ttl=60)
def fetch_current_price(symbol: str) -> Tuple[Optional[float], bool]:
    try:
        url = f"{POLYGON_BASE_URL}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
        params = {"apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK" and "ticker" in data:
                ticker_data = data["ticker"]
                if "lastTrade" in ticker_data:
                    return ticker_data["lastTrade"].get("p"), True
                elif "day" in ticker_data:
                    return ticker_data["day"].get("c"), True
                elif "prevDay" in ticker_data:
                    return ticker_data["prevDay"].get("c"), True
        return None, False
    except Exception:
        return None, False

# ============================================================================
# TRADE LOGIC
# ============================================================================

def determine_ma_bias(current_price: Optional[float], ema_50: Optional[float], sma_200: Optional[float]) -> MABias:
    if None in (current_price, ema_50, sma_200):
        return MABias.NEUTRAL
    if ema_50 > sma_200 and current_price > ema_50:
        return MABias.BULLISH
    elif ema_50 < sma_200 and current_price < ema_50:
        return MABias.BEARISH
    return MABias.NEUTRAL

def calculate_trade_setup(stock: StockData) -> TradeSetup:
    setup = TradeSetup(direction=TradeDirection.NO_TRADE)
    
    if stock.ceiling is None or stock.floor is None:
        setup.warnings.append("Set overnight high/low points to calculate levels")
        return setup
    
    if stock.current_price is None:
        setup.warnings.append("No current price available")
        return setup
    
    if stock.ceiling <= stock.floor:
        setup.warnings.append("Ceiling must be greater than Floor")
        return setup
    
    current_hour = datetime.now().hour
    if 9 <= current_hour <= 10:
        pass  # Optimal time
    else:
        setup.warnings.append(f"Current: {datetime.now().strftime('%I:%M %p')} • Optimal: 9-10am ET")
    
    if stock.ma_bias == MABias.BULLISH:
        setup.direction = TradeDirection.LONG
        setup.entry = stock.floor
        setup.exit_target = stock.ceiling
        setup.stop_loss = round(stock.floor * (1 - STOP_BUFFER_PERCENT), 2)
        setup.is_valid = True
        if stock.current_price > stock.floor * 1.02:
            setup.warnings.append("Price above Floor - entry may have passed")
        
    elif stock.ma_bias == MABias.BEARISH:
        setup.direction = TradeDirection.SHORT
        setup.entry = stock.ceiling
        setup.exit_target = stock.floor
        setup.stop_loss = round(stock.ceiling * (1 + STOP_BUFFER_PERCENT), 2)
        setup.is_valid = True
        if stock.current_price < stock.ceiling * 0.98:
            setup.warnings.append("Price below Ceiling - entry may have passed")
    else:
        setup.warnings.append("Neutral bias - no clear trade direction")
        return setup
    
    if setup.entry and setup.exit_target and setup.stop_loss:
        if setup.direction == TradeDirection.LONG:
            setup.reward = round(setup.exit_target - setup.entry, 2)
            setup.risk = round(setup.entry - setup.stop_loss, 2)
        else:
            setup.reward = round(setup.entry - setup.exit_target, 2)
            setup.risk = round(setup.stop_loss - setup.entry, 2)
        
        if setup.risk > 0:
            setup.rr_ratio = round(setup.reward / setup.risk, 2)
            if setup.rr_ratio < 1.5:
                setup.warnings.append(f"R:R {setup.rr_ratio}:1 below 1.5 minimum")
    
    return setup

# ============================================================================
# PREMIUM CSS STYLES
# ============================================================================

def inject_premium_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    /* ===== ROOT VARIABLES ===== */
    :root {
        --bg-primary: #0a0a0f;
        --bg-secondary: #12121a;
        --glass-bg: rgba(255, 255, 255, 0.03);
        --glass-border: rgba(255, 255, 255, 0.08);
        --glass-highlight: rgba(255, 255, 255, 0.1);
        --text-primary: #ffffff;
        --text-secondary: #8b8b9e;
        --text-muted: #5a5a6e;
        --accent-green: #00d4aa;
        --accent-green-glow: rgba(0, 212, 170, 0.4);
        --accent-red: #ff4757;
        --accent-red-glow: rgba(255, 71, 87, 0.4);
        --accent-blue: #667eea;
        --accent-purple: #a855f7;
        --accent-gold: #f59e0b;
    }
    
    /* ===== GLOBAL STYLES ===== */
    .stApp {
        background: var(--bg-primary);
        background-image: 
            radial-gradient(ellipse 80% 50% at 50% -20%, rgba(102, 126, 234, 0.15), transparent),
            radial-gradient(ellipse 60% 40% at 80% 100%, rgba(168, 85, 247, 0.1), transparent),
            radial-gradient(ellipse 40% 30% at 10% 60%, rgba(0, 212, 170, 0.08), transparent);
        font-family: 'Outfit', sans-serif;
    }
    
    /* Hide Streamlit defaults */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* ===== ANIMATED HEADER ===== */
    .prophet-header {
        text-align: center;
        padding: 40px 20px;
        position: relative;
        overflow: hidden;
    }
    
    .prophet-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 600px;
        height: 300px;
        background: radial-gradient(ellipse, rgba(102, 126, 234, 0.2) 0%, transparent 70%);
        pointer-events: none;
        animation: headerPulse 4s ease-in-out infinite;
    }
    
    @keyframes headerPulse {
        0%, 100% { opacity: 0.5; transform: translateX(-50%) scale(1); }
        50% { opacity: 0.8; transform: translateX(-50%) scale(1.1); }
    }
    
    .prophet-title {
        font-family: 'Outfit', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #a855f7 50%, #00d4aa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -2px;
        margin: 0;
        position: relative;
        animation: titleShimmer 3s ease-in-out infinite;
    }
    
    @keyframes titleShimmer {
        0%, 100% { filter: brightness(1); }
        50% { filter: brightness(1.2); }
    }
    
    .prophet-subtitle {
        font-size: 1.1rem;
        color: var(--text-secondary);
        margin-top: 10px;
        font-weight: 400;
        letter-spacing: 3px;
        text-transform: uppercase;
    }
    
    /* ===== STATUS BAR ===== */
    .status-bar {
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 20px;
        padding: 20px 30px;
        margin: 0 auto 40px;
        max-width: 900px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 20px;
        box-shadow: 
            0 4px 30px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 var(--glass-highlight);
    }
    
    .status-item {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .status-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        animation: pulse 2s ease-in-out infinite;
    }
    
    .status-dot.connected {
        background: var(--accent-green);
        box-shadow: 0 0 15px var(--accent-green-glow);
    }
    
    .status-dot.disconnected {
        background: var(--accent-red);
        box-shadow: 0 0 15px var(--accent-red-glow);
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.2); opacity: 0.7; }
    }
    
    .status-label {
        color: var(--text-secondary);
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    .trade-badge {
        padding: 8px 16px;
        border-radius: 30px;
        font-weight: 600;
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: all 0.3s ease;
    }
    
    .trade-badge:hover {
        transform: translateY(-2px);
    }
    
    .trade-badge.long {
        background: rgba(0, 212, 170, 0.15);
        color: var(--accent-green);
        border: 1px solid rgba(0, 212, 170, 0.3);
        box-shadow: 0 0 20px rgba(0, 212, 170, 0.1);
    }
    
    .trade-badge.short {
        background: rgba(255, 71, 87, 0.15);
        color: var(--accent-red);
        border: 1px solid rgba(255, 71, 87, 0.3);
        box-shadow: 0 0 20px rgba(255, 71, 87, 0.1);
    }
    
    .trade-badge.none {
        background: rgba(139, 139, 158, 0.15);
        color: var(--text-secondary);
        border: 1px solid rgba(139, 139, 158, 0.3);
    }
    
    /* ===== GLASS CARD ===== */
    .glass-card {
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        padding: 30px;
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.4),
            inset 0 1px 0 var(--glass-highlight);
    }
    
    .glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--glass-highlight), transparent);
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 
            0 20px 60px rgba(0, 0, 0, 0.5),
            inset 0 1px 0 var(--glass-highlight);
    }
    
    .glass-card.long-glow {
        border-color: rgba(0, 212, 170, 0.3);
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.4),
            0 0 60px rgba(0, 212, 170, 0.15),
            inset 0 1px 0 rgba(0, 212, 170, 0.2);
    }
    
    .glass-card.long-glow::after {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(ellipse at center, rgba(0, 212, 170, 0.05) 0%, transparent 70%);
        pointer-events: none;
    }
    
    .glass-card.short-glow {
        border-color: rgba(255, 71, 87, 0.3);
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.4),
            0 0 60px rgba(255, 71, 87, 0.15),
            inset 0 1px 0 rgba(255, 71, 87, 0.2);
    }
    
    .glass-card.short-glow::after {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(ellipse at center, rgba(255, 71, 87, 0.05) 0%, transparent 70%);
        pointer-events: none;
    }
    
    /* ===== CARD HEADER ===== */
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 25px;
        position: relative;
        z-index: 1;
    }
    
    .stock-identity {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    
    .stock-icon {
        width: 60px;
        height: 60px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.8rem;
        background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
        border: 1px solid var(--glass-border);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .stock-name-group h2 {
        font-family: 'Outfit', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .stock-name-group .company-name {
        font-size: 0.9rem;
        color: var(--text-muted);
        margin-top: 2px;
    }
    
    .price-display {
        text-align: right;
    }
    
    .current-price {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2rem;
        font-weight: 600;
        color: var(--text-primary);
        letter-spacing: -1px;
    }
    
    .price-status {
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-top: 4px;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 6px;
    }
    
    .price-status .dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--accent-green);
        animation: pulse 2s infinite;
    }
    
    /* ===== BIAS INDICATOR ===== */
    .bias-section {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        position: relative;
        z-index: 1;
    }
    
    .bias-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    
    .bias-label {
        font-size: 0.85rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 500;
    }
    
    .bias-badge {
        padding: 8px 20px;
        border-radius: 30px;
        font-weight: 700;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .bias-badge.bullish {
        background: linear-gradient(135deg, rgba(0, 212, 170, 0.2) 0%, rgba(0, 212, 170, 0.1) 100%);
        color: var(--accent-green);
        border: 1px solid rgba(0, 212, 170, 0.4);
        box-shadow: 0 0 20px rgba(0, 212, 170, 0.2);
    }
    
    .bias-badge.bearish {
        background: linear-gradient(135deg, rgba(255, 71, 87, 0.2) 0%, rgba(255, 71, 87, 0.1) 100%);
        color: var(--accent-red);
        border: 1px solid rgba(255, 71, 87, 0.4);
        box-shadow: 0 0 20px rgba(255, 71, 87, 0.2);
    }
    
    .bias-badge.neutral {
        background: linear-gradient(135deg, rgba(139, 139, 158, 0.2) 0%, rgba(139, 139, 158, 0.1) 100%);
        color: var(--text-secondary);
        border: 1px solid rgba(139, 139, 158, 0.4);
    }
    
    .ma-values {
        display: flex;
        gap: 30px;
    }
    
    .ma-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    
    .ma-item .label {
        font-size: 0.75rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .ma-item .value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1rem;
        color: var(--text-primary);
        font-weight: 500;
    }
    
    /* ===== DAY STRUCTURE ===== */
    .structure-section {
        margin-bottom: 20px;
        position: relative;
        z-index: 1;
    }
    
    .structure-title {
        font-size: 0.85rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .structure-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
    }
    
    .structure-box {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        border: 1px solid transparent;
        transition: all 0.3s ease;
    }
    
    .structure-box.ceiling {
        border-color: rgba(255, 71, 87, 0.2);
    }
    
    .structure-box.ceiling:hover {
        border-color: rgba(255, 71, 87, 0.4);
        box-shadow: 0 0 30px rgba(255, 71, 87, 0.1);
    }
    
    .structure-box.floor {
        border-color: rgba(0, 212, 170, 0.2);
    }
    
    .structure-box.floor:hover {
        border-color: rgba(0, 212, 170, 0.4);
        box-shadow: 0 0 30px rgba(0, 212, 170, 0.1);
    }
    
    .structure-box .box-label {
        font-size: 0.75rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    
    .structure-box .box-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    .structure-box.ceiling .box-value {
        color: var(--accent-red);
    }
    
    .structure-box.floor .box-value {
        color: var(--accent-green);
    }
    
    .structure-box .box-detail {
        font-size: 0.75rem;
        color: var(--text-muted);
    }
    
    /* ===== TRADE SIGNAL ===== */
    .trade-signal {
        background: rgba(0, 0, 0, 0.3);
        border-radius: 20px;
        padding: 25px;
        position: relative;
        z-index: 1;
        overflow: hidden;
    }
    
    .trade-signal::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        border-radius: 20px 20px 0 0;
    }
    
    .trade-signal.long::before {
        background: linear-gradient(90deg, var(--accent-green), rgba(0, 212, 170, 0.3));
    }
    
    .trade-signal.short::before {
        background: linear-gradient(90deg, var(--accent-red), rgba(255, 71, 87, 0.3));
    }
    
    .trade-signal.none::before {
        background: linear-gradient(90deg, var(--text-muted), rgba(139, 139, 158, 0.3));
    }
    
    .signal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }
    
    .signal-direction {
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    
    .signal-direction.long {
        color: var(--accent-green);
        text-shadow: 0 0 30px var(--accent-green-glow);
    }
    
    .signal-direction.short {
        color: var(--accent-red);
        text-shadow: 0 0 30px var(--accent-red-glow);
    }
    
    .signal-direction.none {
        color: var(--text-muted);
    }
    
    .signal-icon {
        font-size: 2rem;
    }
    
    .trade-levels {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
        margin-bottom: 20px;
    }
    
    .level-box {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        border: 1px solid var(--glass-border);
    }
    
    .level-box .level-label {
        font-size: 0.7rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    
    .level-box .level-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    .level-box.entry .level-value {
        color: var(--accent-blue);
    }
    
    .level-box.target .level-value {
        color: var(--accent-green);
    }
    
    .level-box.stop .level-value {
        color: var(--accent-red);
    }
    
    .rr-display {
        display: flex;
        justify-content: center;
        gap: 30px;
        padding: 15px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        border: 1px solid var(--glass-border);
    }
    
    .rr-item {
        text-align: center;
    }
    
    .rr-item .rr-label {
        font-size: 0.7rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 5px;
    }
    
    .rr-item .rr-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1rem;
        font-weight: 600;
        color: var(--accent-gold);
    }
    
    /* ===== WARNINGS ===== */
    .warning-box {
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 12px;
        padding: 12px 16px;
        margin-top: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 0.85rem;
        color: var(--accent-gold);
    }
    
    .warning-box .warning-icon {
        font-size: 1rem;
    }
    
    /* ===== SIDEBAR STYLES ===== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0d14 0%, #12121a 100%);
        border-right: 1px solid var(--glass-border);
    }
    
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: var(--text-primary);
        font-family: 'Outfit', sans-serif;
    }
    
    /* ===== EXPANDER OVERRIDE ===== */
    .streamlit-expanderHeader {
        background: var(--glass-bg) !important;
        border-radius: 16px !important;
        border: 1px solid var(--glass-border) !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
    }
    
    /* ===== RULES SECTION ===== */
    .rules-section {
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        border: 1px solid var(--glass-border);
        padding: 30px;
        margin-top: 40px;
    }
    
    .rules-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--accent-purple);
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .rule-item {
        padding: 15px 0;
        border-bottom: 1px solid var(--glass-border);
        color: var(--text-secondary);
        line-height: 1.6;
    }
    
    .rule-item:last-child {
        border-bottom: none;
    }
    
    .rule-item strong {
        color: var(--text-primary);
    }
    
    /* ===== FOOTER ===== */
    .footer {
        text-align: center;
        padding: 40px 20px;
        color: var(--text-muted);
        font-size: 0.85rem;
    }
    
    .footer-brand {
        font-weight: 600;
        background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* ===== ANIMATIONS ===== */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .glass-card {
        animation: fadeInUp 0.6s ease-out forwards;
    }
    
    .glass-card:nth-child(1) { animation-delay: 0.1s; }
    .glass-card:nth-child(2) { animation-delay: 0.2s; }
    .glass-card:nth-child(3) { animation-delay: 0.3s; }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# UI COMPONENTS
# ============================================================================

def format_price(price: Optional[float]) -> str:
    if price is None:
        return "—"
    return f"${price:,.2f}"

def render_header():
    st.markdown("""
    <div class="prophet-header">
        <h1 class="prophet-title">STOCK PROPHET</h1>
        <p class="prophet-subtitle">Elite Trading Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

def render_status_bar(setups: List[TradeSetup], polygon_connected: bool):
    long_count = sum(1 for s in setups if s.direction == TradeDirection.LONG)
    short_count = sum(1 for s in setups if s.direction == TradeDirection.SHORT)
    no_trade = sum(1 for s in setups if s.direction == TradeDirection.NO_TRADE)
    
    status_class = "connected" if polygon_connected else "disconnected"
    status_text = "Live Data" if polygon_connected else "Offline"
    
    st.markdown(f"""
    <div class="status-bar">
        <div class="status-item">
            <div class="status-dot {status_class}"></div>
            <span class="status-label">{status_text}</span>
        </div>
        <div style="display: flex; gap: 15px;">
            <div class="trade-badge long">
                <span>📈</span>
                <span>{long_count} LONG</span>
            </div>
            <div class="trade-badge short">
                <span>📉</span>
                <span>{short_count} SHORT</span>
            </div>
            <div class="trade-badge none">
                <span>⏸️</span>
                <span>{no_trade} WAIT</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_stock_card(stock: StockData, setup: TradeSetup):
    info = STOCK_INFO.get(stock.symbol, {"name": stock.symbol, "icon": "📊", "color": "#667eea"})
    
    # Determine glow class
    if setup.direction == TradeDirection.LONG:
        glow_class = "long-glow"
        signal_class = "long"
        signal_icon = "🚀"
    elif setup.direction == TradeDirection.SHORT:
        glow_class = "short-glow"
        signal_class = "short"
        signal_icon = "🔻"
    else:
        glow_class = ""
        signal_class = "none"
        signal_icon = "⏸️"
    
    # Bias class
    if stock.ma_bias == MABias.BULLISH:
        bias_class = "bullish"
        bias_text = "BULLISH"
    elif stock.ma_bias == MABias.BEARISH:
        bias_class = "bearish"
        bias_text = "BEARISH"
    else:
        bias_class = "neutral"
        bias_text = "NEUTRAL"
    
    # Format values
    price_str = format_price(stock.current_price)
    ema_str = f"${stock.ema_50:.2f}" if stock.ema_50 else "—"
    sma_str = f"${stock.sma_200:.2f}" if stock.sma_200 else "—"
    ceiling_str = format_price(stock.ceiling)
    floor_str = format_price(stock.floor)
    
    # Ceiling/Floor details
    ceiling_detail = ""
    if stock.high_point_1 and stock.high_point_2:
        ceiling_detail = f"H1: ${stock.high_point_1:.2f} @ {stock.high_time_1} • H2: ${stock.high_point_2:.2f} @ {stock.high_time_2}"
    
    floor_detail = ""
    if stock.low_point_1 and stock.low_point_2:
        floor_detail = f"L1: ${stock.low_point_1:.2f} @ {stock.low_time_1} • L2: ${stock.low_point_2:.2f} @ {stock.low_time_2}"
    
    # Trade levels
    entry_str = format_price(setup.entry)
    target_str = format_price(setup.exit_target)
    stop_str = format_price(setup.stop_loss)
    reward_str = f"{setup.reward} pts" if setup.reward else "—"
    risk_str = f"{setup.risk} pts" if setup.risk else "—"
    rr_str = f"{setup.rr_ratio}:1" if setup.rr_ratio else "—"
    
    # Warnings HTML
    warnings_html = ""
    for warning in setup.warnings:
        warnings_html += f'<div class="warning-box"><span class="warning-icon">⚠️</span>{warning}</div>'
    
    card_html = f"""
    <div class="glass-card {glow_class}">
        <div class="card-header">
            <div class="stock-identity">
                <div class="stock-icon">{info['icon']}</div>
                <div class="stock-name-group">
                    <h2>{stock.symbol}</h2>
                    <div class="company-name">{info['name']}</div>
                </div>
            </div>
            <div class="price-display">
                <div class="current-price">{price_str}</div>
                <div class="price-status">
                    <span class="dot"></span>
                    <span>15-min delayed</span>
                </div>
            </div>
        </div>
        
        <div class="bias-section">
            <div class="bias-header">
                <span class="bias-label">MA Bias</span>
                <span class="bias-badge {bias_class}">{bias_text}</span>
            </div>
            <div class="ma-values">
                <div class="ma-item">
                    <span class="label">50 EMA</span>
                    <span class="value">{ema_str}</span>
                </div>
                <div class="ma-item">
                    <span class="label">200 SMA</span>
                    <span class="value">{sma_str}</span>
                </div>
            </div>
        </div>
        
        <div class="structure-section">
            <div class="structure-title">
                <span>📊</span>
                <span>Day Structure (Overnight Session)</span>
            </div>
            <div class="structure-grid">
                <div class="structure-box ceiling">
                    <div class="box-label">Ceiling</div>
                    <div class="box-value">{ceiling_str}</div>
                    <div class="box-detail">{ceiling_detail}</div>
                </div>
                <div class="structure-box floor">
                    <div class="box-label">Floor</div>
                    <div class="box-value">{floor_str}</div>
                    <div class="box-detail">{floor_detail}</div>
                </div>
            </div>
        </div>
        
        <div class="trade-signal {signal_class}">
            <div class="signal-header">
                <span class="signal-direction {signal_class}">{setup.direction.value}</span>
                <span class="signal-icon">{signal_icon}</span>
            </div>
            
            <div class="trade-levels">
                <div class="level-box entry">
                    <div class="level-label">Entry</div>
                    <div class="level-value">{entry_str}</div>
                </div>
                <div class="level-box target">
                    <div class="level-label">Target</div>
                    <div class="level-value">{target_str}</div>
                </div>
                <div class="level-box stop">
                    <div class="level-label">Stop Loss</div>
                    <div class="level-value">{stop_str}</div>
                </div>
            </div>
            
            <div class="rr-display">
                <div class="rr-item">
                    <div class="rr-label">Reward</div>
                    <div class="rr-value">{reward_str}</div>
                </div>
                <div class="rr-item">
                    <div class="rr-label">Risk</div>
                    <div class="rr-value">{risk_str}</div>
                </div>
                <div class="rr-item">
                    <div class="rr-label">R:R Ratio</div>
                    <div class="rr-value">{rr_str}</div>
                </div>
            </div>
            
            {warnings_html}
        </div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)

def render_sidebar_inputs(symbol: str) -> dict:
    info = STOCK_INFO.get(symbol, {"name": symbol, "icon": "📊", "color": "#667eea"})
    
    st.sidebar.markdown(f"### {info['icon']} {symbol}")
    st.sidebar.caption(info['name'])
    
    if f"{symbol}_data" not in st.session_state:
        st.session_state[f"{symbol}_data"] = {
            "current_price": 0.0,
            "ema_50": 0.0,
            "sma_200": 0.0,
            "high_1": 0.0,
            "high_time_1": "5:00 PM",
            "high_2": 0.0,
            "high_time_2": "6:00 AM",
            "low_1": 0.0,
            "low_time_1": "5:00 PM",
            "low_2": 0.0,
            "low_time_2": "6:00 AM",
        }
    
    data = st.session_state[f"{symbol}_data"]
    
    # Price input
    data["current_price"] = st.sidebar.number_input(
        "Current Price $",
        min_value=0.0,
        value=data["current_price"],
        step=0.01,
        key=f"{symbol}_price",
        format="%.2f"
    )
    
    # MA inputs
    col1, col2 = st.sidebar.columns(2)
    with col1:
        data["ema_50"] = st.number_input(
            "50 EMA",
            min_value=0.0,
            value=data["ema_50"],
            step=0.01,
            key=f"{symbol}_ema",
            format="%.2f"
        )
    with col2:
        data["sma_200"] = st.number_input(
            "200 SMA",
            min_value=0.0,
            value=data["sma_200"],
            step=0.01,
            key=f"{symbol}_sma",
            format="%.2f"
        )
    
    st.sidebar.markdown("**🔺 Overnight Highs (Ceiling)**")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        data["high_1"] = st.number_input(
            "High 1 $",
            min_value=0.0,
            value=data["high_1"],
            step=0.01,
            key=f"{symbol}_high1",
            format="%.2f"
        )
    with col2:
        data["high_time_1"] = st.text_input(
            "Time 1",
            value=data["high_time_1"],
            key=f"{symbol}_high_time1"
        )
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        data["high_2"] = st.number_input(
            "High 2 $",
            min_value=0.0,
            value=data["high_2"],
            step=0.01,
            key=f"{symbol}_high2",
            format="%.2f"
        )
    with col2:
        data["high_time_2"] = st.text_input(
            "Time 2",
            value=data["high_time_2"],
            key=f"{symbol}_high_time2"
        )
    
    st.sidebar.markdown("**🔻 Overnight Lows (Floor)**")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        data["low_1"] = st.number_input(
            "Low 1 $",
            min_value=0.0,
            value=data["low_1"],
            step=0.01,
            key=f"{symbol}_low1",
            format="%.2f"
        )
    with col2:
        data["low_time_1"] = st.text_input(
            "Time 1",
            value=data["low_time_1"],
            key=f"{symbol}_low_time1"
        )
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        data["low_2"] = st.number_input(
            "Low 2 $",
            min_value=0.0,
            value=data["low_2"],
            step=0.01,
            key=f"{symbol}_low2",
            format="%.2f"
        )
    with col2:
        data["low_time_2"] = st.text_input(
            "Time 2",
            value=data["low_time_2"],
            key=f"{symbol}_low_time2"
        )
    
    st.sidebar.markdown("---")
    
    return data

def render_rules():
    st.markdown("""
    <div class="rules-section">
        <div class="rules-title">
            <span>📖</span>
            <span>Trading Rules</span>
        </div>
        
        <div class="rule-item">
            <strong>1. MA Bias → Direction</strong><br>
            🟢 <strong>BULLISH:</strong> 50 EMA > 200 SMA AND Price > 50 EMA → LONG only<br>
            🔴 <strong>BEARISH:</strong> 50 EMA < 200 SMA AND Price < 50 EMA → SHORT only
        </div>
        
        <div class="rule-item">
            <strong>2. Day Structure → Levels</strong><br>
            📊 Ceiling = Higher of two overnight highs (5pm-7am)<br>
            📊 Floor = Lower of two overnight lows (5pm-7am)
        </div>
        
        <div class="rule-item">
            <strong>3. Trade Execution</strong><br>
            🚀 LONG: Enter at Floor → Exit at Ceiling<br>
            🔻 SHORT: Enter at Ceiling → Exit at Floor<br>
            ⏰ Optimal entry window: 9-10am ET
        </div>
        
        <div class="rule-item">
            <strong>4. Risk Management</strong><br>
            🛡️ Stop Loss: 0.2% beyond entry line<br>
            ⚖️ Minimum R:R Ratio: 1.5:1
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_footer():
    st.markdown("""
    <div class="footer">
        <span class="footer-brand">Stock Prophet Elite</span> • v2.0<br>
        Data via Polygon.io (15-min delayed) • Not financial advice
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# DATA PROCESSING
# ============================================================================

def process_stock_data(symbol: str, inputs: dict) -> StockData:
    stock = StockData(symbol=symbol)
    
    # Get current price from Polygon or manual
    if inputs.get("current_price", 0) > 0:
        stock.current_price = inputs["current_price"]
        stock.polygon_connected = True
    else:
        price, connected = fetch_current_price(symbol)
        stock.current_price = price
        stock.polygon_connected = connected
    
    # MA values
    stock.ema_50 = inputs.get("ema_50") if inputs.get("ema_50", 0) > 0 else None
    stock.sma_200 = inputs.get("sma_200") if inputs.get("sma_200", 0) > 0 else None
    
    # High points
    stock.high_point_1 = inputs.get("high_1") if inputs.get("high_1", 0) > 0 else None
    stock.high_time_1 = inputs.get("high_time_1", "")
    stock.high_point_2 = inputs.get("high_2") if inputs.get("high_2", 0) > 0 else None
    stock.high_time_2 = inputs.get("high_time_2", "")
    
    # Low points
    stock.low_point_1 = inputs.get("low_1") if inputs.get("low_1", 0) > 0 else None
    stock.low_time_1 = inputs.get("low_time_1", "")
    stock.low_point_2 = inputs.get("low_2") if inputs.get("low_2", 0) > 0 else None
    stock.low_time_2 = inputs.get("low_time_2", "")
    
    # Calculate ceiling and floor
    highs = [h for h in [stock.high_point_1, stock.high_point_2] if h is not None]
    lows = [l for l in [stock.low_point_1, stock.low_point_2] if l is not None]
    
    stock.ceiling = max(highs) if highs else None
    stock.floor = min(lows) if lows else None
    
    # Determine MA bias
    stock.ma_bias = determine_ma_bias(stock.current_price, stock.ema_50, stock.sma_200)
    
    return stock

# ============================================================================
# MAIN
# ============================================================================

def main():
    st.set_page_config(
        page_title="Stock Prophet Elite",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    inject_premium_styles()
    render_header()
    
    # Sidebar
    st.sidebar.markdown("# 🎛️ Data Input")
    st.sidebar.caption("Enter values from ThinkorSwim")
    
    if st.sidebar.button("🔄 Refresh Prices", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Collect inputs
    all_inputs = {}
    for symbol in STOCK_UNIVERSE:
        all_inputs[symbol] = render_sidebar_inputs(symbol)
    
    # Process stocks
    stocks = [process_stock_data(symbol, all_inputs[symbol]) for symbol in STOCK_UNIVERSE]
    setups = [calculate_trade_setup(stock) for stock in stocks]
    
    # Check if any connected
    any_connected = any(s.polygon_connected for s in stocks)
    
    # Render status bar
    render_status_bar(setups, any_connected)
    
    # Render stock cards
    for stock, setup in zip(stocks, setups):
        render_stock_card(stock, setup)
    
    # Rules section
    with st.expander("📖 Trading Rules Reference", expanded=False):
        render_rules()
    
    render_footer()

if __name__ == "__main__":
    main()
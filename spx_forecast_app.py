"""
Stock Prophet - Daily Trading Entry System
Powered by Polygon API + ThinkorSwim Manual Inputs
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

POLYGON_API_KEY = "DCWuTS1R_fukpfjgf7QnXrLTEOS_giq6"
POLYGON_BASE_URL = "https://api.polygon.io"

WATCHLIST = ["AAPL", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "MSFT", "AMD", "SPY", "QQQ"]

STOP_BUFFER = {
    "AAPL": 0.50, "NVDA": 1.00, "TSLA": 1.00, "AMZN": 1.00, "META": 1.00,
    "GOOGL": 0.75, "MSFT": 0.50, "AMD": 0.50, "SPY": 0.50, "QQQ": 0.50
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class StockData:
    symbol: str
    current_price: Optional[float] = None
    prev_close: Optional[float] = None
    prev_high: Optional[float] = None
    prev_low: Optional[float] = None
    ema_50: Optional[float] = None
    sma_200: Optional[float] = None
    ma_bias: str = "Neutral"
    high_line: Optional[float] = None
    low_line: Optional[float] = None
    use_manual: bool = False
    polygon_connected: bool = False
    last_updated: Optional[datetime] = None

@dataclass
class TradeSetup:
    direction: str  # "LONG", "SHORT", "NO TRADE"
    entry: Optional[float] = None
    exit_target: Optional[float] = None
    stop_loss: Optional[float] = None
    reward: Optional[float] = None
    risk: Optional[float] = None
    rr_ratio: Optional[float] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

# ============================================================================
# POLYGON API FUNCTIONS
# ============================================================================

def check_polygon_connection() -> bool:
    """Test Polygon API connection"""
    try:
        url = f"{POLYGON_BASE_URL}/v3/reference/tickers?ticker=AAPL&apiKey={POLYGON_API_KEY}"
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except Exception as e:
        # Log error for debugging but don't crash
        print(f"Polygon connection check failed: {e}")
        return False

def fetch_current_price(symbol: str) -> Tuple[Optional[float], bool]:
    """Fetch current price snapshot (15-min delayed)"""
    try:
        url = f"{POLYGON_BASE_URL}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}?apiKey={POLYGON_API_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "ticker" in data and "lastTrade" in data["ticker"]:
                return data["ticker"]["lastTrade"]["p"], True
            elif "ticker" in data and "day" in data["ticker"]:
                return data["ticker"]["day"]["c"], True
        # If snapshot fails, try previous day close as fallback
        return None, False
    except Exception as e:
        print(f"Price fetch failed for {symbol}: {e}")
        return None, False

def fetch_prev_day(symbol: str) -> Tuple[Optional[float], Optional[float], Optional[float], bool]:
    """Fetch previous day OHLC"""
    try:
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                return result.get("c"), result.get("h"), result.get("l"), True
    except:
        pass
    return None, None, None, False

def fetch_historical_bars(symbol: str, days: int = 250) -> Optional[pd.DataFrame]:
    """Fetch historical bars for MA calculation"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 50)  # Extra buffer for trading days
        
        url = (f"{POLYGON_BASE_URL}/v2/aggs/ticker/{symbol}/range/1/day/"
               f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
               f"?adjusted=true&sort=asc&apiKey={POLYGON_API_KEY}")
        
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                df = pd.DataFrame(data["results"])
                df['date'] = pd.to_datetime(df['t'], unit='ms')
                df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
                return df[['date', 'open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        pass
    return None

def calculate_ma_bias(df: pd.DataFrame, current_price: float) -> Tuple[Optional[float], Optional[float], str]:
    """Calculate 50 EMA and 200 SMA, determine bias"""
    if df is None or len(df) < 200:
        return None, None, "Neutral"
    
    # Calculate EMAs and SMAs on daily data (proxy for 30-min, adjust as needed)
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()
    
    ema_50 = df['ema_50'].iloc[-1]
    sma_200 = df['sma_200'].iloc[-1]
    
    # Determine bias
    if ema_50 > sma_200 and current_price > ema_50:
        bias = "Bullish"
    elif ema_50 < sma_200 and current_price < ema_50:
        bias = "Bearish"
    else:
        bias = "Neutral"
    
    return ema_50, sma_200, bias

def fetch_all_stock_data(symbol: str) -> StockData:
    """Fetch all data for a single stock from Polygon"""
    stock = StockData(symbol=symbol)
    
    # Get current price
    price, connected = fetch_current_price(symbol)
    if price:
        stock.current_price = price
        stock.polygon_connected = True
    
    # Get previous day data
    prev_close, prev_high, prev_low, success = fetch_prev_day(symbol)
    if success:
        stock.prev_close = prev_close
        stock.prev_high = prev_high
        stock.prev_low = prev_low
        stock.polygon_connected = True
    
    # Get historical data for MA calculation
    if stock.current_price:
        df = fetch_historical_bars(symbol)
        if df is not None:
            ema_50, sma_200, bias = calculate_ma_bias(df, stock.current_price)
            stock.ema_50 = ema_50
            stock.sma_200 = sma_200
            stock.ma_bias = bias
    
    stock.last_updated = datetime.now()
    return stock

# ============================================================================
# TRADE LOGIC
# ============================================================================

def calculate_trade_setup(stock: StockData) -> TradeSetup:
    """Calculate trade setup based on MA bias and day structure"""
    setup = TradeSetup(direction="NO TRADE")
    
    # Check for required data
    if stock.high_line is None or stock.low_line is None:
        setup.warnings.append("⚠️ Missing High Line or Low Line")
        return setup
    
    if stock.current_price is None:
        setup.warnings.append("⚠️ No current price available")
        return setup
    
    buffer = STOP_BUFFER.get(stock.symbol, 0.50)
    
    # Get current time for entry window check
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    
    if stock.ma_bias == "Bullish":
        # LONG setup: Entry at Floor, Exit at Ceiling
        setup.direction = "LONG"
        setup.entry = stock.low_line
        setup.exit_target = stock.high_line
        setup.stop_loss = stock.low_line - buffer
        setup.reward = stock.high_line - stock.low_line
        setup.risk = buffer
        
    elif stock.ma_bias == "Bearish":
        # SHORT setup: Entry at Ceiling, Exit at Floor
        setup.direction = "SHORT"
        setup.entry = stock.high_line
        setup.exit_target = stock.low_line
        setup.stop_loss = stock.high_line + buffer
        setup.reward = stock.high_line - stock.low_line
        setup.risk = buffer
        
    else:  # Neutral
        setup.direction = "NO TRADE"
        setup.warnings.append("⚠️ MA Bias is Neutral - No clear direction")
        return setup
    
    # Calculate R:R ratio
    if setup.risk and setup.risk > 0:
        setup.rr_ratio = setup.reward / setup.risk
    
    # Entry window warning (9-10am optimal)
    if current_hour < 9 or current_hour >= 10:
        setup.warnings.append(f"⏰ Outside optimal entry window (9-10am EST)")
    
    # Price position warnings
    if setup.direction == "LONG" and stock.current_price > stock.low_line:
        diff = stock.current_price - stock.low_line
        setup.warnings.append(f"📍 Price ${diff:.2f} above entry zone")
    elif setup.direction == "SHORT" and stock.current_price < stock.high_line:
        diff = stock.high_line - stock.current_price
        setup.warnings.append(f"📍 Price ${diff:.2f} below entry zone")
    
    return setup

# ============================================================================
# STREAMLIT UI
# ============================================================================

def apply_custom_css():
    """Apply dark glassmorphism theme"""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
    
    :root {
        --bg-primary: #0a0a0f;
        --bg-secondary: rgba(20, 20, 30, 0.8);
        --bg-card: rgba(25, 25, 40, 0.6);
        --glass-border: rgba(255, 255, 255, 0.1);
        --text-primary: #ffffff;
        --text-secondary: rgba(255, 255, 255, 0.7);
        --text-muted: rgba(255, 255, 255, 0.4);
        --accent-green: #00ff88;
        --accent-red: #ff4466;
        --accent-blue: #4488ff;
        --accent-gold: #ffd700;
        --glow-green: 0 0 30px rgba(0, 255, 136, 0.3);
        --glow-red: 0 0 30px rgba(255, 68, 102, 0.3);
        --glow-blue: 0 0 20px rgba(68, 136, 255, 0.2);
    }
    
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0f0f1a 100%);
        font-family: 'Space Grotesk', sans-serif;
    }
    
    .stApp > header {
        background: transparent !important;
    }
    
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        max-width: 1400px;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(20, 20, 35, 0.95) 0%, rgba(10, 10, 20, 0.98) 100%);
        border-right: 1px solid var(--glass-border);
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: var(--text-secondary);
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
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(255, 255, 255, 0.2);
        transform: translateY(-2px);
    }
    
    .glass-card.long-setup {
        border-color: rgba(0, 255, 136, 0.4);
        box-shadow: var(--glow-green);
    }
    
    .glass-card.short-setup {
        border-color: rgba(255, 68, 102, 0.4);
        box-shadow: var(--glow-red);
    }
    
    .glass-card.no-trade {
        border-color: rgba(128, 128, 128, 0.3);
        opacity: 0.7;
    }
    
    /* Top stats bar */
    .stats-bar {
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;
    }
    
    .status-indicator {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
    }
    
    .status-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    
    .status-dot.connected {
        background: var(--accent-green);
        box-shadow: 0 0 10px var(--accent-green);
    }
    
    .status-dot.disconnected {
        background: var(--accent-red);
        box-shadow: 0 0 10px var(--accent-red);
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Stock card elements */
    .stock-symbol {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
    }
    
    .stock-price {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.4rem;
        color: var(--text-primary);
    }
    
    .bias-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .bias-bullish {
        background: rgba(0, 255, 136, 0.2);
        color: var(--accent-green);
        border: 1px solid rgba(0, 255, 136, 0.3);
    }
    
    .bias-bearish {
        background: rgba(255, 68, 102, 0.2);
        color: var(--accent-red);
        border: 1px solid rgba(255, 68, 102, 0.3);
    }
    
    .bias-neutral {
        background: rgba(128, 128, 128, 0.2);
        color: rgba(255, 255, 255, 0.6);
        border: 1px solid rgba(128, 128, 128, 0.3);
    }
    
    .trade-direction {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.2rem;
        font-weight: 700;
        padding: 8px 16px;
        border-radius: 8px;
        display: inline-block;
    }
    
    .trade-long {
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.3), rgba(0, 200, 100, 0.2));
        color: var(--accent-green);
        border: 1px solid rgba(0, 255, 136, 0.4);
    }
    
    .trade-short {
        background: linear-gradient(135deg, rgba(255, 68, 102, 0.3), rgba(200, 50, 80, 0.2));
        color: var(--accent-red);
        border: 1px solid rgba(255, 68, 102, 0.4);
    }
    
    .trade-none {
        background: rgba(128, 128, 128, 0.2);
        color: rgba(255, 255, 255, 0.5);
        border: 1px solid rgba(128, 128, 128, 0.3);
    }
    
    .data-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
    }
    
    .data-label {
        color: var(--text-muted);
    }
    
    .data-value {
        color: var(--text-primary);
        font-weight: 500;
    }
    
    .warning-box {
        background: rgba(255, 200, 50, 0.1);
        border: 1px solid rgba(255, 200, 50, 0.3);
        border-radius: 8px;
        padding: 8px 12px;
        margin-top: 8px;
        font-size: 0.85rem;
        color: rgba(255, 200, 50, 0.9);
    }
    
    /* Rules section */
    .rules-section {
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 16px;
        padding: 1.5rem;
        margin-top: 2rem;
    }
    
    .rules-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: var(--accent-gold);
    }
    
    /* Summary badges */
    .summary-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        font-weight: 600;
        margin-right: 10px;
    }
    
    .summary-long {
        background: rgba(0, 255, 136, 0.2);
        color: var(--accent-green);
    }
    
    .summary-short {
        background: rgba(255, 68, 102, 0.2);
        color: var(--accent-red);
    }
    
    .summary-none {
        background: rgba(128, 128, 128, 0.2);
        color: rgba(255, 255, 255, 0.6);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 12px !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, rgba(68, 136, 255, 0.3), rgba(50, 100, 200, 0.2)) !important;
        border: 1px solid rgba(68, 136, 255, 0.4) !important;
        color: white !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(68, 136, 255, 0.5), rgba(50, 100, 200, 0.4)) !important;
        box-shadow: var(--glow-blue) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Input styling */
    .stNumberInput input, .stSelectbox select, .stTextInput input {
        background: rgba(30, 30, 50, 0.8) !important;
        border: 1px solid var(--glass-border) !important;
        color: white !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Toggle styling */
    .stCheckbox label {
        color: var(--text-secondary) !important;
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

def render_stock_card(stock: StockData, setup: TradeSetup):
    """Render a single stock card"""
    # Determine card class based on setup
    if setup.direction == "LONG":
        card_class = "long-setup"
    elif setup.direction == "SHORT":
        card_class = "short-setup"
    else:
        card_class = "no-trade"
    
    # Bias badge class
    bias_class = f"bias-{stock.ma_bias.lower()}"
    
    # Trade direction class
    if setup.direction == "LONG":
        trade_class = "trade-long"
    elif setup.direction == "SHORT":
        trade_class = "trade-short"
    else:
        trade_class = "trade-none"
    
    # Connection status
    conn_status = "🟢" if stock.polygon_connected else "🔴"
    data_source = "Manual" if stock.use_manual else "Polygon"
    
    with st.expander(f"**{stock.symbol}** — ${stock.current_price or 0:.2f} {conn_status}", expanded=True):
        st.markdown(f"""
        <div class="glass-card {card_class}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                <div>
                    <div class="stock-symbol">{stock.symbol}</div>
                    <div class="stock-price">${stock.current_price or 0:.2f}</div>
                    <div style="font-size: 0.75rem; color: rgba(255,255,255,0.4); margin-top: 4px;">
                        {conn_status} {data_source} {f"• Updated: {stock.last_updated.strftime('%H:%M:%S')}" if stock.last_updated else ""}
                    </div>
                </div>
                <span class="bias-badge {bias_class}">{stock.ma_bias}</span>
            </div>
            
            <div style="margin-bottom: 1rem;">
                <div class="data-row">
                    <span class="data-label">50 EMA</span>
                    <span class="data-value">${stock.ema_50:.2f if stock.ema_50 else 'N/A'}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">200 SMA</span>
                    <span class="data-value">${stock.sma_200:.2f if stock.sma_200 else 'N/A'}</span>
                </div>
            </div>
            
            <div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 12px; margin-bottom: 1rem;">
                <div style="font-size: 0.75rem; color: rgba(255,255,255,0.5); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.1em;">Day Structure</div>
                <div class="data-row" style="border: none;">
                    <span class="data-label">🔺 Ceiling (High Line)</span>
                    <span class="data-value">${stock.high_line:.2f if stock.high_line else 'Not Set'}</span>
                </div>
                <div class="data-row" style="border: none;">
                    <span class="data-label">🔻 Floor (Low Line)</span>
                    <span class="data-value">${stock.low_line:.2f if stock.low_line else 'Not Set'}</span>
                </div>
            </div>
            
            <div style="text-align: center; margin-bottom: 1rem;">
                <span class="trade-direction {trade_class}">{"📈 " if setup.direction == "LONG" else "📉 " if setup.direction == "SHORT" else "⏸️ "}{setup.direction}</span>
            </div>
            
            {f'''
            <div class="data-row">
                <span class="data-label">Entry</span>
                <span class="data-value" style="color: {"#00ff88" if setup.direction == "LONG" else "#ff4466"};">${setup.entry:.2f}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Exit Target</span>
                <span class="data-value">${setup.exit_target:.2f}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Stop Loss</span>
                <span class="data-value" style="color: #ff4466;">${setup.stop_loss:.2f}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Reward / Risk</span>
                <span class="data-value" style="color: #ffd700;">${setup.reward:.2f} / ${setup.risk:.2f} ({setup.rr_ratio:.1f}R)</span>
            </div>
            ''' if setup.entry else ''}
        </div>
        """, unsafe_allow_html=True)
        
        # Render warnings
        if setup.warnings:
            for warning in setup.warnings:
                st.markdown(f"""<div class="warning-box">{warning}</div>""", unsafe_allow_html=True)

def render_sidebar_inputs(symbol: str, stock: StockData) -> StockData:
    """Render sidebar inputs for a stock"""
    st.markdown(f"### {symbol}")
    
    # Manual override toggle
    use_manual = st.checkbox(f"Manual Override", key=f"{symbol}_manual", value=stock.use_manual)
    stock.use_manual = use_manual
    
    if use_manual:
        # Manual current price
        stock.current_price = st.number_input(
            "Current Price", 
            value=float(stock.current_price or 0),
            step=0.01,
            key=f"{symbol}_price"
        )
        
        # Manual MA Bias
        bias_options = ["Bullish", "Bearish", "Neutral"]
        bias_index = bias_options.index(stock.ma_bias) if stock.ma_bias in bias_options else 2
        stock.ma_bias = st.selectbox(
            "MA Bias",
            options=bias_options,
            index=bias_index,
            key=f"{symbol}_bias"
        )
    else:
        # Show Polygon data
        if stock.current_price:
            st.markdown(f"**Price:** ${stock.current_price:.2f}")
        else:
            st.markdown("**Price:** Not available")
        
        if stock.ema_50 and stock.sma_200:
            st.markdown(f"**50 EMA:** ${stock.ema_50:.2f}")
            st.markdown(f"**200 SMA:** ${stock.sma_200:.2f}")
            st.markdown(f"**Bias:** {stock.ma_bias}")
        
        # Allow manual bias override even when using Polygon
        if st.checkbox(f"Override MA Bias", key=f"{symbol}_bias_override"):
            stock.ma_bias = st.selectbox(
                "MA Bias",
                options=["Bullish", "Bearish", "Neutral"],
                index=["Bullish", "Bearish", "Neutral"].index(stock.ma_bias),
                key=f"{symbol}_bias_select"
            )
    
    # Day Structure (always manual from TOS)
    st.markdown("**Day Structure (from TOS)**")
    stock.high_line = st.number_input(
        "High Line (Ceiling)",
        value=float(stock.high_line or 0),
        step=0.01,
        key=f"{symbol}_high"
    )
    stock.low_line = st.number_input(
        "Low Line (Floor)",
        value=float(stock.low_line or 0),
        step=0.01,
        key=f"{symbol}_low"
    )
    
    st.markdown("---")
    return stock

def render_trading_rules():
    """Render collapsible trading rules"""
    with st.expander("📖 Trading Rules Reference", expanded=False):
        st.markdown("""
        <div class="rules-section">
            <div class="rules-title">⚡ THE TWO PILLARS</div>
            
            <h4>1️⃣ MA BIAS → Direction</h4>
            <p><strong>50 EMA vs 200 SMA on 30-min Chart</strong></p>
            <ul>
                <li><span style="color: #00ff88;">BULLISH:</span> 50 EMA > 200 SMA AND Price > 50 EMA → LONG ONLY</li>
                <li><span style="color: #ff4466;">BEARISH:</span> 50 EMA < 200 SMA AND Price < 50 EMA → SHORT ONLY</li>
                <li><span style="color: rgba(255,255,255,0.5);">NEUTRAL:</span> Mixed signals → NO TRADE</li>
            </ul>
            
            <h4>2️⃣ DAY STRUCTURE → Entry/Exit Zones</h4>
            <p><strong>High Line + Low Line from TOS Overnight Session (5pm-7am)</strong></p>
            <ul>
                <li><strong>High Line = Ceiling:</strong> SHORT entry / LONG exit</li>
                <li><strong>Low Line = Floor:</strong> LONG entry / SHORT exit</li>
            </ul>
            
            <div class="rules-title" style="margin-top: 1.5rem;">📊 TRADE EXECUTION</div>
            
            <h4>LONG Setup (Bullish Bias)</h4>
            <ul>
                <li>Entry: At Floor (Low Line)</li>
                <li>Exit: At Ceiling (High Line)</li>
                <li>Stop: Below Floor (Low Line - buffer)</li>
            </ul>
            
            <h4>SHORT Setup (Bearish Bias)</h4>
            <ul>
                <li>Entry: At Ceiling (High Line)</li>
                <li>Exit: At Floor (Low Line)</li>
                <li>Stop: Above Ceiling (High Line + buffer)</li>
            </ul>
            
            <div class="rules-title" style="margin-top: 1.5rem;">⏰ TIMING</div>
            <ul>
                <li><strong>Optimal Entry Window:</strong> 9:00 AM - 10:00 AM EST</li>
                <li><strong>Avoid:</strong> Trading outside the entry window unless setup is exceptional</li>
            </ul>
            
            <div class="rules-title" style="margin-top: 1.5rem;">⚠️ CONFLICT RULES</div>
            <ul>
                <li>If bias is NEUTRAL → NO TRADE</li>
                <li>If High Line or Low Line not set → NO TRADE</li>
                <li>If price already past entry zone → Reduced position or wait for pullback</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="Stock Prophet",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    apply_custom_css()
    
    # Initialize session state
    if 'stocks' not in st.session_state:
        st.session_state.stocks = {symbol: StockData(symbol=symbol) for symbol in WATCHLIST}
    if 'polygon_connected' not in st.session_state:
        st.session_state.polygon_connected = False
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = None
    
    # Header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-family: 'Space Grotesk', sans-serif; font-size: 2.5rem; font-weight: 700; 
                   background: linear-gradient(135deg, #4488ff, #00ff88); -webkit-background-clip: text; 
                   -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;">
            📈 STOCK PROPHET
        </h1>
        <p style="color: rgba(255,255,255,0.6); font-family: 'JetBrains Mono', monospace; font-size: 0.9rem;">
            Daily Trading Entry System • MA Bias + Day Structure
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check Polygon connection
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("🔄 Refresh All", use_container_width=True):
            with st.spinner("Fetching data from Polygon..."):
                st.session_state.polygon_connected = check_polygon_connection()
                for symbol in WATCHLIST:
                    if not st.session_state.stocks[symbol].use_manual:
                        new_data = fetch_all_stock_data(symbol)
                        # Preserve manual inputs
                        new_data.high_line = st.session_state.stocks[symbol].high_line
                        new_data.low_line = st.session_state.stocks[symbol].low_line
                        new_data.use_manual = st.session_state.stocks[symbol].use_manual
                        st.session_state.stocks[symbol] = new_data
                st.session_state.last_refresh = datetime.now()
                st.rerun()
    
    # Connection status and summary
    polygon_status = "🟢 Connected" if st.session_state.polygon_connected else "🔴 Disconnected"
    
    # Calculate summary
    long_count = 0
    short_count = 0
    no_trade_count = 0
    
    for symbol in WATCHLIST:
        stock = st.session_state.stocks[symbol]
        setup = calculate_trade_setup(stock)
        if setup.direction == "LONG":
            long_count += 1
        elif setup.direction == "SHORT":
            short_count += 1
        else:
            no_trade_count += 1
    
    st.markdown(f"""
    <div class="stats-bar">
        <div class="status-indicator">
            <span class="status-dot {'connected' if st.session_state.polygon_connected else 'disconnected'}"></span>
            <span>Polygon API: {polygon_status}</span>
            <span style="color: rgba(255,255,255,0.4); margin-left: 10px;">
                {f"Last refresh: {st.session_state.last_refresh.strftime('%H:%M:%S')}" if st.session_state.last_refresh else "Not refreshed yet"}
            </span>
        </div>
        <div>
            <span class="summary-badge summary-long">{long_count} LONG</span>
            <span class="summary-badge summary-short">{short_count} SHORT</span>
            <span class="summary-badge summary-none">{no_trade_count} NO TRADE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for inputs
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h2 style="font-family: 'Space Grotesk', sans-serif; color: white;">⚙️ Stock Inputs</h2>
            <p style="color: rgba(255,255,255,0.5); font-size: 0.85rem;">Configure each stock's parameters</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Stock selector tabs
        selected_stock = st.selectbox(
            "Select Stock to Configure",
            options=WATCHLIST,
            key="stock_selector"
        )
        
        st.markdown("---")
        
        # Render inputs for selected stock
        stock = st.session_state.stocks[selected_stock]
        updated_stock = render_sidebar_inputs(selected_stock, stock)
        st.session_state.stocks[selected_stock] = updated_stock
    
    # Main content - Stock cards grid
    col1, col2 = st.columns(2)
    
    for i, symbol in enumerate(WATCHLIST):
        stock = st.session_state.stocks[symbol]
        setup = calculate_trade_setup(stock)
        
        with col1 if i % 2 == 0 else col2:
            render_stock_card(stock, setup)
    
    # Trading Rules Reference
    render_trading_rules()
    
    # Footer
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem; padding: 1rem; color: rgba(255,255,255,0.3); font-size: 0.8rem;">
        <p>Stock Prophet v1.0 • Data from Polygon.io (15-min delayed) • For educational purposes only</p>
        <p>⚠️ Not financial advice. Always do your own research and manage risk appropriately.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
"""
Stock Prophet - Daily Trading Entry System
Uses MA Bias + Day Structure for 10 Popular Stocks
Data from Polygon API or Manual ThinkorSwim Input
"""

import streamlit as st
import requests
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

POLYGON_API_KEY = "DCWuTS1R_fukpfjgf7QnXrLTEOS_giq6"
POLYGON_BASE_URL = "https://api.polygon.io"

# Stock Universe
STOCK_UNIVERSE = ["AAPL", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "MSFT", "AMD", "SPY", "QQQ"]

# Risk Management
STOP_BUFFER_PERCENT = 0.002  # 0.2% buffer beyond entry line

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
    prev_close: Optional[float] = None
    prev_high: Optional[float] = None
    prev_low: Optional[float] = None
    ema_50: Optional[float] = None
    sma_200: Optional[float] = None
    ma_bias: MABias = MABias.NEUTRAL
    high_line: Optional[float] = None  # Overnight ceiling
    low_line: Optional[float] = None   # Overnight floor
    use_polygon: bool = True
    polygon_connected: bool = False
    last_updated: Optional[datetime] = None

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
# POLYGON API FUNCTIONS
# ============================================================================

@st.cache_data(ttl=60)  # Cache for 1 minute
def fetch_current_price(symbol: str) -> Tuple[Optional[float], bool]:
    """Fetch current price snapshot from Polygon"""
    try:
        url = f"{POLYGON_BASE_URL}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
        params = {"apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK" and "ticker" in data:
                ticker_data = data["ticker"]
                # Try to get last trade price, fallback to day close
                if "lastTrade" in ticker_data:
                    return ticker_data["lastTrade"].get("p"), True
                elif "day" in ticker_data:
                    return ticker_data["day"].get("c"), True
                elif "prevDay" in ticker_data:
                    return ticker_data["prevDay"].get("c"), True
        return None, False
    except Exception as e:
        st.error(f"Error fetching price for {symbol}: {e}")
        return None, False

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_previous_day(symbol: str) -> Tuple[Optional[float], Optional[float], Optional[float], bool]:
    """Fetch previous day OHLC from Polygon"""
    try:
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{symbol}/prev"
        params = {"apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                return result.get("h"), result.get("l"), result.get("c"), True
        return None, None, None, False
    except Exception as e:
        st.error(f"Error fetching previous day for {symbol}: {e}")
        return None, None, None, False

@st.cache_data(ttl=900)  # Cache for 15 minutes
def fetch_historical_bars(symbol: str, days: int = 250) -> Tuple[Optional[pd.DataFrame], bool]:
    """Fetch historical daily bars for MA calculation"""
    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days + 50)).strftime("%Y-%m-%d")
        
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
        params = {"apiKey": POLYGON_API_KEY, "limit": 300}
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK" and data.get("results"):
                df = pd.DataFrame(data["results"])
                df['date'] = pd.to_datetime(df['t'], unit='ms')
                df = df.sort_values('date')
                return df, True
        return None, False
    except Exception as e:
        st.error(f"Error fetching history for {symbol}: {e}")
        return None, False

def calculate_moving_averages(df: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
    """Calculate 50 EMA and 200 SMA from historical data"""
    if df is None or len(df) < 200:
        return None, None
    
    try:
        # Calculate EMAs and SMAs
        df['ema_50'] = df['c'].ewm(span=50, adjust=False).mean()
        df['sma_200'] = df['c'].rolling(window=200).mean()
        
        # Get latest values
        ema_50 = df['ema_50'].iloc[-1]
        sma_200 = df['sma_200'].iloc[-1]
        
        return round(ema_50, 2), round(sma_200, 2)
    except Exception:
        return None, None

def determine_ma_bias(current_price: Optional[float], ema_50: Optional[float], sma_200: Optional[float]) -> MABias:
    """Determine MA Bias based on price relationship to MAs"""
    if None in (current_price, ema_50, sma_200):
        return MABias.NEUTRAL
    
    # Bullish: 50 EMA > 200 SMA AND Price > 50 EMA
    if ema_50 > sma_200 and current_price > ema_50:
        return MABias.BULLISH
    # Bearish: 50 EMA < 200 SMA AND Price < 50 EMA
    elif ema_50 < sma_200 and current_price < ema_50:
        return MABias.BEARISH
    else:
        return MABias.NEUTRAL

# ============================================================================
# TRADE LOGIC
# ============================================================================

def calculate_trade_setup(stock: StockData) -> TradeSetup:
    """Calculate trade setup based on MA Bias and Day Structure"""
    setup = TradeSetup(direction=TradeDirection.NO_TRADE)
    
    # Validate required data
    if stock.high_line is None or stock.low_line is None:
        setup.warnings.append("⚠️ Missing High Line or Low Line")
        return setup
    
    if stock.current_price is None:
        setup.warnings.append("⚠️ No current price available")
        return setup
    
    if stock.high_line <= stock.low_line:
        setup.warnings.append("⚠️ High Line must be greater than Low Line")
        return setup
    
    # Check time window (optimal entry 9-10am)
    current_hour = datetime.now().hour
    if current_hour < 9 or current_hour > 10:
        setup.warnings.append(f"ℹ️ Current time: {datetime.now().strftime('%I:%M %p')} - Optimal entry window is 9-10am ET")
    
    # Determine trade based on bias
    if stock.ma_bias == MABias.BULLISH:
        # LONG at Floor, Exit at Ceiling
        setup.direction = TradeDirection.LONG
        setup.entry = stock.low_line
        setup.exit_target = stock.high_line
        setup.stop_loss = round(stock.low_line * (1 - STOP_BUFFER_PERCENT), 2)
        setup.is_valid = True
        
        # Check if price is near entry
        if stock.current_price > stock.low_line * 1.02:
            setup.warnings.append("⚠️ Price above Floor - may have missed entry")
        
    elif stock.ma_bias == MABias.BEARISH:
        # SHORT at Ceiling, Exit at Floor
        setup.direction = TradeDirection.SHORT
        setup.entry = stock.high_line
        setup.exit_target = stock.low_line
        setup.stop_loss = round(stock.high_line * (1 + STOP_BUFFER_PERCENT), 2)
        setup.is_valid = True
        
        # Check if price is near entry
        if stock.current_price < stock.high_line * 0.98:
            setup.warnings.append("⚠️ Price below Ceiling - may have missed entry")
    else:
        setup.warnings.append("⚠️ Neutral bias - no clear trade direction")
        return setup
    
    # Calculate reward/risk
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
                setup.warnings.append(f"⚠️ R:R ratio ({setup.rr_ratio}) below 1.5 minimum")
    
    return setup

# ============================================================================
# UI COMPONENTS
# ============================================================================

def inject_styles():
    """Inject custom CSS for glassmorphism dark theme"""
    st.markdown("""
    <style>
    /* Dark theme base */
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* Glassmorphism card */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        margin: 10px 0;
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    /* Long trade glow */
    .long-glow {
        box-shadow: 0 0 20px rgba(34, 197, 94, 0.3),
                    0 0 40px rgba(34, 197, 94, 0.1);
        border-color: rgba(34, 197, 94, 0.5);
    }
    
    /* Short trade glow */
    .short-glow {
        box-shadow: 0 0 20px rgba(239, 68, 68, 0.3),
                    0 0 40px rgba(239, 68, 68, 0.1);
        border-color: rgba(239, 68, 68, 0.5);
    }
    
    /* No trade (neutral) */
    .neutral-glow {
        box-shadow: 0 0 20px rgba(107, 114, 128, 0.2);
        border-color: rgba(107, 114, 128, 0.3);
    }
    
    /* Status indicators */
    .status-connected {
        color: #22c55e;
        font-weight: 600;
    }
    
    .status-disconnected {
        color: #ef4444;
        font-weight: 600;
    }
    
    /* Stock symbol header */
    .stock-symbol {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Price display */
    .current-price {
        font-size: 1.5rem;
        font-weight: 600;
        color: #e2e8f0;
    }
    
    /* Bias badges */
    .bias-bullish {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    
    .bias-bearish {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    
    .bias-neutral {
        background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    
    /* Trade direction badges */
    .trade-long {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        color: white;
        padding: 8px 20px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1.1rem;
        display: inline-block;
    }
    
    .trade-short {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 8px 20px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1.1rem;
        display: inline-block;
    }
    
    .trade-none {
        background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
        color: white;
        padding: 8px 20px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1.1rem;
        display: inline-block;
    }
    
    /* Data rows */
    .data-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .data-label {
        color: #94a3b8;
        font-size: 0.9rem;
    }
    
    .data-value {
        color: #e2e8f0;
        font-weight: 600;
    }
    
    /* Warning text */
    .warning-text {
        color: #fbbf24;
        font-size: 0.85rem;
        margin: 4px 0;
    }
    
    /* Top bar */
    .top-bar {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 15px 20px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
    }
    
    /* Summary badges */
    .summary-badge {
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    
    .summary-long {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    
    .summary-short {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .summary-none {
        background: rgba(107, 114, 128, 0.2);
        color: #9ca3af;
        border: 1px solid rgba(107, 114, 128, 0.3);
    }
    
    /* Rules section */
    .rules-section {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 20px;
        margin-top: 30px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .rules-title {
        color: #a78bfa;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 15px;
    }
    
    .rule-item {
        color: #cbd5e1;
        padding: 8px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Improve sidebar */
    .css-1d391kg {
        background: rgba(0, 0, 0, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)

def render_top_bar(stocks: List[StockData], setups: List[TradeSetup], polygon_status: bool):
    """Render top summary bar"""
    long_count = sum(1 for s in setups if s.direction == TradeDirection.LONG)
    short_count = sum(1 for s in setups if s.direction == TradeDirection.SHORT)
    no_trade_count = sum(1 for s in setups if s.direction == TradeDirection.NO_TRADE)
    
    status_class = "status-connected" if polygon_status else "status-disconnected"
    status_icon = "🟢" if polygon_status else "🔴"
    status_text = "Connected (15-min delayed)" if polygon_status else "Disconnected"
    
    st.markdown(f"""
    <div class="top-bar">
        <div>
            <span style="color: #94a3b8; margin-right: 8px;">Polygon:</span>
            <span class="{status_class}">{status_icon} {status_text}</span>
        </div>
        <div style="display: flex; gap: 10px;">
            <span class="summary-badge summary-long">📈 {long_count} LONG</span>
            <span class="summary-badge summary-short">📉 {short_count} SHORT</span>
            <span class="summary-badge summary-none">⏸️ {no_trade_count} NO TRADE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def format_price(price: Optional[float]) -> str:
    """Format price for display"""
    if price is None:
        return "N/A"
    return f"${price:,.2f}"

def render_stock_card(stock: StockData, setup: TradeSetup):
    """Render individual stock card with trade setup"""
    # Determine card glow class
    if setup.direction == TradeDirection.LONG:
        glow_class = "long-glow"
    elif setup.direction == TradeDirection.SHORT:
        glow_class = "short-glow"
    else:
        glow_class = "neutral-glow"
    
    # Determine bias class
    if stock.ma_bias == MABias.BULLISH:
        bias_class = "bias-bullish"
    elif stock.ma_bias == MABias.BEARISH:
        bias_class = "bias-bearish"
    else:
        bias_class = "bias-neutral"
    
    # Determine trade class
    if setup.direction == TradeDirection.LONG:
        trade_class = "trade-long"
    elif setup.direction == TradeDirection.SHORT:
        trade_class = "trade-short"
    else:
        trade_class = "trade-none"
    
    # Format MA values
    ema_50_str = f"${stock.ema_50:.2f}" if stock.ema_50 else "N/A"
    sma_200_str = f"${stock.sma_200:.2f}" if stock.sma_200 else "N/A"
    
    # Build warnings HTML
    warnings_html = ""
    for warning in setup.warnings:
        warnings_html += f'<div class="warning-text">{warning}</div>'
    
    # Status indicator
    status_indicator = "🟢" if stock.polygon_connected else "🔴"
    if not stock.use_polygon:
        status_indicator = "📝"  # Manual mode
    
    html = f"""
    <div class="glass-card {glow_class}">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <div>
                <span class="stock-symbol">{stock.symbol}</span>
                <span style="margin-left: 8px;">{status_indicator}</span>
            </div>
            <span class="current-price">{format_price(stock.current_price)}</span>
        </div>
        
        <div style="margin-bottom: 15px;">
            <span class="{bias_class}">{stock.ma_bias.value}</span>
            <span style="color: #64748b; font-size: 0.8rem; margin-left: 10px;">
                50 EMA: {ema_50_str} | 200 SMA: {sma_200_str}
            </span>
        </div>
        
        <div class="data-row">
            <span class="data-label">📊 Day Structure</span>
            <span class="data-value">Floor: {format_price(stock.low_line)} | Ceiling: {format_price(stock.high_line)}</span>
        </div>
        
        <div style="margin: 15px 0; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px;">
            <div style="margin-bottom: 10px;">
                <span class="{trade_class}">{setup.direction.value}</span>
            </div>
            
            <div class="data-row">
                <span class="data-label">Entry</span>
                <span class="data-value">{format_price(setup.entry)}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Target</span>
                <span class="data-value" style="color: #22c55e;">{format_price(setup.exit_target)}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Stop Loss</span>
                <span class="data-value" style="color: #ef4444;">{format_price(setup.stop_loss)}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Reward / Risk</span>
                <span class="data-value">{setup.reward if setup.reward else 'N/A'} / {setup.risk if setup.risk else 'N/A'} pts</span>
            </div>
            <div class="data-row" style="border-bottom: none;">
                <span class="data-label">R:R Ratio</span>
                <span class="data-value" style="color: {'#22c55e' if setup.rr_ratio and setup.rr_ratio >= 1.5 else '#fbbf24'};">{setup.rr_ratio if setup.rr_ratio else 'N/A'}:1</span>
            </div>
        </div>
        
        {warnings_html}
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)

def render_trading_rules():
    """Render collapsible trading rules reference"""
    with st.expander("📖 Trading Rules Reference", expanded=False):
        st.markdown("""
        <div class="rules-section">
            <div class="rules-title">🎯 THE TWO PILLARS</div>
            
            <div class="rule-item">
                <strong>1. MA Bias → Direction</strong><br>
                • <span style="color: #22c55e;">BULLISH:</span> 50 EMA > 200 SMA AND Price > 50 EMA → LONG only<br>
                • <span style="color: #ef4444;">BEARISH:</span> 50 EMA < 200 SMA AND Price < 50 EMA → SHORT only<br>
                • <span style="color: #6b7280;">NEUTRAL:</span> Mixed signals → NO TRADE
            </div>
            
            <div class="rule-item">
                <strong>2. Day Structure → Entry/Exit Zones</strong><br>
                • High Line = Overnight Ceiling (5pm-7am high from TOS)<br>
                • Low Line = Overnight Floor (5pm-7am low from TOS)<br>
                • LONG: Enter at Floor, Exit at Ceiling<br>
                • SHORT: Enter at Ceiling, Exit at Floor
            </div>
            
            <div class="rules-title" style="margin-top: 20px;">⚠️ RISK MANAGEMENT</div>
            
            <div class="rule-item">
                • Stop Loss: 0.2% beyond entry line<br>
                • Minimum R:R Ratio: 1.5:1<br>
                • Optimal Entry Window: 9-10am ET<br>
                • Never trade against the MA Bias
            </div>
            
            <div class="rules-title" style="margin-top: 20px;">✅ TRADE EXECUTION</div>
            
            <div class="rule-item">
                • Wait for price to reach your entry zone<br>
                • Confirm with price action (rejection candle, volume)<br>
                • Set stop immediately upon entry<br>
                • Take profit at target or trail stop
            </div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# SIDEBAR INPUTS
# ============================================================================

def render_sidebar_inputs(symbol: str) -> dict:
    """Render sidebar inputs for a stock and return values"""
    st.sidebar.markdown(f"### {symbol}")
    
    # Initialize session state for this stock if not exists
    if f"{symbol}_data" not in st.session_state:
        st.session_state[f"{symbol}_data"] = {
            "use_polygon": True,
            "manual_price": 0.0,
            "manual_bias": "Neutral",
            "high_line": 0.0,
            "low_line": 0.0
        }
    
    data = st.session_state[f"{symbol}_data"]
    
    # Data source toggle
    use_polygon = st.sidebar.toggle(
        "Use Polygon Data",
        value=data["use_polygon"],
        key=f"{symbol}_polygon_toggle"
    )
    data["use_polygon"] = use_polygon
    
    # Manual price override
    if not use_polygon:
        manual_price = st.sidebar.number_input(
            "Current Price ($)",
            min_value=0.0,
            value=data["manual_price"],
            step=0.01,
            key=f"{symbol}_manual_price"
        )
        data["manual_price"] = manual_price
    
    # MA Bias (auto or manual)
    if not use_polygon:
        manual_bias = st.sidebar.selectbox(
            "MA Bias",
            options=["Bullish", "Bearish", "Neutral"],
            index=["Bullish", "Bearish", "Neutral"].index(data["manual_bias"]),
            key=f"{symbol}_manual_bias"
        )
        data["manual_bias"] = manual_bias
    
    # High Line (always manual - overnight ceiling)
    high_line = st.sidebar.number_input(
        "High Line (Ceiling) $",
        min_value=0.0,
        value=data["high_line"],
        step=0.01,
        key=f"{symbol}_high_line"
    )
    data["high_line"] = high_line
    
    # Low Line (always manual - overnight floor)
    low_line = st.sidebar.number_input(
        "Low Line (Floor) $",
        min_value=0.0,
        value=data["low_line"],
        step=0.01,
        key=f"{symbol}_low_line"
    )
    data["low_line"] = low_line
    
    st.sidebar.markdown("---")
    
    return data

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def fetch_all_stock_data(symbols: List[str]) -> Tuple[List[StockData], bool]:
    """Fetch data for all stocks"""
    stocks = []
    any_connected = False
    
    for symbol in symbols:
        # Get sidebar inputs
        inputs = st.session_state.get(f"{symbol}_data", {
            "use_polygon": True,
            "manual_price": 0.0,
            "manual_bias": "Neutral",
            "high_line": 0.0,
            "low_line": 0.0
        })
        
        stock = StockData(symbol=symbol)
        stock.use_polygon = inputs.get("use_polygon", True)
        stock.high_line = inputs.get("high_line") if inputs.get("high_line", 0) > 0 else None
        stock.low_line = inputs.get("low_line") if inputs.get("low_line", 0) > 0 else None
        
        if stock.use_polygon:
            # Fetch from Polygon
            price, connected = fetch_current_price(symbol)
            stock.current_price = price
            stock.polygon_connected = connected
            any_connected = any_connected or connected
            
            # Fetch previous day
            prev_high, prev_low, prev_close, _ = fetch_previous_day(symbol)
            stock.prev_high = prev_high
            stock.prev_low = prev_low
            stock.prev_close = prev_close
            
            # Fetch historical and calculate MAs
            df, _ = fetch_historical_bars(symbol)
            if df is not None:
                stock.ema_50, stock.sma_200 = calculate_moving_averages(df)
            
            # Determine MA Bias
            stock.ma_bias = determine_ma_bias(stock.current_price, stock.ema_50, stock.sma_200)
            
            stock.last_updated = datetime.now()
        else:
            # Use manual inputs
            stock.current_price = inputs.get("manual_price") if inputs.get("manual_price", 0) > 0 else None
            bias_str = inputs.get("manual_bias", "Neutral")
            stock.ma_bias = MABias(bias_str)
            stock.polygon_connected = False
        
        stocks.append(stock)
    
    return stocks, any_connected

def main():
    st.set_page_config(
        page_title="Stock Prophet",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    inject_styles()
    
    # Title
    st.markdown("""
    <h1 style="
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        margin-bottom: 10px;
    ">📈 STOCK PROPHET</h1>
    <p style="text-align: center; color: #94a3b8; margin-bottom: 30px;">
        Daily Trading Entries • MA Bias + Day Structure System
    </p>
    """, unsafe_allow_html=True)
    
    # Sidebar header
    st.sidebar.markdown("## 🎛️ Stock Inputs")
    st.sidebar.markdown("Set High/Low Lines from TOS overnight session (5pm-7am)")
    st.sidebar.markdown("---")
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh All Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Render sidebar inputs for each stock
    for symbol in STOCK_UNIVERSE:
        render_sidebar_inputs(symbol)
    
    # Fetch all stock data
    with st.spinner("Fetching market data..."):
        stocks, polygon_status = fetch_all_stock_data(STOCK_UNIVERSE)
    
    # Calculate trade setups
    setups = [calculate_trade_setup(stock) for stock in stocks]
    
    # Render top bar
    render_top_bar(stocks, setups, polygon_status)
    
    # Render stock cards in a grid
    col1, col2 = st.columns(2)
    
    for i, (stock, setup) in enumerate(zip(stocks, setups)):
        with col1 if i % 2 == 0 else col2:
            with st.expander(f"{stock.symbol} - {setup.direction.value}", expanded=True):
                render_stock_card(stock, setup)
    
    # Trading rules reference
    render_trading_rules()
    
    # Footer
    st.markdown("""
    <div style="text-align: center; margin-top: 40px; padding: 20px; color: #64748b; font-size: 0.8rem;">
        Stock Prophet v1.0 • Data from Polygon.io (15-min delayed) • Not financial advice
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
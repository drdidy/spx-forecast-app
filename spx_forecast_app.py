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
    high_line: Optional[float] = None
    low_line: Optional[float] = None
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

@st.cache_data(ttl=60)
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
                if "lastTrade" in ticker_data:
                    return ticker_data["lastTrade"].get("p"), True
                elif "day" in ticker_data:
                    return ticker_data["day"].get("c"), True
                elif "prevDay" in ticker_data:
                    return ticker_data["prevDay"].get("c"), True
        return None, False
    except Exception:
        return None, False

@st.cache_data(ttl=300)
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
    except Exception:
        return None, None, None, False

@st.cache_data(ttl=900)
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
    except Exception:
        return None, False

def calculate_moving_averages(df: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
    """Calculate 50 EMA and 200 SMA from historical data"""
    if df is None or len(df) < 200:
        return None, None
    
    try:
        df['ema_50'] = df['c'].ewm(span=50, adjust=False).mean()
        df['sma_200'] = df['c'].rolling(window=200).mean()
        ema_50 = df['ema_50'].iloc[-1]
        sma_200 = df['sma_200'].iloc[-1]
        return round(ema_50, 2), round(sma_200, 2)
    except Exception:
        return None, None

def determine_ma_bias(current_price: Optional[float], ema_50: Optional[float], sma_200: Optional[float]) -> MABias:
    """Determine MA Bias based on price relationship to MAs"""
    if None in (current_price, ema_50, sma_200):
        return MABias.NEUTRAL
    
    if ema_50 > sma_200 and current_price > ema_50:
        return MABias.BULLISH
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
    
    if stock.high_line is None or stock.low_line is None:
        setup.warnings.append("⚠️ Missing High Line or Low Line")
        return setup
    
    if stock.current_price is None:
        setup.warnings.append("⚠️ No current price available")
        return setup
    
    if stock.high_line <= stock.low_line:
        setup.warnings.append("⚠️ High Line must be greater than Low Line")
        return setup
    
    current_hour = datetime.now().hour
    if current_hour < 9 or current_hour > 10:
        setup.warnings.append(f"ℹ️ Optimal entry: 9-10am ET")
    
    if stock.ma_bias == MABias.BULLISH:
        setup.direction = TradeDirection.LONG
        setup.entry = stock.low_line
        setup.exit_target = stock.high_line
        setup.stop_loss = round(stock.low_line * (1 - STOP_BUFFER_PERCENT), 2)
        setup.is_valid = True
        
        if stock.current_price > stock.low_line * 1.02:
            setup.warnings.append("⚠️ Price above Floor - may have missed entry")
        
    elif stock.ma_bias == MABias.BEARISH:
        setup.direction = TradeDirection.SHORT
        setup.entry = stock.high_line
        setup.exit_target = stock.low_line
        setup.stop_loss = round(stock.high_line * (1 + STOP_BUFFER_PERCENT), 2)
        setup.is_valid = True
        
        if stock.current_price < stock.high_line * 0.98:
            setup.warnings.append("⚠️ Price below Ceiling - may have missed entry")
    else:
        setup.warnings.append("⚠️ Neutral bias - no clear trade direction")
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
                setup.warnings.append(f"⚠️ R:R ratio ({setup.rr_ratio}) below 1.5")
    
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
    
    /* Card styles */
    .stock-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        margin: 10px 0;
    }
    
    .long-card {
        box-shadow: 0 0 20px rgba(34, 197, 94, 0.3);
        border-color: rgba(34, 197, 94, 0.5);
    }
    
    .short-card {
        box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
        border-color: rgba(239, 68, 68, 0.5);
    }
    
    .neutral-card {
        box-shadow: 0 0 20px rgba(107, 114, 128, 0.2);
        border-color: rgba(107, 114, 128, 0.3);
    }
    
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

def format_price(price: Optional[float]) -> str:
    """Format price for display"""
    if price is None:
        return "N/A"
    return f"${price:,.2f}"

def render_stock_card(stock: StockData, setup: TradeSetup):
    """Render individual stock card using native Streamlit components"""
    
    # Determine card color based on trade direction
    if setup.direction == TradeDirection.LONG:
        card_class = "long-card"
        direction_color = "🟢"
        bg_color = "rgba(34, 197, 94, 0.1)"
    elif setup.direction == TradeDirection.SHORT:
        card_class = "short-card"
        direction_color = "🔴"
        bg_color = "rgba(239, 68, 68, 0.1)"
    else:
        card_class = "neutral-card"
        direction_color = "⚪"
        bg_color = "rgba(107, 114, 128, 0.1)"
    
    # Status indicator
    if stock.use_polygon:
        status = "🟢 Polygon" if stock.polygon_connected else "🔴 Offline"
    else:
        status = "📝 Manual"
    
    # Card container
    st.markdown(f'<div class="stock-card {card_class}">', unsafe_allow_html=True)
    
    # Header row
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown(f"### {stock.symbol} {direction_color}")
    with col2:
        st.markdown(f"### {format_price(stock.current_price)}")
    with col3:
        st.caption(status)
    
    # MA Bias section
    bias_colors = {
        MABias.BULLISH: "🟢 BULLISH",
        MABias.BEARISH: "🔴 BEARISH", 
        MABias.NEUTRAL: "⚪ NEUTRAL"
    }
    
    st.markdown(f"**MA Bias:** {bias_colors[stock.ma_bias]}")
    
    if stock.ema_50 and stock.sma_200:
        st.caption(f"50 EMA: ${stock.ema_50:.2f} | 200 SMA: ${stock.sma_200:.2f}")
    
    st.divider()
    
    # Day Structure
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🔺 Ceiling (High Line)", format_price(stock.high_line))
    with col2:
        st.metric("🔻 Floor (Low Line)", format_price(stock.low_line))
    
    st.divider()
    
    # Trade Setup
    st.markdown(f"### 🎯 YOUR TRADE: **{setup.direction.value}**")
    
    if setup.is_valid:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Entry", format_price(setup.entry))
        with col2:
            st.metric("Target", format_price(setup.exit_target), delta="Exit")
        with col3:
            st.metric("Stop Loss", format_price(setup.stop_loss), delta="Risk", delta_color="inverse")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Reward", f"{setup.reward} pts" if setup.reward else "N/A")
        with col2:
            st.metric("Risk", f"{setup.risk} pts" if setup.risk else "N/A")
        with col3:
            rr_color = "normal" if setup.rr_ratio and setup.rr_ratio >= 1.5 else "off"
            st.metric("R:R Ratio", f"{setup.rr_ratio}:1" if setup.rr_ratio else "N/A")
    
    # Warnings
    if setup.warnings:
        st.markdown("---")
        for warning in setup.warnings:
            st.warning(warning)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_top_bar(stocks: List[StockData], setups: List[TradeSetup], polygon_status: bool):
    """Render top summary bar"""
    long_count = sum(1 for s in setups if s.direction == TradeDirection.LONG)
    short_count = sum(1 for s in setups if s.direction == TradeDirection.SHORT)
    no_trade_count = sum(1 for s in setups if s.direction == TradeDirection.NO_TRADE)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_text = "🟢 Connected (15-min delay)" if polygon_status else "🔴 Disconnected"
        st.markdown(f"**Polygon:** {status_text}")
    
    with col2:
        st.markdown(f"**📈 LONG:** {long_count}")
    
    with col3:
        st.markdown(f"**📉 SHORT:** {short_count}")
    
    with col4:
        st.markdown(f"**⏸️ NO TRADE:** {no_trade_count}")
    
    st.divider()

def render_trading_rules():
    """Render collapsible trading rules reference"""
    with st.expander("📖 Trading Rules Reference", expanded=False):
        st.markdown("""
        ### 🎯 THE TWO PILLARS
        
        **1. MA Bias → Direction (50 EMA vs 200 SMA on daily chart)**
        - 🟢 **BULLISH:** 50 EMA > 200 SMA AND Price > 50 EMA → LONG only
        - 🔴 **BEARISH:** 50 EMA < 200 SMA AND Price < 50 EMA → SHORT only
        - ⚪ **NEUTRAL:** Mixed signals → NO TRADE
        
        **2. Day Structure → Entry/Exit Zones**
        - **High Line** = Overnight Ceiling (5pm-7am high from TOS)
        - **Low Line** = Overnight Floor (5pm-7am low from TOS)
        - LONG: Enter at Floor, Exit at Ceiling
        - SHORT: Enter at Ceiling, Exit at Floor
        
        ---
        
        ### ⚠️ RISK MANAGEMENT
        - Stop Loss: 0.2% beyond entry line
        - Minimum R:R Ratio: 1.5:1
        - Optimal Entry Window: 9-10am ET
        - Never trade against the MA Bias
        
        ---
        
        ### ✅ TRADE EXECUTION
        1. Wait for price to reach your entry zone
        2. Confirm with price action (rejection candle, volume)
        3. Set stop immediately upon entry
        4. Take profit at target or trail stop
        """)

def render_sidebar_inputs(symbol: str) -> dict:
    """Render sidebar inputs for a stock"""
    st.sidebar.markdown(f"### {symbol}")
    
    # Initialize session state
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
    
    # Manual overrides
    if not use_polygon:
        manual_price = st.sidebar.number_input(
            "Current Price ($)",
            min_value=0.0,
            value=data["manual_price"],
            step=0.01,
            key=f"{symbol}_manual_price"
        )
        data["manual_price"] = manual_price
        
        manual_bias = st.sidebar.selectbox(
            "MA Bias",
            options=["Bullish", "Bearish", "Neutral"],
            index=["Bullish", "Bearish", "Neutral"].index(data["manual_bias"]),
            key=f"{symbol}_manual_bias"
        )
        data["manual_bias"] = manual_bias
    
    # High/Low Lines (always manual)
    high_line = st.sidebar.number_input(
        "High Line (Ceiling) $",
        min_value=0.0,
        value=data["high_line"],
        step=0.01,
        key=f"{symbol}_high_line"
    )
    data["high_line"] = high_line
    
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
            price, connected = fetch_current_price(symbol)
            stock.current_price = price
            stock.polygon_connected = connected
            any_connected = any_connected or connected
            
            prev_high, prev_low, prev_close, _ = fetch_previous_day(symbol)
            stock.prev_high = prev_high
            stock.prev_low = prev_low
            stock.prev_close = prev_close
            
            df, _ = fetch_historical_bars(symbol)
            if df is not None:
                stock.ema_50, stock.sma_200 = calculate_moving_averages(df)
            
            stock.ma_bias = determine_ma_bias(stock.current_price, stock.ema_50, stock.sma_200)
            stock.last_updated = datetime.now()
        else:
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
    st.title("📈 STOCK PROPHET")
    st.caption("Daily Trading Entries • MA Bias + Day Structure System")
    
    # Sidebar
    st.sidebar.markdown("## 🎛️ Stock Inputs")
    st.sidebar.caption("Set High/Low Lines from TOS overnight session (5pm-7am)")
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🔄 Refresh All Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Render sidebar inputs
    for symbol in STOCK_UNIVERSE:
        render_sidebar_inputs(symbol)
    
    # Fetch data
    with st.spinner("Fetching market data..."):
        stocks, polygon_status = fetch_all_stock_data(STOCK_UNIVERSE)
    
    # Calculate setups
    setups = [calculate_trade_setup(stock) for stock in stocks]
    
    # Top bar
    render_top_bar(stocks, setups, polygon_status)
    
    # Stock cards in grid
    col1, col2 = st.columns(2)
    
    for i, (stock, setup) in enumerate(zip(stocks, setups)):
        with col1 if i % 2 == 0 else col2:
            with st.expander(f"**{stock.symbol}** - {setup.direction.value}", expanded=True):
                render_stock_card(stock, setup)
    
    # Trading rules
    render_trading_rules()
    
    # Footer
    st.markdown("---")
    st.caption("Stock Prophet v1.0 • Data from Polygon.io (15-min delayed) • Not financial advice")

if __name__ == "__main__":
    main()
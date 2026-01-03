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

STOCK_UNIVERSE = ["AAPL", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "MSFT", "AMD", "SPY", "QQQ"]
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
    if df is None or len(df) < 200:
        return None, None
    try:
        df['ema_50'] = df['c'].ewm(span=50, adjust=False).mean()
        df['sma_200'] = df['c'].rolling(window=200).mean()
        return round(df['ema_50'].iloc[-1], 2), round(df['sma_200'].iloc[-1], 2)
    except Exception:
        return None, None

def determine_ma_bias(current_price: Optional[float], ema_50: Optional[float], sma_200: Optional[float]) -> MABias:
    if None in (current_price, ema_50, sma_200):
        return MABias.NEUTRAL
    if ema_50 > sma_200 and current_price > ema_50:
        return MABias.BULLISH
    elif ema_50 < sma_200 and current_price < ema_50:
        return MABias.BEARISH
    return MABias.NEUTRAL

# ============================================================================
# TRADE LOGIC
# ============================================================================

def calculate_trade_setup(stock: StockData) -> TradeSetup:
    setup = TradeSetup(direction=TradeDirection.NO_TRADE)
    
    if stock.high_line is None or stock.low_line is None:
        setup.warnings.append("Missing High Line or Low Line")
        return setup
    
    if stock.current_price is None:
        setup.warnings.append("No current price available")
        return setup
    
    if stock.high_line <= stock.low_line:
        setup.warnings.append("High Line must be greater than Low Line")
        return setup
    
    current_hour = datetime.now().hour
    if current_hour < 9 or current_hour > 10:
        setup.warnings.append("Optimal entry: 9-10am ET")
    
    if stock.ma_bias == MABias.BULLISH:
        setup.direction = TradeDirection.LONG
        setup.entry = stock.low_line
        setup.exit_target = stock.high_line
        setup.stop_loss = round(stock.low_line * (1 - STOP_BUFFER_PERCENT), 2)
        setup.is_valid = True
        if stock.current_price > stock.low_line * 1.02:
            setup.warnings.append("Price above Floor - may have missed entry")
        
    elif stock.ma_bias == MABias.BEARISH:
        setup.direction = TradeDirection.SHORT
        setup.entry = stock.high_line
        setup.exit_target = stock.low_line
        setup.stop_loss = round(stock.high_line * (1 + STOP_BUFFER_PERCENT), 2)
        setup.is_valid = True
        if stock.current_price < stock.high_line * 0.98:
            setup.warnings.append("Price below Ceiling - may have missed entry")
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
                setup.warnings.append(f"R:R ratio ({setup.rr_ratio}) below 1.5")
    
    return setup

# ============================================================================
# UI FUNCTIONS
# ============================================================================

def format_price(price: Optional[float]) -> str:
    if price is None:
        return "N/A"
    return f"${price:,.2f}"

def render_stock_card(stock: StockData, setup: TradeSetup):
    """Render stock card using only native Streamlit components"""
    
    # Header with symbol and price
    col1, col2 = st.columns([2, 2])
    with col1:
        if setup.direction == TradeDirection.LONG:
            st.subheader(f"🟢 {stock.symbol}")
        elif setup.direction == TradeDirection.SHORT:
            st.subheader(f"🔴 {stock.symbol}")
        else:
            st.subheader(f"⚪ {stock.symbol}")
    
    with col2:
        price_str = format_price(stock.current_price)
        if stock.use_polygon:
            status = "Polygon" if stock.polygon_connected else "Offline"
        else:
            status = "Manual"
        st.subheader(f"{price_str}")
        st.caption(status)
    
    # MA Bias
    if stock.ma_bias == MABias.BULLISH:
        st.success(f"MA Bias: BULLISH")
    elif stock.ma_bias == MABias.BEARISH:
        st.error(f"MA Bias: BEARISH")
    else:
        st.info(f"MA Bias: NEUTRAL")
    
    if stock.ema_50 and stock.sma_200:
        st.caption(f"50 EMA: ${stock.ema_50:.2f} | 200 SMA: ${stock.sma_200:.2f}")
    
    # Day Structure
    st.write("**Day Structure:**")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Ceiling (High Line)", format_price(stock.high_line))
    with col2:
        st.metric("Floor (Low Line)", format_price(stock.low_line))
    
    # Trade Setup
    st.write("---")
    if setup.direction == TradeDirection.LONG:
        st.success(f"**YOUR TRADE: {setup.direction.value}**")
    elif setup.direction == TradeDirection.SHORT:
        st.error(f"**YOUR TRADE: {setup.direction.value}**")
    else:
        st.info(f"**YOUR TRADE: {setup.direction.value}**")
    
    if setup.is_valid:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Entry", format_price(setup.entry))
        with col2:
            st.metric("Target", format_price(setup.exit_target))
        with col3:
            st.metric("Stop Loss", format_price(setup.stop_loss))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            reward_str = f"{setup.reward} pts" if setup.reward else "N/A"
            st.metric("Reward", reward_str)
        with col2:
            risk_str = f"{setup.risk} pts" if setup.risk else "N/A"
            st.metric("Risk", risk_str)
        with col3:
            rr_str = f"{setup.rr_ratio}:1" if setup.rr_ratio else "N/A"
            st.metric("R:R Ratio", rr_str)
    
    # Warnings
    for warning in setup.warnings:
        st.warning(warning)

def render_sidebar_inputs(symbol: str) -> dict:
    """Render sidebar inputs for a stock"""
    st.sidebar.write(f"**{symbol}**")
    
    if f"{symbol}_data" not in st.session_state:
        st.session_state[f"{symbol}_data"] = {
            "use_polygon": True,
            "manual_price": 0.0,
            "manual_bias": "Neutral",
            "high_line": 0.0,
            "low_line": 0.0
        }
    
    data = st.session_state[f"{symbol}_data"]
    
    use_polygon = st.sidebar.toggle(
        "Use Polygon",
        value=data["use_polygon"],
        key=f"{symbol}_polygon_toggle"
    )
    data["use_polygon"] = use_polygon
    
    if not use_polygon:
        data["manual_price"] = st.sidebar.number_input(
            "Price ($)",
            min_value=0.0,
            value=data["manual_price"],
            step=0.01,
            key=f"{symbol}_manual_price"
        )
        
        data["manual_bias"] = st.sidebar.selectbox(
            "MA Bias",
            options=["Bullish", "Bearish", "Neutral"],
            index=["Bullish", "Bearish", "Neutral"].index(data["manual_bias"]),
            key=f"{symbol}_manual_bias"
        )
    
    data["high_line"] = st.sidebar.number_input(
        "High Line $",
        min_value=0.0,
        value=data["high_line"],
        step=0.01,
        key=f"{symbol}_high_line"
    )
    
    data["low_line"] = st.sidebar.number_input(
        "Low Line $",
        min_value=0.0,
        value=data["low_line"],
        step=0.01,
        key=f"{symbol}_low_line"
    )
    
    st.sidebar.write("---")
    return data

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
            stock.ma_bias = MABias(inputs.get("manual_bias", "Neutral"))
            stock.polygon_connected = False
        
        stocks.append(stock)
    
    return stocks, any_connected

# ============================================================================
# MAIN
# ============================================================================

def main():
    st.set_page_config(
        page_title="Stock Prophet",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Title
    st.title("📈 STOCK PROPHET")
    st.caption("Daily Trading Entries • MA Bias + Day Structure System")
    
    # Sidebar
    st.sidebar.title("Stock Inputs")
    st.sidebar.caption("Set High/Low Lines from TOS overnight session (5pm-7am)")
    
    if st.sidebar.button("🔄 Refresh All", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.write("---")
    
    for symbol in STOCK_UNIVERSE:
        render_sidebar_inputs(symbol)
    
    # Fetch data
    with st.spinner("Fetching market data..."):
        stocks, polygon_status = fetch_all_stock_data(STOCK_UNIVERSE)
    
    setups = [calculate_trade_setup(stock) for stock in stocks]
    
    # Summary bar
    long_count = sum(1 for s in setups if s.direction == TradeDirection.LONG)
    short_count = sum(1 for s in setups if s.direction == TradeDirection.SHORT)
    no_trade_count = sum(1 for s in setups if s.direction == TradeDirection.NO_TRADE)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status = "🟢 Connected" if polygon_status else "🔴 Disconnected"
        st.write(f"**Polygon:** {status}")
    with col2:
        st.write(f"**📈 LONG:** {long_count}")
    with col3:
        st.write(f"**📉 SHORT:** {short_count}")
    with col4:
        st.write(f"**⏸️ NO TRADE:** {no_trade_count}")
    
    st.write("---")
    
    # Stock cards
    col1, col2 = st.columns(2)
    
    for i, (stock, setup) in enumerate(zip(stocks, setups)):
        with col1 if i % 2 == 0 else col2:
            with st.expander(f"{stock.symbol} - {setup.direction.value}", expanded=True):
                render_stock_card(stock, setup)
    
    # Trading rules
    with st.expander("📖 Trading Rules Reference"):
        st.write("""
        ### THE TWO PILLARS
        
        **1. MA Bias → Direction**
        - BULLISH: 50 EMA > 200 SMA AND Price > 50 EMA → LONG only
        - BEARISH: 50 EMA < 200 SMA AND Price < 50 EMA → SHORT only
        - NEUTRAL: Mixed signals → NO TRADE
        
        **2. Day Structure → Entry/Exit**
        - High Line = Overnight Ceiling (5pm-7am high)
        - Low Line = Overnight Floor (5pm-7am low)
        - LONG: Enter at Floor, Exit at Ceiling
        - SHORT: Enter at Ceiling, Exit at Floor
        
        ### RISK MANAGEMENT
        - Stop Loss: 0.2% beyond entry line
        - Minimum R:R Ratio: 1.5:1
        - Optimal Entry: 9-10am ET
        """)
    
    st.write("---")
    st.caption("Stock Prophet v1.0 • Data from Polygon.io (15-min delayed) • Not financial advice")

if __name__ == "__main__":
    main()
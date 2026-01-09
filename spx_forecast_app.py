import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import pytz

# Page configuration
st.set_page_config(
    page_title="Overnight Structure & NY Session Projector",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for glassmorphism and professional styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3a 50%, #0a0a1a 100%);
    }
    
    .main-header {
        background: linear-gradient(135deg, rgba(30, 30, 60, 0.8), rgba(60, 30, 90, 0.6));
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 25px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    .main-header h1 {
        color: #ffffff;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2.2rem;
        margin: 0;
        text-shadow: 0 0 30px rgba(100, 150, 255, 0.5);
    }
    
    .main-header p {
        color: rgba(255, 255, 255, 0.7);
        font-family: 'Inter', sans-serif;
        margin-top: 10px;
    }
    
    .glass-card {
        background: linear-gradient(135deg, rgba(40, 40, 80, 0.6), rgba(20, 20, 50, 0.8));
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    
    .projection-card {
        background: linear-gradient(135deg, rgba(0, 100, 150, 0.4), rgba(0, 50, 100, 0.6));
        backdrop-filter: blur(20px);
        border: 1px solid rgba(0, 200, 255, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 8px 32px rgba(0, 150, 255, 0.1);
    }
    
    .bullish-card {
        background: linear-gradient(135deg, rgba(0, 150, 100, 0.4), rgba(0, 100, 50, 0.6));
        border: 1px solid rgba(0, 255, 150, 0.2);
    }
    
    .bearish-card {
        background: linear-gradient(135deg, rgba(150, 50, 50, 0.4), rgba(100, 30, 30, 0.6));
        border: 1px solid rgba(255, 100, 100, 0.2);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #00d4ff;
        font-family: 'Inter', sans-serif;
    }
    
    .metric-label {
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.9rem;
        font-family: 'Inter', sans-serif;
    }
    
    .strike-price {
        font-size: 1.5rem;
        font-weight: 600;
        color: #ffd700;
        font-family: 'Inter', sans-serif;
    }
    
    .time-badge {
        display: inline-block;
        background: rgba(100, 150, 255, 0.3);
        padding: 5px 15px;
        border-radius: 20px;
        color: #ffffff;
        font-weight: 500;
        margin: 5px;
    }
    
    .stSelectbox > div > div {
        background: rgba(40, 40, 80, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    
    .stNumberInput > div > div > input {
        background: rgba(40, 40, 80, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: white;
    }
    
    .stTimeInput > div > div > input {
        background: rgba(40, 40, 80, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: white;
    }
    
    div[data-testid="stMetric"] {
        background: rgba(40, 40, 80, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 15px;
    }
    
    div[data-testid="stMetric"] label {
        color: rgba(255, 255, 255, 0.7) !important;
    }
    
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #00d4ff !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #4a90d9, #357abd);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 25px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #5aa0e9, #4a90d9);
        box-shadow: 0 5px 20px rgba(74, 144, 217, 0.4);
    }
    
    .session-header {
        color: #00d4ff;
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid rgba(0, 212, 255, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Polygon API Key
POLYGON_API_KEY = "fTpxPfqJpFgONsxaAPPQ0I8xZlqKS_SC"

# Stock list
STOCKS = {
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
    "AAPL": "Apple",
    "GOOGL": "Alphabet (GOOGL)",
    "GOOG": "Alphabet (GOOG)",
    "AMZN": "Amazon",
    "META": "Meta Platforms",
    "AVGO": "Broadcom",
    "TSLA": "Tesla",
    "BRK.B": "Berkshire Hathaway",
    "JPM": "JPMorgan Chase",
    "V": "Visa",
    "UNH": "UnitedHealth Group"
}

# Session times (in Eastern Time)
SESSIONS = {
    "Asia": {"start": "19:00", "end": "03:00"},  # 7 PM - 3 AM ET
    "London": {"start": "03:00", "end": "09:00"},  # 3 AM - 9 AM ET
    "New York": {"start": "09:00", "end": "16:00"}  # 9 AM - 4 PM ET
}

# NY projection times
NY_PROJECTION_TIMES = ["09:00", "09:30", "10:00"]


def get_current_price(symbol: str) -> dict:
    """Fetch current price from Polygon"""
    try:
        # Handle BRK.B special case
        api_symbol = symbol.replace(".", "")
        
        url = f"https://api.polygon.io/v2/aggs/ticker/{api_symbol}/prev"
        params = {"apiKey": POLYGON_API_KEY}
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            return {
                "symbol": symbol,
                "close": result.get("c"),
                "high": result.get("h"),
                "low": result.get("l"),
                "open": result.get("o"),
                "volume": result.get("v"),
                "timestamp": datetime.fromtimestamp(result.get("t") / 1000).strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Try snapshot endpoint as fallback
        url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{api_symbol}"
        params = {"apiKey": POLYGON_API_KEY}
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("status") == "OK" and data.get("ticker"):
            ticker = data["ticker"]
            day = ticker.get("day", {})
            return {
                "symbol": symbol,
                "close": day.get("c") or ticker.get("lastTrade", {}).get("p"),
                "high": day.get("h"),
                "low": day.get("l"),
                "open": day.get("o"),
                "volume": day.get("v"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        return None
    except Exception as e:
        st.error(f"Error fetching price: {e}")
        return None


def time_to_blocks(time_str: str, base_time: str = "00:00") -> float:
    """Convert time to 30-minute blocks from base time"""
    t = datetime.strptime(time_str, "%H:%M")
    base = datetime.strptime(base_time, "%H:%M")
    
    # Handle overnight (if time is before base, add 24 hours)
    if t < base:
        t += timedelta(days=1)
    
    diff = (t - base).total_seconds() / 60  # minutes
    return diff / 30  # 30-minute blocks


def calculate_slope(price1: float, time1: str, price2: float, time2: str) -> float:
    """Calculate slope between two points (price change per 30-min block)"""
    blocks = time_to_blocks(time2, time1)
    if blocks == 0:
        return 0
    return (price2 - price1) / blocks


def project_price(start_price: float, start_time: str, target_time: str, slope: float) -> float:
    """Project price at target time based on slope"""
    blocks = time_to_blocks(target_time, start_time)
    return start_price + (slope * blocks)


def get_closest_otm_strikes(current_price: float, direction: str, num_strikes: int = 3) -> list:
    """Get closest OTM strike prices"""
    # Standard strike intervals based on price
    if current_price < 50:
        interval = 1
    elif current_price < 100:
        interval = 2.5
    elif current_price < 200:
        interval = 5
    elif current_price < 500:
        interval = 5
    else:
        interval = 10
    
    strikes = []
    
    if direction == "CALL":  # Bullish - OTM calls are above current price
        base_strike = np.ceil(current_price / interval) * interval
        for i in range(num_strikes):
            strikes.append(base_strike + (i * interval))
    else:  # PUT - Bearish - OTM puts are below current price
        base_strike = np.floor(current_price / interval) * interval
        for i in range(num_strikes):
            strikes.append(base_strike - (i * interval))
    
    return strikes


def determine_closest_session(asia_time: str, london_time: str) -> str:
    """Determine which session's low/high we're closer to for NY projection"""
    # Convert times to comparable format
    asia_t = datetime.strptime(asia_time, "%H:%M")
    london_t = datetime.strptime(london_time, "%H:%M")
    ny_open = datetime.strptime("09:00", "%H:%M")
    
    # Handle overnight
    if asia_t > ny_open:
        asia_t -= timedelta(days=1)
    if london_t > ny_open:
        london_t -= timedelta(days=1)
    
    # Calculate time difference to NY open
    asia_diff = abs((ny_open - asia_t).total_seconds())
    london_diff = abs((ny_open - london_t).total_seconds())
    
    return "London" if london_diff < asia_diff else "Asia"


# Main App
st.markdown("""
<div class="main-header">
    <h1>🌙 Overnight Structure & NY Session Projector</h1>
    <p>Project NY Session entries from Asia & London session structures on 30-minute charts</p>
</div>
""", unsafe_allow_html=True)

# Sidebar - Stock Selection
with st.sidebar:
    st.markdown("### 📊 Stock Selection")
    selected_symbol = st.selectbox(
        "Select Stock",
        options=list(STOCKS.keys()),
        format_func=lambda x: f"{x} - {STOCKS[x]}"
    )
    
    st.markdown("---")
    
    # Fetch current price
    if st.button("🔄 Refresh Current Price", use_container_width=True):
        st.session_state.refresh_price = True
    
    price_data = get_current_price(selected_symbol)
    
    if price_data:
        st.markdown("### 💰 Current Price Data")
        st.metric("Last Close", f"${price_data['close']:.2f}")
        if price_data.get('high'):
            st.metric("Day High", f"${price_data['high']:.2f}")
        if price_data.get('low'):
            st.metric("Day Low", f"${price_data['low']:.2f}")
        st.caption(f"📅 {price_data['timestamp']}")
    
    st.markdown("---")
    st.markdown("### ⏰ Session Times (ET)")
    st.markdown("""
    <div class="glass-card">
        <strong>🌏 Asia:</strong> 7:00 PM - 3:00 AM<br>
        <strong>🇬🇧 London:</strong> 3:00 AM - 9:00 AM<br>
        <strong>🗽 New York:</strong> 9:00 AM - 4:00 PM
    </div>
    """, unsafe_allow_html=True)

# Main content area
current_price = price_data['close'] if price_data else 0

col1, col2 = st.columns(2)

# BULLISH SETUP - Low to Low Trendline
with col1:
    st.markdown("""
    <div class="bullish-card">
        <div class="session-header">📈 BULLISH SETUP (Low-to-Low Trendline)</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("🌏 Asia Session LOW", expanded=True):
        asia_low = st.number_input(
            "Asia Session Low Price",
            min_value=0.0,
            value=current_price * 0.99 if current_price else 100.0,
            step=0.01,
            key="asia_low"
        )
        asia_low_time = st.time_input(
            "Time of Asia Low (ET)",
            value=time(22, 0),
            key="asia_low_time"
        )
    
    with st.expander("🇬🇧 London Session LOW", expanded=True):
        london_low = st.number_input(
            "London Session Low Price",
            min_value=0.0,
            value=current_price * 0.995 if current_price else 100.0,
            step=0.01,
            key="london_low"
        )
        london_low_time = st.time_input(
            "Time of London Low (ET)",
            value=time(5, 30),
            key="london_low_time"
        )

# BEARISH SETUP - High to High Trendline
with col2:
    st.markdown("""
    <div class="bearish-card">
        <div class="session-header">📉 BEARISH SETUP (High-to-High Trendline)</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("🌏 Asia Session HIGH", expanded=True):
        asia_high = st.number_input(
            "Asia Session High Price",
            min_value=0.0,
            value=current_price * 1.01 if current_price else 105.0,
            step=0.01,
            key="asia_high"
        )
        asia_high_time = st.time_input(
            "Time of Asia High (ET)",
            value=time(21, 0),
            key="asia_high_time"
        )
    
    with st.expander("🇬🇧 London Session HIGH", expanded=True):
        london_high = st.number_input(
            "London Session High Price",
            min_value=0.0,
            value=current_price * 1.005 if current_price else 105.0,
            step=0.01,
            key="london_high"
        )
        london_high_time = st.time_input(
            "Time of London High (ET)",
            value=time(6, 0),
            key="london_high_time"
        )

st.markdown("---")

# Calculate Projections Button
if st.button("🎯 CALCULATE NY SESSION PROJECTIONS", use_container_width=True, type="primary"):
    
    st.markdown("## 🗽 New York Session Projections")
    
    # Format times
    asia_low_time_str = asia_low_time.strftime("%H:%M")
    london_low_time_str = london_low_time.strftime("%H:%M")
    asia_high_time_str = asia_high_time.strftime("%H:%M")
    london_high_time_str = london_high_time.strftime("%H:%M")
    
    # Determine which session is closer for each setup
    bullish_anchor = determine_closest_session(asia_low_time_str, london_low_time_str)
    bearish_anchor = determine_closest_session(asia_high_time_str, london_high_time_str)
    
    # Calculate slopes
    bullish_slope = calculate_slope(asia_low, asia_low_time_str, london_low, london_low_time_str)
    bearish_slope = calculate_slope(asia_high, asia_high_time_str, london_high, london_high_time_str)
    
    col_bull, col_bear = st.columns(2)
    
    # BULLISH PROJECTIONS
    with col_bull:
        st.markdown("""
        <div class="bullish-card">
            <div class="session-header">📈 BULLISH (Support Trendline)</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.info(f"📍 Anchor Session: **{bullish_anchor}** (closer to NY open)")
        st.metric("Trendline Slope", f"{bullish_slope:.4f} per 30-min block")
        
        # Use the closer session as anchor
        if bullish_anchor == "London":
            anchor_price = london_low
            anchor_time = london_low_time_str
        else:
            anchor_price = asia_low
            anchor_time = asia_low_time_str
        
        st.markdown("### 🎯 Entry Levels (Support)")
        
        projections_bullish = []
        for ny_time in NY_PROJECTION_TIMES:
            projected = project_price(anchor_price, anchor_time, ny_time, bullish_slope)
            projections_bullish.append({"time": ny_time, "price": projected})
            
            time_label = datetime.strptime(ny_time, "%H:%M").strftime("%I:%M %p")
            st.markdown(f"""
            <div class="projection-card bullish-card">
                <span class="time-badge">{time_label} ET</span>
                <div class="metric-value">${projected:.2f}</div>
                <div class="metric-label">Support / Entry Level</div>
            </div>
            """, unsafe_allow_html=True)
        
        # OTM Calls
        st.markdown("### 📞 Closest OTM CALL Strikes")
        avg_entry = np.mean([p['price'] for p in projections_bullish])
        call_strikes = get_closest_otm_strikes(avg_entry, "CALL")
        
        for i, strike in enumerate(call_strikes):
            st.markdown(f"""
            <div class="glass-card">
                <span class="strike-price">${strike:.2f} CALL</span>
                <span style="color: rgba(255,255,255,0.5); margin-left: 10px;">{'1st OTM' if i==0 else f'{i+1}nd OTM' if i==1 else f'{i+1}rd OTM'}</span>
            </div>
            """, unsafe_allow_html=True)
    
    # BEARISH PROJECTIONS
    with col_bear:
        st.markdown("""
        <div class="bearish-card">
            <div class="session-header">📉 BEARISH (Resistance Trendline)</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.info(f"📍 Anchor Session: **{bearish_anchor}** (closer to NY open)")
        st.metric("Trendline Slope", f"{bearish_slope:.4f} per 30-min block")
        
        # Use the closer session as anchor
        if bearish_anchor == "London":
            anchor_price = london_high
            anchor_time = london_high_time_str
        else:
            anchor_price = asia_high
            anchor_time = asia_high_time_str
        
        st.markdown("### 🎯 Entry Levels (Resistance)")
        
        projections_bearish = []
        for ny_time in NY_PROJECTION_TIMES:
            projected = project_price(anchor_price, anchor_time, ny_time, bearish_slope)
            projections_bearish.append({"time": ny_time, "price": projected})
            
            time_label = datetime.strptime(ny_time, "%H:%M").strftime("%I:%M %p")
            st.markdown(f"""
            <div class="projection-card bearish-card">
                <span class="time-badge">{time_label} ET</span>
                <div class="metric-value">${projected:.2f}</div>
                <div class="metric-label">Resistance / Entry Level</div>
            </div>
            """, unsafe_allow_html=True)
        
        # OTM Puts
        st.markdown("### 📉 Closest OTM PUT Strikes")
        avg_entry = np.mean([p['price'] for p in projections_bearish])
        put_strikes = get_closest_otm_strikes(avg_entry, "PUT")
        
        for i, strike in enumerate(put_strikes):
            st.markdown(f"""
            <div class="glass-card">
                <span class="strike-price">${strike:.2f} PUT</span>
                <span style="color: rgba(255,255,255,0.5); margin-left: 10px;">{'1st OTM' if i==0 else f'{i+1}nd OTM' if i==1 else f'{i+1}rd OTM'}</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Summary Table
    st.markdown("---")
    st.markdown("## 📊 Summary Table")
    
    summary_data = []
    for i, ny_time in enumerate(NY_PROJECTION_TIMES):
        time_label = datetime.strptime(ny_time, "%H:%M").strftime("%I:%M %p")
        summary_data.append({
            "NY Time": time_label,
            "Bullish Entry (Support)": f"${projections_bullish[i]['price']:.2f}",
            "Bearish Entry (Resistance)": f"${projections_bearish[i]['price']:.2f}",
            "Range": f"${abs(projections_bearish[i]['price'] - projections_bullish[i]['price']):.2f}"
        })
    
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    # Strike recommendations
    st.markdown("### 💡 Strike Recommendations")
    rec_col1, rec_col2 = st.columns(2)
    
    with rec_col1:
        st.success(f"""
        **BULLISH PLAY**
        - Entry Zone: ${projections_bullish[0]['price']:.2f} - ${projections_bullish[-1]['price']:.2f}
        - Recommended Strike: **${call_strikes[0]:.2f} CALL**
        - Alternative: ${call_strikes[1]:.2f} CALL (cheaper premium)
        """)
    
    with rec_col2:
        st.error(f"""
        **BEARISH PLAY**
        - Entry Zone: ${projections_bearish[0]['price']:.2f} - ${projections_bearish[-1]['price']:.2f}
        - Recommended Strike: **${put_strikes[0]:.2f} PUT**
        - Alternative: ${put_strikes[1]:.2f} PUT (cheaper premium)
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: rgba(255,255,255,0.5); padding: 20px;">
    <p>🌙 Overnight Structure Projector | Built for 30-Minute Chart Analysis</p>
    <p style="font-size: 0.8rem;">Projections based on trendline extrapolation from Asia/London session highs and lows</p>
</div>
""", unsafe_allow_html=True)

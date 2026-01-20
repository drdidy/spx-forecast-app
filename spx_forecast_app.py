import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="ES Real-Time Data", page_icon="📈", layout="wide")

# Initialize session state
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# Header
st.title("📈 ES Futures - Real-Time Data")

# Sidebar controls
st.sidebar.header("Settings")

ticker = st.sidebar.selectbox(
    "Ticker",
    options=["ES=F", "NQ=F", "YM=F", "RTY=F", "SPY", "QQQ"],
    index=0,
    help="ES=F: E-mini S&P 500, NQ=F: E-mini Nasdaq, YM=F: E-mini Dow, RTY=F: E-mini Russell"
)

refresh_interval = st.sidebar.selectbox(
    "Refresh Interval",
    options=[5, 10, 15, 30, 60],
    index=1,
    format_func=lambda x: f"{x} seconds"
)

auto_refresh = st.sidebar.toggle("Auto Refresh", value=st.session_state.auto_refresh)
st.session_state.auto_refresh = auto_refresh

# Manual refresh button
if st.sidebar.button("🔄 Refresh Now", type="primary"):
    st.rerun()


def fetch_realtime_data(symbol):
    """Fetch real-time data using yfinance"""
    try:
        ticker_obj = yf.Ticker(symbol)
        
        # Get real-time quote info
        info = ticker_obj.fast_info
        
        # Get intraday data (1-minute intervals for today)
        intraday = ticker_obj.history(period="1d", interval="1m")
        
        # Get 5-day data for context
        daily = ticker_obj.history(period="5d", interval="5m")
        
        return {
            'info': info,
            'intraday': intraday,
            'daily': daily,
            'ticker': ticker_obj
        }
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None


def format_change(current, previous):
    """Format price change with color"""
    if previous == 0:
        return 0, "0.00%"
    change = current - previous
    pct_change = (change / previous) * 100
    return change, f"{pct_change:+.2f}%"


# Main data fetch
with st.spinner("Fetching real-time data..."):
    data = fetch_realtime_data(ticker)
    st.session_state.last_update = datetime.now()

if data:
    info = data['info']
    intraday = data['intraday']
    daily = data['daily']
    
    # Current price display
    st.subheader(f"{ticker} - Live Quote")
    
    # Get current values
    try:
        current_price = info.last_price
        prev_close = info.previous_close
        day_high = info.day_high
        day_low = info.day_low
        
        change, pct_change = format_change(current_price, prev_close)
        
        # Price metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Last Price",
                f"${current_price:,.2f}",
                f"{change:+.2f} ({pct_change})"
            )
        
        with col2:
            st.metric("Previous Close", f"${prev_close:,.2f}")
        
        with col3:
            st.metric("Day High", f"${day_high:,.2f}")
        
        with col4:
            st.metric("Day Low", f"${day_low:,.2f}")
        
        with col5:
            day_range = day_high - day_low
            st.metric("Day Range", f"${day_range:,.2f}")
            
    except Exception as e:
        st.warning(f"Some quote data unavailable: {e}")
    
    # Last update time
    update_col1, update_col2 = st.columns([3, 1])
    with update_col1:
        st.caption(f"🕐 Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
    with update_col2:
        if auto_refresh:
            st.caption(f"⏱️ Auto-refresh: {refresh_interval}s")
    
    st.divider()
    
    # Charts
    tab1, tab2, tab3 = st.tabs(["📊 Intraday Chart", "📈 5-Day Chart", "📋 Raw Data"])
    
    with tab1:
        if not intraday.empty:
            st.subheader("Today's Price Action (1-min)")
            
            # Flatten columns if needed
            if isinstance(intraday.columns, pd.MultiIndex):
                intraday.columns = intraday.columns.get_level_values(0)
            
            # Create chart with high, low, close
            chart_data = intraday[['High', 'Low', 'Close']].copy()
            st.line_chart(chart_data, height=400)
            
            # Volume chart
            st.subheader("Volume")
            st.bar_chart(intraday['Volume'], height=200)
            
            # Current session stats
            st.subheader("Session Statistics")
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
            
            with stats_col1:
                session_high = intraday['High'].max()
                st.metric("Session High", f"${session_high:,.2f}")
            
            with stats_col2:
                session_low = intraday['Low'].min()
                st.metric("Session Low", f"${session_low:,.2f}")
            
            with stats_col3:
                session_range = session_high - session_low
                st.metric("Session Range", f"${session_range:,.2f}")
            
            with stats_col4:
                total_volume = intraday['Volume'].sum()
                st.metric("Total Volume", f"{total_volume:,.0f}")
        else:
            st.warning("No intraday data available. Market may be closed.")
    
    with tab2:
        if not daily.empty:
            st.subheader("5-Day Price Action (5-min)")
            
            if isinstance(daily.columns, pd.MultiIndex):
                daily.columns = daily.columns.get_level_values(0)
            
            st.line_chart(daily['Close'], height=400)
            
            # 5-day stats
            st.subheader("5-Day Statistics")
            st.dataframe(daily.describe(), use_container_width=True)
        else:
            st.warning("No 5-day data available.")
    
    with tab3:
        st.subheader("Intraday Data (1-min)")
        if not intraday.empty:
            # Show most recent data first
            display_df = intraday.sort_index(ascending=False).head(100)
            st.dataframe(display_df, use_container_width=True)
            
            # Download
            csv = intraday.to_csv()
            st.download_button(
                "📥 Download Full Intraday Data",
                data=csv,
                file_name=f"{ticker}_intraday_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("No data to display.")

else:
    st.error("Failed to fetch data. Please try again.")

# Auto-refresh logic
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()

# Footer
st.divider()
st.caption("Data provided by Yahoo Finance. Note: Yahoo Finance data may have 15-20 minute delay for futures.")
st.caption("For true real-time data, consider using a professional data feed (Polygon, IBKR, etc.)")

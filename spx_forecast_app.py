import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="ES Futures Data", page_icon="📈", layout="wide")

st.title("📈 ES Futures Data Viewer")
st.markdown("Pull E-mini S&P 500 Futures data from Yahoo Finance")

# Sidebar controls
st.sidebar.header("Settings")

# Ticker selection
ticker_options = {
    "ES=F (E-mini S&P 500 Continuous)": "ES=F",
    "SPY (S&P 500 ETF)": "SPY",
    "^GSPC (S&P 500 Index)": "^GSPC"
}
selected_ticker = st.sidebar.selectbox(
    "Select Ticker",
    options=list(ticker_options.keys()),
    index=0
)
ticker = ticker_options[selected_ticker]

# Date range
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "Start Date",
        value=datetime.now() - timedelta(days=30)
    )
with col2:
    end_date = st.date_input(
        "End Date",
        value=datetime.now()
    )

# Interval selection
interval = st.sidebar.selectbox(
    "Interval",
    options=["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"],
    index=5
)

# Fetch data button
if st.sidebar.button("Fetch Data", type="primary"):
    with st.spinner("Fetching data..."):
        try:
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False
            )
            
            if data.empty:
                st.error("No data returned. Try adjusting your date range or interval.")
            else:
                st.session_state['data'] = data
                st.session_state['ticker'] = ticker
                st.success(f"Fetched {len(data)} rows of data")
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")

# Display data if available
if 'data' in st.session_state and not st.session_state['data'].empty:
    data = st.session_state['data']
    
    # Current price info
    st.subheader(f"Current Data: {st.session_state.get('ticker', ticker)}")
    
    # Flatten multi-level columns if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # Metrics row
    latest = data.iloc[-1]
    prev = data.iloc[-2] if len(data) > 1 else latest
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        change = latest['Close'] - prev['Close']
        st.metric("Close", f"${latest['Close']:.2f}", f"{change:+.2f}")
    with col2:
        st.metric("High", f"${latest['High']:.2f}")
    with col3:
        st.metric("Low", f"${latest['Low']:.2f}")
    with col4:
        st.metric("Volume", f"{latest['Volume']:,.0f}")
    
    # Chart
    st.subheader("Price Chart")
    st.line_chart(data['Close'])
    
    # OHLC Chart
    st.subheader("OHLC Data")
    
    # Display options
    show_all = st.checkbox("Show all columns", value=True)
    
    if show_all:
        st.dataframe(data, use_container_width=True)
    else:
        st.dataframe(data[['Open', 'High', 'Low', 'Close', 'Volume']], use_container_width=True)
    
    # Download button
    csv = data.to_csv()
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"{ticker}_{start_date}_{end_date}.csv",
        mime="text/csv"
    )
    
    # Basic stats
    st.subheader("Summary Statistics")
    st.dataframe(data.describe(), use_container_width=True)

else:
    st.info("👈 Configure settings and click 'Fetch Data' to get started")
    
# Footer
st.markdown("---")
st.caption("Data provided by Yahoo Finance via yfinance library")

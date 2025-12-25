"""
Polygon Options API Diagnostic - Streamlit Version
Run with: streamlit run test_polygon_streamlit.py
"""

import streamlit as st
import requests
from datetime import datetime, time, timedelta
import pytz

POLYGON_API_KEY = "DCWuTS1R_fukpfjgf7QnXrLTEOS_giq6"
POLYGON_BASE_URL = "https://api.polygon.io"

CT_TZ = pytz.timezone('America/Chicago')

def get_ct_now():
    return datetime.now(CT_TZ)

def get_next_trading_day():
    now = get_ct_now()
    today = now.date()
    weekday = today.weekday()
    current_time = now.time()
    market_close = time(16, 0)
    
    if weekday == 5:
        next_day = today + timedelta(days=2)
    elif weekday == 6:
        next_day = today + timedelta(days=1)
    elif current_time > market_close:
        if weekday == 4:
            next_day = today + timedelta(days=3)
        else:
            next_day = today + timedelta(days=1)
    else:
        next_day = today
    return datetime.combine(next_day, time(0, 0))

def build_option_ticker(underlying: str, expiry_date: datetime, strike: float, option_type: str) -> str:
    date_str = expiry_date.strftime("%y%m%d")
    cp = "C" if option_type.upper() in ["CALL", "C"] else "P"
    strike_str = f"{int(strike * 1000):08d}"
    return f"O:{underlying}{date_str}{cp}{strike_str}"

st.set_page_config(page_title="Polygon API Diagnostic", page_icon="🔍", layout="wide")

st.title("🔍 Polygon Options API Diagnostic")
st.markdown("---")

# Timing info
now = get_ct_now()
next_trading = get_next_trading_day()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Current CT Time", now.strftime('%H:%M:%S'))
with col2:
    st.metric("Today", now.strftime('%A, %b %d'))
with col3:
    st.metric("Options Expiry", next_trading.strftime('%Y-%m-%d'))

st.markdown("---")

# Test SPX Price
st.subheader("1️⃣ SPX Price Check")
spx_price = 0
try:
    url = f"{POLYGON_BASE_URL}/v3/snapshot?ticker.any_of=I:SPX"
    params = {"apiKey": POLYGON_API_KEY}
    response = requests.get(url, params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("results"):
            spx_price = data["results"][0].get("value", 0)
            st.success(f"✅ SPX Price: **{spx_price:,.2f}**")
        else:
            st.warning(f"⚠️ No SPX data returned. Response: {data}")
    else:
        st.error(f"❌ HTTP {response.status_code}: {response.text[:200]}")
except Exception as e:
    st.error(f"❌ Exception: {e}")

if spx_price == 0:
    spx_price = st.number_input("Enter SPX price manually:", value=5950.0, step=1.0)

st.markdown("---")

# Build option tickers
st.subheader("2️⃣ Option Ticker Construction")

atm_strike = int(round(spx_price / 5) * 5)
call_strike = atm_strike + 20
put_strike = atm_strike - 20

call_ticker = build_option_ticker("SPX", next_trading, call_strike, "C")
put_ticker = build_option_ticker("SPX", next_trading, put_strike, "P")

col1, col2 = st.columns(2)
with col1:
    st.code(f"CALL: {call_ticker}")
    st.caption(f"Strike: {call_strike}")
with col2:
    st.code(f"PUT: {put_ticker}")
    st.caption(f"Strike: {put_strike}")

st.markdown("---")

# Test endpoints
st.subheader("3️⃣ API Endpoint Tests")

if st.button("🚀 Run Diagnostic", type="primary"):
    
    results = {}
    
    # Test 1: Quote endpoint
    with st.spinner("Testing Quote endpoint..."):
        try:
            url = f"{POLYGON_BASE_URL}/v3/quotes/{call_ticker}"
            params = {"limit": 1, "apiKey": POLYGON_API_KEY}
            response = requests.get(url, params=params, timeout=10)
            
            results['quote_status'] = response.status_code
            results['quote_data'] = response.json()
            
            if response.status_code == 200 and results['quote_data'].get("results"):
                r = results['quote_data']["results"][0]
                results['quote_bid'] = r.get('bid_price', 0)
                results['quote_ask'] = r.get('ask_price', 0)
            else:
                results['quote_bid'] = 0
                results['quote_ask'] = 0
        except Exception as e:
            results['quote_status'] = 'ERROR'
            results['quote_error'] = str(e)
    
    # Test 2: Trades endpoint
    with st.spinner("Testing Trades endpoint..."):
        try:
            url = f"{POLYGON_BASE_URL}/v3/trades/{call_ticker}"
            params = {"limit": 1, "apiKey": POLYGON_API_KEY}
            response = requests.get(url, params=params, timeout=10)
            
            results['trades_status'] = response.status_code
            results['trades_data'] = response.json()
            
            if response.status_code == 200 and results['trades_data'].get("results"):
                results['last_trade'] = results['trades_data']["results"][0].get('price', 0)
            else:
                results['last_trade'] = 0
        except Exception as e:
            results['trades_status'] = 'ERROR'
            results['trades_error'] = str(e)
    
    # Test 3: Snapshot endpoint
    with st.spinner("Testing Snapshot endpoint..."):
        try:
            url = f"{POLYGON_BASE_URL}/v3/snapshot/options/{call_ticker}"
            params = {"apiKey": POLYGON_API_KEY}
            response = requests.get(url, params=params, timeout=10)
            
            results['snapshot_status'] = response.status_code
            results['snapshot_data'] = response.json()
            
            if response.status_code == 200 and results['snapshot_data'].get("results"):
                r = results['snapshot_data']["results"]
                results['open_interest'] = r.get('open_interest', 0)
                results['iv'] = r.get('implied_volatility', 0)
                results['delta'] = r.get('greeks', {}).get('delta', 0)
            else:
                results['open_interest'] = 0
                results['iv'] = 0
                results['delta'] = 0
        except Exception as e:
            results['snapshot_status'] = 'ERROR'
            results['snapshot_error'] = str(e)
    
    # Test 4: SPY fallback
    with st.spinner("Testing SPY fallback..."):
        try:
            spy_strike = round(call_strike / 10)
            spy_ticker = build_option_ticker("SPY", next_trading, spy_strike, "C")
            
            url = f"{POLYGON_BASE_URL}/v3/quotes/{spy_ticker}"
            params = {"limit": 1, "apiKey": POLYGON_API_KEY}
            response = requests.get(url, params=params, timeout=10)
            
            results['spy_ticker'] = spy_ticker
            results['spy_status'] = response.status_code
            results['spy_data'] = response.json()
            
            if response.status_code == 200 and results['spy_data'].get("results"):
                r = results['spy_data']["results"][0]
                results['spy_bid'] = r.get('bid_price', 0)
                results['spy_ask'] = r.get('ask_price', 0)
            else:
                results['spy_bid'] = 0
                results['spy_ask'] = 0
        except Exception as e:
            results['spy_status'] = 'ERROR'
            results['spy_error'] = str(e)
    
    # Display results
    st.markdown("---")
    st.subheader("📊 Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Quote Endpoint**")
        if results.get('quote_status') == 200:
            if results.get('quote_bid', 0) > 0:
                st.success(f"✅ Bid: ${results['quote_bid']:.2f}")
                st.success(f"✅ Ask: ${results['quote_ask']:.2f}")
            else:
                st.warning("⚠️ Status 200 but no quotes")
                st.json(results.get('quote_data', {}))
        else:
            st.error(f"❌ Status: {results.get('quote_status')}")
            if 'quote_error' in results:
                st.error(results['quote_error'])
    
    with col2:
        st.markdown("**Trades Endpoint**")
        if results.get('trades_status') == 200:
            if results.get('last_trade', 0) > 0:
                st.success(f"✅ Last: ${results['last_trade']:.2f}")
            else:
                st.warning("⚠️ Status 200 but no trades")
        else:
            st.error(f"❌ Status: {results.get('trades_status')}")
    
    with col3:
        st.markdown("**Snapshot Endpoint**")
        if results.get('snapshot_status') == 200:
            if results.get('delta', 0) != 0:
                st.success(f"✅ Delta: {results['delta']:.3f}")
                st.success(f"✅ IV: {results['iv']:.2%}" if results['iv'] else "IV: N/A")
            else:
                st.warning("⚠️ Status 200 but no data")
        else:
            st.error(f"❌ Status: {results.get('snapshot_status')}")
    
    st.markdown("---")
    st.markdown("**SPY Fallback Test**")
    st.code(results.get('spy_ticker', 'N/A'))
    if results.get('spy_status') == 200 and results.get('spy_bid', 0) > 0:
        st.success(f"✅ SPY Bid: ${results['spy_bid']:.2f} | Ask: ${results['spy_ask']:.2f}")
        st.info(f"💡 SPX equivalent: ${results['spy_bid'] * 10:.2f} - ${results['spy_ask'] * 10:.2f}")
    else:
        st.warning("⚠️ SPY quotes also unavailable")
    
    st.markdown("---")
    st.subheader("🔍 Diagnosis")
    
    has_quotes = results.get('quote_bid', 0) > 0 or results.get('spy_bid', 0) > 0
    
    if has_quotes:
        st.success("✅ Options quotes ARE available! The main app should work.")
    else:
        st.error("❌ No options quotes returned")
        st.markdown("""
        **Possible causes:**
        1. **Polygon Free Tier** - Free tier does NOT include options quotes. You need Options Starter ($79/mo) or higher.
        2. **Market not open yet** - SPX options may not have quotes in pre-market
        3. **API Key issue** - Your key may not have options permissions
        4. **Rate limiting** - You may have exceeded API limits
        
        **To verify your plan:**
        - Log in to [polygon.io](https://polygon.io)
        - Check your subscription level
        - Options require "Options Starter" or higher
        """)

st.markdown("---")
st.caption("Run this diagnostic when SPX Prophet isn't showing option prices")
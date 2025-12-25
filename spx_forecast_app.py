"""
Polygon Options API Diagnostic - Streamlit Version v2
Run with: streamlit run test_polygon_streamlit.py
"""

import streamlit as st
import requests
from datetime import datetime, time, timedelta, date
import pytz

# Updated API key
DEFAULT_API_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
POLYGON_BASE_URL = "https://api.polygon.io"

CT_TZ = pytz.timezone('America/Chicago')

# US Market Holidays 2025
HOLIDAYS_2025 = [
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),   # Independence Day
    date(2025, 9, 1),   # Labor Day
    date(2025, 11, 27), # Thanksgiving
    date(2025, 12, 25), # Christmas
]

def get_ct_now():
    return datetime.now(CT_TZ)

def is_market_holiday(d: date) -> bool:
    return d in HOLIDAYS_2025

def get_next_trading_day():
    now = get_ct_now()
    today = now.date()
    weekday = today.weekday()
    current_time = now.time()
    market_close = time(16, 0)
    
    if weekday >= 5 or current_time > market_close or is_market_holiday(today):
        next_day = today + timedelta(days=1)
    else:
        next_day = today
    
    while next_day.weekday() >= 5 or is_market_holiday(next_day):
        next_day += timedelta(days=1)
    
    return datetime.combine(next_day, time(0, 0))

def build_option_ticker(underlying: str, expiry_date: datetime, strike: float, option_type: str) -> str:
    date_str = expiry_date.strftime("%y%m%d")
    cp = "C" if option_type.upper() in ["CALL", "C"] else "P"
    strike_str = f"{int(strike * 1000):08d}"
    return f"O:{underlying}{date_str}{cp}{strike_str}"

st.set_page_config(page_title="Polygon API Diagnostic v2", page_icon="🔍", layout="wide")

st.title("🔍 Polygon Options API Diagnostic v2")

# Sidebar for API key
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Polygon API Key", value=DEFAULT_API_KEY, type="password")
    st.caption("Enter your API key from polygon.io dashboard")
    
    if st.button("🔄 Clear Cache & Refresh"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# Step 0: Check subscription
st.subheader("0️⃣ Subscription Check")

try:
    # Check account status using a simple endpoint
    url = f"{POLYGON_BASE_URL}/v1/marketstatus/now"
    params = {"apiKey": api_key}
    response = requests.get(url, params=params, timeout=10)
    
    if response.status_code == 200:
        st.success("✅ API Key is valid!")
        data = response.json()
        st.json(data)
    elif response.status_code == 401:
        st.error("❌ Invalid API Key (401 Unauthorized)")
    elif response.status_code == 403:
        st.error("❌ API Key doesn't have access (403 Forbidden)")
    else:
        st.warning(f"⚠️ Status {response.status_code}: {response.text[:200]}")
except Exception as e:
    st.error(f"❌ Exception: {e}")

st.markdown("---")

# Timing info
now = get_ct_now()
next_trading = get_next_trading_day()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Current CT Time", now.strftime('%H:%M:%S'))
with col2:
    st.metric("Today", now.strftime('%A, %b %d'))
with col3:
    is_holiday = is_market_holiday(now.date())
    st.metric("Holiday?", "🎄 YES" if is_holiday else "No")
with col4:
    st.metric("Next Trading Day", next_trading.strftime('%a %b %d'))

if is_market_holiday(now.date()):
    st.warning(f"⚠️ Today is Christmas - Markets are CLOSED. Testing with Friday Dec 26 expiry.")

st.markdown("---")

# Test SPX Price
st.subheader("1️⃣ SPX Price Check")
spx_price = 0
try:
    url = f"{POLYGON_BASE_URL}/v3/snapshot?ticker.any_of=I:SPX"
    params = {"apiKey": api_key}
    response = requests.get(url, params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("results"):
            spx_price = data["results"][0].get("value", 0)
            st.success(f"✅ SPX Price: **{spx_price:,.2f}**")
        else:
            st.warning(f"⚠️ No SPX data returned")
    else:
        st.error(f"❌ HTTP {response.status_code}")
except Exception as e:
    st.error(f"❌ Exception: {e}")

if spx_price == 0:
    spx_price = st.number_input("Enter SPX price manually:", value=5950.0, step=1.0)

st.markdown("---")

# Build option tickers - try SPXW (weekly) instead of SPX
st.subheader("2️⃣ Option Ticker Construction")

st.info(f"📅 Building options for expiry: **{next_trading.strftime('%Y-%m-%d')}** ({next_trading.strftime('%A')})")

atm_strike = int(round(spx_price / 5) * 5)
call_strike = atm_strike + 20
put_strike = atm_strike - 20

# Try both SPX and SPXW tickers
call_ticker_spx = build_option_ticker("SPX", next_trading, call_strike, "C")
call_ticker_spxw = build_option_ticker("SPXW", next_trading, call_strike, "C")
spy_ticker = build_option_ticker("SPY", next_trading, round(call_strike/10), "C")

col1, col2, col3 = st.columns(3)
with col1:
    st.code(f"SPX: {call_ticker_spx}")
with col2:
    st.code(f"SPXW: {call_ticker_spxw}")
with col3:
    st.code(f"SPY: {spy_ticker}")

st.markdown("---")

# Test endpoints
st.subheader("3️⃣ API Endpoint Tests")

if st.button("🚀 Run Full Diagnostic", type="primary"):
    
    st.markdown("### Testing SPX Options")
    
    # Test SPX Quote
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**SPX Ticker**")
        try:
            url = f"{POLYGON_BASE_URL}/v3/quotes/{call_ticker_spx}"
            params = {"limit": 1, "apiKey": api_key}
            response = requests.get(url, params=params, timeout=10)
            st.write(f"Status: {response.status_code}")
            data = response.json()
            if response.status_code == 200 and data.get("results"):
                st.success("✅ Has data!")
                st.json(data["results"][0])
            else:
                st.warning(f"Response: {data}")
        except Exception as e:
            st.error(str(e))
    
    with col2:
        st.markdown("**SPXW Ticker (Weekly)**")
        try:
            url = f"{POLYGON_BASE_URL}/v3/quotes/{call_ticker_spxw}"
            params = {"limit": 1, "apiKey": api_key}
            response = requests.get(url, params=params, timeout=10)
            st.write(f"Status: {response.status_code}")
            data = response.json()
            if response.status_code == 200 and data.get("results"):
                st.success("✅ Has data!")
                st.json(data["results"][0])
            else:
                st.warning(f"Response: {data}")
        except Exception as e:
            st.error(str(e))
    
    st.markdown("---")
    st.markdown("### Testing Snapshot Endpoint (Greeks/IV)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**SPX Snapshot**")
        try:
            url = f"{POLYGON_BASE_URL}/v3/snapshot/options/{call_ticker_spx}"
            params = {"apiKey": api_key}
            response = requests.get(url, params=params, timeout=10)
            st.write(f"Status: {response.status_code}")
            data = response.json()
            if response.status_code == 200 and data.get("results"):
                st.success("✅ Has data!")
                st.json(data["results"])
            else:
                st.warning(f"Response: {data}")
        except Exception as e:
            st.error(str(e))
    
    with col2:
        st.markdown("**SPXW Snapshot**")
        try:
            url = f"{POLYGON_BASE_URL}/v3/snapshot/options/{call_ticker_spxw}"
            params = {"apiKey": api_key}
            response = requests.get(url, params=params, timeout=10)
            st.write(f"Status: {response.status_code}")
            data = response.json()
            if response.status_code == 200 and data.get("results"):
                st.success("✅ Has data!")
                st.json(data["results"])
            else:
                st.warning(f"Response: {data}")
        except Exception as e:
            st.error(str(e))
    
    st.markdown("---")
    st.markdown("### Testing SPY Options (Most Liquid)")
    
    try:
        url = f"{POLYGON_BASE_URL}/v3/quotes/{spy_ticker}"
        params = {"limit": 1, "apiKey": api_key}
        response = requests.get(url, params=params, timeout=10)
        st.write(f"Status: {response.status_code}")
        data = response.json()
        if response.status_code == 200 and data.get("results"):
            st.success("✅ SPY options working!")
            st.json(data["results"][0])
        else:
            st.warning(f"Response: {data}")
    except Exception as e:
        st.error(str(e))
    
    st.markdown("---")
    st.markdown("### Testing Options Chain Endpoint")
    
    try:
        # Try to get the options chain
        url = f"{POLYGON_BASE_URL}/v3/reference/options/contracts"
        params = {
            "underlying_ticker": "SPY",
            "expiration_date": next_trading.strftime("%Y-%m-%d"),
            "limit": 5,
            "apiKey": api_key
        }
        response = requests.get(url, params=params, timeout=10)
        st.write(f"Status: {response.status_code}")
        data = response.json()
        if response.status_code == 200 and data.get("results"):
            st.success(f"✅ Found {len(data['results'])} contracts!")
            for contract in data["results"][:3]:
                st.code(contract.get("ticker", "N/A"))
        else:
            st.warning(f"Response: {data}")
    except Exception as e:
        st.error(str(e))

st.markdown("---")
st.subheader("📝 Notes")
st.markdown("""
**Market is closed today (Christmas)** - Live quotes won't be available until Friday Dec 26.
However, the API should still return 200 (not 403) if your subscription is active.

**If still seeing 403:** Your new subscription might take 5-10 minutes to fully activate.
""")
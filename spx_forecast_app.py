"""
Polygon Options API Diagnostic - v3 with I:SPX
Run with: streamlit run test_polygon_streamlit.py
"""

import streamlit as st
import requests
from datetime import datetime, time, timedelta, date
import pytz

# Updated API key
POLYGON_API_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
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

st.set_page_config(page_title="Polygon API Diagnostic v3", page_icon="🔍", layout="wide")

st.title("🔍 Polygon Options API Diagnostic v3")
st.caption("Using I:SPX as underlying ticker")

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
    st.warning(f"⚠️ Today is Christmas - Markets are CLOSED.")

st.markdown("---")

# Step 1: Check API Key validity
st.subheader("1️⃣ API Key Check")
try:
    url = f"{POLYGON_BASE_URL}/v1/marketstatus/now"
    params = {"apiKey": POLYGON_API_KEY}
    response = requests.get(url, params=params, timeout=10)
    
    if response.status_code == 200:
        st.success(f"✅ API Key is valid!")
    else:
        st.error(f"❌ Status {response.status_code}")
except Exception as e:
    st.error(f"❌ Exception: {e}")

st.markdown("---")

# Step 2: Get SPX Price
st.subheader("2️⃣ SPX Index Price (I:SPX)")
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
            st.warning(f"⚠️ No data: {data}")
    else:
        st.error(f"❌ HTTP {response.status_code}: {response.text[:200]}")
except Exception as e:
    st.error(f"❌ Exception: {e}")

if spx_price == 0:
    spx_price = st.number_input("Enter SPX price manually:", value=6930.0, step=1.0)

st.markdown("---")

# Step 3: Query Options Contracts for I:SPX
st.subheader("3️⃣ Options Contracts for I:SPX")

expiry_date = next_trading.strftime("%Y-%m-%d")
st.info(f"📅 Looking for contracts expiring: **{expiry_date}**")

if st.button("🔍 Search for SPX Options Contracts", type="primary"):
    
    try:
        url = f"{POLYGON_BASE_URL}/v3/reference/options/contracts"
        params = {
            "underlying_ticker": "I:SPX",
            "expiration_date": expiry_date,
            "limit": 20,
            "apiKey": POLYGON_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        
        st.write(f"**Status:** {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            results = data.get("results", [])
            if results:
                st.success(f"✅ Found **{len(results)}** contracts!")
                
                # Show sample contracts
                st.markdown("**Sample Contracts:**")
                for contract in results[:10]:
                    ticker = contract.get("ticker", "N/A")
                    strike = contract.get("strike_price", 0)
                    cp = contract.get("contract_type", "")
                    st.code(f"{ticker} | Strike: {strike} | Type: {cp}")
                
                # Store first contract for snapshot test
                st.session_state['sample_contract'] = results[0].get("ticker")
            else:
                st.warning("⚠️ No contracts found for this expiration date")
                st.json(data)
        else:
            st.error(f"❌ Error: {data}")
            
    except Exception as e:
        st.error(f"❌ Exception: {e}")

st.markdown("---")

# Step 4: Test Options Snapshot
st.subheader("4️⃣ Options Snapshot (Greeks, IV, OI)")

sample_ticker = st.session_state.get('sample_contract', '')
if sample_ticker:
    st.info(f"Testing with: **{sample_ticker}**")

if st.button("📊 Get Options Snapshot", type="secondary"):
    
    if not sample_ticker:
        st.warning("⚠️ Run Step 3 first to find a contract")
    else:
        try:
            url = f"{POLYGON_BASE_URL}/v3/snapshot/options/{sample_ticker}"
            params = {"apiKey": POLYGON_API_KEY}
            response = requests.get(url, params=params, timeout=10)
            
            st.write(f"**Status:** {response.status_code}")
            data = response.json()
            
            if response.status_code == 200 and data.get("results"):
                st.success("✅ Snapshot data retrieved!")
                result = data["results"]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Pricing**")
                    day = result.get("day", {})
                    st.metric("Open", f"${day.get('open', 0):.2f}")
                    st.metric("High", f"${day.get('high', 0):.2f}")
                    st.metric("Low", f"${day.get('low', 0):.2f}")
                    st.metric("Close", f"${day.get('close', 0):.2f}")
                    st.metric("Volume", f"{day.get('volume', 0):,}")
                
                with col2:
                    st.markdown("**Greeks**")
                    greeks = result.get("greeks", {})
                    st.metric("Delta", f"{greeks.get('delta', 0):.4f}")
                    st.metric("Gamma", f"{greeks.get('gamma', 0):.6f}")
                    st.metric("Theta", f"{greeks.get('theta', 0):.4f}")
                    st.metric("Vega", f"{greeks.get('vega', 0):.4f}")
                
                with col3:
                    st.markdown("**Other**")
                    st.metric("IV", f"{result.get('implied_volatility', 0):.2%}")
                    st.metric("Open Interest", f"{result.get('open_interest', 0):,}")
                    
                    underlying = result.get("underlying_asset", {})
                    st.metric("Underlying", f"${underlying.get('price', 0):,.2f}")
                
                st.markdown("---")
                st.markdown("**Full Response:**")
                st.json(result)
            else:
                st.warning(f"⚠️ No snapshot data: {data}")
                
        except Exception as e:
            st.error(f"❌ Exception: {e}")

st.markdown("---")

# Step 5: Test Quote Endpoint
st.subheader("5️⃣ Options Quote (Bid/Ask)")

if st.button("💰 Get Options Quote", type="secondary"):
    
    if not sample_ticker:
        st.warning("⚠️ Run Step 3 first to find a contract")
    else:
        try:
            url = f"{POLYGON_BASE_URL}/v3/quotes/{sample_ticker}"
            params = {"limit": 1, "apiKey": POLYGON_API_KEY}
            response = requests.get(url, params=params, timeout=10)
            
            st.write(f"**Status:** {response.status_code}")
            data = response.json()
            
            if response.status_code == 200 and data.get("results"):
                st.success("✅ Quote data retrieved!")
                quote = data["results"][0]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Bid", f"${quote.get('bid_price', 0):.2f}")
                    st.metric("Bid Size", quote.get('bid_size', 0))
                with col2:
                    st.metric("Ask", f"${quote.get('ask_price', 0):.2f}")
                    st.metric("Ask Size", quote.get('ask_size', 0))
                
                st.json(quote)
            else:
                st.warning(f"⚠️ No quote data (market may be closed): {data}")
                
        except Exception as e:
            st.error(f"❌ Exception: {e}")

st.markdown("---")
st.subheader("📝 Summary")
st.markdown("""
**Key Findings:**
- Use `I:SPX` as the underlying ticker for SPX options
- SPXW (weekly) contracts are found under `I:SPX` - filter by expiration date
- Options Starter plan provides **15-minute delayed** data
- Market is closed today (Christmas) - quotes won't have live bid/ask until Friday

**Next Steps:**
Once we confirm the API works, we'll rebuild SPX Prophet with:
- Real Greeks (delta, gamma, theta, vega)
- Implied Volatility
- Open Interest analysis
- Historical options data (2 years!)
""")
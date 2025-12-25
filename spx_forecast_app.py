"""
Polygon Options API Diagnostic - v4 - Find Available Contracts
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

def get_ct_now():
    return datetime.now(CT_TZ)

st.set_page_config(page_title="Polygon API Diagnostic v4", page_icon="🔍", layout="wide")

st.title("🔍 Polygon Options API Diagnostic v4")
st.caption("Finding available SPX contracts")

now = get_ct_now()
st.info(f"📅 Current date: **{now.strftime('%A, %B %d, %Y')}** | Time: **{now.strftime('%H:%M CT')}**")

st.markdown("---")

# Step 1: Search for ANY SPX contracts (no date filter)
st.subheader("1️⃣ Find ALL Available SPX Contracts")

if st.button("🔍 Search ALL I:SPX Contracts (no date filter)", type="primary"):
    
    try:
        url = f"{POLYGON_BASE_URL}/v3/reference/options/contracts"
        params = {
            "underlying_ticker": "I:SPX",
            "limit": 50,
            "apiKey": POLYGON_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        
        st.write(f"**Status:** {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            results = data.get("results", [])
            if results:
                st.success(f"✅ Found **{len(results)}** contracts!")
                
                # Get unique expiration dates
                expirations = sorted(set([c.get("expiration_date", "") for c in results]))
                st.markdown(f"**Available Expiration Dates:** {', '.join(expirations[:10])}")
                
                # Show sample contracts
                st.markdown("**Sample Contracts:**")
                for contract in results[:15]:
                    ticker = contract.get("ticker", "N/A")
                    strike = contract.get("strike_price", 0)
                    cp = contract.get("contract_type", "")
                    exp = contract.get("expiration_date", "")
                    st.code(f"{ticker} | Strike: {strike} | {cp} | Exp: {exp}")
                
                st.session_state['sample_contract'] = results[0].get("ticker")
                st.session_state['available_expirations'] = expirations
            else:
                st.warning("⚠️ No contracts found")
                st.json(data)
        else:
            st.error(f"❌ Error: {data}")
            
    except Exception as e:
        st.error(f"❌ Exception: {e}")

st.markdown("---")

# Step 2: Try SPY instead (definitely has contracts)
st.subheader("2️⃣ Find SPY Contracts (for comparison)")

if st.button("🔍 Search SPY Contracts", type="secondary"):
    
    try:
        url = f"{POLYGON_BASE_URL}/v3/reference/options/contracts"
        params = {
            "underlying_ticker": "SPY",
            "expiration_date.gte": now.strftime("%Y-%m-%d"),
            "expiration_date.lte": (now + timedelta(days=7)).strftime("%Y-%m-%d"),
            "limit": 20,
            "apiKey": POLYGON_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        
        st.write(f"**Status:** {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            results = data.get("results", [])
            if results:
                st.success(f"✅ Found **{len(results)}** SPY contracts!")
                
                expirations = sorted(set([c.get("expiration_date", "") for c in results]))
                st.markdown(f"**Available Expiration Dates:** {', '.join(expirations)}")
                
                for contract in results[:10]:
                    ticker = contract.get("ticker", "N/A")
                    strike = contract.get("strike_price", 0)
                    cp = contract.get("contract_type", "")
                    exp = contract.get("expiration_date", "")
                    st.code(f"{ticker} | Strike: {strike} | {cp} | Exp: {exp}")
                
                st.session_state['spy_contract'] = results[0].get("ticker")
            else:
                st.warning("⚠️ No SPY contracts found")
        else:
            st.error(f"❌ Error: {data}")
            
    except Exception as e:
        st.error(f"❌ Exception: {e}")

st.markdown("---")

# Step 3: Test Snapshot on found contract
st.subheader("3️⃣ Test Options Snapshot")

sample = st.session_state.get('sample_contract', '') or st.session_state.get('spy_contract', '')
if sample:
    st.info(f"Testing with: **{sample}**")

manual_ticker = st.text_input("Or enter a ticker manually:", value=sample)

if st.button("📊 Get Snapshot", type="secondary"):
    ticker_to_test = manual_ticker or sample
    
    if not ticker_to_test:
        st.warning("⚠️ No contract to test")
    else:
        try:
            url = f"{POLYGON_BASE_URL}/v3/snapshot/options/{ticker_to_test}"
            params = {"apiKey": POLYGON_API_KEY}
            response = requests.get(url, params=params, timeout=10)
            
            st.write(f"**Status:** {response.status_code}")
            data = response.json()
            
            if response.status_code == 200 and data.get("results"):
                st.success("✅ Snapshot retrieved!")
                result = data["results"]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Greeks**")
                    greeks = result.get("greeks", {})
                    st.metric("Delta", f"{greeks.get('delta', 0):.4f}")
                    st.metric("Gamma", f"{greeks.get('gamma', 0):.6f}")
                    st.metric("Theta", f"{greeks.get('theta', 0):.4f}")
                    st.metric("Vega", f"{greeks.get('vega', 0):.4f}")
                
                with col2:
                    st.markdown("**IV & OI**")
                    st.metric("Implied Vol", f"{result.get('implied_volatility', 0):.2%}")
                    st.metric("Open Interest", f"{result.get('open_interest', 0):,}")
                
                with col3:
                    st.markdown("**Day Data**")
                    day = result.get("day", {})
                    st.metric("Close", f"${day.get('close', 0):.2f}")
                    st.metric("Volume", f"{day.get('volume', 0):,}")
                
                with st.expander("Full Response"):
                    st.json(result)
            else:
                st.warning(f"⚠️ Response: {data}")
                
        except Exception as e:
            st.error(f"❌ Exception: {e}")

st.markdown("---")

# Step 4: Check what indices are available
st.subheader("4️⃣ Check Available Indices")

if st.button("📋 List Available Indices"):
    try:
        url = f"{POLYGON_BASE_URL}/v3/reference/tickers"
        params = {
            "type": "INDEX",
            "market": "indices",
            "search": "SPX",
            "limit": 20,
            "apiKey": POLYGON_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        
        st.write(f"**Status:** {response.status_code}")
        data = response.json()
        
        if response.status_code == 200 and data.get("results"):
            st.success(f"✅ Found indices!")
            for idx in data["results"]:
                st.code(f"{idx.get('ticker', 'N/A')} - {idx.get('name', 'N/A')}")
        else:
            st.warning(f"Response: {data}")
    except Exception as e:
        st.error(f"❌ Exception: {e}")

st.markdown("---")
st.markdown("""
**Debug Notes:**
- If no I:SPX contracts found, the Indices plan might not be active yet
- Try SPY contracts as a fallback (should always work with Options plan)
- Contract data might not be available on holidays
""")
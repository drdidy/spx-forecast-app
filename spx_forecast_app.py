"""
Polygon Options API Diagnostic - v4 FIXED
Run with: streamlit run test_polygon_v4.py
"""

import streamlit as st
import requests
from datetime import datetime, time, timedelta, date
import pytz

# Your new API key
POLYGON_API_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
POLYGON_BASE_URL = "https://api.polygon.io"

CT_TZ = pytz.timezone('America/Chicago')

def get_ct_now():
    return datetime.now(CT_TZ)

st.set_page_config(page_title="Polygon v4 FIXED", page_icon="🔍", layout="wide")

st.title("🔍 Polygon Options Diagnostic v4 FIXED")

now = get_ct_now()
st.info(f"📅 **{now.strftime('%A, %B %d, %Y')}** | **{now.strftime('%H:%M CT')}**")

st.markdown("---")

##############################################
# TEST 1: Search ALL SPX contracts (NO date filter)
##############################################
st.subheader("1️⃣ Find ALL SPX Contracts (NO date filter)")

if st.button("🔍 Search ALL I:SPX Contracts", key="btn1"):
    with st.spinner("Searching..."):
        try:
            url = f"{POLYGON_BASE_URL}/v3/reference/options/contracts"
            params = {
                "underlying_ticker": "I:SPX",
                "limit": 100,
                "apiKey": POLYGON_API_KEY
            }
            response = requests.get(url, params=params, timeout=15)
            
            st.write(f"**Status:** {response.status_code}")
            data = response.json()
            
            results = data.get("results", [])
            if results:
                st.success(f"✅ Found **{len(results)}** SPX contracts!")
                
                expirations = sorted(set([c.get("expiration_date", "") for c in results]))
                st.write(f"**Expiration dates found:** {', '.join(expirations[:15])}")
                
                st.markdown("**Sample contracts:**")
                for c in results[:10]:
                    st.code(f"{c.get('ticker')} | Strike: {c.get('strike_price')} | {c.get('contract_type')} | Exp: {c.get('expiration_date')}")
                
                st.session_state['found_contract'] = results[0].get("ticker")
            else:
                st.warning("⚠️ No I:SPX contracts found")
                st.json(data)
        except Exception as e:
            st.error(f"❌ Error: {e}")

st.markdown("---")

##############################################
# TEST 2: Search SPY contracts (should always work)
##############################################
st.subheader("2️⃣ Find SPY Contracts (should work)")

if st.button("🔍 Search SPY Contracts", key="btn2"):
    with st.spinner("Searching..."):
        try:
            url = f"{POLYGON_BASE_URL}/v3/reference/options/contracts"
            params = {
                "underlying_ticker": "SPY",
                "limit": 50,
                "apiKey": POLYGON_API_KEY
            }
            response = requests.get(url, params=params, timeout=15)
            
            st.write(f"**Status:** {response.status_code}")
            data = response.json()
            
            results = data.get("results", [])
            if results:
                st.success(f"✅ Found **{len(results)}** SPY contracts!")
                
                expirations = sorted(set([c.get("expiration_date", "") for c in results]))
                st.write(f"**Expiration dates:** {', '.join(expirations[:10])}")
                
                for c in results[:8]:
                    st.code(f"{c.get('ticker')} | Strike: {c.get('strike_price')} | {c.get('contract_type')}")
                
                st.session_state['spy_contract'] = results[0].get("ticker")
            else:
                st.warning("⚠️ No SPY contracts found")
                st.json(data)
        except Exception as e:
            st.error(f"❌ Error: {e}")

st.markdown("---")

##############################################
# TEST 3: Get snapshot for a contract
##############################################
st.subheader("3️⃣ Get Options Snapshot (Greeks, IV)")

contract = st.session_state.get('found_contract') or st.session_state.get('spy_contract') or ""
test_ticker = st.text_input("Contract ticker to test:", value=contract)

if st.button("📊 Get Snapshot", key="btn3"):
    if not test_ticker:
        st.warning("Enter a ticker or run tests above first")
    else:
        with st.spinner("Fetching snapshot..."):
            try:
                url = f"{POLYGON_BASE_URL}/v3/snapshot/options/{test_ticker}"
                params = {"apiKey": POLYGON_API_KEY}
                response = requests.get(url, params=params, timeout=15)
                
                st.write(f"**Status:** {response.status_code}")
                data = response.json()
                
                if response.status_code == 200 and data.get("results"):
                    st.success("✅ Got snapshot!")
                    r = data["results"]
                    
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown("**Greeks**")
                        g = r.get("greeks", {})
                        st.metric("Delta", f"{g.get('delta', 0):.4f}")
                        st.metric("Gamma", f"{g.get('gamma', 0):.6f}")
                        st.metric("Theta", f"{g.get('theta', 0):.4f}")
                        st.metric("Vega", f"{g.get('vega', 0):.4f}")
                    with c2:
                        st.markdown("**IV & OI**")
                        st.metric("IV", f"{r.get('implied_volatility', 0):.2%}")
                        st.metric("Open Interest", f"{r.get('open_interest', 0):,}")
                    with c3:
                        st.markdown("**Price**")
                        d = r.get("day", {})
                        st.metric("Close", f"${d.get('close', 0):.2f}")
                        st.metric("Volume", f"{d.get('volume', 0):,}")
                    
                    with st.expander("Full JSON"):
                        st.json(r)
                else:
                    st.warning(f"No data: {data}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

st.markdown("---")

##############################################
# TEST 4: Check your subscription
##############################################
st.subheader("4️⃣ Check API Access")

if st.button("🔑 Check API Key Status", key="btn4"):
    try:
        url = f"{POLYGON_BASE_URL}/v1/marketstatus/now"
        params = {"apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            st.success("✅ API key is valid!")
            st.json(response.json())
        else:
            st.error(f"❌ Status {response.status_code}: {response.text}")
    except Exception as e:
        st.error(f"❌ Error: {e}")

st.markdown("---")
st.caption("v4 FIXED - No date filtering on SPX search")
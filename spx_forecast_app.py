"""
SCHWAB API VALIDATION APP
========================
Phase 1: Test that the Schwab API connection works before building Market Prophet

This minimal Streamlit app:
1. Handles OAuth 2.0 authentication with Schwab
2. Fetches a quote to prove the connection works
3. Stores and refreshes tokens properly

Run with: streamlit run app.py
"""

import streamlit as st
import requests
import base64
import json
import os
import webbrowser
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
import threading
import socket
import ssl

# =============================================================================
# CONFIGURATION
# =============================================================================

# Schwab API Credentials (from your documentation)
CLIENT_ID = "mLgLwkRB1Y93Gtqc80G2qS4exFtSZD4rpmEJGvPD7SA6eZ9x"
CLIENT_SECRET = "5BBVH9UK5jJ8c8EUuLHKX69mEBUaubz63L0X4z9hHDUb5tpGxxvaV5AX1A9k5S4s"
REDIRECT_URI = "https://127.0.0.1:8080/callback"

# API URLs
AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
API_BASE = "https://api.schwabapi.com/marketdata/v1"

# Token storage file
TOKEN_FILE = Path("tokens.json")

# =============================================================================
# TOKEN MANAGEMENT
# =============================================================================

def save_tokens(tokens: dict):
    """Save tokens to file"""
    tokens['saved_at'] = datetime.now().isoformat()
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)
    st.session_state.tokens = tokens

def load_tokens() -> dict | None:
    """Load tokens from file"""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None

def get_basic_auth_header() -> str:
    """Generate Basic Auth header for token requests"""
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"

def is_token_expired(tokens: dict) -> bool:
    """Check if access token is expired"""
    if not tokens or 'saved_at' not in tokens:
        return True
    saved_at = datetime.fromisoformat(tokens['saved_at'])
    expires_in = tokens.get('expires_in', 1800)  # Default 30 min
    expiry_time = saved_at + timedelta(seconds=expires_in - 60)  # 1 min buffer
    return datetime.now() >= expiry_time

def exchange_code_for_tokens(auth_code: str) -> dict | None:
    """Exchange authorization code for access/refresh tokens"""
    headers = {
        "Authorization": get_basic_auth_header(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI
    }
    
    try:
        response = requests.post(TOKEN_URL, headers=headers, data=data)
        if response.status_code == 200:
            tokens = response.json()
            save_tokens(tokens)
            return tokens
        else:
            st.error(f"Token exchange failed: {response.status_code}")
            st.code(response.text)
            return None
    except Exception as e:
        st.error(f"Token exchange error: {e}")
        return None

def refresh_access_token(refresh_token: str) -> dict | None:
    """Use refresh token to get new access token"""
    headers = {
        "Authorization": get_basic_auth_header(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    try:
        response = requests.post(TOKEN_URL, headers=headers, data=data)
        if response.status_code == 200:
            tokens = response.json()
            # Keep the refresh token if not returned
            if 'refresh_token' not in tokens:
                tokens['refresh_token'] = refresh_token
            save_tokens(tokens)
            return tokens
        else:
            st.error(f"Token refresh failed: {response.status_code}")
            st.code(response.text)
            return None
    except Exception as e:
        st.error(f"Token refresh error: {e}")
        return None

def get_valid_token() -> str | None:
    """Get a valid access token, refreshing if necessary"""
    tokens = st.session_state.get('tokens') or load_tokens()
    
    if not tokens:
        return None
    
    if is_token_expired(tokens):
        st.info("Token expired, refreshing...")
        tokens = refresh_access_token(tokens.get('refresh_token'))
        if not tokens:
            return None
    
    return tokens.get('access_token')

# =============================================================================
# API CALLS
# =============================================================================

def get_quote(symbol: str) -> dict | None:
    """Fetch quote for a symbol"""
    token = get_valid_token()
    if not token:
        st.error("No valid token available. Please authenticate first.")
        return None
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # URL encode the symbol ($ becomes %24 for indices)
    encoded_symbol = urllib.parse.quote(symbol, safe='')
    url = f"{API_BASE}/quotes?symbols={encoded_symbol}&fields=quote,reference"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.error("Authentication failed. Token may be invalid.")
            # Clear tokens and force re-auth
            if TOKEN_FILE.exists():
                TOKEN_FILE.unlink()
            st.session_state.tokens = None
            return None
        else:
            st.error(f"API Error {response.status_code}")
            st.code(response.text)
            return None
    except Exception as e:
        st.error(f"API request error: {e}")
        return None

def get_options_chain(symbol: str, dte: int = 0) -> dict | None:
    """Fetch options chain for a symbol"""
    token = get_valid_token()
    if not token:
        st.error("No valid token available. Please authenticate first.")
        return None
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    encoded_symbol = urllib.parse.quote(symbol, safe='')
    url = f"{API_BASE}/chains?symbol={encoded_symbol}&contractType=ALL&strikeCount=10&includeUnderlyingQuote=true&daysToExpiration={dte}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Options Chain Error {response.status_code}")
            st.code(response.text)
            return None
    except Exception as e:
        st.error(f"Options chain error: {e}")
        return None

def get_price_history(symbol: str) -> dict | None:
    """Fetch price history (30-min candles) for a symbol"""
    token = get_valid_token()
    if not token:
        st.error("No valid token available. Please authenticate first.")
        return None
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    encoded_symbol = urllib.parse.quote(symbol, safe='')
    url = f"{API_BASE}/pricehistory?symbol={encoded_symbol}&periodType=day&period=2&frequencyType=minute&frequency=30&needExtendedHoursData=true&needPreviousClose=true"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Price History Error {response.status_code}")
            st.code(response.text)
            return None
    except Exception as e:
        st.error(f"Price history error: {e}")
        return None

# =============================================================================
# STREAMLIT UI
# =============================================================================

st.set_page_config(
    page_title="Schwab API Test",
    page_icon="📊",
    layout="wide"
)

st.title("🔌 Schwab API Connection Test")
st.markdown("**Phase 1**: Validate API connectivity before building Market Prophet")

# Initialize session state
if 'tokens' not in st.session_state:
    st.session_state.tokens = load_tokens()

# =============================================================================
# SIDEBAR: Authentication
# =============================================================================

with st.sidebar:
    st.header("🔐 Authentication")
    
    # Show current auth status
    tokens = st.session_state.tokens
    if tokens and not is_token_expired(tokens):
        st.success("✅ Authenticated")
        saved_at = datetime.fromisoformat(tokens['saved_at'])
        expires_in = tokens.get('expires_in', 1800)
        expires_at = saved_at + timedelta(seconds=expires_in)
        st.caption(f"Token expires: {expires_at.strftime('%H:%M:%S')}")
        
        if st.button("🔄 Refresh Token"):
            new_tokens = refresh_access_token(tokens.get('refresh_token'))
            if new_tokens:
                st.success("Token refreshed!")
                st.rerun()
        
        if st.button("🚪 Logout"):
            if TOKEN_FILE.exists():
                TOKEN_FILE.unlink()
            st.session_state.tokens = None
            st.rerun()
    else:
        st.warning("⚠️ Not authenticated")
        
        st.markdown("### Step 1: Generate Auth URL")
        
        # Generate authorization URL
        auth_params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": "readonly"
        }
        auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
        
        st.code(auth_url, language=None)
        
        st.markdown("""
        **Instructions:**
        1. Copy the URL above and paste it in your browser
        2. Log in to Schwab and authorize the app
        3. You'll be redirected to `https://127.0.0.1:8080/callback?code=...`
        4. Copy the `code` parameter from the URL
        5. Paste it below
        """)
        
        st.markdown("### Step 2: Enter Auth Code")
        auth_code = st.text_input("Authorization Code", type="password", 
                                   help="The 'code' parameter from the callback URL")
        
        if st.button("🔑 Exchange for Tokens", disabled=not auth_code):
            with st.spinner("Exchanging code for tokens..."):
                tokens = exchange_code_for_tokens(auth_code)
                if tokens:
                    st.success("✅ Authentication successful!")
                    st.rerun()

# =============================================================================
# MAIN: API Tests
# =============================================================================

# Check if authenticated
if not st.session_state.tokens or is_token_expired(st.session_state.tokens):
    st.info("👈 Please authenticate using the sidebar first")
    st.stop()

st.success("✅ Connected to Schwab API")

# Test tabs
tab1, tab2, tab3, tab4 = st.tabs(["📈 Quote Test", "⛓️ Options Chain", "📊 Price History", "🔧 Raw API"])

# -----------------------------------------------------------------------------
# Tab 1: Quote Test
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Test Quote Endpoint")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        symbol = st.text_input("Symbol", value="$SPX", 
                               help="Use $ prefix for indices (e.g., $SPX, $VIX)")
    with col2:
        st.write("")  # Spacer
        st.write("")
        fetch_quote = st.button("📥 Fetch Quote", type="primary")
    
    if fetch_quote:
        with st.spinner(f"Fetching {symbol}..."):
            data = get_quote(symbol)
            if data:
                st.success(f"✅ Successfully fetched {symbol}")
                
                # Display nicely formatted quote
                for sym, info in data.items():
                    st.markdown(f"### {sym}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    quote = info.get('quote', {})
                    ref = info.get('reference', {})
                    
                    with col1:
                        st.metric("Last Price", f"${quote.get('lastPrice', 'N/A'):,.2f}")
                    with col2:
                        change = quote.get('netChange', 0)
                        pct = quote.get('netPercentChange', 0)
                        st.metric("Change", f"${change:+,.2f}", f"{pct:+.2f}%")
                    with col3:
                        st.metric("Bid", f"${quote.get('bidPrice', 'N/A'):,.2f}")
                    with col4:
                        st.metric("Ask", f"${quote.get('askPrice', 'N/A'):,.2f}")
                    
                    with st.expander("📋 Full Response"):
                        st.json(info)

# -----------------------------------------------------------------------------
# Tab 2: Options Chain Test
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("Test Options Chain Endpoint")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        opt_symbol = st.text_input("Underlying Symbol", value="$SPX", key="opt_sym")
    with col2:
        dte = st.number_input("Days to Expiration", min_value=0, max_value=30, value=0)
    with col3:
        st.write("")
        st.write("")
        fetch_chain = st.button("📥 Fetch Chain", type="primary")
    
    if fetch_chain:
        with st.spinner(f"Fetching {opt_symbol} options chain..."):
            data = get_options_chain(opt_symbol, dte)
            if data:
                st.success(f"✅ Successfully fetched options chain")
                
                # Summary
                underlying = data.get('underlying', {})
                st.markdown(f"**Underlying:** {underlying.get('last', 'N/A')} | "
                           f"**Contracts:** {data.get('numberOfContracts', 'N/A')}")
                
                # Show call/put counts
                calls = data.get('callExpDateMap', {})
                puts = data.get('putExpDateMap', {})
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**CALLS**")
                    for exp_date, strikes in list(calls.items())[:1]:  # First expiration
                        st.caption(f"Expiration: {exp_date}")
                        for strike, contracts in list(strikes.items())[:5]:  # First 5 strikes
                            c = contracts[0]
                            st.text(f"  {strike}: Bid ${c.get('bid', 0):.2f} / Ask ${c.get('ask', 0):.2f} | Δ={c.get('delta', 0):.3f}")
                
                with col2:
                    st.markdown("**PUTS**")
                    for exp_date, strikes in list(puts.items())[:1]:
                        st.caption(f"Expiration: {exp_date}")
                        for strike, contracts in list(strikes.items())[:5]:
                            c = contracts[0]
                            st.text(f"  {strike}: Bid ${c.get('bid', 0):.2f} / Ask ${c.get('ask', 0):.2f} | Δ={c.get('delta', 0):.3f}")
                
                with st.expander("📋 Full Response"):
                    st.json(data)

# -----------------------------------------------------------------------------
# Tab 3: Price History Test
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Test Price History Endpoint (30-min candles)")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        hist_symbol = st.text_input("Symbol", value="$SPX", key="hist_sym")
    with col2:
        st.write("")
        st.write("")
        fetch_hist = st.button("📥 Fetch History", type="primary")
    
    if fetch_hist:
        with st.spinner(f"Fetching {hist_symbol} price history..."):
            data = get_price_history(hist_symbol)
            if data:
                st.success(f"✅ Successfully fetched price history")
                
                candles = data.get('candles', [])
                st.metric("Candles Returned", len(candles))
                st.caption(f"Previous Close: ${data.get('previousClose', 'N/A'):,.2f}")
                
                # Show last 10 candles
                if candles:
                    st.markdown("**Last 10 Candles (30-min):**")
                    for candle in candles[-10:]:
                        dt = datetime.fromtimestamp(candle['datetime'] / 1000)
                        st.text(f"  {dt.strftime('%m/%d %H:%M')} | "
                               f"O:{candle['open']:,.2f} H:{candle['high']:,.2f} "
                               f"L:{candle['low']:,.2f} C:{candle['close']:,.2f}")
                
                with st.expander("📋 Full Response"):
                    st.json(data)

# -----------------------------------------------------------------------------
# Tab 4: Raw API Test
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("Raw API Request")
    st.caption("Test any Market Data endpoint directly")
    
    endpoint = st.text_input("Endpoint (after /marketdata/v1/)", value="quotes?symbols=$SPX,$VIX")
    
    if st.button("🚀 Send Request"):
        token = get_valid_token()
        if token:
            url = f"{API_BASE}/{endpoint}"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {token}"
            }
            
            with st.spinner("Sending request..."):
                try:
                    response = requests.get(url, headers=headers)
                    st.code(f"GET {url}", language=None)
                    st.metric("Status Code", response.status_code)
                    
                    if response.status_code == 200:
                        st.success("✅ Success")
                        st.json(response.json())
                    else:
                        st.error("❌ Error")
                        st.code(response.text)
                except Exception as e:
                    st.error(f"Request failed: {e}")

# =============================================================================
# Footer
# =============================================================================
st.divider()
st.caption("Schwab API Test App | Phase 1 of Market Prophet")

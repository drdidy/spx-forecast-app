"""
Polygon Options API Diagnostic Script
Run this locally to diagnose why options aren't loading
"""

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

def test_polygon_connection():
    print("=" * 60)
    print("POLYGON OPTIONS API DIAGNOSTIC")
    print("=" * 60)
    print()
    
    # Step 1: Check current time and trading day
    now = get_ct_now()
    next_trading = get_next_trading_day()
    print(f"1. TIMING CHECK")
    print(f"   Current CT time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   Weekday: {now.strftime('%A')}")
    print(f"   Next trading day: {next_trading.date()}")
    print(f"   Options expiry: {next_trading.strftime('%y%m%d')}")
    print()
    
    # Step 2: Get current SPX price
    print(f"2. FETCHING CURRENT SPX PRICE")
    try:
        url = f"{POLYGON_BASE_URL}/v3/snapshot?ticker.any_of=I:SPX"
        params = {"apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                spx_price = data["results"][0].get("value", 0)
                print(f"   SPX Price: {spx_price}")
            else:
                print(f"   No results returned")
                print(f"   Response: {data}")
                spx_price = 5950  # fallback
        else:
            print(f"   Error: {response.text}")
            spx_price = 5950
    except Exception as e:
        print(f"   Exception: {e}")
        spx_price = 5950
    print()
    
    # Step 3: Build option tickers
    print(f"3. BUILDING OPTION TICKERS")
    
    # Round to nearest 5
    atm_strike = int(round(spx_price / 5) * 5)
    call_strike = atm_strike + 20  # Slightly OTM call
    put_strike = atm_strike - 20   # Slightly OTM put
    
    call_ticker = build_option_ticker("SPX", next_trading, call_strike, "C")
    put_ticker = build_option_ticker("SPX", next_trading, put_strike, "P")
    
    print(f"   ATM Strike: {atm_strike}")
    print(f"   Call Strike: {call_strike} -> Ticker: {call_ticker}")
    print(f"   Put Strike: {put_strike} -> Ticker: {put_ticker}")
    print()
    
    # Step 4: Test each endpoint for the call
    print(f"4. TESTING CALL OPTION ENDPOINTS")
    print(f"   Ticker: {call_ticker}")
    print()
    
    # 4a: Quote endpoint
    print(f"   4a. Quote Endpoint (/v3/quotes)")
    try:
        url = f"{POLYGON_BASE_URL}/v3/quotes/{call_ticker}"
        params = {"limit": 1, "apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        print(f"       Status: {response.status_code}")
        data = response.json()
        if data.get("results") and len(data["results"]) > 0:
            result = data["results"][0]
            print(f"       Bid: {result.get('bid_price', 'N/A')}")
            print(f"       Ask: {result.get('ask_price', 'N/A')}")
        else:
            print(f"       No quotes returned")
            print(f"       Response: {data}")
    except Exception as e:
        print(f"       Exception: {e}")
    print()
    
    # 4b: Trades endpoint
    print(f"   4b. Trades Endpoint (/v3/trades)")
    try:
        url = f"{POLYGON_BASE_URL}/v3/trades/{call_ticker}"
        params = {"limit": 1, "apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        print(f"       Status: {response.status_code}")
        data = response.json()
        if data.get("results") and len(data["results"]) > 0:
            result = data["results"][0]
            print(f"       Last Trade Price: {result.get('price', 'N/A')}")
        else:
            print(f"       No trades returned")
            print(f"       Response: {data}")
    except Exception as e:
        print(f"       Exception: {e}")
    print()
    
    # 4c: Snapshot endpoint
    print(f"   4c. Snapshot Endpoint (/v3/snapshot/options)")
    try:
        url = f"{POLYGON_BASE_URL}/v3/snapshot/options/{call_ticker}"
        params = {"apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        print(f"       Status: {response.status_code}")
        data = response.json()
        if data.get("results"):
            result = data["results"]
            print(f"       Open Interest: {result.get('open_interest', 'N/A')}")
            print(f"       Implied Vol: {result.get('implied_volatility', 'N/A')}")
            greeks = result.get("greeks", {})
            print(f"       Delta: {greeks.get('delta', 'N/A')}")
        else:
            print(f"       No snapshot returned")
            print(f"       Response: {data}")
    except Exception as e:
        print(f"       Exception: {e}")
    print()
    
    # Step 5: Try SPY as fallback
    print(f"5. TESTING SPY FALLBACK")
    spy_strike = round(call_strike / 10)
    spy_ticker = build_option_ticker("SPY", next_trading, spy_strike, "C")
    print(f"   SPY Strike: {spy_strike} -> Ticker: {spy_ticker}")
    
    try:
        url = f"{POLYGON_BASE_URL}/v3/quotes/{spy_ticker}"
        params = {"limit": 1, "apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status: {response.status_code}")
        data = response.json()
        if data.get("results") and len(data["results"]) > 0:
            result = data["results"][0]
            print(f"   Bid: {result.get('bid_price', 'N/A')}")
            print(f"   Ask: {result.get('ask_price', 'N/A')}")
        else:
            print(f"   No quotes returned")
            print(f"   Response: {data}")
    except Exception as e:
        print(f"   Exception: {e}")
    print()
    
    # Step 6: Check API subscription
    print(f"6. CHECKING API SUBSCRIPTION")
    try:
        # Try to get account info or a simple endpoint
        url = f"{POLYGON_BASE_URL}/v3/reference/options/contracts/{call_ticker}"
        params = {"apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        print(f"   Contract lookup status: {response.status_code}")
        data = response.json()
        if data.get("results"):
            print(f"   Contract exists: Yes")
            print(f"   Expiration: {data['results'].get('expiration_date', 'N/A')}")
        else:
            print(f"   Contract info: {data}")
    except Exception as e:
        print(f"   Exception: {e}")
    print()
    
    print("=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
    print()
    print("COMMON ISSUES:")
    print("1. If Status 403: API key may not have options access")
    print("2. If Status 200 but no results: Options may not be trading yet")
    print("3. If contract doesn't exist: Check expiration date format")
    print("4. Free Polygon tier does NOT include real-time options")
    print()

if __name__ == "__main__":
    test_polygon_connection()
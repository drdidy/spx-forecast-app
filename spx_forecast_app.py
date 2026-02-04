# ═══════════════════════════════════════════════════════════════════════════════
# SPX PROPHET - STRUCTURAL 0DTE TRADING SYSTEM
# "Where Structure Becomes Foresight"
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import pytz
import json
import os
import math
from datetime import datetime, date, time, timedelta
from enum import Enum
from typing import Optional, Dict

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="SPX Prophet", page_icon="◭", layout="wide")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
CT = pytz.timezone("America/Chicago")
ET = pytz.timezone("America/New_York")
UTC = pytz.UTC

SLOPE = 0.52
SAVE_FILE = "spx_prophet_inputs.json"

POLYGON_API_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
POLYGON_BASE_URL = "https://api.polygon.io"

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════
class ChannelType(Enum):
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"
    MIXED = "MIXED"
    CONTRACTING = "CONTRACTING"
    UNDETERMINED = "UNDETERMINED"

class Position(Enum):
    ABOVE = "ABOVE"
    INSIDE = "INSIDE"
    BELOW = "BELOW"

class Bias(Enum):
    CALLS = "CALLS"
    PUTS = "PUTS"
    NEUTRAL = "NEUTRAL"

class VIXPosition(Enum):
    ABOVE_RANGE = "ABOVE"
    IN_RANGE = "IN RANGE"
    BELOW_RANGE = "BELOW"
    UNKNOWN = "UNKNOWN"

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════
def now_ct():
    return datetime.now(CT)

def blocks_between(start, end):
    """Calculate 30-minute blocks between two times.
    Used for intraday projections within the same trading session."""
    if start is None or end is None or end <= start:
        return 0
    return max(0, int((end - start).total_seconds() / 1800))

def trading_blocks_between(start_time, end_time):
    """Calculate trading blocks between two times for prior day projections.
    
    For cross-day calculations, we count:
    - Blocks from anchor time to that day's RTH close (3:00 PM CT)
    - Overnight blocks to the next trading day's reference time
    - Weekend is treated as one extended overnight session
    
    Key insight: The TRADING reference time matters, not the calendar date.
    If user picks Sunday or Monday, we project to MONDAY's reference time.
    """
    if start_time is None or end_time is None:
        return 0
    
    # Ensure both are timezone-aware
    if start_time.tzinfo is None or end_time.tzinfo is None:
        return blocks_between(start_time, end_time)
    
    start_date = start_time.date()
    end_date = end_time.date()
    
    # If same day, use simple calculation
    if start_date == end_date:
        return blocks_between(start_time, end_time)
    
    # Blocks from start_time to 3:00 PM CT (end of RTH) on start day
    start_day_close = start_time.replace(hour=15, minute=0, second=0, microsecond=0)
    if start_time < start_day_close:
        blocks_to_close = int((start_day_close - start_time).total_seconds() / 1800)
    else:
        blocks_to_close = 0
    
    # Blocks from 8:30 AM to end_time on final day
    end_day_open = end_time.replace(hour=8, minute=30, second=0, microsecond=0)
    if end_time >= end_day_open:
        blocks_from_open = int((end_time - end_day_open).total_seconds() / 1800)
    else:
        blocks_from_open = 0
    
    # Check if this crosses a weekend
    # Weekend crossing = start is Friday (4) or earlier, and end is Saturday (5), Sunday (6), or Monday (0)
    # OR start is Friday and there's a weekend between start and end
    start_weekday = start_date.weekday()
    end_weekday = end_date.weekday()
    
    # Count weekend days between start and end
    crosses_weekend = False
    current = start_date + timedelta(days=1)
    while current <= end_date:
        if current.weekday() in [5, 6]:  # Saturday or Sunday
            crosses_weekend = True
            break
        current += timedelta(days=1)
    
    # Also check if end_date itself is a weekend (user picked Sunday)
    if end_weekday in [5, 6]:
        crosses_weekend = True
    
    if crosses_weekend:
        # Weekend overnight: Friday 3PM → Monday 8:30AM = ~32 blocks for the overnight portion
        OVERNIGHT_WEEKEND_BLOCKS = 32
        total_blocks = blocks_to_close + OVERNIGHT_WEEKEND_BLOCKS + blocks_from_open
    else:
        # Regular overnight (weekday to weekday, no weekend)
        # Count trading days between
        trading_days_between = 0
        current = start_date + timedelta(days=1)
        while current < end_date:
            if current.weekday() < 5:
                trading_days_between += 1
            current += timedelta(days=1)
        
        BLOCKS_PER_FULL_DAY = 26
        OVERNIGHT_REGULAR_BLOCKS = 17
        
        blocks_middle_days = trading_days_between * BLOCKS_PER_FULL_DAY
        total_blocks = blocks_to_close + blocks_middle_days + OVERNIGHT_REGULAR_BLOCKS + blocks_from_open
    
    return max(0, total_blocks)

def save_inputs(data):
    try:
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

def load_inputs():
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def get_prior_trading_day(ref_date):
    prior = ref_date - timedelta(days=1)
    while prior.weekday() >= 5:
        prior -= timedelta(days=1)
    return prior

def get_actual_trading_day(selected_date):
    """If user selects a weekend, return the next Monday (actual trading day).
    Otherwise return the selected date."""
    if selected_date.weekday() == 5:  # Saturday
        return selected_date + timedelta(days=2)  # Monday
    elif selected_date.weekday() == 6:  # Sunday
        return selected_date + timedelta(days=1)  # Monday
    return selected_date
# ═══════════════════════════════════════════════════════════════════════════════
# BLACK-SCHOLES PRICING
# ═══════════════════════════════════════════════════════════════════════════════
def norm_cdf(x):
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p, sign = 0.3275911, 1 if x >= 0 else -1
    x = abs(x) / math.sqrt(2)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
    return 0.5 * (1.0 + sign * y)

def black_scholes(S, K, T, r, sigma, opt_type):
    if T <= 0:
        return max(0, S - K) if opt_type == "CALL" else max(0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if opt_type == "CALL":
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def estimate_0dte_premium(spot, strike, hours_to_expiry, vix, opt_type):
    """
    0DTE SPX premium estimation - calibrated to real market data.
    
    Includes PUT SKEW adjustment (puts are more expensive than calls).
    
    Calibrated against actual SPX 0DTE trades:
    CALLS (6980C):
    - 22 OTM @ 5.85hrs = $2.30
    - 3 OTM @ 5.58hrs = $7.50
    
    PUTS (6975P):
    - 18 OTM @ 6.5hrs = $8.60
    - 3 OTM @ 5.5hrs = $13.45
    
    Average error: ~15% for both calls and puts
    """
    # Calculate OTM/ITM distance
    if opt_type == "CALL":
        otm = max(0, strike - spot)
        itm = max(0, spot - strike)
    else:  # PUT
        otm = max(0, spot - strike)
        itm = max(0, strike - spot)
    
    # ATM base premium (scales with VIX)
    atm_base = 9.5 + (vix - 15) * 0.4
    
    # Time decay factor - non-linear, accelerates toward expiry
    if hours_to_expiry >= 5.5:
        time_factor = 1.0
    elif hours_to_expiry >= 5:
        time_factor = 0.85
    elif hours_to_expiry >= 4:
        time_factor = 0.65
    elif hours_to_expiry >= 3:
        time_factor = 0.48
    elif hours_to_expiry >= 2:
        time_factor = 0.32
    elif hours_to_expiry >= 1:
        time_factor = 0.18
    else:
        time_factor = 0.08
    
    # OTM decay with minimum floor (lottery ticket value)
    base_decay = math.exp(-otm / 11)
    min_floor = 2.0 * time_factor
    
    # Extrinsic value = max(exponential decay, floor)
    exp_premium = atm_base * time_factor * base_decay
    extrinsic = max(exp_premium, min_floor)
    
    # PUT SKEW: Puts are more expensive than calls due to crash protection demand
    # Skew increases with distance OTM (more hedging value for far OTM puts)
    # Near ATM: ~1.8x, Far OTM (20+): ~3.5x
    if opt_type == "PUT":
        skew = min(3.5, 1.8 + (otm / 20) * 1.5)
        extrinsic = extrinsic * skew
    
    # Total premium = extrinsic + intrinsic
    premium = extrinsic + itm
    
    return max(round(premium, 2), 0.05)

# ═══════════════════════════════════════════════════════════════════════════════
# REAL SPX OPTIONS PREMIUM - Polygon API
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=30, show_spinner=False)
def fetch_real_option_premium(strike, opt_type, trading_date):
    """
    Fetch REAL SPX 0DTE option premium from Polygon.
    
    Args:
        strike: Strike price (e.g., 6050)
        opt_type: "CALL" or "PUT"
        trading_date: The trading date (for 0DTE expiry)
    
    Returns:
        Dict with bid, ask, mid, last, delta (if available)
    """
    result = {
        "available": False,
        "bid": None,
        "ask": None,
        "mid": None,
        "last": None,
        "delta": None,
        "underlying_price": None,
        "ticker": None,
        "error": None
    }
    
    try:
        # SPX options ticker format: O:SPXW{YYMMDD}{C/P}{STRIKE}
        # Strike format: 8 digits, price * 1000, zero-padded
        # Example: Strike 6050 -> 06050000 (6050.000)
        date_str = trading_date.strftime("%y%m%d")
        opt_letter = "C" if opt_type == "CALL" else "P"
        
        # Strike with 3 implied decimal places, 8 digits total
        strike_int = int(strike * 1000)
        strike_str = f"{strike_int:08d}"
        
        # The ticker includes SPXW but we query using SPX as underlying
        ticker = f"O:SPXW{date_str}{opt_letter}{strike_str}"
        result["ticker"] = ticker
        
        # Method 1: Use the universal snapshot endpoint with just the ticker
        # This doesn't require specifying underlying
        url = f"{POLYGON_BASE_URL}/v3/snapshot?ticker.any_of={ticker}"
        params = {"apiKey": POLYGON_API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results") and len(data["results"]) > 0:
                r = data["results"][0]
                
                # Get quote data from session
                if r.get("session"):
                    session = r["session"]
                    result["last"] = session.get("close") or session.get("previous_close")
                
                # Get quote data
                if r.get("last_quote"):
                    q = r["last_quote"]
                    result["bid"] = q.get("bid")
                    result["ask"] = q.get("ask")
                    if result["bid"] and result["ask"]:
                        result["mid"] = round((result["bid"] + result["ask"]) / 2, 2)
                
                # Get last trade
                if r.get("last_trade"):
                    result["last"] = r["last_trade"].get("price")
                
                # Get Greeks
                if r.get("greeks"):
                    result["delta"] = r["greeks"].get("delta")
                
                # Get underlying price
                if r.get("underlying_asset"):
                    result["underlying_price"] = r["underlying_asset"].get("price")
                
                result["available"] = result["mid"] is not None or result["last"] is not None
                return result
        
        # Method 2: Try last trade endpoint directly
        url = f"{POLYGON_BASE_URL}/v2/last/trade/{ticker}"
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                result["last"] = data["results"].get("price") or data["results"].get("p")
                result["available"] = result["last"] is not None
                return result
        
        # Method 3: Try quotes endpoint
        url = f"{POLYGON_BASE_URL}/v3/quotes/{ticker}"
        params["limit"] = 1
        params["order"] = "desc"
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results") and len(data["results"]) > 0:
                q = data["results"][0]
                result["bid"] = q.get("bid_price")
                result["ask"] = q.get("ask_price")
                if result["bid"] and result["ask"]:
                    result["mid"] = round((result["bid"] + result["ask"]) / 2, 2)
                    result["available"] = True
                    return result
        
        result["error"] = f"No data found for {ticker}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def calculate_premium_at_entry(current_premium, current_spx, entry_spx, strike, opt_type, delta=None):
    """
    Calculate what an option premium will be when SPX reaches entry level.
    
    For CALLS at ascending floor:
    - SPX drops to floor → CALL premium DECREASES (cheaper entry!)
    
    For PUTS at descending ceiling:
    - SPX rises to ceiling → PUT premium DECREASES (cheaper entry!)
    
    Uses delta approximation: ΔPremium ≈ delta × ΔSPX
    
    Args:
        current_premium: Current option price
        current_spx: Current SPX price
        entry_spx: Entry level (floor for calls, ceiling for puts)
        strike: Option strike
        opt_type: "CALL" or "PUT"
        delta: Option delta (if available, otherwise estimate)
    
    Returns:
        Estimated premium at entry level
    """
    if current_premium is None or current_spx is None or entry_spx is None:
        return None
    
    spx_move = entry_spx - current_spx  # Negative if dropping to floor, positive if rising to ceiling
    
    # Estimate delta if not provided
    if delta is None:
        # Rough delta estimate based on moneyness
        if opt_type == "CALL":
            otm = strike - current_spx
            if otm <= 0:  # ITM
                delta = 0.60
            elif otm <= 10:
                delta = 0.45
            elif otm <= 20:
                delta = 0.30
            elif otm <= 30:
                delta = 0.20
            else:
                delta = 0.10
        else:  # PUT
            otm = current_spx - strike
            if otm <= 0:  # ITM
                delta = -0.60
            elif otm <= 10:
                delta = -0.45
            elif otm <= 20:
                delta = -0.30
            elif otm <= 30:
                delta = -0.20
            else:
                delta = -0.10
    
    # Premium change = delta × SPX move
    # For calls: if SPX drops (negative move), premium drops (delta positive)
    # For puts: if SPX rises (positive move), premium drops (delta negative)
    premium_change = delta * spx_move
    
    # New premium (with floor of $0.05)
    new_premium = max(0.05, current_premium + premium_change)
    
    return round(new_premium, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING - Yahoo Finance
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=60, show_spinner=False)
def fetch_es_current():
    try:
        es = yf.Ticker("ES=F")
        d = es.history(period="2d", interval="5m")
        if d is not None and not d.empty:
            return round(float(d['Close'].iloc[-1]), 2)
    except:
        pass
    return None

@st.cache_data(ttl=60, show_spinner=False)
def fetch_es_candles(days=7):
    try:
        es = yf.Ticker("ES=F")
        data = es.history(period=f"{days}d", interval="30m")
        if data is not None and not data.empty and len(data) > 10:
            return data
    except:
        pass
    return None

@st.cache_data(ttl=60, show_spinner=False)
def fetch_es_with_ema():
    """Fetch ES futures with EMAs based on 30-minute chart from Yahoo Finance."""
    result = {
        "price": None, "ema_200": None, "ema_8": None, "ema_21": None,
        "above_200": None, "ema_cross": None, "ema_bias": Bias.NEUTRAL
    }
    try:
        es = yf.Ticker("ES=F")
        # Use 30-minute chart - need ~15 trading days for 200 periods
        data = es.history(period="1mo", interval="30m")
        
        if data is not None and not data.empty and len(data) > 200:
            # Calculate EMAs on 30-minute closes
            data['EMA_8'] = data['Close'].ewm(span=8, adjust=False).mean()
            data['EMA_21'] = data['Close'].ewm(span=21, adjust=False).mean()
            data['EMA_200'] = data['Close'].ewm(span=200, adjust=False).mean()
            
            result["price"] = round(float(data['Close'].iloc[-1]), 2)
            result["ema_8"] = round(float(data['EMA_8'].iloc[-1]), 2)
            result["ema_21"] = round(float(data['EMA_21'].iloc[-1]), 2)
            result["ema_200"] = round(float(data['EMA_200'].iloc[-1]), 2)
            result["above_200"] = result["price"] > result["ema_200"]
            result["ema_cross"] = "BULLISH" if result["ema_8"] > result["ema_21"] else "BEARISH"
            
            if result["above_200"] and result["ema_cross"] == "BULLISH":
                result["ema_bias"] = Bias.CALLS
            elif not result["above_200"] and result["ema_cross"] == "BEARISH":
                result["ema_bias"] = Bias.PUTS
            else:
                result["ema_bias"] = Bias.NEUTRAL
    except:
        pass
    return result

@st.cache_data(ttl=60, show_spinner=False)
def fetch_vix_yahoo():
    try:
        vix = yf.Ticker("^VIX")
        data = vix.history(period="2d")
        if data is not None and not data.empty:
            return round(float(data['Close'].iloc[-1]), 2)
    except:
        pass
    return 16.0

# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING - Polygon API
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=60, show_spinner=False)
def fetch_vix_polygon():
    try:
        url = f"{POLYGON_BASE_URL}/v3/snapshot?ticker.any_of=I:VIX"
        params = {"apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("results") and len(data["results"]) > 0:
                return round(float(data["results"][0].get("value", 0)), 2)
    except:
        pass
    return None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_vix_overnight_range(trading_date, zone_start_hour=2, zone_start_min=0, zone_end_hour=5, zone_end_min=30):
    result = {"bottom": None, "top": None, "range_size": None, "available": False}
    try:
        date_str = trading_date.strftime("%Y-%m-%d")
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/I:VIX/range/1/minute/{date_str}/{date_str}"
        params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("results") and len(data["results"]) > 0:
                df = pd.DataFrame(data["results"])
                df['datetime'] = pd.to_datetime(df['t'], unit='ms', utc=True).dt.tz_convert(CT)
                zone_start = CT.localize(datetime.combine(trading_date, time(zone_start_hour, zone_start_min)))
                zone_end = CT.localize(datetime.combine(trading_date, time(zone_end_hour, zone_end_min)))
                zone_df = df[(df['datetime'] >= zone_start) & (df['datetime'] <= zone_end)]
                if not zone_df.empty and len(zone_df) > 5:
                    result["bottom"] = round(float(zone_df['l'].min()), 2)
                    result["top"] = round(float(zone_df['h'].max()), 2)
                    result["range_size"] = round(result["top"] - result["bottom"], 2)
                    result["available"] = True
    except:
        pass
    return result

def get_vix_position(current_vix, vix_range):
    if not vix_range["available"] or current_vix is None:
        return VIXPosition.UNKNOWN, "No range data"
    bottom, top = vix_range["bottom"], vix_range["top"]
    if current_vix > top:
        return VIXPosition.ABOVE_RANGE, f"{round(current_vix - top, 1)} above"
    elif current_vix < bottom:
        return VIXPosition.BELOW_RANGE, f"{round(bottom - current_vix, 1)} below"
    else:
        return VIXPosition.IN_RANGE, f"Within {bottom}-{top}"

# ═══════════════════════════════════════════════════════════════════════════════
# VIX TERM STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def fetch_vix_term_structure():
    """
    Fetch VIX term structure (VIX vs VIX futures).
    Contango (normal): VIX futures > VIX spot → stable/bullish
    Backwardation (fear): VIX spot > VIX futures → volatile/bearish
    """
    result = {"vix_spot": None, "vix_future": None, "structure": "UNKNOWN", "spread": None}
    try:
        # VIX spot
        vix = yf.Ticker("^VIX")
        vix_data = vix.history(period="2d")
        
        # VIX 3-month (proxy for futures)
        vix3m = yf.Ticker("^VIX3M")
        vix3m_data = vix3m.history(period="2d")
        
        if not vix_data.empty and not vix3m_data.empty:
            spot = round(float(vix_data['Close'].iloc[-1]), 2)
            future = round(float(vix3m_data['Close'].iloc[-1]), 2)
            spread = round(future - spot, 2)  # Positive = contango, Negative = backwardation
            
            result["vix_spot"] = spot
            result["vix_future"] = future
            result["spread"] = spread
            
            if spread > 1.5:
                result["structure"] = "CONTANGO"  # Normal, stable
            elif spread < -1.5:
                result["structure"] = "BACKWARDATION"  # Fear, volatile
            else:
                result["structure"] = "FLAT"  # Neutral
    except:
        pass
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# RETAIL POSITIONING
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def fetch_retail_positioning():
    result = {"vix": None, "vix3m": None, "spread": None, "positioning": "BALANCED", "warning": None, "bias": Bias.NEUTRAL}
    try:
        vix_data = yf.Ticker("^VIX").history(period="2d")
        vix3m_data = yf.Ticker("^VIX3M").history(period="2d")
        if not vix_data.empty and not vix3m_data.empty:
            vix = round(float(vix_data['Close'].iloc[-1]), 2)
            vix3m = round(float(vix3m_data['Close'].iloc[-1]), 2)
            spread = round(vix - vix3m, 2)
            result["vix"], result["vix3m"], result["spread"] = vix, vix3m, spread
            if spread <= -3.0:
                result["positioning"], result["warning"], result["bias"] = "CALL BUYING EXTREME", "Extreme complacency - high fade probability", Bias.PUTS
            elif spread <= -1.5:
                result["positioning"], result["warning"], result["bias"] = "CALL BUYING HEAVY", "Market often fades the crowd", Bias.PUTS
            elif spread >= 3.0:
                result["positioning"], result["warning"], result["bias"] = "PUT BUYING EXTREME", "Extreme fear - high fade probability", Bias.CALLS
            elif spread >= 1.5:
                result["positioning"], result["warning"], result["bias"] = "PUT BUYING HEAVY", "Market often fades the crowd", Bias.CALLS
    except:
        pass
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION LEVEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════
def analyze_session_tests(sydney, tokyo, london, channel_type):
    """
    Analyze how many sessions tested and respected the key levels.
    More session tests = stronger level confirmation.
    
    Returns dict with floor_tests, ceiling_tests, and which sessions tested each.
    """
    result = {
        "floor_tests": 0,
        "ceiling_tests": 0,
        "floor_sessions": [],
        "ceiling_sessions": [],
        "floor_respected": True,
        "ceiling_respected": True
    }
    
    if not sydney or not tokyo:
        return result
    
    # Determine the key level bounds based on Sydney (baseline)
    sydney_high = sydney["high"]
    sydney_low = sydney["low"]
    tolerance = 2.0  # Points tolerance for "testing" a level
    
    # Check Tokyo
    if tokyo:
        # Did Tokyo test Sydney's low (floor area)?
        if tokyo["low"] <= sydney_low + tolerance:
            result["floor_tests"] += 1
            result["floor_sessions"].append("Tokyo")
            # Did it respect (close above)?
            # We approximate by checking if high recovered
            if tokyo["high"] > sydney_low + 5:
                pass  # Respected
            else:
                result["floor_respected"] = False
        
        # Did Tokyo test Sydney's high (ceiling area)?
        if tokyo["high"] >= sydney_high - tolerance:
            result["ceiling_tests"] += 1
            result["ceiling_sessions"].append("Tokyo")
    
    # Check London
    if london:
        current_low = min(sydney_low, tokyo["low"]) if tokyo else sydney_low
        current_high = max(sydney_high, tokyo["high"]) if tokyo else sydney_high
        
        # Did London test the floor?
        if london["low"] <= current_low + tolerance:
            result["floor_tests"] += 1
            result["floor_sessions"].append("London")
        
        # Did London test the ceiling?
        if london["high"] >= current_high - tolerance:
            result["ceiling_tests"] += 1
            result["ceiling_sessions"].append("London")
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# GAP ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
def analyze_gap(current_price, prior_close, ceiling, floor):
    """
    Analyze the gap relative to the overnight channel.
    
    Returns:
    - gap_direction: UP, DOWN, or FLAT
    - gap_size: Size in points
    - gap_position: Where the gap puts us relative to channel
    - gap_into_level: True if gap brings us TO a key level (good setup)
    """
    result = {
        "direction": "FLAT",
        "size": 0,
        "into_floor": False,
        "into_ceiling": False,
        "away_from_floor": False,
        "away_from_ceiling": False
    }
    
    if prior_close is None or current_price is None:
        return result
    
    gap = current_price - prior_close
    result["size"] = round(abs(gap), 1)
    
    if gap > 3:
        result["direction"] = "UP"
    elif gap < -3:
        result["direction"] = "DOWN"
    else:
        result["direction"] = "FLAT"
    
    channel_range = ceiling - floor
    dist_to_floor = current_price - floor
    dist_to_ceiling = ceiling - current_price
    
    # Check if gap brings us TO a key level
    if result["direction"] == "DOWN" and dist_to_floor <= channel_range * 0.3:
        result["into_floor"] = True
    elif result["direction"] == "UP" and dist_to_ceiling <= channel_range * 0.3:
        result["into_ceiling"] = True
    
    # Check if gap takes us AWAY from a level
    if result["direction"] == "UP" and dist_to_floor > channel_range * 0.5:
        result["away_from_floor"] = True
    elif result["direction"] == "DOWN" and dist_to_ceiling > channel_range * 0.5:
        result["away_from_ceiling"] = True
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# PRIOR CLOSE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
def analyze_prior_close(prior_close, ceiling, floor):
    """
    Analyze where prior RTH closed relative to today's overnight channel.
    
    If prior close is near today's floor → floor is validated
    If prior close is near today's ceiling → ceiling is validated
    """
    result = {
        "validates_floor": False,
        "validates_ceiling": False,
        "position": "MIDDLE"
    }
    
    if prior_close is None or ceiling is None or floor is None:
        return result
    
    channel_range = ceiling - floor
    dist_to_floor = prior_close - floor
    dist_to_ceiling = ceiling - prior_close
    
    if dist_to_floor <= channel_range * 0.3:
        result["validates_floor"] = True
        result["position"] = "NEAR_FLOOR"
    elif dist_to_ceiling <= channel_range * 0.3:
        result["validates_ceiling"] = True
        result["position"] = "NEAR_CEILING"
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# PRIOR DAY RTH DATA
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_prior_day_rth(trading_date):
    """Fetch prior day's RTH (Regular Trading Hours) data for ES futures using Yahoo Finance.
    RTH is 8:30 AM - 3:00 PM CT (9:30 AM - 4:00 PM ET)
    
    Returns:
    - primary_high_wick: The highest high (wick) of any RTH candle
    - secondary_high_wick: Lower high wick made AFTER primary (1hr+ gap), or None
    - primary_low_open: The lowest open of any BULLISH RTH candle (buyers defended)
    - secondary_low_open: Higher low open made AFTER primary (1hr+ gap, bullish), or None
    """
    result = {
        "primary_high_wick": None, "primary_high_wick_time": None,
        "secondary_high_wick": None, "secondary_high_wick_time": None,
        "primary_low_open": None, "primary_low_open_time": None,
        "secondary_low_open": None, "secondary_low_open_time": None,
        "high": None, "low": None, "close": None,
        "available": False,
        # Legacy keys for backward compatibility
        "highest_wick": None, "highest_wick_time": None,
        "lowest_close": None, "lowest_close_time": None,
    }
    try:
        prior_day = get_prior_trading_day(trading_date)
        
        # Fetch 30-minute candles for ES futures from Yahoo (matches our trading blocks)
        es = yf.Ticker("ES=F")
        # Get 5 days of data to ensure we have the prior day
        df = es.history(period="5d", interval="30m")
        
        if df is not None and not df.empty:
            # Convert index to CT timezone
            if df.index.tz is None:
                df.index = df.index.tz_localize('America/New_York').tz_convert(CT)
            else:
                df.index = df.index.tz_convert(CT)
            
            # RTH hours: 8:30 AM - 3:00 PM CT
            rth_start = CT.localize(datetime.combine(prior_day, time(8, 30)))
            rth_end = CT.localize(datetime.combine(prior_day, time(15, 0)))
            
            # Filter to prior day RTH
            rth_df = df[(df.index >= rth_start) & (df.index <= rth_end)].copy()
            
            if not rth_df.empty and len(rth_df) > 3:
                # ─────────────────────────────────────────────────────────────
                # PRIMARY HIGH WICK: Highest high of any candle
                # ─────────────────────────────────────────────────────────────
                primary_high_idx = rth_df['High'].idxmax()
                result["primary_high_wick"] = round(float(rth_df.loc[primary_high_idx, 'High']), 2)
                result["primary_high_wick_time"] = primary_high_idx
                
                # ─────────────────────────────────────────────────────────────
                # SECONDARY HIGH WICK: Lower high made 1hr+ after primary
                # ─────────────────────────────────────────────────────────────
                min_gap = timedelta(hours=1)
                secondary_high_search = rth_df[rth_df.index >= primary_high_idx + min_gap]
                if not secondary_high_search.empty:
                    # Find highest wick after primary (must be lower than primary)
                    secondary_high_candidates = secondary_high_search[
                        secondary_high_search['High'] < result["primary_high_wick"]
                    ]
                    if not secondary_high_candidates.empty:
                        sec_high_idx = secondary_high_candidates['High'].idxmax()
                        result["secondary_high_wick"] = round(float(secondary_high_candidates.loc[sec_high_idx, 'High']), 2)
                        result["secondary_high_wick_time"] = sec_high_idx
                
                # ─────────────────────────────────────────────────────────────
                # PRIMARY LOW OPEN: Lowest open of any BULLISH candle
                # Bullish = Close > Open (buyers stepped in and defended)
                # ─────────────────────────────────────────────────────────────
                bullish_candles = rth_df[rth_df['Close'] > rth_df['Open']]
                if not bullish_candles.empty:
                    primary_low_idx = bullish_candles['Open'].idxmin()
                    result["primary_low_open"] = round(float(bullish_candles.loc[primary_low_idx, 'Open']), 2)
                    result["primary_low_open_time"] = primary_low_idx
                    
                    # ─────────────────────────────────────────────────────────
                    # SECONDARY LOW OPEN: Higher low open made 1hr+ after primary (bullish)
                    # ─────────────────────────────────────────────────────────
                    secondary_low_search = bullish_candles[bullish_candles.index >= primary_low_idx + min_gap]
                    if not secondary_low_search.empty:
                        # Find lowest open after primary (must be higher than primary)
                        secondary_low_candidates = secondary_low_search[
                            secondary_low_search['Open'] > result["primary_low_open"]
                        ]
                        if not secondary_low_candidates.empty:
                            sec_low_idx = secondary_low_candidates['Open'].idxmin()
                            result["secondary_low_open"] = round(float(secondary_low_candidates.loc[sec_low_idx, 'Open']), 2)
                            result["secondary_low_open_time"] = sec_low_idx
                
                # Also store overall H/L/C for display
                result["high"] = result["primary_high_wick"]
                result["low"] = round(float(rth_df['Low'].min()), 2)
                result["close"] = round(float(rth_df.iloc[-1]['Close']), 2)
                result["available"] = True
                
                # Legacy keys for backward compatibility
                result["highest_wick"] = result["primary_high_wick"]
                result["highest_wick_time"] = result["primary_high_wick_time"]
                result["lowest_close"] = result["primary_low_open"]  # Now uses low open
                result["lowest_close_time"] = result["primary_low_open_time"]
                
    except Exception as e:
        pass
    return result

def calc_prior_day_targets(prior_rth, ref_time):
    """Calculate BOTH ascending and descending targets from ALL prior day anchors.
    
    From PRIMARY HIGH WICK:
    - Ascending line (+0.52/30min) = Resistance (SELL point)
    - Descending line (-0.52/30min) = Support (BUY point)
    
    From SECONDARY HIGH WICK (if exists):
    - Ascending line (+0.52/30min) = Resistance (SELL point)
    - Descending line (-0.52/30min) = Support (BUY point)
    
    From PRIMARY LOW OPEN:
    - Ascending line (+0.52/30min) = Support (BUY point)
    - Descending line (-0.52/30min) = Resistance (SELL point)
    
    From SECONDARY LOW OPEN (if exists):
    - Ascending line (+0.52/30min) = Support (BUY point)
    - Descending line (-0.52/30min) = Resistance (SELL point)
    
    Returns dict with all eight targets (4 pivots x 2 directions).
    """
    result = {
        "available": False,
        # Primary High Wick
        "primary_high_wick": None,
        "primary_high_wick_time": None,
        "primary_high_wick_ascending": None,
        "primary_high_wick_descending": None,
        # Secondary High Wick
        "secondary_high_wick": None,
        "secondary_high_wick_time": None,
        "secondary_high_wick_ascending": None,
        "secondary_high_wick_descending": None,
        # Primary Low Open
        "primary_low_open": None,
        "primary_low_open_time": None,
        "primary_low_open_ascending": None,
        "primary_low_open_descending": None,
        # Secondary Low Open
        "secondary_low_open": None,
        "secondary_low_open_time": None,
        "secondary_low_open_ascending": None,
        "secondary_low_open_descending": None,
        # Legacy keys for backward compatibility
        "highest_wick": None,
        "highest_wick_ascending": None,
        "highest_wick_descending": None,
        "lowest_close": None,
        "lowest_close_ascending": None,
        "lowest_close_descending": None,
    }
    
    if not prior_rth.get("available"):
        return result
    
    result["available"] = True
    
    # ─────────────────────────────────────────────────────────────────────────
    # PRIMARY HIGH WICK
    # ─────────────────────────────────────────────────────────────────────────
    if prior_rth.get("primary_high_wick") is not None and prior_rth.get("primary_high_wick_time"):
        result["primary_high_wick"] = prior_rth["primary_high_wick"]
        result["primary_high_wick_time"] = prior_rth["primary_high_wick_time"]
        blocks = trading_blocks_between(prior_rth["primary_high_wick_time"], ref_time)
        result["primary_high_wick_ascending"] = round(prior_rth["primary_high_wick"] + SLOPE * blocks, 2)
        result["primary_high_wick_descending"] = round(prior_rth["primary_high_wick"] - SLOPE * blocks, 2)
        # Legacy
        result["highest_wick"] = result["primary_high_wick"]
        result["highest_wick_ascending"] = result["primary_high_wick_ascending"]
        result["highest_wick_descending"] = result["primary_high_wick_descending"]
    
    # ─────────────────────────────────────────────────────────────────────────
    # SECONDARY HIGH WICK
    # ─────────────────────────────────────────────────────────────────────────
    if prior_rth.get("secondary_high_wick") is not None and prior_rth.get("secondary_high_wick_time"):
        result["secondary_high_wick"] = prior_rth["secondary_high_wick"]
        result["secondary_high_wick_time"] = prior_rth["secondary_high_wick_time"]
        blocks = trading_blocks_between(prior_rth["secondary_high_wick_time"], ref_time)
        result["secondary_high_wick_ascending"] = round(prior_rth["secondary_high_wick"] + SLOPE * blocks, 2)
        result["secondary_high_wick_descending"] = round(prior_rth["secondary_high_wick"] - SLOPE * blocks, 2)
    
    # ─────────────────────────────────────────────────────────────────────────
    # PRIMARY LOW OPEN
    # ─────────────────────────────────────────────────────────────────────────
    if prior_rth.get("primary_low_open") is not None and prior_rth.get("primary_low_open_time"):
        result["primary_low_open"] = prior_rth["primary_low_open"]
        result["primary_low_open_time"] = prior_rth["primary_low_open_time"]
        blocks = trading_blocks_between(prior_rth["primary_low_open_time"], ref_time)
        result["primary_low_open_ascending"] = round(prior_rth["primary_low_open"] + SLOPE * blocks, 2)
        result["primary_low_open_descending"] = round(prior_rth["primary_low_open"] - SLOPE * blocks, 2)
        # Legacy
        result["lowest_close"] = result["primary_low_open"]
        result["lowest_close_ascending"] = result["primary_low_open_ascending"]
        result["lowest_close_descending"] = result["primary_low_open_descending"]
    
    # ─────────────────────────────────────────────────────────────────────────
    # SECONDARY LOW OPEN
    # ─────────────────────────────────────────────────────────────────────────
    if prior_rth.get("secondary_low_open") is not None and prior_rth.get("secondary_low_open_time"):
        result["secondary_low_open"] = prior_rth["secondary_low_open"]
        result["secondary_low_open_time"] = prior_rth["secondary_low_open_time"]
        blocks = trading_blocks_between(prior_rth["secondary_low_open_time"], ref_time)
        result["secondary_low_open_ascending"] = round(prior_rth["secondary_low_open"] + SLOPE * blocks, 2)
        result["secondary_low_open_descending"] = round(prior_rth["secondary_low_open"] - SLOPE * blocks, 2)
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════
def extract_sessions(es_candles, trading_date):
    if es_candles is None or es_candles.empty:
        return None
    result = {}
    overnight_day = get_prior_trading_day(trading_date)
    df = es_candles.copy()
    if df.index.tz is None:
        df.index = df.index.tz_localize(ET).tz_convert(CT)
    else:
        df.index = df.index.tz_convert(CT)
    
    sessions = {
        "sydney": (CT.localize(datetime.combine(overnight_day, time(17, 0))),
                   CT.localize(datetime.combine(overnight_day, time(20, 30)))),
        "tokyo": (CT.localize(datetime.combine(overnight_day, time(21, 0))),
                  CT.localize(datetime.combine(trading_date, time(1, 30)))),
        "london": (CT.localize(datetime.combine(trading_date, time(2, 0))),
                   CT.localize(datetime.combine(trading_date, time(5, 30)))),  # London ends at 5:30 AM CT
        "overnight": (CT.localize(datetime.combine(overnight_day, time(17, 0))),
                      CT.localize(datetime.combine(trading_date, time(8, 30))))
    }
    
    for name, (start, end) in sessions.items():
        mask = (df.index >= start) & (df.index <= end)
        data = df[mask]
        if not data.empty:
            result[name] = {
                "high": round(data['High'].max(), 2),
                "low": round(data['Low'].min(), 2),
                "high_time": data['High'].idxmax(),
                "low_time": data['Low'].idxmin()
            }
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# CHANNEL LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
def determine_channel(sydney, tokyo, london=None):
    """
    Determine channel type by comparing Asian Session vs European Session.
    
    The overnight session is viewed as ONE structure:
    - Asian Session = Sydney + Tokyo combined (their combined high/low)
    - European Session = London
    
    ASCENDING: London made higher highs AND/OR higher lows vs Asian
    DESCENDING: London made lower highs AND/OR lower lows vs Asian
    MIXED: Conflicting signals (higher high + lower low, or vice versa)
    CONTRACTING: London stayed inside Asian range
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # FALLBACK: No Sydney but have Tokyo + London → Tokyo = Asian, London = European
    # ─────────────────────────────────────────────────────────────────────────
    if not sydney and tokyo and london:
        asian_high = tokyo["high"]
        asian_low = tokyo["low"]
        asian_high_time = tokyo.get("high_time")
        asian_low_time = tokyo.get("low_time")
        
        # Use the overall high/low for pivot points
        true_high = max(asian_high, london["high"])
        true_low = min(asian_low, london["low"])
        high_time = asian_high_time if asian_high >= london["high"] else london.get("high_time")
        low_time = asian_low_time if asian_low <= london["low"] else london.get("low_time")
        
        # Compare London vs Tokyo (Asian)
        london_higher_high = london["high"] > asian_high
        london_higher_low = london["low"] > asian_low
        london_lower_high = london["high"] < asian_high
        london_lower_low = london["low"] < asian_low
        
        return _determine_channel_from_comparison(
            asian_high, asian_low, london["high"], london["low"],
            london_higher_high, london_higher_low, london_lower_high, london_lower_low,
            true_high, true_low, high_time, low_time, "Tokyo", "London"
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # NORMAL CASE: Need at least Sydney + Tokyo for Asian session
    # ─────────────────────────────────────────────────────────────────────────
    if not sydney or not tokyo:
        return ChannelType.UNDETERMINED, "Missing session data (need Sydney+Tokyo or Tokyo+London)", None, None, None, None
    
    # ─────────────────────────────────────────────────────────────────────────
    # ASIAN SESSION: Combine Sydney + Tokyo into one session
    # ─────────────────────────────────────────────────────────────────────────
    asian_high = max(sydney["high"], tokyo["high"])
    asian_low = min(sydney["low"], tokyo["low"])
    
    # Track which session made the high/low for time reference
    if sydney["high"] >= tokyo["high"]:
        asian_high_time = sydney.get("high_time")
    else:
        asian_high_time = tokyo.get("high_time")
    
    if sydney["low"] <= tokyo["low"]:
        asian_low_time = sydney.get("low_time")
    else:
        asian_low_time = tokyo.get("low_time")
    
    # ─────────────────────────────────────────────────────────────────────────
    # NO LONDON: Can only use Asian session data
    # ─────────────────────────────────────────────────────────────────────────
    if not london:
        # Without London, compare Sydney vs Tokyo within Asian session
        tokyo_higher_high = tokyo["high"] > sydney["high"]
        tokyo_higher_low = tokyo["low"] > sydney["low"]
        tokyo_lower_high = tokyo["high"] < sydney["high"]
        tokyo_lower_low = tokyo["low"] < sydney["low"]
        
        if tokyo_higher_high and tokyo_higher_low:
            return ChannelType.ASCENDING, f"Asian: Tokyo higher H/L vs Sydney", asian_high, asian_low, asian_high_time, asian_low_time
        elif tokyo_lower_high and tokyo_lower_low:
            return ChannelType.DESCENDING, f"Asian: Tokyo lower H/L vs Sydney", asian_high, asian_low, asian_high_time, asian_low_time
        elif tokyo_higher_high and tokyo_lower_low:
            return ChannelType.MIXED, f"Asian: Tokyo expanded both ways", asian_high, asian_low, asian_high_time, asian_low_time
        elif tokyo_lower_high and tokyo_higher_low:
            return ChannelType.CONTRACTING, f"Asian: Tokyo contracted vs Sydney", asian_high, asian_low, asian_high_time, asian_low_time
        elif tokyo_higher_high or tokyo_higher_low:
            return ChannelType.ASCENDING, f"Asian: Tokyo higher {'high' if tokyo_higher_high else 'low'}", asian_high, asian_low, asian_high_time, asian_low_time
        elif tokyo_lower_high or tokyo_lower_low:
            return ChannelType.DESCENDING, f"Asian: Tokyo lower {'high' if tokyo_lower_high else 'low'}", asian_high, asian_low, asian_high_time, asian_low_time
        else:
            return ChannelType.CONTRACTING, "Asian: No clear direction", asian_high, asian_low, asian_high_time, asian_low_time
    
    # ─────────────────────────────────────────────────────────────────────────
    # WITH LONDON: Compare European (London) vs Asian (Sydney+Tokyo)
    # This is the PRIMARY determination method
    # ─────────────────────────────────────────────────────────────────────────
    
    # Overall high/low for pivot points
    true_high = max(asian_high, london["high"])
    true_low = min(asian_low, london["low"])
    high_time = asian_high_time if asian_high >= london["high"] else london.get("high_time")
    low_time = asian_low_time if asian_low <= london["low"] else london.get("low_time")
    
    # Compare London vs Asian session
    london_higher_high = london["high"] > asian_high
    london_higher_low = london["low"] > asian_low
    london_lower_high = london["high"] < asian_high
    london_lower_low = london["low"] < asian_low
    
    return _determine_channel_from_comparison(
        asian_high, asian_low, london["high"], london["low"],
        london_higher_high, london_higher_low, london_lower_high, london_lower_low,
        true_high, true_low, high_time, low_time, "Asian", "London"
    )


def _determine_channel_from_comparison(asian_high, asian_low, london_high, london_low,
                                        higher_high, higher_low, lower_high, lower_low,
                                        true_high, true_low, high_time, low_time,
                                        asian_name, london_name):
    """
    Helper function to determine channel type from session comparison.
    
    ASCENDING: Higher highs AND higher lows (or just higher lows - key signal)
    DESCENDING: Lower highs AND lower lows (or just lower highs - key signal)
    MIXED: Conflicting signals
    CONTRACTING: London inside Asian range
    """
    
    # Calculate the differences for display
    high_diff = london_high - asian_high
    low_diff = london_low - asian_low
    
    # ─────────────────────────────────────────────────────────────────────────
    # CLEAR PATTERNS (both high and low agree)
    # ─────────────────────────────────────────────────────────────────────────
    if higher_high and higher_low:
        # Clear ASCENDING: Both high and low are higher
        reason = f"{london_name} > {asian_name}: Higher H (+{high_diff:.1f}) & Higher L (+{low_diff:.1f})"
        return ChannelType.ASCENDING, reason, true_high, true_low, high_time, low_time
    
    if lower_high and lower_low:
        # Clear DESCENDING: Both high and low are lower
        reason = f"{london_name} < {asian_name}: Lower H ({high_diff:.1f}) & Lower L ({low_diff:.1f})"
        return ChannelType.DESCENDING, reason, true_high, true_low, high_time, low_time
    
    # ─────────────────────────────────────────────────────────────────────────
    # MIXED PATTERNS (high and low conflict)
    # ─────────────────────────────────────────────────────────────────────────
    if higher_high and lower_low:
        # Expanded both ways - MIXED
        reason = f"{london_name} expanded: Higher H (+{high_diff:.1f}) but Lower L ({low_diff:.1f})"
        return ChannelType.MIXED, reason, true_high, true_low, high_time, low_time
    
    if lower_high and higher_low:
        # Contracted range - determine bias by MAGNITUDE of moves
        # Whichever move is larger determines the bias
        high_move = abs(high_diff)  # How much lower the high is
        low_move = abs(low_diff)    # How much higher the low is
        
        if low_move > high_move * 2:
            # Higher low is significantly larger - ASCENDING bias
            # Buyers are strongly defending, slight lower high doesn't matter
            reason = f"{london_name}: Higher L (+{low_diff:.1f}) dominates Lower H ({high_diff:.1f}) → Ascending"
            return ChannelType.ASCENDING, reason, true_high, true_low, high_time, low_time
        elif high_move > low_move * 2:
            # Lower high is significantly larger - DESCENDING bias
            reason = f"{london_name}: Lower H ({high_diff:.1f}) dominates Higher L (+{low_diff:.1f}) → Descending"
            return ChannelType.DESCENDING, reason, true_high, true_low, high_time, low_time
        else:
            # Moves are similar magnitude - MIXED (no clear direction)
            reason = f"{london_name} contracted: Lower H ({high_diff:.1f}), Higher L (+{low_diff:.1f}) → Mixed"
            return ChannelType.MIXED, reason, true_high, true_low, high_time, low_time
    
    # ─────────────────────────────────────────────────────────────────────────
    # SINGLE SIGNAL PATTERNS (only one of high/low moved)
    # ─────────────────────────────────────────────────────────────────────────
    if higher_high and not lower_low and not higher_low:
        # Only higher high - ASCENDING
        reason = f"{london_name}: Higher H (+{high_diff:.1f}), L unchanged"
        return ChannelType.ASCENDING, reason, true_high, true_low, high_time, low_time
    
    if higher_low and not lower_high and not higher_high:
        # Only higher low - ASCENDING (buyers defending)
        reason = f"{london_name}: Higher L (+{low_diff:.1f}), H unchanged"
        return ChannelType.ASCENDING, reason, true_high, true_low, high_time, low_time
    
    if lower_high and not higher_low and not lower_low:
        # Only lower high - DESCENDING (sellers defending)
        reason = f"{london_name}: Lower H ({high_diff:.1f}), L unchanged"
        return ChannelType.DESCENDING, reason, true_high, true_low, high_time, low_time
    
    if lower_low and not higher_high and not lower_high:
        # Only lower low - DESCENDING
        reason = f"{london_name}: Lower L ({low_diff:.1f}), H unchanged"
        return ChannelType.DESCENDING, reason, true_high, true_low, high_time, low_time
    
    # ─────────────────────────────────────────────────────────────────────────
    # NO MOVEMENT (London = Asian range)
    # ─────────────────────────────────────────────────────────────────────────
    reason = f"{london_name} = {asian_name} range (no expansion)"
    return ChannelType.CONTRACTING, reason, true_high, true_low, high_time, low_time


def validate_and_adjust_pivots(channel_type, upper_pivot, lower_pivot, upper_time, lower_time, 
                                sessions_data, ref_time):
    """
    Validate that no price broke through the projected channel lines during building phase.
    If price broke through, adjust the pivot to the new extreme BUT ALSO TRACK THE ORIGINAL.
    
    Rule: No price can exist outside the channel before 5:30 AM lock.
    - If price broke BELOW ascending floor line → new lower_pivot = that low
    - If price broke ABOVE descending ceiling line → new upper_pivot = that high
    
    IMPORTANT: We track BOTH because the market often respects the ORIGINAL level
    even after an overnight "break" (like today's Sydney floor example).
    
    Args:
        channel_type: ASCENDING, DESCENDING, MIXED, etc.
        upper_pivot, lower_pivot: Current pivot prices
        upper_time, lower_time: When pivots were made
        sessions_data: Dict with sydney, tokyo, london session data
        ref_time: Reference time for projection
    
    Returns:
        Dict with both original and adjusted pivots:
        {
            "upper_pivot": adjusted_upper,
            "lower_pivot": adjusted_lower,
            "upper_time": adjusted_upper_time,
            "lower_time": adjusted_lower_time,
            "original_upper_pivot": original_upper,
            "original_lower_pivot": original_lower,
            "original_upper_time": original_upper_time,
            "original_lower_time": original_lower_time,
            "floor_was_adjusted": bool,
            "ceiling_was_adjusted": bool,
            "adjustment_session": which session caused the adjustment
        }
    """
    
    result = {
        "upper_pivot": upper_pivot,
        "lower_pivot": lower_pivot,
        "upper_time": upper_time,
        "lower_time": lower_time,
        "original_upper_pivot": upper_pivot,
        "original_lower_pivot": lower_pivot,
        "original_upper_time": upper_time,
        "original_lower_time": lower_time,
        "floor_was_adjusted": False,
        "ceiling_was_adjusted": False,
        "floor_adjustment_session": None,
        "ceiling_adjustment_session": None,
    }
    
    if not sessions_data or channel_type in [ChannelType.UNDETERMINED, ChannelType.CONTRACTING]:
        return result
    
    # Collect all session lows and highs with their times
    all_lows = []
    all_highs = []
    
    for session_name in ["sydney", "tokyo", "london"]:
        session = sessions_data.get(session_name)
        if session:
            all_lows.append((session["low"], session.get("low_time"), session_name))
            all_highs.append((session["high"], session.get("high_time"), session_name))
    
    adjusted_lower = lower_pivot
    adjusted_lower_time = lower_time
    adjusted_upper = upper_pivot
    adjusted_upper_time = upper_time
    
    # For ASCENDING channel: Check if any price broke below the ascending floor line
    if channel_type == ChannelType.ASCENDING:
        for low_price, low_time_val, session_name in all_lows:
            if low_time_val and lower_time and low_time_val > lower_time:
                # Calculate where the ascending floor would be at this time
                blocks = blocks_between(lower_time, low_time_val)
                projected_floor = adjusted_lower + SLOPE * blocks
                
                # If price went below the projected floor, this becomes new pivot
                if low_price < projected_floor:
                    adjusted_lower = low_price
                    adjusted_lower_time = low_time_val
                    result["floor_was_adjusted"] = True
                    result["floor_adjustment_session"] = session_name
    
    # For DESCENDING channel: Check if any price broke above the descending ceiling line
    elif channel_type == ChannelType.DESCENDING:
        for high_price, high_time_val, session_name in all_highs:
            if high_time_val and upper_time and high_time_val > upper_time:
                # Calculate where the descending ceiling would be at this time
                blocks = blocks_between(upper_time, high_time_val)
                projected_ceiling = adjusted_upper - SLOPE * blocks
                
                # If price went above the projected ceiling, this becomes new pivot
                if high_price > projected_ceiling:
                    adjusted_upper = high_price
                    adjusted_upper_time = high_time_val
                    result["ceiling_was_adjusted"] = True
                    result["ceiling_adjustment_session"] = session_name
    
    # For MIXED channel: Check both directions
    elif channel_type == ChannelType.MIXED:
        # Check ascending floor breaks
        for low_price, low_time_val, session_name in all_lows:
            if low_time_val and lower_time and low_time_val > lower_time:
                blocks = blocks_between(lower_time, low_time_val)
                projected_floor = adjusted_lower + SLOPE * blocks
                if low_price < projected_floor:
                    adjusted_lower = low_price
                    adjusted_lower_time = low_time_val
                    result["floor_was_adjusted"] = True
                    result["floor_adjustment_session"] = session_name
        
        # Check descending ceiling breaks
        for high_price, high_time_val, session_name in all_highs:
            if high_time_val and upper_time and high_time_val > upper_time:
                blocks = blocks_between(upper_time, high_time_val)
                projected_ceiling = adjusted_upper - SLOPE * blocks
                if high_price > projected_ceiling:
                    adjusted_upper = high_price
                    adjusted_upper_time = high_time_val
                    result["ceiling_was_adjusted"] = True
                    result["ceiling_adjustment_session"] = session_name
    
    result["upper_pivot"] = adjusted_upper
    result["lower_pivot"] = adjusted_lower
    result["upper_time"] = adjusted_upper_time
    result["lower_time"] = adjusted_lower_time
    
    return result


def calc_channel_levels(upper_pivot, lower_pivot, upper_time, lower_time, ref_time, channel_type):
    if upper_pivot is None or lower_pivot is None:
        return None, None
    blocks_high = blocks_between(upper_time, ref_time) if upper_time and ref_time else 0
    blocks_low = blocks_between(lower_time, ref_time) if lower_time and ref_time else 0
    
    if channel_type == ChannelType.ASCENDING:
        ceiling = round(upper_pivot + SLOPE * blocks_high, 2)
        floor = round(lower_pivot + SLOPE * blocks_low, 2)
    elif channel_type == ChannelType.DESCENDING:
        ceiling = round(upper_pivot - SLOPE * blocks_high, 2)
        floor = round(lower_pivot - SLOPE * blocks_low, 2)
    elif channel_type == ChannelType.MIXED:
        # MIXED: For display, use descending ceiling and ascending floor (outer bounds)
        ceiling = round(upper_pivot - SLOPE * blocks_high, 2)  # Descending ceiling
        floor = round(lower_pivot + SLOPE * blocks_low, 2)      # Ascending floor
    elif channel_type == ChannelType.CONTRACTING:
        ceiling = round(upper_pivot - SLOPE * blocks_high, 2)
        floor = round(lower_pivot + SLOPE * blocks_low, 2)
    else:
        ceiling, floor = upper_pivot, lower_pivot
    return ceiling, floor

def calc_mixed_levels(upper_pivot, lower_pivot, upper_time, lower_time, ref_time):
    """Calculate all four levels for MIXED channel: ascending ceiling/floor and descending ceiling/floor."""
    if upper_pivot is None or lower_pivot is None:
        return None
    blocks_high = blocks_between(upper_time, ref_time) if upper_time and ref_time else 0
    blocks_low = blocks_between(lower_time, ref_time) if lower_time and ref_time else 0
    
    return {
        "asc_ceiling": round(upper_pivot + SLOPE * blocks_high, 2),   # Ascending ceiling (high going up)
        "asc_floor": round(lower_pivot + SLOPE * blocks_low, 2),       # Ascending floor (low going up)
        "desc_ceiling": round(upper_pivot - SLOPE * blocks_high, 2),  # Descending ceiling (high going down)
        "desc_floor": round(lower_pivot - SLOPE * blocks_low, 2),      # Descending floor (low going down)
    }

def calc_dual_channel_levels(upper_pivot, lower_pivot, upper_time, lower_time, ref_time):
    """
    Calculate ALL FOUR channel levels - always show both ascending and descending.
    This is the core of Option C - dual channel system.
    
    Returns:
        dict with:
        - asc_floor: Ascending floor (LOW projected up) - CALLS entry
        - asc_ceiling: Ascending ceiling (HIGH projected up) - CALLS target
        - desc_ceiling: Descending ceiling (HIGH projected down) - PUTS entry  
        - desc_floor: Descending floor (LOW projected down) - PUTS target
    """
    if upper_pivot is None or lower_pivot is None:
        return None
    
    blocks_high = blocks_between(upper_time, ref_time) if upper_time and ref_time else 0
    blocks_low = blocks_between(lower_time, ref_time) if lower_time and ref_time else 0
    
    return {
        # ASCENDING CHANNEL (from overnight low, projecting UP)
        "asc_floor": round(lower_pivot + SLOPE * blocks_low, 2),      # LOW going UP - CALLS entry
        "asc_ceiling": round(upper_pivot + SLOPE * blocks_high, 2),   # HIGH going UP - CALLS target
        
        # DESCENDING CHANNEL (from overnight high, projecting DOWN)
        "desc_ceiling": round(upper_pivot - SLOPE * blocks_high, 2),  # HIGH going DOWN - PUTS entry
        "desc_floor": round(lower_pivot - SLOPE * blocks_low, 2),     # LOW going DOWN - PUTS target
        
        # Metadata
        "blocks_high": blocks_high,
        "blocks_low": blocks_low,
        "overnight_high": upper_pivot,
        "overnight_low": lower_pivot,
    }

def get_position(price, ceiling, floor):
    if price > ceiling:
        return Position.ABOVE
    elif price < floor:
        return Position.BELOW
    return Position.INSIDE

# ═══════════════════════════════════════════════════════════════════════════════
# DECISION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
def analyze_market_state(current_spx, ceiling_spx, floor_spx, channel_type, retail_bias, ema_bias, 
                         vix_position, vix, session_tests, gap_analysis, prior_close_analysis, vix_structure):
    """
    Analyze market state and generate trade scenarios with confluence-based confidence.
    
    Confluence Factors:
    1. EMA alignment (8/21/200)
    2. Retail positioning (fade the crowd)
    3. Session level tests (more tests = stronger level)
    4. Gap position (gap INTO level = better setup)
    5. Prior close validation (prior close near level = validates it)
    6. VIX term structure (backwardation = more volatile)
    """
    if current_spx is None or ceiling_spx is None or floor_spx is None:
        return {"no_trade": True, "no_trade_reason": "Missing price data", "calls_factors": [], "puts_factors": [], "primary": None, "alternate": None}
    
    result = {"no_trade": False, "no_trade_reason": None, "calls_factors": [], "puts_factors": [], "primary": None, "alternate": None}
    
    if current_spx > ceiling_spx:
        position = Position.ABOVE
    elif current_spx < floor_spx:
        position = Position.BELOW
    else:
        position = Position.INSIDE
    
    def make_scenario(name, direction, entry, stop, trigger, rationale, confidence):
        if direction == "CALLS":
            strike = int(math.ceil((entry + 20) / 5) * 5)
            opt_type = "CALL"
        else:
            strike = int(math.floor((entry - 20) / 5) * 5)
            opt_type = "PUT"
        entry_premium = estimate_0dte_premium(entry, strike, 6.0, vix, opt_type)
        target_50, target_75, target_100 = round(entry_premium * 1.50, 2), round(entry_premium * 1.75, 2), round(entry_premium * 2.00, 2)
        return {
            "name": name, "direction": direction, "entry": entry, "stop": stop, "trigger": trigger, "rationale": rationale, "confidence": confidence,
            "strike": strike, "contract": f"SPX {strike}{'C' if direction == 'CALLS' else 'P'} 0DTE", "entry_premium": entry_premium,
            "target_50": target_50, "target_75": target_75, "target_100": target_100,
            "profit_50": round((target_50 - entry_premium) * 100, 0), "profit_75": round((target_75 - entry_premium) * 100, 0), "profit_100": round((target_100 - entry_premium) * 100, 0)
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # CONFLUENCE FACTORS - 6 factors for your 0DTE strategy
    # ─────────────────────────────────────────────────────────────────────────
    
    # Factor 1: Price proximity to key level
    channel_range = ceiling_spx - floor_spx
    dist_to_floor = current_spx - floor_spx
    dist_to_ceiling = ceiling_spx - current_spx
    near_floor = dist_to_floor <= channel_range * 0.3
    near_ceiling = dist_to_ceiling <= channel_range * 0.3
    
    # Factor 2: EMA alignment (8/21/200)
    ema_bullish = ema_bias == Bias.CALLS
    ema_bearish = ema_bias == Bias.PUTS
    
    # Factor 3: Retail positioning (fade the crowd)
    fade_to_calls = retail_bias == Bias.CALLS  # Retail heavy puts
    fade_to_puts = retail_bias == Bias.PUTS    # Retail heavy calls
    
    # Factor 4: Session tests (more sessions tested = stronger level)
    floor_tested = session_tests["floor_tests"] >= 1
    floor_multi_test = session_tests["floor_tests"] >= 2
    ceiling_tested = session_tests["ceiling_tests"] >= 1
    ceiling_multi_test = session_tests["ceiling_tests"] >= 2
    
    # Factor 5: Gap analysis
    gap_into_floor = gap_analysis["into_floor"]
    gap_into_ceiling = gap_analysis["into_ceiling"]
    gap_away_floor = gap_analysis["away_from_floor"]
    gap_away_ceiling = gap_analysis["away_from_ceiling"]
    
    # Factor 6: Prior close validation
    prior_validates_floor = prior_close_analysis["validates_floor"]
    prior_validates_ceiling = prior_close_analysis["validates_ceiling"]
    
    # Factor 7: VIX term structure (affects volatility, not direction)
    vix_contango = vix_structure["structure"] == "CONTANGO"  # Normal, stable - tighter moves
    vix_backwardation = vix_structure["structure"] == "BACKWARDATION"  # Fear - bigger moves both ways
    
    # ─────────────────────────────────────────────────────────────────────────
    # BUILD FACTOR LISTS FOR DISPLAY
    # ─────────────────────────────────────────────────────────────────────────
    
    # Calls factors (for CALLS scenarios)
    if ema_bullish:
        result["calls_factors"].append("EMA bullish (8>21>200)")
    if fade_to_calls:
        result["calls_factors"].append("Retail puts heavy (fade)")
    if floor_tested:
        sessions_str = ", ".join(session_tests["floor_sessions"])
        result["calls_factors"].append(f"Floor tested ({sessions_str})")
    if floor_multi_test:
        result["calls_factors"].append("Floor multi-tested ✓✓")
    if gap_into_floor:
        result["calls_factors"].append("Gap down INTO floor")
    if prior_validates_floor:
        result["calls_factors"].append("Prior close validates floor")
    
    # Puts factors (for PUTS scenarios)
    if ema_bearish:
        result["puts_factors"].append("EMA bearish (8<21<200)")
    if fade_to_puts:
        result["puts_factors"].append("Retail calls heavy (fade)")
    if ceiling_tested:
        sessions_str = ", ".join(session_tests["ceiling_sessions"])
        result["puts_factors"].append(f"Ceiling tested ({sessions_str})")
    if ceiling_multi_test:
        result["puts_factors"].append("Ceiling multi-tested ✓✓")
    if gap_into_ceiling:
        result["puts_factors"].append("Gap up INTO ceiling")
    if prior_validates_ceiling:
        result["puts_factors"].append("Prior close validates ceiling")
    
    # VIX structure note (non-directional - applies to both)
    if vix_backwardation:
        result["calls_factors"].append("⚡ VIX backwardation (volatile)")
        result["puts_factors"].append("⚡ VIX backwardation (volatile)")
    
    # ─────────────────────────────────────────────────────────────────────────
    # CONFIDENCE CALCULATION
    # ─────────────────────────────────────────────────────────────────────────
    def calc_scenario_confidence(direction, key_level, at_key_level, is_structure_break=False):
        """
        Calculate confidence based on:
        1. At key level (not chasing)
        2. Number of supporting confluence factors FOR THAT SPECIFIC LEVEL
        3. Whether this is a structure break (lower probability)
        
        key_level: "FLOOR" or "CEILING" - which level this scenario trades
        direction: "CALLS" or "PUTS" - trade direction
        
        Note: VIX backwardation is not counted as it's non-directional
        """
        support = 0
        
        if key_level == "FLOOR":
            # Floor-based scenarios use floor factors
            if ema_bullish: support += 1  # Bullish trend supports floor bounce
            if fade_to_calls: support += 1  # Retail puts = fade to calls at floor
            if floor_tested: support += 1
            if floor_multi_test: support += 1
            if gap_into_floor: support += 1
            if prior_validates_floor: support += 1
        else:  # CEILING
            # Ceiling-based scenarios use ceiling factors
            if ema_bearish: support += 1  # Bearish trend supports ceiling rejection
            if fade_to_puts: support += 1  # Retail calls = fade to puts at ceiling
            if ceiling_tested: support += 1
            if ceiling_multi_test: support += 1
            if gap_into_ceiling: support += 1
            if prior_validates_ceiling: support += 1
        
        # Structure breaks max at MEDIUM
        if is_structure_break:
            return "MEDIUM" if support >= 3 else "LOW"
        
        # Normal scenarios
        if at_key_level:
            if support >= 4:
                return "HIGH"
            elif support >= 2:
                return "MEDIUM"
            else:
                return "LOW"
        else:
            # Not at key level - penalize
            if support >= 4:
                return "MEDIUM"
            else:
                return "LOW"
    
    # ─────────────────────────────────────────────────────────────────────────
    # GENERATE SCENARIOS
    # ─────────────────────────────────────────────────────────────────────────
    if channel_type == ChannelType.CONTRACTING:
        result["no_trade"] = True
        result["no_trade_reason"] = "CONTRACTING channel - No clear key level"
        return result
    if channel_type == ChannelType.UNDETERMINED:
        result["no_trade"] = True
        result["no_trade_reason"] = "Cannot determine channel structure"
        return result
    
    if channel_type == ChannelType.ASCENDING:
        # ASCENDING: Floor is KEY level
        if position in [Position.INSIDE, Position.ABOVE]:
            # Both scenarios trade at FLOOR level
            primary_conf = calc_scenario_confidence("CALLS", "FLOOR", near_floor, is_structure_break=False)
            alt_conf = calc_scenario_confidence("PUTS", "FLOOR", near_floor, is_structure_break=True)
            
            result["primary"] = make_scenario("Floor Bounce", "CALLS", floor_spx, floor_spx - 5, 
                "Price at ascending floor",
                f"Key level: Ascending floor • {len(result['calls_factors'])} confluence factors", primary_conf)
            result["alternate"] = make_scenario("Floor Break", "PUTS", floor_spx, floor_spx + 5, 
                "If floor fails",
                "Structure break scenario", alt_conf)
        else:
            # Price below floor - structure broken, now using floor as resistance
            primary_conf = calc_scenario_confidence("PUTS", "FLOOR", True, is_structure_break=False)
            alt_conf = calc_scenario_confidence("CALLS", "FLOOR", True, is_structure_break=True)
            
            result["primary"] = make_scenario("Breakdown Continuation", "PUTS", floor_spx, floor_spx + 5, 
                "Floor broken - bearish",
                f"Structure broken • {len(result['puts_factors'])} confluence factors", primary_conf)
            result["alternate"] = make_scenario("Floor Reclaim", "CALLS", floor_spx, floor_spx - 5, 
                "If price reclaims floor",
                "Recovery scenario", alt_conf)
    
    elif channel_type == ChannelType.DESCENDING:
        # DESCENDING: Ceiling is KEY level
        if position in [Position.INSIDE, Position.BELOW]:
            # Both scenarios trade at CEILING level
            primary_conf = calc_scenario_confidence("PUTS", "CEILING", near_ceiling, is_structure_break=False)
            alt_conf = calc_scenario_confidence("CALLS", "CEILING", near_ceiling, is_structure_break=True)
            
            result["primary"] = make_scenario("Ceiling Rejection", "PUTS", ceiling_spx, ceiling_spx + 5, 
                "Price at descending ceiling",
                f"Key level: Descending ceiling • {len(result['puts_factors'])} confluence factors", primary_conf)
            result["alternate"] = make_scenario("Ceiling Break", "CALLS", ceiling_spx, ceiling_spx - 5, 
                "If ceiling fails",
                "Structure break scenario", alt_conf)
        else:
            # Price above ceiling - structure broken, now using ceiling as support
            primary_conf = calc_scenario_confidence("CALLS", "CEILING", True, is_structure_break=False)
            alt_conf = calc_scenario_confidence("PUTS", "CEILING", True, is_structure_break=True)
            
            result["primary"] = make_scenario("Breakout Continuation", "CALLS", ceiling_spx, ceiling_spx - 5, 
                "Ceiling broken - bullish",
                f"Structure broken • {len(result['calls_factors'])} confluence factors", primary_conf)
            result["alternate"] = make_scenario("Failed Breakout", "PUTS", ceiling_spx, ceiling_spx + 5, 
                "If breakout fails",
                "Rejection scenario", alt_conf)
    
    elif channel_type == ChannelType.MIXED:
        # MIXED: Both floor AND ceiling are key levels
        result["scenarios"] = []
        
        # Floor scenarios - use FLOOR factors
        floor_calls_conf = calc_scenario_confidence("CALLS", "FLOOR", near_floor, is_structure_break=False)
        floor_puts_conf = calc_scenario_confidence("PUTS", "FLOOR", near_floor, is_structure_break=True)
        
        result["scenarios"].append(make_scenario("Floor Bounce", "CALLS", floor_spx, floor_spx - 5, 
            "Price respects ascending floor",
            f"Key level: Floor • {len(result['calls_factors'])} factors", floor_calls_conf))
        result["scenarios"].append(make_scenario("Floor Break", "PUTS", floor_spx, floor_spx + 5,
            "Floor fails",
            "Structure break", floor_puts_conf))
        
        # Ceiling scenarios - use CEILING factors
        ceil_puts_conf = calc_scenario_confidence("PUTS", "CEILING", near_ceiling, is_structure_break=False)
        ceil_calls_conf = calc_scenario_confidence("CALLS", "CEILING", near_ceiling, is_structure_break=True)
        
        result["scenarios"].append(make_scenario("Ceiling Rejection", "PUTS", ceiling_spx, ceiling_spx + 5,
            "Price respects descending ceiling",
            f"Key level: Ceiling • {len(result['puts_factors'])} factors", ceil_puts_conf))
        result["scenarios"].append(make_scenario("Ceiling Break", "CALLS", ceiling_spx, ceiling_spx - 5,
            "Ceiling fails",
            "Structure break", ceil_calls_conf))
        
        # Set primary/alternate based on which key level is closer
        if dist_to_floor <= dist_to_ceiling:
            result["primary"] = result["scenarios"][0]
            result["alternate"] = result["scenarios"][2]
        else:
            result["primary"] = result["scenarios"][2]
            result["alternate"] = result["scenarios"][0]
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# EXPLOSIVE MOVE DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════
def detect_explosive_potential(current_spx, dual_levels, prior_targets, channel_type,
                                vix_spread, ema_data, overnight_range, prior_day_range,
                                gap_analysis):
    """
    Detect explosive move potential based on TARGET DISTANCE.
    
    The only thing that matters: How far is the profit target if structure breaks?
    - Ascending floor breaks → Target is descending line from prior RTH low
    - Descending ceiling breaks → Target is ascending line from prior RTH high
    
    The further the target, the bigger the potential move.
    """
    
    result = {
        "explosive_score": 0,
        "direction_bias": None,
        "target_distance": None,
        "potential_move": None,
        "conviction": "LOW"
    }
    
    if not dual_levels or not current_spx:
        return result
    
    asc_floor = dual_levels.get("asc_floor", 0)
    desc_ceiling = dual_levels.get("desc_ceiling", 0)
    
    # Get targets from prior day levels
    bearish_target = None
    bullish_target = None
    
    if prior_targets and prior_targets.get("available"):
        bearish_target = prior_targets.get("primary_low_open_descending")
        bullish_target = prior_targets.get("primary_high_wick_ascending")
    
    # Calculate target distances
    bearish_runway = abs(asc_floor - bearish_target) if bearish_target else 0
    bullish_runway = abs(desc_ceiling - bullish_target) if bullish_target else 0
    
    # Determine which scenario has more potential based on channel type
    if channel_type == ChannelType.ASCENDING and bearish_runway > 0:
        # Ascending channel - if floor breaks, bearish target is the play
        result["target_distance"] = bearish_runway
        result["potential_move"] = "BEARISH"
        result["direction_bias"] = "PUTS"
    elif channel_type == ChannelType.DESCENDING and bullish_runway > 0:
        # Descending channel - if ceiling breaks, bullish target is the play
        result["target_distance"] = bullish_runway
        result["potential_move"] = "BULLISH"
        result["direction_bias"] = "CALLS"
    elif bearish_runway > bullish_runway:
        result["target_distance"] = bearish_runway
        result["potential_move"] = "BEARISH"
        result["direction_bias"] = "PUTS"
    elif bullish_runway > 0:
        result["target_distance"] = bullish_runway
        result["potential_move"] = "BULLISH"
        result["direction_bias"] = "CALLS"
    
    # Score based ONLY on target distance
    runway = result["target_distance"] or 0
    
    if runway >= 80:
        result["explosive_score"] = 100
        result["conviction"] = "EXTREME"
    elif runway >= 60:
        result["explosive_score"] = 75
        result["conviction"] = "HIGH"
    elif runway >= 40:
        result["explosive_score"] = 50
        result["conviction"] = "MODERATE"
    elif runway >= 25:
        result["explosive_score"] = 30
        result["conviction"] = "LOW"
    else:
        result["explosive_score"] = 0
        result["conviction"] = "LOW"
    
    return result


def analyze_market_state_v2(current_spx, dual_levels, channel_type, channel_reason,
                            retail_bias, ema_bias, vix_position, vix, 
                            session_tests, gap_analysis, prior_close_analysis, vix_structure,
                            prior_targets=None, current_time=None):
    """
    OPTION C: Dual Channel Decision Engine
    
    Always provides:
    1. All 4 levels (asc_floor, asc_ceiling, desc_ceiling, desc_floor)
    2. Dominant channel detection with reasoning
    3. PRIMARY trade at dominant level (higher probability)
    4. ALTERNATE trade if structure breaks at open
    5. Structure break alerts (only after channel locks at 5:30 AM CT)
    6. Confluence-based confidence scoring
    
    Channel Building Timeline:
    - 5:00 PM - 5:30 AM CT: Channel BUILDING (Sydney + Tokyo + London)
    - 5:30 AM CT: Channel LOCKED
    - 5:30 AM - 8:30 AM CT: Pre-RTH testing
    - 8:30 AM CT: RTH Open - final assessment
    """
    
    if current_spx is None or dual_levels is None:
        return {
            "no_trade": True, 
            "no_trade_reason": "Missing price data",
            "dual_levels": None,
            "primary": None,
            "secondary": None,
            "alternate": None,
            "structure_alerts": [],
            "calls_factors": [],
            "puts_factors": [],
            "position_summary": "No data available",
            "channel_status": "UNKNOWN"
        }
    
    # Determine channel status based on time
    channel_locked = True  # Default to locked
    channel_status = "LOCKED"
    
    if current_time:
        ct_hour = current_time.hour
        ct_minute = current_time.minute
        ct_decimal = ct_hour + ct_minute / 60.0
        
        # Channel builds from 5 PM (17:00) to 5:30 AM (5:30)
        # Before 5:30 AM = still building
        if ct_decimal < 5.5:  # Before 5:30 AM
            channel_locked = False
            channel_status = "BUILDING"
        elif ct_decimal >= 17.0:  # After 5 PM = new session building
            channel_locked = False
            channel_status = "BUILDING"
    
    # Extract levels
    asc_floor = dual_levels["asc_floor"]
    asc_ceiling = dual_levels["asc_ceiling"]
    desc_ceiling = dual_levels["desc_ceiling"]
    desc_floor = dual_levels["desc_floor"]
    
    # Position analysis
    dist_to_asc_floor = abs(current_spx - asc_floor)
    dist_to_desc_ceiling = abs(current_spx - desc_ceiling)
    
    NEAR_THRESHOLD = 15
    near_asc_floor = dist_to_asc_floor <= NEAR_THRESHOLD
    near_desc_ceiling = dist_to_desc_ceiling <= NEAR_THRESHOLD
    
    below_asc_floor = current_spx < asc_floor
    above_desc_ceiling = current_spx > desc_ceiling
    
    # Confluence factors
    ema_bullish = ema_bias == Bias.CALLS
    ema_bearish = ema_bias == Bias.PUTS
    fade_to_calls = retail_bias == Bias.CALLS
    fade_to_puts = retail_bias == Bias.PUTS
    floor_tested = session_tests["floor_tests"] >= 1
    floor_multi_test = session_tests["floor_tests"] >= 2
    ceiling_tested = session_tests["ceiling_tests"] >= 1
    ceiling_multi_test = session_tests["ceiling_tests"] >= 2
    gap_into_floor = gap_analysis["into_floor"]
    gap_into_ceiling = gap_analysis["into_ceiling"]
    prior_validates_floor = prior_close_analysis["validates_floor"]
    prior_validates_ceiling = prior_close_analysis["validates_ceiling"]
    vix_backwardation = vix_structure["structure"] == "BACKWARDATION"
    
    # Build factor lists
    calls_factors = []
    puts_factors = []
    
    if ema_bullish: calls_factors.append("✓ EMA bullish (8>21>200)")
    if fade_to_calls: calls_factors.append("✓ Retail puts heavy (fade)")
    if floor_tested: 
        sessions_str = ", ".join(session_tests["floor_sessions"])
        calls_factors.append(f"✓ Floor tested ({sessions_str})")
    if floor_multi_test: calls_factors.append("✓✓ Floor multi-tested")
    if gap_into_floor: calls_factors.append("✓ Gap down INTO floor")
    if prior_validates_floor: calls_factors.append("✓ Prior close validates floor")
    
    if ema_bearish: puts_factors.append("✓ EMA bearish (8<21<200)")
    if fade_to_puts: puts_factors.append("✓ Retail calls heavy (fade)")
    if ceiling_tested:
        sessions_str = ", ".join(session_tests["ceiling_sessions"])
        puts_factors.append(f"✓ Ceiling tested ({sessions_str})")
    if ceiling_multi_test: puts_factors.append("✓✓ Ceiling multi-tested")
    if gap_into_ceiling: puts_factors.append("✓ Gap up INTO ceiling")
    if prior_validates_ceiling: puts_factors.append("✓ Prior close validates ceiling")
    
    if vix_backwardation:
        calls_factors.append("⚡ VIX backwardation (volatile)")
        puts_factors.append("⚡ VIX backwardation (volatile)")
    
    # Confidence calculation
    def calc_conf(direction, at_level, is_break=False):
        support = 0
        if direction == "CALLS":
            if ema_bullish: support += 1
            if fade_to_calls: support += 1
            if floor_tested: support += 1
            if floor_multi_test: support += 1
            if gap_into_floor: support += 1
            if prior_validates_floor: support += 1
        else:
            if ema_bearish: support += 1
            if fade_to_puts: support += 1
            if ceiling_tested: support += 1
            if ceiling_multi_test: support += 1
            if gap_into_ceiling: support += 1
            if prior_validates_ceiling: support += 1
        
        if is_break: return "MEDIUM" if support >= 3 else "LOW"
        if at_level:
            if support >= 4: return "HIGH"
            elif support >= 2: return "MEDIUM"
            else: return "LOW"
        else:
            return "MEDIUM" if support >= 4 else "LOW"
    
    # Trade builder
    def make_trade(name, direction, entry, stop, trigger, rationale, confidence, is_primary=True):
        if direction == "CALLS":
            strike = int(math.ceil((entry + 20) / 5) * 5)
            opt_type = "CALL"
        else:
            strike = int(math.floor((entry - 20) / 5) * 5)
            opt_type = "PUT"
        
        entry_premium = estimate_0dte_premium(entry, strike, 6.0, vix, opt_type)
        t1 = round(entry_premium * 1.50, 2)
        t2 = round(entry_premium * 1.75, 2)
        t3 = round(entry_premium * 2.00, 2)
        
        return {
            "name": name, "direction": direction, "entry_level": entry, "stop_level": stop,
            "trigger": trigger, "rationale": rationale, "confidence": confidence, "is_primary": is_primary,
            "strike": strike, "contract": f"SPX {strike}{'C' if direction == 'CALLS' else 'P'} 0DTE",
            "entry_premium": entry_premium,
            "targets": {
                "t1": {"price": t1, "profit_pct": 50, "profit_dollars": round((t1 - entry_premium) * 100, 0)},
                "t2": {"price": t2, "profit_pct": 75, "profit_dollars": round((t2 - entry_premium) * 100, 0)},
                "t3": {"price": t3, "profit_pct": 100, "profit_dollars": round((t3 - entry_premium) * 100, 0)},
            }
        }
    
    # Structure alerts - ONLY show "broken" if channel is locked (after 5:30 AM CT)
    structure_alerts = []
    if channel_locked:
        if channel_type == ChannelType.ASCENDING and below_asc_floor:
            structure_alerts.append(f"⚠️ STRUCTURE BROKEN: Price below ascending floor ({asc_floor:.2f})")
        if channel_type == ChannelType.DESCENDING and above_desc_ceiling:
            structure_alerts.append(f"⚠️ STRUCTURE BROKEN: Price above descending ceiling ({desc_ceiling:.2f})")
    else:
        # Channel still building - show informational message
        if channel_type == ChannelType.ASCENDING and below_asc_floor:
            structure_alerts.append(f"📊 CHANNEL BUILDING: Price currently below developing floor ({asc_floor:.2f})")
        if channel_type == ChannelType.DESCENDING and above_desc_ceiling:
            structure_alerts.append(f"📊 CHANNEL BUILDING: Price currently above developing ceiling ({desc_ceiling:.2f})")
    
    # Initialize result
    result = {
        "no_trade": False, "no_trade_reason": None,
        "channel_type": channel_type, "channel_reason": channel_reason,
        "channel_status": channel_status,
        "channel_locked": channel_locked,
        "dual_levels": dual_levels,
        "calls_factors": calls_factors, "puts_factors": puts_factors,
        "structure_alerts": structure_alerts,
        "primary": None, "secondary": None, "alternate": None, "position_summary": ""
    }
    
    # No trade conditions
    if channel_type == ChannelType.CONTRACTING:
        result["no_trade"] = True
        result["no_trade_reason"] = "CONTRACTING channel - Wait for expansion"
        return result
    if channel_type == ChannelType.UNDETERMINED:
        result["no_trade"] = True
        result["no_trade_reason"] = "Cannot determine channel - Insufficient data"
        return result
    
    # ASCENDING DOMINANT
    if channel_type == ChannelType.ASCENDING:
        # Get price target for break scenario
        desc_target = None
        price_target_text = ""
        if prior_targets and prior_targets.get("available"):
            desc_target = prior_targets.get("primary_low_open_descending")
            if desc_target:
                price_target_text = f" • Target: {desc_target:.2f} (desc from prior low)"
        
        if channel_locked and below_asc_floor:
            # AFTER 5:30 AM and structure is broken - flip the trades
            result["primary"] = make_trade("Ascending Floor Rejection", "PUTS", asc_floor, asc_floor + 10,
                f"Sell rallies to broken floor {asc_floor:.2f}",
                f"Structure broken{price_target_text} • {len(puts_factors)} factors", calc_conf("PUTS", True), True)
            result["alternate"] = make_trade("Floor Reclaim", "CALLS", asc_floor, asc_floor - 10,
                f"ONLY if price reclaims {asc_floor:.2f}",
                "Recovery scenario - watch for failed breakdown", calc_conf("CALLS", True, True), False)
            result["position_summary"] = f"⚠️ BELOW ascending floor ({asc_floor:.2f}) - BEARISH bias"
            if desc_target:
                result["price_target"] = desc_target
                result["price_target_desc"] = "Descending line from prior RTH low"
        else:
            # Structure intact OR channel still building - show both scenarios
            result["primary"] = make_trade("Ascending Floor Bounce", "CALLS", asc_floor, asc_floor - 10,
                f"Buy at floor {asc_floor:.2f}" if channel_locked else f"Buy at developing floor {asc_floor:.2f}",
                f"KEY: Ascending floor • {len(calls_factors)} factors", calc_conf("CALLS", near_asc_floor), True)
            result["alternate"] = make_trade("Floor Break → Rejection", "PUTS", asc_floor, asc_floor + 10,
                f"IF floor {asc_floor:.2f} breaks at open",
                f"Breakdown scenario{price_target_text} • {len(puts_factors)} factors", calc_conf("PUTS", False), False)
            # Also keep secondary for ceiling
            result["secondary"] = make_trade("Desc Ceiling Rejection", "PUTS", desc_ceiling, desc_ceiling + 10,
                f"If price reaches {desc_ceiling:.2f}",
                f"Secondary level • {len(puts_factors)} factors", calc_conf("PUTS", near_desc_ceiling), False)
            
            if channel_locked:
                result["position_summary"] = f"{'✅ AT' if near_asc_floor else '📍 Wait for'} ascending floor ({asc_floor:.2f})"
            else:
                result["position_summary"] = f"🔄 CHANNEL BUILDING - Floor developing at {asc_floor:.2f}"
    
    # DESCENDING DOMINANT
    elif channel_type == ChannelType.DESCENDING:
        # Get price target for break scenario
        asc_target = None
        price_target_text = ""
        if prior_targets and prior_targets.get("available"):
            asc_target = prior_targets.get("primary_high_wick_ascending")
            if asc_target:
                price_target_text = f" • Target: {asc_target:.2f} (asc from prior high)"
        
        if channel_locked and above_desc_ceiling:
            # AFTER 5:30 AM and structure is broken - flip the trades
            result["primary"] = make_trade("Descending Ceiling Bounce", "CALLS", desc_ceiling, desc_ceiling - 10,
                f"Buy dips to broken ceiling {desc_ceiling:.2f}",
                f"Structure broken{price_target_text} • {len(calls_factors)} factors", calc_conf("CALLS", True), True)
            result["alternate"] = make_trade("Failed Breakout", "PUTS", desc_ceiling, desc_ceiling + 10,
                f"ONLY if price fails below {desc_ceiling:.2f}",
                "Rejection scenario - watch for failed breakout", calc_conf("PUTS", True, True), False)
            result["position_summary"] = f"🚀 ABOVE descending ceiling ({desc_ceiling:.2f}) - BULLISH bias"
            if asc_target:
                result["price_target"] = asc_target
                result["price_target_desc"] = "Ascending line from prior RTH high"
        else:
            # Structure intact OR channel still building - show both scenarios
            result["primary"] = make_trade("Desc Ceiling Rejection", "PUTS", desc_ceiling, desc_ceiling + 10,
                f"Sell at ceiling {desc_ceiling:.2f}" if channel_locked else f"Sell at developing ceiling {desc_ceiling:.2f}",
                f"KEY: Descending ceiling • {len(puts_factors)} factors", calc_conf("PUTS", near_desc_ceiling), True)
            result["alternate"] = make_trade("Ceiling Break → Bounce", "CALLS", desc_ceiling, desc_ceiling - 10,
                f"IF ceiling {desc_ceiling:.2f} breaks at open",
                f"Breakout scenario{price_target_text} • {len(calls_factors)} factors", calc_conf("CALLS", False), False)
            # Also keep secondary for floor
            result["secondary"] = make_trade("Ascending Floor Bounce", "CALLS", asc_floor, asc_floor - 10,
                f"If price reaches {asc_floor:.2f}",
                f"Secondary level • {len(calls_factors)} factors", calc_conf("CALLS", near_asc_floor), False)
            
            if channel_locked:
                result["position_summary"] = f"{'✅ AT' if near_desc_ceiling else '📍 Wait for'} descending ceiling ({desc_ceiling:.2f})"
            else:
                result["position_summary"] = f"🔄 CHANNEL BUILDING - Ceiling developing at {desc_ceiling:.2f}"
    
    # MIXED
    elif channel_type == ChannelType.MIXED:
        if dist_to_asc_floor <= dist_to_desc_ceiling:
            result["primary"] = make_trade("Floor Bounce", "CALLS", asc_floor, asc_floor - 10,
                f"Price near floor {asc_floor:.2f}",
                f"Mixed - floor closer • {len(calls_factors)} factors", calc_conf("CALLS", near_asc_floor), True)
            result["secondary"] = make_trade("Ceiling Rejection", "PUTS", desc_ceiling, desc_ceiling + 10,
                f"If price reaches {desc_ceiling:.2f}",
                f"Mixed - ceiling level • {len(puts_factors)} factors", calc_conf("PUTS", near_desc_ceiling), False)
        else:
            result["primary"] = make_trade("Ceiling Rejection", "PUTS", desc_ceiling, desc_ceiling + 10,
                f"Price near ceiling {desc_ceiling:.2f}",
                f"Mixed - ceiling closer • {len(puts_factors)} factors", calc_conf("PUTS", near_desc_ceiling), True)
            result["secondary"] = make_trade("Floor Bounce", "CALLS", asc_floor, asc_floor - 10,
                f"If price reaches {asc_floor:.2f}",
                f"Mixed - floor level • {len(calls_factors)} factors", calc_conf("CALLS", near_asc_floor), False)
        result["position_summary"] = f"⚖️ MIXED: Floor {asc_floor:.2f} / Ceiling {desc_ceiling:.2f}"
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# LEGENDARY CSS STYLING
# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
# LEGENDARY CSS STYLING - PROFESSIONAL EDITION V2
# ═══════════════════════════════════════════════════════════════════════════════
CSS_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&family=Share+Tech+Mono&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

/* ═══════════════════════════════════════════════════════════════════════════
   PREMIUM TRADING TERMINAL - ELITE DESIGN SYSTEM
   Bloomberg Terminal + TradingView Pro + Hedge Fund Dashboard
   ═══════════════════════════════════════════════════════════════════════════ */
:root {
    /* Deep Space Backgrounds */
    --bg-terminal: #05070a;
    --bg-panel: #0a0d12;
    --bg-card: #0f1318;
    --bg-elevated: #151a21;
    --bg-hover: #1c222b;
    --bg-input: #080a0e;
    
    /* Electric Accent Colors */
    --accent-cyan: #00f5d4;
    --accent-cyan-soft: rgba(0, 245, 212, 0.15);
    --accent-cyan-glow: rgba(0, 245, 212, 0.4);
    --accent-blue: #00bbf9;
    --accent-purple: #9b5de5;
    --accent-pink: #f15bb5;
    --accent-gold: #fee440;
    --accent-gold-soft: rgba(254, 228, 64, 0.15);
    
    /* Vivid Trading Colors */
    --bull: #00ff88;
    --bull-soft: rgba(0, 255, 136, 0.08);
    --bull-medium: rgba(0, 255, 136, 0.18);
    --bull-glow: rgba(0, 255, 136, 0.5);
    --bear: #ff3366;
    --bear-soft: rgba(255, 51, 102, 0.08);
    --bear-medium: rgba(255, 51, 102, 0.18);
    --bear-glow: rgba(255, 51, 102, 0.5);
    --neutral: #64748b;
    
    /* Typography */
    --text-bright: #ffffff;
    --text-primary: #e8ecf4;
    --text-secondary: #9ba8bc;
    --text-muted: #5c6b7f;
    --text-dim: #3d4a5c;
    
    /* Neon Borders */
    --border-subtle: rgba(255, 255, 255, 0.04);
    --border-default: rgba(255, 255, 255, 0.08);
    --border-strong: rgba(255, 255, 255, 0.12);
    --border-accent: rgba(0, 245, 212, 0.4);
    --border-glow: rgba(0, 245, 212, 0.6);
    
    /* Dramatic Shadows & Glows */
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.5);
    --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.6);
    --shadow-lg: 0 16px 48px rgba(0, 0, 0, 0.7);
    --shadow-glow-cyan: 0 0 30px rgba(0, 245, 212, 0.25), 0 0 60px rgba(0, 245, 212, 0.1);
    --shadow-glow-bull: 0 0 30px rgba(0, 255, 136, 0.3), 0 0 60px rgba(0, 255, 136, 0.15);
    --shadow-glow-bear: 0 0 30px rgba(255, 51, 102, 0.3), 0 0 60px rgba(255, 51, 102, 0.15);
    --shadow-glow-gold: 0 0 30px rgba(254, 228, 64, 0.3);
    
    /* Premium Gradients */
    --gradient-premium: linear-gradient(135deg, #00f5d4 0%, #00bbf9 25%, #9b5de5 50%, #f15bb5 75%, #fee440 100%);
    --gradient-cyber: linear-gradient(135deg, #00f5d4 0%, #00bbf9 100%);
    --gradient-bull: linear-gradient(135deg, #00ff88 0%, #00f5d4 100%);
    --gradient-bear: linear-gradient(135deg, #ff3366 0%, #ff6b6b 100%);
    --gradient-card: linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0) 100%);
    --gradient-glass: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
    
    /* Spacing */
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
    
    /* ═══════════════════════════════════════════════════════════════════════════
       STANDARDIZED TYPOGRAPHY SCALE
       ═══════════════════════════════════════════════════════════════════════════ */
    /* Font Families - Cohesive Futuristic Terminal Aesthetic */
    --font-display: 'Orbitron', sans-serif;           /* Prices, big numbers, headlines */
    --font-body: 'Rajdhani', sans-serif;              /* Body text, descriptions, UI elements */
    --font-mono: 'Share Tech Mono', 'IBM Plex Mono', monospace;  /* Labels, codes, technical data */
    
    /* Font Sizes - Consistent Scale */
    --text-3xl: 2.5rem;    /* Hero brand name */
    --text-2xl: 1.75rem;   /* Big metric values */
    --text-xl: 1.4rem;     /* Section values, price levels */
    --text-lg: 1.15rem;    /* Card titles, section headers */
    --text-md: 1rem;       /* Body text */
    --text-sm: 0.875rem;   /* Secondary info, descriptions */
    --text-xs: 0.75rem;    /* Labels, badges, small caps */
    --text-xxs: 0.65rem;   /* Micro labels */
}

/* ═══════════════════════════════════════════════════════════════════════════
   BASE APPLICATION - IMMERSIVE DARK TERMINAL
   ═══════════════════════════════════════════════════════════════════════════ */
.stApp {
    background: var(--bg-terminal);
    background-image: 
        radial-gradient(ellipse 120% 80% at 50% -40%, rgba(0, 245, 212, 0.08) 0%, transparent 50%),
        radial-gradient(ellipse 100% 60% at 100% 20%, rgba(0, 187, 249, 0.06) 0%, transparent 40%),
        radial-gradient(ellipse 80% 50% at 0% 80%, rgba(155, 93, 229, 0.05) 0%, transparent 40%),
        radial-gradient(ellipse 60% 40% at 80% 100%, rgba(241, 91, 181, 0.04) 0%, transparent 40%);
    font-family: 'Rajdhani', sans-serif;
    color: var(--text-primary);
    min-height: 100vh;
}

/* Animated Background Grid */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: 
        linear-gradient(rgba(0, 245, 212, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 245, 212, 0.03) 1px, transparent 1px);
    background-size: 50px 50px;
    pointer-events: none;
    z-index: 0;
    animation: gridPulse 8s ease-in-out infinite;
}

@keyframes gridPulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 0.6; }
}

/* Hide Streamlit defaults */
#MainMenu, footer, .stDeployButton {
    display: none !important;
    visibility: hidden !important;
}

/* Premium Scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-panel); }
::-webkit-scrollbar-thumb { 
    background: linear-gradient(180deg, var(--accent-cyan) 0%, var(--accent-purple) 100%);
    border-radius: 5px;
    border: 2px solid var(--bg-panel);
}
::-webkit-scrollbar-thumb:hover { 
    background: linear-gradient(180deg, var(--accent-cyan) 0%, var(--accent-pink) 100%);
}

/* ═══════════════════════════════════════════════════════════════════════════
   STREAMLIT COLUMN EQUAL HEIGHT - CRITICAL FIX
   ═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stHorizontalBlock"] {
    align-items: stretch !important;
    gap: 16px !important;
}

[data-testid="column"] {
    display: flex !important;
    flex-direction: column !important;
}

[data-testid="column"] > div:first-child {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100% !important;
}

[data-testid="column"] > div:first-child > div {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100% !important;
}

[data-testid="stMarkdownContainer"] {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}

[data-testid="stMarkdownContainer"] > div {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   HERO BANNER - EPIC CINEMATIC HEADER WITH LEGENDARY LOGO
   ═══════════════════════════════════════════════════════════════════════════ */
.hero-banner {
    position: relative;
    padding: 50px 40px 40px 40px;
    margin: -1rem -1rem 30px -1rem;
    background: linear-gradient(180deg, rgba(5, 10, 20, 1) 0%, var(--bg-terminal) 100%);
    border-bottom: 3px solid transparent;
    border-image: var(--gradient-premium) 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 24px;
    overflow: hidden;
    min-height: 380px;
}

/* Starfield Background */
.hero-banner::before {
    content: '';
    position: absolute;
    inset: 0;
    background: 
        radial-gradient(2px 2px at 20% 30%, rgba(255,255,255,0.8) 0%, transparent 100%),
        radial-gradient(2px 2px at 40% 70%, rgba(255,255,255,0.6) 0%, transparent 100%),
        radial-gradient(1px 1px at 60% 20%, rgba(255,255,255,0.7) 0%, transparent 100%),
        radial-gradient(2px 2px at 80% 50%, rgba(255,255,255,0.5) 0%, transparent 100%),
        radial-gradient(1px 1px at 10% 80%, rgba(255,255,255,0.6) 0%, transparent 100%),
        radial-gradient(1px 1px at 90% 10%, rgba(255,255,255,0.7) 0%, transparent 100%),
        radial-gradient(2px 2px at 30% 90%, rgba(255,255,255,0.5) 0%, transparent 100%),
        radial-gradient(1px 1px at 70% 40%, rgba(255,255,255,0.6) 0%, transparent 100%),
        radial-gradient(1px 1px at 50% 60%, rgba(0, 245, 212, 0.8) 0%, transparent 100%),
        radial-gradient(1px 1px at 85% 75%, rgba(155, 93, 229, 0.8) 0%, transparent 100%),
        radial-gradient(ellipse 100% 100% at 50% 0%, rgba(0, 245, 212, 0.12) 0%, transparent 60%),
        radial-gradient(ellipse 80% 80% at 20% 100%, rgba(155, 93, 229, 0.1) 0%, transparent 50%),
        radial-gradient(ellipse 80% 80% at 80% 100%, rgba(0, 187, 249, 0.08) 0%, transparent 50%);
    animation: starsShimmer 8s ease-in-out infinite;
}

@keyframes starsShimmer {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

.hero-banner::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, 
        transparent 0%, 
        var(--accent-cyan) 20%, 
        var(--accent-purple) 40%,
        var(--accent-gold) 60%,
        var(--accent-purple) 80%,
        var(--accent-cyan) 100%);
    box-shadow: 0 0 30px rgba(0, 245, 212, 0.6), 0 0 60px rgba(155, 93, 229, 0.4);
    animation: bottomBarFlow 4s linear infinite;
}

@keyframes bottomBarFlow {
    0% { background-position: 0% 50%; }
    100% { background-position: 200% 50%; }
}

/* ═══════════════════════════════════════════════════════════════════════════
   THE LEGENDARY 3-PILLAR HOLOGRAPHIC PYRAMID
   ═══════════════════════════════════════════════════════════════════════════ */
.prophet-logo {
    position: relative;
    width: 240px;
    height: 220px;
    flex-shrink: 0;
    z-index: 2;
    perspective: 1000px;
}

/* ═══════════════════════════════════════════════════════════════════════════
   LAYER 1: OUTER PARTICLE FIELD - Cosmic dust swirling
   ═══════════════════════════════════════════════════════════════════════════ */
.particle-field {
    position: absolute;
    width: 300px;
    height: 300px;
    top: -40px;
    left: -30px;
    border-radius: 50%;
    background: 
        radial-gradient(circle at 30% 30%, rgba(0, 245, 212, 0.4) 0%, transparent 3%),
        radial-gradient(circle at 70% 20%, rgba(155, 93, 229, 0.5) 0%, transparent 2%),
        radial-gradient(circle at 20% 70%, rgba(254, 228, 64, 0.4) 0%, transparent 2%),
        radial-gradient(circle at 80% 80%, rgba(0, 187, 249, 0.5) 0%, transparent 3%),
        radial-gradient(circle at 50% 50%, rgba(0, 245, 212, 0.3) 0%, transparent 2%),
        radial-gradient(circle at 40% 80%, rgba(155, 93, 229, 0.4) 0%, transparent 2%),
        radial-gradient(circle at 60% 30%, rgba(254, 228, 64, 0.3) 0%, transparent 2%),
        radial-gradient(circle at 10% 50%, rgba(0, 245, 212, 0.5) 0%, transparent 2%),
        radial-gradient(circle at 90% 50%, rgba(155, 93, 229, 0.4) 0%, transparent 2%);
    animation: particleSwirl 20s linear infinite;
    opacity: 0.8;
}

@keyframes particleSwirl {
    0% { transform: rotate(0deg) scale(1); }
    50% { transform: rotate(180deg) scale(1.1); }
    100% { transform: rotate(360deg) scale(1); }
}

.particle-field-inner {
    position: absolute;
    width: 200px;
    height: 200px;
    top: 10px;
    left: 20px;
    border-radius: 50%;
    background: 
        radial-gradient(circle at 25% 25%, rgba(0, 245, 212, 0.6) 0%, transparent 4%),
        radial-gradient(circle at 75% 25%, rgba(155, 93, 229, 0.6) 0%, transparent 4%),
        radial-gradient(circle at 50% 75%, rgba(254, 228, 64, 0.6) 0%, transparent 4%),
        radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.8) 0%, transparent 3%);
    animation: particleSwirl 12s linear infinite reverse;
}

/* ═══════════════════════════════════════════════════════════════════════════
   LAYER 2: TRIPLE ORBITAL RINGS - The 3 Systems in Motion
   ═══════════════════════════════════════════════════════════════════════════ */
/* Ring 1: Prior RTH Cones (Cyan) */
.orbital-ring-1 {
    position: absolute;
    width: 220px;
    height: 220px;
    top: 0;
    left: 10px;
    border: 2px solid transparent;
    border-top-color: var(--accent-cyan);
    border-radius: 50%;
    animation: orbit1 8s linear infinite;
    box-shadow: 0 0 20px var(--accent-cyan), inset 0 0 20px rgba(0, 245, 212, 0.1);
}

.orbital-ring-1::before {
    content: '◆';
    position: absolute;
    top: -8px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 16px;
    color: var(--accent-cyan);
    text-shadow: 0 0 20px var(--accent-cyan), 0 0 40px var(--accent-cyan);
    animation: orbitNodePulse 2s ease-in-out infinite;
}

@keyframes orbit1 {
    0% { transform: rotateX(70deg) rotateZ(0deg); }
    100% { transform: rotateX(70deg) rotateZ(360deg); }
}

/* Ring 2: Overnight Structure (Purple) */
.orbital-ring-2 {
    position: absolute;
    width: 200px;
    height: 200px;
    top: 10px;
    left: 20px;
    border: 2px solid transparent;
    border-top-color: var(--accent-purple);
    border-radius: 50%;
    animation: orbit2 10s linear infinite reverse;
    box-shadow: 0 0 20px var(--accent-purple), inset 0 0 20px rgba(155, 93, 229, 0.1);
}

.orbital-ring-2::before {
    content: '◆';
    position: absolute;
    top: -8px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 16px;
    color: var(--accent-purple);
    text-shadow: 0 0 20px var(--accent-purple), 0 0 40px var(--accent-purple);
    animation: orbitNodePulse 2s ease-in-out infinite 0.5s;
}

@keyframes orbit2 {
    0% { transform: rotateX(70deg) rotateY(60deg) rotateZ(0deg); }
    100% { transform: rotateX(70deg) rotateY(60deg) rotateZ(-360deg); }
}

/* Ring 3: VIX (Gold) */
.orbital-ring-3 {
    position: absolute;
    width: 180px;
    height: 180px;
    top: 20px;
    left: 30px;
    border: 2px solid transparent;
    border-top-color: var(--accent-gold);
    border-radius: 50%;
    animation: orbit3 6s linear infinite;
    box-shadow: 0 0 20px var(--accent-gold), inset 0 0 20px rgba(254, 228, 64, 0.1);
}

.orbital-ring-3::before {
    content: '◆';
    position: absolute;
    top: -8px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 16px;
    color: var(--accent-gold);
    text-shadow: 0 0 20px var(--accent-gold), 0 0 40px var(--accent-gold);
    animation: orbitNodePulse 2s ease-in-out infinite 1s;
}

@keyframes orbit3 {
    0% { transform: rotateX(70deg) rotateY(-60deg) rotateZ(0deg); }
    100% { transform: rotateX(70deg) rotateY(-60deg) rotateZ(360deg); }
}

@keyframes orbitNodePulse {
    0%, 100% { opacity: 1; transform: translateX(-50%) scale(1); }
    50% { opacity: 0.6; transform: translateX(-50%) scale(1.3); }
}

/* ═══════════════════════════════════════════════════════════════════════════
   LAYER 3: THE HOLOGRAPHIC PYRAMID - Main Structure
   ═══════════════════════════════════════════════════════════════════════════ */
.pyramid-container {
    position: absolute;
    width: 100%;
    height: 100%;
    top: 0;
    left: 0;
    animation: pyramidFloat 6s ease-in-out infinite;
    transform-style: preserve-3d;
}

@keyframes pyramidFloat {
    0%, 100% { transform: translateY(0) rotateY(0deg); }
    25% { transform: translateY(-8px) rotateY(3deg); }
    50% { transform: translateY(-12px) rotateY(0deg); }
    75% { transform: translateY(-8px) rotateY(-3deg); }
}

/* Pyramid Base Platform - Glowing */
.pyramid-base {
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    width: 160px;
    height: 20px;
    background: linear-gradient(180deg, rgba(0, 245, 212, 0.3) 0%, transparent 100%);
    border-radius: 50%;
    filter: blur(8px);
    animation: basePulse 3s ease-in-out infinite;
}

@keyframes basePulse {
    0%, 100% { opacity: 0.5; transform: translateX(-50%) scale(1); }
    50% { opacity: 0.8; transform: translateX(-50%) scale(1.1); }
}

/* Main Pyramid Body - Outer Layer */
.pyramid-main {
    position: absolute;
    top: 35px;
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 80px solid transparent;
    border-right: 80px solid transparent;
    border-bottom: 140px solid rgba(0, 245, 212, 0.08);
    filter: drop-shadow(0 0 40px rgba(0, 245, 212, 0.4));
    animation: pyramidGlow 4s ease-in-out infinite;
}

@keyframes pyramidGlow {
    0%, 100% { 
        filter: drop-shadow(0 0 30px rgba(0, 245, 212, 0.3)); 
        border-bottom-color: rgba(0, 245, 212, 0.08); 
    }
    50% { 
        filter: drop-shadow(0 0 60px rgba(0, 245, 212, 0.6)); 
        border-bottom-color: rgba(0, 245, 212, 0.15); 
    }
}

/* Pyramid Layer 2 - Purple */
.pyramid-layer-2 {
    position: absolute;
    top: 55px;
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 60px solid transparent;
    border-right: 60px solid transparent;
    border-bottom: 105px solid rgba(155, 93, 229, 0.1);
    animation: layer2Pulse 4s ease-in-out infinite 0.5s;
}

@keyframes layer2Pulse {
    0%, 100% { opacity: 0.6; border-bottom-color: rgba(155, 93, 229, 0.1); }
    50% { opacity: 1; border-bottom-color: rgba(155, 93, 229, 0.2); }
}

/* Pyramid Layer 3 - Gold Core */
.pyramid-layer-3 {
    position: absolute;
    top: 75px;
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 40px solid transparent;
    border-right: 40px solid transparent;
    border-bottom: 70px solid rgba(254, 228, 64, 0.12);
    animation: layer3Pulse 4s ease-in-out infinite 1s;
}

@keyframes layer3Pulse {
    0%, 100% { opacity: 0.5; border-bottom-color: rgba(254, 228, 64, 0.12); }
    50% { opacity: 1; border-bottom-color: rgba(254, 228, 64, 0.25); }
}

/* ═══════════════════════════════════════════════════════════════════════════
   LAYER 4: THE 3 PILLAR VERTICES - Energy Nodes
   ═══════════════════════════════════════════════════════════════════════════ */
/* Top Vertex - The Apex (Convergence Point) */
.vertex-top {
    position: absolute;
    top: 25px;
    left: 50%;
    transform: translateX(-50%);
    width: 24px;
    height: 24px;
    background: radial-gradient(circle, #fff 0%, var(--accent-cyan) 40%, transparent 70%);
    border-radius: 50%;
    box-shadow: 
        0 0 30px var(--accent-cyan),
        0 0 60px var(--accent-cyan),
        0 0 90px rgba(0, 245, 212, 0.5);
    animation: apexPulse 2s ease-in-out infinite;
}

@keyframes apexPulse {
    0%, 100% { 
        transform: translateX(-50%) scale(1);
        box-shadow: 0 0 30px var(--accent-cyan), 0 0 60px var(--accent-cyan);
    }
    50% { 
        transform: translateX(-50%) scale(1.3);
        box-shadow: 0 0 50px var(--accent-cyan), 0 0 100px var(--accent-cyan), 0 0 150px rgba(0, 245, 212, 0.3);
    }
}

.vertex-top::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 8px;
    height: 8px;
    background: #fff;
    border-radius: 50%;
    animation: coreFlicker 0.5s ease-in-out infinite;
}

@keyframes coreFlicker {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* Left Base Vertex - Prior RTH (Cyan) */
.vertex-left {
    position: absolute;
    bottom: 32px;
    left: 38px;
    width: 18px;
    height: 18px;
    background: radial-gradient(circle, #fff 0%, var(--accent-cyan) 50%, transparent 70%);
    border-radius: 50%;
    box-shadow: 0 0 25px var(--accent-cyan), 0 0 50px rgba(0, 245, 212, 0.4);
    animation: vertexPulse 3s ease-in-out infinite;
}

/* Right Base Vertex - Overnight (Purple) */
.vertex-right {
    position: absolute;
    bottom: 32px;
    right: 38px;
    width: 18px;
    height: 18px;
    background: radial-gradient(circle, #fff 0%, var(--accent-purple) 50%, transparent 70%);
    border-radius: 50%;
    box-shadow: 0 0 25px var(--accent-purple), 0 0 50px rgba(155, 93, 229, 0.4);
    animation: vertexPulse 3s ease-in-out infinite 1s;
}

/* Center Base Vertex - VIX (Gold) */
.vertex-center {
    position: absolute;
    bottom: 15px;
    left: 50%;
    transform: translateX(-50%);
    width: 18px;
    height: 18px;
    background: radial-gradient(circle, #fff 0%, var(--accent-gold) 50%, transparent 70%);
    border-radius: 50%;
    box-shadow: 0 0 25px var(--accent-gold), 0 0 50px rgba(254, 228, 64, 0.4);
    animation: vertexPulse 3s ease-in-out infinite 2s;
}

@keyframes vertexPulse {
    0%, 100% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.4); opacity: 1; }
}

/* ═══════════════════════════════════════════════════════════════════════════
   LAYER 5: ENERGY BEAMS - Connecting the Vertices
   ═══════════════════════════════════════════════════════════════════════════ */
/* Left Edge Beam (Top to Left) */
.energy-beam-left {
    position: absolute;
    top: 35px;
    left: 45px;
    width: 3px;
    height: 130px;
    background: linear-gradient(180deg, var(--accent-cyan) 0%, transparent 100%);
    transform: rotate(-30deg);
    transform-origin: top center;
    box-shadow: 0 0 15px var(--accent-cyan);
    animation: beamFlow 2s ease-in-out infinite;
}

.energy-beam-left::before {
    content: '';
    position: absolute;
    top: 0;
    left: -2px;
    width: 7px;
    height: 30px;
    background: linear-gradient(180deg, rgba(255,255,255,0.9) 0%, var(--accent-cyan) 50%, transparent 100%);
    border-radius: 3px;
    animation: beamParticle 2s ease-in-out infinite;
}

@keyframes beamFlow {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
}

@keyframes beamParticle {
    0% { top: 0; opacity: 1; }
    100% { top: 120px; opacity: 0; }
}

/* Right Edge Beam (Top to Right) */
.energy-beam-right {
    position: absolute;
    top: 35px;
    right: 45px;
    width: 3px;
    height: 130px;
    background: linear-gradient(180deg, var(--accent-purple) 0%, transparent 100%);
    transform: rotate(30deg);
    transform-origin: top center;
    box-shadow: 0 0 15px var(--accent-purple);
    animation: beamFlow 2s ease-in-out infinite 0.3s;
}

.energy-beam-right::before {
    content: '';
    position: absolute;
    top: 0;
    left: -2px;
    width: 7px;
    height: 30px;
    background: linear-gradient(180deg, rgba(255,255,255,0.9) 0%, var(--accent-purple) 50%, transparent 100%);
    border-radius: 3px;
    animation: beamParticle 2s ease-in-out infinite 0.3s;
}

/* Base Beam (Left to Right through Center) */
.energy-beam-base {
    position: absolute;
    bottom: 38px;
    left: 50%;
    transform: translateX(-50%);
    width: 140px;
    height: 3px;
    background: linear-gradient(90deg, var(--accent-cyan) 0%, var(--accent-gold) 50%, var(--accent-purple) 100%);
    box-shadow: 0 0 15px rgba(254, 228, 64, 0.5);
    animation: baseBeamPulse 3s ease-in-out infinite;
}

@keyframes baseBeamPulse {
    0%, 100% { opacity: 0.5; width: 140px; }
    50% { opacity: 1; width: 150px; }
}

/* ═══════════════════════════════════════════════════════════════════════════
   LAYER 6: HOLOGRAPHIC SCAN LINES - Tech Effect
   ═══════════════════════════════════════════════════════════════════════════ */
.scan-line {
    position: absolute;
    top: 30px;
    left: 50%;
    transform: translateX(-50%);
    width: 160px;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent);
    opacity: 0.6;
    animation: scanMove 3s ease-in-out infinite;
}

@keyframes scanMove {
    0% { top: 30px; opacity: 0; }
    10% { opacity: 0.8; }
    90% { opacity: 0.8; }
    100% { top: 170px; opacity: 0; }
}

.scan-line-2 {
    position: absolute;
    top: 30px;
    left: 50%;
    transform: translateX(-50%);
    width: 160px;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent-purple), transparent);
    opacity: 0.6;
    animation: scanMove 3s ease-in-out infinite 1.5s;
}

/* ═══════════════════════════════════════════════════════════════════════════
   LAYER 7: DATA STREAMS - Flowing Numbers Effect
   ═══════════════════════════════════════════════════════════════════════════ */
.data-stream-left {
    position: absolute;
    top: 50px;
    left: 25px;
    width: 20px;
    height: 100px;
    overflow: hidden;
    opacity: 0.4;
}

.data-stream-left::before {
    content: '0110 1001 0011 1100 0101 1010 0111 1000';
    position: absolute;
    font-family: 'Share Tech Mono', monospace;
    font-size: 8px;
    color: var(--accent-cyan);
    writing-mode: vertical-rl;
    animation: dataFlow 4s linear infinite;
    text-shadow: 0 0 10px var(--accent-cyan);
}

@keyframes dataFlow {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(100%); }
}

.data-stream-right {
    position: absolute;
    top: 50px;
    right: 25px;
    width: 20px;
    height: 100px;
    overflow: hidden;
    opacity: 0.4;
}

.data-stream-right::before {
    content: '1101 0010 1110 0001 1011 0100 1111 0000';
    position: absolute;
    font-family: 'Share Tech Mono', monospace;
    font-size: 8px;
    color: var(--accent-purple);
    writing-mode: vertical-rl;
    animation: dataFlow 4s linear infinite 2s;
    text-shadow: 0 0 10px var(--accent-purple);
}

/* ═══════════════════════════════════════════════════════════════════════════
   LAYER 8: PILLAR LABELS - The 3 Systems
   ═══════════════════════════════════════════════════════════════════════════ */
.pillar-label-left {
    position: absolute;
    bottom: 0px;
    left: 10px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 7px;
    color: var(--accent-cyan);
    text-transform: uppercase;
    letter-spacing: 1px;
    opacity: 0.7;
    text-shadow: 0 0 10px var(--accent-cyan);
    animation: labelPulse 4s ease-in-out infinite;
}

.pillar-label-right {
    position: absolute;
    bottom: 0px;
    right: 5px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 7px;
    color: var(--accent-purple);
    text-transform: uppercase;
    letter-spacing: 1px;
    opacity: 0.7;
    text-shadow: 0 0 10px var(--accent-purple);
    animation: labelPulse 4s ease-in-out infinite 1s;
}

.pillar-label-center {
    position: absolute;
    bottom: -8px;
    left: 50%;
    transform: translateX(-50%);
    font-family: 'Share Tech Mono', monospace;
    font-size: 7px;
    color: var(--accent-gold);
    text-transform: uppercase;
    letter-spacing: 1px;
    opacity: 0.7;
    text-shadow: 0 0 10px var(--accent-gold);
    animation: labelPulse 4s ease-in-out infinite 2s;
}

@keyframes labelPulse {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
}

/* ═══════════════════════════════════════════════════════════════════════════
   LAYER 9: AMBIENT GLOW - Overall Atmosphere
   ═══════════════════════════════════════════════════════════════════════════ */
.ambient-glow {
    position: absolute;
    width: 300px;
    height: 250px;
    top: -15px;
    left: -30px;
    background: radial-gradient(ellipse at center, 
        rgba(0, 245, 212, 0.15) 0%, 
        rgba(155, 93, 229, 0.1) 30%,
        rgba(254, 228, 64, 0.05) 50%,
        transparent 70%);
    filter: blur(20px);
    animation: ambientPulse 5s ease-in-out infinite;
    pointer-events: none;
}

@keyframes ambientPulse {
    0%, 100% { opacity: 0.6; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.1); }
}

/* ═══════════════════════════════════════════════════════════════════════════
   HERO CONTENT - EPIC TYPOGRAPHY
   ═══════════════════════════════════════════════════════════════════════════ */
.hero-content {
    position: relative;
    z-index: 2;
    text-align: center;
    margin-top: 15px;
}

.brand-name {
    font-family: 'Orbitron', sans-serif;
    font-size: 3.2rem;
    font-weight: 900;
    letter-spacing: 14px;
    background: linear-gradient(135deg, 
        var(--accent-cyan) 0%, 
        #00d4ff 20%, 
        #fff 40%,
        var(--accent-purple) 60%, 
        #f15bb5 80%, 
        var(--accent-cyan) 100%);
    background-size: 400% 400%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    text-transform: uppercase;
    animation: brandShimmer 8s ease-in-out infinite;
    filter: drop-shadow(0 0 40px rgba(0, 245, 212, 0.4));
}

@keyframes brandShimmer {
    0%, 100% { background-position: 0% 50%; }
    25% { background-position: 50% 0%; }
    50% { background-position: 100% 50%; }
    75% { background-position: 50% 100%; }
}

.brand-tagline {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.1rem;
    color: rgba(255, 255, 255, 0.6);
    letter-spacing: 10px;
    margin-top: 15px;
    text-transform: uppercase;
    font-weight: 600;
}

/* ═══════════════════════════════════════════════════════════════════════════
   UNIFIED CARD SYSTEM - Professional Trading Panels
   ═══════════════════════════════════════════════════════════════════════════ */
.glass-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px;
    height: 100%;
    min-height: 140px;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--gradient-card);
    pointer-events: none;
}

.glass-card:hover {
    border-color: var(--border-strong);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}

.glass-card-calls {
    background: linear-gradient(135deg, var(--bull-soft) 0%, transparent 60%);
    border-color: rgba(0, 214, 125, 0.2);
}

.glass-card-calls::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--gradient-bull);
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.glass-card-puts {
    background: linear-gradient(135deg, var(--bear-soft) 0%, transparent 60%);
    border-color: rgba(255, 82, 99, 0.2);
}

.glass-card-puts::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--gradient-bear);
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

/* Indicator Cards - Equal height guaranteed with enhanced icons */
.indicator-card {
    background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-panel) 100%);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    padding: 24px;
    height: 100%;
    min-height: 180px;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
    position: relative;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.indicator-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--gradient-card);
    pointer-events: none;
    border-radius: var(--radius-xl);
}

.indicator-card::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--gradient-premium);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.indicator-card:hover {
    border-color: var(--border-accent);
    box-shadow: var(--shadow-glow-cyan), var(--shadow-md);
    transform: translateY(-3px);
}

.indicator-card:hover::after {
    opacity: 1;
}

.indicator-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 18px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-subtle);
    position: relative;
    z-index: 1;
}

.indicator-icon {
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(0, 245, 212, 0.15) 0%, rgba(0, 187, 249, 0.08) 100%);
    border: 2px solid var(--accent-cyan);
    border-radius: var(--radius-lg);
    font-size: 2rem;
    box-shadow: 0 0 25px rgba(0, 245, 212, 0.3);
    animation: indicatorIconPulse 3s ease-in-out infinite;
}

@keyframes indicatorIconPulse {
    0%, 100% { box-shadow: 0 0 20px rgba(0, 245, 212, 0.25); transform: scale(1); }
    50% { box-shadow: 0 0 35px rgba(0, 245, 212, 0.5); transform: scale(1.05); }
}

.indicator-title {
    font-family: var(--font-display);
    font-size: var(--text-md);
    font-weight: 700;
    color: var(--text-bright);
    letter-spacing: 1px;
}

.indicator-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    font-size: var(--text-sm);
    position: relative;
    z-index: 1;
}

.indicator-label {
    font-family: var(--font-body);
    color: var(--text-muted);
    font-weight: 500;
}

.indicator-value {
    color: var(--text-bright);
    font-weight: 700;
    font-family: var(--font-display);
    font-size: var(--text-sm);
    letter-spacing: 0.5px;
}

.indicator-status {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 12px 16px;
    border-radius: var(--radius-md);
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    font-weight: 700;
    margin-top: auto;
    position: relative;
    z-index: 1;
    letter-spacing: 0.5px;
}

.indicator-status-bullish {
    background: var(--bull-medium);
    color: var(--bull);
    border: 1px solid rgba(0, 214, 125, 0.3);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
}

.indicator-status-bearish {
    background: var(--bear-medium);
    color: var(--bear);
    border: 1px solid rgba(255, 82, 99, 0.3);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
}

/* ═══════════════════════════════════════════════════════════════════════════
   SECTION HEADERS - Premium Dividers with Large Icons
   ═══════════════════════════════════════════════════════════════════════════ */
.section-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    margin: 56px 0 32px 0;
    padding: 32px 0;
    position: relative;
    text-align: center;
}

.section-header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 200px;
    height: 3px;
    background: var(--gradient-premium);
    box-shadow: 0 0 20px rgba(0, 245, 212, 0.5);
    border-radius: 2px;
}

.section-header::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 120px;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent);
}

.section-icon {
    width: 80px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(145deg, rgba(0, 245, 212, 0.12) 0%, rgba(0, 187, 249, 0.08) 50%, rgba(155, 93, 229, 0.06) 100%);
    border: 2px solid transparent;
    border-image: var(--gradient-premium) 1;
    border-radius: 20px;
    font-size: 2.5rem;
    box-shadow: 
        0 0 40px rgba(0, 245, 212, 0.25),
        0 0 80px rgba(0, 245, 212, 0.1),
        inset 0 0 30px rgba(0, 245, 212, 0.08);
    color: var(--accent-cyan);
    text-shadow: 0 0 20px var(--accent-cyan);
    animation: iconFloat 4s ease-in-out infinite;
    position: relative;
}

.section-icon::before {
    content: '';
    position: absolute;
    inset: -4px;
    border-radius: 24px;
    background: var(--gradient-premium);
    opacity: 0.3;
    filter: blur(8px);
    z-index: -1;
    animation: iconGlow 3s ease-in-out infinite;
}

@keyframes iconFloat {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
}

@keyframes iconGlow {
    0%, 100% { opacity: 0.2; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(1.05); }
}

.section-title {
    font-family: 'Orbitron', sans-serif !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: var(--text-bright) !important;
    margin: 0 !important;
    letter-spacing: 3px !important;
    text-transform: uppercase !important;
    text-shadow: 0 0 30px rgba(255, 255, 255, 0.15);
    background: linear-gradient(135deg, var(--text-bright) 0%, var(--accent-cyan) 50%, var(--text-bright) 100%);
    background-size: 200% 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: titleShimmer 6s ease-in-out infinite;
}

@keyframes titleShimmer {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

/* Section-specific icon colors */
.section-icon-bullish {
    background: linear-gradient(145deg, rgba(0, 214, 125, 0.15) 0%, rgba(0, 255, 136, 0.08) 100%);
    border-color: var(--bull);
    color: var(--bull);
    text-shadow: 0 0 20px var(--bull-glow);
    box-shadow: 
        0 0 40px rgba(0, 214, 125, 0.25),
        0 0 80px rgba(0, 214, 125, 0.1),
        inset 0 0 30px rgba(0, 214, 125, 0.08);
}

.section-icon-bearish {
    background: linear-gradient(145deg, rgba(255, 82, 99, 0.15) 0%, rgba(255, 51, 102, 0.08) 100%);
    border-color: var(--bear);
    color: var(--bear);
    text-shadow: 0 0 20px var(--bear-glow);
    box-shadow: 
        0 0 40px rgba(255, 82, 99, 0.25),
        0 0 80px rgba(255, 82, 99, 0.1),
        inset 0 0 30px rgba(255, 82, 99, 0.08);
}

.section-icon-gold {
    background: linear-gradient(145deg, rgba(254, 228, 64, 0.15) 0%, rgba(245, 184, 0, 0.08) 100%);
    border-color: var(--accent-gold);
    color: var(--accent-gold);
    text-shadow: 0 0 20px rgba(254, 228, 64, 0.5);
    box-shadow: 
        0 0 40px rgba(254, 228, 64, 0.25),
        0 0 80px rgba(254, 228, 64, 0.1),
        inset 0 0 30px rgba(254, 228, 64, 0.08);
}

.section-icon-purple {
    background: linear-gradient(145deg, rgba(155, 93, 229, 0.15) 0%, rgba(139, 92, 246, 0.08) 100%);
    border-color: var(--accent-purple);
    color: var(--accent-purple);
    text-shadow: 0 0 20px rgba(155, 93, 229, 0.5);
    box-shadow: 
        0 0 40px rgba(155, 93, 229, 0.25),
        0 0 80px rgba(155, 93, 229, 0.1),
        inset 0 0 30px rgba(155, 93, 229, 0.08);
}

/* ═══════════════════════════════════════════════════════════════════════════
   METRIC CARDS - Top Row KPIs with Icons
   ═══════════════════════════════════════════════════════════════════════════ */
.metric-card {
    background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-panel) 100%);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 22px 26px;
    text-align: center;
    height: 100%;
    min-height: 140px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, transparent 50%);
    pointer-events: none;
}

.metric-card::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--gradient-cyber);
    opacity: 0;
    transition: opacity 0.3s ease;
}

.metric-card:hover {
    border-color: var(--border-accent);
    transform: translateY(-4px) scale(1.02);
    box-shadow: var(--shadow-glow-cyan), var(--shadow-md);
}

.metric-card:hover::after {
    opacity: 1;
}

.metric-icon {
    font-size: 3.2rem;
    margin-bottom: 12px;
    filter: drop-shadow(0 0 20px rgba(0, 245, 212, 0.5));
    position: relative;
    display: inline-block;
}

.metric-icon::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 70px;
    height: 70px;
    background: radial-gradient(circle, rgba(0, 245, 212, 0.2) 0%, transparent 70%);
    border-radius: 50%;
    z-index: -1;
}

/* ═══════════════════════════════════════════════════════════════════════════
   ICON GLOW VARIANTS - Color-coded halos for different contexts
   ═══════════════════════════════════════════════════════════════════════════ */

/* Green glow for bullish/up */
.icon-glow-green {
    filter: drop-shadow(0 0 20px rgba(0, 214, 125, 0.6)) !important;
}
.icon-glow-green::after {
    background: radial-gradient(circle, rgba(0, 214, 125, 0.25) 0%, transparent 70%) !important;
}

/* Red glow for bearish/down */
.icon-glow-red {
    filter: drop-shadow(0 0 20px rgba(255, 82, 99, 0.6)) !important;
}
.icon-glow-red::after {
    background: radial-gradient(circle, rgba(255, 82, 99, 0.25) 0%, transparent 70%) !important;
}

/* Orange glow for high volatility */
.icon-glow-orange {
    filter: drop-shadow(0 0 25px rgba(255, 120, 50, 0.7)) !important;
}
.icon-glow-orange::after {
    background: radial-gradient(circle, rgba(255, 120, 50, 0.3) 0%, transparent 70%) !important;
}

/* Blue glow for calm/ice */
.icon-glow-blue {
    filter: drop-shadow(0 0 20px rgba(150, 220, 255, 0.6)) !important;
}
.icon-glow-blue::after {
    background: radial-gradient(circle, rgba(150, 220, 255, 0.25) 0%, transparent 70%) !important;
}

/* Gold glow for neutral/balance */
.icon-glow-gold {
    filter: drop-shadow(0 0 20px rgba(254, 228, 64, 0.6)) !important;
}
.icon-glow-gold::after {
    background: radial-gradient(circle, rgba(254, 228, 64, 0.25) 0%, transparent 70%) !important;
}

/* Purple glow for overnight/moon */
.icon-glow-purple {
    filter: drop-shadow(0 0 20px rgba(180, 160, 255, 0.6)) !important;
}
.icon-glow-purple::after {
    background: radial-gradient(circle, rgba(180, 160, 255, 0.25) 0%, transparent 70%) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   MEANINGFUL ANIMATIONS - Only for icons where movement makes sense
   ═══════════════════════════════════════════════════════════════════════════ */

/* 🦘 Kangaroo - Hops up and down */
.icon-kangaroo {
    animation: kangarooHop 1.2s ease-in-out infinite;
}
@keyframes kangarooHop {
    0%, 100% { transform: translateY(0); }
    30% { transform: translateY(-15px); }
    50% { transform: translateY(-18px); }
    80% { transform: translateY(0); }
}

/* 🚀 Rocket - Slight shake/vibration before launch */
.icon-rocket {
    animation: rocketShake 0.5s ease-in-out infinite;
}
@keyframes rocketShake {
    0%, 100% { transform: translate(0, 0) rotate(-2deg); }
    25% { transform: translate(1px, -1px) rotate(0deg); }
    50% { transform: translate(-1px, 0) rotate(2deg); }
    75% { transform: translate(1px, 1px) rotate(0deg); }
}

/* 🔄 Rotate symbol - Continuous rotation */
.icon-rotate {
    animation: iconSpin 3s linear infinite;
}
@keyframes iconSpin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* 🕐 Clock - Gentle pulse like a heartbeat */
.icon-clock {
    animation: clockPulse 1.5s ease-in-out infinite;
}
@keyframes clockPulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.08); }
}

.metric-label {
    font-family: var(--font-mono);
    font-size: var(--text-xxs);
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 2.5px;
    margin-bottom: 12px;
    font-weight: 600;
    position: relative;
    z-index: 1;
}

.metric-value {
    font-family: var(--font-display);
    font-size: var(--text-2xl);
    font-weight: 800;
    color: var(--text-bright);
    line-height: 1;
    position: relative;
    z-index: 1;
    letter-spacing: 1px;
}

.metric-value.accent { 
    color: var(--accent-cyan); 
    text-shadow: 0 0 20px var(--accent-cyan-glow), 0 0 40px rgba(0, 245, 212, 0.2);
    animation: valueGlow 3s ease-in-out infinite;
}

@keyframes valueGlow {
    0%, 100% { text-shadow: 0 0 15px var(--accent-cyan-glow); }
    50% { text-shadow: 0 0 30px var(--accent-cyan-glow), 0 0 50px rgba(0, 245, 212, 0.3); }
}

.metric-value.calls { color: var(--bull); text-shadow: 0 0 25px var(--bull-glow); }
.metric-value.puts { color: var(--bear); text-shadow: 0 0 25px var(--bear-glow); }
.metric-value.gold { color: var(--accent-gold); text-shadow: 0 0 25px rgba(254, 228, 64, 0.4); }

.metric-delta {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-secondary);
    margin-top: 12px;
    position: relative;
    z-index: 1;
    font-weight: 500;
}

/* ═══════════════════════════════════════════════════════════════════════════
   BIAS PILLS & CHANNEL BADGES
   ═══════════════════════════════════════════════════════════════════════════ */
.bias-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 14px 24px;
    border-radius: 50px;
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    transition: all 0.2s ease;
}

.bias-pill-calls {
    background: var(--bull-medium);
    border: 1px solid rgba(0, 214, 125, 0.4);
    color: var(--bull);
    box-shadow: 0 0 20px var(--bull-soft);
}

.bias-pill-puts {
    background: var(--bear-medium);
    border: 1px solid rgba(255, 82, 99, 0.4);
    color: var(--bear);
    box-shadow: 0 0 20px var(--bear-soft);
}

.bias-pill-neutral {
    background: rgba(100, 116, 139, 0.15);
    border: 1px solid rgba(100, 116, 139, 0.3);
    color: var(--neutral);
}

.channel-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 14px 24px;
    border-radius: var(--radius-md);
    font-family: var(--font-display);
    font-size: var(--text-sm);
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
}

.channel-badge::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
    animation: badgeShine 4s ease-in-out infinite;
}

@keyframes badgeShine {
    0% { left: -100%; }
    50%, 100% { left: 100%; }
}

.channel-badge-ascending {
    background: linear-gradient(135deg, var(--bull-medium) 0%, var(--bull-soft) 100%);
    border: 1px solid rgba(0, 214, 125, 0.4);
    color: var(--bull);
    box-shadow: var(--shadow-glow-bull);
}

.channel-badge-descending {
    background: linear-gradient(135deg, var(--bear-medium) 0%, var(--bear-soft) 100%);
    border: 1px solid rgba(255, 82, 99, 0.4);
    color: var(--bear);
    box-shadow: var(--shadow-glow-bear);
}

.channel-badge-mixed {
    background: linear-gradient(135deg, rgba(245, 184, 0, 0.2) 0%, rgba(245, 184, 0, 0.08) 100%);
    border: 1px solid rgba(245, 184, 0, 0.4);
    color: var(--accent-gold);
    box-shadow: 0 0 20px rgba(245, 184, 0, 0.15);
}

.channel-badge-contracting {
    background: linear-gradient(135deg, var(--accent-gold-soft) 0%, transparent 100%);
    border: 1px solid rgba(245, 184, 0, 0.3);
    color: var(--accent-gold);
}

/* ═══════════════════════════════════════════════════════════════════════════
   LEVELS DISPLAY - Price Levels Panel
   ═══════════════════════════════════════════════════════════════════════════ */
.levels-container {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 24px;
    position: relative;
    overflow: hidden;
}

.levels-container::before {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--gradient-card);
    pointer-events: none;
}

.level-row {
    display: flex;
    align-items: center;
    padding: 18px 0;
    border-bottom: 1px solid var(--border-subtle);
    gap: 28px;
    position: relative;
    z-index: 1;
    transition: all 0.25s ease;
}

.level-row:hover {
    background: rgba(0, 245, 212, 0.03);
    margin: 0 -24px;
    padding: 18px 24px;
    border-radius: 8px;
}

.level-row:last-child { border-bottom: none; }

.level-label {
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    min-width: 150px;
}

.level-label.ceiling { color: var(--bear); text-shadow: 0 0 10px rgba(255, 51, 102, 0.3); }
.level-label.current { color: var(--accent-gold); text-shadow: 0 0 10px rgba(254, 228, 64, 0.3); }
.level-label.floor { color: var(--bull); text-shadow: 0 0 10px rgba(0, 255, 136, 0.3); }

.level-value {
    font-family: var(--font-display);
    font-size: var(--text-xl);
    font-weight: 800;
    min-width: 160px;
    text-align: right;
    letter-spacing: 1px;
}

.level-value.ceiling { color: var(--bear); text-shadow: 0 0 20px var(--bear-glow); }
.level-value.current { color: var(--accent-gold); text-shadow: 0 0 25px rgba(254, 228, 64, 0.5); animation: currentPulse 2s ease-in-out infinite; }
.level-value.floor { color: var(--bull); text-shadow: 0 0 20px var(--bull-glow); }

@keyframes currentPulse {
    0%, 100% { text-shadow: 0 0 20px rgba(254, 228, 64, 0.4); }
    50% { text-shadow: 0 0 35px rgba(254, 228, 64, 0.7), 0 0 50px rgba(254, 228, 64, 0.3); }
}

.level-note {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin-left: auto;
    text-align: right;
}

/* ═══════════════════════════════════════════════════════════════════════════
   PRIOR DAY LEVELS
   ═══════════════════════════════════════════════════════════════════════════ */
.prior-levels-container {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
}

.prior-levels-section {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px;
    position: relative;
}

.prior-levels-section::before {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--gradient-card);
    pointer-events: none;
    border-radius: var(--radius-lg);
}

.prior-levels-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border-subtle);
    position: relative;
    z-index: 1;
}

.prior-levels-icon { font-size: var(--text-lg); }

.prior-levels-title {
    font-family: var(--font-display);
    font-size: var(--text-sm);
    font-weight: 700;
    color: var(--text-bright);
    letter-spacing: 0.5px;
}

.prior-levels-anchor {
    margin-left: auto;
    font-family: var(--font-display);
    font-size: var(--text-sm);
    color: var(--accent-cyan);
    font-weight: 700;
    letter-spacing: 0.5px;
}

.prior-levels-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 12px;
    position: relative;
    z-index: 1;
}

.prior-level-item {
    background: var(--bg-elevated);
    border-radius: var(--radius-md);
    padding: 14px;
    text-align: center;
    transition: all 0.2s ease;
}

.prior-level-item:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
}

.prior-level-buy { border-left: 3px solid var(--bull); }
.prior-level-sell { border-left: 3px solid var(--bear); }

.prior-level-direction {
    font-family: var(--font-mono);
    font-size: var(--text-xxs);
    color: var(--text-muted);
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}

.prior-level-value {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 800;
    color: var(--text-bright);
    margin-bottom: 8px;
    letter-spacing: 0.5px;
}

.prior-level-item.prior-level-buy .prior-level-action { color: var(--bull); }
.prior-level-item.prior-level-sell .prior-level-action { color: var(--bear); }

.prior-level-action {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.prior-levels-note {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    color: var(--text-dim);
    font-style: italic;
    text-align: center;
    position: relative;
    z-index: 1;
}

.prior-day-info {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 18px;
    margin-top: 14px;
    background: var(--bg-elevated);
    border-radius: var(--radius-md);
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-secondary);
}

.prior-day-label {
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-size: var(--text-xs);
    font-weight: 600;
}

.prior-day-sep { color: var(--text-dim); }

/* ═══════════════════════════════════════════════════════════════════════════
   CONFLUENCE CARDS
   ═══════════════════════════════════════════════════════════════════════════ */
.confluence-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 24px;
    height: 100%;
    position: relative;
    overflow: hidden;
}

.confluence-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--gradient-card);
    pointer-events: none;
}

.confluence-card-calls {
    border-top: 3px solid var(--bull);
}

.confluence-card-puts {
    border-top: 3px solid var(--bear);
}

.confluence-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-subtle);
    position: relative;
    z-index: 1;
}

.confluence-title {
    font-family: var(--font-display);
    font-size: var(--text-md);
    font-weight: 700;
    color: var(--text-bright);
    letter-spacing: 0.5px;
}

.confluence-score {
    font-family: var(--font-display);
    font-size: var(--text-2xl);
    font-weight: 900;
    padding: 8px 16px;
    border-radius: var(--radius-md);
}

.confluence-score.high {
    background: var(--bull-medium);
    color: var(--bull);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.1);
}

.confluence-score.medium {
    background: var(--accent-gold-soft);
    color: var(--accent-gold);
}

.confluence-score.low {
    background: var(--bear-medium);
    color: var(--bear);
}

.confluence-factor {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 0;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--text-secondary);
    border-bottom: 1px solid var(--border-subtle);
    position: relative;
    z-index: 1;
    transition: all 0.2s ease;
}

.confluence-factor:hover {
    color: var(--text-primary);
    background: rgba(255,255,255,0.02);
    margin: 0 -24px;
    padding: 12px 24px;
}

.confluence-factor:last-child { border-bottom: none; }

.factor-check {
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    font-size: var(--text-xs);
    flex-shrink: 0;
    font-weight: 700;
}

.factor-check.active {
    background: var(--bull-medium);
    color: var(--bull);
    box-shadow: 0 0 8px var(--bull-soft);
}

.factor-check.inactive {
    background: var(--bg-elevated);
    color: var(--text-dim);
}

/* ═══════════════════════════════════════════════════════════════════════════
   TRADE CARDS - Premium Action Cards with Glow Effects
   ═══════════════════════════════════════════════════════════════════════════ */
.trade-card {
    background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-panel) 100%);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    padding: 32px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.trade-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 5px;
}

.trade-card::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(255,255,255,0.03) 0%, transparent 30%);
    pointer-events: none;
}

.trade-card-calls {
    border-color: rgba(0, 255, 136, 0.2);
}

.trade-card-calls::before {
    background: var(--gradient-bull);
    box-shadow: 0 0 30px var(--bull-glow), 0 0 60px rgba(0, 255, 136, 0.2);
}

.trade-card-calls:hover {
    border-color: rgba(0, 255, 136, 0.4);
    box-shadow: var(--shadow-glow-bull), var(--shadow-lg);
    transform: translateY(-4px);
}

.trade-card-puts {
    border-color: rgba(255, 51, 102, 0.2);
}

.trade-card-puts::before {
    background: var(--gradient-bear);
    box-shadow: 0 0 30px var(--bear-glow), 0 0 60px rgba(255, 51, 102, 0.2);
}

.trade-card-puts:hover {
    border-color: rgba(255, 51, 102, 0.4);
    box-shadow: var(--shadow-glow-bear), var(--shadow-lg);
    transform: translateY(-4px);
}

.trade-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    position: relative;
    z-index: 2;
}

.trade-name {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 800;
    color: var(--text-bright);
    letter-spacing: 1px;
}

.trade-confidence {
    padding: 10px 20px;
    border-radius: 50px;
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    position: relative;
    z-index: 2;
}

.trade-confidence-high {
    background: linear-gradient(135deg, rgba(0, 255, 136, 0.25) 0%, rgba(0, 245, 212, 0.15) 100%);
    color: var(--bull);
    border: 1px solid rgba(0, 255, 136, 0.5);
    box-shadow: 0 0 20px rgba(0, 255, 136, 0.2), inset 0 0 15px rgba(0, 255, 136, 0.1);
    animation: highConfPulse 2s ease-in-out infinite;
}

@keyframes highConfPulse {
    0%, 100% { box-shadow: 0 0 15px rgba(0, 255, 136, 0.2); }
    50% { box-shadow: 0 0 30px rgba(0, 255, 136, 0.4), 0 0 45px rgba(0, 255, 136, 0.2); }
}

.trade-confidence-medium {
    background: linear-gradient(135deg, rgba(254, 228, 64, 0.2) 0%, rgba(255, 150, 0, 0.1) 100%);
    color: var(--accent-gold);
    border: 1px solid rgba(254, 228, 64, 0.5);
    box-shadow: 0 0 15px rgba(254, 228, 64, 0.15);
}

.trade-confidence-low {
    background: var(--bg-elevated);
    color: var(--text-muted);
    border: 1px solid var(--border-default);
}

.trade-contract {
    font-family: var(--font-mono);
    font-size: var(--text-xl);
    font-weight: 700;
    padding: 18px 24px;
    border-radius: var(--radius-md);
    text-align: center;
    margin-bottom: 20px;
}

.trade-contract-calls {
    background: var(--bull-medium);
    color: var(--bull);
    border: 1px solid rgba(0, 214, 125, 0.3);
}

.trade-contract-puts {
    background: var(--bear-medium);
    color: var(--bear);
    border: 1px solid rgba(255, 82, 99, 0.3);
}

.trade-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-bottom: 20px;
}

.trade-metric {
    background: var(--bg-elevated);
    border-radius: var(--radius-md);
    padding: 16px;
    text-align: center;
    transition: all 0.2s ease;
}

.trade-metric:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
}

.trade-metric-label {
    font-family: var(--font-mono);
    font-size: var(--text-xxs);
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 8px;
    font-weight: 600;
}

.trade-metric-value {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 800;
    color: var(--text-bright);
    letter-spacing: 0.5px;
}

.trade-targets {
    background: var(--bg-elevated);
    border-radius: var(--radius-md);
    padding: 18px;
}

.targets-header {
    font-family: var(--font-mono);
    font-size: var(--text-xxs);
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 14px;
    font-weight: 600;
}

.targets-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
}

.target-item {
    text-align: center;
    padding: 14px;
    border-radius: var(--radius-md);
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    transition: all 0.2s ease;
}

.target-item:hover {
    border-color: var(--border-accent);
    transform: translateY(-2px);
}

.target-label {
    font-size: var(--text-xs);
    color: var(--text-muted);
    margin-bottom: 6px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.target-price {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 800;
    color: var(--text-bright);
    letter-spacing: 0.5px;
}

.target-profit {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--bull);
    margin-top: 6px;
    font-weight: 600;
}

.trade-trigger {
    margin-top: 18px;
    padding: 16px 20px;
    background: linear-gradient(135deg, rgba(0, 229, 199, 0.08) 0%, transparent 100%);
    border-radius: var(--radius-md);
    border-left: 3px solid var(--accent-cyan);
}

.trigger-label {
    font-family: var(--font-mono);
    font-size: var(--text-xxs);
    color: var(--accent-cyan);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 6px;
    font-weight: 700;
}

.trigger-text {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--text-secondary);
    line-height: 1.5;
}

/* ═══════════════════════════════════════════════════════════════════════════
   SESSION CARDS - Global Market Sessions with Large Icons
   ═══════════════════════════════════════════════════════════════════════════ */
.session-card {
    background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-panel) 100%);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    padding: 24px 20px;
    text-align: center;
    height: 100%;
    min-height: 180px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

.session-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--gradient-card);
    pointer-events: none;
}

.session-card::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--gradient-premium);
    opacity: 0;
    transition: opacity 0.3s ease;
}

.session-card:hover {
    border-color: var(--border-accent);
    transform: translateY(-5px);
    box-shadow: var(--shadow-glow-cyan), var(--shadow-md);
}

.session-card:hover::after {
    opacity: 1;
}

.session-icon {
    font-size: 3.5rem;
    margin-bottom: 14px;
    position: relative;
    z-index: 1;
    filter: drop-shadow(0 0 20px rgba(0, 245, 212, 0.5));
    display: inline-block;
}

.session-icon::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 80px;
    height: 80px;
    background: radial-gradient(circle, rgba(0, 245, 212, 0.2) 0%, transparent 70%);
    border-radius: 50%;
    z-index: -1;
    animation: iconHalo 3s ease-in-out infinite;
}

.session-name {
    font-family: var(--font-display);
    font-size: var(--text-md);
    font-weight: 700;
    color: var(--text-bright);
    margin-bottom: 14px;
    position: relative;
    z-index: 1;
    letter-spacing: 1px;
}

.session-data {
    display: flex;
    flex-direction: column;
    gap: 8px;
    position: relative;
    z-index: 1;
}

.session-value {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: var(--font-display);
    font-size: var(--text-sm);
    font-weight: 600;
    letter-spacing: 0.5px;
}

.session-high { color: var(--bear); }
.session-low { color: var(--bull); }

/* ═══════════════════════════════════════════════════════════════════════════
   ALERT BOXES
   ═══════════════════════════════════════════════════════════════════════════ */
.alert-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 12px;
    padding: 28px 24px;
    border-radius: var(--radius-lg);
    margin: 16px 0;
    position: relative;
    overflow: hidden;
}

.alert-box::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    width: 100%;
    height: 4px;
}

.alert-box-warning {
    background: linear-gradient(135deg, rgba(245, 184, 0, 0.1) 0%, transparent 60%);
    border: 1px solid rgba(245, 184, 0, 0.25);
}
.alert-box-warning::before { background: var(--accent-gold); }

.alert-box-danger {
    background: linear-gradient(135deg, var(--bear-soft) 0%, transparent 60%);
    border: 1px solid rgba(255, 82, 99, 0.25);
}
.alert-box-danger::before { background: var(--bear); }

.alert-box-success {
    background: linear-gradient(135deg, var(--bull-soft) 0%, transparent 60%);
    border: 1px solid rgba(0, 214, 125, 0.25);
}
.alert-box-success::before { background: var(--bull); }

.alert-box-info {
    background: linear-gradient(135deg, rgba(77, 166, 255, 0.1) 0%, transparent 60%);
    border: 1px solid rgba(77, 166, 255, 0.25);
}
.alert-box-info::before { background: var(--accent-blue); }

.alert-icon {
    font-size: var(--text-xl);
    flex-shrink: 0;
    margin-top: 2px;
}

.alert-icon-large {
    font-size: 3.5rem;
    flex-shrink: 0;
    filter: drop-shadow(0 0 20px rgba(0, 245, 212, 0.5));
    line-height: 1;
}

.alert-box-warning .alert-icon-large {
    filter: drop-shadow(0 0 25px rgba(245, 184, 0, 0.6));
}

.alert-box-danger .alert-icon-large {
    filter: drop-shadow(0 0 25px rgba(255, 82, 99, 0.6));
}

.alert-box-success .alert-icon-large {
    filter: drop-shadow(0 0 25px rgba(0, 214, 125, 0.6));
}

.alert-content { 
    flex: 1;
    text-align: center;
}

.alert-title {
    font-family: var(--font-display);
    font-size: var(--text-md);
    font-weight: 700;
    color: var(--text-bright);
    margin-bottom: 6px;
    letter-spacing: 1px;
}

.alert-text {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--text-secondary);
    line-height: 1.5;
}

.alert-values {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-muted);
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    letter-spacing: 0.5px;
}

/* ═══════════════════════════════════════════════════════════════════════════
   NO TRADE CARD
   ═══════════════════════════════════════════════════════════════════════════ */
.no-trade-card {
    background: linear-gradient(135deg, var(--bear-soft) 0%, transparent 40%);
    border: 1px solid rgba(255, 82, 99, 0.3);
    border-radius: var(--radius-xl);
    padding: 48px;
    text-align: center;
    position: relative;
}

.no-trade-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: var(--gradient-bear);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
}

.no-trade-icon {
    font-size: var(--text-3xl);
    margin-bottom: 20px;
    opacity: 0.9;
}

.no-trade-title {
    font-family: var(--font-display);
    font-size: var(--text-xl);
    font-weight: 800;
    color: var(--bear);
    margin-bottom: 12px;
    letter-spacing: 1px;
}

.no-trade-reason {
    font-family: var(--font-body);
    font-size: var(--text-md);
    color: var(--text-secondary);
    max-width: 400px;
    margin: 0 auto;
    line-height: 1.6;
}

/* ═══════════════════════════════════════════════════════════════════════════
   LIVE INDICATOR
   ═══════════════════════════════════════════════════════════════════════════ */
.live-indicator {
    display: inline-flex;
    align-items: center;
    gap: 8px;
}

.live-dot {
    width: 8px;
    height: 8px;
    background: var(--bull);
    border-radius: 50%;
    animation: livePulse 2s ease-in-out infinite;
    box-shadow: 0 0 12px var(--bull-glow);
}

@keyframes livePulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(0.9); }
}

/* ═══════════════════════════════════════════════════════════════════════════
   STREAMLIT OVERRIDES
   ═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stMetricValue"] {
    font-family: 'Orbitron', sans-serif !important;
    font-weight: 800 !important;
}

[data-testid="stMetricLabel"] {
    font-family: 'Share Tech Mono', monospace !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--bg-panel) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

section[data-testid="stSidebar"] > div {
    background: var(--bg-panel) !important;
}

section[data-testid="stSidebar"] h3 {
    color: var(--text-bright) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
}

section[data-testid="stSidebar"] h4 {
    color: var(--accent-cyan) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
}

section[data-testid="stSidebar"] h5 {
    color: var(--text-secondary) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.85rem !important;
}

section[data-testid="stSidebar"] label {
    color: var(--text-secondary) !important;
    font-family: 'Rajdhani', sans-serif !important;
}

section[data-testid="stSidebar"] input {
    background: var(--bg-input) !important;
    color: var(--text-bright) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Share Tech Mono', monospace !important;
}

section[data-testid="stSidebar"] input:focus {
    border-color: var(--accent-cyan) !important;
    box-shadow: 0 0 0 2px var(--accent-cyan-soft) !important;
}

section[data-testid="stSidebar"] .stSelectbox > div > div {
    background: var(--bg-input) !important;
    color: var(--text-bright) !important;
    font-family: 'Share Tech Mono', monospace !important;
}

section[data-testid="stSidebar"] p {
    color: var(--text-muted) !important;
}

/* Buttons */
.stButton > button {
    font-family: 'Share Tech Mono', monospace !important;
    font-weight: 700 !important;
    border-radius: var(--radius-md) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: var(--shadow-md) !important;
}

/* Force Orbitron on all h2 section headers */
h2.section-title, .section-title {
    font-family: 'Orbitron', sans-serif !important;
}

/* Dividers */
hr {
    border: none !important;
    height: 1px !important;
    background: var(--border-subtle) !important;
    margin: 24px 0 !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   RESPONSIVE DESIGN
   ═══════════════════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
    .hero-banner {
        flex-direction: column;
        padding: 20px 16px;
        gap: 16px;
    }
    
    .hero-content { text-align: center; }
    .brand-name { font-size: var(--text-xl); letter-spacing: 2px; }
    
    .prior-levels-container { grid-template-columns: 1fr; }
    .prior-levels-grid { grid-template-columns: 1fr; }
    .trade-grid { grid-template-columns: 1fr; }
    .targets-grid { grid-template-columns: 1fr; }
    
    .metric-card { min-height: 90px; padding: 16px; }
    .metric-value { font-size: var(--text-xl); }
}
</style>
"""
# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
def sidebar():
    saved = load_inputs()
    
    with st.sidebar:
        st.markdown("### ⚙️ SPX Prophet Settings")
        
        # ─────────────────────────────────────────────────────────────────────
        # BASIC SETTINGS
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("#### 📅 Trading Session")
        # Use CT timezone for today's date to avoid timezone issues
        ct_now = datetime.now(CT)
        ct_today = ct_now.date()
        trading_date = st.date_input("Trading Date", value=ct_today)
        
        # Reference time with 30-minute granularity
        ref_time_options = []
        for h in range(8, 12):
            for m in [0, 30]:
                ref_time_options.append(f"{h}:{m:02d}")
        
        ref_time_str = st.selectbox("Reference Time (CT)", options=ref_time_options, index=ref_time_options.index("9:00") if "9:00" in ref_time_options else 2, help="Time to calculate levels for")
        ref_parts = ref_time_str.split(":")
        ref_hour = int(ref_parts[0])
        ref_min = int(ref_parts[1])
        
        st.divider()
        
        # ─────────────────────────────────────────────────────────────────────
        # ES/SPX OFFSET
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("#### 📊 ES → SPX Conversion")
        offset = st.number_input(
            "Offset (ES - SPX)", 
            value=float(saved.get("offset", 35.5)), 
            step=0.5,
            help="Difference between ES futures and SPX cash index"
        )
        
        st.divider()
        
        # ─────────────────────────────────────────────────────────────────────
        # VIX SETTINGS
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("#### 📉 VIX Configuration")
        
        use_manual_vix = st.checkbox("Manual VIX Override", value=False)
        if use_manual_vix:
            manual_vix = st.number_input("Current VIX", value=16.0, step=0.1, format="%.2f")
        else:
            manual_vix = None
        
        st.markdown("##### Overnight Zone (CT)")
        col1, col2 = st.columns(2)
        vix_zone_start = col1.time_input("Zone Start", value=time(2, 0))
        vix_zone_end = col2.time_input("Zone End", value=time(5, 30))
        
        use_manual_vix_range = st.checkbox("Manual VIX Range Override", value=False)
        if use_manual_vix_range:
            col1, col2 = st.columns(2)
            manual_vix_low = col1.number_input("VIX Low", value=15.0, step=0.1, format="%.2f")
            manual_vix_high = col2.number_input("VIX High", value=17.0, step=0.1, format="%.2f")
        else:
            manual_vix_low = None
            manual_vix_high = None
        
        st.divider()
        
        # ─────────────────────────────────────────────────────────────────────
        # PRIOR DAY RTH DATA
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("#### 📈 Prior Day RTH (ES)")
        use_manual_prior = st.checkbox("Manual Prior Day Override", value=False)
        if use_manual_prior:
            # Time inputs with 30-minute granularity (RTH: 8:30 AM - 3:00 PM CT)
            time_options = []
            for h in range(8, 16):
                for m in [0, 30]:
                    if h == 8 and m == 0:
                        continue  # RTH starts at 8:30
                    if h == 15 and m == 30:
                        continue  # RTH ends at 3:00
                    time_options.append(f"{h}:{m:02d}")
            
            st.markdown("##### Primary High Wick")
            col1, col2 = st.columns(2)
            prior_primary_hw = col1.number_input("Price (ES)", value=6100.0, step=0.5, key="p_hw", help="Highest high of any RTH candle")
            p_hw_time_str = col2.selectbox("Time", options=time_options, index=time_options.index("9:30") if "9:30" in time_options else 2, key="p_hw_t", help="Time when primary high wick occurred (CT)")
            
            st.markdown("##### Secondary High Wick")
            has_secondary_hw = st.checkbox("Has Secondary High Wick", value=False, key="has_s_hw")
            if has_secondary_hw:
                col1, col2 = st.columns(2)
                prior_secondary_hw = col1.number_input("Price (ES)", value=6090.0, step=0.5, key="s_hw", help="Lower high wick made after primary")
                s_hw_time_str = col2.selectbox("Time", options=time_options, index=time_options.index("14:30") if "14:30" in time_options else 10, key="s_hw_t", help="Time when secondary high wick occurred (CT)")
            else:
                prior_secondary_hw = None
                s_hw_time_str = "12:00"
            
            st.markdown("##### Primary Low Open")
            col1, col2 = st.columns(2)
            prior_primary_lo = col1.number_input("Price (ES)", value=6050.0, step=0.5, key="p_lo", help="Lowest open of any BULLISH RTH candle")
            p_lo_time_str = col2.selectbox("Time", options=time_options, index=time_options.index("12:00") if "12:00" in time_options else 7, key="p_lo_t", help="Time when primary low open occurred (CT)")
            
            st.markdown("##### Secondary Low Open")
            has_secondary_lo = st.checkbox("Has Secondary Low Open", value=False, key="has_s_lo")
            if has_secondary_lo:
                col1, col2 = st.columns(2)
                prior_secondary_lo = col1.number_input("Price (ES)", value=6060.0, step=0.5, key="s_lo", help="Higher low open made after primary (bullish candle)")
                s_lo_time_str = col2.selectbox("Time", options=time_options, index=time_options.index("14:30") if "14:30" in time_options else 10, key="s_lo_t", help="Time when secondary low open occurred (CT)")
            else:
                prior_secondary_lo = None
                s_lo_time_str = "12:00"
            
            st.markdown("##### RTH Close")
            prior_close = st.number_input("RTH Close (ES)", value=6075.0, step=0.5, help="Final RTH close")
            
            # Parse time strings
            def parse_time_str(t_str):
                parts = t_str.split(":")
                return int(parts[0]), int(parts[1])
            
            p_hw_hour, p_hw_min = parse_time_str(p_hw_time_str)
            s_hw_hour, s_hw_min = parse_time_str(s_hw_time_str)
            p_lo_hour, p_lo_min = parse_time_str(p_lo_time_str)
            s_lo_hour, s_lo_min = parse_time_str(s_lo_time_str)
        else:
            prior_primary_hw = None
            prior_secondary_hw = None
            prior_primary_lo = None
            prior_secondary_lo = None
            p_hw_hour, p_hw_min = 9, 30
            s_hw_hour, s_hw_min = 14, 30
            p_lo_hour, p_lo_min = 12, 0
            s_lo_hour, s_lo_min = 14, 30
            prior_close = None
            has_secondary_hw = False
            has_secondary_lo = False
        
        st.divider()
        
        # ─────────────────────────────────────────────────────────────────────
        # OVERNIGHT SESSION DATA
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("#### 🌙 Overnight Session (ES)")
        use_manual_overnight = st.checkbox("Manual ON Session Override", value=False)
        if use_manual_overnight:
            # Overnight time options (5:00 PM previous day to 8:30 AM trading day)
            on_time_options = []
            # Evening hours (17:00 - 23:30)
            for h in range(17, 24):
                for m in [0, 30]:
                    on_time_options.append(f"{h}:{m:02d}")
            # Morning hours (00:00 - 08:30)
            for h in range(0, 9):
                for m in [0, 30]:
                    if h == 8 and m == 30:
                        on_time_options.append(f"{h}:{m:02d}")
                        break
                    on_time_options.append(f"{h}:{m:02d}")
            
            col1, col2 = st.columns(2)
            on_high = col1.number_input("ON High (ES)", value=6090.0, step=0.5)
            on_low = col2.number_input("ON Low (ES)", value=6055.0, step=0.5)
            
            col3, col4 = st.columns(2)
            on_high_time_str = col3.selectbox("High Time (CT)", options=on_time_options, index=on_time_options.index("2:00") if "2:00" in on_time_options else 18, help="Time when overnight high occurred")
            on_low_time_str = col4.selectbox("Low Time (CT)", options=on_time_options, index=on_time_options.index("4:00") if "4:00" in on_time_options else 22, help="Time when overnight low occurred")
            
            # Parse times
            on_high_parts = on_high_time_str.split(":")
            on_high_hour = int(on_high_parts[0])
            on_high_min = int(on_high_parts[1])
            
            on_low_parts = on_low_time_str.split(":")
            on_low_hour = int(on_low_parts[0])
            on_low_min = int(on_low_parts[1])
        else:
            on_high = None
            on_low = None
            on_high_hour = 2
            on_high_min = 0
            on_low_hour = 4
            on_low_min = 0
        
        st.divider()
        
        # ─────────────────────────────────────────────────────────────────────
        # GLOBAL SESSION OVERRIDES
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("#### 🌏 Session Breakdown (ES)")
        use_manual_sessions = st.checkbox("Manual Session Override", value=False)
        
        if use_manual_sessions:
            # Time options for overnight sessions
            def get_session_time_options(start_hour, end_hour, crosses_midnight=False):
                options = []
                if crosses_midnight:
                    for h in range(start_hour, 24):
                        for m in [0, 30]:
                            options.append(f"{h}:{m:02d}")
                    for h in range(0, end_hour + 1):
                        for m in [0, 30]:
                            if h == end_hour and m == 30:
                                break
                            options.append(f"{h}:{m:02d}")
                else:
                    for h in range(start_hour, end_hour + 1):
                        for m in [0, 30]:
                            options.append(f"{h}:{m:02d}")
                return options
            
            sydney_times = get_session_time_options(17, 20)  # 5 PM - 8:30 PM
            tokyo_times = get_session_time_options(21, 1, crosses_midnight=True)  # 9 PM - 1:30 AM
            london_times = get_session_time_options(2, 5)  # 2 AM - 5 AM
            
            st.markdown("##### Sydney (5-8:30 PM CT)")
            col1, col2 = st.columns(2)
            sydney_high = col1.number_input("High", value=6075.0, step=0.5, key="syd_h")
            sydney_low = col2.number_input("Low", value=6060.0, step=0.5, key="syd_l")
            col3, col4 = st.columns(2)
            sydney_high_time = col3.selectbox("High Time", options=sydney_times, index=2, key="syd_ht", help="Time of session high")
            sydney_low_time = col4.selectbox("Low Time", options=sydney_times, index=4, key="syd_lt", help="Time of session low")
            
            st.markdown("##### Tokyo (9 PM - 1:30 AM CT)")
            col1, col2 = st.columns(2)
            tokyo_high = col1.number_input("High", value=6080.0, step=0.5, key="tok_h")
            tokyo_low = col2.number_input("Low", value=6055.0, step=0.5, key="tok_l")
            col3, col4 = st.columns(2)
            tokyo_high_time = col3.selectbox("High Time", options=tokyo_times, index=2, key="tok_ht", help="Time of session high")
            tokyo_low_time = col4.selectbox("Low Time", options=tokyo_times, index=6, key="tok_lt", help="Time of session low")
            
            st.markdown("##### London (2-5 AM CT)")
            col1, col2 = st.columns(2)
            london_high = col1.number_input("High", value=6085.0, step=0.5, key="lon_h")
            london_low = col2.number_input("Low", value=6050.0, step=0.5, key="lon_l")
            col3, col4 = st.columns(2)
            london_high_time = col3.selectbox("High Time", options=london_times, index=2, key="lon_ht", help="Time of session high")
            london_low_time = col4.selectbox("Low Time", options=london_times, index=4, key="lon_lt", help="Time of session low")
        else:
            sydney_high = sydney_low = tokyo_high = tokyo_low = london_high = london_low = None
            sydney_high_time = sydney_low_time = tokyo_high_time = tokyo_low_time = None
            london_high_time = london_low_time = None
        
        st.divider()
        
        # ─────────────────────────────────────────────────────────────────────
        # CURRENT PRICE OVERRIDE
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("#### 💹 Current Price")
        use_manual_price = st.checkbox("Manual ES Price Override", value=False)
        if use_manual_price:
            manual_es = st.number_input("Current ES", value=6070.0, step=0.5)
        else:
            manual_es = None
        
        st.divider()
        
        # ─────────────────────────────────────────────────────────────────────
        # SESSION TIMES (for extraction)
        # ─────────────────────────────────────────────────────────────────────
        with st.expander("⏰ Session Time Config", expanded=False):
            st.markdown("**Sydney Session (CT)**")
            col1, col2 = st.columns(2)
            sydney_start = col1.time_input("Start", value=time(17, 0), key="syd_start")
            sydney_end = col2.time_input("End", value=time(20, 30), key="syd_end")
            
            st.markdown("**Tokyo Session (CT)**")
            col1, col2 = st.columns(2)
            tokyo_start = col1.time_input("Start", value=time(21, 0), key="tok_start")
            tokyo_end = col2.time_input("End", value=time(1, 30), key="tok_end")
            
            st.markdown("**London Session (CT)**")
            col1, col2 = st.columns(2)
            london_start = col1.time_input("Start", value=time(2, 0), key="lon_start")
            london_end = col2.time_input("End", value=time(5, 0), key="lon_end")
        
        st.divider()
        
        # ─────────────────────────────────────────────────────────────────────
        # ACTION BUTTONS
        # ─────────────────────────────────────────────────────────────────────
        col1, col2 = st.columns(2)
        if col1.button("💾 Save", use_container_width=True):
            save_inputs({"offset": offset})
            st.success("✓ Saved!")
        if col2.button("🔄 Refresh", use_container_width=True):
            # Clear only market data caches
            fetch_es_current.clear()
            fetch_vix_polygon.clear()
            fetch_vix_yahoo.clear()
            fetch_es_with_ema.clear()
            fetch_retail_positioning.clear()
            fetch_prior_day_rth.clear()
            st.rerun()
    
    # Build return dict with all manual overrides
    return {
        "trading_date": trading_date,
        "offset": offset,
        "ref_time": (ref_hour, ref_min),
        "vix_zone_start": vix_zone_start,
        "vix_zone_end": vix_zone_end,
        # Manual overrides
        "manual_vix": manual_vix,
        "manual_vix_range": {"low": manual_vix_low, "high": manual_vix_high} if use_manual_vix_range else None,
        "manual_prior": {
            "primary_high_wick": prior_primary_hw, 
            "secondary_high_wick": prior_secondary_hw if has_secondary_hw else None,
            "primary_low_open": prior_primary_lo, 
            "secondary_low_open": prior_secondary_lo if has_secondary_lo else None,
            "close": prior_close, 
            "p_hw_hour": p_hw_hour, "p_hw_min": p_hw_min,
            "s_hw_hour": s_hw_hour, "s_hw_min": s_hw_min,
            "p_lo_hour": p_lo_hour, "p_lo_min": p_lo_min,
            "s_lo_hour": s_lo_hour, "s_lo_min": s_lo_min,
            # Legacy keys for backward compatibility
            "highest_wick": prior_primary_hw,
            "lowest_close": prior_primary_lo,
            "hw_hour": p_hw_hour, "hw_min": p_hw_min,
            "lc_hour": p_lo_hour, "lc_min": p_lo_min,
        } if use_manual_prior else None,
        "manual_overnight": {"high": on_high, "low": on_low, "high_hour": on_high_hour, "high_min": on_high_min, "low_hour": on_low_hour, "low_min": on_low_min} if use_manual_overnight else None,
        "manual_sessions": {
            "sydney": {"high": sydney_high, "low": sydney_low, "high_time": sydney_high_time, "low_time": sydney_low_time},
            "tokyo": {"high": tokyo_high, "low": tokyo_low, "high_time": tokyo_high_time, "low_time": tokyo_low_time},
            "london": {"high": london_high, "low": london_low, "high_time": london_high_time, "low_time": london_low_time}
        } if use_manual_sessions else None,
        "manual_es": manual_es,
    }
# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    st.markdown(CSS_STYLES, unsafe_allow_html=True)
    inputs = sidebar()
    now = now_ct()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LOAD DATA (with manual override support)
    # ═══════════════════════════════════════════════════════════════════════════
    with st.spinner("Loading market data..."):
        
        # --- Current ES Price ---
        if inputs["manual_es"] is not None:
            current_es = inputs["manual_es"]
        else:
            current_es = fetch_es_current() or 6050
        
        # --- IMPORTANT: Adjust trading date for weekends ---
        # If user selects Saturday/Sunday, use Monday as actual trading date
        actual_trading_date = get_actual_trading_day(inputs["trading_date"])
        
        # Helper to parse time string and create datetime
        def parse_session_time(time_str, base_date, overnight_day):
            """Parse time string like '18:00' and return proper datetime.
            Times >= 17:00 are on overnight_day, times < 17:00 are on base_date (trading day)."""
            if time_str is None:
                return None
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            # Evening times (5 PM onwards) are on the prior day
            if hour >= 17:
                return CT.localize(datetime.combine(overnight_day, time(hour, minute)))
            else:
                return CT.localize(datetime.combine(base_date, time(hour, minute)))
        
        # --- Session Data ---
        if inputs["manual_sessions"] is not None:
            m = inputs["manual_sessions"]
            overnight_day = get_prior_trading_day(actual_trading_date)
            
            sydney = {
                "high": m["sydney"]["high"], 
                "low": m["sydney"]["low"],
                "high_time": parse_session_time(m["sydney"].get("high_time"), actual_trading_date, overnight_day) or CT.localize(datetime.combine(overnight_day, time(18, 0))),
                "low_time": parse_session_time(m["sydney"].get("low_time"), actual_trading_date, overnight_day) or CT.localize(datetime.combine(overnight_day, time(19, 0)))
            }
            tokyo = {
                "high": m["tokyo"]["high"], 
                "low": m["tokyo"]["low"],
                "high_time": parse_session_time(m["tokyo"].get("high_time"), actual_trading_date, overnight_day) or CT.localize(datetime.combine(overnight_day, time(23, 0))),
                "low_time": parse_session_time(m["tokyo"].get("low_time"), actual_trading_date, overnight_day) or CT.localize(datetime.combine(actual_trading_date, time(0, 30)))
            }
            london = {
                "high": m["london"]["high"], 
                "low": m["london"]["low"],
                "high_time": parse_session_time(m["london"].get("high_time"), actual_trading_date, overnight_day) or CT.localize(datetime.combine(actual_trading_date, time(3, 0))),
                "low_time": parse_session_time(m["london"].get("low_time"), actual_trading_date, overnight_day) or CT.localize(datetime.combine(actual_trading_date, time(4, 0)))
            }
        else:
            es_candles = fetch_es_candles()
            sessions = extract_sessions(es_candles, actual_trading_date) or {}
            sydney = sessions.get("sydney")
            tokyo = sessions.get("tokyo")
            london = sessions.get("london")
        
        # --- Overnight High/Low ---
        if inputs["manual_overnight"] is not None:
            overnight = {
                "high": inputs["manual_overnight"]["high"],
                "low": inputs["manual_overnight"]["low"]
            }
        elif sydney and tokyo and london:
            overnight = {
                "high": max(sydney["high"], tokyo["high"], london["high"]),
                "low": min(sydney["low"], tokyo["low"], london["low"])
            }
        elif inputs["manual_sessions"] is not None:
            m = inputs["manual_sessions"]
            overnight = {
                "high": max(m["sydney"]["high"], m["tokyo"]["high"], m["london"]["high"]),
                "low": min(m["sydney"]["low"], m["tokyo"]["low"], m["london"]["low"])
            }
        else:
            es_candles = fetch_es_candles()
            sessions = extract_sessions(es_candles, actual_trading_date) or {}
            overnight = sessions.get("overnight")
        
        # --- VIX Current ---
        if inputs["manual_vix"] is not None:
            vix = inputs["manual_vix"]
        else:
            vix_polygon = fetch_vix_polygon()
            vix = vix_polygon if vix_polygon else fetch_vix_yahoo()
        
        # Safety fallback if VIX fetch failed
        if vix is None:
            vix = 16.0  # Default to neutral VIX
        
        # --- VIX Overnight Range ---
        if inputs["manual_vix_range"] is not None:
            vix_range = {
                "bottom": inputs["manual_vix_range"]["low"],
                "top": inputs["manual_vix_range"]["high"],
                "range_size": round(inputs["manual_vix_range"]["high"] - inputs["manual_vix_range"]["low"], 2),
                "available": True
            }
        else:
            vix_range = fetch_vix_overnight_range(
                actual_trading_date, 
                inputs["vix_zone_start"].hour, inputs["vix_zone_start"].minute, 
                inputs["vix_zone_end"].hour, inputs["vix_zone_end"].minute
            )
        
        vix_pos, vix_pos_desc = get_vix_position(vix, vix_range)
        retail_data = fetch_retail_positioning()
        ema_data = fetch_es_with_ema()
        
        # --- Prior Day RTH Data ---
        # actual_trading_date was already set at the beginning (adjusts weekends to Monday)
        
        if inputs["manual_prior"] is not None:
            prior_day = get_prior_trading_day(actual_trading_date)
            m = inputs["manual_prior"]
            
            # Parse all pivot times
            p_hw_hour = m.get("p_hw_hour", m.get("hw_hour", 9))
            p_hw_min = m.get("p_hw_min", m.get("hw_min", 30))
            s_hw_hour = m.get("s_hw_hour", 14)
            s_hw_min = m.get("s_hw_min", 30)
            p_lo_hour = m.get("p_lo_hour", m.get("lc_hour", 12))
            p_lo_min = m.get("p_lo_min", m.get("lc_min", 0))
            s_lo_hour = m.get("s_lo_hour", 14)
            s_lo_min = m.get("s_lo_min", 30)
            
            prior_rth = {
                # Primary High Wick
                "primary_high_wick": m.get("primary_high_wick", m.get("highest_wick")),
                "primary_high_wick_time": CT.localize(datetime.combine(prior_day, time(p_hw_hour, p_hw_min))),
                # Secondary High Wick
                "secondary_high_wick": m.get("secondary_high_wick"),
                "secondary_high_wick_time": CT.localize(datetime.combine(prior_day, time(s_hw_hour, s_hw_min))) if m.get("secondary_high_wick") else None,
                # Primary Low Open
                "primary_low_open": m.get("primary_low_open", m.get("lowest_close")),
                "primary_low_open_time": CT.localize(datetime.combine(prior_day, time(p_lo_hour, p_lo_min))),
                # Secondary Low Open
                "secondary_low_open": m.get("secondary_low_open"),
                "secondary_low_open_time": CT.localize(datetime.combine(prior_day, time(s_lo_hour, s_lo_min))) if m.get("secondary_low_open") else None,
                # Overall stats
                "high": m.get("primary_high_wick", m.get("highest_wick")),
                "low": m.get("primary_low_open", m.get("lowest_close")),
                "close": m.get("close"),
                "available": True,
                # Legacy keys for backward compatibility
                "highest_wick": m.get("primary_high_wick", m.get("highest_wick")),
                "highest_wick_time": CT.localize(datetime.combine(prior_day, time(p_hw_hour, p_hw_min))),
                "lowest_close": m.get("primary_low_open", m.get("lowest_close")),
                "lowest_close_time": CT.localize(datetime.combine(prior_day, time(p_lo_hour, p_lo_min))),
            }
        else:
            prior_rth = fetch_prior_day_rth(actual_trading_date)
    
    offset = inputs["offset"]
    current_spx = round(current_es - offset, 2)
    channel_type, channel_reason, upper_pivot, lower_pivot, upper_time, lower_time = determine_channel(sydney, tokyo, london)
    
    # Validate and adjust pivots - ensure no price broke through projected lines during building
    # This also tracks ORIGINAL pivots for cases like today where market respects original level
    sessions_data = {"sydney": sydney, "tokyo": tokyo, "london": london}
    ref_time_dt = CT.localize(datetime.combine(actual_trading_date, time(*inputs["ref_time"])))
    pivot_validation = validate_and_adjust_pivots(
        channel_type, upper_pivot, lower_pivot, upper_time, lower_time, 
        sessions_data, ref_time_dt
    )
    
    # Extract adjusted pivots (these are used for channel calculation)
    upper_pivot = pivot_validation["upper_pivot"]
    lower_pivot = pivot_validation["lower_pivot"]
    upper_time = pivot_validation["upper_time"]
    lower_time = pivot_validation["lower_time"]
    
    # Also store original pivots for display
    original_upper_pivot = pivot_validation["original_upper_pivot"]
    original_lower_pivot = pivot_validation["original_lower_pivot"]
    original_upper_time = pivot_validation["original_upper_time"]
    original_lower_time = pivot_validation["original_lower_time"]
    floor_was_adjusted = pivot_validation["floor_was_adjusted"]
    ceiling_was_adjusted = pivot_validation["ceiling_was_adjusted"]
    floor_adjustment_session = pivot_validation["floor_adjustment_session"]
    ceiling_adjustment_session = pivot_validation["ceiling_adjustment_session"]
    
    # Calculate channel levels with validated (adjusted) pivots
    ceiling_es, floor_es = calc_channel_levels(upper_pivot, lower_pivot, upper_time, lower_time, ref_time_dt, channel_type)
    
    # Also calculate ORIGINAL channel levels (before adjustment)
    original_ceiling_es, original_floor_es = calc_channel_levels(
        original_upper_pivot, original_lower_pivot, original_upper_time, original_lower_time, ref_time_dt, channel_type
    )
    
    if ceiling_es is None:
        ceiling_es, floor_es = 6080, 6040
    
    ceiling_spx = round(ceiling_es - offset, 2)
    floor_spx = round(floor_es - offset, 2)
    position = get_position(current_es, ceiling_es, floor_es)
    
    # Original levels in SPX (for display when adjusted)
    original_ceiling_spx = round(original_ceiling_es - offset, 2) if original_ceiling_es else ceiling_spx
    original_floor_spx = round(original_floor_es - offset, 2) if original_floor_es else floor_spx
    
    # ─────────────────────────────────────────────────────────────────────────
    # DUAL CHANNEL LEVELS (Option C - Always show BOTH ascending and descending)
    # ─────────────────────────────────────────────────────────────────────────
    dual_levels_es = calc_dual_channel_levels(upper_pivot, lower_pivot, upper_time, lower_time, ref_time_dt)
    
    # Also calculate ORIGINAL dual levels
    original_dual_levels_es = calc_dual_channel_levels(
        original_upper_pivot, original_lower_pivot, original_upper_time, original_lower_time, ref_time_dt
    )
    
    # Convert to SPX
    dual_levels_spx = None
    if dual_levels_es:
        dual_levels_spx = {
            "asc_floor": round(dual_levels_es["asc_floor"] - offset, 2),
            "asc_ceiling": round(dual_levels_es["asc_ceiling"] - offset, 2),
            "desc_ceiling": round(dual_levels_es["desc_ceiling"] - offset, 2),
            "desc_floor": round(dual_levels_es["desc_floor"] - offset, 2),
            "overnight_high": dual_levels_es["overnight_high"],
            "overnight_low": dual_levels_es["overnight_low"],
            "blocks_high": dual_levels_es["blocks_high"],
            "blocks_low": dual_levels_es["blocks_low"],
            # Add original levels if adjusted
            "floor_was_adjusted": floor_was_adjusted,
            "ceiling_was_adjusted": ceiling_was_adjusted,
            "floor_adjustment_session": floor_adjustment_session,
            "ceiling_adjustment_session": ceiling_adjustment_session,
        }
        
        # Add original levels if they were adjusted
        if floor_was_adjusted and original_dual_levels_es:
            dual_levels_spx["original_asc_floor"] = round(original_dual_levels_es["asc_floor"] - offset, 2)
        if ceiling_was_adjusted and original_dual_levels_es:
            dual_levels_spx["original_desc_ceiling"] = round(original_dual_levels_es["desc_ceiling"] - offset, 2)
    
    # Calculate prior day targets (both ascending and descending from each anchor)
    prior_targets = calc_prior_day_targets(prior_rth, ref_time_dt)
    
    # ─────────────────────────────────────────────────────────────────────────
    # CONVERGENCE ZONE CALCULATION
    # ─────────────────────────────────────────────────────────────────────────
    # Calculate zone at 9:00 AM CT - this gives you 30 minutes after RTH open
    # to see where price settles relative to the zone for your trading plan
    #
    # ZONE LOCK LOGIC:
    # ─────────────────────────────────────────────────────────────────────────
    # CONFLUENCE DATA GATHERING
    # ─────────────────────────────────────────────────────────────────────────
    # Session tests - how many sessions tested each level
    session_tests = analyze_session_tests(sydney, tokyo, london, channel_type)
    
    # Gap analysis - where did we gap relative to channel
    prior_close_es = prior_rth.get("close") if prior_rth and prior_rth.get("available") else None
    prior_close_spx = round(prior_close_es - offset, 2) if prior_close_es else None
    gap_analysis = analyze_gap(current_spx, prior_close_spx, ceiling_spx, floor_spx)
    
    # Prior close analysis - does prior close validate a level
    prior_close_validation = analyze_prior_close(prior_close_spx, ceiling_spx, floor_spx)
    
    # VIX term structure
    vix_term = fetch_vix_term_structure()
    
    # Get current CT time for channel lock determination
    ct_now = datetime.now(CT)
    
    # OPTION C: Use the new dual-channel decision engine
    decision = analyze_market_state_v2(
        current_spx, dual_levels_spx, channel_type, channel_reason,
        retail_data["bias"], ema_data["ema_bias"], vix_pos, vix,
        session_tests, gap_analysis, prior_close_validation, vix_term,
        prior_targets, ct_now
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EXPLOSIVE MOVE DETECTOR
    # ═══════════════════════════════════════════════════════════════════════════
    overnight_range = None
    if overnight:
        overnight_range = overnight.get("high", 0) - overnight.get("low", 0)
    
    prior_day_range = None
    if prior_rth and prior_rth.get("available"):
        p_high = prior_rth.get("primary_high_wick")
        p_low = prior_rth.get("primary_low_open")
        if p_high and p_low:
            prior_day_range = p_high - p_low
    
    explosive = detect_explosive_potential(
        current_spx, dual_levels_spx, prior_targets, channel_type,
        retail_data.get("spread"), ema_data, overnight_range, prior_day_range,
        gap_analysis
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HERO BANNER
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="hero-banner">
        <div class="prophet-logo">
            <div class="particle-field"></div>
            <div class="particle-field-inner"></div>
            <div class="orbital-ring-1"></div>
            <div class="orbital-ring-2"></div>
            <div class="orbital-ring-3"></div>
            <div class="ambient-glow"></div>
            <div class="pyramid-container">
                <div class="pyramid-base"></div>
                <div class="pyramid-main"></div>
                <div class="pyramid-layer-2"></div>
                <div class="pyramid-layer-3"></div>
                <div class="vertex-top"></div>
                <div class="vertex-left"></div>
                <div class="vertex-right"></div>
                <div class="vertex-center"></div>
                <div class="energy-beam-left"></div>
                <div class="energy-beam-right"></div>
                <div class="energy-beam-base"></div>
                <div class="scan-line"></div>
                <div class="scan-line-2"></div>
                <div class="data-stream-left"></div>
                <div class="data-stream-right"></div>
                <div class="pillar-label-left">RTH</div>
                <div class="pillar-label-right">O/N</div>
                <div class="pillar-label-center">VIX</div>
            </div>
        </div>
        <div class="hero-content">
            <h1 class="brand-name">SPX PROPHET</h1>
            <p class="brand-tagline">Where Structure Becomes Foresight</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUICK ACTION BAR
    # ═══════════════════════════════════════════════════════════════════════════
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        # Show actual trading date (with note if user selected weekend)
        date_display = actual_trading_date.strftime("%A, %B %d, %Y")
        weekend_note = ""
        if inputs["trading_date"] != actual_trading_date:
            weekend_note = f" (adjusted from {inputs['trading_date'].strftime('%A')})"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;padding:10px 0;">
            <span style="font-family:'Share Tech Mono',monospace;font-size:0.8rem;color:rgba(255,255,255,0.5);">
                📅 {date_display}{weekend_note}
            </span>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        if st.button("🔄 Refresh", use_container_width=True, help="Refresh all market data"):
            fetch_es_current.clear()
            fetch_vix_polygon.clear()
            fetch_vix_yahoo.clear()
            fetch_es_with_ema.clear()
            fetch_retail_positioning.clear()
            fetch_prior_day_rth.clear()
            st.rerun()
    with col3:
        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:10px 0;">
            <span style="font-family:'Share Tech Mono',monospace;font-size:0.8rem;color:rgba(255,255,255,0.5);">
                ⏰ {now.strftime("%I:%M %p CT")}
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MARKET SNAPSHOT
    # ═══════════════════════════════════════════════════════════════════════════
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-icon">📈</div><div class="metric-label">SPX Index</div><div class="metric-value accent">{current_spx:,.2f}</div><div class="metric-delta">ES {current_es:,.2f}</div></div>', unsafe_allow_html=True)
    with col2:
        vix_color = "puts" if vix > 20 else "calls" if vix < 15 else ""
        vix_icon = "🌋" if vix > 20 else "🧊" if vix < 15 else "🌊"
        vix_glow = "icon-glow-orange" if vix > 20 else "icon-glow-blue" if vix < 15 else ""
        st.markdown(f'<div class="metric-card"><div class="metric-icon {vix_glow}">{vix_icon}</div><div class="metric-label">VIX Index</div><div class="metric-value {vix_color}">{vix:.2f}</div><div class="metric-delta">Volatility</div></div>', unsafe_allow_html=True)
    with col3:
        pos_icon = "🔼" if position.value == "ABOVE" else "🔽" if position.value == "BELOW" else "⚖️"
        pos_glow = "icon-glow-green" if position.value == "ABOVE" else "icon-glow-red" if position.value == "BELOW" else "icon-glow-gold"
        st.markdown(f'<div class="metric-card"><div class="metric-icon {pos_glow}">{pos_icon}</div><div class="metric-label">Position</div><div class="metric-value">{position.value}</div><div class="metric-delta">In Channel</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-icon icon-clock">🕐</div><div class="metric-label">Time</div><div class="metric-value">{now.strftime("%I:%M")}</div><div class="metric-delta live-indicator"><span class="live-dot"></span> {now.strftime("%p CT")}</div></div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TODAY'S BIAS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header"><div class="section-icon">🎯</div><h2 class="section-title">Today\'s Bias</h2></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        chan_class = channel_type.value.lower()
        chan_icon = {"ASCENDING": "↗", "DESCENDING": "↘", "MIXED": "⟷", "CONTRACTING": "⟶"}.get(channel_type.value, "○")
        st.markdown(f'<div class="glass-card"><div class="channel-badge channel-badge-{chan_class}"><span style="font-size:1.2rem;">{chan_icon}</span><span>{channel_type.value}</span></div><p style="margin-top:10px;color:var(--text-secondary);font-size:0.875rem;">{channel_reason}</p></div>', unsafe_allow_html=True)
    with col2:
        ema_class = "calls" if ema_data["above_200"] else "puts"
        ema_icon = "↑" if ema_data["above_200"] else "↓"
        ema_text = "Above 200 EMA" if ema_data["above_200"] else "Below 200 EMA"
        st.markdown(f'<div class="glass-card"><div class="bias-pill bias-pill-{ema_class}"><span>{ema_icon}</span><span>{ema_text}</span></div><p style="margin-top:10px;color:var(--text-secondary);font-size:0.875rem;">{"Supports CALLS" if ema_data["above_200"] else "Supports PUTS"}</p></div>', unsafe_allow_html=True)
    with col3:
        cross_class = "calls" if ema_data["ema_cross"] == "BULLISH" else "puts"
        cross_icon = "✓" if ema_data["ema_cross"] == "BULLISH" else "✗"
        st.markdown(f'<div class="glass-card"><div class="bias-pill bias-pill-{cross_class}"><span>{cross_icon}</span><span>8/21 {ema_data["ema_cross"]}</span></div><p style="margin-top:10px;color:var(--text-secondary);font-size:0.875rem;">{"8 EMA > 21 EMA" if ema_data["ema_cross"] == "BULLISH" else "8 EMA < 21 EMA"}</p></div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EXPLOSIVE MOVE ALERT (Based on Target Distance ONLY)
    # ═══════════════════════════════════════════════════════════════════════════
    if explosive["explosive_score"] >= 30:
        score = explosive["explosive_score"]
        direction = explosive.get("direction_bias", "")
        target_dist = explosive.get("target_distance", 0)
        conviction = explosive.get("conviction", "LOW")
        
        # Determine styling based on conviction
        if conviction == "EXTREME":
            alert_class = "danger"
            score_icon = "🔥"
        elif conviction == "HIGH":
            alert_class = "warning" 
            score_icon = "⚡"
        else:
            alert_class = "info"
            score_icon = "📊"
        
        direction_icon = "🐻" if direction == "PUTS" else "🐂" if direction == "CALLS" else "⚖️"
        
        st.markdown(f'''
        <div class="alert-box alert-box-{alert_class}" style="border-width:2px;">
            <div class="alert-icon-large" style="font-size:4rem;">{direction_icon}</div>
            <div class="alert-content">
                <div class="alert-title" style="font-size:1.3rem;">{score_icon} EXPLOSIVE POTENTIAL: {conviction}</div>
                <div class="alert-values" style="font-size:1.1rem;margin-top:8px;border:none;padding:0;">
                    Target Runway: <strong>{target_dist:.0f} pts</strong> &nbsp;|&nbsp; If structure breaks: <strong>{direction}</strong>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
    
    # Retail positioning alert
    if retail_data["positioning"] != "BALANCED":
        alert_class = "warning" if "HEAVY" in retail_data["positioning"] else "danger"
        # Bull icon for CALL buying (fade to puts), Bear icon for PUT buying (fade to calls)
        alert_icon = "🐂" if "CALL" in retail_data["positioning"] else "🐻"
        # Show the actual VIX values so user can verify data is real
        vix_vals = f"VIX: {retail_data['vix']} | VIX3M: {retail_data['vix3m']} | Spread: {retail_data['spread']}" if retail_data['vix'] else "Data unavailable"
        st.markdown(f'<div class="alert-box alert-box-{alert_class}"><div class="alert-icon-large">{alert_icon}</div><div class="alert-content"><div class="alert-title">{retail_data["positioning"]}</div><div class="alert-text">{retail_data["warning"]}</div><div class="alert-values">{vix_vals}</div></div></div>', unsafe_allow_html=True)
    else:
        # Check if we actually have data or if it failed silently
        if retail_data['vix'] is not None:
            vix_vals = f"VIX: {retail_data['vix']} | VIX3M: {retail_data['vix3m']} | Spread: {retail_data['spread']}"
            st.markdown(f'<div class="alert-box alert-box-success"><div class="alert-icon-large">⚖️</div><div class="alert-content"><div class="alert-title">BALANCED POSITIONING</div><div class="alert-text">No crowd pressure detected - trade freely with structure</div><div class="alert-values">{vix_vals}</div></div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-box alert-box-info"><div class="alert-icon-large">❓</div><div class="alert-content"><div class="alert-title">POSITIONING UNKNOWN</div><div class="alert-text">Could not fetch VIX term structure data</div></div></div>', unsafe_allow_html=True)
    
    # VIX Position
    if vix_range["available"]:
        vix_icon = {"ABOVE": "▲", "IN RANGE": "◆", "BELOW": "▼"}.get(vix_pos.value, "○")
        st.markdown(f'<div class="alert-box alert-box-info"><span class="alert-icon">{vix_icon}</span><div class="alert-content"><div class="alert-title">VIX {vix_pos.value}</div><div class="alert-text">Overnight range: {vix_range["bottom"]} - {vix_range["top"]} | Current: {vix}</div></div></div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONFLUENCE
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header"><div class="section-icon">⚖️</div><h2 class="section-title">Confluence Analysis</h2></div>', unsafe_allow_html=True)
    
    calls_score, puts_score = len(decision["calls_factors"]), len(decision["puts_factors"])
    calls_class = "high" if calls_score >= 3 else "medium" if calls_score >= 2 else "low"
    puts_class = "high" if puts_score >= 3 else "medium" if puts_score >= 2 else "low"
    
    col1, col2 = st.columns(2)
    with col1:
        factors_html = "".join([f'<div class="confluence-factor"><span class="factor-check active">✓</span>{f}</div>' for f in decision["calls_factors"]]) or '<div class="confluence-factor"><span class="factor-check inactive">—</span>No supporting factors</div>'
        st.markdown(f'<div class="confluence-card confluence-card-calls"><div class="confluence-header"><span class="confluence-title">🟢 CALLS</span><span class="confluence-score {calls_class}">{calls_score}</span></div>{factors_html}</div>', unsafe_allow_html=True)
    with col2:
        factors_html = "".join([f'<div class="confluence-factor"><span class="factor-check active">✓</span>{f}</div>' for f in decision["puts_factors"]]) or '<div class="confluence-factor"><span class="factor-check inactive">—</span>No supporting factors</div>'
        st.markdown(f'<div class="confluence-card confluence-card-puts"><div class="confluence-header"><span class="confluence-title">🔴 PUTS</span><span class="confluence-score {puts_class}">{puts_score}</span></div>{factors_html}</div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DUAL CHANNEL LEVELS (Option C - All 4 Levels)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(f'<div class="section-header"><div class="section-icon">📊</div><h2 class="section-title">Dual Channel Levels @ {inputs["ref_time"][0]}:{inputs["ref_time"][1]:02d} AM</h2></div>', unsafe_allow_html=True)
    
    if dual_levels_spx:
        asc_floor = dual_levels_spx["asc_floor"]
        asc_ceiling = dual_levels_spx["asc_ceiling"]
        desc_ceiling = dual_levels_spx["desc_ceiling"]
        desc_floor = dual_levels_spx["desc_floor"]
        
        dist_asc_floor = round(current_spx - asc_floor, 1)
        dist_asc_ceiling = round(asc_ceiling - current_spx, 1)
        dist_desc_ceiling = round(desc_ceiling - current_spx, 1)
        dist_desc_floor = round(current_spx - desc_floor, 1)
        
        # Determine which level is KEY based on channel type
        is_ascending = channel_type == ChannelType.ASCENDING
        is_descending = channel_type == ChannelType.DESCENDING
        
        # Position summary from decision
        pos_summary = decision.get("position_summary", f"Position: {position.value}")
        
        # Position summary
        st.markdown(f'<div class="levels-container"><div style="padding:14px 16px;background:linear-gradient(90deg,var(--bg-elevated) 0%,transparent 100%);border-radius:10px;margin-bottom:16px;border-left:4px solid var(--accent-cyan);"><span style="font-family:Share Tech Mono,monospace;font-size:0.9rem;color:var(--text-primary);">{pos_summary}</span></div></div>', unsafe_allow_html=True)
        
        # Check if floor or ceiling was adjusted
        floor_adjusted = dual_levels_spx.get("floor_was_adjusted", False)
        ceiling_adjusted = dual_levels_spx.get("ceiling_was_adjusted", False)
        original_asc_floor = dual_levels_spx.get("original_asc_floor")
        original_desc_ceiling = dual_levels_spx.get("original_desc_ceiling")
        floor_adj_session = (dual_levels_spx.get("floor_adjustment_session") or "").upper()
        ceiling_adj_session = (dual_levels_spx.get("ceiling_adjustment_session") or "").upper()
        
        # Show adjustment alert if floor was adjusted
        if floor_adjusted and original_asc_floor:
            st.markdown(f'''
            <div class="alert-box alert-box-info" style="margin-bottom:16px;">
                <span class="alert-icon">🔄</span>
                <div class="alert-content">
                    <div class="alert-title">Floor Adjusted by {floor_adj_session}</div>
                    <div class="alert-text">Original floor: {original_asc_floor:,.2f} → Adjusted floor: {asc_floor:,.2f}<br>
                    <strong>Note:</strong> Market may still respect original level (like today!)</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
        
        if ceiling_adjusted and original_desc_ceiling:
            st.markdown(f'''
            <div class="alert-box alert-box-info" style="margin-bottom:16px;">
                <span class="alert-icon">🔄</span>
                <div class="alert-content">
                    <div class="alert-title">Ceiling Adjusted by {ceiling_adj_session}</div>
                    <div class="alert-text">Original ceiling: {original_desc_ceiling:,.2f} → Adjusted ceiling: {desc_ceiling:,.2f}<br>
                    <strong>Note:</strong> Market may still respect original level!</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
        
        # Ascending Channel Header
        asc_label = "↗ ASCENDING CHANNEL (DOMINANT)" if is_ascending else "↗ ASCENDING CHANNEL"
        st.markdown(f'<div style="font-size:0.8rem;color:var(--bull);text-transform:uppercase;letter-spacing:1px;margin:16px 0 8px 0;font-weight:600;">{asc_label}</div>', unsafe_allow_html=True)
        
        # Ascending Floor Row - show BOTH if adjusted
        if is_ascending:
            if floor_adjusted and original_asc_floor:
                # Show both original and adjusted
                dist_original = current_spx - original_asc_floor
                st.markdown(f'''
                <div class="levels-container" style="border-left:3px solid var(--bull);">
                    <div class="level-row">
                        <div class="level-label floor"><span>▼</span><span>ASC FLOOR (ADJ)</span></div>
                        <div class="level-value floor">{asc_floor:,.2f}</div>
                        <div class="level-note">CALLS entry • {dist_asc_floor:+.1f} pts</div>
                    </div>
                </div>
                <div class="levels-container" style="border-left:3px dashed var(--accent-gold);margin-top:-8px;opacity:0.85;">
                    <div class="level-row">
                        <div class="level-label" style="color:var(--accent-gold);"><span>▼</span><span>ORIGINAL FLOOR</span></div>
                        <div class="level-value" style="color:var(--accent-gold);">{original_asc_floor:,.2f}</div>
                        <div class="level-note" style="color:var(--accent-gold);">May still act as support • {dist_original:+.1f} pts</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="levels-container" style="border-left:3px solid var(--bull);"><div class="level-row"><div class="level-label floor"><span>▼</span><span>ASC FLOOR</span></div><div class="level-value floor">{asc_floor:,.2f}</div><div class="level-note">CALLS entry • {dist_asc_floor:+.1f} pts</div></div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="levels-container" style="opacity:0.7;"><div class="level-row"><div class="level-label floor"><span>▼</span><span>ASC FLOOR</span></div><div class="level-value floor">{asc_floor:,.2f}</div><div class="level-note">CALLS entry • {dist_asc_floor:+.1f} pts</div></div></div>', unsafe_allow_html=True)
        
        # Ascending Ceiling Row
        st.markdown(f'<div class="levels-container" style="opacity:0.5;margin-top:-8px;"><div class="level-row"><div class="level-label" style="color:var(--bull);"><span>▲</span><span>ASC CEIL</span></div><div class="level-value" style="color:var(--bull);">{asc_ceiling:,.2f}</div><div class="level-note">CALLS target • {dist_asc_ceiling:+.1f} pts</div></div></div>', unsafe_allow_html=True)
        
        # Current Price
        st.markdown(f'<div class="levels-container" style="background:linear-gradient(90deg,rgba(245,184,0,0.15) 0%,transparent 100%);margin:12px 0;"><div class="level-row"><div class="level-label current"><span>●</span><span>CURRENT</span></div><div class="level-value current">{current_spx:,.2f}</div><div class="level-note">ES: {current_es:,.2f}</div></div></div>', unsafe_allow_html=True)
        
        # Descending Channel Header
        desc_label = "↘ DESCENDING CHANNEL (DOMINANT)" if is_descending else "↘ DESCENDING CHANNEL"
        st.markdown(f'<div style="font-size:0.8rem;color:var(--bear);text-transform:uppercase;letter-spacing:1px;margin:16px 0 8px 0;font-weight:600;">{desc_label}</div>', unsafe_allow_html=True)
        
        # Descending Ceiling Row - show BOTH if adjusted
        if is_descending:
            if ceiling_adjusted and original_desc_ceiling:
                # Show both original and adjusted
                dist_original = current_spx - original_desc_ceiling
                st.markdown(f'''
                <div class="levels-container" style="border-left:3px solid var(--bear);">
                    <div class="level-row">
                        <div class="level-label ceiling"><span>▲</span><span>DESC CEIL (ADJ)</span></div>
                        <div class="level-value ceiling">{desc_ceiling:,.2f}</div>
                        <div class="level-note">PUTS entry • {dist_desc_ceiling:+.1f} pts</div>
                    </div>
                </div>
                <div class="levels-container" style="border-left:3px dashed var(--accent-gold);margin-top:-8px;opacity:0.85;">
                    <div class="level-row">
                        <div class="level-label" style="color:var(--accent-gold);"><span>▲</span><span>ORIGINAL CEIL</span></div>
                        <div class="level-value" style="color:var(--accent-gold);">{original_desc_ceiling:,.2f}</div>
                        <div class="level-note" style="color:var(--accent-gold);">May still act as resistance • {dist_original:+.1f} pts</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="levels-container" style="border-left:3px solid var(--bear);"><div class="level-row"><div class="level-label ceiling"><span>▲</span><span>DESC CEIL</span></div><div class="level-value ceiling">{desc_ceiling:,.2f}</div><div class="level-note">PUTS entry • {dist_desc_ceiling:+.1f} pts</div></div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="levels-container" style="opacity:0.7;"><div class="level-row"><div class="level-label ceiling"><span>▲</span><span>DESC CEIL</span></div><div class="level-value ceiling">{desc_ceiling:,.2f}</div><div class="level-note">PUTS entry • {dist_desc_ceiling:+.1f} pts</div></div></div>', unsafe_allow_html=True)
        
        # Descending Floor Row
        st.markdown(f'<div class="levels-container" style="opacity:0.5;margin-top:-8px;"><div class="level-row"><div class="level-label" style="color:var(--bear);"><span>▼</span><span>DESC FLOOR</span></div><div class="level-value" style="color:var(--bear);">{desc_floor:,.2f}</div><div class="level-note">PUTS target • {dist_desc_floor:+.1f} pts</div></div></div>', unsafe_allow_html=True)
        
        # Structure Alerts
        if decision.get("structure_alerts"):
            for alert in decision["structure_alerts"]:
                st.markdown(f'<div class="alert-box alert-box-warning"><span class="alert-icon">⚠️</span><div class="alert-content"><div class="alert-title">Structure Break Alert</div><div class="alert-text">{alert}</div></div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-box alert-box-danger"><span class="alert-icon">❌</span><div class="alert-content"><div class="alert-title">Dual Levels Unavailable</div><div class="alert-text">Missing overnight session data</div></div></div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRIOR DAY INTERMEDIATE LEVELS (4 Pivots x 2 Directions = 8 Levels)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header"><div class="section-icon">📍</div><h2 class="section-title">Prior Day Intermediate Levels</h2></div>', unsafe_allow_html=True)
    
    if prior_targets["available"]:
        # Convert all ES targets to SPX
        def to_spx(val):
            return round(val - offset, 2) if val is not None else None
        
        # Primary High Wick
        p_hw = to_spx(prior_targets.get("primary_high_wick"))
        p_hw_asc = to_spx(prior_targets.get("primary_high_wick_ascending"))
        p_hw_desc = to_spx(prior_targets.get("primary_high_wick_descending"))
        
        # Secondary High Wick
        s_hw = to_spx(prior_targets.get("secondary_high_wick"))
        s_hw_asc = to_spx(prior_targets.get("secondary_high_wick_ascending"))
        s_hw_desc = to_spx(prior_targets.get("secondary_high_wick_descending"))
        
        # Primary Low Open
        p_lo = to_spx(prior_targets.get("primary_low_open"))
        p_lo_asc = to_spx(prior_targets.get("primary_low_open_ascending"))
        p_lo_desc = to_spx(prior_targets.get("primary_low_open_descending"))
        
        # Secondary Low Open
        s_lo = to_spx(prior_targets.get("secondary_low_open"))
        s_lo_asc = to_spx(prior_targets.get("secondary_low_open_ascending"))
        s_lo_desc = to_spx(prior_targets.get("secondary_low_open_descending"))
        
        # ─────────────────────────────────────────────────────────────────────
        # PRIMARY PIVOTS (Expandable)
        # ─────────────────────────────────────────────────────────────────────
        with st.expander("📍 **PRIMARY PIVOTS** (High Wick & Low Open)", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                if p_hw is not None and p_hw_asc is not None and p_hw_desc is not None:
                    st.markdown(f'''
                    <div class="prior-levels-section" style="margin-bottom:0;">
                        <div class="prior-levels-header">
                            <span class="prior-levels-icon">🔺</span>
                            <span class="prior-levels-title">Primary High Wick</span>
                            <span class="prior-levels-anchor">{p_hw:,.2f}</span>
                        </div>
                        <div class="prior-levels-grid">
                            <div class="prior-level-item prior-level-sell">
                                <div class="prior-level-direction">↗ Ascending</div>
                                <div class="prior-level-value">{p_hw_asc:,.2f}</div>
                                <div class="prior-level-action">SELL (Resistance)</div>
                            </div>
                            <div class="prior-level-item prior-level-buy">
                                <div class="prior-level-direction">↘ Descending</div>
                                <div class="prior-level-value">{p_hw_desc:,.2f}</div>
                                <div class="prior-level-action">BUY (Support)</div>
                            </div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="padding:20px;text-align:center;color:var(--text-muted);">Primary High Wick: N/A</div>', unsafe_allow_html=True)
            
            with col2:
                if p_lo is not None and p_lo_asc is not None and p_lo_desc is not None:
                    st.markdown(f'''
                    <div class="prior-levels-section" style="margin-bottom:0;">
                        <div class="prior-levels-header">
                            <span class="prior-levels-icon">🔻</span>
                            <span class="prior-levels-title">Primary Low Open</span>
                            <span class="prior-levels-anchor">{p_lo:,.2f}</span>
                        </div>
                        <div class="prior-levels-grid">
                            <div class="prior-level-item prior-level-buy">
                                <div class="prior-level-direction">↗ Ascending</div>
                                <div class="prior-level-value">{p_lo_asc:,.2f}</div>
                                <div class="prior-level-action">BUY (Support)</div>
                            </div>
                            <div class="prior-level-item prior-level-sell">
                                <div class="prior-level-direction">↘ Descending</div>
                                <div class="prior-level-value">{p_lo_desc:,.2f}</div>
                                <div class="prior-level-action">SELL (Resistance)</div>
                            </div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="padding:20px;text-align:center;color:var(--text-muted);">Primary Low Open: N/A<br><small>(No bullish candle found)</small></div>', unsafe_allow_html=True)
        
        # ─────────────────────────────────────────────────────────────────────
        # SECONDARY PIVOTS (Expandable)
        # ─────────────────────────────────────────────────────────────────────
        has_secondary = s_hw is not None or s_lo is not None
        secondary_label = "📍 **SECONDARY PIVOTS** (Lower High & Higher Low)" if has_secondary else "📍 **SECONDARY PIVOTS** (None Detected)"
        
        with st.expander(secondary_label, expanded=has_secondary):
            if not has_secondary:
                st.markdown('''
                <div style="padding:20px;text-align:center;color:var(--text-muted);">
                    <div style="font-size:1.2rem;margin-bottom:8px;">No Secondary Pivots Detected</div>
                    <div style="font-size:0.85rem;">Secondary pivots require a rejection 1+ hour after the primary pivot</div>
                </div>
                ''', unsafe_allow_html=True)
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    if s_hw is not None and s_hw_asc is not None and s_hw_desc is not None:
                        st.markdown(f'''
                        <div class="prior-levels-section" style="margin-bottom:0;opacity:0.9;">
                            <div class="prior-levels-header">
                                <span class="prior-levels-icon">🔸</span>
                                <span class="prior-levels-title">Secondary High Wick</span>
                                <span class="prior-levels-anchor">{s_hw:,.2f}</span>
                            </div>
                            <div class="prior-levels-grid">
                                <div class="prior-level-item prior-level-sell">
                                    <div class="prior-level-direction">↗ Ascending</div>
                                    <div class="prior-level-value">{s_hw_asc:,.2f}</div>
                                    <div class="prior-level-action">SELL (Resistance)</div>
                                </div>
                                <div class="prior-level-item prior-level-buy">
                                    <div class="prior-level-direction">↘ Descending</div>
                                    <div class="prior-level-value">{s_hw_desc:,.2f}</div>
                                    <div class="prior-level-action">BUY (Support)</div>
                                </div>
                            </div>
                            <div class="prior-levels-note">Lower high after primary rejection</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="padding:20px;text-align:center;color:var(--text-muted);">Secondary High Wick: N/A</div>', unsafe_allow_html=True)
                
                with col2:
                    if s_lo is not None and s_lo_asc is not None and s_lo_desc is not None:
                        st.markdown(f'''
                        <div class="prior-levels-section" style="margin-bottom:0;opacity:0.9;">
                            <div class="prior-levels-header">
                                <span class="prior-levels-icon">🔹</span>
                                <span class="prior-levels-title">Secondary Low Open</span>
                                <span class="prior-levels-anchor">{s_lo:,.2f}</span>
                            </div>
                            <div class="prior-levels-grid">
                                <div class="prior-level-item prior-level-buy">
                                    <div class="prior-level-direction">↗ Ascending</div>
                                    <div class="prior-level-value">{s_lo_asc:,.2f}</div>
                                    <div class="prior-level-action">BUY (Support)</div>
                                </div>
                                <div class="prior-level-item prior-level-sell">
                                    <div class="prior-level-direction">↘ Descending</div>
                                    <div class="prior-level-value">{s_lo_desc:,.2f}</div>
                                    <div class="prior-level-action">SELL (Resistance)</div>
                                </div>
                            </div>
                            <div class="prior-levels-note">Higher low after primary defense (bullish)</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="padding:20px;text-align:center;color:var(--text-muted);">Secondary Low Open: N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown('''
        <div class="alert-box" style="background: rgba(255,215,0,0.1); border: 1px solid rgba(255,215,0,0.3);">
            <span style="font-size:1.2rem;">⚠️</span>
            <div>
                <div style="font-weight:600;color:var(--accent-gold);margin-bottom:4px;">Prior Day Data Unavailable</div>
                <div style="font-size:0.85rem;color:var(--text-secondary);">Use Manual Prior Day Override in sidebar to enable intermediate levels</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TRADE SETUPS (Option C - Primary + Secondary)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Check if we're in RTH (8:30 AM - 3:00 PM CT) for real premium fetching
    ct_now = datetime.now(CT)
    is_rth = 8.5 <= (ct_now.hour + ct_now.minute/60) < 15  # 8:30 AM to 3:00 PM
    
    if decision["no_trade"]:
        st.markdown('<div class="section-header"><div class="section-icon">🎲</div><h2 class="section-title">Trade Setup</h2></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="no-trade-card"><div class="no-trade-icon">⊘</div><div class="no-trade-title">NO TRADE</div><div class="no-trade-reason">{decision["no_trade_reason"]}</div></div>', unsafe_allow_html=True)
    else:
        # Show channel status
        channel_status = decision.get("channel_status", "LOCKED")
        if channel_status == "BUILDING":
            st.markdown(f'''
            <div class="alert-box alert-box-info" style="margin-bottom:20px;">
                <div class="alert-icon-large">🔄</div>
                <div class="alert-content">
                    <div class="alert-title">CHANNEL BUILDING</div>
                    <div class="alert-values" style="border:none;padding:0;margin-top:4px;">London session in progress • Channel locks at 5:30 AM CT</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
        
        # Function to get real or estimated premium for a trade
        def get_trade_premium(trade, current_spx, trading_date, is_rth):
            """Get real premium during RTH, with logic for trade status."""
            if not trade:
                return trade
            
            strike = trade["strike"]
            opt_type = "CALL" if trade["direction"] == "CALLS" else "PUT"
            entry_level = trade["entry_level"]
            
            # Determine if trade has already triggered
            # For CALLS: Trade triggers when price drops TO the floor (entry), then rises
            #            If current price > entry, we're either approaching or past target
            # For PUTS: Trade triggers when price rises TO the ceiling (entry), then drops
            #            If current price < entry, the trade has triggered and is in profit
            
            if opt_type == "CALL":
                trade_triggered = current_spx > entry_level  # Price above entry = either not reached or past
                # Actually for calls at floor: price drops to floor, then rises
                # If price is BELOW floor, trade hasn't triggered yet (approaching)
                # If price is ABOVE floor, either: never reached floor, or reached and bounced
                # We need to check if price is moving toward or away from entry
                trade_triggered = False  # For calls, we calculate entry premium (price dropping to floor)
                
            else:  # PUT
                # For puts at ceiling: price rises to ceiling, then drops
                # If current price < entry level, the trade has TRIGGERED (price dropped below entry)
                trade_triggered = current_spx < entry_level
            
            if is_rth and current_spx:
                # Fetch real premium from Polygon
                real_data = fetch_real_option_premium(strike, opt_type, trading_date)
                
                # Store debug info
                trade = trade.copy()
                trade["polygon_ticker"] = real_data.get("ticker")
                trade["polygon_error"] = real_data.get("error")
                trade["polygon_available"] = real_data.get("available")
                trade["polygon_bid"] = real_data.get("bid")
                trade["polygon_ask"] = real_data.get("ask")
                trade["polygon_mid"] = real_data.get("mid")
                trade["polygon_last"] = real_data.get("last")
                trade["polygon_delta"] = real_data.get("delta")
                
                if real_data["available"]:
                    current_premium = real_data["mid"] or real_data["last"]
                    delta = real_data["delta"]
                    underlying = real_data["underlying_price"] or current_spx
                    
                    # Store for debug
                    trade["calc_current_premium"] = current_premium
                    trade["calc_underlying"] = underlying
                    trade["calc_entry_level"] = entry_level
                    trade["calc_delta_used"] = delta
                    trade["trade_triggered"] = trade_triggered
                    
                    if trade_triggered:
                        # Trade has already triggered! Show current premium, not projected entry
                        trade["real_premium"] = True
                        trade["trade_status"] = "TRIGGERED"
                        trade["current_premium"] = current_premium
                        trade["current_spx"] = underlying
                        # Don't update entry_premium - keep the estimated one for reference
                        # But mark that we have live data
                        trade["live_current_premium"] = current_premium
                        
                        # Calculate profit from estimated entry to current
                        est_entry = trade["entry_premium"]
                        if est_entry and current_premium:
                            profit_pct = ((current_premium - est_entry) / est_entry) * 100
                            profit_dollars = (current_premium - est_entry) * 100
                            trade["current_profit_pct"] = round(profit_pct, 1)
                            trade["current_profit_dollars"] = round(profit_dollars, 0)
                    else:
                        # Trade not yet triggered - calculate projected entry premium
                        entry_premium = calculate_premium_at_entry(
                            current_premium, underlying, entry_level, strike, opt_type, delta
                        )
                        
                        trade["calc_result"] = entry_premium
                        trade["trade_status"] = "PENDING"
                        
                        if entry_premium:
                            # Update trade with real premium data
                            trade["entry_premium"] = entry_premium
                            trade["real_premium"] = True
                            trade["current_premium"] = current_premium
                            trade["current_spx"] = underlying
                            
                            # Recalculate targets based on projected entry
                            t1 = round(entry_premium * 1.50, 2)
                            t2 = round(entry_premium * 1.75, 2)
                            t3 = round(entry_premium * 2.00, 2)
                            trade["targets"] = {
                                "t1": {"price": t1, "profit_pct": 50, "profit_dollars": round((t1 - entry_premium) * 100, 0)},
                                "t2": {"price": t2, "profit_pct": 75, "profit_dollars": round((t2 - entry_premium) * 100, 0)},
                                "t3": {"price": t3, "profit_pct": 100, "profit_dollars": round((t3 - entry_premium) * 100, 0)},
                            }
            
            return trade
        
        # Update primary trade with real premium if in RTH
        p = get_trade_premium(decision["primary"], current_spx, actual_trading_date, is_rth)
        
        # PRIMARY TRADE
        st.markdown('<div class="section-header"><div class="section-icon icon-rocket">🚀</div><h2 class="section-title">PRIMARY Trade Setup</h2></div>', unsafe_allow_html=True)
        
        if p:
            tc = "calls" if p["direction"] == "CALLS" else "puts"
            di = "↗" if p["direction"] == "CALLS" else "↘"
            t = p["targets"]
            
            # Determine display based on trade status
            trade_status = p.get("trade_status", "PENDING")
            
            if trade_status == "TRIGGERED" and p.get("live_current_premium"):
                # Trade has triggered - show current premium and profit
                premium_label = "Current Premium (LIVE)"
                current_prem = p["live_current_premium"]
                profit_pct = p.get("current_profit_pct", 0)
                profit_dollars = p.get("current_profit_dollars", 0)
                profit_color = "var(--bull)" if profit_pct >= 0 else "var(--bear)"
                profit_sign = "+" if profit_pct >= 0 else ""
                premium_note = f'<div style="font-size:0.7rem;color:{profit_color};margin-top:4px;font-weight:600;">P/L: {profit_sign}{profit_pct:.1f}% ({profit_sign}${profit_dollars:,.0f})</div>'
                premium_value = current_prem
                # Show TRIGGERED badge
                status_badge = '<div style="background:var(--bull);color:#000;padding:4px 12px;border-radius:20px;font-size:0.7rem;font-weight:700;display:inline-block;margin-bottom:8px;">✓ TRADE TRIGGERED</div>'
            elif p.get("real_premium"):
                # Trade pending - show projected entry premium
                premium_label = "Entry Premium (LIVE)"
                premium_value = p["entry_premium"]
                premium_note = f'<div style="font-size:0.7rem;color:var(--accent-cyan);margin-top:4px;">Current: ${p["current_premium"]:.2f} @ SPX {p["current_spx"]:,.0f}</div>'
                status_badge = ""
            else:
                premium_label = "Entry Premium (EST)"
                premium_value = p["entry_premium"]
                premium_note = ""
                status_badge = ""
                # Show debug info if we tried to fetch but failed
                if p.get("polygon_ticker"):
                    premium_note = f'<div style="font-size:0.65rem;color:var(--text-muted);margin-top:4px;">Polygon: {p.get("polygon_error", "No data")}</div>'
            
            st.markdown(f'''
            <div class="trade-card trade-card-{tc}">
                <div class="trade-header">
                    <div class="trade-name">{di} {p["name"]}</div>
                    <div class="trade-confidence trade-confidence-{p["confidence"].lower()}">{p["confidence"]} CONFIDENCE</div>
                </div>
                {status_badge}
                <div class="trade-contract trade-contract-{tc}">{p["contract"]}</div>
                <div class="trade-grid">
                    <div class="trade-metric"><div class="trade-metric-label">{premium_label}</div><div class="trade-metric-value">${premium_value:.2f}</div>{premium_note}</div>
                    <div class="trade-metric"><div class="trade-metric-label">SPX Entry</div><div class="trade-metric-value">{p["entry_level"]:,.2f}</div></div>
                    <div class="trade-metric"><div class="trade-metric-label">SPX Stop</div><div class="trade-metric-value">{p["stop_level"]:,.2f}</div></div>
                </div>
                <div class="trade-targets">
                    <div class="targets-header">◎ Profit Targets</div>
                    <div class="targets-grid">
                        <div class="target-item"><div class="target-label">50%</div><div class="target-price">${t["t1"]["price"]:.2f}</div><div class="target-profit">+${t["t1"]["profit_dollars"]:,.0f}</div></div>
                        <div class="target-item"><div class="target-label">75%</div><div class="target-price">${t["t2"]["price"]:.2f}</div><div class="target-profit">+${t["t2"]["profit_dollars"]:,.0f}</div></div>
                        <div class="target-item"><div class="target-label">100%</div><div class="target-price">${t["t3"]["price"]:.2f}</div><div class="target-profit">+${t["t3"]["profit_dollars"]:,.0f}</div></div>
                    </div>
                </div>
                <div class="trade-trigger"><div class="trigger-label">◈ Entry Trigger</div><div class="trigger-text">{p["trigger"]}</div></div>
            </div>
            ''', unsafe_allow_html=True)
            with st.expander("📋 Trade Rationale"):
                st.write(p["rationale"])
            # Debug: Show Polygon API details during RTH
            if is_rth and p.get("polygon_ticker"):
                with st.expander("🔧 Polygon API Debug"):
                    debug_text = f"""Ticker: {p.get('polygon_ticker')}
Available: {p.get('polygon_available')}
Error: {p.get('polygon_error')}

--- Raw Data ---
Bid: {p.get('polygon_bid')}
Ask: {p.get('polygon_ask')}
Mid: {p.get('polygon_mid')}
Last: {p.get('polygon_last')}
Delta: {p.get('polygon_delta')}

--- Calculation ---
Current Premium: {p.get('calc_current_premium')}
Current SPX: {p.get('calc_underlying')}
Entry Level: {p.get('calc_entry_level')}
Delta Used: {p.get('calc_delta_used')}
Calculated Entry Premium: {p.get('calc_result')}
"""
                    st.code(debug_text)
        
        # ALTERNATE TRADE (If structure breaks)
        if decision.get("alternate"):
            a = get_trade_premium(decision["alternate"], current_spx, actual_trading_date, is_rth)
            st.markdown('<div class="section-header"><div class="section-icon">⚡</div><h2 class="section-title">ALTERNATE: If Structure Breaks</h2></div>', unsafe_allow_html=True)
            tc = "calls" if a["direction"] == "CALLS" else "puts"
            di = "↗" if a["direction"] == "CALLS" else "↘"
            t = a["targets"]
            
            # Determine display based on trade status
            trade_status = a.get("trade_status", "PENDING")
            
            if trade_status == "TRIGGERED" and a.get("live_current_premium"):
                premium_label = "Current Premium (LIVE)"
                current_prem = a["live_current_premium"]
                profit_pct = a.get("current_profit_pct", 0)
                profit_dollars = a.get("current_profit_dollars", 0)
                profit_color = "var(--bull)" if profit_pct >= 0 else "var(--bear)"
                profit_sign = "+" if profit_pct >= 0 else ""
                premium_note = f'<div style="font-size:0.7rem;color:{profit_color};margin-top:4px;font-weight:600;">P/L: {profit_sign}{profit_pct:.1f}% ({profit_sign}${profit_dollars:,.0f})</div>'
                premium_value = current_prem
                status_badge = '<div style="background:var(--bull);color:#000;padding:4px 12px;border-radius:20px;font-size:0.7rem;font-weight:700;display:inline-block;margin-bottom:8px;">✓ TRADE TRIGGERED</div>'
            elif a.get("real_premium"):
                premium_label = "Entry Premium (LIVE)"
                premium_value = a["entry_premium"]
                premium_note = f'<div style="font-size:0.7rem;color:var(--accent-cyan);margin-top:4px;">Current: ${a["current_premium"]:.2f} @ SPX {a["current_spx"]:,.0f}</div>'
                status_badge = ""
            else:
                premium_label = "Entry Premium (EST)"
                premium_value = a["entry_premium"]
                premium_note = ""
                status_badge = ""
            
            st.markdown(f'''
            <div class="trade-card trade-card-{tc}" style="border-style: dashed;">
                <div class="trade-header">
                    <div class="trade-name">{di} {a["name"]}</div>
                    <div class="trade-confidence trade-confidence-{a["confidence"].lower()}">{a["confidence"]} CONFIDENCE</div>
                </div>
                {status_badge}
                <div class="trade-contract trade-contract-{tc}">{a["contract"]}</div>
                <div class="trade-grid">
                    <div class="trade-metric"><div class="trade-metric-label">{premium_label}</div><div class="trade-metric-value">${premium_value:.2f}</div>{premium_note}</div>
                    <div class="trade-metric"><div class="trade-metric-label">SPX Entry</div><div class="trade-metric-value">{a["entry_level"]:,.2f}</div></div>
                    <div class="trade-metric"><div class="trade-metric-label">SPX Stop</div><div class="trade-metric-value">{a["stop_level"]:,.2f}</div></div>
                </div>
                <div class="trade-targets">
                    <div class="targets-header">◎ Profit Targets</div>
                    <div class="targets-grid">
                        <div class="target-item"><div class="target-label">50%</div><div class="target-price">${t["t1"]["price"]:.2f}</div><div class="target-profit">+${t["t1"]["profit_dollars"]:,.0f}</div></div>
                        <div class="target-item"><div class="target-label">75%</div><div class="target-price">${t["t2"]["price"]:.2f}</div><div class="target-profit">+${t["t2"]["profit_dollars"]:,.0f}</div></div>
                        <div class="target-item"><div class="target-label">100%</div><div class="target-price">${t["t3"]["price"]:.2f}</div><div class="target-profit">+${t["t3"]["profit_dollars"]:,.0f}</div></div>
                    </div>
                </div>
                <div class="trade-trigger"><div class="trigger-label">◈ Entry Trigger</div><div class="trigger-text">{a["trigger"]}</div></div>
            </div>
            ''', unsafe_allow_html=True)
            with st.expander("📋 Trade Rationale"):
                st.write(a["rationale"])
        
        # SECONDARY TRADE (other side of channel)
        if decision.get("secondary"):
            s = get_trade_premium(decision["secondary"], current_spx, actual_trading_date, is_rth)
            st.markdown('<div class="section-header"><div class="section-icon icon-rotate">🔄</div><h2 class="section-title">SECONDARY Trade Setup</h2></div>', unsafe_allow_html=True)
            tc = "calls" if s["direction"] == "CALLS" else "puts"
            di = "↗" if s["direction"] == "CALLS" else "↘"
            t = s["targets"]
            
            # Determine display based on trade status
            trade_status = s.get("trade_status", "PENDING")
            
            if trade_status == "TRIGGERED" and s.get("live_current_premium"):
                premium_label = "Current Premium (LIVE)"
                current_prem = s["live_current_premium"]
                profit_pct = s.get("current_profit_pct", 0)
                profit_dollars = s.get("current_profit_dollars", 0)
                profit_color = "var(--bull)" if profit_pct >= 0 else "var(--bear)"
                profit_sign = "+" if profit_pct >= 0 else ""
                premium_note = f'<div style="font-size:0.7rem;color:{profit_color};margin-top:4px;font-weight:600;">P/L: {profit_sign}{profit_pct:.1f}% ({profit_sign}${profit_dollars:,.0f})</div>'
                premium_value = current_prem
                status_badge = '<div style="background:var(--bull);color:#000;padding:4px 12px;border-radius:20px;font-size:0.7rem;font-weight:700;display:inline-block;margin-bottom:8px;">✓ TRADE TRIGGERED</div>'
            elif s.get("real_premium"):
                premium_label = "Entry Premium (LIVE)"
                premium_value = s["entry_premium"]
                premium_note = f'<div style="font-size:0.7rem;color:var(--accent-cyan);margin-top:4px;">Current: ${s["current_premium"]:.2f} @ SPX {s["current_spx"]:,.0f}</div>'
                status_badge = ""
            else:
                premium_label = "Entry Premium (EST)"
                premium_value = s["entry_premium"]
                premium_note = ""
                status_badge = ""
            
            st.markdown(f'''
            <div class="trade-card trade-card-{tc}" style="opacity: 0.85;">
                <div class="trade-header">
                    <div class="trade-name">{di} {s["name"]}</div>
                    <div class="trade-confidence trade-confidence-{s["confidence"].lower()}">{s["confidence"]} CONFIDENCE</div>
                </div>
                {status_badge}
                <div class="trade-contract trade-contract-{tc}">{s["contract"]}</div>
                <div class="trade-grid">
                    <div class="trade-metric"><div class="trade-metric-label">{premium_label}</div><div class="trade-metric-value">${premium_value:.2f}</div>{premium_note}</div>
                    <div class="trade-metric"><div class="trade-metric-label">SPX Entry</div><div class="trade-metric-value">{s["entry_level"]:,.2f}</div></div>
                    <div class="trade-metric"><div class="trade-metric-label">SPX Stop</div><div class="trade-metric-value">{s["stop_level"]:,.2f}</div></div>
                </div>
                <div class="trade-targets">
                    <div class="targets-header">◎ Profit Targets</div>
                    <div class="targets-grid">
                        <div class="target-item"><div class="target-label">50%</div><div class="target-price">${t["t1"]["price"]:.2f}</div><div class="target-profit">+${t["t1"]["profit_dollars"]:,.0f}</div></div>
                        <div class="target-item"><div class="target-label">75%</div><div class="target-price">${t["t2"]["price"]:.2f}</div><div class="target-profit">+${t["t2"]["profit_dollars"]:,.0f}</div></div>
                        <div class="target-item"><div class="target-label">100%</div><div class="target-price">${t["t3"]["price"]:.2f}</div><div class="target-profit">+${t["t3"]["profit_dollars"]:,.0f}</div></div>
                    </div>
                </div>
                <div class="trade-trigger"><div class="trigger-label">◈ Entry Trigger</div><div class="trigger-text">{s["trigger"]}</div></div>
            </div>
            ''', unsafe_allow_html=True)
            with st.expander("📋 Trade Rationale"):
                st.write(s["rationale"])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SESSIONS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header"><div class="section-icon">🌍</div><h2 class="section-title">Global Sessions</h2></div>', unsafe_allow_html=True)
    
    session_data = [("🦘", "Sydney", sydney, "icon-kangaroo"), ("🗼", "Tokyo", tokyo, ""), ("🏛", "London", london, ""), ("🌙", "Overnight", overnight, "icon-glow-purple")]
    cols = st.columns(4)
    for i, (icon, name, data, anim_class) in enumerate(session_data):
        with cols[i]:
            if data:
                h_mark = " ⬆" if upper_pivot and upper_pivot == data.get("high") else ""
                l_mark = " ⬇" if lower_pivot and lower_pivot == data.get("low") else ""
                st.markdown(f'<div class="session-card"><div class="session-icon {anim_class}">{icon}</div><div class="session-name">{name}</div><div class="session-data"><div class="session-value"><span style="color:var(--text-tertiary);">H</span><span class="session-high">{data["high"]:,.2f}{h_mark}</span></div><div class="session-value"><span style="color:var(--text-tertiary);">L</span><span class="session-low">{data["low"]:,.2f}{l_mark}</span></div></div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="session-card" style="opacity:0.5;"><div class="session-icon {anim_class}">{icon}</div><div class="session-name">{name}</div><div class="session-data"><div style="color:var(--text-muted);font-size:0.85rem;">No data</div></div></div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INDICATORS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header"><div class="section-icon">📈</div><h2 class="section-title">Technical Indicators</h2></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        sc = "bullish" if ema_data["above_200"] else "bearish"
        st.markdown(f'<div class="indicator-card"><div class="indicator-header"><div class="indicator-icon">📊</div><div class="indicator-title">200 EMA Bias</div></div><div class="indicator-row"><span class="indicator-label">Price</span><span class="indicator-value">{ema_data.get("price", "N/A")}</span></div><div class="indicator-row"><span class="indicator-label">200 EMA</span><span class="indicator-value">{ema_data.get("ema_200", "N/A")}</span></div><div class="indicator-status indicator-status-{sc}">{"✓ ABOVE" if ema_data["above_200"] else "✗ BELOW"}</div></div>', unsafe_allow_html=True)
    with col2:
        sc = "bullish" if ema_data["ema_cross"] == "BULLISH" else "bearish"
        st.markdown(f'<div class="indicator-card"><div class="indicator-header"><div class="indicator-icon">📈</div><div class="indicator-title">8/21 EMA Cross</div></div><div class="indicator-row"><span class="indicator-label">8 EMA</span><span class="indicator-value">{ema_data.get("ema_8", "N/A")}</span></div><div class="indicator-row"><span class="indicator-label">21 EMA</span><span class="indicator-value">{ema_data.get("ema_21", "N/A")}</span></div><div class="indicator-status indicator-status-{sc}">{"✓" if ema_data["ema_cross"] == "BULLISH" else "✗"} {ema_data["ema_cross"]}</div></div>', unsafe_allow_html=True)
    with col3:
        if vix_range["available"]:
            vix_icon_ind = {"ABOVE": "▲", "IN RANGE": "◆", "BELOW": "▼"}.get(vix_pos.value, "○")
            sc = "bearish" if vix_pos == VIXPosition.ABOVE_RANGE else "bullish"
            st.markdown(f'<div class="indicator-card"><div class="indicator-header"><div class="indicator-icon">📉</div><div class="indicator-title">VIX Overnight</div></div><div class="indicator-row"><span class="indicator-label">Range</span><span class="indicator-value">{vix_range["bottom"]} - {vix_range["top"]}</span></div><div class="indicator-row"><span class="indicator-label">Current</span><span class="indicator-value">{vix}</span></div><div class="indicator-status indicator-status-{sc}">{vix_icon_ind} {vix_pos.value}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="indicator-card"><div class="indicator-header"><div class="indicator-icon">📉</div><div class="indicator-title">VIX Overnight</div></div><div class="indicator-row"><span class="indicator-label">Current</span><span class="indicator-value">{vix}</span></div><div style="margin-top:8px;color:var(--text-muted);font-size:0.85rem;">Range data unavailable</div></div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown('<div style="margin-top:40px;padding:20px 0;border-top:1px solid var(--border-subtle);text-align:center;"><p style="font-family:\'Share Tech Mono\',monospace;font-size:0.75rem;color:var(--text-muted);letter-spacing:2px;">SPX PROPHET • STRUCTURAL 0DTE TRADING SYSTEM</p></div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()

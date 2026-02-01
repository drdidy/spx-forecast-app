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
def fetch_vix_overnight_range(trading_date, zone_start_hour=2, zone_start_min=0, zone_end_hour=6, zone_end_min=0):
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
    - highest_wick: The highest high (wick) of any RTH candle
    - lowest_close: The lowest close of any RTH candle
    """
    result = {
        "highest_wick": None, "highest_wick_time": None,
        "lowest_close": None, "lowest_close_time": None,
        "high": None, "low": None, "close": None,
        "available": False
    }
    try:
        prior_day = get_prior_trading_day(trading_date)
        
        # Fetch 5-minute candles for ES futures from Yahoo
        es = yf.Ticker("ES=F")
        # Get 5 days of data to ensure we have the prior day
        df = es.history(period="5d", interval="5m")
        
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
            rth_df = df[(df.index >= rth_start) & (df.index <= rth_end)]
            
            if not rth_df.empty and len(rth_df) > 5:
                # Highest Wick = highest high of any candle
                high_idx = rth_df['High'].idxmax()
                result["highest_wick"] = round(float(rth_df.loc[high_idx, 'High']), 2)
                result["highest_wick_time"] = high_idx
                
                # Lowest Close = lowest close of any candle (NOT lowest wick)
                lowest_close_idx = rth_df['Close'].idxmin()
                result["lowest_close"] = round(float(rth_df.loc[lowest_close_idx, 'Close']), 2)
                result["lowest_close_time"] = lowest_close_idx
                
                # Also store overall H/L/C for display
                result["high"] = result["highest_wick"]
                result["low"] = round(float(rth_df['Low'].min()), 2)
                result["close"] = round(float(rth_df.iloc[-1]['Close']), 2)
                result["available"] = True
    except Exception as e:
        pass
    return result

def calc_prior_day_targets(prior_rth, ref_time):
    """Calculate BOTH ascending and descending targets from prior day anchors.
    
    From HIGHEST WICK:
    - Ascending line (+0.52/30min) = Resistance (SELL point)
    - Descending line (-0.52/30min) = Support (BUY point)
    
    From LOWEST CLOSE:
    - Ascending line (+0.52/30min) = Support (BUY point)
    - Descending line (-0.52/30min) = Resistance (SELL point)
    
    Returns dict with all four targets.
    """
    result = {
        "available": False,
        "highest_wick": None,
        "highest_wick_ascending": None,  # SELL point (resistance)
        "highest_wick_descending": None,  # BUY point (support)
        "lowest_close": None,
        "lowest_close_ascending": None,   # BUY point (support)
        "lowest_close_descending": None,  # SELL point (resistance)
    }
    
    if not prior_rth["available"]:
        return result
    
    result["available"] = True
    result["highest_wick"] = prior_rth["highest_wick"]
    result["lowest_close"] = prior_rth["lowest_close"]
    
    # Calculate blocks from highest wick time (using trading blocks for cross-day)
    if prior_rth["highest_wick"] is not None and prior_rth["highest_wick_time"]:
        blocks = trading_blocks_between(prior_rth["highest_wick_time"], ref_time)
        result["highest_wick_ascending"] = round(prior_rth["highest_wick"] + SLOPE * blocks, 2)
        result["highest_wick_descending"] = round(prior_rth["highest_wick"] - SLOPE * blocks, 2)
    
    # Calculate blocks from lowest close time (using trading blocks for cross-day)
    if prior_rth["lowest_close"] is not None and prior_rth["lowest_close_time"]:
        blocks = trading_blocks_between(prior_rth["lowest_close_time"], ref_time)
        result["lowest_close_ascending"] = round(prior_rth["lowest_close"] + SLOPE * blocks, 2)
        result["lowest_close_descending"] = round(prior_rth["lowest_close"] - SLOPE * blocks, 2)
    
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


def analyze_market_state_v2(current_spx, dual_levels, channel_type, channel_reason,
                            retail_bias, ema_bias, vix_position, vix, 
                            session_tests, gap_analysis, prior_close_analysis, vix_structure):
    """
    OPTION C: Dual Channel Decision Engine
    
    Always provides:
    1. All 4 levels (asc_floor, asc_ceiling, desc_ceiling, desc_floor)
    2. Dominant channel detection with reasoning
    3. PRIMARY trade at dominant level (higher probability)
    4. SECONDARY trade at other level (backup/hedge)
    5. Structure break alerts
    6. Confluence-based confidence scoring
    """
    
    if current_spx is None or dual_levels is None:
        return {
            "no_trade": True, 
            "no_trade_reason": "Missing price data",
            "dual_levels": None,
            "primary": None,
            "secondary": None,
            "structure_alerts": [],
            "calls_factors": [],
            "puts_factors": [],
            "position_summary": "No data available"
        }
    
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
    
    # Structure alerts
    structure_alerts = []
    if channel_type == ChannelType.ASCENDING and below_asc_floor:
        structure_alerts.append(f"⚠️ STRUCTURE BROKEN: Price below ascending floor ({asc_floor:.2f})")
    if channel_type == ChannelType.DESCENDING and above_desc_ceiling:
        structure_alerts.append(f"⚠️ STRUCTURE BROKEN: Price above descending ceiling ({desc_ceiling:.2f})")
    
    # Initialize result
    result = {
        "no_trade": False, "no_trade_reason": None,
        "channel_type": channel_type, "channel_reason": channel_reason,
        "dual_levels": dual_levels,
        "calls_factors": calls_factors, "puts_factors": puts_factors,
        "structure_alerts": structure_alerts,
        "primary": None, "secondary": None, "position_summary": ""
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
        if below_asc_floor:
            # Structure broken
            result["primary"] = make_trade("Breakdown Continuation", "PUTS", asc_floor, asc_floor + 10,
                f"Sell rallies to broken floor {asc_floor:.2f}",
                f"Structure broken • {len(puts_factors)} factors", calc_conf("PUTS", True), True)
            result["secondary"] = make_trade("Floor Reclaim", "CALLS", asc_floor, asc_floor - 10,
                f"ONLY if price reclaims {asc_floor:.2f}",
                "Recovery scenario", calc_conf("CALLS", True, True), False)
            result["position_summary"] = f"⚠️ BELOW ascending floor ({asc_floor:.2f}) - BEARISH bias"
        else:
            result["primary"] = make_trade("Ascending Floor Bounce", "CALLS", asc_floor, asc_floor - 10,
                f"Wait for price at {asc_floor:.2f}",
                f"KEY: Ascending floor • {len(calls_factors)} factors", calc_conf("CALLS", near_asc_floor), True)
            result["secondary"] = make_trade("Desc Ceiling Rejection", "PUTS", desc_ceiling, desc_ceiling + 10,
                f"If price reaches {desc_ceiling:.2f}",
                f"Secondary level • {len(puts_factors)} factors", calc_conf("PUTS", near_desc_ceiling), False)
            result["position_summary"] = f"{'✅ AT' if near_asc_floor else '📍 Wait for'} ascending floor ({asc_floor:.2f})"
    
    # DESCENDING DOMINANT
    elif channel_type == ChannelType.DESCENDING:
        if above_desc_ceiling:
            # Structure broken
            result["primary"] = make_trade("Breakout Continuation", "CALLS", desc_ceiling, desc_ceiling - 10,
                f"Buy dips to broken ceiling {desc_ceiling:.2f}",
                f"Structure broken • {len(calls_factors)} factors", calc_conf("CALLS", True), True)
            result["secondary"] = make_trade("Failed Breakout", "PUTS", desc_ceiling, desc_ceiling + 10,
                f"ONLY if price fails below {desc_ceiling:.2f}",
                "Rejection scenario", calc_conf("PUTS", True, True), False)
            result["position_summary"] = f"🚀 ABOVE descending ceiling ({desc_ceiling:.2f}) - BULLISH bias"
        else:
            result["primary"] = make_trade("Desc Ceiling Rejection", "PUTS", desc_ceiling, desc_ceiling + 10,
                f"Wait for price at {desc_ceiling:.2f}",
                f"KEY: Descending ceiling • {len(puts_factors)} factors", calc_conf("PUTS", near_desc_ceiling), True)
            result["secondary"] = make_trade("Ascending Floor Bounce", "CALLS", asc_floor, asc_floor - 10,
                f"If price reaches {asc_floor:.2f}",
                f"Secondary level • {len(calls_factors)} factors", calc_conf("CALLS", near_asc_floor), False)
            result["position_summary"] = f"{'✅ AT' if near_desc_ceiling else '📍 Wait for'} descending ceiling ({desc_ceiling:.2f})"
    
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Orbitron:wght@400;500;600;700;800;900&display=swap');

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
    /* Font Families - 3 Purpose-Driven Fonts */
    --font-display: 'Orbitron', 'Plus Jakarta Sans', sans-serif;  /* Headlines, big numbers */
    --font-body: 'Plus Jakarta Sans', 'Inter', sans-serif;        /* Body text, cards */
    --font-mono: 'JetBrains Mono', monospace;                     /* Labels, technical data */
    
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
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
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
   HERO BANNER - CINEMATIC HEADER
   ═══════════════════════════════════════════════════════════════════════════ */
.hero-banner {
    position: relative;
    padding: 40px 40px;
    margin: -1rem -1rem 30px -1rem;
    background: linear-gradient(180deg, var(--bg-panel) 0%, var(--bg-terminal) 100%);
    border-bottom: 2px solid transparent;
    border-image: var(--gradient-premium) 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 30px;
    overflow: hidden;
}

.hero-banner::before {
    content: '';
    position: absolute;
    inset: 0;
    background: 
        radial-gradient(ellipse 80% 120% at 20% 50%, rgba(0, 245, 212, 0.12) 0%, transparent 50%),
        radial-gradient(ellipse 80% 120% at 80% 50%, rgba(155, 93, 229, 0.1) 0%, transparent 50%),
        radial-gradient(ellipse 100% 100% at 50% 0%, rgba(0, 187, 249, 0.08) 0%, transparent 60%);
    animation: heroAurora 10s ease-in-out infinite;
}

@keyframes heroAurora {
    0%, 100% { opacity: 0.6; transform: scale(1) translateX(0); }
    33% { opacity: 1; transform: scale(1.05) translateX(2%); }
    66% { opacity: 0.8; transform: scale(1.02) translateX(-2%); }
}

.hero-banner::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--gradient-premium);
    box-shadow: 0 0 20px rgba(0, 245, 212, 0.5), 0 0 40px rgba(155, 93, 229, 0.3);
}

/* Animated Holographic Logo */
.prophet-logo {
    position: relative;
    width: 90px;
    height: 90px;
    flex-shrink: 0;
    z-index: 2;
}

.logo-pyramid {
    position: absolute;
    width: 100%;
    height: 100%;
    animation: pyramidFloat 4s ease-in-out infinite;
}

@keyframes pyramidFloat {
    0%, 100% { transform: translateY(0) scale(1) rotateY(0deg); }
    50% { transform: translateY(-6px) scale(1.05) rotateY(5deg); }
}

.pyramid-body {
    position: absolute;
    top: 4px;
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 42px solid transparent;
    border-right: 42px solid transparent;
    border-bottom: 75px solid rgba(0, 245, 212, 0.15);
    filter: drop-shadow(0 0 25px rgba(0, 245, 212, 0.4));
    animation: pyramidGlow 2s ease-in-out infinite;
}

@keyframes pyramidGlow {
    0%, 100% { filter: drop-shadow(0 0 20px rgba(0, 245, 212, 0.3)); border-bottom-color: rgba(0, 245, 212, 0.15); }
    50% { filter: drop-shadow(0 0 40px rgba(0, 245, 212, 0.6)); border-bottom-color: rgba(0, 245, 212, 0.25); }
}

.pyramid-inner {
    position: absolute;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 26px solid transparent;
    border-right: 26px solid transparent;
    border-bottom: 46px solid rgba(155, 93, 229, 0.2);
    animation: innerPulse 2s ease-in-out infinite 0.5s;
}

@keyframes innerPulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
}

.eye-container {
    position: absolute;
    top: 28px;
    left: 50%;
    transform: translateX(-50%);
    width: 32px;
    height: 20px;
}

.eye-rays {
    position: absolute;
    width: 60px;
    height: 60px;
    top: -20px;
    left: -14px;
    background: radial-gradient(circle, rgba(254, 228, 64, 0.3) 0%, transparent 60%);
    animation: raysPulse 1.5s ease-in-out infinite;
}

@keyframes raysPulse {
    0%, 100% { opacity: 0.4; transform: scale(0.9); }
    50% { opacity: 1; transform: scale(1.2); }
}

.eye-outer {
    position: absolute;
    width: 32px;
    height: 18px;
    border: 2px solid var(--accent-gold);
    border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
    animation: eyeBlink 4s ease-in-out infinite;
    box-shadow: 0 0 15px var(--accent-gold), 0 0 30px rgba(254, 228, 64, 0.3), inset 0 0 10px rgba(254, 228, 64, 0.3);
}

@keyframes eyeBlink {
    0%, 45%, 55%, 100% { transform: scaleY(1); }
    50% { transform: scaleY(0.1); }
}

.eye-iris {
    position: absolute;
    width: 14px;
    height: 14px;
    background: radial-gradient(circle, var(--accent-gold) 0%, #ff9500 60%, #ff6b00 100%);
    border-radius: 50%;
    top: 2px;
    left: 9px;
    box-shadow: 0 0 15px var(--accent-gold), 0 0 25px rgba(254, 228, 64, 0.5);
    animation: irisGlow 2s ease-in-out infinite;
}

@keyframes irisGlow {
    0%, 100% { box-shadow: 0 0 10px var(--accent-gold); }
    50% { box-shadow: 0 0 25px var(--accent-gold), 0 0 40px rgba(254, 228, 64, 0.6); }
}

.eye-pupil {
    position: absolute;
    width: 6px;
    height: 6px;
    background: #000;
    border-radius: 50%;
    top: 4px;
    left: 4px;
    box-shadow: inset 0 0 3px rgba(254, 228, 64, 0.5);
}

.hero-content {
    position: relative;
    z-index: 2;
    text-align: center;
}

.brand-name {
    font-family: var(--font-display);
    font-size: var(--text-3xl);
    font-weight: 900;
    letter-spacing: 8px;
    background: var(--gradient-premium);
    background-size: 200% 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    text-transform: uppercase;
    animation: gradientFlow 4s ease infinite;
    text-shadow: 0 0 40px rgba(0, 245, 212, 0.3);
}

@keyframes gradientFlow {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

.brand-tagline {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-secondary);
    letter-spacing: 4px;
    margin-top: 8px;
    text-transform: uppercase;
    font-weight: 500;
    opacity: 0.8;
}
    transform: translate(-50%, -50%);
    background: radial-gradient(circle, rgba(0,229,199,0.25) 0%, transparent 60%);
    animation: rayPulse 2.5s ease-in-out infinite;
}

@keyframes rayPulse {
    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.4; }
    50% { transform: translate(-50%, -50%) scale(1.4); opacity: 0.7; }
}

.hero-content {
    position: relative;
    z-index: 2;
}

.brand-name {
    font-family: var(--font-body);
    font-size: var(--text-2xl);
    font-weight: 800;
    letter-spacing: 4px;
    background: var(--gradient-premium);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    text-transform: uppercase;
}

.brand-tagline {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-muted);
    letter-spacing: 3px;
    margin-top: 4px;
    text-transform: uppercase;
    font-weight: 500;
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

/* Indicator Cards - Equal height guaranteed */
.indicator-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px;
    height: 100%;
    min-height: 160px;
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
    border-radius: var(--radius-lg);
}

.indicator-card:hover {
    border-color: var(--border-accent);
    box-shadow: var(--shadow-glow-cyan);
}

.indicator-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border-subtle);
    position: relative;
    z-index: 1;
}

.indicator-icon {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--bg-elevated) 0%, var(--bg-card) 100%);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    font-size: var(--text-md);
}

.indicator-title {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    font-weight: 700;
    color: var(--text-bright);
    letter-spacing: 0.3px;
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
    font-family: var(--font-mono);
    font-size: var(--text-sm);
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
   SECTION HEADERS - Premium Dividers
   ═══════════════════════════════════════════════════════════════════════════ */
.section-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin: 44px 0 24px 0;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-subtle);
    position: relative;
}

.section-header::before {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 0;
    width: 120px;
    height: 3px;
    background: var(--gradient-premium);
    box-shadow: 0 0 15px rgba(0, 245, 212, 0.4);
    border-radius: 2px;
}

.section-icon {
    width: 46px;
    height: 46px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--bg-elevated) 0%, var(--bg-card) 100%);
    border: 1px solid var(--border-accent);
    border-radius: var(--radius-md);
    font-size: var(--text-lg);
    box-shadow: var(--shadow-sm), 0 0 15px rgba(0, 245, 212, 0.15);
    color: var(--accent-cyan);
}

.section-title {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 700;
    color: var(--text-bright);
    margin: 0;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

/* ═══════════════════════════════════════════════════════════════════════════
   METRIC CARDS - Top Row KPIs
   ═══════════════════════════════════════════════════════════════════════════ */
.metric-card {
    background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-panel) 100%);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 22px 26px;
    text-align: center;
    height: 100%;
    min-height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: center;
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
    height: 2px;
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
    font-family: var(--font-body);
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
    font-family: var(--font-body);
    font-size: var(--text-sm);
    font-weight: 700;
    color: var(--text-bright);
}

.prior-levels-anchor {
    margin-left: auto;
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    color: var(--accent-cyan);
    font-weight: 700;
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
    font-family: var(--font-body);
    font-size: var(--text-lg);
    font-weight: 800;
    color: var(--text-bright);
    margin-bottom: 8px;
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
    font-family: var(--font-body);
    font-size: var(--text-md);
    font-weight: 700;
    color: var(--text-bright);
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
    font-family: var(--font-body);
    font-size: var(--text-lg);
    font-weight: 800;
    color: var(--text-bright);
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
    font-family: var(--font-body);
    font-size: var(--text-lg);
    font-weight: 800;
    color: var(--text-bright);
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
   SESSION CARDS
   ═══════════════════════════════════════════════════════════════════════════ */
.session-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px;
    text-align: center;
    height: 100%;
    min-height: 140px;
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

.session-card:hover {
    border-color: var(--border-accent);
    transform: translateY(-3px);
    box-shadow: var(--shadow-glow-cyan);
}

.session-icon {
    font-size: var(--text-xl);
    margin-bottom: 10px;
    position: relative;
    z-index: 1;
}

.session-name {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    font-weight: 700;
    color: var(--text-bright);
    margin-bottom: 14px;
    position: relative;
    z-index: 1;
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
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    font-weight: 600;
}

.session-high { color: var(--bear); }
.session-low { color: var(--bull); }

/* ═══════════════════════════════════════════════════════════════════════════
   ALERT BOXES
   ═══════════════════════════════════════════════════════════════════════════ */
.alert-box {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 20px 24px;
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
    width: 4px;
    height: 100%;
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

.alert-content { flex: 1; }

.alert-title {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    font-weight: 700;
    color: var(--text-bright);
    margin-bottom: 6px;
}

.alert-text {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--text-secondary);
    line-height: 1.5;
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
    font-family: var(--font-body);
    font-size: var(--text-xl);
    font-weight: 800;
    color: var(--bear);
    margin-bottom: 12px;
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
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 800 !important;
}

[data-testid="stMetricLabel"] {
    font-family: 'JetBrains Mono', monospace !important;
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
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
}

section[data-testid="stSidebar"] h4 {
    color: var(--accent-cyan) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
}

section[data-testid="stSidebar"] h5 {
    color: var(--text-secondary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
}

section[data-testid="stSidebar"] label {
    color: var(--text-secondary) !important;
    font-family: 'Inter', sans-serif !important;
}

section[data-testid="stSidebar"] input {
    background: var(--bg-input) !important;
    color: var(--text-bright) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-sm) !important;
}

section[data-testid="stSidebar"] input:focus {
    border-color: var(--accent-cyan) !important;
    box-shadow: 0 0 0 2px var(--accent-cyan-soft) !important;
}

section[data-testid="stSidebar"] .stSelectbox > div > div {
    background: var(--bg-input) !important;
    color: var(--text-bright) !important;
}

section[data-testid="stSidebar"] p {
    color: var(--text-muted) !important;
}

/* Buttons */
.stButton > button {
    font-family: 'JetBrains Mono', monospace !important;
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
        trading_date = st.date_input("Trading Date", value=date.today())
        
        col1, col2 = st.columns(2)
        ref_hour = col1.selectbox("Ref Hour", options=list(range(8, 12)), index=1, format_func=lambda x: f"{x}:00")
        ref_min = col2.selectbox("Ref Min", options=[0, 15, 30, 45], index=0, format_func=lambda x: f":{x:02d}")
        
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
        vix_zone_end = col2.time_input("Zone End", value=time(6, 0))
        
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
            col1, col2 = st.columns(2)
            prior_highest_wick = col1.number_input("Highest Wick (ES)", value=6100.0, step=0.5, help="Highest high of any RTH candle")
            prior_lowest_close = col2.number_input("Lowest Close (ES)", value=6050.0, step=0.5, help="Lowest close of any RTH candle")
            
            col3, col4 = st.columns(2)
            prior_hw_hour = col3.selectbox("HW Time (Hour)", options=list(range(8, 16)), index=4, help="Hour when highest wick occurred")
            prior_lc_hour = col4.selectbox("LC Time (Hour)", options=list(range(8, 16)), index=4, help="Hour when lowest close occurred")
            
            prior_close = st.number_input("RTH Close (ES)", value=6075.0, step=0.5, help="Final RTH close")
        else:
            prior_highest_wick = None
            prior_lowest_close = None
            prior_hw_hour = 12
            prior_lc_hour = 12
            prior_close = None
        
        st.divider()
        
        # ─────────────────────────────────────────────────────────────────────
        # OVERNIGHT SESSION DATA
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("#### 🌙 Overnight Session (ES)")
        use_manual_overnight = st.checkbox("Manual ON Session Override", value=False)
        if use_manual_overnight:
            col1, col2 = st.columns(2)
            on_high = col1.number_input("ON High", value=6090.0, step=0.5)
            on_low = col2.number_input("ON Low", value=6055.0, step=0.5)
        else:
            on_high = None
            on_low = None
        
        st.divider()
        
        # ─────────────────────────────────────────────────────────────────────
        # GLOBAL SESSION OVERRIDES
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("#### 🌏 Session Breakdown (ES)")
        use_manual_sessions = st.checkbox("Manual Session Override", value=False)
        
        if use_manual_sessions:
            st.markdown("##### Sydney (5-8:30 PM CT)")
            col1, col2 = st.columns(2)
            sydney_high = col1.number_input("Syd High", value=6075.0, step=0.5, key="syd_h")
            sydney_low = col2.number_input("Syd Low", value=6060.0, step=0.5, key="syd_l")
            
            st.markdown("##### Tokyo (9 PM - 1:30 AM CT)")
            col1, col2 = st.columns(2)
            tokyo_high = col1.number_input("Tok High", value=6080.0, step=0.5, key="tok_h")
            tokyo_low = col2.number_input("Tok Low", value=6055.0, step=0.5, key="tok_l")
            
            st.markdown("##### London (2-5 AM CT)")
            col1, col2 = st.columns(2)
            london_high = col1.number_input("Lon High", value=6085.0, step=0.5, key="lon_h")
            london_low = col2.number_input("Lon Low", value=6050.0, step=0.5, key="lon_l")
        else:
            sydney_high = sydney_low = tokyo_high = tokyo_low = london_high = london_low = None
        
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
        "manual_prior": {"highest_wick": prior_highest_wick, "lowest_close": prior_lowest_close, "close": prior_close, "hw_hour": prior_hw_hour, "lc_hour": prior_lc_hour} if use_manual_prior else None,
        "manual_overnight": {"high": on_high, "low": on_low} if use_manual_overnight else None,
        "manual_sessions": {
            "sydney": {"high": sydney_high, "low": sydney_low},
            "tokyo": {"high": tokyo_high, "low": tokyo_low},
            "london": {"high": london_high, "low": london_low}
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
        
        # --- Session Data ---
        if inputs["manual_sessions"] is not None:
            m = inputs["manual_sessions"]
            overnight_day = get_prior_trading_day(actual_trading_date)
            sydney = {
                "high": m["sydney"]["high"], "low": m["sydney"]["low"],
                "high_time": CT.localize(datetime.combine(overnight_day, time(18, 0))),
                "low_time": CT.localize(datetime.combine(overnight_day, time(19, 0)))
            }
            tokyo = {
                "high": m["tokyo"]["high"], "low": m["tokyo"]["low"],
                "high_time": CT.localize(datetime.combine(overnight_day, time(23, 0))),
                "low_time": CT.localize(datetime.combine(actual_trading_date, time(0, 30)))
            }
            london = {
                "high": m["london"]["high"], "low": m["london"]["low"],
                "high_time": CT.localize(datetime.combine(actual_trading_date, time(3, 0))),
                "low_time": CT.localize(datetime.combine(actual_trading_date, time(4, 0)))
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
            hw_hour = inputs["manual_prior"].get("hw_hour", 12)
            lc_hour = inputs["manual_prior"].get("lc_hour", 12)
            prior_rth = {
                "highest_wick": inputs["manual_prior"]["highest_wick"],
                "highest_wick_time": CT.localize(datetime.combine(prior_day, time(hw_hour, 0))),
                "lowest_close": inputs["manual_prior"]["lowest_close"],
                "lowest_close_time": CT.localize(datetime.combine(prior_day, time(lc_hour, 0))),
                "high": inputs["manual_prior"]["highest_wick"],
                "low": inputs["manual_prior"]["lowest_close"],
                "close": inputs["manual_prior"]["close"],
                "available": True
            }
        else:
            prior_rth = fetch_prior_day_rth(actual_trading_date)
    
    offset = inputs["offset"]
    current_spx = round(current_es - offset, 2)
    channel_type, channel_reason, upper_pivot, lower_pivot, upper_time, lower_time = determine_channel(sydney, tokyo, london)
    
    # Reference time uses actual trading day
    ref_time_dt = CT.localize(datetime.combine(actual_trading_date, time(*inputs["ref_time"])))
    ceiling_es, floor_es = calc_channel_levels(upper_pivot, lower_pivot, upper_time, lower_time, ref_time_dt, channel_type)
    
    if ceiling_es is None:
        ceiling_es, floor_es = 6080, 6040
    
    ceiling_spx = round(ceiling_es - offset, 2)
    floor_spx = round(floor_es - offset, 2)
    position = get_position(current_es, ceiling_es, floor_es)
    
    # ─────────────────────────────────────────────────────────────────────────
    # DUAL CHANNEL LEVELS (Option C - Always show BOTH ascending and descending)
    # ─────────────────────────────────────────────────────────────────────────
    dual_levels_es = calc_dual_channel_levels(upper_pivot, lower_pivot, upper_time, lower_time, ref_time_dt)
    
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
        }
    
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
    
    # OPTION C: Use the new dual-channel decision engine
    decision = analyze_market_state_v2(
        current_spx, dual_levels_spx, channel_type, channel_reason,
        retail_data["bias"], ema_data["ema_bias"], vix_pos, vix,
        session_tests, gap_analysis, prior_close_validation, vix_term
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HERO BANNER
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="hero-banner">
        <div class="prophet-logo">
            <div class="logo-pyramid">
                <div class="pyramid-body"></div>
                <div class="pyramid-inner"></div>
                <div class="eye-container">
                    <div class="eye-rays"></div>
                    <div class="eye-outer"></div>
                    <div class="eye-iris"><div class="eye-pupil"></div></div>
                </div>
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
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:rgba(255,255,255,0.5);">
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
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:rgba(255,255,255,0.5);">
                ⏰ {now.strftime("%I:%M %p CT")}
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MARKET SNAPSHOT
    # ═══════════════════════════════════════════════════════════════════════════
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">SPX Index</div><div class="metric-value accent">{current_spx:,.2f}</div><div class="metric-delta">ES {current_es:,.2f}</div></div>', unsafe_allow_html=True)
    with col2:
        vix_color = "puts" if vix > 20 else "calls" if vix < 15 else ""
        st.markdown(f'<div class="metric-card"><div class="metric-label">VIX Index</div><div class="metric-value {vix_color}">{vix:.2f}</div><div class="metric-delta">Volatility</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Position</div><div class="metric-value">{position.value}</div><div class="metric-delta">In Channel</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Time</div><div class="metric-value">{now.strftime("%I:%M")}</div><div class="metric-delta live-indicator"><span class="live-dot"></span> {now.strftime("%p CT")}</div></div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TODAY'S BIAS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header"><div class="section-icon">◎</div><h2 class="section-title">Today\'s Bias</h2></div>', unsafe_allow_html=True)
    
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
    
    # Retail positioning alert
    if retail_data["positioning"] != "BALANCED":
        alert_class = "warning" if "HEAVY" in retail_data["positioning"] else "danger"
        alert_icon = "⚡" if "EXTREME" in retail_data["positioning"] else "⚠"
        st.markdown(f'<div class="alert-box alert-box-{alert_class}"><span class="alert-icon">{alert_icon}</span><div class="alert-content"><div class="alert-title">{retail_data["positioning"]}</div><div class="alert-text">{retail_data["warning"]}</div></div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-box alert-box-success"><span class="alert-icon">✓</span><div class="alert-content"><div class="alert-title">BALANCED POSITIONING</div><div class="alert-text">No crowd pressure detected - trade freely with structure</div></div></div>', unsafe_allow_html=True)
    
    # VIX Position
    if vix_range["available"]:
        vix_icon = {"ABOVE": "▲", "IN RANGE": "◆", "BELOW": "▼"}.get(vix_pos.value, "○")
        st.markdown(f'<div class="alert-box alert-box-info"><span class="alert-icon">{vix_icon}</span><div class="alert-content"><div class="alert-title">VIX {vix_pos.value}</div><div class="alert-text">Overnight range: {vix_range["bottom"]} - {vix_range["top"]} | Current: {vix}</div></div></div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONFLUENCE
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header"><div class="section-icon">⚖</div><h2 class="section-title">Confluence Analysis</h2></div>', unsafe_allow_html=True)
    
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
    st.markdown(f'<div class="section-header"><div class="section-icon">◫</div><h2 class="section-title">Dual Channel Levels @ {inputs["ref_time"][0]}:{inputs["ref_time"][1]:02d} AM</h2></div>', unsafe_allow_html=True)
    
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
        st.markdown(f'<div class="levels-container"><div style="padding:14px 16px;background:linear-gradient(90deg,var(--bg-elevated) 0%,transparent 100%);border-radius:10px;margin-bottom:16px;border-left:4px solid var(--accent-cyan);"><span style="font-family:JetBrains Mono,monospace;font-size:0.9rem;color:var(--text-primary);">{pos_summary}</span></div></div>', unsafe_allow_html=True)
        
        # Ascending Channel Header
        asc_label = "↗ ASCENDING CHANNEL (DOMINANT)" if is_ascending else "↗ ASCENDING CHANNEL"
        st.markdown(f'<div style="font-size:0.8rem;color:var(--bull);text-transform:uppercase;letter-spacing:1px;margin:16px 0 8px 0;font-weight:600;">{asc_label}</div>', unsafe_allow_html=True)
        
        # Ascending Floor Row
        if is_ascending:
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
        
        # Descending Ceiling Row
        if is_descending:
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
    # PRIOR DAY INTERMEDIATE LEVELS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header"><div class="section-icon">◎</div><h2 class="section-title">Prior Day Intermediate Levels</h2></div>', unsafe_allow_html=True)
    
    if prior_targets["available"] and prior_targets["highest_wick"] is not None and prior_targets["lowest_close"] is not None:
        # Convert ES targets to SPX
        hw_anchor_spx = round(prior_targets["highest_wick"] - offset, 2)
        lc_anchor_spx = round(prior_targets["lowest_close"] - offset, 2)
        hw_asc = round(prior_targets["highest_wick_ascending"] - offset, 2) if prior_targets["highest_wick_ascending"] else None
        hw_desc = round(prior_targets["highest_wick_descending"] - offset, 2) if prior_targets["highest_wick_descending"] else None
        lc_asc = round(prior_targets["lowest_close_ascending"] - offset, 2) if prior_targets["lowest_close_ascending"] else None
        lc_desc = round(prior_targets["lowest_close_descending"] - offset, 2) if prior_targets["lowest_close_descending"] else None
        
        # Only display if all values are available
        if all([hw_asc, hw_desc, lc_asc, lc_desc]):
            st.markdown(f'''
            <div class="prior-levels-container">
                <div class="prior-levels-section">
                    <div class="prior-levels-header">
                        <span class="prior-levels-icon">📍</span>
                        <span class="prior-levels-title">From Highest Wick</span>
                        <span class="prior-levels-anchor">{hw_anchor_spx:,.2f}</span>
                    </div>
                    <div class="prior-levels-grid">
                        <div class="prior-level-item prior-level-sell">
                            <div class="prior-level-direction">↗ Ascending</div>
                            <div class="prior-level-value">{hw_asc:,.2f}</div>
                            <div class="prior-level-action">SELL (Resistance)</div>
                        </div>
                        <div class="prior-level-item prior-level-buy">
                            <div class="prior-level-direction">↘ Descending</div>
                            <div class="prior-level-value">{hw_desc:,.2f}</div>
                            <div class="prior-level-action">BUY (Support)</div>
                        </div>
                    </div>
                    <div class="prior-levels-note">Use when price opened ABOVE prior day high</div>
                </div>
                <div class="prior-levels-section">
                    <div class="prior-levels-header">
                        <span class="prior-levels-icon">📍</span>
                        <span class="prior-levels-title">From Lowest Close</span>
                        <span class="prior-levels-anchor">{lc_anchor_spx:,.2f}</span>
                    </div>
                    <div class="prior-levels-grid">
                        <div class="prior-level-item prior-level-buy">
                            <div class="prior-level-direction">↗ Ascending</div>
                            <div class="prior-level-value">{lc_asc:,.2f}</div>
                            <div class="prior-level-action">BUY (Support)</div>
                        </div>
                        <div class="prior-level-item prior-level-sell">
                            <div class="prior-level-direction">↘ Descending</div>
                            <div class="prior-level-value">{lc_desc:,.2f}</div>
                            <div class="prior-level-action">SELL (Resistance)</div>
                        </div>
                    </div>
                    <div class="prior-levels-note">Use when price opened BELOW prior day low</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('''
            <div class="alert-box" style="background: rgba(255,215,0,0.1); border: 1px solid rgba(255,215,0,0.3);">
                <span style="font-size:1.2rem;">⚠️</span>
                <div>
                    <div style="font-weight:600;color:var(--accent-gold);margin-bottom:4px;">Prior Day Data Incomplete</div>
                    <div style="font-size:0.85rem;color:var(--text-secondary);">Some values missing - use Manual Override in sidebar</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
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
    if decision["no_trade"]:
        st.markdown('<div class="section-header"><div class="section-icon">◉</div><h2 class="section-title">Trade Setup</h2></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="no-trade-card"><div class="no-trade-icon">⊘</div><div class="no-trade-title">NO TRADE</div><div class="no-trade-reason">{decision["no_trade_reason"]}</div></div>', unsafe_allow_html=True)
    else:
        # PRIMARY TRADE
        st.markdown('<div class="section-header"><div class="section-icon">◉</div><h2 class="section-title">PRIMARY Trade Setup</h2></div>', unsafe_allow_html=True)
        
        p = decision["primary"]
        if p:
            tc = "calls" if p["direction"] == "CALLS" else "puts"
            di = "↗" if p["direction"] == "CALLS" else "↘"
            t = p["targets"]
            st.markdown(f'''
            <div class="trade-card trade-card-{tc}">
                <div class="trade-header">
                    <div class="trade-name">{di} {p["name"]}</div>
                    <div class="trade-confidence trade-confidence-{p["confidence"].lower()}">{p["confidence"]} CONFIDENCE</div>
                </div>
                <div class="trade-contract trade-contract-{tc}">{p["contract"]}</div>
                <div class="trade-grid">
                    <div class="trade-metric"><div class="trade-metric-label">Entry Premium</div><div class="trade-metric-value">${p["entry_premium"]:.2f}</div></div>
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
        
        # SECONDARY TRADE
        if decision["secondary"]:
            st.markdown('<div class="section-header"><div class="section-icon">◌</div><h2 class="section-title">SECONDARY Trade Setup</h2></div>', unsafe_allow_html=True)
            s = decision["secondary"]
            tc = "calls" if s["direction"] == "CALLS" else "puts"
            di = "↗" if s["direction"] == "CALLS" else "↘"
            t = s["targets"]
            st.markdown(f'''
            <div class="trade-card trade-card-{tc}" style="opacity: 0.85;">
                <div class="trade-header">
                    <div class="trade-name">{di} {s["name"]}</div>
                    <div class="trade-confidence trade-confidence-{s["confidence"].lower()}">{s["confidence"]} CONFIDENCE</div>
                </div>
                <div class="trade-contract trade-contract-{tc}">{s["contract"]}</div>
                <div class="trade-grid">
                    <div class="trade-metric"><div class="trade-metric-label">Entry Premium</div><div class="trade-metric-value">${s["entry_premium"]:.2f}</div></div>
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
    st.markdown('<div class="section-header"><div class="section-icon">◐</div><h2 class="section-title">Global Sessions</h2></div>', unsafe_allow_html=True)
    
    session_data = [("🦘", "Sydney", sydney), ("🗼", "Tokyo", tokyo), ("🏛", "London", london), ("🌙", "Overnight", overnight)]
    cols = st.columns(4)
    for i, (icon, name, data) in enumerate(session_data):
        with cols[i]:
            if data:
                h_mark = " ⬆" if upper_pivot and upper_pivot == data.get("high") else ""
                l_mark = " ⬇" if lower_pivot and lower_pivot == data.get("low") else ""
                st.markdown(f'<div class="session-card"><div class="session-icon">{icon}</div><div class="session-name">{name}</div><div class="session-data"><div class="session-value"><span style="color:var(--text-tertiary);">H</span><span class="session-high">{data["high"]:,.2f}{h_mark}</span></div><div class="session-value"><span style="color:var(--text-tertiary);">L</span><span class="session-low">{data["low"]:,.2f}{l_mark}</span></div></div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="session-card" style="opacity:0.5;"><div class="session-icon">{icon}</div><div class="session-name">{name}</div><div class="session-data"><div style="color:var(--text-muted);font-size:0.85rem;">No data</div></div></div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INDICATORS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header"><div class="section-icon">◧</div><h2 class="section-title">Technical Indicators</h2></div>', unsafe_allow_html=True)
    
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
    st.markdown('<div style="margin-top:40px;padding:20px 0;border-top:1px solid var(--border-subtle);text-align:center;"><p style="font-family:\'JetBrains Mono\',monospace;font-size:0.75rem;color:var(--text-muted);letter-spacing:2px;">SPX PROPHET • STRUCTURAL 0DTE TRADING SYSTEM</p></div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()

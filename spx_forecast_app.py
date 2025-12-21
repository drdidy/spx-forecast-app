"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           SPX PROPHET v5.0                                    ║
║                    The Complete 0DTE Trading System                           ║
║                       NOW WITH POLYGON.IO INTEGRATION                         ║
║                                                                               ║
║  NEW FEATURES:                                                                ║
║  • Auto VIX Zone Detection (5pm-6am overnight range)                         ║
║  • Auto Prior Day Pivot Detection with exact times                           ║
║  • Live/Delayed SPX & VIX prices from Polygon                                ║
║  • 30-Minute Candle Close Verification                                        ║
║  • Real-time Rail Proximity Alerts                                            ║
║  • Manual Override preserved for all inputs                                   ║
║                                                                               ║
║  POLYGON PLAN MODES:                                                          ║
║  • Basic (Free): 15-min delayed data - still auto-detects zones/pivots       ║
║  • Starter+: Real-time data with instant updates                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, time
import pytz
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
import streamlit.components.v1 as components

# ============================================================================
# POLYGON.IO CONFIGURATION
# ============================================================================

POLYGON_API_KEY = "DCWuTS1R_fukpfjgf7QnXrLTEOS_giq6"  # Your API Key
POLYGON_BASE_URL = "https://api.polygon.io"

# Ticker symbols for Polygon (indices use I: prefix)
POLYGON_SPX = "I:SPX"
POLYGON_VIX = "I:VIX"

# Polygon access flags - set based on your subscription
# Indices requires paid plan ($49/mo Starter), Stocks is free
POLYGON_HAS_INDICES = True   # ENABLED - David has Indices Starter!
POLYGON_HAS_STOCKS = True    # Free tier works for stocks

# ============================================================================
# CONFIGURATION - All times in CT (Chicago Time)
# ============================================================================

CT_TZ = pytz.timezone('America/Chicago')
ET_TZ = pytz.timezone('America/New_York')

# VIX Zone Constants
VIX_ZONE_ESTABLISHMENT_START = time(17, 0)   # 5:00 PM CT
VIX_ZONE_ESTABLISHMENT_END = time(6, 0)       # 6:00 AM CT (next day)
VIX_RELIABLE_BREAKOUT_START = time(6, 0)      # 6:00 AM CT
VIX_RELIABLE_BREAKOUT_END = time(6, 30)       # 6:30 AM CT
VIX_DANGER_ZONE_START = time(6, 30)           # 6:30 AM CT
VIX_DANGER_ZONE_END = time(9, 30)             # 9:30 AM CT

# VIX Zone Size → Expected SPX Move (based on empirical data)
VIX_TO_SPX_MOVE = {
    0.10: (35, 40),
    0.15: (40, 45),
    0.20: (45, 50),
    0.25: (50, 55),
    0.30: (55, 60),
}

# Cone Constants
SLOPE_PER_30MIN = 0.45  # Points per 30-min block
MIN_CONE_WIDTH = 18.0   # Minimum tradeable width
CONFLUENCE_THRESHOLD = 5.0

# Trade Constants
STOP_LOSS_PTS = 6.0
STRIKE_OTM_DISTANCE = 17.5
DELTA = 0.33
CONTRACT_MULTIPLIER = 100

# Choppy Day Thresholds
LOW_VIX_THRESHOLD = 13.0
NARROW_CONE_THRESHOLD = 25.0

def get_ct_now() -> datetime:
    return datetime.now(CT_TZ)

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Pivot:
    price: float
    time: datetime
    name: str
    is_secondary: bool = False
    price_for_ascending: float = 0.0
    price_for_descending: float = 0.0
    
    def __post_init__(self):
        if self.price_for_ascending == 0.0:
            self.price_for_ascending = self.price
        if self.price_for_descending == 0.0:
            self.price_for_descending = self.price

@dataclass
class Cone:
    name: str
    pivot: Pivot
    ascending_rail: float
    descending_rail: float
    width: float
    blocks: int

@dataclass
class VIXZone:
    bottom: float
    top: float
    current: float
    position_pct: float
    status: str
    bias: str
    breakout_time: str
    zones_above: List[float]
    zones_below: List[float]
    zone_size: float = 0.15
    expected_move: tuple = (40, 45)
    auto_detected: bool = False  # NEW: Flag if zone was auto-detected

@dataclass
class TradeSetup:
    direction: str
    cone_name: str
    cone_width: float
    entry: float
    stop: float
    target_12: float
    target_25: float
    target_50: float
    strike: int
    spx_pts_12: float
    spx_pts_25: float
    spx_pts_50: float
    profit_12: float
    profit_25: float
    profit_50: float
    risk_per_contract: float
    rr_ratio: float
    distance: float
    is_active: bool = False

@dataclass
class DayAssessment:
    tradeable: bool
    score: int
    reasons: List[str]
    warnings: List[str]
    recommendation: str

@dataclass
class PolygonStatus:
    """Track Polygon API status and data freshness"""
    connected: bool = False
    last_update: Optional[datetime] = None
    data_delay: str = "Unknown"
    spx_price: float = 0.0
    vix_price: float = 0.0
    error_message: str = ""

# ============================================================================
# POLYGON.IO API FUNCTIONS
# ============================================================================

@st.cache_data(ttl=60)
def polygon_get_previous_close(ticker: str) -> Optional[Dict]:
    """
    Get previous day's OHLC data from Polygon.
    Works with Basic (free) plan - returns previous trading day data.
    """
    try:
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{ticker}/prev"
        params = {"apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results") and len(data["results"]) > 0:
                result = data["results"][0]
                return {
                    "open": result.get("o", 0),
                    "high": result.get("h", 0),
                    "low": result.get("l", 0),
                    "close": result.get("c", 0),
                    "volume": result.get("v", 0),
                    "timestamp": result.get("t", 0),
                    "vwap": result.get("vw", 0)
                }
        return None
    except Exception as e:
        st.session_state.polygon_error = str(e)
        return None

@st.cache_data(ttl=300)
def polygon_get_intraday_bars(ticker: str, date_str: str, timespan: str = "30", multiplier: int = 1) -> Optional[pd.DataFrame]:
    """
    Get intraday bars from Polygon.
    
    Args:
        ticker: Polygon ticker (e.g., "I:SPX" or "I:VIX")
        date_str: Date in YYYY-MM-DD format
        timespan: "minute", "hour", etc.
        multiplier: Bar size multiplier (30 for 30-minute bars)
    
    Returns:
        DataFrame with OHLCV data and timestamps in CT
    """
    try:
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{ticker}/range/{multiplier}/minute/{date_str}/{date_str}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "apiKey": POLYGON_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                df = pd.DataFrame(data["results"])
                # Convert timestamp (ms) to datetime
                df['datetime'] = pd.to_datetime(df['t'], unit='ms', utc=True)
                df['datetime'] = df['datetime'].dt.tz_convert(CT_TZ)
                df = df.rename(columns={
                    'o': 'Open',
                    'h': 'High',
                    'l': 'Low',
                    'c': 'Close',
                    'v': 'Volume',
                    'vw': 'VWAP'
                })
                df = df.set_index('datetime')
                return df
        return None
    except Exception as e:
        st.session_state.polygon_error = str(e)
        return None

@st.cache_data(ttl=60)  # Reduced cache time
def polygon_get_overnight_vix_range(session_date: datetime) -> Optional[Dict]:
    """
    AUTO-DETECT VIX ZONE: Get VIX high/low from 2am CT to 6am CT session day.
    
    Note: VIX index data from Polygon starts around 2:15am CT (pre-market).
    This captures the early morning VIX range before RTH opens.
    
    Returns:
        Dict with 'bottom', 'top', 'zone_size', and bar data
    """
    try:
        # Calculate date range for early morning window
        # 2am CT to 6am CT on session day
        session_date_str = session_date.strftime("%Y-%m-%d")
        
        # Get 1-minute VIX bars for the session day
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{POLYGON_VIX}/range/1/minute/{session_date_str}/{session_date_str}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000,
            "apiKey": POLYGON_API_KEY
        }
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                df = pd.DataFrame(data["results"])
                df['datetime'] = pd.to_datetime(df['t'], unit='ms', utc=True)
                df['datetime'] = df['datetime'].dt.tz_convert(CT_TZ)
                
                # Filter to early morning window: 2am CT to 6am CT
                zone_start = CT_TZ.localize(datetime.combine(session_date.date(), time(2, 0)))
                zone_end = CT_TZ.localize(datetime.combine(session_date.date(), time(6, 0)))
                
                mask = (df['datetime'] >= zone_start) & (df['datetime'] <= zone_end)
                zone_df = df[mask]
                
                # Store debug info about what data we actually got
                actual_start = df['datetime'].min()
                actual_end = df['datetime'].max()
                
                if not zone_df.empty:
                    vix_high = float(zone_df['h'].max())
                    vix_low = float(zone_df['l'].min())
                    zone_size = round(vix_high - vix_low, 2)
                    
                    # Get the actual filtered time range
                    filtered_start = zone_df['datetime'].min()
                    filtered_end = zone_df['datetime'].max()
                    
                    return {
                        'bottom': round(vix_low, 2),
                        'top': round(vix_high, 2),
                        'zone_size': zone_size,
                        'bar_count': len(zone_df),
                        'start_time': filtered_start,
                        'end_time': filtered_end,
                        # Debug info
                        'requested_start': zone_start.strftime('%Y-%m-%d %H:%M CT'),
                        'requested_end': zone_end.strftime('%Y-%m-%d %H:%M CT'),
                        'filtered_data_start': filtered_start.strftime('%Y-%m-%d %H:%M CT'),
                        'filtered_data_end': filtered_end.strftime('%Y-%m-%d %H:%M CT'),
                        'actual_data_start': actual_start.strftime('%Y-%m-%d %H:%M CT'),
                        'actual_data_end': actual_end.strftime('%Y-%m-%d %H:%M CT'),
                        'total_bars_fetched': len(df),
                        'overnight_bars_found': len(zone_df),
                        'session_date': session_date_str
                    }
                else:
                    # No data found in window - return debug info about what we got
                    return {
                        'bottom': 0,
                        'top': 0,
                        'zone_size': 0,
                        'bar_count': 0,
                        'error': 'No data in 2am-6am window',
                        'requested_start': zone_start.strftime('%Y-%m-%d %H:%M CT'),
                        'requested_end': zone_end.strftime('%Y-%m-%d %H:%M CT'),
                        'actual_data_start': actual_start.strftime('%Y-%m-%d %H:%M CT') if not df.empty else 'N/A',
                        'actual_data_end': actual_end.strftime('%Y-%m-%d %H:%M CT') if not df.empty else 'N/A',
                        'total_bars_fetched': len(df),
                        'overnight_bars_found': 0,
                        'session_date': session_date_str
                    }
        
        return None
    except Exception as e:
        st.session_state.polygon_error = f"VIX zone error: {str(e)}"
        return None

@st.cache_data(ttl=60)
def polygon_get_current_price(ticker: str) -> Optional[float]:
    """
    Get the most recent price for a ticker.
    With Basic plan, this is 15-min delayed.
    """
    try:
        # Use previous close endpoint for most recent data on Basic plan
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{ticker}/prev"
        params = {"apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results") and len(data["results"]) > 0:
                return data["results"][0].get("c", 0)
        return None
    except:
        return None

@st.cache_data(ttl=300)
def polygon_get_prior_session_pivots(session_date: datetime) -> Optional[Dict]:
    """
    AUTO-DETECT PIVOTS: Get prior session High, Low, Close with exact times.
    
    HIGH PIVOT:
    - Ascending rail uses: Highest PRICE (including wick)
    - Descending rail uses: Highest 30-min CLOSE
    
    LOW PIVOT:
    - Both rails use: Lowest 30-min CLOSE (no wicks)
    
    Returns complete pivot data with exact timestamps for accurate block counting.
    """
    try:
        # Determine prior trading day
        prior_day = session_date - timedelta(days=1)
        
        # Account for weekends
        if session_date.weekday() == 0:  # Monday
            prior_day = session_date - timedelta(days=3)  # Friday
        elif session_date.weekday() == 6:  # Sunday (shouldn't happen but just in case)
            prior_day = session_date - timedelta(days=2)  # Friday
        
        prior_date_str = prior_day.strftime("%Y-%m-%d")
        
        # Get 30-minute bars for the prior trading day
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{POLYGON_SPX}/range/30/minute/{prior_date_str}/{prior_date_str}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "apiKey": POLYGON_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                df = pd.DataFrame(data["results"])
                df['datetime'] = pd.to_datetime(df['t'], unit='ms', utc=True)
                df['datetime'] = df['datetime'].dt.tz_convert(CT_TZ)
                
                # Filter to RTH (8:30 AM - 3:00 PM CT)
                rth_start = time(8, 30)
                rth_end = time(15, 0)
                df = df[(df['datetime'].dt.time >= rth_start) & (df['datetime'].dt.time <= rth_end)]
                
                if df.empty:
                    return None
                
                # HIGH PIVOT
                # - Time of highest HIGH (wick included) for ascending rail
                high_idx = df['h'].idxmax()
                high_row = df.loc[high_idx]
                high_price = float(high_row['h'])  # Highest price (with wick)
                high_time = high_row['datetime']
                
                # - Highest CLOSE for descending rail
                high_close = float(df['c'].max())
                
                # LOW PIVOT
                # - Both rails use lowest CLOSE (no wicks)
                low_close_idx = df['c'].idxmin()
                low_row = df.loc[low_close_idx]
                low_close = float(low_row['c'])
                low_time = low_row['datetime']
                
                # CLOSE
                close_price = float(df.iloc[-1]['c'])
                close_time = df.iloc[-1]['datetime']
                
                return {
                    'high': high_price,
                    'high_close': high_close,
                    'high_time': high_time,
                    'low': low_close,  # Using close, not low wick
                    'low_close': low_close,
                    'low_time': low_time,
                    'close': close_price,
                    'close_time': close_time,
                    'date': prior_day,
                    'bar_count': len(df),
                    'source': 'polygon'
                }
        
        return None
    except Exception as e:
        st.session_state.polygon_error = f"Prior session error: {str(e)}"
        return None

@st.cache_data(ttl=60)
def polygon_get_30min_vix_candles(session_date: datetime) -> Optional[pd.DataFrame]:
    """
    Get 30-minute VIX candles for the session day.
    Used to verify 30-min candle CLOSES at zone edge.
    """
    try:
        date_str = session_date.strftime("%Y-%m-%d")
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{POLYGON_VIX}/range/30/minute/{date_str}/{date_str}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "apiKey": POLYGON_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                df = pd.DataFrame(data["results"])
                df['datetime'] = pd.to_datetime(df['t'], unit='ms', utc=True)
                df['datetime'] = df['datetime'].dt.tz_convert(CT_TZ)
                df = df.rename(columns={
                    'o': 'Open',
                    'h': 'High',
                    'l': 'Low',
                    'c': 'Close',
                    'v': 'Volume'
                })
                df = df.set_index('datetime')
                return df
        return None
    except:
        return None

def check_polygon_connection() -> PolygonStatus:
    """
    Check if Polygon API is accessible and return status.
    Tests with VIX endpoint since we have Indices Starter.
    """
    status = PolygonStatus()
    try:
        # Test with VIX endpoint (we have Indices Starter now!)
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/I:VIX/prev"
        params = {"apiKey": POLYGON_API_KEY}
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            status.connected = True
            if POLYGON_HAS_INDICES:
                status.data_delay = "Real-time SPX/VIX (Indices Starter)"
            else:
                status.data_delay = "Using yfinance for SPX/VIX (Polygon Stocks OK)"
            status.last_update = get_ct_now()
            # Get VIX price
            if data.get("results"):
                status.vix_price = data["results"][0].get("c", 0)
        elif response.status_code == 401:
            status.error_message = "API Key invalid or expired"
        elif response.status_code == 403:
            status.error_message = "Not authorized - check subscription"
        else:
            status.error_message = f"API returned status {response.status_code}"
            
    except requests.exceptions.Timeout:
        status.error_message = "Connection timeout"
    except Exception as e:
        status.error_message = str(e)
    
    return status

# ============================================================================
# VIX ZONE ANALYSIS
# ============================================================================

def analyze_vix(bottom: float, top: float, current: float, auto_detected: bool = False) -> VIXZone:
    """
    Analyze VIX position and determine bias.
    Now includes auto_detected flag to show if zone was from Polygon.
    """
    zone_size = round(top - bottom, 2) if (top > 0 and bottom > 0 and top > bottom) else 0.15
    
    # Determine expected SPX move based on zone size
    if zone_size <= 0.10:
        expected_move = (35, 40)
    elif zone_size <= 0.15:
        expected_move = (40, 45)
    elif zone_size <= 0.20:
        expected_move = (45, 50)
    elif zone_size <= 0.25:
        expected_move = (50, 55)
    else:
        expected_move = (55, 60)
    
    zones_above = [round(top + (i * zone_size), 2) for i in range(1, 5)]
    zones_below = [round(bottom - (i * zone_size), 2) for i in range(1, 5)]
    
    if bottom <= 0 or top <= 0:
        return VIXZone(
            bottom=0, top=0, current=current,
            position_pct=0, status='NO_DATA', bias='UNKNOWN',
            breakout_time='NONE', zones_above=zones_above, zones_below=zones_below,
            zone_size=zone_size, expected_move=expected_move, auto_detected=auto_detected
        )
    
    if current <= 0:
        return VIXZone(
            bottom=bottom, top=top, current=0,
            position_pct=0, status='WAITING', bias='UNKNOWN',
            breakout_time='NONE', zones_above=zones_above, zones_below=zones_below,
            zone_size=zone_size, expected_move=expected_move, auto_detected=auto_detected
        )
    
    if zone_size > 0:
        position_pct = ((current - bottom) / zone_size) * 100
    else:
        position_pct = 50
    
    ct_now = get_ct_now()
    current_time = ct_now.time()
    
    if time(6, 0) <= current_time < time(6, 30):
        breakout_time = 'RELIABLE'
    elif time(6, 30) <= current_time < time(9, 30):
        breakout_time = 'DANGER'
    else:
        breakout_time = 'RTH'
    
    if current > top:
        status = 'BREAKOUT_UP'
        bias = 'PUTS'
        position_pct = 100 + ((current - top) / zone_size * 50) if zone_size > 0 else 100
    elif current < bottom:
        status = 'BREAKOUT_DOWN'
        bias = 'CALLS'
        position_pct = -((bottom - current) / zone_size * 50) if zone_size > 0 else 0
    else:
        status = 'CONTAINED'
        if position_pct >= 75:
            bias = 'CALLS'
        elif position_pct <= 25:
            bias = 'PUTS'
        else:
            bias = 'WAIT'
    
    return VIXZone(
        bottom=bottom, top=top, current=current,
        position_pct=position_pct, status=status, bias=bias,
        breakout_time=breakout_time, zones_above=zones_above, zones_below=zones_below,
        zone_size=zone_size, expected_move=expected_move, auto_detected=auto_detected
    )

# ============================================================================
# 30-MINUTE CANDLE CLOSE VERIFICATION (NEW!)
# ============================================================================

def verify_vix_candle_close(vix_zone: VIXZone, session_date: datetime) -> Dict:
    """
    NEW FEATURE: Verify if VIX has CLOSED (not just wicked) at zone edge.
    
    This is critical for the trading system - wicks don't count, only closes!
    
    Returns:
        Dict with verification status and details
    """
    result = {
        'verified': False,
        'last_candle_close': None,
        'last_candle_time': None,
        'closed_at_edge': False,
        'edge_type': None,  # 'top' or 'bottom'
        'message': "Waiting for candle data..."
    }
    
    # Get 30-min VIX candles
    candles = polygon_get_30min_vix_candles(session_date)
    
    if candles is None or candles.empty:
        result['message'] = "No candle data available"
        return result
    
    # Get the last completed candle
    last_candle = candles.iloc[-1]
    result['last_candle_close'] = float(last_candle['Close'])
    result['last_candle_time'] = candles.index[-1].strftime('%H:%M')
    
    # Check if last candle CLOSED at zone edge
    close_price = result['last_candle_close']
    
    # Within 0.02 of zone edge counts as "at edge"
    tolerance = 0.02
    
    if abs(close_price - vix_zone.top) <= tolerance or close_price > vix_zone.top:
        result['closed_at_edge'] = True
        result['edge_type'] = 'top'
        result['verified'] = True
        result['message'] = f"✅ VIX CLOSED at TOP ({close_price:.2f}) → PUTS confirmed"
    elif abs(close_price - vix_zone.bottom) <= tolerance or close_price < vix_zone.bottom:
        result['closed_at_edge'] = True
        result['edge_type'] = 'bottom'
        result['verified'] = True
        result['message'] = f"✅ VIX CLOSED at BOTTOM ({close_price:.2f}) → CALLS confirmed"
    else:
        result['message'] = f"VIX closed at {close_price:.2f} (mid-zone) - waiting for edge close"
    
    return result

# ============================================================================
# CONE CALCULATIONS
# ============================================================================

def count_blocks_v2(pivot_time: datetime, eval_time: datetime) -> int:
    """Count 30-minute blocks between pivot and evaluation time, handling weekends."""
    if eval_time <= pivot_time:
        return 1
    
    pivot_dow = pivot_time.weekday()
    eval_dow = eval_time.weekday()
    
    if pivot_time.date() == eval_time.date():
        diff = (eval_time - pivot_time).total_seconds()
        return max(int(diff // 1800), 1)
    
    spans_weekend = False
    
    if pivot_dow <= 4:
        days_diff = (eval_time.date() - pivot_time.date()).days
        if days_diff >= 2:
            temp = pivot_time
            while temp.date() < eval_time.date():
                if temp.weekday() == 4:
                    spans_weekend = True
                    break
                temp = temp + timedelta(days=1)
    
    if spans_weekend:
        friday = pivot_time
        while friday.weekday() != 4:
            friday = friday + timedelta(days=1)
        
        friday_close = friday.replace(hour=16, minute=0, second=0, microsecond=0)
        if friday_close.tzinfo is None:
            friday_close = CT_TZ.localize(friday_close)
        
        sunday_open = friday + timedelta(days=2)
        sunday_open = sunday_open.replace(hour=17, minute=0, second=0, microsecond=0)
        if sunday_open.tzinfo is None:
            sunday_open = CT_TZ.localize(sunday_open)
        
        total_blocks = 0
        
        if pivot_time < friday_close:
            blocks_to_friday = (friday_close - pivot_time).total_seconds() // 1800
            total_blocks += int(blocks_to_friday)
        
        if eval_time > sunday_open:
            blocks_from_sunday = (eval_time - sunday_open).total_seconds() // 1800
            total_blocks += int(blocks_from_sunday)
        
        return max(total_blocks, 1)
    
    else:
        diff = (eval_time - pivot_time).total_seconds()
        return max(int(diff // 1800), 1)

def build_cones(pivots: List[Pivot], eval_time: datetime) -> List[Cone]:
    """Build cones from pivots at evaluation time."""
    cones = []
    for pivot in pivots:
        start_time = pivot.time + timedelta(minutes=30)
        blocks = count_blocks_v2(start_time, eval_time)
        
        ascending = pivot.price_for_ascending + (blocks * SLOPE_PER_30MIN)
        descending = pivot.price_for_descending - (blocks * SLOPE_PER_30MIN)
        width = ascending - descending
        
        cones.append(Cone(
            name=pivot.name,
            pivot=pivot,
            ascending_rail=round(ascending, 2),
            descending_rail=round(descending, 2),
            width=round(width, 2),
            blocks=blocks
        ))
    return cones

def find_nearest(price: float, cones: List[Cone]) -> Tuple[Cone, str, float]:
    """Find nearest rail to current price."""
    nearest = None
    rail_type = ""
    min_dist = float('inf')
    
    for cone in cones:
        d_asc = abs(price - cone.ascending_rail)
        d_desc = abs(price - cone.descending_rail)
        
        if d_asc < min_dist:
            min_dist = d_asc
            nearest = cone
            rail_type = "ascending"
        if d_desc < min_dist:
            min_dist = d_desc
            nearest = cone
            rail_type = "descending"
    
    return nearest, rail_type, round(min_dist, 2)

def find_active_cone(price: float, cones: List[Cone]) -> Dict:
    """Determine which cone the current price is inside of, or nearest to."""
    result = {
        'inside_cone': None,
        'nearest_cone': None,
        'nearest_rail': None,
        'distance': 0,
        'position': 'unknown',
        'at_rail': False,
        'rail_type': None
    }
    
    if not cones:
        return result
    
    for cone in cones:
        if cone.descending_rail <= price <= cone.ascending_rail:
            result['inside_cone'] = cone
            result['position'] = 'inside'
            
            dist_to_asc = cone.ascending_rail - price
            dist_to_desc = price - cone.descending_rail
            
            if dist_to_asc <= 3:
                result['at_rail'] = True
                result['rail_type'] = 'ascending'
                result['distance'] = round(dist_to_asc, 2)
            elif dist_to_desc <= 3:
                result['at_rail'] = True
                result['rail_type'] = 'descending'
                result['distance'] = round(dist_to_desc, 2)
            else:
                result['distance'] = round(min(dist_to_asc, dist_to_desc), 2)
            
            return result
    
    nearest, rail_type, min_dist = find_nearest(price, cones)
    result['nearest_cone'] = nearest
    result['nearest_rail'] = rail_type
    result['distance'] = min_dist
    
    all_ascending = [c.ascending_rail for c in cones]
    all_descending = [c.descending_rail for c in cones]
    
    if price > max(all_ascending):
        result['position'] = 'above_all'
    elif price < min(all_descending):
        result['position'] = 'below_all'
    else:
        result['position'] = 'between_cones'
    
    return result

# ============================================================================
# TRADE SETUP GENERATION
# ============================================================================

def generate_setups(cones: List[Cone], current_price: float, vix_bias: str) -> List[TradeSetup]:
    """Generate trade setups with realistic targets and profit estimates."""
    setups = []
    
    for cone in cones:
        if cone.width < MIN_CONE_WIDTH:
            continue
        
        # CALLS SETUP
        entry_c = cone.descending_rail
        dist_c = abs(current_price - entry_c)
        
        spx_pts_12_c = cone.width * 0.125
        spx_pts_25_c = cone.width * 0.25
        spx_pts_50_c = cone.width * 0.50
        
        target_12_c = round(entry_c + spx_pts_12_c, 2)
        target_25_c = round(entry_c + spx_pts_25_c, 2)
        target_50_c = round(entry_c + spx_pts_50_c, 2)
        
        strike_c = int(entry_c + STRIKE_OTM_DISTANCE)
        strike_c = ((strike_c + 4) // 5) * 5
        
        profit_12_c = round(spx_pts_12_c * DELTA * CONTRACT_MULTIPLIER, 0)
        profit_25_c = round(spx_pts_25_c * DELTA * CONTRACT_MULTIPLIER, 0)
        profit_50_c = round(spx_pts_50_c * DELTA * CONTRACT_MULTIPLIER, 0)
        risk_c = round(STOP_LOSS_PTS * DELTA * CONTRACT_MULTIPLIER, 0)
        
        rr_c = round(profit_12_c / risk_c, 1) if risk_c > 0 else 0
        
        setups.append(TradeSetup(
            direction='CALLS',
            cone_name=cone.name,
            cone_width=cone.width,
            entry=entry_c,
            stop=round(entry_c - STOP_LOSS_PTS, 2),
            target_12=target_12_c,
            target_25=target_25_c,
            target_50=target_50_c,
            strike=strike_c,
            spx_pts_12=round(spx_pts_12_c, 1),
            spx_pts_25=round(spx_pts_25_c, 1),
            spx_pts_50=round(spx_pts_50_c, 1),
            profit_12=profit_12_c,
            profit_25=profit_25_c,
            profit_50=profit_50_c,
            risk_per_contract=risk_c,
            rr_ratio=rr_c,
            distance=round(dist_c, 2),
            is_active=(dist_c <= 5 and vix_bias == 'CALLS')
        ))
        
        # PUTS SETUP
        entry_p = cone.ascending_rail
        dist_p = abs(current_price - entry_p)
        
        spx_pts_12_p = cone.width * 0.125
        spx_pts_25_p = cone.width * 0.25
        spx_pts_50_p = cone.width * 0.50
        
        target_12_p = round(entry_p - spx_pts_12_p, 2)
        target_25_p = round(entry_p - spx_pts_25_p, 2)
        target_50_p = round(entry_p - spx_pts_50_p, 2)
        
        strike_p = int(entry_p - STRIKE_OTM_DISTANCE)
        strike_p = (strike_p // 5) * 5
        
        profit_12_p = round(spx_pts_12_p * DELTA * CONTRACT_MULTIPLIER, 0)
        profit_25_p = round(spx_pts_25_p * DELTA * CONTRACT_MULTIPLIER, 0)
        profit_50_p = round(spx_pts_50_p * DELTA * CONTRACT_MULTIPLIER, 0)
        risk_p = round(STOP_LOSS_PTS * DELTA * CONTRACT_MULTIPLIER, 0)
        
        rr_p = round(profit_12_p / risk_p, 1) if risk_p > 0 else 0
        
        setups.append(TradeSetup(
            direction='PUTS',
            cone_name=cone.name,
            cone_width=cone.width,
            entry=entry_p,
            stop=round(entry_p + STOP_LOSS_PTS, 2),
            target_12=target_12_p,
            target_25=target_25_p,
            target_50=target_50_p,
            strike=strike_p,
            spx_pts_12=round(spx_pts_12_p, 1),
            spx_pts_25=round(spx_pts_25_p, 1),
            spx_pts_50=round(spx_pts_50_p, 1),
            profit_12=profit_12_p,
            profit_25=profit_25_p,
            profit_50=profit_50_p,
            risk_per_contract=risk_p,
            rr_ratio=rr_p,
            distance=round(dist_p, 2),
            is_active=(dist_p <= 5 and vix_bias == 'PUTS')
        ))
    
    setups.sort(key=lambda s: s.distance)
    return setups

# ============================================================================
# DAY ASSESSMENT
# ============================================================================

def assess_day(vix: VIXZone, cones: List[Cone], current_price: float) -> DayAssessment:
    """Assess if today is tradeable or choppy."""
    score = 100
    reasons = []
    warnings = []
    
    if vix.bias == 'WAIT':
        score -= 40
        warnings.append("VIX mid-zone (40-60%) - no clear edge")
    elif vix.bias in ['CALLS', 'PUTS']:
        reasons.append(f"VIX at edge ({vix.position_pct:.0f}%) - clear {vix.bias} bias")
    
    if vix.status in ['BREAKOUT_UP', 'BREAKOUT_DOWN']:
        if vix.breakout_time == 'RELIABLE':
            reasons.append("VIX breakout in reliable window (6-6:30am CT)")
        elif vix.breakout_time == 'DANGER':
            score -= 25
            warnings.append("⚠️ VIX breakout in DANGER window (6:30-9:30am) - reversal risk!")
    
    if cones:
        max_width = max(c.width for c in cones)
        if max_width < NARROW_CONE_THRESHOLD:
            score -= 30
            warnings.append(f"Narrow cones (max {max_width:.0f} pts) - limited profit potential")
        else:
            reasons.append(f"Good cone width ({max_width:.0f} pts)")
    
    if vix.current > 0 and vix.current < LOW_VIX_THRESHOLD:
        score -= 15
        warnings.append(f"Low VIX ({vix.current:.2f}) - expect smaller moves")
    
    if score >= 70:
        tradeable = True
        recommendation = 'FULL'
    elif score >= 50:
        tradeable = True
        recommendation = 'REDUCED'
    else:
        tradeable = False
        recommendation = 'SKIP'
    
    return DayAssessment(
        tradeable=tradeable,
        score=max(0, score),
        reasons=reasons,
        warnings=warnings,
        recommendation=recommendation
    )

# ============================================================================
# YFINANCE FALLBACK (When Polygon fails)
# ============================================================================

import yfinance as yf

@st.cache_data(ttl=300)
def yf_fetch_overnight_vix_range(session_date: datetime) -> Optional[Dict]:
    """
    Fetch VIX overnight range (5pm-6am CT) using yfinance.
    This provides auto VIX zone detection without needing Polygon paid plan.
    """
    try:
        vix = yf.Ticker("^VIX")
        
        # Get prior day for overnight window
        prev_day = session_date - timedelta(days=1)
        if session_date.weekday() == 0:  # Monday
            prev_day = session_date - timedelta(days=3)  # Friday
        
        # Fetch 2 days of 1-minute data to capture overnight
        start = prev_day - timedelta(days=1)
        end = session_date + timedelta(days=1)
        
        df = vix.history(start=start, end=end, interval='1m')
        
        if df.empty:
            # Try with less granular data
            df = vix.history(start=start, end=end, interval='5m')
        
        if df.empty:
            return None
        
        df.index = df.index.tz_convert(CT_TZ)
        
        # Filter to overnight window: 5pm CT prev day to 6am CT session day
        overnight_start = CT_TZ.localize(datetime.combine(prev_day.date(), time(17, 0)))
        overnight_end = CT_TZ.localize(datetime.combine(session_date.date(), time(6, 0)))
        
        mask = (df.index >= overnight_start) & (df.index <= overnight_end)
        overnight_df = df[mask]
        
        if overnight_df.empty:
            # If no overnight data, use prior day's range as fallback
            prior_day_mask = df.index.date == prev_day.date()
            prior_df = df[prior_day_mask]
            if not prior_df.empty:
                vix_high = float(prior_df['High'].max())
                vix_low = float(prior_df['Low'].min())
                zone_size = round(vix_high - vix_low, 2)
                return {
                    'bottom': round(vix_low, 2),
                    'top': round(vix_high, 2),
                    'zone_size': zone_size,
                    'source': 'yfinance (prior day range)'
                }
            return None
        
        vix_high = float(overnight_df['High'].max())
        vix_low = float(overnight_df['Low'].min())
        zone_size = round(vix_high - vix_low, 2)
        
        return {
            'bottom': round(vix_low, 2),
            'top': round(vix_high, 2),
            'zone_size': zone_size,
            'bar_count': len(overnight_df),
            'source': 'yfinance'
        }
    except Exception as e:
        return None

@st.cache_data(ttl=60)
def yf_fetch_current_vix() -> float:
    """Fetch current VIX price using yfinance."""
    try:
        vix = yf.Ticker("^VIX")
        data = vix.history(period='1d', interval='1m')
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except:
        pass
    return 0.0

@st.cache_data(ttl=300)
def yf_fetch_prior_session(session_date: datetime) -> Optional[Dict]:
    """Fallback to yfinance if Polygon fails."""
    try:
        spx = yf.Ticker("^GSPC")
        end = session_date
        start = end - timedelta(days=10)
        
        df_daily = spx.history(start=start, end=end, interval='1d')
        if len(df_daily) < 1:
            return None
        
        last = df_daily.iloc[-1]
        prior_date = df_daily.index[-1]
        
        df_intra = spx.history(start=start, end=end, interval='30m')
        
        high_price = float(last['High'])
        high_close = float(last['High'])
        low_close = float(last['Low'])
        
        high_time = CT_TZ.localize(datetime.combine(prior_date.date(), time(12, 0)))
        low_time = CT_TZ.localize(datetime.combine(prior_date.date(), time(12, 0)))
        
        if not df_intra.empty:
            df_intra.index = df_intra.index.tz_convert(CT_TZ)
            day_data = df_intra[df_intra.index.date == prior_date.date()]
            
            if not day_data.empty:
                high_time = day_data['High'].idxmax()
                high_price = float(day_data['High'].max())
                high_close = float(day_data['Close'].max())
                
                low_close_idx = day_data['Close'].idxmin()
                low_time = low_close_idx
                low_close = float(day_data['Close'].min())
        
        return {
            'high': high_price,
            'high_close': high_close,
            'low': low_close,
            'low_close': low_close,
            'close': float(last['Close']),
            'date': prior_date,
            'high_time': high_time,
            'low_time': low_time,
            'source': 'yfinance'
        }
    except:
        return None

@st.cache_data(ttl=60)
def yf_fetch_current_spx() -> float:
    """Fallback to yfinance for current SPX."""
    try:
        spx = yf.Ticker("^GSPC")
        data = spx.history(period='1d', interval='1m')
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except:
        pass
    return 0.0

# ============================================================================
# RENDERING FUNCTIONS
# ============================================================================

def render_polygon_status_badge(status: PolygonStatus) -> str:
    """Render a status badge showing Polygon connection status."""
    if status.connected:
        bg = "#ecfdf5"
        border = "#10b981"
        color = "#059669"
        icon = "🟢"
        text = f"POLYGON CONNECTED • {status.data_delay}"
        subtext = f"SPX: {status.spx_price:,.2f}" if status.spx_price > 0 else ""
    else:
        bg = "#fef2f2"
        border = "#ef4444"
        color = "#dc2626"
        icon = "🔴"
        text = "POLYGON OFFLINE"
        subtext = status.error_message or "Using yfinance fallback"
    
    return f'''
    <div style="background:{bg};border:1px solid {border};border-radius:8px;padding:8px 12px;margin-bottom:15px;display:flex;align-items:center;gap:8px;">
        <span style="font-size:12px;">{icon}</span>
        <div>
            <div style="font-weight:600;font-size:12px;color:{color};">{text}</div>
            <div style="font-size:11px;color:#6b7280;">{subtext}</div>
        </div>
    </div>
    '''

def render_auto_detection_badge(vix_auto: bool, pivot_auto: bool, pivot_source: str = "") -> str:
    """Render badge showing what was auto-detected vs manual."""
    items = []
    
    if vix_auto:
        items.append('<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:4px;font-size:11px;">VIX Zone: AUTO</span>')
    else:
        items.append('<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:4px;font-size:11px;">VIX Zone: MANUAL</span>')
    
    if pivot_auto:
        source_text = f"({pivot_source})" if pivot_source else ""
        items.append(f'<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:4px;font-size:11px;">Pivots: AUTO {source_text}</span>')
    else:
        items.append('<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:4px;font-size:11px;">Pivots: MANUAL</span>')
    
    return f'''
    <div style="display:flex;gap:8px;margin-bottom:15px;flex-wrap:wrap;">
        {" ".join(items)}
    </div>
    '''

def render_candle_close_verification(verification: Dict) -> str:
    """Render the 30-min candle close verification status."""
    if verification.get('verified'):
        bg = "#ecfdf5"
        border = "#10b981"
        color = "#059669"
        icon = "✅"
    else:
        bg = "#fffbeb"
        border = "#f59e0b"
        color = "#d97706"
        icon = "⏳"
    
    message = verification.get('message', 'Checking...')
    last_time = verification.get('last_candle_time', '--:--')
    last_close = verification.get('last_candle_close', 0)
    
    return f'''
    <div style="background:{bg};border:1px solid {border};border-radius:8px;padding:12px;margin-bottom:15px;">
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:18px;">{icon}</span>
            <div>
                <div style="font-weight:600;font-size:13px;color:{color};">30-MIN CANDLE CLOSE CHECK</div>
                <div style="font-size:12px;color:#6b7280;">{message}</div>
                <div style="font-size:11px;color:#9ca3af;margin-top:4px;">Last candle: {last_time} CT | Close: {last_close:.2f}</div>
            </div>
        </div>
    </div>
    '''

def render_active_cone_banner(active_cone_info: Dict, spx: float) -> str:
    """Render the active cone status banner."""
    if not active_cone_info:
        return ''
    
    inside = active_cone_info.get('inside_cone')
    nearest = active_cone_info.get('nearest_cone')
    at_rail = active_cone_info.get('at_rail', False)
    rail_type = active_cone_info.get('rail_type')
    distance = active_cone_info.get('distance', 0)
    position = active_cone_info.get('position', 'unknown')
    
    if inside:
        cone_name = inside.name
        if at_rail:
            if rail_type == 'ascending':
                icon = '🎯'
                color = '#dc2626'
                bg = '#fef2f2'
                border = '#ef4444'
                text = f"AT {cone_name} ASCENDING RAIL (PUTS entry zone)"
                subtext = f"SPX {spx:,.2f} is {distance:.1f} pts from rail at {inside.ascending_rail:.2f}"
            else:
                icon = '🎯'
                color = '#059669'
                bg = '#ecfdf5'
                border = '#10b981'
                text = f"AT {cone_name} DESCENDING RAIL (CALLS entry zone)"
                subtext = f"SPX {spx:,.2f} is {distance:.1f} pts from rail at {inside.descending_rail:.2f}"
        else:
            icon = '📍'
            color = '#6b7280'
            bg = '#f9fafb'
            border = '#d1d5db'
            text = f"INSIDE {cone_name} CONE"
            subtext = f"SPX {spx:,.2f} — Rails: ▲{inside.ascending_rail:.2f} / ▼{inside.descending_rail:.2f}"
    elif nearest:
        cone_name = nearest.name
        nearest_rail = active_cone_info.get('nearest_rail')
        
        if position == 'above_all':
            icon = '⬆️'
            text = f"ABOVE ALL CONES — Nearest: {cone_name} ascending"
        elif position == 'below_all':
            icon = '⬇️'
            text = f"BELOW ALL CONES — Nearest: {cone_name} descending"
        else:
            icon = '↔️'
            text = f"BETWEEN CONES — Nearest: {cone_name} {nearest_rail}"
        
        color = '#d97706'
        bg = '#fffbeb'
        border = '#f59e0b'
        
        if nearest_rail == 'ascending':
            subtext = f"SPX {spx:,.2f} is {distance:.1f} pts from {cone_name} ascending rail at {nearest.ascending_rail:.2f}"
        else:
            subtext = f"SPX {spx:,.2f} is {distance:.1f} pts from {cone_name} descending rail at {nearest.descending_rail:.2f}"
    else:
        return ''
    
    return f'''
    <div style="background:{bg};border:2px solid {border};border-radius:12px;padding:16px 20px;margin-bottom:20px;display:flex;align-items:center;gap:16px;">
        <div style="font-size:32px;">{icon}</div>
        <div>
            <div style="font-weight:700;font-size:16px;color:{color};">{text}</div>
            <div style="font-size:13px;color:#6b7280;margin-top:4px;">{subtext}</div>
        </div>
    </div>
    '''

def render_dashboard(spx: float, vix: VIXZone, cones: List[Cone], setups: List[TradeSetup], 
                     assessment: DayAssessment, prior: Dict, dark_mode: bool = False,
                     active_cone_info: Dict = None, polygon_status: PolygonStatus = None,
                     candle_verification: Dict = None, vix_auto: bool = False, pivot_auto: bool = False,
                     pivot_source: str = "") -> str:
    """Render an institutional-grade trading dashboard."""
    
    # Professional trading terminal color scheme
    if dark_mode:
        bg_main = "#0a0a0f"
        bg_card = "#12121a"
        bg_elevated = "#1a1a24"
        text_primary = "#e8e8ed"
        text_secondary = "#6b6b7b"
        text_muted = "#45454f"
        border_color = "#2a2a35"
        accent_green = "#00d4aa"
        accent_red = "#ff4757"
        accent_yellow = "#ffd43b"
        accent_blue = "#4dabf7"
    else:
        bg_main = "#f5f5f7"
        bg_card = "#ffffff"
        bg_elevated = "#fafafa"
        text_primary = "#1a1a2e"
        text_secondary = "#5a5a6e"
        text_muted = "#8a8a9a"
        border_color = "#e5e5ea"
        accent_green = "#00a67e"
        accent_red = "#dc3545"
        accent_yellow = "#e6a700"
        accent_blue = "#0066cc"
    
    # Determine bias styling
    if vix.bias == 'CALLS':
        bias_bg = f"linear-gradient(135deg, {accent_green}15, {accent_green}05)"
        bias_border = accent_green
        bias_text = accent_green
        bias_glow = f"0 0 40px {accent_green}20"
    elif vix.bias == 'PUTS':
        bias_bg = f"linear-gradient(135deg, {accent_red}15, {accent_red}05)"
        bias_border = accent_red
        bias_text = accent_red
        bias_glow = f"0 0 40px {accent_red}20"
    else:
        bias_bg = f"linear-gradient(135deg, {accent_yellow}15, {accent_yellow}05)"
        bias_border = accent_yellow
        bias_text = accent_yellow
        bias_glow = f"0 0 40px {accent_yellow}20"
    
    # Connection status
    conn_status = ""
    if polygon_status:
        if polygon_status.connected:
            conn_status = f'<span style="color:{accent_green};font-size:10px;letter-spacing:1px;">● LIVE</span>'
        else:
            conn_status = f'<span style="color:{accent_red};font-size:10px;letter-spacing:1px;">● OFFLINE</span>'
    
    # Auto/Manual badges
    vix_badge = f'<span style="background:{accent_blue}20;color:{accent_blue};padding:2px 6px;border-radius:3px;font-size:9px;letter-spacing:0.5px;">AUTO</span>' if vix_auto else f'<span style="background:{accent_yellow}20;color:{accent_yellow};padding:2px 6px;border-radius:3px;font-size:9px;letter-spacing:0.5px;">MANUAL</span>'
    pivot_badge = f'<span style="background:{accent_blue}20;color:{accent_blue};padding:2px 6px;border-radius:3px;font-size:9px;letter-spacing:0.5px;">AUTO</span>' if pivot_auto else f'<span style="background:{accent_yellow}20;color:{accent_yellow};padding:2px 6px;border-radius:3px;font-size:9px;letter-spacing:0.5px;">MANUAL</span>'
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            
            body {{ 
                font-family: 'Inter', -apple-system, sans-serif;
                background: {bg_main};
                color: {text_primary};
                line-height: 1.5;
                -webkit-font-smoothing: antialiased;
            }}
            
            .dashboard {{
                max-width: 1400px;
                margin: 0 auto;
                padding: 24px;
            }}
            
            /* Header */
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 24px;
                padding-bottom: 20px;
                border-bottom: 1px solid {border_color};
            }}
            
            .header-left h1 {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 2px;
                color: {text_muted};
                margin-bottom: 4px;
            }}
            
            .header-left .price {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 36px;
                font-weight: 700;
                color: {text_primary};
                letter-spacing: -1px;
            }}
            
            .header-left .price .ticker {{
                font-size: 14px;
                color: {text_secondary};
                margin-right: 8px;
                vertical-align: middle;
            }}
            
            .header-right {{
                text-align: right;
            }}
            
            .header-right .time {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 24px;
                font-weight: 600;
                color: {text_primary};
            }}
            
            .header-right .date {{
                font-size: 12px;
                color: {text_secondary};
                margin-top: 4px;
            }}
            
            /* Bias Hero */
            .bias-hero {{
                background: {bias_bg};
                border: 1px solid {bias_border}40;
                border-radius: 16px;
                padding: 32px 40px;
                margin-bottom: 24px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: {bias_glow};
            }}
            
            .bias-main {{
                display: flex;
                align-items: center;
                gap: 24px;
            }}
            
            .bias-indicator {{
                width: 64px;
                height: 64px;
                border-radius: 50%;
                background: {bias_border}20;
                border: 2px solid {bias_border};
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 28px;
            }}
            
            .bias-text h2 {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 32px;
                font-weight: 700;
                color: {bias_text};
                letter-spacing: 2px;
            }}
            
            .bias-text p {{
                font-size: 13px;
                color: {text_secondary};
                margin-top: 4px;
            }}
            
            .bias-metrics {{
                display: flex;
                gap: 40px;
            }}
            
            .bias-metric {{
                text-align: center;
            }}
            
            .bias-metric .label {{
                font-size: 10px;
                color: {text_muted};
                letter-spacing: 1px;
                text-transform: uppercase;
                margin-bottom: 4px;
            }}
            
            .bias-metric .value {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 20px;
                font-weight: 600;
                color: {text_primary};
            }}
            
            /* Grid Layout */
            .grid-2 {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 24px;
            }}
            
            .grid-3 {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                margin-bottom: 24px;
            }}
            
            .grid-4 {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 12px;
            }}
            
            /* Cards */
            .card {{
                background: {bg_card};
                border: 1px solid {border_color};
                border-radius: 12px;
                padding: 20px;
            }}
            
            .card-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 1px solid {border_color};
            }}
            
            .card-title {{
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1.5px;
                text-transform: uppercase;
                color: {text_muted};
            }}
            
            /* Metric Boxes */
            .metric-box {{
                background: {bg_elevated};
                border-radius: 8px;
                padding: 16px;
                text-align: center;
            }}
            
            .metric-box .label {{
                font-size: 10px;
                color: {text_muted};
                letter-spacing: 0.5px;
                text-transform: uppercase;
                margin-bottom: 6px;
            }}
            
            .metric-box .value {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 22px;
                font-weight: 600;
                color: {text_primary};
            }}
            
            .metric-box .sub {{
                font-size: 11px;
                color: {text_secondary};
                margin-top: 4px;
            }}
            
            /* Tables */
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            
            th {{
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.5px;
                text-transform: uppercase;
                color: {text_muted};
                text-align: left;
                padding: 12px 16px;
                border-bottom: 1px solid {border_color};
            }}
            
            td {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 13px;
                padding: 14px 16px;
                border-bottom: 1px solid {border_color}80;
                color: {text_primary};
            }}
            
            tr:last-child td {{
                border-bottom: none;
            }}
            
            tr:hover td {{
                background: {bg_elevated};
            }}
            
            .text-green {{ color: {accent_green}; }}
            .text-red {{ color: {accent_red}; }}
            .text-yellow {{ color: {accent_yellow}; }}
            .text-muted {{ color: {text_muted}; }}
            
            /* Tags */
            .tag {{
                display: inline-block;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                font-family: 'JetBrains Mono', monospace;
            }}
            
            .tag-green {{ background: {accent_green}15; color: {accent_green}; }}
            .tag-red {{ background: {accent_red}15; color: {accent_red}; }}
            .tag-yellow {{ background: {accent_yellow}15; color: {accent_yellow}; }}
            .tag-blue {{ background: {accent_blue}15; color: {accent_blue}; }}
            
            /* Active Row */
            .active-row {{
                background: {accent_green}08 !important;
                border-left: 3px solid {accent_green};
            }}
            
            .active-row td:first-child {{
                padding-left: 13px;
            }}
            
            /* Status Banner */
            .status-banner {{
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 14px 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
            
            .status-banner.alert {{
                background: {accent_red}10;
                border: 1px solid {accent_red}30;
            }}
            
            .status-banner.success {{
                background: {accent_green}10;
                border: 1px solid {accent_green}30;
            }}
            
            .status-banner.warning {{
                background: {accent_yellow}10;
                border: 1px solid {accent_yellow}30;
            }}
            
            .status-banner .icon {{
                font-size: 24px;
            }}
            
            .status-banner .content h4 {{
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 2px;
            }}
            
            .status-banner .content p {{
                font-size: 12px;
                color: {text_secondary};
            }}
            
            /* Cone Visual */
            .cone-row {{
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            
            .cone-name {{
                min-width: 70px;
                font-weight: 600;
            }}
            
            .cone-visual {{
                flex: 1;
                height: 8px;
                background: {bg_elevated};
                border-radius: 4px;
                position: relative;
                overflow: hidden;
            }}
            
            .cone-fill {{
                height: 100%;
                border-radius: 4px;
                background: linear-gradient(90deg, {accent_red}60, {accent_green}60);
            }}
            
        </style>
    </head>
    <body>
        <div class="dashboard">
            
            <!-- Header -->
            <div class="header">
                <div class="header-left">
                    <h1>SPX PROPHET</h1>
                    <div class="price">
                        <span class="ticker">SPX</span>{spx:,.2f}
                    </div>
                    <div style="margin-top:8px;display:flex;gap:12px;align-items:center;">
                        {conn_status}
                        <span style="color:{text_muted};font-size:11px;">VIX {vix_badge}</span>
                        <span style="color:{text_muted};font-size:11px;">PIVOTS {pivot_badge}</span>
                    </div>
                </div>
                <div class="header-right">
                    <div class="time">{get_ct_now().strftime('%H:%M')}</div>
                    <div class="date">{get_ct_now().strftime('%B %d, %Y')} CT</div>
                </div>
            </div>
    '''
    
    # Active Cone Alert Banner
    if active_cone_info:
        inside = active_cone_info.get('inside_cone')
        at_rail = active_cone_info.get('at_rail', False)
        distance = active_cone_info.get('distance', 0)
        rail_type = active_cone_info.get('rail_type')
        
        if inside and at_rail:
            if rail_type == 'ascending':
                html += f'''
                <div class="status-banner alert">
                    <div class="icon">🎯</div>
                    <div class="content">
                        <h4 style="color:{accent_red};">AT {inside.name} ASCENDING RAIL — PUTS ENTRY ZONE</h4>
                        <p>{distance:.1f} pts from rail at {inside.ascending_rail:.2f}</p>
                    </div>
                </div>
                '''
            else:
                html += f'''
                <div class="status-banner success">
                    <div class="icon">🎯</div>
                    <div class="content">
                        <h4 style="color:{accent_green};">AT {inside.name} DESCENDING RAIL — CALLS ENTRY ZONE</h4>
                        <p>{distance:.1f} pts from rail at {inside.descending_rail:.2f}</p>
                    </div>
                </div>
                '''
    
    # Bias Hero Section
    bias_icon = '↗' if vix.bias == 'CALLS' else '↘' if vix.bias == 'PUTS' else '⟷'
    html += f'''
            <!-- Bias Hero -->
            <div class="bias-hero">
                <div class="bias-main">
                    <div class="bias-indicator">{bias_icon}</div>
                    <div class="bias-text">
                        <h2>{vix.bias}</h2>
                        <p>VIX at {vix.position_pct:.0f}% of overnight zone</p>
                    </div>
                </div>
                <div class="bias-metrics">
                    <div class="bias-metric">
                        <div class="label">VIX</div>
                        <div class="value">{vix.current:.2f}</div>
                    </div>
                    <div class="bias-metric">
                        <div class="label">Zone</div>
                        <div class="value">{vix.bottom:.2f} - {vix.top:.2f}</div>
                    </div>
                    <div class="bias-metric">
                        <div class="label">Expected Move</div>
                        <div class="value">{vix.expected_move[0]}-{vix.expected_move[1]} pts</div>
                    </div>
                </div>
            </div>
    '''
    
    # Day Assessment
    if assessment.recommendation == 'FULL':
        assess_class = 'success'
        assess_icon = '✓'
        assess_color = accent_green
    elif assessment.recommendation == 'REDUCED':
        assess_class = 'warning'
        assess_icon = '!'
        assess_color = accent_yellow
    else:
        assess_class = 'alert'
        assess_icon = '✕'
        assess_color = accent_red
    
    warnings_html = ''.join([f'<span style="display:block;margin-top:4px;">• {w}</span>' for w in assessment.warnings]) if assessment.warnings else ''
    
    html += f'''
            <!-- Day Assessment -->
            <div class="status-banner {assess_class}" style="margin-bottom:24px;">
                <div class="icon" style="font-size:20px;width:36px;height:36px;border-radius:50%;background:{assess_color}20;display:flex;align-items:center;justify-content:center;color:{assess_color};font-weight:700;">{assess_icon}</div>
                <div class="content" style="flex:1;">
                    <h4 style="color:{assess_color};">{assessment.recommendation} SIZE — Score: {assessment.score}/100</h4>
                    <p style="color:{text_secondary};">{warnings_html if warnings_html else 'No warnings'}</p>
                </div>
            </div>
    '''
    
    # Structural Cones Table
    html += f'''
            <!-- Cones -->
            <div class="card" style="margin-bottom:24px;">
                <div class="card-header">
                    <span class="card-title">Structural Cones @ 10:00 AM CT</span>
                </div>
                <table>
                    <tr>
                        <th>Pivot</th>
                        <th>Ascending Rail</th>
                        <th>Descending Rail</th>
                        <th style="text-align:center;">Width</th>
                        <th style="text-align:center;">Blocks</th>
                    </tr>
    '''
    
    for cone in cones:
        width_class = 'tag-green' if cone.width >= 25 else 'tag-yellow' if cone.width >= MIN_CONE_WIDTH else 'tag-red'
        html += f'''
                    <tr>
                        <td style="font-weight:600;">{cone.name}</td>
                        <td class="text-red">{cone.ascending_rail:.2f}</td>
                        <td class="text-green">{cone.descending_rail:.2f}</td>
                        <td style="text-align:center;"><span class="tag {width_class}">{cone.width:.0f} pts</span></td>
                        <td style="text-align:center;color:{text_muted};">{cone.blocks}</td>
                    </tr>
        '''
    
    html += '''
                </table>
            </div>
    '''
    
    # Trade Setups - Calls
    calls_setups = [s for s in setups if s.direction == 'CALLS']
    if calls_setups:
        html += f'''
            <div class="card" style="margin-bottom:24px;">
                <div class="card-header">
                    <span class="card-title" style="color:{accent_green};">↗ CALLS SETUPS</span>
                    <span style="font-size:11px;color:{text_muted};">Enter at Descending Rail</span>
                </div>
                <table>
                    <tr>
                        <th>Cone</th>
                        <th>Entry</th>
                        <th>Stop</th>
                        <th>T1 (12.5%)</th>
                        <th>T2 (25%)</th>
                        <th>T3 (50%)</th>
                        <th>Strike</th>
                        <th style="text-align:right;">Distance</th>
                    </tr>
        '''
        for s in calls_setups:
            row_class = 'active-row' if s.is_active else ''
            dist_class = 'tag-green' if s.distance <= 5 else 'tag-yellow' if s.distance <= 15 else ''
            html += f'''
                    <tr class="{row_class}">
                        <td style="font-weight:600;">{s.cone_name}</td>
                        <td class="text-green" style="font-weight:600;">{s.entry:.2f}</td>
                        <td class="text-red">{s.stop:.2f}</td>
                        <td>{s.target_12:.2f}</td>
                        <td>{s.target_25:.2f}</td>
                        <td>{s.target_50:.2f}</td>
                        <td>{s.strike}C</td>
                        <td style="text-align:right;"><span class="tag {dist_class}">{s.distance:.1f}</span></td>
                    </tr>
            '''
        html += '''
                </table>
            </div>
        '''
    
    # Trade Setups - Puts
    puts_setups = [s for s in setups if s.direction == 'PUTS']
    if puts_setups:
        html += f'''
            <div class="card" style="margin-bottom:24px;">
                <div class="card-header">
                    <span class="card-title" style="color:{accent_red};">↘ PUTS SETUPS</span>
                    <span style="font-size:11px;color:{text_muted};">Enter at Ascending Rail</span>
                </div>
                <table>
                    <tr>
                        <th>Cone</th>
                        <th>Entry</th>
                        <th>Stop</th>
                        <th>T1 (12.5%)</th>
                        <th>T2 (25%)</th>
                        <th>T3 (50%)</th>
                        <th>Strike</th>
                        <th style="text-align:right;">Distance</th>
                    </tr>
        '''
        for s in puts_setups:
            row_class = 'active-row' if s.is_active else ''
            dist_class = 'tag-green' if s.distance <= 5 else 'tag-yellow' if s.distance <= 15 else ''
            html += f'''
                    <tr class="{row_class}">
                        <td style="font-weight:600;">{s.cone_name}</td>
                        <td class="text-red" style="font-weight:600;">{s.entry:.2f}</td>
                        <td class="text-green">{s.stop:.2f}</td>
                        <td>{s.target_12:.2f}</td>
                        <td>{s.target_25:.2f}</td>
                        <td>{s.target_50:.2f}</td>
                        <td>{s.strike}P</td>
                        <td style="text-align:right;"><span class="tag {dist_class}">{s.distance:.1f}</span></td>
                    </tr>
            '''
        html += '''
                </table>
            </div>
        '''
    
    # Prior Day Reference
    if prior:
        html += f'''
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Prior Session Reference</span>
                </div>
                <div class="grid-4">
                    <div class="metric-box">
                        <div class="label">High</div>
                        <div class="value">{prior.get('high', 0):,.2f}</div>
                    </div>
                    <div class="metric-box">
                        <div class="label">Low</div>
                        <div class="value">{prior.get('low', 0):,.2f}</div>
                    </div>
                    <div class="metric-box">
                        <div class="label">Close</div>
                        <div class="value">{prior.get('close', 0):,.2f}</div>
                    </div>
                    <div class="metric-box">
                        <div class="label">Range</div>
                        <div class="value">{prior.get('high', 0) - prior.get('low', 0):,.0f} pts</div>
                    </div>
                </div>
            </div>
        '''
    
    html += '''
        </div>
    </body>
    </html>
    '''
    
    return html

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    st.set_page_config(
        page_title="SPX Prophet v5.0",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    if 'use_polygon' not in st.session_state:
        st.session_state.use_polygon = True
    if 'use_manual_vix' not in st.session_state:
        st.session_state.use_manual_vix = False
    if 'use_manual_pivots' not in st.session_state:
        st.session_state.use_manual_pivots = False
    if 'vix_bottom' not in st.session_state:
        st.session_state.vix_bottom = 0.0
    if 'vix_top' not in st.session_state:
        st.session_state.vix_top = 0.0
    if 'vix_current' not in st.session_state:
        st.session_state.vix_current = 0.0
    if 'manual_high' not in st.session_state:
        st.session_state.manual_high = 0.0
    if 'manual_low' not in st.session_state:
        st.session_state.manual_low = 0.0
    if 'manual_close' not in st.session_state:
        st.session_state.manual_close = 0.0
    if 'manual_high_time' not in st.session_state:
        st.session_state.manual_high_time = "10:30"
    if 'manual_low_time' not in st.session_state:
        st.session_state.manual_low_time = "14:00"
    if 'use_sec_high' not in st.session_state:
        st.session_state.use_sec_high = False
    if 'use_sec_low' not in st.session_state:
        st.session_state.use_sec_low = False
    if 'sec_high' not in st.session_state:
        st.session_state.sec_high = 0.0
    if 'sec_low' not in st.session_state:
        st.session_state.sec_low = 0.0
    if 'sec_high_time' not in st.session_state:
        st.session_state.sec_high_time = "11:00"
    if 'sec_low_time' not in st.session_state:
        st.session_state.sec_low_time = "13:00"
    if 'polygon_error' not in st.session_state:
        st.session_state.polygon_error = ""
    
    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ SPX Prophet v5.0")
        st.markdown("---")
        
        # Session Date
        session_date = st.date_input("📅 Session Date", value=get_ct_now().date())
        session_dt = CT_TZ.localize(datetime.combine(session_date, time(10, 0)))
        
        st.markdown("---")
        
        # Data Source Toggle
        st.markdown("### 📡 Data Source")
        st.session_state.use_polygon = st.checkbox("Use Polygon.io", value=st.session_state.use_polygon)
        
        if st.session_state.use_polygon:
            st.info("🔄 Auto-detecting VIX zone and pivots from Polygon...")
        
        st.markdown("---")
        
        # VIX Zone Section
        st.markdown("### 📊 VIX Zone (2am-6am CT)")
        st.session_state.use_manual_vix = st.checkbox("Manual VIX Override", value=st.session_state.use_manual_vix)
        
        if st.session_state.use_manual_vix:
            c1, c2 = st.columns(2)
            with c1:
                st.session_state.vix_bottom = st.number_input("Bottom", min_value=0.0, max_value=100.0, 
                                                               value=st.session_state.vix_bottom, step=0.05, format="%.2f")
            with c2:
                st.session_state.vix_top = st.number_input("Top", min_value=0.0, max_value=100.0, 
                                                           value=st.session_state.vix_top, step=0.05, format="%.2f")
        
        st.session_state.vix_current = st.number_input("Current VIX", min_value=0.0, max_value=100.0, 
                                                        value=st.session_state.vix_current, step=0.05, format="%.2f")
        
        st.markdown("---")
        
        # Pivots Section
        st.markdown("### 📍 Prior Day Pivots")
        st.session_state.use_manual_pivots = st.checkbox("Manual Pivot Override", value=st.session_state.use_manual_pivots)
        
        if st.session_state.use_manual_pivots:
            c1, c2 = st.columns(2)
            with c1:
                st.session_state.manual_high = st.number_input("High", min_value=0.0, max_value=10000.0, 
                                                                value=st.session_state.manual_high, step=0.25, format="%.2f")
            with c2:
                st.session_state.manual_high_time = st.text_input("High Time (CT)", value=st.session_state.manual_high_time)
            
            c1, c2 = st.columns(2)
            with c1:
                st.session_state.manual_low = st.number_input("Low", min_value=0.0, max_value=10000.0, 
                                                               value=st.session_state.manual_low, step=0.25, format="%.2f")
            with c2:
                st.session_state.manual_low_time = st.text_input("Low Time (CT)", value=st.session_state.manual_low_time)
            
            st.session_state.manual_close = st.number_input("Close", min_value=0.0, max_value=10000.0, 
                                                             value=st.session_state.manual_close, step=0.25, format="%.2f")
        
        st.markdown("### 📐 Secondary Pivots")
        st.session_state.use_sec_high = st.checkbox("Enable High²", value=st.session_state.use_sec_high)
        if st.session_state.use_sec_high:
            c1, c2 = st.columns(2)
            with c1:
                st.session_state.sec_high = st.number_input("High² Price", min_value=0.0, max_value=10000.0, 
                                                             value=st.session_state.sec_high, step=0.25, format="%.2f")
            with c2:
                st.session_state.sec_high_time = st.text_input("Time (CT)", value=st.session_state.sec_high_time, key="sht")
        
        st.session_state.use_sec_low = st.checkbox("Enable Low²", value=st.session_state.use_sec_low)
        if st.session_state.use_sec_low:
            c1, c2 = st.columns(2)
            with c1:
                st.session_state.sec_low = st.number_input("Low² Price", min_value=0.0, max_value=10000.0, 
                                                            value=st.session_state.sec_low, step=0.25, format="%.2f")
            with c2:
                st.session_state.sec_low_time = st.text_input("Time (CT)", value=st.session_state.sec_low_time, key="slt")
        
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col2:
            theme_label = "🌙 Dark" if not st.session_state.dark_mode else "☀️ Light"
            if st.button(theme_label, use_container_width=True):
                st.session_state.dark_mode = not st.session_state.dark_mode
                st.rerun()
    
    # ========== MAIN DATA FETCHING ==========
    
    # Check Polygon connection
    polygon_status = None
    if st.session_state.use_polygon:
        polygon_status = check_polygon_connection()
    
    # Fetch VIX Zone (auto or manual)
    # Note: Polygon Indices requires paid plan, so we use yfinance for VIX
    vix_auto_detected = False
    vix_bottom = st.session_state.vix_bottom
    vix_top = st.session_state.vix_top
    vix_debug_info = None  # Store debug info about VIX detection
    
    if not st.session_state.use_manual_vix:
        # Try Polygon first if we have paid Indices access
        overnight_vix = None
        if POLYGON_HAS_INDICES and st.session_state.use_polygon:
            overnight_vix = polygon_get_overnight_vix_range(session_dt)
        
        # Otherwise use yfinance (free, works great)
        if overnight_vix is None:
            overnight_vix = yf_fetch_overnight_vix_range(session_dt)
        
        if overnight_vix:
            vix_bottom = overnight_vix['bottom']
            vix_top = overnight_vix['top']
            vix_auto_detected = True
            vix_debug_info = overnight_vix  # Save all debug info
    
    # Also auto-fetch current VIX if not manually set
    if st.session_state.vix_current == 0:
        current_vix = yf_fetch_current_vix()
        if current_vix > 0:
            st.session_state.vix_current = current_vix
    
    # Fetch Pivots (auto or manual)
    pivot_auto_detected = False
    pivot_source = ""
    prior = None
    
    # Use yfinance for SPX pivots (Polygon Indices requires paid plan)
    # When POLYGON_HAS_INDICES is True, we'll use Polygon instead
    if POLYGON_HAS_INDICES and st.session_state.use_polygon and not st.session_state.use_manual_pivots:
        prior = polygon_get_prior_session_pivots(session_dt)
        if prior:
            pivot_auto_detected = True
            pivot_source = "Polygon"
    
    # Use yfinance (free, works great for historical data)
    if prior is None:
        prior = yf_fetch_prior_session(session_dt)
        if prior:
            pivot_auto_detected = True  # Still auto-detected, just via yfinance
            pivot_source = "yfinance"
    
    # Use manual pivots if enabled
    if st.session_state.use_manual_pivots and st.session_state.manual_high > 0:
        prior_high = st.session_state.manual_high
        prior_low = st.session_state.manual_low
        prior_close = st.session_state.manual_close
        try:
            h, m = map(int, st.session_state.manual_high_time.split(':'))
            high_time = CT_TZ.localize(datetime.combine(session_date - timedelta(days=1), time(h, m)))
        except:
            high_time = CT_TZ.localize(datetime.combine(session_date - timedelta(days=1), time(10, 30)))
        try:
            h, m = map(int, st.session_state.manual_low_time.split(':'))
            low_time = CT_TZ.localize(datetime.combine(session_date - timedelta(days=1), time(h, m)))
        except:
            low_time = CT_TZ.localize(datetime.combine(session_date - timedelta(days=1), time(14, 0)))
        high_close = prior_high  # Manual doesn't distinguish
        pivot_auto_detected = False
    elif prior:
        prior_high = prior['high']
        prior_low = prior['low']
        prior_close = prior['close']
        high_time = prior.get('high_time', CT_TZ.localize(datetime.combine(session_date - timedelta(days=1), time(12, 0))))
        low_time = prior.get('low_time', CT_TZ.localize(datetime.combine(session_date - timedelta(days=1), time(12, 0))))
        high_close = prior.get('high_close', prior_high)
    else:
        prior_high = 0
        prior_low = 0
        prior_close = 0
        high_time = CT_TZ.localize(datetime.combine(session_date - timedelta(days=1), time(12, 0)))
        low_time = high_time
        high_close = 0
    
    # Get current SPX price (use yfinance since Polygon Indices requires paid plan)
    spx = 0.0
    if POLYGON_HAS_INDICES and st.session_state.use_polygon:
        spx = polygon_get_current_price(POLYGON_SPX) or 0.0
    if spx == 0:
        spx = yf_fetch_current_spx() or prior_close or 6000
    
    # Build pivots
    pivots = []
    if prior_high > 0:
        pivots = [
            Pivot(
                price=prior_high,
                time=high_time,
                name='High',
                is_secondary=False,
                price_for_ascending=prior_high,
                price_for_descending=high_close
            ),
            Pivot(
                price=prior_low,
                time=low_time,
                name='Low',
                is_secondary=False,
                price_for_ascending=prior_low,
                price_for_descending=prior_low
            ),
            Pivot(
                price=prior_close,
                time=CT_TZ.localize(datetime.combine(session_date - timedelta(days=1), time(15, 0))),
                name='Close',
                is_secondary=False,
                price_for_ascending=prior_close,
                price_for_descending=prior_close
            ),
        ]
        
        # Add secondary pivots if enabled
        if st.session_state.use_sec_high and st.session_state.sec_high > 0:
            try:
                h, m = map(int, st.session_state.sec_high_time.split(':'))
                t = CT_TZ.localize(datetime.combine(session_date - timedelta(days=1), time(h, m)))
                pivots.append(Pivot(
                    price=st.session_state.sec_high,
                    time=t,
                    name='High²',
                    is_secondary=True,
                    price_for_ascending=st.session_state.sec_high,
                    price_for_descending=st.session_state.sec_high
                ))
            except:
                pass
        
        if st.session_state.use_sec_low and st.session_state.sec_low > 0:
            try:
                h, m = map(int, st.session_state.sec_low_time.split(':'))
                t = CT_TZ.localize(datetime.combine(session_date - timedelta(days=1), time(h, m)))
                pivots.append(Pivot(
                    price=st.session_state.sec_low,
                    time=t,
                    name='Low²',
                    is_secondary=True,
                    price_for_ascending=st.session_state.sec_low,
                    price_for_descending=st.session_state.sec_low
                ))
            except:
                pass
    
    # Build cones
    eval_time = CT_TZ.localize(datetime.combine(session_date, time(10, 0)))
    cones = build_cones(pivots, eval_time) if pivots else []
    
    # Analyze VIX
    vix = analyze_vix(vix_bottom, vix_top, st.session_state.vix_current, auto_detected=vix_auto_detected)
    
    # Generate setups
    setups = generate_setups(cones, spx, vix.bias) if cones else []
    
    # Assess day
    assessment = assess_day(vix, cones, spx)
    
    # Find active cone
    active_cone_info = find_active_cone(spx, cones) if cones else None
    
    # Verify candle close (if Polygon is available)
    candle_verification = None
    if st.session_state.use_polygon and vix.bottom > 0:
        candle_verification = verify_vix_candle_close(vix, session_dt)
    
    # Render dashboard
    html = render_dashboard(
        spx, vix, cones, setups, assessment, prior,
        dark_mode=st.session_state.dark_mode,
        active_cone_info=active_cone_info,
        polygon_status=polygon_status,
        candle_verification=candle_verification,
        vix_auto=vix_auto_detected,
        pivot_auto=pivot_auto_detected,
        pivot_source=pivot_source
    )
    
    components.html(html, height=1600, scrolling=True)
    
    # ========== VIX DEBUG INFO ==========
    if vix_debug_info:
        with st.expander("🔍 VIX Zone Debug Info (click to expand)"):
            st.markdown("### VIX Data Detection Details")
            st.markdown(f"**Session Date:** {vix_debug_info.get('session_date', 'N/A')}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Requested Window:**")
                st.write(f"Start: {vix_debug_info.get('requested_start', 'N/A')}")
                st.write(f"End: {vix_debug_info.get('requested_end', 'N/A')}")
            
            with col2:
                st.markdown("**Filtered Data Used:**")
                st.write(f"Start: {vix_debug_info.get('filtered_data_start', 'N/A')}")
                st.write(f"End: {vix_debug_info.get('filtered_data_end', 'N/A')}")
            
            st.markdown("---")
            st.markdown("**Raw API Data Range (before filtering):**")
            st.write(f"Start: {vix_debug_info.get('actual_data_start', 'N/A')}")
            st.write(f"End: {vix_debug_info.get('actual_data_end', 'N/A')}")
            
            st.markdown("---")
            st.markdown("**Bar Counts:**")
            st.write(f"Total bars fetched from API: {vix_debug_info.get('total_bars_fetched', 'N/A')}")
            st.write(f"Bars within 2am-6am window: {vix_debug_info.get('overnight_bars_found', vix_debug_info.get('bar_count', 'N/A'))}")
            
            st.markdown("---")
            st.markdown("**Detected Zone:**")
            st.write(f"Bottom: {vix_debug_info.get('bottom', 'N/A')}")
            st.write(f"Top: {vix_debug_info.get('top', 'N/A')}")
            st.write(f"Zone Size: {vix_debug_info.get('zone_size', 'N/A')}")
            
            if vix_debug_info.get('error'):
                st.error(f"Error: {vix_debug_info.get('error')}")

if __name__ == "__main__":
    main()
"""
SPX PROPHET - 0DTE Trading System
Complete Streamlit Application
Version 2.1 | January 2026
"""

import streamlit as st
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
import requests
from dataclasses import dataclass
import pytz

# ============================================================
# CONFIGURATION
# ============================================================

INPUTS_FILE = "spx_prophet_inputs.json"
POLYGON_API_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
REFRESH_INTERVAL = 900

CT = pytz.timezone("America/Chicago")
ET = pytz.timezone("America/New_York")

RTH_OPEN_HOUR, RTH_OPEN_MIN = 8, 30
RTH_CLOSE_HOUR, RTH_CLOSE_MIN = 15, 0
ENTRY_CUTOFF_HOUR, ENTRY_CUTOFF_MIN = 11, 30
ENTRY_HOUR, ENTRY_MIN = 9, 0  # CRITICAL: 9:00 AM CT entry time

CONE_SLOPE = 0.475

# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class ManualInputs:
    vix_overnight_high: float = 0.0
    vix_overnight_low: float = 0.0
    vix_current: float = 0.0
    es_spx_offset: float = 0.0
    prior_high: float = 0.0
    prior_low: float = 0.0
    prior_close: float = 0.0
    manual_ceiling: float = 0.0
    manual_floor: float = 0.0
    use_manual_structure: bool = False
    trading_date: str = ""  # YYYY-MM-DD format for the trading day
    date: str = ""
    last_updated: str = ""
    
    def to_dict(self) -> dict:
        return self.__dict__.copy()
    
    @classmethod
    def from_dict(cls, data: dict) -> "ManualInputs":
        fields = {k: data.get(k, getattr(cls, k, None) if hasattr(cls, k) else None) 
                 for k in cls.__dataclass_fields__}
        # Handle None values
        for k, v in fields.items():
            if v is None:
                if k in ['use_manual_structure']:
                    fields[k] = False
                elif k in ['trading_date', 'date', 'last_updated']:
                    fields[k] = ""
                else:
                    fields[k] = 0.0
        return cls(**fields)

@dataclass
class MABias:
    ema_50: float
    sma_200: float
    bias: str
    instruction: str

@dataclass
class DayStructure:
    ceiling_spx: float
    floor_spx: float
    ceiling_es: float
    floor_es: float
    is_manual: bool = False

@dataclass
class VIXZone:
    zone_size: float
    zone_position: str
    puts_springboard: float
    calls_springboard: float
    timing_signal: str
    position_percent: float

@dataclass
class ConeRails:
    c1_ascending: float
    c1_descending: float
    c2_ascending: float
    c2_descending: float
    c3_ascending: float
    c3_descending: float
    blocks_elapsed: float

@dataclass
class TradeSignal:
    direction: str
    entry_level: float
    strike: int
    distance: float
    all_aligned: bool
    reason: str

@dataclass
class OptionsData:
    strike: int
    option_type: str
    last: float
    bid: float
    ask: float
    volume: int
    open_interest: int
    ticker: str

# ============================================================
# PERSISTENCE
# ============================================================

def save_inputs(inputs: ManualInputs) -> None:
    now = datetime.now(CT)
    inputs.last_updated = now.strftime("%Y-%m-%d %H:%M:%S")
    inputs.date = now.strftime("%Y-%m-%d")
    with open(INPUTS_FILE, "w") as f:
        json.dump(inputs.to_dict(), f, indent=2)

def load_inputs() -> ManualInputs:
    if os.path.exists(INPUTS_FILE):
        with open(INPUTS_FILE, "r") as f:
            return ManualInputs.from_dict(json.load(f))
    return ManualInputs()

# ============================================================
# DATA FETCHING
# ============================================================

def get_polygon_api_key() -> str:
    if "polygon_api_key" in st.session_state and st.session_state.polygon_api_key:
        return st.session_state.polygon_api_key
    return POLYGON_API_KEY

def get_es_price_polygon() -> Optional[float]:
    api_key = get_polygon_api_key()
    if not api_key:
        return None
    try:
        url = f"https://api.polygon.io/v2/aggs/ticker/I:ES1!/prev?apiKey={api_key}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                return float(data["results"][0].get("c", 0))
    except Exception:
        pass
    return None

def get_es_price_yahoo() -> Optional[float]:
    try:
        import yfinance as yf
        es = yf.Ticker("ES=F")
        data = es.history(period="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception:
        pass
    return None

def get_es_candles_polygon(days: int = 20) -> Optional[list]:
    api_key = get_polygon_api_key()
    if not api_key:
        return None
    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        url = f"https://api.polygon.io/v2/aggs/ticker/I:ES1!/range/30/minute/{start_date}/{end_date}?adjusted=true&sort=asc&limit=50000&apiKey={api_key}"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "results" in data:
                return data["results"]
    except Exception:
        pass
    return None

def get_es_candles_yahoo(days: int = 20) -> Optional[list]:
    try:
        import yfinance as yf
        es = yf.Ticker("ES=F")
        data = es.history(period=f"{days}d", interval="30m")
        if not data.empty:
            candles = []
            for idx, row in data.iterrows():
                candles.append({
                    "t": int(idx.timestamp() * 1000),
                    "o": row["Open"], "h": row["High"],
                    "l": row["Low"], "c": row["Close"]
                })
            return candles
    except Exception:
        pass
    return None

def get_spx_options_polygon(strike: int, option_type: str = "call", trading_date: str = None) -> Optional[OptionsData]:
    """
    Fetch SPXW options data from Polygon for the specified trading date.
    
    Option ticker format: O:SPXW{YYMMDD}{C/P}{strike*1000:08d}
    """
    api_key = get_polygon_api_key()
    if not api_key:
        return None
    
    try:
        # Use provided trading date or default to today
        if trading_date:
            exp_date = trading_date
            exp_dt = datetime.strptime(trading_date, "%Y-%m-%d")
        else:
            exp_dt = datetime.now()
            exp_date = exp_dt.strftime("%Y-%m-%d")
        
        exp_str = exp_dt.strftime("%y%m%d")
        opt_type = "C" if option_type.lower() == "call" else "P"
        strike_padded = str(int(strike * 1000)).zfill(8)
        option_ticker = f"O:SPXW{exp_str}{opt_type}{strike_padded}"
        
        # Method 1: Direct single contract snapshot
        url = f"https://api.polygon.io/v3/snapshot/options/SPXW/{option_ticker}?apiKey={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "results" in data:
                result = data["results"]
                day = result.get("day", {})
                quote = result.get("last_quote", {})
                return OptionsData(
                    strike=strike,
                    option_type=option_type,
                    last=day.get("close", day.get("last", 0)) or 0,
                    bid=quote.get("bid", 0) or 0,
                    ask=quote.get("ask", 0) or 0,
                    volume=day.get("volume", 0) or 0,
                    open_interest=result.get("open_interest", 0) or 0,
                    ticker=option_ticker
                )
        
        # Method 2: Options chain search
        url = f"https://api.polygon.io/v3/snapshot/options/SPXW?strike_price={strike}&expiration_date={exp_date}&contract_type={option_type.lower()}&apiKey={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                for result in data["results"]:
                    ticker = result.get("details", {}).get("ticker", "")
                    if "SPXW" in ticker:
                        day = result.get("day", {})
                        quote = result.get("last_quote", {})
                        return OptionsData(
                            strike=strike, option_type=option_type,
                            last=day.get("close", 0) or 0,
                            bid=quote.get("bid", 0) or 0,
                            ask=quote.get("ask", 0) or 0,
                            volume=day.get("volume", 0) or 0,
                            open_interest=result.get("open_interest", 0) or 0,
                            ticker=ticker
                        )
    except Exception as e:
        pass
    return None

@dataclass
class EconomicEvent:
    """Economic calendar event"""
    time: str
    name: str
    impact: str  # HIGH, MEDIUM, LOW
    actual: str
    forecast: str
    previous: str

def get_economic_calendar() -> list:
    """
    Fetch today's economic calendar events.
    Uses free APIs - Trading Economics or Forex Factory style data.
    """
    events = []
    today = datetime.now(CT).strftime("%Y-%m-%d")
    
    # Try Polygon economic calendar (if available)
    api_key = get_polygon_api_key()
    if api_key:
        try:
            # Polygon doesn't have a direct econ calendar, but we can check for known events
            pass
        except:
            pass
    
    # Fallback: Use a free economic calendar API
    try:
        # Try financialmodelingprep free API
        url = f"https://financialmodelingprep.com/api/v3/economic_calendar?from={today}&to={today}&apikey=demo"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for item in data[:10]:  # Limit to 10 events
                if item.get("country", "").upper() == "US":
                    event_time = item.get("date", "")
                    if "T" in event_time:
                        # Parse and convert to CT
                        try:
                            dt = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                            dt_ct = dt.astimezone(CT)
                            time_str = dt_ct.strftime("%I:%M %p")
                        except:
                            time_str = event_time.split("T")[1][:5] if "T" in event_time else ""
                    else:
                        time_str = ""
                    
                    events.append(EconomicEvent(
                        time=time_str,
                        name=item.get("event", "Unknown"),
                        impact=item.get("impact", "MEDIUM").upper(),
                        actual=str(item.get("actual", "")),
                        forecast=str(item.get("estimate", "")),
                        previous=str(item.get("previous", ""))
                    ))
            return events
    except:
        pass
    
    # If APIs fail, return common high-impact events to watch for
    # These are typical times for major US economic releases (CT)
    now = datetime.now(CT)
    weekday = now.weekday()
    
    # Static list of common high-impact events by day
    common_events = {
        0: [  # Monday
            EconomicEvent("", "Check calendar for scheduled releases", "MEDIUM", "", "", ""),
        ],
        1: [  # Tuesday
            EconomicEvent("", "Check calendar for scheduled releases", "MEDIUM", "", "", ""),
        ],
        2: [  # Wednesday
            EconomicEvent("1:00 PM", "FOMC Minutes (if scheduled)", "HIGH", "", "", ""),
        ],
        3: [  # Thursday
            EconomicEvent("7:30 AM", "Jobless Claims", "MEDIUM", "", "", ""),
        ],
        4: [  # Friday
            EconomicEvent("7:30 AM", "NFP/Employment (1st Fri)", "HIGH", "", "", ""),
        ],
    }
    
    # Always include these high-impact event times to watch
    key_times = [
        EconomicEvent("7:30 AM", "Major Economic Data Window", "HIGH", "", "", ""),
        EconomicEvent("9:00 AM", "Secondary Data Window", "MEDIUM", "", "", ""),
        EconomicEvent("9:45 AM", "PMI Data Window", "MEDIUM", "", "", ""),
        EconomicEvent("1:00 PM", "Fed Speakers/FOMC Window", "HIGH", "", "", ""),
    ]
    
    if weekday < 5:
        return common_events.get(weekday, []) + key_times
    return [EconomicEvent("", "Market Closed - Weekend", "LOW", "", "", "")]

# ============================================================
# CALCULATIONS
# ============================================================

def calculate_ema(prices: list, period: int) -> float:
    if len(prices) < period:
        return prices[-1] if prices else 0
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_sma(prices: list, period: int) -> float:
    if len(prices) < period:
        return sum(prices) / len(prices) if prices else 0
    return sum(prices[-period:]) / period

def calculate_ma_bias(candles: list) -> MABias:
    if not candles or len(candles) < 200:
        return MABias(0, 0, "NEUTRAL", "Insufficient data")
    
    closes = [c.get("c", c.get("close", 0)) for c in candles]
    ema_50 = calculate_ema(closes, 50)
    sma_200 = calculate_sma(closes, 200)
    
    diff_pct = (ema_50 - sma_200) / sma_200 * 100 if sma_200 else 0
    
    if diff_pct > 0.1:
        return MABias(round(ema_50, 2), round(sma_200, 2), "LONG", "CALLS Allowed")
    elif diff_pct < -0.1:
        return MABias(round(ema_50, 2), round(sma_200, 2), "SHORT", "PUTS Allowed")
    return MABias(round(ema_50, 2), round(sma_200, 2), "NEUTRAL", "No Trades")

def calculate_day_structure(candles: list, es_spx_offset: float,
                           manual_ceiling: float = 0, manual_floor: float = 0,
                           use_manual: bool = False) -> DayStructure:
    """Calculate CEILING/FLOOR projected to 9:00 AM CT entry"""
    if use_manual and manual_ceiling > 0 and manual_floor > 0:
        return DayStructure(
            manual_ceiling, manual_floor,
            manual_ceiling + es_spx_offset, manual_floor + es_spx_offset,
            is_manual=True
        )
    
    if not candles:
        return DayStructure(0, 0, 0, 0)
    
    now = datetime.now(CT)
    overnight_start = now.replace(hour=17, minute=0) - timedelta(days=1)
    
    overnight_candles = []
    for c in candles:
        ts = c.get("t", 0)
        if ts > 1e12:
            ts = ts / 1000
        try:
            ct = datetime.fromtimestamp(ts, tz=CT)
            if overnight_start <= ct <= now:
                overnight_candles.append(c)
        except:
            pass
    
    if not overnight_candles:
        overnight_candles = candles[-20:] if len(candles) >= 20 else candles
    
    highs = [c.get("h", c.get("high", 0)) for c in overnight_candles]
    lows = [c.get("l", c.get("low", 0)) for c in overnight_candles]
    
    ceiling_es = max(highs) if highs else 0
    floor_es = min(lows) if lows else 0
    
    return DayStructure(
        round(ceiling_es - es_spx_offset, 2),
        round(floor_es - es_spx_offset, 2),
        round(ceiling_es, 2),
        round(floor_es, 2)
    )

def calculate_vix_zone(vix_high: float, vix_low: float, vix_current: float) -> VIXZone:
    if vix_high <= 0 or vix_low <= 0:
        return VIXZone(0, "NO DATA", 0, 0, "WAIT", 50)
    
    zone_size = max(vix_high - vix_low, 0.01)
    puts_spring = vix_high
    calls_spring = vix_low
    
    if vix_current > vix_high:
        zones_above = (vix_current - vix_high) / zone_size
        position = f"ABOVE +{zones_above:.1f}"
        pct = 100 + zones_above * 50
        calls_spring = vix_high + (int(zones_above) + 1) * zone_size
        timing = "PUTS" if abs(vix_current - vix_high) <= zone_size * 0.20 else "WAIT"
    elif vix_current < vix_low:
        zones_below = (vix_low - vix_current) / zone_size
        position = f"BELOW -{zones_below:.1f}"
        pct = -zones_below * 50
        puts_spring = vix_low - (int(zones_below) + 1) * zone_size
        timing = "CALLS" if abs(vix_current - vix_low) <= zone_size * 0.20 else "WAIT"
    else:
        range_pos = (vix_current - vix_low) / zone_size
        pct = range_pos * 100
        position = f"INSIDE ({pct:.0f}%)"
        timing = "CALLS" if range_pos <= 0.30 else ("PUTS" if range_pos >= 0.70 else "WAIT")
    
    return VIXZone(round(zone_size, 2), position, round(puts_spring, 2),
                   round(calls_spring, 2), timing, round(pct, 1))

def calculate_cone_rails(prior_high: float, prior_low: float, prior_close: float,
                        es_spx_offset: float) -> ConeRails:
    """
    Calculate cone rails projected to 9:00 AM CT entry time.
    
    Anchor: 3:00 PM CT (close of 2:30pm candle - actual RTH close)
    Target: 9:00 AM CT next trading day (entry time)
    
    Market schedule:
    - 2:30 PM candle closes at 3:00 PM CT (RTH close - THIS IS THE ANCHOR)
    - 3:00 PM and 3:30 PM candles trade
    - Maintenance break
    - Futures reopen at 5:00 PM CT
    - Overnight session until next day
    - RTH opens 8:30 AM CT, entry at 9:00 AM CT
    
    Blocks from 3pm to 9am = 18 hours = 1080 minutes = 36 thirty-minute blocks
    This is FIXED regardless of current time - we're projecting to entry.
    """
    # Fixed calculation: 3pm to 9am is always 18 hours = 36 blocks
    # The prior day values are from yesterday's close, projected to today's 9am entry
    BLOCKS_3PM_TO_9AM = 36  # 18 hours * 2 blocks/hour
    
    exp = BLOCKS_3PM_TO_9AM * CONE_SLOPE  # 36 * 0.475 = 17.1 points
    
    return ConeRails(
        round((prior_high + exp) - es_spx_offset, 2),
        round((prior_high - exp) - es_spx_offset, 2),
        round((prior_low + exp) - es_spx_offset, 2),
        round((prior_low - exp) - es_spx_offset, 2),
        round((prior_close + exp) - es_spx_offset, 2),
        round((prior_close - exp) - es_spx_offset, 2),
        BLOCKS_3PM_TO_9AM
    )

def calculate_trade_signal(ma: MABias, struct: DayStructure, vix: VIXZone,
                          price: float) -> TradeSignal:
    if ma.bias == "NEUTRAL":
        return TradeSignal("NO_TRADE", 0, 0, 0, False, "MA Bias NEUTRAL")
    
    if ma.bias == "LONG":
        entry = struct.floor_spx
        dist = abs(price - entry) if price > 0 else 0
        strike = int(round((entry + 15) / 5) * 5)
        
        if vix.timing_signal == "CALLS":
            return TradeSignal("CALLS", entry, strike, round(dist, 2), True, "All pillars aligned for CALLS")
        elif vix.timing_signal == "PUTS":
            return TradeSignal("NO_TRADE", entry, 0, round(dist, 2), False, "MA LONG but VIX says PUTS")
        return TradeSignal("WAIT", entry, strike, round(dist, 2), False, "Waiting for VIX CALLS springboard")
    
    else:  # SHORT
        entry = struct.ceiling_spx
        dist = abs(entry - price) if price > 0 else 0
        strike = int(round((entry - 15) / 5) * 5)
        
        if vix.timing_signal == "PUTS":
            return TradeSignal("PUTS", entry, strike, round(dist, 2), True, "All pillars aligned for PUTS")
        elif vix.timing_signal == "CALLS":
            return TradeSignal("NO_TRADE", entry, 0, round(dist, 2), False, "MA SHORT but VIX says CALLS")
        return TradeSignal("WAIT", entry, strike, round(dist, 2), False, "Waiting for VIX PUTS springboard")

# ============================================================
# UTILITIES
# ============================================================

def is_rth_open() -> bool:
    now = datetime.now(CT)
    if now.weekday() >= 5:
        return False
    rth_open = now.replace(hour=RTH_OPEN_HOUR, minute=RTH_OPEN_MIN, second=0)
    rth_close = now.replace(hour=RTH_CLOSE_HOUR, minute=RTH_CLOSE_MIN, second=0)
    return rth_open <= now <= rth_close

def is_entry_window() -> bool:
    now = datetime.now(CT)
    if now.weekday() >= 5:
        return False
    entry_open = now.replace(hour=RTH_OPEN_HOUR, minute=RTH_OPEN_MIN, second=0)
    entry_close = now.replace(hour=ENTRY_CUTOFF_HOUR, minute=ENTRY_CUTOFF_MIN, second=0)
    return entry_open <= now <= entry_close

def get_time_display() -> Tuple[str, str, str]:
    now = datetime.now(CT)
    time_str = now.strftime("%I:%M %p CT").lstrip("0")
    date_str = now.strftime("%A, %B %d, %Y")
    if is_entry_window():
        status = "● Entry Window Open"
    elif is_rth_open():
        status = "● RTH Open (Past Cutoff)"
    else:
        status = "○ Market Closed"
    return time_str, date_str, status


# ============================================================
# STREAMLIT UI
# ============================================================

def apply_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
        :root {
            --bg-deep: #05080d; --bg-panel: #0a0f18; --bg-elevated: #101820;
            --border: #1a2433; --border-active: #2a3a50;
            --text-primary: #f0f4f8; --text-secondary: #7a8a9a; --text-muted: #4a5a6a;
            --green: #00e676; --green-bg: rgba(0,230,118,0.08);
            --red: #ff5252; --red-bg: rgba(255,82,82,0.08);
            --gold: #ffab00; --gold-bg: rgba(255,171,0,0.08);
            --blue: #40c4ff;
        }
        .stApp { background-color: var(--bg-deep); }
        .main .block-container { padding-top: 2rem; max-width: 100%; }
        #MainMenu, footer, header { visibility: hidden; }
        
        .prophet-card {
            background: var(--bg-panel); border: 1px solid var(--border);
            border-radius: 12px; padding: 20px; margin-bottom: 16px;
        }
        .prophet-card-header {
            font-family: 'IBM Plex Mono', monospace; font-size: 10px; font-weight: 600;
            text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-muted);
            margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
        }
        .prophet-card-header::after { content: ''; flex: 1; height: 1px; background: var(--border); }
        
        .pillar {
            background: var(--bg-panel); border: 1px solid var(--border);
            padding: 20px 24px; display: flex; align-items: center; gap: 20px; margin-bottom: 2px;
        }
        .pillar:first-child { border-radius: 12px 12px 0 0; }
        .pillar:last-child { border-radius: 0 0 12px 12px; }
        .pillar.pass { background: var(--bg-elevated); border-color: var(--border-active); }
        
        .pillar-number {
            width: 48px; height: 48px; border-radius: 50%; background: var(--bg-deep);
            border: 2px solid var(--border); display: flex; align-items: center; justify-content: center;
            font-family: 'IBM Plex Mono', monospace; font-size: 18px; font-weight: 700;
            color: var(--text-muted); flex-shrink: 0;
        }
        .pillar-number.pass { border-color: var(--green); color: var(--green); background: var(--green-bg); }
        .pillar-number.fail { border-color: var(--red); color: var(--red); background: var(--red-bg); }
        .pillar-number.wait { border-color: var(--gold); color: var(--gold); background: var(--gold-bg); }
        
        .trade-decision {
            background: var(--bg-panel); border: 2px solid var(--border);
            border-radius: 16px; padding: 32px; text-align: center; margin: 24px 0;
        }
        .trade-decision.ready { border-color: var(--green); background: linear-gradient(180deg, var(--green-bg), var(--bg-panel)); }
        .trade-decision.no-trade { border-color: var(--red); background: linear-gradient(180deg, var(--red-bg), var(--bg-panel)); }
        .trade-decision.waiting { border-color: var(--gold); background: linear-gradient(180deg, var(--gold-bg), var(--bg-panel)); }
        
        .value-large { font-family: 'IBM Plex Mono', monospace; font-size: 36px; font-weight: 700; letter-spacing: -1px; }
        .value-medium { font-family: 'IBM Plex Mono', monospace; font-size: 20px; font-weight: 600; }
        .value-small { font-family: 'IBM Plex Mono', monospace; font-size: 14px; }
        
        .text-green { color: var(--green) !important; }
        .text-red { color: var(--red) !important; }
        .text-gold { color: var(--gold) !important; }
        .text-blue { color: var(--blue) !important; }
        .text-muted { color: var(--text-muted) !important; }
        .text-secondary { color: var(--text-secondary) !important; }
        
        .stTextInput > div > div > input, .stNumberInput > div > div > input {
            background-color: var(--bg-deep) !important; border: 1px solid var(--border) !important;
            border-radius: 6px !important; color: var(--text-primary) !important;
            font-family: 'IBM Plex Mono', monospace !important;
        }
        .stButton > button {
            background-color: var(--bg-deep) !important; border: 1px solid var(--border) !important;
            border-radius: 6px !important; color: var(--text-primary) !important;
            font-family: 'IBM Plex Mono', monospace !important; font-weight: 600 !important;
            width: 100%; padding: 12px 24px !important;
        }
        .stButton > button:hover { background-color: var(--bg-elevated) !important; border-color: var(--border-active) !important; }
        [data-testid="stSidebar"] { background-color: var(--bg-panel) !important; }
        
        .entry-badge {
            background: var(--gold-bg); border: 1px solid var(--gold); border-radius: 6px;
            padding: 8px 12px; font-family: 'IBM Plex Mono', monospace; font-size: 12px;
            color: var(--gold); display: inline-block; margin: 8px 0;
        }
    </style>
    """, unsafe_allow_html=True)

def render_pillar(num, name, role, question, answer, detail, status):
    s = "pass" if status == "pass" else ("fail" if status == "fail" else "wait")
    ac = "text-green" if answer in ["LONG","CALLS","FLOOR"] else ("text-red" if answer in ["SHORT","PUTS","CEILING"] else "text-gold")
    return f'''<div class="pillar {s}">
        <div class="pillar-number {s}">{num}</div>
        <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:4px;">
                <span style="font-weight:600;font-size:15px;color:var(--text-primary);">{name}</span>
                <span style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;">{role}</span>
            </div>
            <p style="font-size:13px;color:var(--text-secondary);margin:0;">{question}</p>
        </div>
        <div style="text-align:right;">
            <div class="value-medium {ac}">{answer}</div>
            <div class="value-small text-secondary">{detail}</div>
        </div>
    </div>'''

def main():
    st.set_page_config(page_title="SPX Prophet", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
    apply_css()
    
    if "inputs" not in st.session_state:
        st.session_state.inputs = load_inputs()
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = None
    if "es_price" not in st.session_state:
        st.session_state.es_price = None
    if "es_candles" not in st.session_state:
        st.session_state.es_candles = None
    if "options_data" not in st.session_state:
        st.session_state.options_data = None
    
    # Sidebar
    with st.sidebar:
        st.markdown('''<div style="margin-bottom:24px;">
            <h1 style="font-family:'IBM Plex Mono',monospace;font-size:20px;font-weight:700;margin-bottom:4px;color:var(--text-primary);">SPX Prophet</h1>
            <p style="font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;">0DTE Trading System v2.2</p>
        </div>''', unsafe_allow_html=True)
        
        st.markdown('<div class="entry-badge">⏰ Entry Time: 9:00 AM CT</div>', unsafe_allow_html=True)
        
        # Trading Date Picker
        st.markdown('<div class="prophet-card-header" style="margin-top:16px;">Trading Date</div>', unsafe_allow_html=True)
        
        # Default to today, or saved date
        from datetime import date, timedelta as td
        today = datetime.now(CT).date()
        
        default_date = today
        if st.session_state.inputs.trading_date:
            try:
                default_date = datetime.strptime(st.session_state.inputs.trading_date, "%Y-%m-%d").date()
            except:
                pass
        
        # Quick select buttons
        st.markdown('<p style="font-size:11px;color:var(--text-muted);margin-bottom:8px;">Quick Select:</p>', unsafe_allow_html=True)
        qcol1, qcol2, qcol3, qcol4 = st.columns(4)
        
        # Find last Friday
        days_since_friday = (today.weekday() - 4) % 7
        if days_since_friday == 0 and datetime.now(CT).hour < 15:
            last_friday = today  # It's Friday before close
        else:
            last_friday = today - td(days=days_since_friday if days_since_friday > 0 else 7)
        
        # Find next Monday
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + td(days=days_until_monday)
        
        with qcol1:
            if st.button("Today", use_container_width=True, key="btn_today"):
                st.session_state.inputs.trading_date = today.strftime("%Y-%m-%d")
                st.session_state.options_data = None
                st.rerun()
        with qcol2:
            if st.button("Yesterday", use_container_width=True, key="btn_yesterday"):
                yesterday = today - td(days=1)
                st.session_state.inputs.trading_date = yesterday.strftime("%Y-%m-%d")
                st.session_state.options_data = None
                st.rerun()
        with qcol3:
            if st.button("Last Fri", use_container_width=True, key="btn_lastfri"):
                st.session_state.inputs.trading_date = last_friday.strftime("%Y-%m-%d")
                st.session_state.options_data = None
                st.rerun()
        with qcol4:
            if st.button("Next Mon", use_container_width=True, key="btn_nextmon"):
                st.session_state.inputs.trading_date = next_monday.strftime("%Y-%m-%d")
                st.session_state.options_data = None
                st.rerun()
        
        # Calendar date picker - click to open calendar
        # Allow selecting dates from 2024 to 2027 for backtesting
        min_date = date(2024, 1, 1)
        max_date = date(2027, 12, 31)
        
        trading_date = st.date_input(
            "📅 Click to open calendar",
            value=default_date,
            min_value=min_date,
            max_value=max_date,
            help="Click to open calendar picker - select any date from 2024-2027",
            key="trading_date_picker"
        )
        
        # Check if it's a weekend
        if trading_date.weekday() >= 5:
            st.warning("⚠️ Weekend selected - no trading")
        
        # Show day of week prominently
        day_name = trading_date.strftime("%A")
        st.markdown(f'<p style="font-size:14px;color:var(--gold);font-weight:600;">📆 {day_name}, {trading_date.strftime("%B %d, %Y")}</p>', unsafe_allow_html=True)
        
        trading_date_str = trading_date.strftime("%Y-%m-%d")
        
        st.markdown('<div class="prophet-card-header" style="margin-top:16px;">VIX Zone (TradingView)</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        vix_high = c1.number_input("ON High", value=st.session_state.inputs.vix_overnight_high, format="%.2f", step=0.01)
        vix_low = c2.number_input("ON Low", value=st.session_state.inputs.vix_overnight_low, format="%.2f", step=0.01)
        vix_current = st.number_input("VIX Current", value=st.session_state.inputs.vix_current, format="%.2f", step=0.01)
        
        st.markdown('<div class="prophet-card-header" style="margin-top:20px;">ES/SPX Offset</div>', unsafe_allow_html=True)
        offset = st.number_input("Offset (ES-SPX)", value=st.session_state.inputs.es_spx_offset, format="%.2f", step=0.5)
        
        st.markdown('<div class="prophet-card-header" style="margin-top:20px;">Prior Day</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        prior_high = c1.number_input("High", value=st.session_state.inputs.prior_high, format="%.0f", step=1.0)
        prior_low = c2.number_input("Low", value=st.session_state.inputs.prior_low, format="%.0f", step=1.0)
        prior_close = c3.number_input("Close", value=st.session_state.inputs.prior_close, format="%.0f", step=1.0)
        
        st.markdown('<div class="prophet-card-header" style="margin-top:20px;">Manual Structure</div>', unsafe_allow_html=True)
        use_manual = st.checkbox("Use manual CEILING/FLOOR", value=st.session_state.inputs.use_manual_structure)
        if use_manual:
            c1, c2 = st.columns(2)
            man_ceil = c1.number_input("CEILING", value=st.session_state.inputs.manual_ceiling, format="%.0f", step=1.0)
            man_floor = c2.number_input("FLOOR", value=st.session_state.inputs.manual_floor, format="%.0f", step=1.0)
        else:
            man_ceil, man_floor = 0.0, 0.0
        
        if st.button("💾 Save Inputs", use_container_width=True):
            st.session_state.inputs = ManualInputs(
                vix_overnight_high=vix_high, vix_overnight_low=vix_low, vix_current=vix_current,
                es_spx_offset=offset, prior_high=prior_high, prior_low=prior_low, prior_close=prior_close,
                manual_ceiling=man_ceil, manual_floor=man_floor, use_manual_structure=use_manual,
                trading_date=trading_date_str
            )
            save_inputs(st.session_state.inputs)
            st.session_state.options_data = None  # Reset options to fetch for new date
            st.success("Saved!")
        
        st.markdown("<hr>", unsafe_allow_html=True)
        api_key = st.text_input("Polygon API Key", value=POLYGON_API_KEY, type="password")
        if api_key:
            st.session_state.polygon_api_key = api_key
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.session_state.last_refresh = None
            st.session_state.options_data = None
            st.rerun()
    
    # Current inputs
    inputs = ManualInputs(
        vix_overnight_high=vix_high, vix_overnight_low=vix_low, vix_current=vix_current,
        es_spx_offset=offset, prior_high=prior_high, prior_low=prior_low, prior_close=prior_close,
        manual_ceiling=man_ceil if use_manual else 0, manual_floor=man_floor if use_manual else 0,
        use_manual_structure=use_manual, trading_date=trading_date_str
    )
    
    # Fetch data
    should_refresh = st.session_state.last_refresh is None or (datetime.now() - st.session_state.last_refresh).seconds > REFRESH_INTERVAL
    if should_refresh:
        with st.spinner("Fetching data..."):
            es_price = get_es_price_polygon() or get_es_price_yahoo()
            es_candles = get_es_candles_polygon() or get_es_candles_yahoo()
            st.session_state.es_price = es_price
            st.session_state.es_candles = es_candles
            st.session_state.last_refresh = datetime.now()
    
    es_price = st.session_state.es_price
    es_candles = st.session_state.es_candles
    spx_price = (es_price - inputs.es_spx_offset) if es_price and inputs.es_spx_offset else 0
    
    # Calculations
    ma = calculate_ma_bias(es_candles) if es_candles else MABias(0, 0, "NEUTRAL", "No data")
    struct = calculate_day_structure(es_candles, inputs.es_spx_offset, inputs.manual_ceiling, inputs.manual_floor, inputs.use_manual_structure) if es_candles else DayStructure(0,0,0,0)
    vix = calculate_vix_zone(inputs.vix_overnight_high, inputs.vix_overnight_low, inputs.vix_current)
    cones = calculate_cone_rails(inputs.prior_high, inputs.prior_low, inputs.prior_close, inputs.es_spx_offset)
    signal = calculate_trade_signal(ma, struct, vix, spx_price)
    
    # Fetch options for the CORRECT strike (15 OTM from entry level)
    # Strike is already calculated in signal as entry ± 15
    if signal.strike > 0 and st.session_state.options_data is None:
        opt_type = "call" if ma.bias == "LONG" else "put"
        st.session_state.options_data = get_spx_options_polygon(signal.strike, opt_type, trading_date_str)
    opts = st.session_state.options_data
    
    time_str, date_str, time_status = get_time_display()
    
    # Format trading date for display
    trading_date_display = trading_date.strftime("%a, %b %d")
    is_today = trading_date == datetime.now(CT).date()
    
    # Header
    c1, c2 = st.columns([2,1])
    with c1:
        src = f"ES {es_price:,.2f} − {inputs.es_spx_offset:.2f}" if es_price else "No data"
        st.markdown(f'''<div style="margin-bottom:24px;">
            <p style="font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">SPX</p>
            <span class="value-large">{spx_price:,.2f}</span>
            <p style="font-size:11px;color:var(--text-muted);margin-top:4px;">Auto: {src}</p>
        </div>''', unsafe_allow_html=True)
    with c2:
        sc = "text-green" if "Entry" in time_status else ("text-gold" if "RTH" in time_status else "text-muted")
        trading_label = "Today" if is_today else trading_date_display
        st.markdown(f'''<div style="text-align:right;margin-bottom:24px;">
            <p class="value-medium">{time_str}</p>
            <p style="font-size:13px;color:var(--text-secondary);margin-top:2px;">{date_str}</p>
            <p class="{sc}" style="font-size:11px;margin-top:8px;">{time_status}</p>
            <p style="font-size:11px;color:var(--gold);margin-top:4px;">📅 Trading: {trading_label}</p>
        </div>''', unsafe_allow_html=True)
    
    st.markdown("<hr style='margin:0 0 24px 0;border-color:var(--border);'>", unsafe_allow_html=True)
    
    # Pillars
    p1_s = "pass" if ma.bias in ["LONG","SHORT"] else "wait"
    p1 = render_pillar(1, "MA Bias", "Filter", "Can I trade CALLS or PUTS?", ma.bias,
                       f"50 EMA {ma.ema_50:,.0f} {'›' if ma.ema_50>ma.sma_200 else '‹'} 200 SMA {ma.sma_200:,.0f}", p1_s)
    
    if ma.bias == "LONG":
        p2_ans, p2_det = "FLOOR", f"{struct.floor_spx:,.0f} ({abs(spx_price-struct.floor_spx):.0f} away)"
    elif ma.bias == "SHORT":
        p2_ans, p2_det = "CEILING", f"{struct.ceiling_spx:,.0f} ({abs(struct.ceiling_spx-spx_price):.0f} away)"
    else:
        p2_ans, p2_det = "—", "Waiting for MA"
    if struct.is_manual:
        p2_det += " [Manual]"
    p2_s = "pass" if ma.bias != "NEUTRAL" and struct.floor_spx > 0 else "wait"
    p2 = render_pillar(2, "Day Structure", "Primary", "Entry level @ 9:00 AM CT?", p2_ans, p2_det, p2_s)
    
    if vix.timing_signal == "WAIT":
        p3_s = "wait"
    elif (ma.bias=="LONG" and vix.timing_signal=="CALLS") or (ma.bias=="SHORT" and vix.timing_signal=="PUTS"):
        p3_s = "pass"
    else:
        p3_s = "fail" if vix.timing_signal in ["CALLS","PUTS"] else "wait"
    p3 = render_pillar(3, "VIX Zone", "Timing", "Is NOW the right time?", vix.timing_signal, vix.zone_position, p3_s)
    
    st.markdown(f'<div style="margin-bottom:24px;">{p1}{p2}{p3}</div>', unsafe_allow_html=True)
    
    # Trade Decision
    if signal.direction == "CALLS":
        dc, dirc, disp = "ready", "text-green", "CALLS ✓"
    elif signal.direction == "PUTS":
        dc, dirc, disp = "ready", "text-red", "PUTS ✓"
    elif signal.direction == "WAIT":
        dc, dirc, disp = "waiting", "text-gold", "WAIT"
    else:
        dc, dirc, disp = "no-trade", "text-muted", "NO TRADE"
    
    suf = "C" if signal.direction in ["CALLS"] or (signal.direction=="WAIT" and ma.bias=="LONG") else ("P" if signal.direction in ["PUTS"] or (signal.direction=="WAIT" and ma.bias=="SHORT") else "")
    
    st.markdown(f'''<div class="trade-decision {dc}">
        <p style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:2px;margin-bottom:12px;">Trade Decision</p>
        <p style="font-family:'IBM Plex Mono',monospace;font-size:48px;font-weight:700;letter-spacing:-2px;margin-bottom:8px;" class="{dirc}">{disp}</p>
        <p style="font-size:13px;color:var(--text-secondary);">{signal.reason}</p>
        <div style="display:flex;justify-content:center;gap:40px;margin-top:24px;padding-top:24px;border-top:1px solid var(--border);">
            <div style="text-align:center;"><p style="font-size:11px;color:var(--text-muted);text-transform:uppercase;margin-bottom:4px;">Entry</p><p class="value-medium text-green">{signal.entry_level:,.0f}</p></div>
            <div style="text-align:center;"><p style="font-size:11px;color:var(--text-muted);text-transform:uppercase;margin-bottom:4px;">Strike</p><p class="value-medium text-green">{signal.strike} {suf}</p></div>
            <div style="text-align:center;"><p style="font-size:11px;color:var(--text-muted);text-transform:uppercase;margin-bottom:4px;">Distance</p><p class="value-medium">{signal.distance:.0f} pts</p></div>
            <div style="text-align:center;"><p style="font-size:11px;color:var(--text-muted);text-transform:uppercase;margin-bottom:4px;">Stop</p><p class="value-medium">50%</p></div>
        </div>
    </div>''', unsafe_allow_html=True)
    
    # Secondary panels
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'''<div class="prophet-card">
            <div class="prophet-card-header">Cone Rails @ 9:00 AM CT</div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
                <span style="font-size:13px;color:var(--text-secondary);">C1 (High {inputs.prior_high:,.0f})</span>
                <div style="display:flex;gap:16px;font-family:'IBM Plex Mono',monospace;font-size:13px;">
                    <span class="text-green">{cones.c1_ascending:,.0f} ↗</span>
                    <span class="text-red">{cones.c1_descending:,.0f} ↘</span>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
                <span style="font-size:13px;color:var(--text-secondary);">C2 (Low {inputs.prior_low:,.0f})</span>
                <div style="display:flex;gap:16px;font-family:'IBM Plex Mono',monospace;font-size:13px;">
                    <span class="text-green">{cones.c2_ascending:,.0f} ↗</span>
                    <span class="text-red">{cones.c2_descending:,.0f} ↘</span>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;">
                <span style="font-size:13px;color:var(--text-secondary);">C3 (Close {inputs.prior_close:,.0f})</span>
                <div style="display:flex;gap:16px;font-family:'IBM Plex Mono',monospace;font-size:13px;">
                    <span class="text-green">{cones.c3_ascending:,.0f} ↗</span>
                    <span class="text-red">{cones.c3_descending:,.0f} ↘</span>
                </div>
            </div>
            <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border);font-size:11px;color:var(--text-muted);">
                3pm→9am: {cones.blocks_elapsed:.0f} blocks | ±{cones.blocks_elapsed*CONE_SLOPE:.1f} pts
            </div>
        </div>''', unsafe_allow_html=True)
    
    with c2:
        if opts:
            st.markdown(f'''<div class="prophet-card">
                <div class="prophet-card-header">0DTE Options</div>
                <div style="font-size:11px;color:var(--text-muted);margin-bottom:12px;">{opts.ticker}</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                    <div style="background:var(--bg-deep);border-radius:8px;padding:14px;text-align:center;">
                        <p style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Strike</p>
                        <p class="value-medium text-green">{opts.strike} {opts.option_type[0].upper()}</p>
                    </div>
                    <div style="background:var(--bg-deep);border-radius:8px;padding:14px;text-align:center;">
                        <p style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Last</p>
                        <p class="value-medium">${opts.last:.2f}</p>
                    </div>
                    <div style="background:var(--bg-deep);border-radius:8px;padding:14px;text-align:center;">
                        <p style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Bid</p>
                        <p class="value-medium">${opts.bid:.2f}</p>
                    </div>
                    <div style="background:var(--bg-deep);border-radius:8px;padding:14px;text-align:center;">
                        <p style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Ask</p>
                        <p class="value-medium">${opts.ask:.2f}</p>
                    </div>
                </div>
                <div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:16px;font-size:11px;color:var(--text-muted);">
                    <div>Vol: {opts.volume:,}</div><div>OI: {opts.open_interest:,}</div>
                </div>
            </div>''', unsafe_allow_html=True)
        else:
            strike_d = f"{signal.strike} {suf}" if signal.strike > 0 else "—"
            msg = "Enter Polygon API key" if not get_polygon_api_key() else "No data available"
            st.markdown(f'''<div class="prophet-card">
                <div class="prophet-card-header">0DTE Options</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                    <div style="background:var(--bg-deep);border-radius:8px;padding:14px;text-align:center;">
                        <p style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Strike</p>
                        <p class="value-medium text-green">{strike_d}</p>
                    </div>
                    <div style="background:var(--bg-deep);border-radius:8px;padding:14px;text-align:center;">
                        <p style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Last</p><p class="value-medium">—</p>
                    </div>
                    <div style="background:var(--bg-deep);border-radius:8px;padding:14px;text-align:center;">
                        <p style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Bid</p><p class="value-medium">—</p>
                    </div>
                    <div style="background:var(--bg-deep);border-radius:8px;padding:14px;text-align:center;">
                        <p style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Ask</p><p class="value-medium">—</p>
                    </div>
                </div>
                <div style="margin-top:12px;font-size:11px;color:var(--text-muted);">{msg}</div>
            </div>''', unsafe_allow_html=True)
    
    # Economic Calendar
    st.markdown('''<div class="prophet-card" style="margin-top:20px;">
        <div class="prophet-card-header">📅 Economic Calendar (Today)</div>
    ''', unsafe_allow_html=True)
    
    econ_events = get_economic_calendar()
    if econ_events:
        events_html = ""
        for event in econ_events:
            # Impact color
            if event.impact == "HIGH":
                impact_color = "text-red"
                impact_icon = "🔴"
            elif event.impact == "MEDIUM":
                impact_color = "text-gold"
                impact_icon = "🟡"
            else:
                impact_color = "text-muted"
                impact_icon = "⚪"
            
            events_html += f'''
            <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-secondary);min-width:70px;">{event.time}</span>
                    <span>{impact_icon}</span>
                    <span style="font-size:13px;color:var(--text-primary);">{event.name}</span>
                </div>
                <div style="display:flex;gap:16px;font-family:'IBM Plex Mono',monospace;font-size:11px;">
                    <span style="color:var(--text-muted);">F: {event.forecast}</span>
                    <span style="color:var(--text-muted);">P: {event.previous}</span>
                </div>
            </div>'''
        
        st.markdown(events_html + '</div>', unsafe_allow_html=True)
    else:
        st.markdown('''
            <div style="padding:16px;text-align:center;color:var(--text-muted);font-size:13px;">
                No major economic events scheduled
            </div>
        </div>''', unsafe_allow_html=True)
    
    # Footer
    st.markdown("<hr style='margin:24px 0;border-color:var(--border);'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        last = st.session_state.last_refresh.strftime("%I:%M %p") if st.session_state.last_refresh else "Never"
        nxt = (st.session_state.last_refresh + timedelta(seconds=REFRESH_INTERVAL)).strftime("%I:%M %p") if st.session_state.last_refresh else "—"
        api_s = "● Connected" if get_polygon_api_key() else "○ No API Key"
        api_c = "text-green" if get_polygon_api_key() else "text-muted"
        st.markdown(f'''<div style="display:flex;align-items:center;gap:16px;">
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="width:8px;height:8px;border-radius:50%;background:var(--green);"></span>
                <span style="font-size:12px;color:var(--text-muted);">Auto-refresh: 15 min</span>
            </div>
            <div class="{api_c}" style="font-size:12px;">Polygon: {api_s}</div>
        </div>''', unsafe_allow_html=True)
    with c2:
        st.markdown(f'''<div style="text-align:right;font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--text-muted);">
            Last: {last} · Next: {nxt}
        </div>''', unsafe_allow_html=True)

if __name__ == "__main__":
    main()

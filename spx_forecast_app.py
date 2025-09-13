import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta, time as dt_time
import pytz
from typing import List, Dict, Tuple, Optional, Callable
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="SPX Prophet",
    page_icon="📈",
    layout="wide"
)

# Constants
CT_TZ = pytz.timezone('America/Chicago')
BLOCK_MINUTES = 30

# Initialize session state
if 'slopes' not in st.session_state:
    st.session_state.slopes = {
        'spx_baseline': -0.25,
        'spx_skyline': 0.31,
        'contract_weekday': -0.30,
        'contract_frimon': -0.10,
        'contract_skyline': 0.15
    }

if 'strike_freeze' not in st.session_state:
    st.session_state.strike_freeze = False

if 'manual_strike' not in st.session_state:
    st.session_state.manual_strike = None

# Helper Functions
def get_previous_business_day(date: datetime) -> datetime:
    """Get the previous business day"""
    while date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        date -= timedelta(days=1)
    return date - timedelta(days=1)

def is_friday_to_monday(anchor_time: datetime, target_time: datetime) -> bool:
    """Check if timespan crosses from Friday to Monday"""
    return anchor_time.weekday() == 4 and target_time.weekday() == 0

def count_blocks_clock(t1: datetime, t2: datetime) -> int:
    """Count 30-min blocks excluding maintenance hour 16:00-17:00 CT"""
    if t2 <= t1:
        return 0
    
    current = t1
    blocks = 0
    
    while current < t2:
        next_block = current + timedelta(minutes=BLOCK_MINUTES)
        
        # Skip maintenance hour 16:00-17:00 CT
        if not (current.hour == 16 and current.minute == 0):
            if next_block <= t2:
                blocks += 1
            elif current < t2:  # Partial block
                blocks += 1
                break
        
        current = next_block
        
        # Skip over maintenance hour
        if current.hour == 16 and current.minute == 0:
            current = current.replace(hour=17, minute=0)
    
    return blocks

def count_blocks_active_contract(t1: datetime, t2: datetime) -> int:
    """Count active trading blocks excluding 15:30-19:00 daily and Fri 15:30 → Sun 19:00"""
    if t2 <= t1:
        return 0
    
    current = t1
    blocks = 0
    
    while current < t2:
        next_block = current + timedelta(minutes=BLOCK_MINUTES)
        
        # Check if current time is in active trading window
        is_active = True
        
        # Daily exclusion: 15:30-19:00
        if current.hour >= 15 and (current.hour < 19 or (current.hour == 15 and current.minute >= 30)):
            is_active = False
        
        # Friday 15:30 → Sunday 19:00
        if current.weekday() == 4 and current.hour >= 15 and current.minute >= 30:
            is_active = False
        elif current.weekday() in [5, 6]:  # Saturday, Sunday
            is_active = False
        elif current.weekday() == 0 and current.hour < 19:  # Sunday before 19:00
            is_active = False
        
        if is_active:
            if next_block <= t2:
                blocks += 1
            elif current < t2:  # Partial block
                blocks += 1
                break
        
        current = next_block
    
    return blocks

def build_rth_times(date: datetime, start: str = "08:30", end: str = "14:00", 
                   tz: str = "America/Chicago") -> List[datetime]:
    """Build RTH times for given date"""
    timezone = pytz.timezone(tz)
    start_hour, start_min = map(int, start.split(':'))
    end_hour, end_min = map(int, end.split(':'))
    
    start_dt = timezone.localize(date.replace(hour=start_hour, minute=start_min, second=0, microsecond=0))
    end_dt = timezone.localize(date.replace(hour=end_hour, minute=end_min, second=0, microsecond=0))
    
    times = []
    current = start_dt
    while current <= end_dt:
        times.append(current)
        current += timedelta(minutes=BLOCK_MINUTES)
    
    return times

def slope_from_points(v1: float, t1: datetime, v2: float, t2: datetime, 
                     count_fn: Callable) -> float:
    """Calculate slope between two points"""
    blocks = count_fn(t1, t2)
    if blocks == 0:
        return 0
    return (v2 - v1) / blocks

def project(v0: float, t0: datetime, t_target: datetime, slope: float, 
           count_fn: Callable) -> float:
    """Project value using slope and block count"""
    blocks = count_fn(t0, t_target)
    return v0 + slope * blocks

def fetch_data_online(symbol: str, period: str = "5d", interval: str = "1m") -> Optional[pd.DataFrame]:
    """Fetch data from yfinance with error handling"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        if data.empty:
            return None
        
        # Convert to CT timezone
        data.index = data.index.tz_convert(CT_TZ)
        return data
    except Exception as e:
        st.warning(f"Failed to fetch {symbol}: {str(e)}")
        return None

def resample_to_30min(data: pd.DataFrame) -> pd.DataFrame:
    """Resample 1-minute data to 30-minute bars"""
    if data is None or data.empty:
        return None
    
    resampled = data.resample('30T').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    
    return resampled

def get_closest_itm_strike(price: float, strike_spacing: float = 5.0) -> float:
    """Get closest ITM call strike"""
    return strike_spacing * np.floor(price / strike_spacing)

def round_to_nickel(price: float) -> float:
    """Round to nearest $0.05"""
    return max(0.05, round(price * 20) / 20)

def calculate_es_spx_offset(es_data: pd.DataFrame, spx_data: pd.DataFrame, 
                          target_time: datetime) -> Optional[float]:
    """Calculate ES→SPX offset at specific time"""
    try:
        # Find closest time match
        es_close = es_data.loc[es_data.index.get_indexer([target_time], method='nearest')[0], 'Close']
        spx_close = spx_data.loc[spx_data.index.get_indexer([target_time], method='nearest')[0], 'Close']
        return es_close - spx_close
    except:
        return None

# Data fetching and processing
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_market_data():
    """Fetch and process market data"""
    data = {}
    
    # Fetch SPX and ES data
    spx_data = fetch_data_online("^GSPC")
    es_data = fetch_data_online("ES=F")
    
    if spx_data is not None:
        data['spx_raw'] = spx_data
        data['spx_30m'] = resample_to_30min(spx_data)
    
    if es_data is not None:
        data['es_raw'] = es_data
        data['es_30m'] = resample_to_30min(es_data)
    
    return data

def create_spx_table(anchor_value: float, anchor_time: datetime, anchor_name: str,
                    projection_date: datetime, slopes: dict, count_fn: Callable,
                    spx_source: str, offset: float = None) -> pd.DataFrame:
    """Create SPX projection table"""
    # Build RTH times
    rth_times = build_rth_times(projection_date, "08:30", "14:00")
    
    # Calculate projections
    baseline_slope = slopes['spx_baseline']
    skyline_slope = slopes['spx_skyline']
    
    rows = []
    for rth_time in rth_times:
        baseline_val = project(anchor_value, anchor_time, rth_time, baseline_slope, count_fn)
        skyline_val = project(anchor_value, anchor_time, rth_time, skyline_slope, count_fn)
        
        rows.append({
            'Time': rth_time.strftime('%H:%M'),
            'Baseline': round(baseline_val, 2),
            'Skyline': round(skyline_val, 2)
        })
    
    df = pd.DataFrame(rows)
    
    # Add metadata
    first_rth = rth_times[0]
    blocks_to_start = count_fn(anchor_time, first_rth)
    
    df.attrs['anchor_name'] = anchor_name
    df.attrs['anchor_value'] = anchor_value
    df.attrs['anchor_time'] = anchor_time
    df.attrs['blocks_to_start'] = blocks_to_start
    df.attrs['baseline_slope'] = baseline_slope
    df.attrs['skyline_slope'] = skyline_slope
    df.attrs['spx_source'] = spx_source
    df.attrs['offset'] = offset
    
    return df

def create_contract_table(anchor_value: float, anchor_time: datetime, strike: float,
                         projection_date: datetime, slopes: dict, count_fn: Callable) -> pd.DataFrame:
    """Create contract projection table"""
    # Build contract RTH times
    rth_times = build_rth_times(projection_date, "07:00", "14:30")
    
    # Determine regime
    is_frimon = is_friday_to_monday(anchor_time, rth_times[0])
    entry_slope = slopes['contract_frimon'] if is_frimon else slopes['contract_weekday']
    exit_slope = slopes['contract_skyline']
    
    rows = []
    for rth_time in rth_times:
        entry_val = project(anchor_value, anchor_time, rth_time, entry_slope, count_fn)
        exit_val = project(anchor_value, anchor_time, rth_time, exit_slope, count_fn)
        
        # Apply minimum price and rounding
        entry_val = round_to_nickel(max(0.05, entry_val))
        exit_val = round_to_nickel(max(0.05, exit_val))
        
        rows.append({
            'Time': rth_time.strftime('%H:%M'),
            'Entry': entry_val,
            'Exit': exit_val
        })
    
    df = pd.DataFrame(rows)
    
    # Add metadata
    first_rth = rth_times[0]
    blocks_to_start = count_fn(anchor_time, first_rth)
    
    df.attrs['strike'] = strike
    df.attrs['anchor_value'] = anchor_value
    df.attrs['anchor_time'] = anchor_time
    df.attrs['blocks_to_start'] = blocks_to_start
    df.attrs['entry_slope'] = entry_slope
    df.attrs['exit_slope'] = exit_slope
    df.attrs['regime'] = 'Fri→Mon' if is_frimon else 'Weekday'
    
    return df

def simple_fan_signals(spx_data: pd.DataFrame, baseline_values: List[float], 
                      skyline_values: List[float], times: List[datetime]) -> pd.DataFrame:
    """Simple fan touch logic"""
    signals = []
    
    if spx_data is None or spx_data.empty:
        return pd.DataFrame(signals)
    
    for i, time_point in enumerate(times):
        try:
            # Find closest SPX candle
            closest_idx = spx_data.index.get_indexer([time_point], method='nearest')[0]
            candle = spx_data.iloc[closest_idx]
            
            baseline = baseline_values[i]
            skyline = skyline_values[i]
            
            # Check touches
            touches_skyline = candle['Low'] <= skyline <= candle['High']
            touches_baseline = candle['Low'] <= baseline <= candle['High']
            
            if touches_skyline:
                if candle['Close'] > skyline:
                    signals.append({
                        'Time': time_point.strftime('%H:%M'),
                        'Rule': 'SKY-TOUCH',
                        'Context': f"Close above skyline ({skyline:.2f})",
                        'Signal': 'Bullish continuation',
                        'Target': 'Monitor for bearish return'
                    })
                else:
                    signals.append({
                        'Time': time_point.strftime('%H:%M'),
                        'Rule': 'SKY-REJECT',
                        'Context': f"Close below skyline ({skyline:.2f})",
                        'Signal': 'Bearish reversal',
                        'Target': f'Baseline ({baseline:.2f})'
                    })
            
            if touches_baseline:
                if candle['Close'] < baseline:
                    signals.append({
                        'Time': time_point.strftime('%H:%M'),
                        'Rule': 'BASE-TOUCH',
                        'Context': f"Close below baseline ({baseline:.2f})",
                        'Signal': 'Bearish continuation',
                        'Target': 'Monitor for bullish return'
                    })
                else:
                    signals.append({
                        'Time': time_point.strftime('%H:%M'),
                        'Rule': 'BASE-BOUNCE',
                        'Context': f"Close above baseline ({baseline:.2f})",
                        'Signal': 'Bullish reversal',
                        'Target': f'Skyline ({skyline:.2f})'
                    })
                    
        except (IndexError, KeyError):
            continue
    
    return pd.DataFrame(signals)

# Main Streamlit App
def main():
    st.title("📈 SPX Prophet")
    st.markdown("**Dual-mode Online/Manual SPX & Options Projections**")
    
    # Current time
    now_ct = datetime.now(CT_TZ)
    
    # Header status
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Current Time (CT)", now_ct.strftime('%H:%M:%S'))
    
    with col2:
        is_market_open = (now_ct.weekday() < 5 and 
                         dt_time(8, 30) <= now_ct.time() <= dt_time(14, 0))
        st.metric("Market Status", "🟢 OPEN" if is_market_open else "🔴 CLOSED")
    
    with col3:
        slopes = st.session_state.slopes
        st.metric("SPX Slopes", f"B: {slopes['spx_baseline']}, S: {slopes['spx_skyline']}")
    
    with col4:
        st.metric("Contract Slopes", f"W: {slopes['contract_weekday']}, F: {slopes['contract_frimon']}")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Data Mode
        data_mode = st.selectbox("Data Mode", ["Online", "Manual"], key="data_mode")
        
        # Dates
        st.subheader("📅 Dates")
        projection_date = st.date_input("Projection Date", value=now_ct.date())
        previous_date = st.date_input("Previous Trading Day", 
                                    value=get_previous_business_day(now_ct).date())
        
        # SPX Source (when Online)
        if data_mode == "Online":
            st.subheader("📊 SPX Source")
            spx_source = st.selectbox("Source Mode", ["ES→SPX", "SPX Direct"])
            
            if spx_source == "ES→SPX":
                rth_threshold = st.number_input("RTH Override Threshold", 
                                              value=2.0, min_value=0.1, step=0.1,
                                              help="Switch to live offset if deviation > threshold")
        else:
            spx_source = "Manual"
            rth_threshold = None
        
        # Slopes
        st.subheader("📈 Slopes")
        st.session_state.slopes['spx_baseline'] = st.number_input(
            "SPX Baseline", value=st.session_state.slopes['spx_baseline'], step=0.01)
        st.session_state.slopes['spx_skyline'] = st.number_input(
            "SPX Skyline", value=st.session_state.slopes['spx_skyline'], step=0.01)
        st.session_state.slopes['contract_weekday'] = st.number_input(
            "Contract Weekday", value=st.session_state.slopes['contract_weekday'], step=0.01)
        st.session_state.slopes['contract_frimon'] = st.number_input(
            "Contract Fri→Mon", value=st.session_state.slopes['contract_frimon'], step=0.01)
        st.session_state.slopes['contract_skyline'] = st.number_input(
            "Contract Skyline", value=st.session_state.slopes['contract_skyline'], step=0.01)
        
        # Contract Settings
        st.subheader("📋 Contract")
        st.session_state.strike_freeze = st.checkbox("Freeze Strike for Session", 
                                                    value=st.session_state.strike_freeze)
        
        strike_spacing = st.number_input("Strike Spacing", value=5.0, min_value=1.0)
        
        if st.button("🔄 Reset All Settings"):
            for key in ['slopes', 'strike_freeze', 'manual_strike']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # Get data based on mode
    if data_mode == "Online":
        with st.spinner("Fetching market data..."):
            market_data = get_market_data()
        
        if not market_data:
            st.error("Failed to fetch market data. Please switch to Manual mode.")
            return
            
        # Process data based on SPX source
        if spx_source == "ES→SPX" and 'es_30m' in market_data and 'spx_30m' in market_data:
            es_data = market_data['es_30m']
            spx_data = market_data['spx_30m']
            
            # Calculate prior day offset
            prev_day_dt = CT_TZ.localize(datetime.combine(previous_date, dt_time(14, 30)))
            prior_offset = calculate_es_spx_offset(es_data, spx_data, prev_day_dt)
            
            if prior_offset is not None:
                st.info(f"Using ES→SPX with prior 14:30 offset: {prior_offset:.2f}")
                # For now, use ES data with offset (simplified)
                active_spx_data = es_data.copy()
                active_spx_data[['Open', 'High', 'Low', 'Close']] -= prior_offset
            else:
                st.warning("Could not calculate ES→SPX offset, falling back to SPX direct")
                active_spx_data = spx_data
                
        elif 'spx_30m' in market_data:
            active_spx_data = market_data['spx_30m']
            prior_offset = None
        else:
            st.error("No SPX data available")
            return
            
        # Extract anchor values
        try:
            prev_day_close_time = CT_TZ.localize(datetime.combine(previous_date, dt_time(15, 0)))
            prev_day_1430_time = CT_TZ.localize(datetime.combine(previous_date, dt_time(14, 30)))
            
            # Get previous day data
            prev_data = active_spx_data[active_spx_data.index.date == previous_date]
            
            if prev_data.empty:
                st.error(f"No data available for {previous_date}")
                return
            
            # SPX anchors
            spx_close_anchor = prev_data.loc[prev_data.index.get_indexer([prev_day_close_time], method='nearest')[0], 'Close']
            spx_high_anchor = prev_data['High'].max()
            spx_low_anchor = prev_data['Low'].min()
            spx_high_time = prev_data['High'].idxmax()
            spx_low_time = prev_data['Low'].idxmin()
            
            # Contract anchor (15:30 high)
            contract_anchor_time = CT_TZ.localize(datetime.combine(previous_date, dt_time(15, 30)))
            try:
                contract_anchor = prev_data.loc[prev_data.index.get_indexer([contract_anchor_time], method='nearest')[0], 'High']
            except:
                contract_anchor = spx_high_anchor  # Fallback
                
        except Exception as e:
            st.error(f"Error processing data: {str(e)}")
            return
            
    else:
        # Manual mode
        st.subheader("📝 Manual Data Entry")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**SPX Previous Day**")
            spx_close_anchor = st.number_input("14:30 Close", value=6500.0, step=0.1)
            spx_high_anchor = st.number_input("High", value=6520.0, step=0.1)
            spx_low_anchor = st.number_input("Low", value=6480.0, step=0.1)
        
        with col2:
            st.write("**Contract Previous Session**")
            contract_anchor = st.number_input("15:30 Candle High", value=25.50, step=0.05)
        
        # Mock times for manual mode
        spx_high_time = CT_TZ.localize(datetime.combine(previous_date, dt_time(11, 0)))
        spx_low_time = CT_TZ.localize(datetime.combine(previous_date, dt_time(13, 0)))
        contract_anchor_time = CT_TZ.localize(datetime.combine(previous_date, dt_time(15, 30)))
        
        active_spx_data = None
        prior_offset = None
    
    # Calculate strike
    strike = get_closest_itm_strike(spx_close_anchor, strike_spacing)
    
    if st.session_state.strike_freeze and st.session_state.manual_strike:
        strike = st.session_state.manual_strike
    else:
        st.session_state.manual_strike = strike
    
    # Display current settings
    st.info(f"**Data Mode:** {data_mode} | **SPX Source:** {spx_source} | **Strike:** {strike} | **Offset:** {prior_offset:.2f if prior_offset else 'N/A'}")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 SPX Projections", "📋 Contract Table", "🎯 Fan Signals", "📋 Plan Card"])
    
    # Tab 1: SPX Projections
    with tab1:
        st.header("SPX Baseline/Skyline Projections")
        
        # Create anchor times
        spx_close_time = CT_TZ.localize(datetime.combine(previous_date, dt_time(15, 0)))
        projection_dt = datetime.combine(projection_date, dt_time(0, 0))
        projection_dt = CT_TZ.localize(projection_dt)
        
        # High anchor table
        st.subheader("🔺 High Anchor Table")
        high_table = create_spx_table(
            spx_high_anchor, spx_high_time, "High", 
            projection_dt, st.session_state.slopes, 
            count_blocks_clock, spx_source, prior_offset
        )
        
        # Display metadata
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Anchor", f"{high_table.attrs['anchor_value']:.2f} @ {high_table.attrs['anchor_time'].strftime('%H:%M')}")
        with col2:
            st.metric("Blocks to 08:30", high_table.attrs['blocks_to_start'])
        with col3:
            st.metric("Slopes", f"B: {high_table.attrs['baseline_slope']}, S: {high_table.attrs['skyline_slope']}")
        with col4:
            st.metric("Mode", "Clock (maint excl.)")
        
        st.dataframe(high_table, use_container_width=True)
        
        if st.button("📥 Export High Table CSV", key="export_high"):
            csv = high_table.to_csv(index=False)
            st.download_button("Download CSV", csv, "spx_high_projections.csv", "text/csv")
        
        # Close anchor table
        st.subheader("🎯 Close Anchor Table")
        close_table = create_spx_table(
            spx_close_anchor, spx_close_time, "Close",
            projection_dt, st.session_state.slopes,
            count_blocks_clock, spx_source, prior_offset
        )
        
        # Display metadata
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Anchor", f"{close_table.attrs['anchor_value']:.2f} @ 15:00")
        with col2:
            st.metric("Blocks to 08:30", close_table.attrs['blocks_to_start'])
        with col3:
            st.metric("Slopes", f"B: {close_table.attrs['baseline_slope']}, S: {close_table.attrs['skyline_slope']}")
        with col4:
            st.metric("Mode", "Clock (maint excl.)")
        
        st.dataframe(close_table, use_container_width=True)
        
        if st.button("📥 Export Close Table CSV", key="export_close"):
            csv = close_table.to_csv(index=False)
            st.download_button("Download CSV", csv, "spx_close_projections.csv", "text/csv")
        
        # Low anchor table
        st.subheader("🔻 Low Anchor Table")
        low_table = create_spx_table(
            spx_low_anchor, spx_low_time, "Low",
            projection_dt, st.session_state.slopes,
            count_blocks_clock, spx_source, prior_offset
        )
        
        # Display metadata
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Anchor", f"{low_table.attrs['anchor_value']:.2f} @ {low_table.attrs['anchor_time'].strftime('%H:%M')}")
        with col2:
            st.metric("Blocks to 08:30", low_table.attrs['blocks_to_start'])
        with col3:
            st.metric("Slopes", f"B: {low_table.attrs['baseline_slope']}, S: {low_table.attrs['skyline_slope']}")
        with col4:
            st.metric("Mode", "Clock (maint excl.)")
        
        st.dataframe(low_table, use_container_width=True)
        
        if st.button("📥 Export Low Table CSV", key="export_low"):
            csv = low_table.to_csv(index=False)
            st.download_button("Download CSV", csv, "spx_low_projections.csv", "text/csv")
    
    # Tab 2: Contract Table
    with tab2:
        st.header(f"Contract Projections - {strike}C")
        
        contract_table = create_contract_table(
            contract_anchor, contract_anchor_time, strike,
            projection_dt, st.session_state.slopes,
            count_blocks_active_contract
        )
        
        # Display metadata
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Strike", f"{contract_table.attrs['strike']}")
        with col2:
            st.metric("Regime", contract_table.attrs['regime'])
        with col3:
            st.metric("Blocks to 07:00", contract_table.attrs['blocks_to_start'])
        with col4:
            st.metric("Mode", "Active Trading")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Entry Slope", contract_table.attrs['entry_slope'])
        with col2:
            st.metric("Exit Slope", contract_table.attrs['exit_slope'])
        
        st.dataframe(contract_table, use_container_width=True)
        
        if st.button("📥 Export Contract CSV"):
            csv = contract_table.to_csv(index=False)
            st.download_button("Download CSV", csv, f"contract_{strike}_projections.csv", "text/csv")
    
    # Tab 3: Fan Signals
    with tab3:
        st.header("Fan Touch Signals")
        
        if data_mode == "Online" and active_spx_data is not None:
            # Use close anchor for fan signals
            rth_times = build_rth_times(projection_dt, "08:30", "14:00")
            baseline_values = [project(spx_close_anchor, spx_close_time, t, 
                                     st.session_state.slopes['spx_baseline'], 
                                     count_blocks_clock) for t in rth_times]
            skyline_values = [project(spx_close_anchor, spx_close_time, t,
                                    st.session_state.slopes['spx_skyline'],
                                    count_blocks_clock) for t in rth_times]
            
            signals_df = simple_fan_signals(active_spx_data, baseline_values, skyline_values, rth_times)
            
            if not signals_df.empty:
                st.dataframe(signals_df, use_container_width=True)
            else:
                st.info("No fan signals detected for current session")
        else:
            st.info("Fan signals require Online mode with live data")
    
    # Tab 4: Plan Card
    with tab4:
        st.header("Trading Plan Card")
        
        key_times = ["08:30", "10:00", "12:00", "14:00"]
        plan_data = []
        
        for time_str in key_times:
            hour, minute = map(int, time_str.split(':'))
            target_time = CT_TZ.localize(projection_dt.replace(hour=hour, minute=minute))
            
            # SPX levels (using close anchor)
            spx_baseline = project(spx_close_anchor, spx_close_time, target_time,
                                 st.session_state.slopes['spx_baseline'], count_blocks_clock)
            spx_skyline = project(spx_close_anchor, spx_close_time, target_time,
                                st.session_state.slopes['spx_skyline'], count_blocks_clock)
            
            # Contract levels
            is_frimon = is_friday_to_monday(contract_anchor_time, target_time)
            contract_slope = st.session_state.slopes['contract_frimon'] if is_frimon else st.session_state.slopes['contract_weekday']
            
            contract_entry = round_to_nickel(project(contract_anchor, contract_anchor_time, target_time,
                                                   contract_slope, count_blocks_active_contract))
            contract_exit = round_to_nickel(project(contract_anchor, contract_anchor_time, target_time,
                                                  st.session_state.slopes['contract_skyline'], count_blocks_active_contract))
            
            plan_data.append({
                'Time': time_str,
                'SPX Baseline': round(spx_baseline, 2),
                'SPX Skyline': round(spx_skyline, 2),
                f'{strike}C Entry': contract_entry,
                f'{strike}C Exit': contract_exit
            })
        
        plan_df = pd.DataFrame(plan_data)
        st.dataframe(plan_df, use_container_width=True)
        
        if st.button("📥 Export Plan CSV"):
            csv = plan_df.to_csv(index=False)
            st.download_button("Download CSV", csv, "trading_plan.csv", "text/csv")
    
    # Footer
    st.markdown("---")
    st.markdown("**SPX Prophet** | Built with Streamlit | Market data via yfinance")

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dt_time
import pytz
from typing import List, Dict, Tuple, Optional, Callable
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="SPX Prophet",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for light mode glassmorphism design
st.markdown("""
<style>
    /* Import Inter font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styles */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Main container glassmorphism */
    .main .block-container {
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(20px);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.4);
        padding: 2rem;
        margin-top: 1rem;
    }
    
    /* Card styling */
    .glass-card {
        background: rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(15px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.4);
        box-shadow: 
            0 4px 16px rgba(0, 0, 0, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 
            0 8px 24px rgba(0, 0, 0, 0.12),
            inset 0 1px 0 rgba(255, 255, 255, 0.4);
    }
    
    /* Header styling */
    .main-header {
        text-align: center;
        background: rgba(255, 255, 255, 0.35);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
    }
    
    .main-header h1 {
        background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    
    .main-header p {
        color: #34495e;
        font-size: 1.2rem;
        font-weight: 500;
        margin: 0;
    }
    
    /* Metric cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        padding: 1rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        background: rgba(255, 255, 255, 0.5);
        transform: translateY(-1px);
    }
    
    .metric-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
        display: block;
    }
    
    .metric-label {
        color: #5a6c7d;
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 0.3rem;
    }
    
    .metric-value {
        color: #2c3e50;
        font-size: 1.1rem;
        font-weight: 600;
    }
    
    /* Input section styling */
    .input-section {
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(15px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .input-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
        color: #2c3e50;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .input-icon {
        font-size: 1.5rem;
        margin-right: 0.5rem;
    }
    
    /* Table styling */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.4);
        overflow: hidden;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    /* Button styling */
    .stButton button {
        background: rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.4);
        border-radius: 10px;
        color: #2c3e50;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        background: rgba(255, 255, 255, 0.5);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: #5a6c7d;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: rgba(255, 255, 255, 0.4);
        color: #2c3e50;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Success/Info styling */
    .stSuccess {
        background: rgba(76, 175, 80, 0.15);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(76, 175, 80, 0.3);
        border-radius: 10px;
    }
    
    .stInfo {
        background: rgba(33, 150, 243, 0.15);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(33, 150, 243, 0.3);
        border-radius: 10px;
    }
    
    /* Text styling */
    h1, h2, h3, h4, h5, h6 {
        color: #2c3e50 !important;
        font-weight: 600 !important;
    }
    
    p, span, div {
        color: #34495e !important;
    }
    
    /* Specific metric styling */
    [data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(15px);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.4);
        padding: 1rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    }
    
    /* Input field styling */
    .stNumberInput > div > div > input {
        background: rgba(255, 255, 255, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 8px !important;
        color: #2c3e50 !important;
    }
    
    .stSelectbox > div > div > div {
        background: rgba(255, 255, 255, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 8px !important;
        color: #2c3e50 !important;
    }
    
    .stDateInput > div > div > input {
        background: rgba(255, 255, 255, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 8px !important;
        color: #2c3e50 !important;
    }
</style>
""", unsafe_allow_html=True)

# Constants
CT_TZ = pytz.timezone('America/Chicago')
BLOCK_MINUTES = 30

# Initialize session state
def init_session_state():
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
    
    # Convert to naive datetime if timezone-aware
    if date.tzinfo is not None:
        date = date.replace(tzinfo=None)
    
    start_dt = timezone.localize(date.replace(hour=start_hour, minute=start_min, second=0, microsecond=0))
    end_dt = timezone.localize(date.replace(hour=end_hour, minute=end_min, second=0, microsecond=0))
    
    times = []
    current = start_dt
    while current <= end_dt:
        times.append(current)
        current += timedelta(minutes=BLOCK_MINUTES)
    
    return times

def project(v0: float, t0: datetime, t_target: datetime, slope: float, 
           count_fn: Callable) -> float:
    """Project value using slope and block count"""
    blocks = count_fn(t0, t_target)
    return v0 + slope * blocks

def get_closest_itm_strike(price: float, strike_spacing: float = 5.0) -> float:
    """Get closest ITM call strike"""
    return strike_spacing * np.floor(price / strike_spacing)

def round_to_nickel(price: float) -> float:
    """Round to nearest $0.05"""
    return max(0.05, round(price * 20) / 20)

def create_spx_table(anchor_value: float, anchor_time: datetime, anchor_name: str,
                    projection_date: datetime, slopes: dict, count_fn: Callable) -> pd.DataFrame:
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

def render_metric_card(icon: str, label: str, value: str, key: str = None):
    """Render a beautiful metric card"""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-icon">{icon}</div>
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def render_input_section(icon: str, title: str, content_func):
    """Render a glassmorphism input section"""
    st.markdown(f"""
    <div class="input-section">
        <div class="input-header">
            <span class="input-icon">{icon}</span>
            {title}
        </div>
    </div>
    """, unsafe_allow_html=True)
    content_func()

# Main Streamlit App
def main():
    init_session_state()
    
    # Custom header
    st.markdown("""
    <div class="main-header">
        <h1>📈 SPX Prophet</h1>
        <p>Professional SPX & Options Projection Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Current time and status
    now_ct = datetime.now(CT_TZ)
    is_market_open = (now_ct.weekday() < 5 and 
                     dt_time(8, 30) <= now_ct.time() <= dt_time(14, 0))
    
    # Status metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_metric_card("🕒", "Current Time (CT)", now_ct.strftime('%H:%M:%S'))
    
    with col2:
        market_status = "🟢 OPEN" if is_market_open else "🔴 CLOSED"
        render_metric_card("📊", "Market Status", market_status)
    
    with col3:
        slopes = st.session_state.slopes
        spx_slopes = f"B: {slopes['spx_baseline']}, S: {slopes['spx_skyline']}"
        render_metric_card("📈", "SPX Slopes", spx_slopes)
    
    with col4:
        contract_slopes = f"W: {slopes['contract_weekday']}, F: {slopes['contract_frimon']}"
        render_metric_card("📋", "Contract Slopes", contract_slopes)
    
    # Sidebar Configuration
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem; background: rgba(255,255,255,0.3); border-radius: 12px; margin-bottom: 1rem;">
            <h2 style="margin: 0; color: #2c3e50;">⚙️ Configuration</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Dates section
        st.markdown("### 📅 Trading Dates")
        projection_date = st.date_input(
            "Projection Date", 
            value=now_ct.date(),
            help="The date for which to generate projections"
        )
        previous_date = st.date_input(
            "Previous Trading Day", 
            value=get_previous_business_day(now_ct).date(),
            help="The previous business day for anchor values"
        )
        
        # Slopes configuration
        st.markdown("### 📈 Slope Configuration")
        
        with st.expander("📊 SPX Slopes", expanded=True):
            st.session_state.slopes['spx_baseline'] = st.number_input(
                "🔻 Baseline (entries)", 
                value=st.session_state.slopes['spx_baseline'], 
                step=0.01,
                help="Negative slope for SPX entry levels"
            )
            st.session_state.slopes['spx_skyline'] = st.number_input(
                "🔺 Skyline (exits)", 
                value=st.session_state.slopes['spx_skyline'], 
                step=0.01,
                help="Positive slope for SPX exit levels"
            )
        
        with st.expander("📋 Contract Slopes", expanded=True):
            st.session_state.slopes['contract_weekday'] = st.number_input(
                "📅 Weekday Entry", 
                value=st.session_state.slopes['contract_weekday'], 
                step=0.01,
                help="Entry slope for Monday-Thursday"
            )
            st.session_state.slopes['contract_frimon'] = st.number_input(
                "🔄 Friday→Monday Entry", 
                value=st.session_state.slopes['contract_frimon'], 
                step=0.01,
                help="Entry slope for Friday to Monday transitions"
            )
            st.session_state.slopes['contract_skyline'] = st.number_input(
                "🎯 Exit Slope", 
                value=st.session_state.slopes['contract_skyline'], 
                step=0.01,
                help="Exit slope for all contract positions"
            )
        
        # Contract settings
        st.markdown("### 📋 Contract Settings")
        strike_spacing = st.number_input(
            "💰 Strike Spacing", 
            value=5.0, 
            min_value=1.0,
            help="Dollar spacing between option strikes"
        )
        
        st.session_state.strike_freeze = st.checkbox(
            "🔒 Freeze Strike for Session", 
            value=st.session_state.strike_freeze,
            help="Keep the same strike for the entire trading session"
        )
        
        # Reset button
        if st.button("🔄 Reset All Settings", help="Reset all configurations to defaults"):
            for key in ['slopes', 'strike_freeze', 'manual_strike']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # Data Input Section
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    def spx_inputs():
        col1, col2, col3 = st.columns(3)
        with col1:
            spx_close_anchor = st.number_input(
                "💼 14:30 Close", 
                value=6500.0, 
                step=0.1,
                help="SPX close price at 14:30 CT previous day"
            )
        with col2:
            spx_high_anchor = st.number_input(
                "🔺 Daily High", 
                value=6520.0, 
                step=0.1,
                help="Highest SPX price from previous day"
            )
        with col3:
            spx_low_anchor = st.number_input(
                "🔻 Daily Low", 
                value=6480.0, 
                step=0.1,
                help="Lowest SPX price from previous day"
            )
        return spx_close_anchor, spx_high_anchor, spx_low_anchor
    
    def contract_inputs():
        contract_anchor = st.number_input(
            "📊 15:30 Candle High", 
            value=25.50, 
            step=0.05,
            help="Highest price of the 15:30 candle from previous session"
        )
        return contract_anchor
    
    col1, col2 = st.columns(2)
    
    with col1:
        render_input_section("📈", "SPX Previous Day Anchors", lambda: None)
        spx_close_anchor, spx_high_anchor, spx_low_anchor = spx_inputs()
    
    with col2:
        render_input_section("📋", "Contract Previous Session", lambda: None)
        contract_anchor = contract_inputs()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Calculate derived values
    strike = get_closest_itm_strike(spx_close_anchor, strike_spacing)
    if st.session_state.strike_freeze and st.session_state.manual_strike:
        strike = st.session_state.manual_strike
    else:
        st.session_state.manual_strike = strike
    
    # Create anchor times (timezone-naive for proper handling)
    spx_high_time = CT_TZ.localize(datetime.combine(previous_date, dt_time(11, 0)))
    spx_low_time = CT_TZ.localize(datetime.combine(previous_date, dt_time(13, 0)))
    spx_close_time = CT_TZ.localize(datetime.combine(previous_date, dt_time(15, 0)))
    contract_anchor_time = CT_TZ.localize(datetime.combine(previous_date, dt_time(15, 30)))
    
    # Display current configuration
    st.success(f"✅ **Configuration Active** | Strike: **{strike}C** | Mode: **Manual Input** | Ready for Projections")
    
    # Create projection datetime (timezone-naive for proper handling)
    projection_dt = datetime.combine(projection_date, dt_time(0, 0))
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 SPX Projections", 
        "📋 Contract Analysis", 
        "🎯 Fan Signals", 
        "📋 Trading Plan"
    ])
    
    # Tab 1: SPX Projections
    with tab1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("## 📊 SPX Baseline & Skyline Projections")
        
        # High anchor table
        st.markdown("### 🔺 High Anchor Projections")
        high_table = create_spx_table(
            spx_high_anchor, spx_high_time, "High", 
            projection_dt, st.session_state.slopes, 
            count_blocks_clock
        )
        
        # Metadata display
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🎯 Anchor Value", f"{high_table.attrs['anchor_value']:.2f}")
        with col2:
            st.metric("⏰ Anchor Time", high_table.attrs['anchor_time'].strftime('%H:%M'))
        with col3:
            st.metric("🔢 Blocks to 08:30", high_table.attrs['blocks_to_start'])
        with col4:
            st.metric("📈 Slopes", f"B: {high_table.attrs['baseline_slope']}, S: {high_table.attrs['skyline_slope']}")
        
        st.dataframe(high_table, use_container_width=True)
        
        col1, col2 = st.columns([3, 1])
        with col2:
            csv = high_table.to_csv(index=False)
            st.download_button(
                "📥 Export CSV", 
                csv, 
                "spx_high_projections.csv", 
                "text/csv",
                use_container_width=True
            )
        
        # Close anchor table
        st.markdown("### 🎯 Close Anchor Projections")
        close_table = create_spx_table(
            spx_close_anchor, spx_close_time, "Close",
            projection_dt, st.session_state.slopes,
            count_blocks_clock
        )
        
        # Metadata display
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🎯 Anchor Value", f"{close_table.attrs['anchor_value']:.2f}")
        with col2:
            st.metric("⏰ Anchor Time", "3:00 PM")
        with col3:
            st.metric("🔢 Blocks to 08:30", close_table.attrs['blocks_to_start'])
        with col4:
            st.metric("📈 Slopes", f"B: {close_table.attrs['baseline_slope']}, S: {close_table.attrs['skyline_slope']}")
        
        st.dataframe(close_table, use_container_width=True)
        
        col1, col2 = st.columns([3, 1])
        with col2:
            csv = close_table.to_csv(index=False)
            st.download_button(
                "📥 Export CSV", 
                csv, 
                "spx_close_projections.csv", 
                "text/csv",
                use_container_width=True
            )
        
        # Low anchor table
        st.markdown("### 🔻 Low Anchor Projections")
        low_table = create_spx_table(
            spx_low_anchor, spx_low_time, "Low",
            projection_dt, st.session_state.slopes,
            count_blocks_clock
        )
        
        # Metadata display
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🎯 Anchor Value", f"{low_table.attrs['anchor_value']:.2f}")
        with col2:
            st.metric("⏰ Anchor Time", low_table.attrs['anchor_time'].strftime('%H:%M'))
        with col3:
            st.metric("🔢 Blocks to 08:30", low_table.attrs['blocks_to_start'])
        with col4:
            st.metric("📈 Slopes", f"B: {low_table.attrs['baseline_slope']}, S: {low_table.attrs['skyline_slope']}")
        
        st.dataframe(low_table, use_container_width=True)
        
        col1, col2 = st.columns([3, 1])
        with col2:
            csv = low_table.to_csv(index=False)
            st.download_button(
                "📥 Export CSV", 
                csv, 
                "spx_low_projections.csv", 
                "text/csv",
                use_container_width=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Tab 2: Contract Analysis
    with tab2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f"## 📋 Contract Analysis - {strike}C")
        
        contract_table = create_contract_table(
            contract_anchor, contract_anchor_time, strike,
            projection_dt, st.session_state.slopes,
            count_blocks_active_contract
        )
        
        # Metadata display
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🎯 Strike Price", f"${contract_table.attrs['strike']:.0f}")
        with col2:
            st.metric("📅 Trading Regime", contract_table.attrs['regime'])
        with col3:
            st.metric("🔢 Blocks to 07:00", contract_table.attrs['blocks_to_start'])
        with col4:
            st.metric("⚡ Block Mode", "Active Trading")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📉 Entry Slope", f"{contract_table.attrs['entry_slope']:.2f}")
        with col2:
            st.metric("📈 Exit Slope", f"{contract_table.attrs['exit_slope']:.2f}")
        
        st.dataframe(contract_table, use_container_width=True)
        
        col1, col2 = st.columns([3, 1])
        with col2:
            csv = contract_table.to_csv(index=False)
            st.download_button(
                "📥 Export CSV", 
                csv, 
                f"contract_{strike}_projections.csv", 
                "text/csv",
                use_container_width=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Tab 3: Fan Signals
    with tab3:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("## 🎯 Fan Touch Signals")
        
        st.info("🔮 **Fan signals require live market data.** In manual mode, this feature shows the framework for real-time signal detection when connected to data feeds.")
        
        # Show example framework
        example_signals = pd.DataFrame([
            {"Time": "09:00", "Rule": "SKY-TOUCH", "Context": "Close above skyline (6,515.25)", "Signal": "Bullish continuation", "Target": "Monitor for bearish return"},
            {"Time": "10:30", "Rule": "BASE-BOUNCE", "Context": "Close above baseline (6,485.50)", "Signal": "Bullish reversal", "Target": "Skyline (6,520.75)"},
            {"Time": "12:00", "Rule": "SKY-REJECT", "Context": "Close below skyline (6,518.25)", "Signal": "Bearish reversal", "Target": "Baseline (6,482.50)"}
        ])
        
        st.markdown("### 📊 Signal Framework (Example)")
        st.dataframe(example_signals, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Tab 4: Trading Plan
    with tab4:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("## 📋 Trading Plan Card")
        st.markdown("**Key decision points for the trading session**")
        
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
                '⏰ Time': time_str,
                '📉 SPX Baseline': f"{spx_baseline:.2f}",
                '📈 SPX Skyline': f"{spx_skyline:.2f}",
                f'📋 {strike}C Entry': f"${contract_entry:.2f}",
                f'🎯 {strike}C Exit': f"${contract_exit:.2f}"
            })
        
        plan_df = pd.DataFrame(plan_data)
        st.dataframe(plan_df, use_container_width=True)
        
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            csv = plan_df.to_csv(index=False)
            st.download_button(
                "📥 Export Plan", 
                csv, 
                "trading_plan.csv", 
                "text/csv",
                use_container_width=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div style="text-align: center; padding: 2rem; margin-top: 2rem; 
                background: rgba(255,255,255,0.25); backdrop-filter: blur(10px); 
                border-radius: 16px; border: 1px solid rgba(255,255,255,0.3);">
        <p style="margin: 0; color: #5a6c7d; font-size: 0.9rem;">
            <strong>SPX Prophet</strong> | Professional Trading Analysis Platform | 
            Built with ❤️ using Streamlit
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

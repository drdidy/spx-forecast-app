import streamlit as st
from datetime import datetime, time, timedelta
import pandas as pd

# --- SLOPE SETTINGS ---
SLOPES = {
    "SPX_HIGH": -0.2792,
    "SPX_CLOSE": -0.2792,
    "SPX_LOW": -0.2792,
    "TSLA": -0.1180,
    "NVDA": -0.0485,
    "AAPL": -0.1137,
    "MSFT": -0.1574,
    "AMZN": -0.0782,
    "GOOGL": -0.0485,
}

# --- HELPERS ---
def generate_time_blocks():
    base = datetime.strptime("08:30", "%H:%M")
    return [(base + timedelta(minutes=30 * i)).strftime("%H:%M") for i in range(13)]

def calculate_spx_blocks(a, t):
    dt, blocks = a, 0
    while dt < t:
        if dt.hour != 16:
            blocks += 1
        dt += timedelta(minutes=30)
    return blocks

def calculate_stock_blocks(a, t):
    prev_close = a.replace(hour=15, minute=0)
    bp = max(0, int((prev_close - a).total_seconds() // 1800))
    next_open  = datetime.combine(t.date(), time(8,30))
    next_close = datetime.combine(t.date(), time(15,0))
    bn = 0 if t <= next_open else int((min(t,next_close) - next_open).total_seconds() // 1800)
    return bp + bn

def generate_spx(price, slope, anchor, fd):
    rows = []
    for slot in generate_time_blocks():
        h, m = map(int, slot.split(":"))
        tgt = datetime.combine(fd, time(h, m))
        b = calculate_spx_blocks(anchor, tgt)
        rows.append({
            "Time": slot,
            "Entry": round(price + slope * b, 2),
            "Exit":  round(price - slope * b, 2)
        })
    return pd.DataFrame(rows)

def generate_stock(price, slope, anchor, fd, invert=False):
    rows = []
    for slot in generate_time_blocks():
        h, m = map(int, slot.split(":"))
        tgt = datetime.combine(fd, time(h, m))
        b = calculate_stock_blocks(anchor, tgt)
        if invert:
            e = price - slope * b
            x = price + slope * b
        else:
            e = price + slope * b
            x = price - slope * b
        rows.append({"Time": slot, "Entry": round(e,2), "Exit": round(x,2)})
    return pd.DataFrame(rows)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Dr Didy Forecast",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- THEME CSS BLOCKS ---
light_css = """
<style>
.main-container { max-width:1200px; margin:0 auto; padding:0 1rem; }
body {background:#eef2f6; color:#333; font-family:'Segoe UI',sans-serif; margin:0;}
.sidebar .sidebar-content {background:#1f1f3b; color:#fff; padding:1rem; border-radius:0 1rem 1rem 0;}
.app-header {margin:1rem 0; padding:1.5rem; background:linear-gradient(90deg,#2a5d84,#1f4068);
            border-radius:1rem; text-align:center; color:#fff; box-shadow:0 4px 12px rgba(0,0,0,0.15);}
.app-header h1 {margin:0; font-size:2.5rem; font-weight:600;}
.input-card {background:#fff; padding:1.5rem 2rem; border-radius:1rem; box-shadow:0 4px 12px rgba(0,0,0,0.05);
             text-align:center;}
.input-card h2 {margin:0 0 1rem; font-size:1.5rem; color:#1f4068;}
.stButton>button {background:#1f4068; color:#fff; border:none;
                  padding:0.75rem 1.5rem; font-size:1rem; font-weight:600;
                  border-radius:0.75rem; margin-top:1rem;}
.stButton>button:hover {background:#16314f;}
.metric-cards {display:flex; gap:1rem; flex-wrap:wrap; margin:1.5rem 0;}
.anchor-card {flex:1 1 30%; display:flex; align-items:center;
             padding:1rem 1.5rem; border-radius:1rem; color:#fff;
             box-shadow:0 8px 20px rgba(0,0,0,0.1);
             transition:transform .2s,box-shadow .2s;}
.anchor-card:hover {transform:translateY(-4px); box-shadow:0 12px 30px rgba(0,0,0,0.15);}
.icon-wrapper {width:48px; height:48px; background:#fff; border-radius:50%;
               display:flex; align-items:center; justify-content:center;
               margin-right:1rem; font-size:1.5rem;}
.content .title {font-weight:600; font-size:1.1rem;}
.content .value {font-weight:300; font-size:2rem; margin-top:0.25rem;}
.anchor-high {background:#ff6b6b;}
.anchor-close {background:#4ecdc4;}
.anchor-low {background:#f7b731; color:#333;}
.card {background:#fff; padding:1rem; border-radius:1rem;
       box-shadow:0 4px 12px rgba(0,0,0,0.05); margin-bottom:2rem;}
@media(max-width:768px){
  .metric-cards {flex-direction:column;}
}
</style>
"""
dark_css = """
<style>
.main-container { max-width:1200px; margin:0 auto; padding:0 1rem; }
body {background:#1f1f1f; color:#e0e0e0; font-family:'Segoe UI',sans-serif; margin:0;}
.sidebar .sidebar-content {background:#2b2b2b; color:#e0e0e0; padding:1rem; border-radius:0 1rem 1rem 0;}
.app-header {margin:1rem 0; padding:1.5rem; background:linear-gradient(90deg,#0f0c29,#24243e);
            border-radius:1rem; text-align:center; color:#f0f0f0;
            box-shadow:0 4px 12px rgba(0,0,0,0.5);}
.app-header h1 {margin:0; font-size:2.5rem; font-weight:600;}
.input-card {background:#292b2f; padding:1.5rem 2rem; border-radius:1rem;
             box-shadow:0 4px 12px rgba(0,0,0,0.6); text-align:center;}
.input-card h2 {margin:0 0 1rem; font-size:1.5rem; color:#f0f0f0;}
.stButton>button {background:#444; color:#e0e0e0; border:none;
                  padding:0.75rem 1.5rem; font-size:1rem; font-weight:600;
                  border-radius:0.75rem; margin-top:1rem;}
.stButton>button:hover {background:#555;}
.metric-cards {display:flex; gap:1rem; flex-wrap:wrap; margin:1.5rem 0;}
.anchor-card {flex:1 1 30%; display:flex; align-items:center;
             padding:1rem 1.5rem; border-radius:1rem; color:#fff;
             box-shadow:0 8px 20px rgba(0,0,0,0.5);
             transition:transform .2s,box-shadow .2s;}
.anchor-card:hover {transform:translateY(-4px); box-shadow:0 12px 30px rgba(0,0,0,0.6);}
.icon-wrapper {width:48px; height:48px; background:#e0e0e0; border-radius:50%;
               display:flex; align-items:center; justify-content:center;
               margin-right:1rem; font-size:1.5rem; color:#1f1f1f;}
.content .title {font-weight:600; font-size:1.1rem;}
.content .value {font-weight:300; font-size:2rem; margin-top:0.25rem;}
.anchor-high {background:#e74c3c;}
.anchor-close {background:#1abc9c;}
.anchor-low {background:#f1c40f; color:#1f1f1f;}
.card {background:#292b2f; padding:1rem; border-radius:1rem;
       box-shadow:0 4px 12px rgba(0,0,0,0.6); margin-bottom:2rem;}
@media(max-width:768px){
  .metric-cards {flex-direction:column;}
}
</style>
"""

# --- THEME SWITCHER ---
with st.sidebar:
    theme = st.radio("🎨 Theme", ["Light","Dark"])
if theme == "Dark":
    st.markdown(dark_css, unsafe_allow_html=True)
else:
    st.markdown(light_css, unsafe_allow_html=True)

# --- WRAP ALL CONTENT IN MAIN CONTAINER ---
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# --- HEADER ---
st.markdown(
    '<div class="app-header"><h1>📊 Dr Didy Forecast</h1></div>',
    unsafe_allow_html=True
)

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Settings")
    forecast_date = st.date_input("Forecast Date", datetime.now().date() + timedelta(days=1))
    st.divider()
    st.subheader("Adjust Slopes")
    for k in SLOPES:
        SLOPES[k] = st.slider(k.replace("_"," "), -1.0, 1.0, SLOPES[k], step=0.0001)

# --- TABS ---
tabs = st.tabs([
    "🧭 SPX",
    "🚗 TSLA",
    "🧠 NVDA",
    "🍎 AAPL",
    "🪟 MSFT",
    "📦 AMZN",
    "🔍 GOOGL"
])

# --- SPX TAB with Tue-contract-low + Thu methods + Mon/Wed/Fri unchanged ---
with tabs[0]:
    st.markdown('<div class="tab-header">🧭 SPX Forecast</div>', unsafe_allow_html=True)

    # Centralized inputs
    st.markdown('<div class="input-card"><h2>Set Anchors & Time</h2></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    hp = c1.number_input("🔼 High Price",   min_value=0.0, value=6185.8, format="%.2f", key="spx_hp")
    ht = c1.time_input("🕒 High Time",      datetime(2025,1,1,11,30).time(), step=1800, key="spx_ht")
    cp = c2.number_input("⏹️ Close Price",  min_value=0.0, value=6170.2, format="%.2f", key="spx_cp")
    ct = c2.time_input("🕒 Close Time",     datetime(2025,1,1,15,0).time(),  step=1800, key="spx_ct")
    lp = c3.number_input("🔽 Low Price",    min_value=0.0, value=6130.4, format="%.2f", key="spx_lp")
    lt = c3.time_input("🕒 Low Time",       datetime(2025,1,1,13,30).time(), step=1800, key="spx_lt")

    # Day flags
    is_tue = forecast_date.weekday() == 1
    is_thu = forecast_date.weekday() == 3

    # Tuesday: contract-low input
    if is_tue:
        st.markdown("**Tuesday: Contract-Low Entry Projection**")
        cl_col1, cl_col2 = st.columns(2)
        with cl_col1:
            tue_cl_time  = st.time_input("Contract Low Time",   datetime(2025,1,1,8,30).time(), key="tue_cl_time")
        with cl_col2:
            tue_cl_price = st.number_input("Contract Low Price", value=5.0, step=0.1, key="tue_cl_price")

    # Thursday: OTM-line + bounce-low inputs
    if is_thu:
        st.markdown("**Thursday SPX methods**")
        o1, o2 = st.columns(2)
        with o1:
            low1_time  = st.time_input("OTM Low 1 Time",   datetime(2025,1,1,3,0).time(), key="tu_low1_time")
            low1_price = st.number_input("OTM Low 1 Price", value=10.0, step=0.1,     key="tu_low1_price")
        with o2:
            low2_time  = st.time_input("OTM Low 2 Time",   datetime(2025,1,1,4,0).time(), key="tu_low2_time")
            low2_price = st.number_input("OTM Low 2 Price", value=12.0, step=0.1,     key="tu_low2_price")
        st.markdown("<br><strong>8 EMA Bounce-Low Anchor</strong>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            bounce_time  = st.time_input("Bounce Low Time",  datetime(2025,1,1,3,30).time(), key="tu_bounce_time")
        with b2:
            bounce_price = st.number_input("Bounce Low Price", value=6100.0, step=0.1,  key="tu_bounce_price")

    # Generate button
    if st.button("🔮 Generate SPX", key="btn_spx"):
        ah = datetime.combine(forecast_date - timedelta(days=1), ht)
        ac = datetime.combine(forecast_date - timedelta(days=1), ct)
        al = datetime.combine(forecast_date - timedelta(days=1), lt)

        # ---- Tuesday logic ----
        if is_tue:
            anchor_dt = datetime.combine(forecast_date, tue_cl_time)
            rows = []
            for slot in generate_time_blocks():
                h, m = map(int, slot.split(":"))
                tgt = datetime.combine(forecast_date, time(h, m))
                b = calculate_spx_blocks(anchor_dt, tgt)
                proj = tue_cl_price + (-0.5250) * b
                rows.append({"Time": slot, "Projected": round(proj, 2)})
            st.subheader("🔹 Tuesday Entry Table")
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

        # ---- Thursday logic ----
        elif is_thu:
            # OTM-line
            dt1 = datetime.combine(forecast_date - timedelta(days=1), low1_time)
            dt2 = datetime.combine(forecast_date - timedelta(days=1), low2_time)
            n12 = calculate_spx_blocks(dt1, dt2) or 1
            alt_slope = (low2_price - low1_price) / n12

            st.subheader("🌀 Thu: OTM-Line Forecast")
            o_rows = []
            for slot in generate_time_blocks():
                h, m = map(int, slot.split(":"))
                tgt = datetime.combine(forecast_date, time(h, m))
                b = calculate_spx_blocks(dt1, tgt)
                proj = low1_price + alt_slope * b
                o_rows.append({"Time": slot, "Projected": round(proj, 2)})
            st.dataframe(pd.DataFrame(o_rows), use_container_width=True)

            # Bounce-low slope
            bounce_dt = datetime.combine(forecast_date - timedelta(days=1), bounce_time)
            bslope = SLOPES["SPX_LOW"]

            st.subheader("📈 Thu: Bounce-Low Slope Forecast")
            br = []
            for slot in generate_time_blocks():
                h, m = map(int, slot.split(":"))
                tgt = datetime.combine(forecast_date, time(h, m))
                b = calculate_spx_blocks(bounce_dt, tgt)
                proj = bounce_price + bslope * b
                br.append({"Time": slot, "Projected": round(proj, 2)})
            st.dataframe(pd.DataFrame(br), use_container_width=True)

        # ---- Mon/Wed/Fri logic ----
        else:
            st.markdown('<div class="metric-cards">', unsafe_allow_html=True)
            for cls, icon, title, val in [
                ("anchor-high","🔼","High Anchor",hp),
                ("anchor-close","⏹️","Close Anchor",cp),
                ("anchor-low","🔽","Low Anchor",lp),
            ]:
                card = f'''
                <div class="anchor-card {cls}">
                  <div class="icon-wrapper">{icon}</div>
                  <div class="content">
                    <div class="title">{title}</div>
                    <div class="value">{val:.2f}</div>
                  </div>
                </div>'''
                st.markdown(card, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            for icon, title, price, slope, anchor in [
                ("🔼","High Anchor", hp, SLOPES["SPX_HIGH"], ah),
                ("🔽","Low Anchor",  lp, SLOPES["SPX_LOW"],  al),
                ("⏹️","Close Anchor",cp, SLOPES["SPX_CLOSE"],ac),
            ]:
                st.subheader(f"{icon} {title} Table")
                df = generate_spx(price, slope, anchor, forecast_date)
                st.dataframe(df.round(2), use_container_width=True)

# --- STOCK TABS ---
icons = {"TSLA":"🚗","NVDA":"🧠","AAPL":"🍎","MSFT":"🪟","AMZN":"📦","GOOGL":"🔍"}
for i, label in enumerate(["TSLA","NVDA","AAPL","MSFT","AMZN","GOOGL"], start=1):
    with tabs[i]:
        st.markdown(f'<div class="tab-header">{icons[label]} {label} Forecast</div>', unsafe_allow_html=True)
        st.markdown('<div class="input-card"><h2>Set Anchors & Time</h2></div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        lp = col1.number_input("🔽 Prev-Day Low Price", min_value=0.0, value=0.0, format="%.2f", key=f"{label}_low_price")
        lt = col1.time_input("🕒 Prev-Day Low Time", datetime(2025,1,1,8,30).time(), step=1800, key=f"{label}_low_time")
        hp = col2.number_input("🔼 Prev-Day High Price",min_value=0.0, value=0.0, format="%.2f", key=f"{label}_high_price")
        ht = col2.time_input("🕒 Prev-Day High Time",datetime(2025,1,1,8,30).time(), step=1800, key=f"{label}_high_time")

        if st.button(f"🔮 Generate {label}", key=f"btn_{label}"):
            a_low  = datetime.combine(forecast_date - timedelta(days=1), lt)
            a_high = datetime.combine(forecast_date - timedelta(days=1), ht)

            st.markdown('<div class="metric-cards">', unsafe_allow_html=True)
            for cls, icon, title, val in [
                ("anchor-low","🔽","Low Anchor",lp),
                ("anchor-high","🔼","High Anchor",hp),
            ]:
                card = f'''
                <div class="anchor-card {cls}">
                  <div class="icon-wrapper">{icon}</div>
                  <div class="content">
                    <div class="title">{title}</div>
                    <div class="value">{val:.2f}</div>
                  </div>
                </div>'''
                st.markdown(card, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.subheader("🔻 Low Anchor Table")
            df_low = generate_stock(lp, SLOPES[label], a_low, forecast_date, invert=True)
            st.dataframe(df_low.round(2), use_container_width=True)

            st.subheader("🔺 High Anchor Table")
            df_high = generate_stock(hp, SLOPES[label], a_high, forecast_date, invert=False)
            st.dataframe(df_high.round(2), use_container_width=True)

# --- CLOSE MAIN CONTAINER ---
st.markdown('</div>', unsafe_allow_html=True)

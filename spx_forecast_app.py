import streamlit as st
from datetime import datetime, time, timedelta
import pandas as pd

# --- SLOPE SETTINGS ---
SLOPES = {
    "SPX_HIGH": -0.2792,
    "SPX_CLOSE": -0.2792,
    "SPX_LOW": -0.2792,
    "TSLA": -0.1508,
    "NVDA": -0.0485,
    "AAPL": -0.1137,
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
... your existing CSS ...
</style>
"""
dark_css = """
<style>
.main-container { max-width:1200px; margin:0 auto; padding:0 1rem; }
... your existing CSS ...
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
tabs = st.tabs(["🧭 SPX","🚗 TSLA","🧠 NVDA","🍎 AAPL","📦 AMZN","🔍 GOOGL"])

# --- SPX TAB ---
with tabs[0]:
    st.markdown('<div class="tab-header">🧭 SPX Forecast</div>', unsafe_allow_html=True)

    # centralized input card
    st.markdown('<div class="input-card"><h2>Set Anchors & Time</h2></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    hp = c1.number_input("🔼 High Price", min_value=0.0, value=6185.8, format="%.2f", key="spx_hp")
    ht = c1.time_input("🕒 High Time", datetime(2025,1,1,11,30).time(), step=1800, key="spx_ht")
    cp = c2.number_input("⏹️ Close Price", min_value=0.0, value=6170.2, format="%.2f", key="spx_cp")
    ct = c2.time_input("🕒 Close Time", datetime(2025,1,1,15,0).time(), step=1800, key="spx_ct")
    lp = c3.number_input("🔽 Low Price", min_value=0.0, value=6130.4, format="%.2f", key="spx_lp")
    lt = c3.time_input("🕒 Low Time", datetime(2025,1,1,13,30).time(), step=1800, key="spx_lt")

    # --- NEW: Tue/Thu logic trigger ---
    is_tu_th = forecast_date.weekday() in (1, 3)
    if is_tu_th:
        st.markdown("**Tuesday/Thursday SPX method**")
        t1, t2 = st.columns(2)
        with t1:
            low1_time  = st.time_input("OTM Low 1 Time", datetime(2025,1,1,3,0).time(), step=1800, key="tu_low1_time")
            low1_price = st.number_input("OTM Low 1 Price", value=10.0, step=0.1, key="tu_low1_price")
        with t2:
            low2_time  = st.time_input("OTM Low 2 Time", datetime(2025,1,1,4,0).time(), step=1800, key="tu_low2_time")
            low2_price = st.number_input("OTM Low 2 Price", value=12.0, step=0.1, key="tu_low2_price")

    # --- Generate Button ---
    if st.button("🔮 Generate SPX", key="btn_spx"):
        ah = datetime.combine(forecast_date - timedelta(days=1), ht)
        ac = datetime.combine(forecast_date - timedelta(days=1), ct)
        al = datetime.combine(forecast_date - timedelta(days=1), lt)

        if is_tu_th:
            # --- Linear interpolation from the two OTM lows ---
            dt1 = datetime.combine(forecast_date - timedelta(days=1), low1_time)
            dt2 = datetime.combine(forecast_date - timedelta(days=1), low2_time)
            n12 = calculate_spx_blocks(dt1, dt2) or 1
            alt_slope = (low2_price - low1_price) / n12

            st.subheader("🌀 Tue/Thu SPX Forecast")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            rows = []
            for slot in generate_time_blocks():
                h, m = map(int, slot.split(":"))
                tgt = datetime.combine(forecast_date, time(h, m))
                b = calculate_spx_blocks(dt1, tgt)
                proj = low1_price + alt_slope * b
                rows.append({"Time": slot, "Projected": round(proj, 2)})
            df_alt = pd.DataFrame(rows)
            st.dataframe(df_alt, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        else:
            # --- Original M/W/F slope method ---
            st.markdown('<div class="metric-cards">', unsafe_allow_html=True)
            for cls, icon, title, val in [
                ("anchor-high",  "🔼", "High Anchor",  hp),
                ("anchor-close", "⏹️", "Close Anchor", cp),
                ("anchor-low",   "🔽", "Low Anchor",   lp),
            ]:
                card = f'''
                <div class="anchor-card {cls}">
                  <div class="icon-wrapper">{icon}</div>
                  <div class="content">
                    <div class="title">{title}</div>
                    <div class="value">{val:.2f}</div>
                  </div>
                </div>
                '''
                st.markdown(card, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            for icon, title, price, slope, anchor in [
                ("🔼","High Anchor",  hp, SLOPES["SPX_HIGH"],  ah),
                ("⏹️","Close Anchor", cp, SLOPES["SPX_CLOSE"], ac),
                ("🔽","Low Anchor",   lp, SLOPES["SPX_LOW"],   al),
            ]:
                st.subheader(f"{icon} {title} Table")
                st.markdown('<div class="card">', unsafe_allow_html=True)
                df = generate_spx(price, slope, anchor, forecast_date)
                st.dataframe(df.round(2), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

# --- STOCK TABS (unchanged) ---
icons = {"TSLA":"🚗","NVDA":"🧠","AAPL":"🍎","AMZN":"📦","GOOGL":"🔍"}
for i, label in enumerate(["TSLA","NVDA","AAPL","AMZN","GOOGL"], start=1):
    with tabs[i]:
        st.markdown(f'<div class="tab-header">{icons[label]} {label} Forecast</div>', unsafe_allow_html=True)
        st.markdown('<div class="input-card"><h2>Set Anchors & Time</h2></div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        lp = col1.number_input("🔽 Prev-Day Low Price", min_value=0.0, value=0.0, format="%.2f", key=f"{label}_low_price")
        lt = col1.time_input("🕒 Prev-Day Low Time", datetime(2025,1,1,8,30).time(), step=1800, key=f"{label}_low_time")
        hp = col2.number_input("🔼 Prev-Day High Price", min_value=0.0, value=0.0, format="%.2f", key=f"{label}_high_price")
        ht = col2.time_input("🕒 Prev-Day High Time", datetime(2025,1,1,8,30).time(), step=1800, key=f"{label}_high_time")

        if st.button(f"🔮 Generate {label}", key=f"btn_{label}"):
            a_low  = datetime.combine(forecast_date - timedelta(days=1), lt)
            a_high = datetime.combine(forecast_date - timedelta(days=1), ht)
            st.markdown('<div class="metric-cards">', unsafe_allow_html=True)
            for cls, icon, title, val in [
                ("anchor-low",  "🔽", "Low Anchor",  lp),
                ("anchor-high", "🔼", "High Anchor", hp),
            ]:
                card = f'''
                <div class="anchor-card {cls}">
                  <div class="icon-wrapper">{icon}</div>
                  <div class="content">
                    <div class="title">{title}</div>
                    <div class="value">{val:.2f}</div>
                  </div>
                </div>
                '''
                st.markdown(card, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.subheader("🔻 Low Anchor Table")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            df_low = generate_stock(lp, SLOPES[label], a_low, forecast_date, invert=True)
            st.dataframe(df_low.round(2), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.subheader("🔺 High Anchor Table")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            df_high = generate_stock(hp, SLOPES[label], a_high, forecast_date, invert=False)
            st.dataframe(df_high.round(2), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

# --- CLOSE MAIN CONTAINER ---
st.markdown('</div>', unsafe_allow_html=True)

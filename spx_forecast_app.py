from datetime import datetime, timedelta
import streamlit as st
import pandas as pd

# --- CONFIG ---
st.set_page_config(page_title="SPX Forecast App", layout="centered")
DEFAULT_SLOPE = -0.3

st.title("📈 SPX Multi-Line Forecast App")
st.markdown("Enter your high, close, and low anchors to forecast SPX price for a given target time.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("🔧 Input Settings")

def get_anchor_input(label, default_dt, default_price):
    date = st.sidebar.date_input(f"{label} Date", value=default_dt.date(), key=f"{label}_date")
    time = st.sidebar.time_input(f"{label} Time", value=default_dt.time(), key=f"{label}_time")
    price = st.sidebar.number_input(f"{label} Price", value=default_price, key=f"{label}_price")
    return datetime.combine(date, time), price

# High Anchor
high_time, high_price = get_anchor_input("High", datetime(2025, 6, 27, 11, 30), 6185.8)

# Mid (Close) Anchor
mid_time, mid_price = get_anchor_input("Close", datetime(2025, 6, 27, 15, 0), 6170.2)

# Low Anchor
low_time, low_price = get_anchor_input("Low", datetime(2025, 6, 27, 13, 30), 6131.83)

# Target
st.sidebar.markdown("---")
st.sidebar.markdown("🎯 **Target Time**")
target_date = st.sidebar.date_input("Target Date", value=datetime(2025, 6, 30).date())
target_time = st.sidebar.time_input("Target Time", value=datetime(2025, 6, 30, 12, 30).time())
target_datetime = datetime.combine(target_date, target_time)

# --- BLOCK COUNTING ---
def count_30min_blocks(start: datetime, end: datetime) -> int:
    if end <= start:
        return 0
    blocks = 0
    current = start
    while current < end:
        # Skip 4-5pm pause
        if not (current.hour == 16):
            # Skip from Friday 4pm until Sunday 5pm
            if not (
                (current.weekday() == 4 and current.hour >= 16) or
                (current.weekday() == 5) or
                (current.weekday() == 6 and current.hour < 17)
            ):
                blocks += 1
        current += timedelta(minutes=30)
    return blocks

# --- FORECAST CALCULATION ---
def forecast(anchor_label, anchor_time, anchor_price):
    blocks = count_30min_blocks(anchor_time, target_datetime)
    projected = anchor_price + (blocks * DEFAULT_SLOPE)
    return {"Anchor": anchor_label, "Blocks": blocks, "Forecast Price": round(projected, 2)}

# --- RUN FORECAST ---
if st.button("📊 Generate Forecast Table"):
    results = [
        forecast("High", high_time, high_price),
        forecast("Close", mid_time, mid_price),
        forecast("Low", low_time, low_price)
    ]
    df = pd.DataFrame(results)
    st.write("### 📋 Forecast Results")
    st.dataframe(df, use_container_width=True)

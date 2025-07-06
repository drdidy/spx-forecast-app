import streamlit as st
from datetime import datetime, timedelta

# --- Default Slopes ---
SLOPES = {
    "SPX_HIGH": -0.048837,
    "SPX_CLOSE": -0.048837,
    "SPX_LOW": -0.048837,
    "TSLA": -0.1508,
    "NVDA": -0.0504,
    "AAPL": -0.1156,
    "AMZN": -0.0782,
    "GOOGL": -0.0485,
}

# --- Generate 30-min Forecast Slots (8:30 AM – 2:30 PM) ---
def generate_time_blocks():
    base = datetime.strptime("08:30", "%H:%M")
    return [(base + timedelta(minutes=30 * i)).strftime("%H:%M") for i in range(13)]

# --- Block Difference Calculator (excluding 4–5PM pause and weekend gap) ---
def calculate_blocks(anchor_time, target_time):
    total_blocks = 0
    while anchor_time < target_time:
        if anchor_time.weekday() >= 5:  # Skip weekends
            anchor_time += timedelta(days=1)
            anchor_time = anchor_time.replace(hour=5, minute=0)
            continue
        if anchor_time.hour == 16:  # Skip 4–5PM break
            anchor_time += timedelta(hours=1)
            continue
        anchor_time += timedelta(minutes=30)
        total_blocks += 1
    return total_blocks

# --- Forecast Table Generator ---
def generate_forecast(anchor_price, slope, anchor_dt):
    time_blocks = generate_time_blocks()
    forecast = []
    for t in time_blocks:
        hour, minute = map(int, t.split(":"))
        today_forecast_time = anchor_dt.replace(hour=hour, minute=minute) + timedelta(days=1)
        block_diff = calculate_blocks(anchor_dt, today_forecast_time)
        price = anchor_price + (slope * block_diff)
        forecast.append({"Time": t, "Forecast Price": round(price, 2)})
    return forecast

# --- Page Setup ---
st.set_page_config("DrSPX Forecast App", layout="wide")
st.title("📊 DrSPX Forecast App")

tab_spx, tab_tsla, tab_nvda, tab_aapl, tab_amzn, tab_googl = st.tabs([
    "🧭 SPX", "🚗 TSLA", "🧠 NVDA", "🍎 AAPL", "📦 AMZN", "🔍 GOOGL"
])

# --- SPX Tab ---
with tab_spx:
    st.subheader("SPX Forecast (High / Close / Low Anchors)")
    col1, col2, col3 = st.columns(3)
    high_price = col1.number_input("High Price", value=6185.8)
    high_time = col1.time_input("High Time", value=datetime(2025, 6, 27, 11, 30).time())

    close_price = col2.number_input("Close Price", value=6170.2)
    close_time = col2.time_input("Close Time", value=datetime(2025, 6, 27, 15, 0).time())

    low_price = col3.number_input("Low Price", value=6131.83)
    low_time = col3.time_input("Low Time", value=datetime(2025, 6, 27, 13, 30).time())

    forecast_date = st.date_input("Forecast Date", value=datetime(2025, 6, 30).date())

    if st.button("Generate SPX Forecast"):
        anchor_dt_high = datetime.combine(forecast_date - timedelta(days=1), high_time)
        anchor_dt_close = datetime.combine(forecast_date - timedelta(days=1), close_time)
        anchor_dt_low = datetime.combine(forecast_date - timedelta(days=1), low_time)

        st.write("### High Anchor Forecast")
        st.dataframe(generate_forecast(high_price, SLOPES["SPX_HIGH"], anchor_dt_high), use_container_width=True)

        st.write("### Close Anchor Forecast")
        st.dataframe(generate_forecast(close_price, SLOPES["SPX_CLOSE"], anchor_dt_close), use_container_width=True)

        st.write("### Low Anchor Forecast")
        st.dataframe(generate_forecast(low_price, SLOPES["SPX_LOW"], anchor_dt_low), use_container_width=True)

# --- Ticker Forecast Tab Function ---
def ticker_tab(tab, label, default_price, slope_key):
    with tab:
        st.subheader(f"{label} Forecast")
        anchor_price = st.number_input(f"{label} Anchor Price", value=default_price, key=f"{label}_price")
        anchor_time = st.time_input(f"{label} Anchor Time", value=datetime(2025, 6, 27, 3, 0).time(), key=f"{label}_time")
        forecast_date = st.date_input(f"{label} Forecast Date", value=datetime(2025, 6, 28).date(), key=f"{label}_date")

        if st.button(f"Generate {label} Forecast"):
            anchor_dt = datetime.combine(forecast_date - timedelta(days=1), anchor_time)
            table = generate_forecast(anchor_price, SLOPES[slope_key], anchor_dt)
            st.dataframe(table, use_container_width=True)

ticker_tab(tab_tsla, "TSLA", 261.4, "TSLA")
ticker_tab(tab_nvda, "NVDA", 131.68, "NVDA")
ticker_tab(tab_aapl, "AAPL", 197.37, "AAPL")
ticker_tab(tab_amzn, "AMZN", 189.14, "AMZN")
ticker_tab(tab_googl, "GOOGL", 169.77, "GOOGL")

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, timezone
import numpy as np

# Page configuration
st.set_page_config(
    page_title="TradePro - Portfolio Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for enterprise styling
st.markdown("""
<style>
    .main > div {
        padding-top: 0rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #e1e5e9;
    }
    
    .header-container {
        background: linear-gradient(90deg, #1f4e79 0%, #2563eb 100%);
        padding: 2rem 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
        color: white;
    }
    
    .portfolio-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    
    .gain-positive {
        color: #10b981;
        font-weight: 600;
    }
    
    .gain-negative {
        color: #ef4444;
        font-weight: 600;
    }
    
    .sidebar-info {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2563eb;
        margin: 1rem 0;
    }
    
    .quick-actions {
        display: flex;
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .action-btn {
        flex: 1;
        padding: 0.75rem;
        background: white;
        border: 2px solid #2563eb;
        border-radius: 0.5rem;
        text-align: center;
        color: #2563eb;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .action-btn:hover {
        background: #2563eb;
        color: white;
    }
    
    .watchlist-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem;
        border-bottom: 1px solid #e1e5e9;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header-container">
    <div style="display: flex; justify-content: between; align-items: center;">
        <div>
            <h1 style="margin: 0; font-size: 2rem;">TradePro Securities</h1>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Professional Trading Platform</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Welcome message
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    # Get current Central Time (UTC-6 or UTC-5 depending on DST)
    # Central Time is UTC-5 during DST (March-November)
    central_offset = timezone(timedelta(hours=-5))  # CDT (Central Daylight Time)
    central_time = datetime.now(central_offset)
    
    st.markdown(f"""
    ### Welcome back, David Okanlawon
    **Account:** Individual Trading Account  
    **Account Number:** ****-****-7892  
    **Last Login:** {central_time.strftime("%B %d, %Y at %I:%M %p CT")}
    """)

with col3:
    # NYSE closes at 4 PM Eastern, which is 3 PM Central
    st.markdown("""
    <div class="sidebar-info">
        <strong>Market Status</strong><br>
        <span style="color: #10b981;">● OPEN</span><br>
        <small>NYSE closes at 3:00 PM CT</small>
    </div>
    """, unsafe_allow_html=True)

# Portfolio Overview
st.markdown("---")
st.markdown("## Portfolio Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Portfolio Value",
        value="$9,203.36",
        delta=None
    )

with col2:
    st.metric(
        label="Today's Gain/Loss",
        value="$630.24",
        delta="7.35%",
        delta_color="normal"
    )

with col3:
    st.metric(
        label="Available Cash",
        value="$1,247.89",
        delta=None
    )

with col4:
    st.metric(
        label="Buying Power",
        value="$2,495.78",
        delta=None
    )

# Quick Actions
st.markdown("### Quick Actions")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("🔍 Research", use_container_width=True):
        st.success("Research tools opened!")

with col2:
    if st.button("📊 Trade", use_container_width=True):
        st.success("Trading interface opened!")

with col3:
    if st.button("📈 Analytics", use_container_width=True):
        st.success("Analytics dashboard opened!")

with col4:
    if st.button("📄 Reports", use_container_width=True):
        st.success("Reports section opened!")

with col5:
    if st.button("⚙️ Settings", use_container_width=True):
        st.success("Account settings opened!")

# Portfolio Performance Chart
st.markdown("### Portfolio Performance (30 Days)")

# Generate sample data for the chart
dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
base_value = 8573.12
np.random.seed(42)
returns = np.random.normal(0.008, 0.025, 30)
returns[-1] = 0.0735  # Today's return
portfolio_values = [base_value]

for i in range(1, 30):
    portfolio_values.append(portfolio_values[-1] * (1 + returns[i]))

performance_df = pd.DataFrame({
    'Date': dates,
    'Portfolio Value': portfolio_values
})

fig = px.line(performance_df, x='Date', y='Portfolio Value', 
              title='', line_shape='spline')
fig.update_layout(
    showlegend=False,
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(color='#374151'),
    xaxis=dict(gridcolor='#e5e7eb'),
    yaxis=dict(gridcolor='#e5e7eb')
)
fig.update_traces(line=dict(color='#2563eb', width=3))

st.plotly_chart(fig, use_container_width=True)

# Holdings and Watchlist
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("### Current Holdings")
    
    holdings_data = {
        'Symbol': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMZN'],
        'Shares': [25, 15, 8, 12, 10, 5],
        'Avg Cost': [156.32, 285.45, 142.18, 201.75, 245.80, 134.25],
        'Current Price': [178.45, 310.22, 138.95, 245.30, 289.15, 142.80],
        'Market Value': [4461.25, 4653.30, 1111.60, 2943.60, 2891.50, 714.00],
        'Gain/Loss': [553.25, 371.55, -25.84, 522.60, 433.50, 42.75],
        'Gain/Loss %': [14.17, 8.67, -2.29, 21.63, 17.65, 6.35]
    }
    
    holdings_df = pd.DataFrame(holdings_data)
    
    # Format the display
    display_df = holdings_df.copy()
    display_df['Market Value'] = display_df['Market Value'].apply(lambda x: f"${x:,.2f}")
    display_df['Avg Cost'] = display_df['Avg Cost'].apply(lambda x: f"${x:.2f}")
    display_df['Current Price'] = display_df['Current Price'].apply(lambda x: f"${x:.2f}")
    display_df['Gain/Loss'] = display_df['Gain/Loss'].apply(lambda x: f"${x:+,.2f}")
    display_df['Gain/Loss %'] = display_df['Gain/Loss %'].apply(lambda x: f"{x:+.2f}%")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

with col2:
    st.markdown("### Watchlist")
    
    watchlist_data = {
        'Symbol': ['SPY', 'QQQ', 'VTI', 'ARKK', 'IWM'],
        'Price': [445.67, 385.42, 241.33, 47.85, 201.25],
        'Change': [2.34, 4.67, 1.85, -0.95, 3.12],
        'Change %': [0.53, 1.23, 0.77, -1.95, 1.58]
    }
    
    watchlist_df = pd.DataFrame(watchlist_data)
    
    for i, row in watchlist_df.iterrows():
        color = "#10b981" if row['Change'] >= 0 else "#ef4444"
        change_sign = "+" if row['Change'] >= 0 else ""
        
        st.markdown(f"""
        <div class="watchlist-item">
            <div>
                <strong>{row['Symbol']}</strong><br>
                <small>${row['Price']:.2f}</small>
            </div>
            <div style="text-align: right; color: {color};">
                <strong>{change_sign}{row['Change']:.2f}</strong><br>
                <small>({change_sign}{row['Change %']:.2f}%)</small>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Portfolio Allocation
st.markdown("### Asset Allocation")

allocation_data = {
    'Asset Class': ['Technology', 'Growth Stocks', 'Electric Vehicles', 'E-commerce', 'Cash'],
    'Allocation': [52.3, 28.7, 12.4, 4.8, 1.8],
    'Value': [4814.46, 2642.36, 1141.72, 441.76, 165.52]
}

allocation_df = pd.DataFrame(allocation_data)

fig_pie = px.pie(
    allocation_df, 
    values='Allocation', 
    names='Asset Class',
    title='',
    color_discrete_sequence=px.colors.qualitative.Set3
)

fig_pie.update_layout(
    showlegend=True,
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(color='#374151')
)

col1, col2 = st.columns([2, 1])
with col1:
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.markdown("#### Recent Activity")
    st.markdown("""
    **Today**
    - Bought 5 shares of NVDA at $289.15
    - Sold 10 shares of META at $312.45
    
    **Yesterday**
    - Dividend received: AAPL ($12.50)
    - Bought 3 shares of TSLA at $245.30
    
    **This Week**
    - Portfolio rebalancing completed
    - Added $1,000 to account
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; padding: 2rem;">
    <p>TradePro Securities | Member SIPC | <a href="#" style="color: #2563eb;">Privacy Policy</a> | <a href="#" style="color: #2563eb;">Terms of Service</a></p>
    <small>Securities products and services are offered through TradePro Securities LLC, Member SIPC.</small>
</div>
""", unsafe_allow_html=True)
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

# Page configuration
st.set_page_config(
    page_title="TradePro Securities",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .portfolio-value {
        font-size: 3rem;
        font-weight: 800;
        color: #059669;
        margin: 0;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
    }
    .status-positive {
        color: #059669;
        font-weight: 600;
    }
    .status-negative {
        color: #dc2626;
        font-weight: 600;
    }
    .sidebar-content {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
    }
    .nav-header {
        background: linear-gradient(90deg, #1e40af, #3b82f6);
        color: white;
        padding: 1rem;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Navigation Header
col_nav1, col_nav2 = st.columns([3, 1])
with col_nav1:
    st.markdown("""
    <div class="nav-header">
        <h1 style="margin:0; font-size: 1.8rem;">📈 TradePro Securities</h1>
        <p style="margin:0.5rem 0 0 0; opacity: 0.9;">Professional Trading Platform</p>
    </div>
    """, unsafe_allow_html=True)

with col_nav2:
    st.markdown("""
    <div style="text-align: right; padding: 1rem; color: #374151;">
        <p style="margin: 0; font-size: 1.1rem; font-weight: 600;">Welcome back,</p>
        <p style="margin: 0; font-size: 1.3rem; font-weight: 700; color: #1f2937;">David Okanlawon</p>
    </div>
    """, unsafe_allow_html=True)

# Main dashboard
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<h2 class="main-header">David\'s Portfolio Overview</h2>', unsafe_allow_html=True)
    
    # Portfolio value display
    col_val1, col_val2, col_val3 = st.columns([2, 1, 1])
    
    with col_val1:
        st.markdown('<p class="portfolio-value">$9,203.36</p>', unsafe_allow_html=True)
        st.markdown('<p style="color: #6b7280; font-size: 1.1rem; margin-top: -1rem;">Total Portfolio Value</p>', unsafe_allow_html=True)
    
    with col_val2:
        st.metric("Today's Change", "+$127.42", "+1.40%")
    
    with col_val3:
        st.metric("Total Return", "+$1,203.36", "+15.04%")

    # Portfolio performance chart
    st.markdown("### Portfolio Performance")
    
    # Generate sample performance data
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
    np.random.seed(42)
    base_value = 8000
    returns = np.random.normal(0.001, 0.02, len(dates))
    portfolio_values = [base_value]
    
    for ret in returns[1:]:
        portfolio_values.append(portfolio_values[-1] * (1 + ret))
    
    # Adjust final value to match our target
    portfolio_values = np.array(portfolio_values)
    portfolio_values = portfolio_values * (9203.36 / portfolio_values[-1])
    
    chart_data = pd.DataFrame({
        'Date': dates,
        'Portfolio Value': portfolio_values
    })
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_data['Date'], 
        y=chart_data['Portfolio Value'],
        mode='lines',
        name='Portfolio Value',
        line=dict(color='#3b82f6', width=2),
        fill='tonexty',
        fillcolor='rgba(59, 130, 246, 0.1)'
    ))
    
    fig.update_layout(
        title="30-Day Portfolio Performance",
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        height=400,
        showlegend=False,
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### David's Account Summary")
    
    # Account metrics
    st.metric("Buying Power", "$2,847.22", "+$340.15")
    st.metric("Cash Balance", "$1,526.89", "-$180.50")
    st.metric("Margin Used", "$0.00", "0%")
    
    st.markdown("---")
    
    # Quick actions
    st.markdown("### Quick Actions")
    if st.button("🛒 Place Order", use_container_width=True):
        st.success("Redirecting to order placement...")
    
    if st.button("📊 Research", use_container_width=True):
        st.info("Opening research center...")
    
    if st.button("📈 Watchlist", use_container_width=True):
        st.info("Loading watchlist...")
    
    if st.button("💰 Deposit Funds", use_container_width=True):
        st.success("Opening deposit interface...")
    
    st.markdown("---")
    
    # Market status
    st.markdown("### Market Status")
    market_status = "🟢 OPEN" if datetime.now().weekday() < 5 and 9 <= datetime.now().hour <= 16 else "🔴 CLOSED"
    st.markdown(f"**Status:** {market_status}")
    st.markdown("**Next Close:** 4:00 PM ET")

# Holdings section
st.markdown("---")
st.markdown("### Current Holdings")

# Sample holdings data
holdings_data = {
    'Symbol': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA'],
    'Company': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.', 'Amazon.com Inc.', 'Tesla Inc.', 'NVIDIA Corp.'],
    'Shares': [15, 8, 3, 5, 12, 6],
    'Avg Cost': [180.50, 320.25, 2650.00, 3200.15, 245.80, 875.60],
    'Current Price': [185.20, 335.80, 2680.45, 3150.22, 268.90, 920.15],
    'Market Value': [2778.00, 2686.40, 8041.35, 15751.10, 3226.80, 5520.90],
    'Day Change': ['+2.1%', '+4.8%', '+1.1%', '-1.6%', '+9.4%', '+5.1%'],
    'Total Return': ['+4.7%', '+4.9%', '+1.1%', '-1.6%', '+9.4%', '+5.1%']
}

holdings_df = pd.DataFrame(holdings_data)

# Adjust market values to sum closer to our portfolio total
holdings_df['Market Value'] = [1556.80, 1493.20, 804.14, 1575.11, 1932.08, 1842.03]

# Display holdings table
st.dataframe(
    holdings_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Market Value": st.column_config.NumberColumn("Market Value", format="$%.2f"),
        "Avg Cost": st.column_config.NumberColumn("Avg Cost", format="$%.2f"),
        "Current Price": st.column_config.NumberColumn("Current Price", format="$%.2f"),
    }
)

# Recent activity
st.markdown("### Recent Activity")
activity_data = {
    'Date': ['2024-08-13', '2024-08-12', '2024-08-12', '2024-08-09'],
    'Action': ['BUY', 'SELL', 'BUY', 'DIVIDEND'],
    'Symbol': ['NVDA', 'AAPL', 'MSFT', 'AAPL'],
    'Quantity': [2, 5, 3, 15],
    'Price': [920.15, 182.30, 335.80, 0.25],
    'Total': [-1840.30, 911.50, -1007.40, 3.75]
}

activity_df = pd.DataFrame(activity_data)
st.dataframe(
    activity_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Total": st.column_config.NumberColumn("Total", format="$%.2f"),
    }
)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 0.9rem; padding: 2rem;">
    <p>TradePro Securities | Member SIPC | Professional Trading Platform</p>
    <p>Account: David Okanlawon | Market data delayed by 15 minutes | Last updated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S ET") + """</p>
</div>
""", unsafe_allow_html=True)
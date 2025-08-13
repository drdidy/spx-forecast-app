import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    .gain-positive {
        color: #059669;
        font-weight: 600;
        font-size: 1.2rem;
    }
    .gain-negative {
        color: #dc2626;
        font-weight: 600;
        font-size: 1.2rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    .nav-bar {
        background: #f8fafc;
        padding: 1rem 0;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 2rem;
    }
    .status-badge {
        background: #dcfce7;
        color: #166534;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Header and Navigation
st.markdown('<div class="nav-bar">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown("# 📈 TradePro Securities")
with col2:
    st.markdown('<span class="status-badge">● Markets Open</span>', unsafe_allow_html=True)
with col3:
    st.markdown("**Welcome, Alex Johnson**")
st.markdown('</div>', unsafe_allow_html=True)

# Main portfolio overview
st.markdown('<h2 class="main-header">Portfolio Overview</h2>', unsafe_allow_html=True)

# Portfolio metrics row
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    st.markdown('<p class="portfolio-value">$9,203.36</p>', unsafe_allow_html=True)
    st.markdown("**Total Portfolio Value**")
    st.markdown('<span class="gain-positive">+$630.24 (+7.35%) Today</span>', unsafe_allow_html=True)

with col2:
    st.metric(
        label="Available Cash",
        value="$1,247.82",
        delta="Ready to invest"
    )

with col3:
    st.metric(
        label="Day's Range",
        value="$8,573.12 - $9,203.36",
        delta=None
    )

with col4:
    st.metric(
        label="Buying Power",
        value="$12,847.92",
        delta="+$630.24"
    )

st.divider()

# Charts and Performance Section
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Portfolio Performance (30 Days)")
    
    # Generate sample portfolio data
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
    np.random.seed(42)
    base_value = 8500
    returns = np.random.normal(0.005, 0.025, len(dates))
    portfolio_values = [base_value]
    
    for return_rate in returns[1:]:
        portfolio_values.append(portfolio_values[-1] * (1 + return_rate))
    
    # Ensure final value matches our target
    portfolio_values[-1] = 9203.36
    
    portfolio_df = pd.DataFrame({
        'Date': dates,
        'Portfolio_Value': portfolio_values
    })
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=portfolio_df['Date'],
        y=portfolio_df['Portfolio_Value'],
        mode='lines',
        name='Portfolio Value',
        line=dict(color='#059669', width=3),
        fill='tonexty',
        fillcolor='rgba(5, 150, 105, 0.1)'
    ))
    
    fig.update_layout(
        height=400,
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#f3f4f6'),
        yaxis=dict(showgrid=True, gridcolor='#f3f4f6', tickformat='$,.0f'),
        margin=dict(l=0, r=0, t=20, b=0)
    )
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Asset Allocation")
    
    # Sample allocation data
    allocation_data = {
        'Asset Type': ['US Stocks', 'ETFs', 'International', 'Bonds', 'Cash'],
        'Value': [4521.65, 2876.43, 1205.28, 352.18, 247.82],
        'Percentage': [49.1, 31.3, 13.1, 3.8, 2.7]
    }
    
    allocation_df = pd.DataFrame(allocation_data)
    
    fig_pie = px.pie(
        allocation_df, 
        values='Value', 
        names='Asset Type',
        color_discrete_sequence=['#059669', '#0ea5e9', '#8b5cf6', '#f59e0b', '#6b7280']
    )
    
    fig_pie.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='%{label}<br>$%{value:,.2f}<br>%{percent}<extra></extra>'
    )
    
    fig_pie.update_layout(
        height=400,
        showlegend=False,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor='white'
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# Holdings and Watchlist
col1, col2 = st.columns(2)

with col1:
    st.subheader("Top Holdings")
    
    holdings_data = {
        'Symbol': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMZN'],
        'Shares': [25, 15, 8, 12, 6, 10],
        'Current Price': [175.84, 342.56, 138.21, 248.50, 421.63, 142.05],
        'Market Value': [4396.00, 5138.40, 1105.68, 2982.00, 2529.78, 1420.50],
        'Day Change': ['+2.34%', '+1.87%', '-0.45%', '+4.21%', '+3.67%', '+0.92%']
    }
    
    holdings_df = pd.DataFrame(holdings_data)
    
    # Style the dataframe
    def color_change(val):
        if '+' in str(val):
            return 'color: #059669'
        elif '-' in str(val):
            return 'color: #dc2626'
        return ''
    
    st.dataframe(
        holdings_df.style.applymap(color_change, subset=['Day Change']).format({
            'Current Price': '${:.2f}',
            'Market Value': '${:,.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )

with col2:
    st.subheader("Watchlist")
    
    watchlist_data = {
        'Symbol': ['META', 'NFLX', 'AMD', 'CRM', 'UBER'],
        'Price': [298.35, 445.67, 112.84, 218.92, 65.43],
        'Change': ['+1.25%', '-0.87%', '+2.14%', '+0.56%', '+3.21%'],
        'Volume': ['2.3M', '1.8M', '4.1M', '1.2M', '5.7M']
    }
    
    watchlist_df = pd.DataFrame(watchlist_data)
    
    st.dataframe(
        watchlist_df.style.applymap(color_change, subset=['Change']).format({
            'Price': '${:.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )

st.divider()

# Market Overview and Recent Activity
col1, col2 = st.columns(2)

with col1:
    st.subheader("Market Overview")
    
    market_data = {
        'Index': ['S&P 500', 'Dow Jones', 'NASDAQ', 'Russell 2000'],
        'Value': [4387.16, 34312.03, 13661.17, 1995.34],
        'Change': ['+0.85%', '+0.72%', '+1.23%', '+0.91%'],
        'Points': ['+36.98', '+245.86', '+166.44', '+17.98']
    }
    
    market_df = pd.DataFrame(market_data)
    
    st.dataframe(
        market_df.style.applymap(color_change, subset=['Change']).format({
            'Value': '{:,.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )

with col2:
    st.subheader("Recent Activity")
    
    activity_data = {
        'Time': ['09:32 AM', '09:45 AM', '10:15 AM', '11:30 AM'],
        'Action': ['BUY', 'SELL', 'BUY', 'BUY'],
        'Symbol': ['NVDA', 'AAPL', 'MSFT', 'TSLA'],
        'Quantity': [2, 5, 3, 1],
        'Price': ['$421.63', '$175.20', '$341.89', '$247.85']
    }
    
    activity_df = pd.DataFrame(activity_data)
    
    def color_action(val):
        if val == 'BUY':
            return 'color: #059669; font-weight: bold'
        elif val == 'SELL':
            return 'color: #dc2626; font-weight: bold'
        return ''
    
    st.dataframe(
        activity_df.style.applymap(color_action, subset=['Action']),
        use_container_width=True,
        hide_index=True
    )

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Market Status:** Open until 4:00 PM ET")
with col2:
    st.markdown("**Last Updated:** " + datetime.now().strftime("%I:%M %p ET"))
with col3:
    st.markdown("**Account Type:** Individual Taxable")
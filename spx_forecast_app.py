import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random

# Page configuration
st.set_page_config(
    page_title="TradeMax Pro - Portfolio Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
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
    .account-balance {
        font-size: 3rem;
        font-weight: 800;
        color: #059669;
        margin: 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .portfolio-section {
        background: #f8fafc;
        padding: 2rem;
        border-radius: 12px;
        border-left: 4px solid #3b82f6;
        margin: 1rem 0;
    }
    .news-item {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid #10b981;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .sidebar-logo {
        text-align: center;
        font-size: 1.8rem;
        font-weight: bold;
        color: #1f2937;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown('<div class="sidebar-logo">📈 TradeMax Pro</div>', unsafe_allow_html=True)
    
    st.markdown("### Navigation")
    menu_options = ["Dashboard", "Portfolio", "Trading", "Research", "Reports", "Settings"]
    selected = st.selectbox("", menu_options, index=0)
    
    st.markdown("---")
    st.markdown("### Quick Actions")
    col1, col2 = st.columns(2)
    with col1:
        st.button("🔥 Buy", use_container_width=True)
    with col2:
        st.button("📉 Sell", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### Market Status")
    st.success("🟢 Markets Open")
    st.caption("NYSE: 9:30 AM - 4:00 PM EST")
    
    st.markdown("---")
    st.markdown("### Support")
    st.info("📞 1-800-TRADEMAX\n💬 Live Chat Available")

# Main content
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown('<h1 class="main-header">Welcome back, Alex Richardson</h1>', unsafe_allow_html=True)
    st.markdown("*Last login: Today, 8:47 AM EST*")

with col2:
    st.markdown("### Account Balance")
    st.markdown('<p class="account-balance">₦9,203.36</p>', unsafe_allow_html=True)

# Portfolio Overview Section
st.markdown("---")
st.markdown("## 📊 Portfolio Overview")

# Create sample portfolio data
portfolio_data = {
    'Symbol': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA', 'META'],
    'Company': ['Apple Inc.', 'Alphabet Inc.', 'Microsoft Corp.', 'Tesla Inc.', 'Amazon.com Inc.', 'NVIDIA Corp.', 'Meta Platforms'],
    'Shares': [25, 8, 15, 12, 6, 20, 10],
    'Price': [182.52, 138.21, 378.85, 248.50, 146.80, 875.28, 325.16],
    'Change': ['+2.45%', '-0.82%', '+1.23%', '+4.67%', '-1.45%', '+3.21%', '+0.95%'],
    'Value': [4563.00, 1105.68, 5682.75, 2982.00, 880.80, 17505.60, 3251.60]
}

df_portfolio = pd.DataFrame(portfolio_data)

# Portfolio metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Portfolio Value",
        value="₦35,971.43",
        delta="₦1,247.89 (+3.59%)"
    )

with col2:
    st.metric(
        label="Today's Change",
        value="₦847.23",
        delta="+2.41%"
    )

with col3:
    st.metric(
        label="Total Positions",
        value="7",
        delta="2 new this week"
    )

with col4:
    st.metric(
        label="Buying Power",
        value="₦9,203.36",
        delta="Available"
    )

# Portfolio allocation chart
fig_pie = px.pie(
    df_portfolio, 
    values='Value', 
    names='Symbol',
    title='Portfolio Allocation by Holdings',
    color_discrete_sequence=px.colors.qualitative.Set3
)
fig_pie.update_traces(textposition='inside', textinfo='percent+label')
fig_pie.update_layout(height=400)

col1, col2 = st.columns([1, 1])

with col1:
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    # Performance chart
    dates = pd.date_range(start='2024-01-01', end='2024-08-13', freq='D')
    portfolio_values = np.cumsum(np.random.randn(len(dates)) * 50) + 30000
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=dates,
        y=portfolio_values,
        mode='lines',
        name='Portfolio Value',
        line=dict(color='#059669', width=3)
    ))
    fig_line.update_layout(
        title='Portfolio Performance (YTD)',
        xaxis_title='Date',
        yaxis_title='Portfolio Value (₦)',
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_line, use_container_width=True)

# Holdings table
st.markdown("### 📈 Current Holdings")
st.dataframe(
    df_portfolio,
    column_config={
        "Symbol": st.column_config.TextColumn("Symbol", width="small"),
        "Company": st.column_config.TextColumn("Company", width="large"),
        "Shares": st.column_config.NumberColumn("Shares", format="%d"),
        "Price": st.column_config.NumberColumn("Price", format="₦%.2f"),
        "Change": st.column_config.TextColumn("Change", width="small"),
        "Value": st.column_config.NumberColumn("Market Value", format="₦%.2f"),
    },
    hide_index=True,
    use_container_width=True
)

# Market overview
st.markdown("---")
st.markdown("## 📊 Market Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("S&P 500", "4,471.07", "+23.45 (+0.53%)")
    st.metric("NASDAQ", "13,722.02", "+87.65 (+0.64%)")

with col2:
    st.metric("DOW JONES", "34,837.71", "+156.82 (+0.45%)")
    st.metric("RUSSELL 2000", "2,084.43", "+12.33 (+0.59%)")

with col3:
    st.metric("VIX", "13.45", "-0.87 (-6.08%)")
    st.metric("10Y Treasury", "4.23%", "+0.02 (+0.47%)")

# Watchlist
st.markdown("---")
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("## 👀 Watchlist")
    
    watchlist_data = {
        'Symbol': ['NFLX', 'CRM', 'SHOP', 'SQ', 'ZOOM'],
        'Company': ['Netflix Inc.', 'Salesforce Inc.', 'Shopify Inc.', 'Block Inc.', 'Zoom Video'],
        'Price': [445.23, 245.67, 67.89, 58.34, 64.12],
        'Change': ['+2.34%', '-1.23%', '+5.67%', '+3.21%', '-0.45%'],
        'Alert': ['📈', '📉', '🚀', '📈', '⚠️']
    }
    
    watchlist_df = pd.DataFrame(watchlist_data)
    st.dataframe(watchlist_df, hide_index=True, use_container_width=True)

with col2:
    st.markdown("## 📰 Market News")
    
    news_items = [
        {
            'title': 'Fed Hints at Rate Cuts',
            'time': '2 hours ago',
            'source': 'Reuters'
        },
        {
            'title': 'Tech Earnings Beat Expectations',
            'time': '4 hours ago',
            'source': 'Bloomberg'
        },
        {
            'title': 'Oil Prices Surge on Supply Concerns',
            'time': '6 hours ago',
            'source': 'WSJ'
        },
        {
            'title': 'Crypto Rally Continues',
            'time': '8 hours ago',
            'source': 'CNBC'
        }
    ]
    
    for news in news_items:
        st.markdown(f"""
        <div class="news-item">
            <strong>{news['title']}</strong><br>
            <small style="color: #6b7280;">{news['time']} • {news['source']}</small>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown("""
    <div style='text-align: center; color: #6b7280; font-size: 0.9rem;'>
        <p>© 2024 TradeMax Pro. All rights reserved. | 
        <a href='#'>Terms</a> | 
        <a href='#'>Privacy</a> | 
        <a href='#'>Contact</a></p>
        <p>Securities offered through TradeMax Securities LLC, Member FINRA/SIPC</p>
    </div>
    """, unsafe_allow_html=True)
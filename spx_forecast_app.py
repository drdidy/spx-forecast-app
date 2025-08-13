import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

# Page configuration
st.set_page_config(
    page_title="TradeMaster Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
    }
    .positive-change {
        color: #16a34a;
        font-weight: bold;
    }
    .negative-change {
        color: #dc2626;
        font-weight: bold;
    }
    .sidebar-content {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .portfolio-summary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    .trade-button {
        background-color: #16a34a;
        color: white;
        padding: 0.5rem 2rem;
        border: none;
        border-radius: 5px;
        font-weight: bold;
        cursor: pointer;
    }
    .market-status {
        background-color: #16a34a;
        color: white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1 style="color: white; margin: 0; display: flex; align-items: center;">
        📈 TradeMaster Pro
        <span style="margin-left: auto; font-size: 0.6em; background-color: rgba(255,255,255,0.2); padding: 0.3rem 1rem; border-radius: 20px;">
            Market Open
        </span>
    </h1>
    <p style="color: #e2e8f0; margin: 0.5rem 0 0 0;">Professional Trading Platform</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## Account Dashboard")
    
    st.markdown("""
    <div class="sidebar-content">
        <h4>Quick Actions</h4>
        <button class="trade-button">🛒 Buy Stocks</button><br><br>
        <button class="trade-button">🏷️ Sell Stocks</button><br><br>
        <button class="trade-button">📊 View Reports</button>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Market Status")
    st.markdown('<span class="market-status">🟢 Markets Open</span>', unsafe_allow_html=True)
    st.write(f"**Current Time:** {datetime.now().strftime('%I:%M %p ET')}")
    
    st.markdown("### Quick Stats")
    st.metric("S&P 500", "4,832.12", "12.34 (0.26%)")
    st.metric("NASDAQ", "15,180.43", "-5.67 (-0.04%)")
    st.metric("DOW", "37,689.54", "89.23 (0.24%)")

# Main content
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Portfolio Value",
        value="$9,203.36",
        delta="$630.24 (7.36%)",
        delta_color="normal"
    )

with col2:
    st.metric(
        label="Today's Change",
        value="$630.24",
        delta="7.36%",
        delta_color="normal"
    )

with col3:
    st.metric(
        label="Available Cash",
        value="$1,247.89",
        delta="Ready to invest"
    )

with col4:
    st.metric(
        label="Total Return",
        value="$2,891.47",
        delta="45.76%",
        delta_color="normal"
    )

# Portfolio Summary Section
st.markdown("## Portfolio Overview")

col1, col2 = st.columns([2, 1])

with col1:
    # Generate sample portfolio performance data
    dates = pd.date_range(start=datetime.now() - timedelta(days=90), end=datetime.now(), freq='D')
    base_value = 8500
    returns = np.random.normal(0.001, 0.02, len(dates))
    portfolio_values = [base_value]
    
    for return_rate in returns[1:]:
        portfolio_values.append(portfolio_values[-1] * (1 + return_rate))
    
    # Ensure the last value is our target portfolio value
    portfolio_values[-1] = 9203.36
    
    df = pd.DataFrame({
        'Date': dates,
        'Portfolio Value': portfolio_values
    })
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Portfolio Value'],
        mode='lines',
        name='Portfolio Value',
        line=dict(color='#3b82f6', width=3),
        fill='tonexty',
        fillcolor='rgba(59, 130, 246, 0.1)'
    ))
    
    fig.update_layout(
        title="Portfolio Performance (90 Days)",
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        height=400,
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    fig.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # Asset allocation pie chart
    assets = {
        'Technology': 35.2,
        'Healthcare': 18.7,
        'Financial': 15.3,
        'Consumer Goods': 12.8,
        'Energy': 8.9,
        'Cash': 9.1
    }
    
    fig_pie = go.Figure(data=[go.Pie(
        labels=list(assets.keys()),
        values=list(assets.values()),
        hole=.4,
        marker_colors=['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#6b7280']
    )])
    
    fig_pie.update_layout(
        title="Asset Allocation",
        height=400,
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5)
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

# Holdings Table
st.markdown("## Current Holdings")

holdings_data = {
    'Symbol': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'JNJ', 'V', 'WMT'],
    'Company': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.', 'Amazon.com Inc.', 
                'Tesla Inc.', 'NVIDIA Corp.', 'Meta Platforms', 'Johnson & Johnson', 
                'Visa Inc.', 'Walmart Inc.'],
    'Shares': [15, 8, 3, 5, 12, 6, 7, 20, 9, 25],
    'Current Price': [189.84, 428.67, 2734.23, 147.92, 248.50, 875.30, 325.67, 
                      168.45, 267.89, 159.32],
    'Market Value': [2847.60, 3429.36, 8202.69, 739.60, 2982.00, 5251.80, 
                     2279.69, 3369.00, 2411.01, 3983.00],
    'Day Change': ['+2.34%', '+1.87%', '+3.21%', '-0.45%', '+4.67%', '+2.91%', 
                   '+1.23%', '-0.12%', '+0.78%', '+1.45%']
}

holdings_df = pd.DataFrame(holdings_data)

# Format the dataframe for better display
formatted_df = holdings_df.copy()
formatted_df['Current Price'] = formatted_df['Current Price'].apply(lambda x: f"${x:.2f}")
formatted_df['Market Value'] = formatted_df['Market Value'].apply(lambda x: f"${x:.2f}")

st.dataframe(
    formatted_df,
    use_container_width=True,
    hide_index=True
)

# Recent Activity
st.markdown("## Recent Activity")

activity_data = {
    'Date': [datetime.now().strftime('%m/%d/%Y')] * 4,
    'Time': ['09:32 AM', '10:45 AM', '02:15 PM', '03:28 PM'],
    'Action': ['BUY', 'SELL', 'BUY', 'DIVIDEND'],
    'Symbol': ['NVDA', 'AAPL', 'MSFT', 'JNJ'],
    'Quantity': [2, 5, 3, '-'],
    'Price': ['$875.30', '$187.50', '$426.80', '$0.68/share'],
    'Amount': ['+$1,750.60', '-$937.50', '+$1,280.40', '+$13.60']
}

activity_df = pd.DataFrame(activity_data)
st.dataframe(activity_df, use_container_width=True, hide_index=True)

# Market News
st.markdown("## Market News & Insights")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **📈 Tech Stocks Rally on AI Optimism**
    *2 hours ago*
    
    Technology shares continued their upward momentum as investors remain bullish on artificial intelligence developments...
    
    **🏦 Federal Reserve Maintains Interest Rates**
    *4 hours ago*
    
    The Federal Reserve decided to keep interest rates unchanged, citing economic stability and inflation targets...
    
    **⚡ Energy Sector Shows Mixed Results**
    *6 hours ago*
    
    Oil prices fluctuated amid global supply chain concerns, affecting energy sector performance...
    """)

with col2:
    st.markdown("""
    **💼 Earnings Season Highlights**
    *1 hour ago*
    
    Several major companies reported stronger-than-expected quarterly earnings, boosting market confidence...
    
    **🌐 Global Markets Update**
    *3 hours ago*
    
    International markets showed resilience despite geopolitical tensions affecting certain sectors...
    
    **📊 Market Analysis: Q3 Outlook**
    *5 hours ago*
    
    Analysts project continued growth in the third quarter, with particular strength in technology and healthcare...
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; padding: 1rem;">
    <p>TradeMaster Pro • Professional Trading Platform • 
    <a href="#" style="color: #3b82f6;">Support</a> • 
    <a href="#" style="color: #3b82f6;">Privacy Policy</a> • 
    <a href="#" style="color: #3b82f6;">Terms of Service</a></p>
    <p><small>Investment products and services are provided by TradeMaster Securities LLC, Member FINRA/SIPC.</small></p>
</div>
""", unsafe_allow_html=True)
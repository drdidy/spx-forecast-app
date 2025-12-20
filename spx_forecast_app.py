"""
Alpha Vantage Data Test
"""

import streamlit as st
import requests

st.set_page_config(page_title="Alpha Vantage Test", layout="wide")

st.title("Alpha Vantage Data Test")

API_KEY = st.text_input("Enter your Alpha Vantage API Key", type="password")

if API_KEY and st.button("Test Data"):
    
    st.markdown("---")
    
    # Test symbols
    symbols = ["SPX", "^GSPC", "$SPX", "SPY", "VIX", "^VIX", "$VIX", "VIXY"]
    
    for symbol in symbols:
        st.markdown(f"### {symbol}")
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if "Global Quote" in data and data["Global Quote"]:
                quote = data["Global Quote"]
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Price", quote.get("05. price", "N/A"))
                col2.metric("High", quote.get("03. high", "N/A"))
                col3.metric("Low", quote.get("04. low", "N/A"))
                col4.metric("Prev Close", quote.get("08. previous close", "N/A"))
            else:
                st.warning(f"No data: {data}")
        except Exception as e:
            st.error(f"Error: {e}")
        
        st.markdown("---")
    
    st.markdown("### Compare with your source:")
    st.markdown("**What does YOUR source show for SPX and VIX right now?**")
    
    col1, col2 = st.columns(2)
    with col1:
        your_spx = st.number_input("Your SPX Price", value=0.0)
    with col2:
        your_vix = st.number_input("Your VIX Price", value=0.0)
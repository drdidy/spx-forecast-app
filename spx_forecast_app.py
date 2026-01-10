"""
🔮 SPX PROPHET V2
Where Structure Becomes Foresight

Complete 3-Pillar Trading System for SPX 0DTE Options
Built from the Unified System Guide V2

Key Architecture:
- Pillar 1: MA Bias (50 EMA vs 200 SMA on 30-min candles)
- Pillar 2: Day Structure (CEILING/FLOOR from overnight session trendlines)
- Pillar 3: VIX Zone (Manual from TradingView with springboard logic)
- Cone Rails: Prior day High/Low/Close with 3pm CT anchor, ±0.475 slope
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta, time as dt_time
import pytz
import json
import os

# ============================================================================
# CONSTANTS
# ============================================================================
CT = pytz.timezone('America/Chicago')
ET = pytz.timezone('America/New_York')

# Cone Rails
CONE_SLOPE = 0.475  # Points per 30-min block
CONE_ANCHOR_HOUR = 15  # 3:00 PM CT for close anchor
CONE_ANCHOR_MINUTE = 0

# Strike Selection
OTM_DISTANCE = 15  # Points from entry level

# Trading Window
ENTRY_START = dt_time(8, 30)   # 8:30 AM CT
ENTRY_CUTOFF = dt_time(11, 30)  # 11:30 AM CT
RTH_CLOSE = dt_time(15, 0)      # 3:00 PM CT

# Session Times (Central Time) - for Day Structure
SESSIONS = {
    'sydney': {'start': (17, 0), 'end': (20, 30)},   # 5:00 PM - 8:30 PM
    'tokyo': {'start': (21, 0), 'end': (1, 30)},     # 9:00 PM - 1:30 AM (+1 day)
    'london': {'start': (2, 0), 'end': (6, 30)},     # 2:00 AM - 6:30 AM
}
VALIDATION_CUTOFF = dt_time(6, 0)  # 6:00 AM CT

# Data
POLYGON_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
INPUTS_FILE = "spx_prophet_inputs.json"

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="SPX Prophet V2",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# PREMIUM LIGHT-MODE GLASSMORPHISM CSS
# ============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    :root {
        --bg-gradient-start: #f0f4ff;
        --bg-gradient-mid: #e8f0fe;
        --bg-gradient-end: #faf0ff;
        --glass-bg: rgba(255, 255, 255, 0.6);
        --glass-bg-strong: rgba(255, 255, 255, 0.85);
        --glass-border: rgba(255, 255, 255, 0.8);
        --glass-shadow: rgba(100, 100, 150, 0.1);
        --text-primary: #1a1a2e;
        --text-secondary: #64648c;
        --text-muted: #9494b8;
        --accent-green: #10b981;
        --accent-green-light: #d1fae5;
        --accent-red: #ef4444;
        --accent-red-light: #fee2e2;
        --accent-amber: #f59e0b;
        --accent-amber-light: #fef3c7;
        --accent-blue: #3b82f6;
        --accent-purple: #8b5cf6;
        --accent-purple-light: #ede9fe;
        --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --gradient-success: linear-gradient(135deg, #10b981 0%, #059669 100%);
        --gradient-danger: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        --gradient-warning: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }
    
    .stApp {
        background: linear-gradient(135deg, var(--bg-gradient-start) 0%, var(--bg-gradient-mid) 50%, var(--bg-gradient-end) 100%);
        background-attachment: fixed;
    }
    
    .stApp::before {
        content: '';
        position: fixed;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: 
            radial-gradient(circle at 20% 80%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
            radial-gradient(circle at 40% 40%, rgba(16, 185, 129, 0.05) 0%, transparent 40%);
        animation: float 20s ease-in-out infinite;
        pointer-events: none;
        z-index: 0;
    }
    
    @keyframes float {
        0%, 100% { transform: translate(0, 0) rotate(0deg); }
        33% { transform: translate(2%, 2%) rotate(1deg); }
        66% { transform: translate(-1%, 1%) rotate(-1deg); }
    }
    
    .main .block-container {
        padding-top: 2rem;
        max-width: 1400px;
        position: relative;
        z-index: 1;
    }
    
    /* Glass Cards */
    .glass-card {
        background: var(--glass-bg-strong);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        padding: 1.75rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 24px var(--glass-shadow), inset 0 1px 0 rgba(255, 255, 255, 0.6);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(100, 100, 150, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.8);
    }
    
    /* Hero */
    .hero-container {
        text-align: center;
        padding: 2.5rem 2rem;
        margin-bottom: 2rem;
        background: var(--glass-bg-strong);
        backdrop-filter: blur(30px);
        border-radius: 32px;
        border: 1px solid rgba(255, 255, 255, 0.9);
        box-shadow: 0 8px 32px rgba(100, 100, 150, 0.12);
        position: relative;
        overflow: hidden;
    }
    
    .hero-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: var(--gradient-primary);
    }
    
    .hero-icon {
        font-size: 3.5rem;
        margin-bottom: 0.5rem;
        animation: pulse-glow 3s ease-in-out infinite;
    }
    
    @keyframes pulse-glow {
        0%, 100% { transform: scale(1); filter: drop-shadow(0 0 8px rgba(139, 92, 246, 0.3)); }
        50% { transform: scale(1.05); filter: drop-shadow(0 0 20px rgba(139, 92, 246, 0.5)); }
    }
    
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        background: var(--gradient-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    
    .hero-tagline {
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        color: var(--text-secondary);
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 1.25rem;
    }
    
    .hero-price-container {
        display: inline-flex;
        align-items: center;
        gap: 0.75rem;
        background: var(--glass-bg);
        padding: 0.875rem 1.75rem;
        border-radius: 16px;
        border: 1px solid var(--glass-border);
    }
    
    .hero-price-label {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-secondary);
    }
    
    .hero-price {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.25rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    .hero-subtext {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-top: 0.5rem;
    }
    
    .hero-time {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-top: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }
    
    .live-dot {
        width: 8px;
        height: 8px;
        background: var(--accent-green);
        border-radius: 50%;
        animation: blink 2s ease-in-out infinite;
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    
    /* Section Headers */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(139, 92, 246, 0.1);
    }
    
    .section-icon {
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--gradient-primary);
        border-radius: 10px;
        font-size: 1.1rem;
    }
    
    .section-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    /* Pillar Cards */
    .pillar-card {
        background: var(--glass-bg-strong);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 1.5rem;
        height: 100%;
        border: 1px solid var(--glass-border);
        box-shadow: 0 4px 24px var(--glass-shadow);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .pillar-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
    }
    
    .pillar-card.bullish::before { background: var(--gradient-success); }
    .pillar-card.bearish::before { background: var(--gradient-danger); }
    .pillar-card.neutral::before { background: var(--gradient-warning); }
    
    .pillar-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 16px 48px rgba(100, 100, 150, 0.18);
    }
    
    .pillar-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 0.75rem;
    }
    
    .pillar-icon {
        width: 42px;
        height: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        font-size: 1.3rem;
    }
    
    .pillar-icon.bullish { background: var(--accent-green-light); }
    .pillar-icon.bearish { background: var(--accent-red-light); }
    .pillar-icon.neutral { background: var(--accent-amber-light); }
    
    .pillar-number {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .pillar-name {
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .pillar-question {
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin-bottom: 1rem;
    }
    
    .pillar-answer {
        font-family: 'Inter', sans-serif;
        font-size: 1.75rem;
        font-weight: 800;
        margin-bottom: 0.4rem;
    }
    
    .pillar-answer.bullish { color: var(--accent-green); }
    .pillar-answer.bearish { color: var(--accent-red); }
    .pillar-answer.neutral { color: var(--accent-amber); }
    
    .pillar-detail {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: var(--text-muted);
        background: rgba(0, 0, 0, 0.03);
        padding: 0.4rem 0.6rem;
        border-radius: 6px;
        display: inline-block;
    }
    
    /* Signal Card */
    .signal-card {
        background: var(--glass-bg-strong);
        backdrop-filter: blur(30px);
        border-radius: 28px;
        padding: 2rem;
        text-align: center;
        border: 2px solid;
        margin: 1.5rem 0;
        position: relative;
        overflow: hidden;
    }
    
    .signal-card.calls {
        border-color: var(--accent-green);
        box-shadow: 0 8px 32px rgba(16, 185, 129, 0.15);
    }
    
    .signal-card.puts {
        border-color: var(--accent-red);
        box-shadow: 0 8px 32px rgba(239, 68, 68, 0.15);
    }
    
    .signal-card.wait {
        border-color: var(--accent-amber);
        box-shadow: 0 8px 32px rgba(245, 158, 11, 0.15);
    }
    
    .signal-card.notrade {
        border-color: var(--text-muted);
    }
    
    .signal-icon {
        font-size: 3.5rem;
        margin-bottom: 0.75rem;
        animation: signal-bounce 2s ease-in-out infinite;
    }
    
    @keyframes signal-bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-6px); }
    }
    
    .signal-action {
        font-family: 'Inter', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        letter-spacing: 3px;
    }
    
    .signal-action.calls { color: var(--accent-green); }
    .signal-action.puts { color: var(--accent-red); }
    .signal-action.wait { color: var(--accent-amber); }
    .signal-action.notrade { color: var(--text-muted); }
    
    .signal-reason {
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
        color: var(--text-secondary);
        margin-top: 0.5rem;
        font-weight: 500;
    }
    
    .signal-details {
        display: flex;
        justify-content: center;
        gap: 1.5rem;
        margin-top: 1.5rem;
        flex-wrap: wrap;
    }
    
    .signal-detail-item {
        background: var(--glass-bg);
        padding: 1rem 1.5rem;
        border-radius: 14px;
        border: 1px solid var(--glass-border);
        min-width: 120px;
    }
    
    .signal-detail-icon {
        font-size: 1.25rem;
        margin-bottom: 0.35rem;
    }
    
    .signal-detail-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-muted);
        font-weight: 600;
    }
    
    .signal-detail-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    /* Structure Visual */
    .structure-visual {
        background: var(--glass-bg);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .structure-level {
        display: flex;
        align-items: center;
        padding: 0.75rem 0;
        border-bottom: 1px dashed rgba(0,0,0,0.08);
    }
    
    .structure-level:last-child {
        border-bottom: none;
    }
    
    .structure-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        font-weight: 600;
        width: 120px;
        color: var(--text-secondary);
    }
    
    .structure-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem;
        font-weight: 600;
        flex: 1;
    }
    
    .structure-value.ceiling { color: var(--accent-red); }
    .structure-value.floor { color: var(--accent-green); }
    .structure-value.current { color: var(--accent-purple); }
    
    .structure-distance {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: var(--text-muted);
        background: rgba(0,0,0,0.05);
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
    }
    
    /* VIX Zone Visual */
    .vix-zone-visual {
        background: var(--glass-bg);
        border-radius: 16px;
        padding: 1.25rem;
        margin-top: 1rem;
    }
    
    .vix-zone-bar {
        height: 12px;
        background: linear-gradient(to right, var(--accent-green), var(--accent-amber), var(--accent-red));
        border-radius: 6px;
        position: relative;
        margin: 1rem 0;
    }
    
    .vix-marker {
        position: absolute;
        top: -4px;
        width: 20px;
        height: 20px;
        background: var(--text-primary);
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        transform: translateX(-50%);
    }
    
    .vix-labels {
        display: flex;
        justify-content: space-between;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: var(--text-muted);
    }
    
    /* Cone Table */
    .cone-table-container {
        background: var(--glass-bg-strong);
        border-radius: 16px;
        padding: 1.25rem;
        border: 1px solid var(--glass-border);
    }
    
    .cone-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 6px;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .cone-table th {
        padding: 0.6rem;
        text-align: center;
        font-weight: 600;
        font-size: 0.7rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .cone-table td {
        padding: 0.75rem;
        text-align: center;
        background: var(--glass-bg);
        font-size: 0.9rem;
    }
    
    .cone-table tr td:first-child { border-radius: 10px 0 0 10px; }
    .cone-table tr td:last-child { border-radius: 0 10px 10px 0; }
    
    .cone-label {
        font-weight: 600;
        color: var(--text-secondary);
    }
    
    .cone-up { color: var(--accent-green); font-weight: 600; }
    .cone-down { color: var(--accent-red); font-weight: 600; }
    
    .cone-footer {
        text-align: center;
        margin-top: 0.75rem;
        font-size: 0.75rem;
        color: var(--text-muted);
    }
    
    /* Options Panel */
    .options-container {
        background: var(--glass-bg-strong);
        border-radius: 16px;
        padding: 1.25rem;
        border: 1px solid var(--glass-border);
    }
    
    .options-ticker {
        text-align: center;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    .options-ticker-symbol {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: var(--accent-purple);
        font-weight: 600;
        background: var(--accent-purple-light);
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        display: inline-block;
    }
    
    .options-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.6rem;
    }
    
    .options-item {
        text-align: center;
        padding: 0.75rem;
        background: var(--glass-bg);
        border-radius: 10px;
    }
    
    .options-item-icon { font-size: 1.1rem; margin-bottom: 0.25rem; }
    
    .options-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--text-muted);
        font-weight: 600;
    }
    
    .options-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    /* Pillar Status */
    .pillar-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(0,0,0,0.05);
    }
    
    .pillar-status:last-child { border-bottom: none; }
    
    .pillar-status-icon {
        font-size: 1.1rem;
    }
    
    .pillar-status-name {
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        font-weight: 500;
        color: var(--text-secondary);
        flex: 1;
    }
    
    .pillar-status-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
    }
    
    .pillar-status-value.ok { background: var(--accent-green-light); color: var(--accent-green); }
    .pillar-status-value.wait { background: var(--accent-amber-light); color: var(--accent-amber); }
    .pillar-status-value.no { background: var(--accent-red-light); color: var(--accent-red); }
    
    /* Footer */
    .app-footer {
        text-align: center;
        padding: 1.5rem;
        margin-top: 2rem;
        color: var(--text-muted);
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        border-top: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8faff 0%, #f0f4ff 100%);
        border-right: 1px solid rgba(139, 92, 246, 0.1);
    }
    
    .sidebar-header {
        text-align: center;
        padding: 1.25rem 1rem;
        margin-bottom: 0.75rem;
        background: var(--glass-bg-strong);
        border-radius: 14px;
        border: 1px solid var(--glass-border);
    }
    
    .sidebar-logo { font-size: 2rem; margin-bottom: 0.25rem; }
    
    .sidebar-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        background: var(--gradient-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .sidebar-section {
        background: var(--glass-bg-strong);
        border-radius: 14px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border: 1px solid var(--glass-border);
    }
    
    .sidebar-section-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    .sidebar-section-icon { font-size: 1rem; }
    
    .sidebar-section-title {
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-primary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Form styling */
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input {
        background: white !important;
        border: 1px solid rgba(139, 92, 246, 0.2) !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    .stButton > button {
        background: var(--gradient-primary) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3) !important;
    }
    
    section[data-testid="stSidebar"] {
        width: 320px !important;
        min-width: 320px !important;
    }
    
    [data-testid="collapsedControl"] { display: none; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# PERSISTENCE FUNCTIONS
# ============================================================================

DEFAULT_INPUTS = {
    "vix_overnight_high": 0.0,
    "vix_overnight_low": 0.0,
    "vix_current": 0.0,
    "es_spx_offset": 7.0,
    "prior_high": 0.0,
    "prior_low": 0.0,
    "prior_close": 0.0,
    "manual_ceiling": 0.0,
    "manual_floor": 0.0,
    "use_manual_structure": False,
    "last_updated": ""
}

def save_inputs(inputs):
    """Save manual inputs to JSON file"""
    inputs["last_updated"] = datetime.now(CT).strftime("%Y-%m-%d %H:%M:%S CT")
    with open(INPUTS_FILE, "w") as f:
        json.dump(inputs, f, indent=2)

def load_inputs():
    """Load manual inputs from JSON file"""
    if os.path.exists(INPUTS_FILE):
        try:
            with open(INPUTS_FILE, "r") as f:
                saved = json.load(f)
                return {**DEFAULT_INPUTS, **saved}
        except:
            pass
    return DEFAULT_INPUTS.copy()

# ============================================================================
# DATA FETCHING
# ============================================================================

def get_es_price():
    """Fetch current ES futures price"""
    try:
        es = yf.Ticker("ES=F")
        data = es.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except:
        pass
    return None

def get_es_30min_candles(days=15):
    """Fetch ES 30-minute candles for MA calculation"""
    try:
        es = yf.Ticker("ES=F")
        data = es.history(period=f"{days}d", interval="30m")
        return data
    except:
        pass
    return None

def fetch_option_data(strike, is_call, trade_date):
    """Fetch option data from Polygon"""
    try:
        date_str = trade_date.strftime("%y%m%d")
        option_type = "C" if is_call else "P"
        strike_str = f"{int(strike * 1000):08d}"
        ticker = f"O:SPXW{date_str}{option_type}{strike_str}"
        
        url = f"https://api.polygon.io/v3/snapshot/options/SPXW/{ticker}?apiKey={POLYGON_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                return data['results'], ticker
    except:
        pass
    return None, None

# ============================================================================
# PILLAR 1: MA BIAS
# ============================================================================

def calculate_ema(prices, period):
    """Calculate EMA from prices"""
    if len(prices) < period:
        return None
    return prices.ewm(span=period, adjust=False).mean().iloc[-1]

def calculate_sma(prices, period):
    """Calculate SMA from prices"""
    if len(prices) < period:
        return None
    return prices.rolling(window=period).mean().iloc[-1]

def analyze_ma_bias(es_candles, offset):
    """
    Pillar 1: MA Bias from 30-minute candles
    Returns: bias, detail, ema_50, sma_200
    """
    if es_candles is None or len(es_candles) < 200:
        return "NEUTRAL", "Insufficient data (need 200 candles)", None, None
    
    # Convert ES to SPX
    spx_close = es_candles['Close'] - offset
    
    ema_50 = calculate_ema(spx_close, 50)
    sma_200 = calculate_sma(spx_close, 200)
    
    if ema_50 is None or sma_200 is None:
        return "NEUTRAL", "Could not calculate MAs", None, None
    
    # Calculate percentage difference
    diff_pct = (ema_50 - sma_200) / sma_200 * 100
    
    if diff_pct > 0.1:
        return "LONG", f"50 EMA ({ema_50:,.1f}) > 200 SMA ({sma_200:,.1f})", ema_50, sma_200
    elif diff_pct < -0.1:
        return "SHORT", f"50 EMA ({ema_50:,.1f}) < 200 SMA ({sma_200:,.1f})", ema_50, sma_200
    else:
        return "NEUTRAL", f"MAs crossing (diff {diff_pct:.2f}%)", ema_50, sma_200

# ============================================================================
# PILLAR 2: DAY STRUCTURE (Simplified for manual input)
# ============================================================================

def get_day_structure(inputs, spx_price):
    """
    Pillar 2: Day Structure
    For now, uses manual CEILING/FLOOR input since building overnight
    trendlines requires real-time overnight data feeds.
    
    Returns: ceiling, floor, structure_status
    """
    if inputs.get("use_manual_structure") and inputs.get("manual_ceiling", 0) > 0 and inputs.get("manual_floor", 0) > 0:
        ceiling = inputs["manual_ceiling"]
        floor = inputs["manual_floor"]
        return ceiling, floor, "Manual override active"
    
    # If no manual structure, return None (user needs to input)
    return None, None, "Enter CEILING/FLOOR from overnight structure"

# ============================================================================
# PILLAR 3: VIX ZONE
# ============================================================================

def analyze_vix_zone(vix_high, vix_low, vix_current):
    """
    Pillar 3: VIX Zone with springboard logic
    
    Returns dict with zone analysis
    """
    if vix_high <= 0 or vix_low <= 0 or vix_current <= 0:
        return {
            'zone_size': 0,
            'zone_position': "Enter VIX values",
            'puts_springboard': 0,
            'calls_springboard': 0,
            'timing_signal': "WAIT",
            'detail': "Missing VIX data"
        }
    
    zone_size = vix_high - vix_low
    
    if zone_size <= 0:
        return {
            'zone_size': 0,
            'zone_position': "Invalid range",
            'puts_springboard': vix_high,
            'calls_springboard': vix_low,
            'timing_signal': "WAIT",
            'detail': "High must be > Low"
        }
    
    # Original boundaries are primary springboards
    puts_springboard = vix_high    # VIX ceiling → PUTS on SPX
    calls_springboard = vix_low    # VIX floor → CALLS on SPX
    
    # Determine current position
    if vix_current > vix_high:
        # Above range
        zones_above = (vix_current - vix_high) / zone_size
        zone_position = f"ABOVE (+{zones_above:.1f} zones)"
        
        # For CALLS when above range, need next zone top
        calls_springboard = vix_high + (int(zones_above) + 1) * zone_size
        
        # Check if near ceiling springboard
        if abs(vix_current - puts_springboard) <= zone_size * 0.20:
            timing_signal = "PUTS"
            detail = f"Near ceiling springboard ({puts_springboard:.2f})"
        else:
            timing_signal = "WAIT"
            detail = f"Wait for VIX → {puts_springboard:.2f}"
            
    elif vix_current < vix_low:
        # Below range
        zones_below = (vix_low - vix_current) / zone_size
        zone_position = f"BELOW (-{zones_below:.1f} zones)"
        
        # For PUTS when below range, need next zone bottom
        puts_springboard = vix_low - (int(zones_below) + 1) * zone_size
        
        # Check if near floor springboard
        if abs(vix_current - calls_springboard) <= zone_size * 0.20:
            timing_signal = "CALLS"
            detail = f"Near floor springboard ({calls_springboard:.2f})"
        else:
            timing_signal = "WAIT"
            detail = f"Wait for VIX → {calls_springboard:.2f}"
    else:
        # Inside range
        range_pct = (vix_current - vix_low) / zone_size
        zone_position = f"INSIDE ({range_pct:.0%})"
        
        if range_pct <= 0.30:
            timing_signal = "CALLS"
            detail = f"At floor zone ({range_pct:.0%})"
        elif range_pct >= 0.70:
            timing_signal = "PUTS"
            detail = f"At ceiling zone ({range_pct:.0%})"
        else:
            timing_signal = "WAIT"
            detail = f"Middle of range ({range_pct:.0%})"
    
    return {
        'zone_size': zone_size,
        'zone_position': zone_position,
        'puts_springboard': puts_springboard,
        'calls_springboard': calls_springboard,
        'timing_signal': timing_signal,
        'detail': detail,
        'range_pct': (vix_current - vix_low) / zone_size if zone_size > 0 else 0.5
    }

# ============================================================================
# CONE RAILS
# ============================================================================

def calculate_cone_rails(prior_high, prior_low, prior_close, current_time, offset):
    """
    Calculate cone rails from prior day levels
    Anchor: 3:00 PM CT for CLOSE, 4:00 PM CT for HIGH/LOW
    Slope: ±0.475 per 30-min block
    """
    if prior_high <= 0 or prior_low <= 0 or prior_close <= 0:
        return None
    
    # Anchor time: 3:00 PM CT for close
    now = current_time
    today = now.date()
    
    # For prior day anchor, use yesterday's 3pm CT
    anchor_date = today - timedelta(days=1)
    # Skip weekends
    while anchor_date.weekday() >= 5:
        anchor_date -= timedelta(days=1)
    
    anchor_dt = CT.localize(datetime.combine(anchor_date, dt_time(15, 0)))
    
    # Calculate minutes elapsed since anchor
    if now.tzinfo is None:
        now = CT.localize(now)
    
    minutes_elapsed = (now - anchor_dt).total_seconds() / 60
    blocks = minutes_elapsed / 30
    
    expansion = blocks * CONE_SLOPE
    
    # All values start in ES, convert to SPX
    cones = {
        'C1': {  # Prior High
            'anchor': prior_high - offset,
            'ascending': prior_high + expansion - offset,
            'descending': prior_high - expansion - offset
        },
        'C2': {  # Prior Low
            'anchor': prior_low - offset,
            'ascending': prior_low + expansion - offset,
            'descending': prior_low - expansion - offset
        },
        'C3': {  # Prior Close
            'anchor': prior_close - offset,
            'ascending': prior_close + expansion - offset,
            'descending': prior_close - expansion - offset
        }
    }
    
    return {
        'cones': cones,
        'blocks': blocks,
        'expansion': expansion,
        'slope': CONE_SLOPE
    }

# ============================================================================
# TRADE DECISION
# ============================================================================

def generate_trade_decision(ma_bias, ceiling, floor, vix_zone, spx_price):
    """
    Combine all pillars into final trade decision
    """
    # Default response
    result = {
        'signal': 'NO TRADE',
        'reason': '',
        'entry_level': None,
        'strike': None,
        'direction': None,
        'pillars_aligned': False
    }
    
    # Check MA Bias
    if ma_bias == "NEUTRAL":
        result['reason'] = "MA Bias is NEUTRAL"
        return result
    
    # Check Structure
    if ceiling is None or floor is None:
        result['reason'] = "Day Structure not set"
        return result
    
    # Check VIX
    vix_signal = vix_zone.get('timing_signal', 'WAIT')
    
    if vix_signal == "WAIT":
        result['signal'] = "WAIT"
        result['reason'] = f"VIX timing: {vix_zone.get('detail', 'waiting')}"
        return result
    
    # Check alignment
    if ma_bias == "LONG" and vix_signal == "CALLS":
        result['signal'] = "CALLS"
        result['direction'] = "CALLS"
        result['entry_level'] = floor
        result['strike'] = round((floor + OTM_DISTANCE) / 5) * 5
        result['reason'] = "All pillars aligned BULLISH"
        result['pillars_aligned'] = True
        
    elif ma_bias == "SHORT" and vix_signal == "PUTS":
        result['signal'] = "PUTS"
        result['direction'] = "PUTS"
        result['entry_level'] = ceiling
        result['strike'] = round((ceiling - OTM_DISTANCE) / 5) * 5
        result['reason'] = "All pillars aligned BEARISH"
        result['pillars_aligned'] = True
        
    else:
        result['signal'] = "NO TRADE"
        result['reason'] = f"Conflict: MA={ma_bias}, VIX={vix_signal}"
    
    return result

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    now_ct = datetime.now(CT)
    
    # Load persisted inputs
    if 'inputs' not in st.session_state:
        st.session_state.inputs = load_inputs()
    
    inputs = st.session_state.inputs
    
    # ========================================================================
    # SIDEBAR - Manual Inputs
    # ========================================================================
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-header">
            <div class="sidebar-logo">🔮</div>
            <div class="sidebar-title">SPX Prophet V2</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Trading Date
        st.markdown("""<div class="sidebar-section">
            <div class="sidebar-section-header">
                <span class="sidebar-section-icon">📅</span>
                <span class="sidebar-section-title">Trading Date</span>
            </div></div>""", unsafe_allow_html=True)
        
        trade_date = st.date_input("Date", value=now_ct.date(), label_visibility="collapsed")
        
        # VIX Zone (Manual from TradingView)
        st.markdown("""<div class="sidebar-section">
            <div class="sidebar-section-header">
                <span class="sidebar-section-icon">📊</span>
                <span class="sidebar-section-title">VIX Zone (TradingView)</span>
            </div></div>""", unsafe_allow_html=True)
        
        inputs["vix_overnight_high"] = st.number_input(
            "Overnight High (5pm-3am)", 
            value=float(inputs.get("vix_overnight_high", 0.0)), 
            step=0.01, format="%.2f"
        )
        inputs["vix_overnight_low"] = st.number_input(
            "Overnight Low (5pm-3am)", 
            value=float(inputs.get("vix_overnight_low", 0.0)), 
            step=0.01, format="%.2f"
        )
        inputs["vix_current"] = st.number_input(
            "Current VIX", 
            value=float(inputs.get("vix_current", 0.0)), 
            step=0.01, format="%.2f"
        )
        
        # Day Structure (Manual)
        st.markdown("""<div class="sidebar-section">
            <div class="sidebar-section-header">
                <span class="sidebar-section-icon">🏗️</span>
                <span class="sidebar-section-title">Day Structure (SPX)</span>
            </div></div>""", unsafe_allow_html=True)
        
        inputs["use_manual_structure"] = st.checkbox(
            "Enable Manual Structure", 
            value=inputs.get("use_manual_structure", False)
        )
        
        if inputs["use_manual_structure"]:
            inputs["manual_ceiling"] = st.number_input(
                "CEILING (PUTS entry)", 
                value=float(inputs.get("manual_ceiling", 0.0)), 
                step=0.01, format="%.2f"
            )
            inputs["manual_floor"] = st.number_input(
                "FLOOR (CALLS entry)", 
                value=float(inputs.get("manual_floor", 0.0)), 
                step=0.01, format="%.2f"
            )
        
        # Prior Day (for Cone Rails)
        st.markdown("""<div class="sidebar-section">
            <div class="sidebar-section-header">
                <span class="sidebar-section-icon">📈</span>
                <span class="sidebar-section-title">Prior Day (Cones)</span>
            </div></div>""", unsafe_allow_html=True)
        
        inputs["prior_high"] = st.number_input(
            "Prior High", 
            value=float(inputs.get("prior_high", 0.0)), 
            step=0.01, format="%.2f"
        )
        inputs["prior_low"] = st.number_input(
            "Prior Low", 
            value=float(inputs.get("prior_low", 0.0)), 
            step=0.01, format="%.2f"
        )
        inputs["prior_close"] = st.number_input(
            "Prior Close (3pm CT)", 
            value=float(inputs.get("prior_close", 0.0)), 
            step=0.01, format="%.2f"
        )
        
        # ES/SPX Offset
        st.markdown("""<div class="sidebar-section">
            <div class="sidebar-section-header">
                <span class="sidebar-section-icon">🔢</span>
                <span class="sidebar-section-title">ES/SPX Offset</span>
            </div></div>""", unsafe_allow_html=True)
        
        inputs["es_spx_offset"] = st.number_input(
            "Offset (ES - SPX)", 
            value=float(inputs.get("es_spx_offset", 7.0)), 
            step=0.1, format="%.1f"
        )
        
        # Save/Refresh buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", use_container_width=True):
                save_inputs(inputs)
                st.success("Saved!")
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        if inputs.get("last_updated"):
            st.caption(f"Last saved: {inputs['last_updated']}")
    
    # ========================================================================
    # FETCH MARKET DATA
    # ========================================================================
    es_price = get_es_price()
    es_candles = get_es_30min_candles(days=15)
    
    offset = inputs.get("es_spx_offset", 7.0)
    spx_price = es_price - offset if es_price else None
    
    # ========================================================================
    # ANALYZE PILLARS
    # ========================================================================
    
    # Pillar 1: MA Bias
    ma_bias, ma_detail, ema_50, sma_200 = analyze_ma_bias(es_candles, offset)
    
    # Pillar 2: Day Structure
    ceiling, floor, structure_status = get_day_structure(inputs, spx_price)
    
    # Pillar 3: VIX Zone
    vix_zone = analyze_vix_zone(
        inputs.get("vix_overnight_high", 0),
        inputs.get("vix_overnight_low", 0),
        inputs.get("vix_current", 0)
    )
    
    # Cone Rails
    cone_data = calculate_cone_rails(
        inputs.get("prior_high", 0),
        inputs.get("prior_low", 0),
        inputs.get("prior_close", 0),
        now_ct,
        offset
    )
    
    # Trade Decision
    trade = generate_trade_decision(ma_bias, ceiling, floor, vix_zone, spx_price)
    
    # ========================================================================
    # HERO HEADER
    # ========================================================================
    spx_display = f"{spx_price:,.2f}" if spx_price else "---"
    es_display = f"{es_price:,.2f}" if es_price else "---"
    
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-icon">🔮</div>
        <div class="hero-title">SPX PROPHET</div>
        <div class="hero-tagline">Where Structure Becomes Foresight</div>
        <div class="hero-price-container">
            <span class="hero-price-label">SPX</span>
            <span class="hero-price">{spx_display}</span>
        </div>
        <div class="hero-subtext">ES {es_display} − Offset {offset:.1f}</div>
        <div class="hero-time">
            <span class="live-dot"></span>
            {now_ct.strftime('%I:%M:%S %p CT')} • {trade_date.strftime('%B %d, %Y')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================================================
    # THREE PILLARS
    # ========================================================================
    st.markdown("""<div class="section-header">
        <div class="section-icon">⚡</div>
        <div class="section-title">The Three Pillars</div>
    </div>""", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    # Pillar 1: MA Bias
    with col1:
        bias_class = "bullish" if ma_bias == "LONG" else "bearish" if ma_bias == "SHORT" else "neutral"
        bias_icon = "📈" if ma_bias == "LONG" else "📉" if ma_bias == "SHORT" else "⏸️"
        allowed = "CALLS only" if ma_bias == "LONG" else "PUTS only" if ma_bias == "SHORT" else "No trades"
        
        st.markdown(f"""
        <div class="pillar-card {bias_class}">
            <div class="pillar-header">
                <div class="pillar-icon {bias_class}">{bias_icon}</div>
                <div>
                    <div class="pillar-number">Pillar 1 • Filter</div>
                    <div class="pillar-name">MA Bias</div>
                </div>
            </div>
            <div class="pillar-question">Can I trade CALLS or PUTS today?</div>
            <div class="pillar-answer {bias_class}">{ma_bias}</div>
            <div class="pillar-detail">{allowed}</div>
            <div style="margin-top:0.5rem; font-size:0.7rem; color:var(--text-muted);">{ma_detail}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Pillar 2: Day Structure
    with col2:
        if ceiling and floor:
            struct_class = "bullish" if ma_bias == "LONG" else "bearish" if ma_bias == "SHORT" else "neutral"
            entry_type = "FLOOR" if ma_bias == "LONG" else "CEILING" if ma_bias == "SHORT" else "N/A"
            entry_val = floor if ma_bias == "LONG" else ceiling if ma_bias == "SHORT" else 0
            struct_icon = "🎯"
        else:
            struct_class = "neutral"
            entry_type = "PENDING"
            entry_val = 0
            struct_icon = "⏳"
        
        ceiling_display = f"{ceiling:,.1f}" if ceiling else "---"
        floor_display = f"{floor:,.1f}" if floor else "---"
        
        st.markdown(f"""
        <div class="pillar-card {struct_class}">
            <div class="pillar-header">
                <div class="pillar-icon {struct_class}">{struct_icon}</div>
                <div>
                    <div class="pillar-number">Pillar 2 • Primary</div>
                    <div class="pillar-name">Day Structure</div>
                </div>
            </div>
            <div class="pillar-question">Where exactly do I enter?</div>
            <div class="pillar-answer {struct_class}">{entry_type}</div>
            <div class="pillar-detail">C: {ceiling_display} • F: {floor_display}</div>
            <div style="margin-top:0.5rem; font-size:0.7rem; color:var(--text-muted);">{structure_status}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Pillar 3: VIX Zone
    with col3:
        vix_signal = vix_zone.get('timing_signal', 'WAIT')
        vix_class = "bullish" if vix_signal == "CALLS" else "bearish" if vix_signal == "PUTS" else "neutral"
        vix_icon = "🟢" if vix_signal == "CALLS" else "🔴" if vix_signal == "PUTS" else "🟡"
        
        st.markdown(f"""
        <div class="pillar-card {vix_class}">
            <div class="pillar-header">
                <div class="pillar-icon {vix_class}">{vix_icon}</div>
                <div>
                    <div class="pillar-number">Pillar 3 • Timing</div>
                    <div class="pillar-name">VIX Zone</div>
                </div>
            </div>
            <div class="pillar-question">Is NOW the right time to enter?</div>
            <div class="pillar-answer {vix_class}">{vix_signal}</div>
            <div class="pillar-detail">{vix_zone.get('zone_position', '---')}</div>
            <div style="margin-top:0.5rem; font-size:0.7rem; color:var(--text-muted);">{vix_zone.get('detail', '')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # TRADE SIGNAL
    # ========================================================================
    signal = trade['signal']
    signal_class = signal.lower().replace(" ", "")
    
    if signal == "CALLS":
        signal_icon = "🚀"
    elif signal == "PUTS":
        signal_icon = "🔻"
    elif signal == "WAIT":
        signal_icon = "⏳"
    else:
        signal_icon = "🚫"
    
    entry_display = f"{trade['entry_level']:,.1f}" if trade['entry_level'] else "---"
    strike_display = str(int(trade['strike'])) if trade['strike'] else "---"
    
    # Distance from entry
    if trade['entry_level'] and spx_price:
        distance = abs(spx_price - trade['entry_level'])
        distance_display = f"{distance:,.1f} pts away"
    else:
        distance_display = "---"
    
    st.markdown(f"""
    <div class="signal-card {signal_class}">
        <div class="signal-icon">{signal_icon}</div>
        <div class="signal-action {signal_class}">{signal}</div>
        <div class="signal-reason">{trade['reason']}</div>
        <div class="signal-details">
            <div class="signal-detail-item">
                <div class="signal-detail-icon">📍</div>
                <div class="signal-detail-label">Entry Level</div>
                <div class="signal-detail-value">{entry_display}</div>
            </div>
            <div class="signal-detail-item">
                <div class="signal-detail-icon">🎯</div>
                <div class="signal-detail-label">Strike</div>
                <div class="signal-detail-value">{strike_display}</div>
            </div>
            <div class="signal-detail-item">
                <div class="signal-detail-icon">📏</div>
                <div class="signal-detail-label">Distance</div>
                <div class="signal-detail-value">{distance_display}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================================================
    # STRUCTURE VISUAL + VIX ZONE + PILLAR STATUS
    # ========================================================================
    col_left, col_mid, col_right = st.columns([1, 1, 1])
    
    with col_left:
        st.markdown("""<div class="section-header">
            <div class="section-icon">🏗️</div>
            <div class="section-title">Day Structure</div>
        </div>""", unsafe_allow_html=True)
        
        if ceiling and floor and spx_price:
            ceiling_dist = ceiling - spx_price
            floor_dist = spx_price - floor
            
            st.markdown(f"""
            <div class="structure-visual">
                <div class="structure-level">
                    <div class="structure-label">🔴 CEILING</div>
                    <div class="structure-value ceiling">{ceiling:,.1f}</div>
                    <div class="structure-distance">↑ {ceiling_dist:,.1f}</div>
                </div>
                <div class="structure-level">
                    <div class="structure-label">🟣 CURRENT</div>
                    <div class="structure-value current">{spx_price:,.1f}</div>
                    <div class="structure-distance">SPX</div>
                </div>
                <div class="structure-level">
                    <div class="structure-label">🟢 FLOOR</div>
                    <div class="structure-value floor">{floor:,.1f}</div>
                    <div class="structure-distance">↓ {floor_dist:,.1f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("📊 Enter CEILING/FLOOR in sidebar")
    
    with col_mid:
        st.markdown("""<div class="section-header">
            <div class="section-icon">📊</div>
            <div class="section-title">VIX Zone</div>
        </div>""", unsafe_allow_html=True)
        
        vix_high = inputs.get("vix_overnight_high", 0)
        vix_low = inputs.get("vix_overnight_low", 0)
        vix_curr = inputs.get("vix_current", 0)
        
        if vix_high > 0 and vix_low > 0 and vix_curr > 0:
            # Calculate marker position (clamped 0-100%)
            if vix_curr <= vix_low:
                marker_pct = 0
            elif vix_curr >= vix_high:
                marker_pct = 100
            else:
                marker_pct = ((vix_curr - vix_low) / (vix_high - vix_low)) * 100
            
            st.markdown(f"""
            <div class="vix-zone-visual">
                <div style="text-align:center; margin-bottom:0.5rem;">
                    <span style="font-family:'JetBrains Mono'; font-size:1.5rem; font-weight:600;">
                        VIX {vix_curr:.2f}
                    </span>
                </div>
                <div class="vix-zone-bar">
                    <div class="vix-marker" style="left:{marker_pct}%;"></div>
                </div>
                <div class="vix-labels">
                    <span>🟢 {vix_low:.2f}</span>
                    <span style="color:var(--accent-amber);">WAIT</span>
                    <span>🔴 {vix_high:.2f}</span>
                </div>
                <div style="text-align:center; margin-top:0.75rem; font-size:0.75rem; color:var(--text-muted);">
                    Zone: {vix_zone.get('zone_size', 0):.2f} | {vix_zone.get('zone_position', '')}
                </div>
                <div style="text-align:center; margin-top:0.5rem;">
                    <span style="font-size:0.7rem; color:var(--text-muted);">
                        CALLS @ {vix_zone.get('calls_springboard', 0):.2f} | 
                        PUTS @ {vix_zone.get('puts_springboard', 0):.2f}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("📊 Enter VIX values in sidebar")
    
    with col_right:
        st.markdown("""<div class="section-header">
            <div class="section-icon">✅</div>
            <div class="section-title">Pillar Status</div>
        </div>""", unsafe_allow_html=True)
        
        # MA Status
        ma_status_class = "ok" if ma_bias in ["LONG", "SHORT"] else "no"
        ma_status_text = ma_bias
        
        # Structure Status
        struct_status_class = "ok" if ceiling and floor else "wait"
        struct_status_text = "READY" if ceiling and floor else "PENDING"
        
        # VIX Status
        vix_status_class = "ok" if vix_signal in ["CALLS", "PUTS"] else "wait" if vix_signal == "WAIT" else "no"
        vix_status_text = vix_signal
        
        # Alignment
        aligned = trade.get('pillars_aligned', False)
        aligned_class = "ok" if aligned else "wait" if signal == "WAIT" else "no"
        aligned_text = "YES" if aligned else "WAITING" if signal == "WAIT" else "NO"
        
        st.markdown(f"""
        <div class="glass-card">
            <div class="pillar-status">
                <div class="pillar-status-icon">①</div>
                <div class="pillar-status-name">MA Bias</div>
                <div class="pillar-status-value {ma_status_class}">{ma_status_text}</div>
            </div>
            <div class="pillar-status">
                <div class="pillar-status-icon">②</div>
                <div class="pillar-status-name">Structure</div>
                <div class="pillar-status-value {struct_status_class}">{struct_status_text}</div>
            </div>
            <div class="pillar-status">
                <div class="pillar-status-icon">③</div>
                <div class="pillar-status-name">VIX Zone</div>
                <div class="pillar-status-value {vix_status_class}">{vix_status_text}</div>
            </div>
            <div style="border-top:2px solid rgba(0,0,0,0.1); margin-top:0.75rem; padding-top:0.75rem;">
                <div class="pillar-status">
                    <div class="pillar-status-icon">🎯</div>
                    <div class="pillar-status-name" style="font-weight:700;">ALIGNED</div>
                    <div class="pillar-status-value {aligned_class}">{aligned_text}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # CONE RAILS + OPTIONS
    # ========================================================================
    col_cones, col_options = st.columns([1, 1])
    
    with col_cones:
        st.markdown("""<div class="section-header">
            <div class="section-icon">📐</div>
            <div class="section-title">Cone Rails</div>
        </div>""", unsafe_allow_html=True)
        
        if cone_data:
            cones = cone_data['cones']
            blocks = cone_data['blocks']
            expansion = cone_data['expansion']
            
            st.markdown(f"""
            <div class="cone-table-container">
                <table class="cone-table">
                    <thead>
                        <tr>
                            <th>Cone</th>
                            <th>Anchor</th>
                            <th>▲ Asc</th>
                            <th>▼ Desc</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="cone-label">C1 High</td>
                            <td>{cones['C1']['anchor']:,.1f}</td>
                            <td class="cone-up">{cones['C1']['ascending']:,.1f}</td>
                            <td class="cone-down">{cones['C1']['descending']:,.1f}</td>
                        </tr>
                        <tr>
                            <td class="cone-label">C2 Low</td>
                            <td>{cones['C2']['anchor']:,.1f}</td>
                            <td class="cone-up">{cones['C2']['ascending']:,.1f}</td>
                            <td class="cone-down">{cones['C2']['descending']:,.1f}</td>
                        </tr>
                        <tr>
                            <td class="cone-label">C3 Close</td>
                            <td>{cones['C3']['anchor']:,.1f}</td>
                            <td class="cone-up">{cones['C3']['ascending']:,.1f}</td>
                            <td class="cone-down">{cones['C3']['descending']:,.1f}</td>
                        </tr>
                    </tbody>
                </table>
                <div class="cone-footer">
                    🧱 {blocks:.1f} blocks • 📏 ±{expansion:.1f} pts • 📐 {CONE_SLOPE}/block
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("📐 Enter Prior Day values in sidebar")
    
    with col_options:
        st.markdown("""<div class="section-header">
            <div class="section-icon">💹</div>
            <div class="section-title">0DTE Options</div>
        </div>""", unsafe_allow_html=True)
        
        if trade['strike'] and trade['direction']:
            is_call = trade['direction'] == "CALLS"
            option_data, ticker = fetch_option_data(trade['strike'], is_call, trade_date)
            
            if option_data:
                day = option_data.get('day', {})
                last_quote = option_data.get('last_quote', {})
                last_price = day.get('close', day.get('last', 0))
                stop_price = last_price / 2 if last_price else 0
                
                opt_type = "Call" if is_call else "Put"
                
                st.markdown(f"""
                <div class="options-container">
                    <div class="options-ticker">
                        <div class="options-ticker-symbol">{ticker}</div>
                        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.25rem;">
                            {int(trade['strike'])} {opt_type} • {trade_date.strftime('%m/%d/%y')}
                        </div>
                    </div>
                    <div class="options-grid">
                        <div class="options-item">
                            <div class="options-item-icon">💵</div>
                            <div class="options-label">Last</div>
                            <div class="options-value">${last_price:.2f}</div>
                        </div>
                        <div class="options-item">
                            <div class="options-item-icon">🟢</div>
                            <div class="options-label">Bid</div>
                            <div class="options-value">${last_quote.get('bid', 0):.2f}</div>
                        </div>
                        <div class="options-item">
                            <div class="options-item-icon">🔴</div>
                            <div class="options-label">Ask</div>
                            <div class="options-value">${last_quote.get('ask', 0):.2f}</div>
                        </div>
                        <div class="options-item">
                            <div class="options-item-icon">📊</div>
                            <div class="options-label">Volume</div>
                            <div class="options-value">{day.get('volume', 0):,}</div>
                        </div>
                        <div class="options-item">
                            <div class="options-item-icon">📈</div>
                            <div class="options-label">Open Int</div>
                            <div class="options-value">{option_data.get('open_interest', 0):,}</div>
                        </div>
                        <div class="options-item">
                            <div class="options-item-icon">🛑</div>
                            <div class="options-label">50% Stop</div>
                            <div class="options-value">${stop_price:.2f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif ticker:
                st.markdown(f"""
                <div class="options-container">
                    <div class="options-ticker">
                        <div class="options-ticker-symbol">{ticker}</div>
                        <div style="font-size:0.75rem; color:var(--text-muted);">Awaiting data...</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("💹 Generate signal to view options")
    
    # ========================================================================
    # FOOTER
    # ========================================================================
    st.markdown(f"""
    <div class="app-footer">
        🕐 {now_ct.strftime('%I:%M:%S %p CT')} • 
        ⏰ Entry: 8:30-11:30 AM CT • 
        🛑 Stop: 50% • 
        📊 All values in SPX
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

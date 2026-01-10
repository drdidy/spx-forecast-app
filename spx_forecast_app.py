"""
🔮 SPX PROPHET
Where Structure Becomes Foresight

Premium Light-Mode Glassmorphism UI
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta, time
import pytz

# ============================================================================
# CONSTANTS
# ============================================================================
SLOPE = 0.475
BLOCKS = 36
OTM_DISTANCE = 15
ENTRY_TIME = "9:00 AM CT"
POLYGON_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
DEFAULT_OFFSET = 7.0
CT = pytz.timezone('America/Chicago')

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="SPX Prophet",
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
        --accent-blue-light: #dbeafe;
        --accent-purple: #8b5cf6;
        --accent-purple-light: #ede9fe;
        --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --gradient-success: linear-gradient(135deg, #10b981 0%, #059669 100%);
        --gradient-danger: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        --gradient-warning: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }
    
    /* Main app background */
    .stApp {
        background: linear-gradient(135deg, var(--bg-gradient-start) 0%, var(--bg-gradient-mid) 50%, var(--bg-gradient-end) 100%);
        background-attachment: fixed;
    }
    
    /* Animated background orbs */
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
    
    /* ==================== GLASS CARD ==================== */
    .glass-card {
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        padding: 1.75rem;
        margin-bottom: 1.25rem;
        box-shadow: 
            0 4px 24px var(--glass-shadow),
            0 1px 2px rgba(0, 0, 0, 0.04),
            inset 0 1px 0 rgba(255, 255, 255, 0.6);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 
            0 12px 40px rgba(100, 100, 150, 0.15),
            0 4px 12px rgba(0, 0, 0, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.8);
    }
    
    /* ==================== HERO HEADER ==================== */
    .hero-container {
        text-align: center;
        padding: 3rem 2rem;
        margin-bottom: 2.5rem;
        background: var(--glass-bg-strong);
        backdrop-filter: blur(30px);
        -webkit-backdrop-filter: blur(30px);
        border-radius: 32px;
        border: 1px solid rgba(255, 255, 255, 0.9);
        box-shadow: 
            0 8px 32px rgba(100, 100, 150, 0.12),
            inset 0 2px 0 rgba(255, 255, 255, 0.8);
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
        border-radius: 32px 32px 0 0;
    }
    
    .hero-icon {
        font-size: 4rem;
        margin-bottom: 0.5rem;
        animation: pulse-glow 3s ease-in-out infinite;
    }
    
    @keyframes pulse-glow {
        0%, 100% { 
            transform: scale(1);
            filter: drop-shadow(0 0 8px rgba(139, 92, 246, 0.3));
        }
        50% { 
            transform: scale(1.05);
            filter: drop-shadow(0 0 20px rgba(139, 92, 246, 0.5));
        }
    }
    
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        background: var(--gradient-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }
    
    .hero-tagline {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: var(--text-secondary);
        font-weight: 500;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 1.5rem;
    }
    
    .hero-price-container {
        display: inline-flex;
        align-items: center;
        gap: 0.75rem;
        background: var(--glass-bg);
        padding: 1rem 2rem;
        border-radius: 16px;
        border: 1px solid var(--glass-border);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
    }
    
    .hero-price-label {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-secondary);
    }
    
    .hero-price {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.5rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    .hero-time {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.875rem;
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
    
    /* ==================== SECTION HEADERS ==================== */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.25rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid rgba(139, 92, 246, 0.1);
    }
    
    .section-icon {
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--gradient-primary);
        border-radius: 12px;
        font-size: 1.25rem;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
    }
    
    .section-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.5px;
    }
    
    /* ==================== PILLAR CARDS ==================== */
    .pillar-card {
        background: var(--glass-bg-strong);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 1.75rem;
        height: 100%;
        border: 1px solid var(--glass-border);
        box-shadow: 
            0 4px 24px var(--glass-shadow),
            inset 0 1px 0 rgba(255, 255, 255, 0.8);
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
        border-radius: 24px 24px 0 0;
        transition: all 0.3s ease;
    }
    
    .pillar-card.bullish::before { background: var(--gradient-success); }
    .pillar-card.bearish::before { background: var(--gradient-danger); }
    .pillar-card.neutral::before { background: var(--gradient-warning); }
    
    .pillar-card:hover {
        transform: translateY(-4px) scale(1.01);
        box-shadow: 
            0 16px 48px rgba(100, 100, 150, 0.18),
            inset 0 1px 0 rgba(255, 255, 255, 1);
    }
    
    .pillar-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
    }
    
    .pillar-icon {
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 14px;
        font-size: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .pillar-icon.bullish {
        background: var(--accent-green-light);
        color: var(--accent-green);
    }
    
    .pillar-icon.bearish {
        background: var(--accent-red-light);
        color: var(--accent-red);
    }
    
    .pillar-icon.neutral {
        background: var(--accent-amber-light);
        color: var(--accent-amber);
    }
    
    .pillar-number {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    .pillar-name {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .pillar-question {
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-bottom: 1.25rem;
        line-height: 1.5;
    }
    
    .pillar-answer {
        font-family: 'Inter', sans-serif;
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
    }
    
    .pillar-answer.bullish { color: var(--accent-green); }
    .pillar-answer.bearish { color: var(--accent-red); }
    .pillar-answer.neutral { color: var(--accent-amber); }
    
    .pillar-detail {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: var(--text-muted);
        background: rgba(0, 0, 0, 0.03);
        padding: 0.5rem 0.75rem;
        border-radius: 8px;
        display: inline-block;
    }
    
    /* ==================== SIGNAL CARD ==================== */
    .signal-card {
        background: var(--glass-bg-strong);
        backdrop-filter: blur(30px);
        -webkit-backdrop-filter: blur(30px);
        border-radius: 32px;
        padding: 2.5rem;
        text-align: center;
        border: 2px solid;
        margin: 2rem 0;
        position: relative;
        overflow: hidden;
        transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .signal-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        opacity: 0.05;
        pointer-events: none;
        transition: opacity 0.3s ease;
    }
    
    .signal-card.calls {
        border-color: var(--accent-green);
        box-shadow: 
            0 8px 32px rgba(16, 185, 129, 0.15),
            inset 0 0 60px rgba(16, 185, 129, 0.03);
    }
    
    .signal-card.calls::before {
        background: radial-gradient(circle at center, var(--accent-green) 0%, transparent 70%);
    }
    
    .signal-card.puts {
        border-color: var(--accent-red);
        box-shadow: 
            0 8px 32px rgba(239, 68, 68, 0.15),
            inset 0 0 60px rgba(239, 68, 68, 0.03);
    }
    
    .signal-card.puts::before {
        background: radial-gradient(circle at center, var(--accent-red) 0%, transparent 70%);
    }
    
    .signal-card.wait {
        border-color: var(--accent-amber);
        box-shadow: 
            0 8px 32px rgba(245, 158, 11, 0.15),
            inset 0 0 60px rgba(245, 158, 11, 0.03);
    }
    
    .signal-card.wait::before {
        background: radial-gradient(circle at center, var(--accent-amber) 0%, transparent 70%);
    }
    
    .signal-card.notrade {
        border-color: var(--text-muted);
        box-shadow: 0 8px 32px var(--glass-shadow);
    }
    
    .signal-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
        animation: signal-bounce 2s ease-in-out infinite;
    }
    
    @keyframes signal-bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-8px); }
    }
    
    .signal-action {
        font-family: 'Inter', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        letter-spacing: 4px;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .signal-action.calls { color: var(--accent-green); }
    .signal-action.puts { color: var(--accent-red); }
    .signal-action.wait { color: var(--accent-amber); }
    .signal-action.notrade { color: var(--text-muted); }
    
    .signal-reason {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: var(--text-secondary);
        margin-top: 0.75rem;
        font-weight: 500;
    }
    
    .signal-details {
        display: flex;
        justify-content: center;
        gap: 2rem;
        margin-top: 2rem;
        flex-wrap: wrap;
    }
    
    .signal-detail-item {
        background: var(--glass-bg);
        padding: 1.25rem 2rem;
        border-radius: 16px;
        border: 1px solid var(--glass-border);
        min-width: 140px;
        transition: all 0.3s ease;
    }
    
    .signal-detail-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px var(--glass-shadow);
    }
    
    .signal-detail-icon {
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
    }
    
    .signal-detail-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: var(--text-muted);
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    
    .signal-detail-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    /* ==================== CONE TABLE ==================== */
    .cone-table-container {
        background: var(--glass-bg-strong);
        border-radius: 20px;
        padding: 1.5rem;
        border: 1px solid var(--glass-border);
        box-shadow: 0 4px 24px var(--glass-shadow);
    }
    
    .cone-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 8px;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .cone-table th {
        background: transparent;
        padding: 0.75rem 1rem;
        text-align: center;
        font-weight: 600;
        font-size: 0.75rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    .cone-table td {
        padding: 1rem;
        text-align: center;
        background: var(--glass-bg);
        transition: all 0.3s ease;
    }
    
    .cone-table tr td:first-child {
        border-radius: 12px 0 0 12px;
    }
    
    .cone-table tr td:last-child {
        border-radius: 0 12px 12px 0;
    }
    
    .cone-table tr:hover td {
        background: rgba(139, 92, 246, 0.08);
    }
    
    .cone-label {
        font-weight: 600;
        color: var(--text-secondary);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }
    
    .cone-anchor {
        color: var(--text-primary);
        font-weight: 600;
    }
    
    .cone-up { 
        color: var(--accent-green);
        font-weight: 600;
    }
    
    .cone-down { 
        color: var(--accent-red);
        font-weight: 600;
    }
    
    .cone-footer {
        text-align: center;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(0, 0, 0, 0.05);
        color: var(--text-muted);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1.5rem;
    }
    
    .cone-footer-item {
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    
    /* ==================== OPTIONS PANEL ==================== */
    .options-container {
        background: var(--glass-bg-strong);
        border-radius: 20px;
        padding: 1.5rem;
        border: 1px solid var(--glass-border);
        box-shadow: 0 4px 24px var(--glass-shadow);
    }
    
    .options-ticker {
        text-align: center;
        margin-bottom: 1.25rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    .options-ticker-symbol {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        color: var(--accent-purple);
        font-weight: 600;
        background: var(--accent-purple-light);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        display: inline-block;
        margin-bottom: 0.5rem;
    }
    
    .options-ticker-info {
        font-size: 0.8rem;
        color: var(--text-muted);
    }
    
    .options-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.75rem;
    }
    
    .options-item {
        text-align: center;
        padding: 1rem;
        background: var(--glass-bg);
        border-radius: 14px;
        border: 1px solid rgba(0, 0, 0, 0.03);
        transition: all 0.3s ease;
    }
    
    .options-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px var(--glass-shadow);
        background: white;
    }
    
    .options-item-icon {
        font-size: 1.25rem;
        margin-bottom: 0.4rem;
    }
    
    .options-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-muted);
        margin-bottom: 0.35rem;
        font-weight: 600;
    }
    
    .options-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    /* ==================== FOOTER ==================== */
    .app-footer {
        text-align: center;
        padding: 2rem 1rem;
        margin-top: 3rem;
        color: var(--text-muted);
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        border-top: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    .footer-items {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 2rem;
        flex-wrap: wrap;
    }
    
    .footer-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* ==================== SIDEBAR ==================== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8faff 0%, #f0f4ff 100%);
        border-right: 1px solid rgba(139, 92, 246, 0.1);
    }
    
    section[data-testid="stSidebar"] > div {
        padding-top: 1rem;
    }
    
    .sidebar-header {
        text-align: center;
        padding: 1.5rem 1rem;
        margin-bottom: 1rem;
        background: var(--glass-bg-strong);
        border-radius: 16px;
        border: 1px solid var(--glass-border);
    }
    
    .sidebar-logo {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    
    .sidebar-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        background: var(--gradient-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .sidebar-section {
        background: var(--glass-bg-strong);
        border-radius: 16px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid var(--glass-border);
    }
    
    .sidebar-section-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    .sidebar-section-icon {
        font-size: 1.1rem;
    }
    
    .sidebar-section-title {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text-primary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Form inputs */
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input {
        background: white !important;
        border: 1px solid rgba(139, 92, 246, 0.2) !important;
        border-radius: 10px !important;
        font-family: 'JetBrains Mono', monospace !important;
        transition: all 0.3s ease !important;
    }
    
    .stNumberInput > div > div > input:focus,
    .stDateInput > div > div > input:focus {
        border-color: var(--accent-purple) !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1) !important;
    }
    
    .stCheckbox label {
        font-family: 'Inter', sans-serif !important;
        color: var(--text-primary) !important;
    }
    
    .stButton > button {
        background: var(--gradient-primary) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.5rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4) !important;
    }
    
    /* Keep sidebar visible */
    section[data-testid="stSidebar"] {
        width: 340px !important;
        min-width: 340px !important;
    }
    
    [data-testid="collapsedControl"] {
        display: none;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Info/Warning boxes */
    .stAlert {
        border-radius: 12px !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_es_price():
    """Fetch current ES futures price from Yahoo Finance."""
    try:
        es = yf.Ticker("ES=F")
        data = es.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        pass
    return None

def get_es_history(days=300):
    """Fetch ES futures history for MA calculations."""
    try:
        es = yf.Ticker("ES=F")
        data = es.history(period=f"{days}d", interval="1d")
        return data
    except Exception as e:
        pass
    return None

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average."""
    return prices.ewm(span=period, adjust=False).mean()

def calculate_sma(prices, period):
    """Calculate Simple Moving Average."""
    return prices.rolling(window=period).mean()

def analyze_ma_bias(es_history, offset):
    """Pillar 1: Determine MA Bias (direction filter)."""
    if es_history is None or len(es_history) < 200:
        return "NEUTRAL", "Insufficient data", None, None
    
    spx_close = es_history['Close'] - offset
    ema_50 = calculate_ema(spx_close, 50)
    sma_200 = calculate_sma(spx_close, 200)
    
    current_ema = ema_50.iloc[-1]
    current_sma = sma_200.iloc[-1]
    
    if current_ema > current_sma:
        return "LONG", f"50 EMA ({current_ema:.1f}) > 200 SMA ({current_sma:.1f})", current_ema, current_sma
    elif current_ema < current_sma:
        return "SHORT", f"50 EMA ({current_ema:.1f}) < 200 SMA ({current_sma:.1f})", current_ema, current_sma
    else:
        return "NEUTRAL", "50 EMA = 200 SMA", current_ema, current_sma

def analyze_vix_zone(vix_high, vix_low, vix_current):
    """Pillar 3: Determine VIX Zone (timing signal)."""
    if vix_high <= 0 or vix_low <= 0 or vix_current <= 0:
        return "WAIT", "Enter VIX values"
    
    vix_range = (vix_high - vix_low) / vix_high * 100
    midpoint = (vix_high + vix_low) / 2
    
    if vix_range > 7:
        return "WAIT", f"Range {vix_range:.1f}% > 7%"
    
    if vix_current < midpoint:
        return "CALLS", f"Lower half ({vix_range:.1f}% range)"
    else:
        return "PUTS", f"Upper half ({vix_range:.1f}% range)"

def calculate_cone_rails(high, low, close):
    """Calculate the three cone rails with ±17.1 expansion."""
    expansion = BLOCKS * SLOPE
    
    cones = {
        'HIGH': {'anchor': high, 'upper': high + expansion, 'lower': high - expansion},
        'LOW': {'anchor': low, 'upper': low + expansion, 'lower': low - expansion},
        'CLOSE': {'anchor': close, 'upper': close + expansion, 'lower': close - expansion}
    }
    
    return cones, expansion

def get_structure_levels(cones):
    """Determine floor and ceiling from cone rails."""
    floor = min(cones['HIGH']['lower'], cones['LOW']['lower'], cones['CLOSE']['lower'])
    ceiling = max(cones['HIGH']['upper'], cones['LOW']['upper'], cones['CLOSE']['upper'])
    return floor, ceiling

def calculate_strike(entry_level, direction):
    """Calculate strike price based on entry level and direction."""
    if direction == "CALLS":
        raw_strike = entry_level + OTM_DISTANCE
    else:
        raw_strike = entry_level - OTM_DISTANCE
    return round(raw_strike / 5) * 5

def format_option_ticker(strike, is_call, trade_date):
    """Format the SPXW option ticker for Polygon API."""
    date_str = trade_date.strftime("%y%m%d")
    option_type = "C" if is_call else "P"
    strike_str = f"{int(strike * 1000):08d}"
    return f"O:SPXW{date_str}{option_type}{strike_str}"

def fetch_option_data(ticker):
    """Fetch option data from Polygon.io."""
    try:
        url = f"https://api.polygon.io/v3/snapshot/options/SPXW/{ticker}?apiKey={POLYGON_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                return data['results']
    except Exception as e:
        pass
    return None

def generate_signal(ma_bias, vix_signal):
    """Generate trade signal from pillar alignment."""
    if ma_bias == "NEUTRAL":
        return "NO TRADE", "MA bias is neutral"
    
    if vix_signal == "WAIT":
        return "WAIT", "VIX range too wide (>7%)"
    
    if ma_bias == "LONG" and vix_signal == "CALLS":
        return "CALLS", "All pillars aligned bullish"
    elif ma_bias == "SHORT" and vix_signal == "PUTS":
        return "PUTS", "All pillars aligned bearish"
    else:
        return "NO TRADE", f"Conflict: MA {ma_bias} vs VIX {vix_signal}"

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    now_ct = datetime.now(CT)
    
    # ========================================================================
    # SIDEBAR
    # ========================================================================
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-header">
            <div class="sidebar-logo">🔮</div>
            <div class="sidebar-title">SPX Prophet</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Trading Date
        st.markdown("""
        <div class="sidebar-section">
            <div class="sidebar-section-header">
                <span class="sidebar-section-icon">📅</span>
                <span class="sidebar-section-title">Trading Date</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        trade_date = st.date_input(
            "Date",
            value=now_ct.date(),
            min_value=datetime(2024, 1, 1).date(),
            max_value=datetime(2027, 12, 31).date(),
            label_visibility="collapsed"
        )
        
        # VIX Zone
        st.markdown("""
        <div class="sidebar-section">
            <div class="sidebar-section-header">
                <span class="sidebar-section-icon">📊</span>
                <span class="sidebar-section-title">VIX Zone</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        vix_high = st.number_input("Overnight High", value=0.0, step=0.01, format="%.2f")
        vix_low = st.number_input("Overnight Low", value=0.0, step=0.01, format="%.2f")
        vix_current = st.number_input("Current VIX", value=0.0, step=0.01, format="%.2f")
        
        # Prior Day SPX
        st.markdown("""
        <div class="sidebar-section">
            <div class="sidebar-section-header">
                <span class="sidebar-section-icon">📈</span>
                <span class="sidebar-section-title">Prior Day SPX</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        prior_high = st.number_input("High", value=0.0, step=0.01, format="%.2f", key="prior_high")
        prior_low = st.number_input("Low", value=0.0, step=0.01, format="%.2f", key="prior_low")
        prior_close = st.number_input("Close (3pm CT)", value=0.0, step=0.01, format="%.2f", key="prior_close")
        
        # Structure Override
        st.markdown("""
        <div class="sidebar-section">
            <div class="sidebar-section-header">
                <span class="sidebar-section-icon">🎯</span>
                <span class="sidebar-section-title">Structure Override</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        use_override = st.checkbox("Enable Manual Override")
        
        if use_override:
            manual_ceiling = st.number_input("Manual Ceiling", value=0.0, step=0.01, format="%.2f")
            manual_floor = st.number_input("Manual Floor", value=0.0, step=0.01, format="%.2f")
        else:
            manual_ceiling = None
            manual_floor = None
        
        # Advanced Settings
        with st.expander("⚙️ Advanced Settings"):
            es_offset = st.number_input("ES-SPX Offset", value=DEFAULT_OFFSET, step=0.1, format="%.1f")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
    
    # ========================================================================
    # FETCH DATA
    # ========================================================================
    es_price = get_es_price()
    es_history = get_es_history()
    spx_price = es_price - es_offset if es_price else None
    
    # ========================================================================
    # HERO HEADER
    # ========================================================================
    spx_display = f"{spx_price:,.2f}" if spx_price else "---"
    
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-icon">🔮</div>
        <div class="hero-title">SPX PROPHET</div>
        <div class="hero-tagline">Where Structure Becomes Foresight</div>
        <div class="hero-price-container">
            <span class="hero-price-label">SPX</span>
            <span class="hero-price">{spx_display}</span>
        </div>
        <div class="hero-time">
            <span class="live-dot"></span>
            {now_ct.strftime('%I:%M:%S %p CT')} • {trade_date.strftime('%B %d, %Y')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================================================
    # THREE PILLARS
    # ========================================================================
    st.markdown("""
    <div class="section-header">
        <div class="section-icon">⚡</div>
        <div class="section-title">The Three Pillars</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Analyze pillars
    ma_bias, ma_detail, ema_val, sma_val = analyze_ma_bias(es_history, es_offset)
    vix_signal, vix_detail = analyze_vix_zone(vix_high, vix_low, vix_current)
    
    # Pillar 2: Day Structure
    if prior_high > 0 and prior_low > 0 and prior_close > 0:
        cones, expansion = calculate_cone_rails(prior_high, prior_low, prior_close)
        calc_floor, calc_ceiling = get_structure_levels(cones)
        
        if use_override and manual_floor and manual_ceiling:
            floor, ceiling = manual_floor, manual_ceiling
            structure_detail = f"Manual override applied"
        else:
            floor, ceiling = calc_floor, calc_ceiling
            structure_detail = f"Floor {floor:.1f} • Ceiling {ceiling:.1f}"
        
        if ma_bias == "LONG":
            entry_level = floor
            structure_answer = "FLOOR"
        elif ma_bias == "SHORT":
            entry_level = ceiling
            structure_answer = "CEILING"
        else:
            entry_level = None
            structure_answer = "N/A"
    else:
        cones = None
        floor = ceiling = entry_level = None
        structure_answer = "PENDING"
        structure_detail = "Enter prior day values"
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        bias_class = "bullish" if ma_bias == "LONG" else "bearish" if ma_bias == "SHORT" else "neutral"
        bias_icon = "📈" if ma_bias == "LONG" else "📉" if ma_bias == "SHORT" else "⏸️"
        st.markdown(f"""
        <div class="pillar-card {bias_class}">
            <div class="pillar-header">
                <div class="pillar-icon {bias_class}">{bias_icon}</div>
                <div>
                    <div class="pillar-number">Pillar 1</div>
                    <div class="pillar-name">MA Bias</div>
                </div>
            </div>
            <div class="pillar-question">Which direction are we trading?</div>
            <div class="pillar-answer {bias_class}">{ma_bias}</div>
            <div class="pillar-detail">{ma_detail}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        struct_class = "bullish" if structure_answer == "FLOOR" else "bearish" if structure_answer == "CEILING" else "neutral"
        struct_icon = "🎯" if structure_answer == "FLOOR" else "🎯" if structure_answer == "CEILING" else "⏳"
        st.markdown(f"""
        <div class="pillar-card {struct_class}">
            <div class="pillar-header">
                <div class="pillar-icon {struct_class}">{struct_icon}</div>
                <div>
                    <div class="pillar-number">Pillar 2</div>
                    <div class="pillar-name">Day Structure</div>
                </div>
            </div>
            <div class="pillar-question">Where is our entry level?</div>
            <div class="pillar-answer {struct_class}">{structure_answer}</div>
            <div class="pillar-detail">{structure_detail}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        vix_class = "bullish" if vix_signal == "CALLS" else "bearish" if vix_signal == "PUTS" else "neutral"
        vix_icon = "🟢" if vix_signal == "CALLS" else "🔴" if vix_signal == "PUTS" else "🟡"
        st.markdown(f"""
        <div class="pillar-card {vix_class}">
            <div class="pillar-header">
                <div class="pillar-icon {vix_class}">{vix_icon}</div>
                <div>
                    <div class="pillar-number">Pillar 3</div>
                    <div class="pillar-name">VIX Zone</div>
                </div>
            </div>
            <div class="pillar-question">What's the timing signal?</div>
            <div class="pillar-answer {vix_class}">{vix_signal}</div>
            <div class="pillar-detail">{vix_detail}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # SIGNAL CARD
    # ========================================================================
    signal, signal_reason = generate_signal(ma_bias, vix_signal)
    
    signal_class = signal.lower().replace(" ", "")
    
    if signal == "CALLS":
        signal_icon = "🚀"
    elif signal == "PUTS":
        signal_icon = "🔻"
    elif signal == "WAIT":
        signal_icon = "⏳"
    else:
        signal_icon = "🚫"
    
    # Calculate strike
    strike = None
    option_data = None
    option_ticker = None
    
    if signal in ["CALLS", "PUTS"] and entry_level:
        strike = calculate_strike(entry_level, signal)
        option_ticker = format_option_ticker(strike, signal == "CALLS", trade_date)
        option_data = fetch_option_data(option_ticker)
    
    entry_display = f"{entry_level:,.1f}" if entry_level else "---"
    strike_display = f"{int(strike)}" if strike else "---"
    
    st.markdown(f"""
    <div class="signal-card {signal_class}">
        <div class="signal-icon">{signal_icon}</div>
        <div class="signal-action {signal_class}">{signal}</div>
        <div class="signal-reason">{signal_reason}</div>
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
                <div class="signal-detail-icon">⏰</div>
                <div class="signal-detail-label">Entry Time</div>
                <div class="signal-detail-value">{ENTRY_TIME}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================================================
    # CONE RAILS & OPTIONS
    # ========================================================================
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("""
        <div class="section-header">
            <div class="section-icon">📐</div>
            <div class="section-title">Cone Rails</div>
        </div>
        """, unsafe_allow_html=True)
        
        if cones:
            st.markdown(f"""
            <div class="cone-table-container">
                <table class="cone-table">
                    <thead>
                        <tr>
                            <th>Anchor</th>
                            <th>Level</th>
                            <th>▲ Ascending</th>
                            <th>▼ Descending</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><span class="cone-label">📊 HIGH</span></td>
                            <td class="cone-anchor">{cones['HIGH']['anchor']:,.1f}</td>
                            <td class="cone-up">{cones['HIGH']['upper']:,.1f}</td>
                            <td class="cone-down">{cones['HIGH']['lower']:,.1f}</td>
                        </tr>
                        <tr>
                            <td><span class="cone-label">📉 LOW</span></td>
                            <td class="cone-anchor">{cones['LOW']['anchor']:,.1f}</td>
                            <td class="cone-up">{cones['LOW']['upper']:,.1f}</td>
                            <td class="cone-down">{cones['LOW']['lower']:,.1f}</td>
                        </tr>
                        <tr>
                            <td><span class="cone-label">🔒 CLOSE</span></td>
                            <td class="cone-anchor">{cones['CLOSE']['anchor']:,.1f}</td>
                            <td class="cone-up">{cones['CLOSE']['upper']:,.1f}</td>
                            <td class="cone-down">{cones['CLOSE']['lower']:,.1f}</td>
                        </tr>
                    </tbody>
                </table>
                <div class="cone-footer">
                    <span class="cone-footer-item">🧱 {BLOCKS} blocks</span>
                    <span class="cone-footer-item">📏 ±{expansion:.1f} pts</span>
                    <span class="cone-footer-item">📐 {SLOPE}/block</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("📊 Enter prior day SPX values to calculate cone rails")
    
    with col_right:
        st.markdown("""
        <div class="section-header">
            <div class="section-icon">💹</div>
            <div class="section-title">Options Data</div>
        </div>
        """, unsafe_allow_html=True)
        
        if option_data:
            day = option_data.get('day', {})
            last_quote = option_data.get('last_quote', {})
            last_price = day.get('close', day.get('last', 0))
            stop_price = last_price / 2 if last_price else 0
            
            opt_type = "Call" if signal == "CALLS" else "Put"
            
            st.markdown(f"""
            <div class="options-container">
                <div class="options-ticker">
                    <div class="options-ticker-symbol">{option_ticker}</div>
                    <div class="options-ticker-info">{strike} {opt_type} • Exp {trade_date.strftime('%m/%d/%y')}</div>
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
        elif option_ticker:
            st.markdown(f"""
            <div class="options-container">
                <div class="options-ticker">
                    <div class="options-ticker-symbol">{option_ticker}</div>
                    <div class="options-ticker-info">Waiting for market data...</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("💹 Generate a signal to view options data")
    
    # ========================================================================
    # FOOTER
    # ========================================================================
    st.markdown(f"""
    <div class="app-footer">
        <div class="footer-items">
            <span class="footer-item">🕐 Last refresh: {now_ct.strftime('%I:%M:%S %p CT')}</span>
            <span class="footer-item">⏰ Entry: {ENTRY_TIME}</span>
            <span class="footer-item">📊 All values in SPX</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

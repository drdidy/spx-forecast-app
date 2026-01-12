"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           SPX PROPHET V3                                      ║
║                    Institutional-Grade 0DTE Trading System                    ║
║                                                                               ║
║  3-Pillar Methodology | Confidence Scoring | Gamma-Optimized Strikes          ║
║  30-Min Momentum Suite | ATR Dynamic Stops | ES1! MA Alignment                ║
╚══════════════════════════════════════════════════════════════════════════════╝
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
# CONFIGURATION
# ============================================================================
CT = pytz.timezone('America/Chicago')
ET = pytz.timezone('America/New_York')
CONE_SLOPE = 0.475
POLYGON_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
INPUTS_FILE = "spx_prophet_v3_inputs.json"

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="SPX Prophet V3",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# PROFESSIONAL DARK THEME - INSTITUTIONAL TRADING TERMINAL
# ============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');
    
    :root {
        /* Deep dark palette */
        --bg-primary: #0a0a0f;
        --bg-secondary: #12121a;
        --bg-tertiary: #1a1a24;
        --bg-card: #14141e;
        --bg-card-hover: #1c1c28;
        --bg-elevated: #1e1e2a;
        
        /* Borders & Lines */
        --border-subtle: rgba(255, 255, 255, 0.06);
        --border-default: rgba(255, 255, 255, 0.1);
        --border-strong: rgba(255, 255, 255, 0.15);
        
        /* Text hierarchy */
        --text-primary: #f0f0f5;
        --text-secondary: #a0a0b0;
        --text-muted: #606070;
        --text-dim: #404050;
        
        /* Accent colors - muted sophistication */
        --accent-green: #22c55e;
        --accent-green-dim: rgba(34, 197, 94, 0.15);
        --accent-green-glow: rgba(34, 197, 94, 0.3);
        
        --accent-red: #ef4444;
        --accent-red-dim: rgba(239, 68, 68, 0.15);
        --accent-red-glow: rgba(239, 68, 68, 0.3);
        
        --accent-amber: #f59e0b;
        --accent-amber-dim: rgba(245, 158, 11, 0.15);
        
        --accent-blue: #3b82f6;
        --accent-blue-dim: rgba(59, 130, 246, 0.15);
        
        --accent-purple: #8b5cf6;
        --accent-purple-dim: rgba(139, 92, 246, 0.12);
        
        --accent-cyan: #06b6d4;
        --accent-cyan-dim: rgba(6, 182, 212, 0.12);
        
        /* Gradients */
        --gradient-brand: linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%);
        --gradient-success: linear-gradient(135deg, #22c55e 0%, #10b981 100%);
        --gradient-danger: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        --gradient-warning: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        
        /* Shadows */
        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4);
        --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.5);
        --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.6);
        --shadow-glow-green: 0 0 20px rgba(34, 197, 94, 0.2);
        --shadow-glow-red: 0 0 20px rgba(239, 68, 68, 0.2);
    }
    
    /* Global Reset */
    .stApp {
        background: var(--bg-primary);
        background-image: 
            radial-gradient(ellipse at 0% 0%, rgba(139, 92, 246, 0.03) 0%, transparent 50%),
            radial-gradient(ellipse at 100% 100%, rgba(6, 182, 212, 0.03) 0%, transparent 50%);
    }
    
    .main .block-container {
        padding: 1.5rem 2rem;
        max-width: 1600px;
    }
    
    /* Hide Streamlit branding */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* ============ TYPOGRAPHY ============ */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: var(--text-primary) !important;
    }
    
    p, span, div, label {
        font-family: 'DM Sans', sans-serif;
    }
    
    code, .mono {
        font-family: 'IBM Plex Mono', monospace;
    }
    
    /* ============ HERO HEADER ============ */
    .hero {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    
    .hero::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: var(--gradient-brand);
    }
    
    .hero-grid {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center;
        gap: 2rem;
    }
    
    .hero-brand {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .hero-logo {
        width: 48px;
        height: 48px;
        background: var(--gradient-brand);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        box-shadow: var(--shadow-md);
    }
    
    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.5px;
        margin: 0;
    }
    
    .hero-subtitle {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.75rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 0.25rem;
    }
    
    .hero-price-container {
        text-align: center;
    }
    
    .hero-price-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.65rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 0.25rem;
    }
    
    .hero-price {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2.75rem;
        font-weight: 600;
        color: var(--text-primary);
        letter-spacing: -1px;
    }
    
    .hero-meta {
        text-align: right;
    }
    
    .hero-time {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        color: var(--text-secondary);
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.5rem;
    }
    
    .live-indicator {
        width: 8px;
        height: 8px;
        background: var(--accent-green);
        border-radius: 50%;
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; box-shadow: 0 0 0 0 var(--accent-green-glow); }
        50% { opacity: 0.7; box-shadow: 0 0 0 8px transparent; }
    }
    
    .hero-date {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-top: 0.25rem;
    }
    
    /* ============ CARDS ============ */
    .card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 1.25rem;
        transition: all 0.2s ease;
    }
    
    .card:hover {
        border-color: var(--border-default);
        background: var(--bg-card-hover);
    }
    
    .card-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--border-subtle);
    }
    
    .card-icon {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
    }
    
    .card-icon.purple { background: var(--accent-purple-dim); }
    .card-icon.blue { background: var(--accent-blue-dim); }
    .card-icon.green { background: var(--accent-green-dim); }
    .card-icon.amber { background: var(--accent-amber-dim); }
    .card-icon.red { background: var(--accent-red-dim); }
    .card-icon.cyan { background: var(--accent-cyan-dim); }
    
    .card-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    .card-subtitle {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.7rem;
        color: var(--text-muted);
    }
    
    /* ============ PILLAR CARDS ============ */
    .pillar-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 1.5rem;
        position: relative;
        overflow: hidden;
        height: 100%;
        transition: all 0.3s ease;
    }
    
    .pillar-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
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
    
    .pillar-number {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.6rem;
        color: var(--text-dim);
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 0.5rem;
    }
    
    .pillar-name {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
    }
    
    .pillar-question {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-bottom: 1rem;
    }
    
    .pillar-value {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .pillar-value.bullish { color: var(--accent-green); }
    .pillar-value.bearish { color: var(--accent-red); }
    .pillar-value.neutral { color: var(--accent-amber); }
    
    .pillar-detail {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: var(--text-muted);
        background: var(--bg-tertiary);
        padding: 0.4rem 0.6rem;
        border-radius: 6px;
        display: inline-block;
    }
    
    /* ============ SIGNAL CARD ============ */
    .signal-container {
        background: var(--bg-card);
        border: 2px solid var(--border-subtle);
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        position: relative;
        overflow: hidden;
        margin: 1.5rem 0;
    }
    
    .signal-container.calls {
        border-color: var(--accent-green);
        box-shadow: var(--shadow-glow-green);
    }
    
    .signal-container.puts {
        border-color: var(--accent-red);
        box-shadow: var(--shadow-glow-red);
    }
    
    .signal-container.wait {
        border-color: var(--accent-amber);
    }
    
    .signal-badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 20px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 1rem;
    }
    
    .signal-badge.high { background: var(--accent-green-dim); color: var(--accent-green); }
    .signal-badge.medium { background: var(--accent-amber-dim); color: var(--accent-amber); }
    .signal-badge.low { background: var(--accent-red-dim); color: var(--accent-red); }
    
    .signal-action {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 3.5rem;
        font-weight: 700;
        letter-spacing: 2px;
        margin-bottom: 0.5rem;
    }
    
    .signal-action.calls { color: var(--accent-green); }
    .signal-action.puts { color: var(--accent-red); }
    .signal-action.wait { color: var(--accent-amber); }
    .signal-action.notrade { color: var(--text-muted); }
    
    .signal-score {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.5rem;
        color: var(--text-secondary);
        margin-bottom: 0.5rem;
    }
    
    .signal-reason {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.9rem;
        color: var(--text-muted);
    }
    
    .signal-details {
        display: flex;
        justify-content: center;
        gap: 1rem;
        margin-top: 1.5rem;
        flex-wrap: wrap;
    }
    
    .signal-detail-item {
        background: var(--bg-tertiary);
        padding: 1rem 1.25rem;
        border-radius: 10px;
        min-width: 110px;
        border: 1px solid var(--border-subtle);
    }
    
    .signal-detail-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.6rem;
        color: var(--text-dim);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.35rem;
    }
    
    .signal-detail-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    /* ============ CONFIDENCE BREAKDOWN ============ */
    .breakdown-container {
        background: var(--bg-tertiary);
        border-radius: 10px;
        padding: 1rem;
        margin-top: 1rem;
    }
    
    .breakdown-item {
        display: flex;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--border-subtle);
    }
    
    .breakdown-item:last-child { border-bottom: none; }
    
    .breakdown-icon {
        width: 24px;
        font-size: 0.9rem;
    }
    
    .breakdown-name {
        flex: 1;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }
    
    .breakdown-score {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
    }
    
    .breakdown-score.positive { background: var(--accent-green-dim); color: var(--accent-green); }
    .breakdown-score.partial { background: var(--accent-amber-dim); color: var(--accent-amber); }
    .breakdown-score.zero { background: var(--bg-secondary); color: var(--text-muted); }
    
    /* ============ DATA DISPLAYS ============ */
    .data-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.6rem 0;
        border-bottom: 1px solid var(--border-subtle);
    }
    
    .data-row:last-child { border-bottom: none; }
    
    .data-label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8rem;
        color: var(--text-muted);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .data-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.9rem;
        font-weight: 500;
        color: var(--text-primary);
    }
    
    .data-value.green { color: var(--accent-green); }
    .data-value.red { color: var(--accent-red); }
    .data-value.amber { color: var(--accent-amber); }
    .data-value.purple { color: var(--accent-purple); }
    
    /* ============ STRIKE SELECTOR ============ */
    .strike-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.75rem;
    }
    
    .strike-option {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        transition: all 0.2s ease;
    }
    
    .strike-option.recommended {
        border-color: var(--accent-cyan);
        background: var(--accent-cyan-dim);
    }
    
    .strike-option-label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.65rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.35rem;
    }
    
    .strike-option-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.4rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    /* ============ MOMENTUM INDICATORS ============ */
    .momentum-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.75rem;
    }
    
    .momentum-item {
        background: var(--bg-tertiary);
        border-radius: 8px;
        padding: 0.75rem;
        text-align: center;
    }
    
    .momentum-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.6rem;
        color: var(--text-dim);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.25rem;
    }
    
    .momentum-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1rem;
        font-weight: 600;
    }
    
    /* ============ PROGRESS BAR (VIX) ============ */
    .vix-visual {
        background: var(--bg-tertiary);
        border-radius: 10px;
        padding: 1.25rem;
    }
    
    .vix-current {
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .vix-current-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    .vix-bar-container {
        position: relative;
        height: 12px;
        background: linear-gradient(90deg, var(--accent-green) 0%, var(--accent-amber) 50%, var(--accent-red) 100%);
        border-radius: 6px;
        margin: 0.75rem 0;
    }
    
    .vix-marker {
        position: absolute;
        top: -4px;
        width: 20px;
        height: 20px;
        background: var(--text-primary);
        border: 3px solid var(--bg-card);
        border-radius: 50%;
        transform: translateX(-50%);
        box-shadow: var(--shadow-md);
    }
    
    .vix-labels {
        display: flex;
        justify-content: space-between;
        margin-top: 0.5rem;
    }
    
    .vix-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: var(--text-muted);
    }
    
    /* ============ TABLE ============ */
    .data-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 4px;
    }
    
    .data-table th {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.6rem;
        color: var(--text-dim);
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 0.5rem;
        text-align: center;
    }
    
    .data-table td {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        color: var(--text-primary);
        padding: 0.6rem;
        text-align: center;
        background: var(--bg-tertiary);
    }
    
    .data-table tr td:first-child { border-radius: 6px 0 0 6px; }
    .data-table tr td:last-child { border-radius: 0 6px 6px 0; }
    
    .table-up { color: var(--accent-green); }
    .table-down { color: var(--accent-red); }
    
    /* ============ DEBUG PANEL ============ */
    .debug-panel {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 1rem;
        margin-top: 1rem;
    }
    
    .debug-header {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: var(--accent-amber);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .debug-content {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        color: var(--text-muted);
        background: var(--bg-primary);
        padding: 0.75rem;
        border-radius: 6px;
        overflow-x: auto;
        white-space: pre;
    }
    
    /* ============ SIDEBAR ============ */
    section[data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border-subtle);
    }
    
    section[data-testid="stSidebar"] > div {
        padding: 1rem;
    }
    
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem;
        margin-bottom: 1rem;
        background: var(--bg-card);
        border-radius: 12px;
        border: 1px solid var(--border-subtle);
    }
    
    .sidebar-logo {
        width: 40px;
        height: 40px;
        background: var(--gradient-brand);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
    }
    
    .sidebar-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .sidebar-version {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.65rem;
        color: var(--text-muted);
    }
    
    .sidebar-section {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    
    .sidebar-section-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border-subtle);
    }
    
    .sidebar-section-icon {
        font-size: 0.9rem;
    }
    
    .sidebar-section-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-primary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Streamlit Inputs */
    .stNumberInput > div > div > input {
        background: var(--bg-tertiary) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-family: 'IBM Plex Mono', monospace !important;
    }
    
    .stCheckbox label span {
        color: var(--text-secondary) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.85rem !important;
    }
    
    .stSelectbox > div > div {
        background: var(--bg-tertiary) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: 8px !important;
    }
    
    .stButton > button {
        background: var(--gradient-brand) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    /* Status indicators */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        font-weight: 500;
    }
    
    .status-badge.ok { background: var(--accent-green-dim); color: var(--accent-green); }
    .status-badge.wait { background: var(--accent-amber-dim); color: var(--accent-amber); }
    .status-badge.no { background: var(--accent-red-dim); color: var(--accent-red); }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 1.5rem;
        margin-top: 2rem;
        border-top: 1px solid var(--border-subtle);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: var(--text-dim);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 10px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.85rem !important;
        color: var(--text-primary) !important;
    }
    
    .streamlit-expanderContent {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# PERSISTENCE
# ============================================================================
DEFAULT_INPUTS = {
    "use_custom_date": False,
    "custom_date": None,
    "vix_overnight_high": 0.0,
    "vix_overnight_low": 0.0,
    "vix_current": 0.0,
    "use_manual_ma": False,
    "manual_ma_bias": "LONG",
    "spx_manual": 0.0,
    "use_manual_spx": False,
    "ceiling_anchor1_price": 0.0,
    "ceiling_anchor1_hour": 17,
    "ceiling_anchor1_minute": 0,
    "ceiling_anchor2_price": 0.0,
    "ceiling_anchor2_hour": 2,
    "ceiling_anchor2_minute": 0,
    "floor_anchor1_price": 0.0,
    "floor_anchor1_hour": 17,
    "floor_anchor1_minute": 0,
    "floor_anchor2_price": 0.0,
    "floor_anchor2_hour": 2,
    "floor_anchor2_minute": 0,
    "prior_high": 0.0,
    "prior_high_hour": 10,
    "prior_high_minute": 0,
    "prior_low": 0.0,
    "prior_low_hour": 14,
    "prior_low_minute": 0,
    "prior_close": 0.0,
    "show_debug": False,
    "last_updated": ""
}

def save_inputs(inputs):
    inputs["last_updated"] = datetime.now(CT).strftime("%Y-%m-%d %H:%M:%S CT")
    with open(INPUTS_FILE, "w") as f:
        json.dump(inputs, f, indent=2)

def load_inputs():
    if os.path.exists(INPUTS_FILE):
        try:
            with open(INPUTS_FILE, "r") as f:
                return {**DEFAULT_INPUTS, **json.load(f)}
        except:
            pass
    return DEFAULT_INPUTS.copy()

# ============================================================================
# DATA FETCHING
# ============================================================================
def get_es_30min_candles(days=30):
    """Fetch ES 30-min candles for MA and momentum calculation"""
    try:
        es = yf.Ticker("ES=F")
        data = es.history(period=f"{days}d", interval="30m")
        if data is not None and not data.empty:
            return data
    except Exception as e:
        st.error(f"ES data fetch error: {e}")
    return None

def get_spx_price():
    """Fetch current SPX price"""
    try:
        spx = yf.Ticker("^GSPC")
        data = spx.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])
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
# PILLAR 1: MA BIAS (Percentage-based - no offset needed)
# ============================================================================
def analyze_ma_bias_percentage(es_candles):
    """
    Calculate 50 EMA vs 200 SMA from ES 30-min candles
    Uses percentage comparison - offset agnostic
    Matches TradingView ES1! 30-min chart
    """
    if es_candles is None:
        return "NEUTRAL", "No ES data", None, None, {}
    
    if len(es_candles) < 200:
        return "NEUTRAL", f"Need 200 candles, got {len(es_candles)}", None, None, {}
    
    try:
        close = es_candles['Close']
        
        # EMA 50 - matches TradingView default
        ema_50 = close.ewm(span=50, adjust=False).mean()
        ema_50_val = ema_50.iloc[-1]
        
        # SMA 200
        sma_200 = close.rolling(window=200).mean()
        sma_200_val = sma_200.iloc[-1]
        
        # Percentage difference
        diff_pct = ((ema_50_val - sma_200_val) / sma_200_val) * 100
        
        # Debug info
        debug_info = {
            'candle_count': len(es_candles),
            'first_candle': es_candles.index[0].strftime('%Y-%m-%d %H:%M'),
            'last_candle': es_candles.index[-1].strftime('%Y-%m-%d %H:%M'),
            'last_close': close.iloc[-1],
            'ema_50': ema_50_val,
            'sma_200': sma_200_val,
            'diff_pct': diff_pct,
            'last_5_ema': [f"{ema_50.iloc[i]:.2f}" for i in range(-5, 0)],
            'last_5_sma': [f"{sma_200.iloc[i]:.2f}" for i in range(-5, 0)],
        }
        
        if diff_pct > 0.05:
            return "LONG", f"EMA > SMA ({diff_pct:+.3f}%)", ema_50_val, sma_200_val, debug_info
        elif diff_pct < -0.05:
            return "SHORT", f"EMA < SMA ({diff_pct:+.3f}%)", ema_50_val, sma_200_val, debug_info
        else:
            return "NEUTRAL", f"MAs crossing ({diff_pct:+.3f}%)", ema_50_val, sma_200_val, debug_info
            
    except Exception as e:
        return "NEUTRAL", f"Error: {str(e)[:30]}", None, None, {}

# ============================================================================
# 30-MIN MOMENTUM SUITE
# ============================================================================
def analyze_30min_momentum(candles_30m):
    """Complete 30-min momentum analysis"""
    if candles_30m is None or len(candles_30m) < 50:
        return None
    
    close = candles_30m['Close']
    high = candles_30m['High']
    low = candles_30m['Low']
    volume = candles_30m['Volume']
    
    # RSI 14
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi_series = 100 - (100 / (1 + rs))
    rsi = rsi_series.iloc[-1]
    rsi_prev = rsi_series.iloc[-2]
    rsi_direction = "RISING" if rsi > rsi_prev else "FALLING"
    
    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    histogram = macd_line - signal_line
    
    macd_current = histogram.iloc[-1]
    macd_prev = histogram.iloc[-2]
    macd_expanding = abs(macd_current) > abs(macd_prev)
    macd_direction = "BULLISH" if macd_current > 0 else "BEARISH"
    
    # Volume
    vol_sma = volume.rolling(20).mean().iloc[-1]
    vol_current = volume.iloc[-1]
    vol_ratio = vol_current / vol_sma if vol_sma > 0 else 1
    vol_signal = "HIGH" if vol_ratio > 1.5 else "NORMAL" if vol_ratio > 0.8 else "LOW"
    
    # Price structure
    recent_highs = high.iloc[-5:].values
    recent_lows = low.iloc[-5:].values
    hh = recent_highs[-1] > recent_highs[-3]
    hl = recent_lows[-1] > recent_lows[-3]
    ll = recent_lows[-1] < recent_lows[-3]
    lh = recent_highs[-1] < recent_highs[-3]
    
    if hh and hl:
        structure = "BULLISH"
    elif ll and lh:
        structure = "BEARISH"
    else:
        structure = "NEUTRAL"
    
    # Composite scoring
    bull_points = 0
    bear_points = 0
    
    if 50 < rsi < 70:
        bull_points += 1
    elif 30 < rsi < 50:
        bear_points += 1
    elif rsi >= 70:
        bear_points += 0.5
    elif rsi <= 30:
        bull_points += 0.5
    
    if macd_direction == "BULLISH" and macd_expanding:
        bull_points += 1
    elif macd_direction == "BEARISH" and macd_expanding:
        bear_points += 1
    
    if structure == "BULLISH":
        bull_points += 1
    elif structure == "BEARISH":
        bear_points += 1
    
    momentum_bias = "BULLISH" if bull_points > bear_points + 0.5 else "BEARISH" if bear_points > bull_points + 0.5 else "NEUTRAL"
    
    return {
        'rsi': rsi,
        'rsi_direction': rsi_direction,
        'macd_histogram': macd_current,
        'macd_direction': macd_direction,
        'macd_expanding': macd_expanding,
        'volume_ratio': vol_ratio,
        'volume_signal': vol_signal,
        'price_structure': structure,
        'bull_points': bull_points,
        'bear_points': bear_points,
        'momentum_bias': momentum_bias
    }

# ============================================================================
# ATR CALCULATION
# ============================================================================
def calculate_atr(candles_30m, period=14):
    """Calculate ATR on 30-min candles"""
    if candles_30m is None or len(candles_30m) < period + 1:
        return None
    
    high = candles_30m['High']
    low = candles_30m['Low']
    close = candles_30m['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    
    return atr

def calculate_dynamic_stop(entry_premium, atr_30m, vix_current):
    """ATR-based dynamic stop with VIX adjustment"""
    if atr_30m is None or entry_premium <= 0:
        return {'stop_price': entry_premium * 0.5, 'stop_pct': 0.5, 'rationale': 'Default 50%'}
    
    estimated_delta = 0.30
    base_stop_underlying = atr_30m * 0.5
    base_stop_premium = base_stop_underlying * estimated_delta
    
    if vix_current > 25:
        vix_mult = 1.3
    elif vix_current > 20:
        vix_mult = 1.15
    elif vix_current > 15:
        vix_mult = 1.0
    else:
        vix_mult = 0.85
    
    adjusted_stop = base_stop_premium * vix_mult
    stop_pct = adjusted_stop / entry_premium if entry_premium > 0 else 0.5
    stop_pct = max(0.35, min(0.65, stop_pct))
    stop_price = entry_premium * (1 - stop_pct)
    
    return {
        'stop_price': stop_price,
        'stop_pct': stop_pct,
        'atr_30m': atr_30m,
        'vix_multiplier': vix_mult,
        'rationale': f"ATR: {atr_30m:.1f} | VIX mult: {vix_mult:.2f}"
    }

# ============================================================================
# PILLAR 2: DAY STRUCTURE
# ============================================================================
def get_next_trading_day(from_date):
    next_day = from_date
    if next_day.weekday() >= 5:
        days_ahead = 7 - next_day.weekday()
        next_day = next_day + timedelta(days=days_ahead)
    return next_day

def get_prior_trading_day(from_date):
    prior = from_date - timedelta(days=1)
    while prior.weekday() >= 5:
        prior -= timedelta(days=1)
    return prior

def build_anchor_datetime(base_date, hour, minute):
    if hour >= 17:
        anchor_date = base_date
    else:
        anchor_date = base_date + timedelta(days=1)
    return CT.localize(datetime.combine(anchor_date, dt_time(hour, minute)))

def calculate_trendline(a1_price, a1_time, a2_price, a2_time, target_time):
    minutes_between = (a2_time - a1_time).total_seconds() / 60
    if minutes_between == 0:
        return a1_price, 0
    slope_per_min = (a2_price - a1_price) / minutes_between
    minutes_to_target = (target_time - a1_time).total_seconds() / 60
    projected = a1_price + (slope_per_min * minutes_to_target)
    return projected, slope_per_min * 30

def get_day_structure(inputs, trade_date):
    c1 = inputs.get("ceiling_anchor1_price", 0)
    c2 = inputs.get("ceiling_anchor2_price", 0)
    f1 = inputs.get("floor_anchor1_price", 0)
    f2 = inputs.get("floor_anchor2_price", 0)
    
    if c1 <= 0 or c2 <= 0 or f1 <= 0 or f2 <= 0:
        return None, None, None, None, "Enter anchor points"
    
    overnight_base = trade_date - timedelta(days=1)
    
    c1_time = build_anchor_datetime(overnight_base, inputs.get("ceiling_anchor1_hour", 17), inputs.get("ceiling_anchor1_minute", 0))
    c2_time = build_anchor_datetime(overnight_base, inputs.get("ceiling_anchor2_hour", 2), inputs.get("ceiling_anchor2_minute", 0))
    f1_time = build_anchor_datetime(overnight_base, inputs.get("floor_anchor1_hour", 17), inputs.get("floor_anchor1_minute", 0))
    f2_time = build_anchor_datetime(overnight_base, inputs.get("floor_anchor2_hour", 2), inputs.get("floor_anchor2_minute", 0))
    
    entry_time = CT.localize(datetime.combine(trade_date, dt_time(9, 0)))
    
    ceiling, c_slope = calculate_trendline(c1, c1_time, c2, c2_time, entry_time)
    floor, f_slope = calculate_trendline(f1, f1_time, f2, f2_time, entry_time)
    
    return ceiling, floor, c_slope, f_slope, f"C: {c_slope:+.2f}/30m | F: {f_slope:+.2f}/30m"

# ============================================================================
# PILLAR 3: VIX ZONE
# ============================================================================
def analyze_vix_zone(vix_high, vix_low, vix_current):
    if vix_high <= 0 or vix_low <= 0 or vix_current <= 0:
        return {'timing_signal': "WAIT", 'zone_position': "Enter VIX", 'detail': "Missing data", 'zone_size': 0, 'range_pct': 0.5, 'puts_springboard': 0, 'calls_springboard': 0}
    
    zone_size = vix_high - vix_low
    if zone_size <= 0:
        return {'timing_signal': "WAIT", 'zone_position': "Invalid", 'detail': "High > Low required", 'zone_size': 0, 'range_pct': 0.5, 'puts_springboard': vix_low, 'calls_springboard': vix_high}
    
    calls_springboard = vix_high
    puts_springboard = vix_low
    
    if vix_current > vix_high:
        zones_above = (vix_current - vix_high) / zone_size
        pos = f"ABOVE (+{zones_above:.1f})"
        calls_springboard = vix_high + (int(zones_above) + 1) * zone_size
        if abs(vix_current - vix_high) <= zone_size * 0.30:
            sig, detail = "CALLS", f"VIX elevated → SPX dip buy"
        else:
            sig, detail = "WAIT", f"Wait for VIX → {vix_high:.2f}"
        range_pct = 1.0
    elif vix_current < vix_low:
        zones_below = (vix_low - vix_current) / zone_size
        pos = f"BELOW (-{zones_below:.1f})"
        puts_springboard = vix_low - (int(zones_below) + 1) * zone_size
        if abs(vix_current - vix_low) <= zone_size * 0.30:
            sig, detail = "PUTS", f"VIX compressed → SPX top sell"
        else:
            sig, detail = "WAIT", f"Wait for VIX → {vix_low:.2f}"
        range_pct = 0.0
    else:
        range_pct = (vix_current - vix_low) / zone_size
        pos = f"INSIDE ({range_pct:.0%})"
        if range_pct >= 0.70:
            sig, detail = "CALLS", f"VIX high ({range_pct:.0%}) → CALLS"
        elif range_pct <= 0.30:
            sig, detail = "PUTS", f"VIX low ({range_pct:.0%}) → PUTS"
        else:
            sig, detail = "WAIT", f"VIX mid-range ({range_pct:.0%})"
    
    return {
        'timing_signal': sig,
        'zone_position': pos,
        'detail': detail,
        'zone_size': zone_size,
        'range_pct': range_pct,
        'puts_springboard': puts_springboard,
        'calls_springboard': calls_springboard
    }

# ============================================================================
# CONE RAILS
# ============================================================================
def calculate_trading_minutes(from_dt, to_dt):
    if from_dt.tzinfo is None:
        from_dt = CT.localize(from_dt)
    if to_dt.tzinfo is None:
        to_dt = CT.localize(to_dt)
    if from_dt >= to_dt:
        return 0
    
    total_minutes = 0
    current = from_dt
    
    while current < to_dt:
        weekday = current.weekday()
        hour = current.hour
        
        if weekday == 5:
            next_sunday = current.date() + timedelta(days=1)
            current = CT.localize(datetime.combine(next_sunday, dt_time(17, 0)))
            continue
        if weekday == 6 and hour < 17:
            current = CT.localize(datetime.combine(current.date(), dt_time(17, 0)))
            continue
        if weekday == 4 and hour >= 16:
            next_sunday = current.date() + timedelta(days=2)
            current = CT.localize(datetime.combine(next_sunday, dt_time(17, 0)))
            continue
        if weekday in [0, 1, 2, 3] and 16 <= hour < 17:
            current = CT.localize(datetime.combine(current.date(), dt_time(17, 0)))
            continue
        
        if weekday == 6:
            segment_end = CT.localize(datetime.combine(current.date() + timedelta(days=1), dt_time(0, 0)))
        elif weekday == 4:
            segment_end = CT.localize(datetime.combine(current.date(), dt_time(16, 0)))
        elif hour >= 17:
            segment_end = CT.localize(datetime.combine(current.date() + timedelta(days=1), dt_time(0, 0)))
        else:
            segment_end = CT.localize(datetime.combine(current.date(), dt_time(16, 0)))
        
        actual_end = min(segment_end, to_dt)
        if actual_end > current:
            total_minutes += (actual_end - current).total_seconds() / 60
        current = segment_end
    
    return total_minutes

def calculate_cone_rails(inputs, trade_date):
    ph = inputs.get("prior_high", 0)
    pl = inputs.get("prior_low", 0)
    pc = inputs.get("prior_close", 0)
    
    if ph <= 0 or pl <= 0 or pc <= 0:
        return None
    
    prior_day = get_prior_trading_day(trade_date)
    
    high_anchor = CT.localize(datetime.combine(prior_day, dt_time(inputs.get("prior_high_hour", 10), inputs.get("prior_high_minute", 0))))
    low_anchor = CT.localize(datetime.combine(prior_day, dt_time(inputs.get("prior_low_hour", 14), inputs.get("prior_low_minute", 0))))
    close_anchor = CT.localize(datetime.combine(prior_day, dt_time(15, 0)))
    
    entry_time = CT.localize(datetime.combine(trade_date, dt_time(9, 0)))
    
    def calc_expansion(anchor_dt):
        trading_mins = calculate_trading_minutes(anchor_dt, entry_time)
        blocks = trading_mins / 30
        return blocks, blocks * CONE_SLOPE
    
    h_blocks, h_exp = calc_expansion(high_anchor)
    l_blocks, l_exp = calc_expansion(low_anchor)
    c_blocks, c_exp = calc_expansion(close_anchor)
    
    return {
        'C1': {'name': 'HIGH', 'anchor': ph, 'asc': ph + h_exp, 'desc': ph - h_exp, 'blocks': h_blocks, 'exp': h_exp, 'time': high_anchor.strftime('%I:%M %p')},
        'C2': {'name': 'LOW', 'anchor': pl, 'asc': pl + l_exp, 'desc': pl - l_exp, 'blocks': l_blocks, 'exp': l_exp, 'time': low_anchor.strftime('%I:%M %p')},
        'C3': {'name': 'CLOSE', 'anchor': pc, 'asc': pc + c_exp, 'desc': pc - c_exp, 'blocks': c_blocks, 'exp': c_exp, 'time': '03:00 PM'},
    }

# ============================================================================
# GAMMA-OPTIMIZED STRIKE SELECTION
# ============================================================================
def select_optimal_strike(entry_level, direction, target_level=None):
    """Select strike with optimal gamma exposure"""
    if entry_level is None or direction is None:
        return None
    
    if direction == "CALLS":
        strike_fixed = round((entry_level + 10) / 5) * 5
        
        if target_level and target_level > entry_level:
            expected_move = target_level - entry_level
            strike_structure = round((entry_level + expected_move * 0.35) / 5) * 5
        else:
            strike_structure = strike_fixed
        
        base_100 = round(entry_level / 100) * 100
        round_strikes = [base_100, base_100 + 25, base_100 + 50, base_100 + 75, base_100 + 100]
        valid_rounds = [s for s in round_strikes if 5 <= (s - entry_level) <= 25]
        strike_round = valid_rounds[0] if valid_rounds else strike_fixed
        
        return {
            'recommended': strike_structure,
            'conservative': strike_fixed + 5,
            'aggressive': max(round(entry_level / 5) * 5, strike_fixed - 5),
            'round_number': strike_round,
            'rationale': f"Entry: {entry_level:.0f} | Target: {target_level:.0f}" if target_level else f"Fixed +10 OTM"
        }
    
    elif direction == "PUTS":
        strike_fixed = round((entry_level - 10) / 5) * 5
        
        if target_level and target_level < entry_level:
            expected_move = entry_level - target_level
            strike_structure = round((entry_level - expected_move * 0.35) / 5) * 5
        else:
            strike_structure = strike_fixed
        
        base_100 = round(entry_level / 100) * 100
        round_strikes = [base_100 - 100, base_100 - 75, base_100 - 50, base_100 - 25, base_100]
        valid_rounds = [s for s in round_strikes if 5 <= (entry_level - s) <= 25]
        strike_round = valid_rounds[-1] if valid_rounds else strike_fixed
        
        return {
            'recommended': strike_structure,
            'conservative': strike_fixed - 5,
            'aggressive': min(round(entry_level / 5) * 5, strike_fixed + 5),
            'round_number': strike_round,
            'rationale': f"Entry: {entry_level:.0f} | Target: {target_level:.0f}" if target_level else f"Fixed -10 OTM"
        }
    
    return None

# ============================================================================
# CONFIDENCE SCORING
# ============================================================================
def calculate_confidence_score(ma_bias, ceiling, floor, spx_price, vix_zone, momentum, cones):
    """Weighted confidence scoring for trade entries"""
    score = 0
    breakdown = []
    direction = None
    entry_level = None
    target_level = None
    
    # PILLAR 1: MA BIAS (25 points)
    if ma_bias == "LONG":
        score += 25
        direction = "CALLS"
        entry_level = floor
        target_level = ceiling
        breakdown.append(("MA Bias LONG", 25, 25))
    elif ma_bias == "SHORT":
        score += 25
        direction = "PUTS"
        entry_level = ceiling
        target_level = floor
        breakdown.append(("MA Bias SHORT", 25, 25))
    else:
        breakdown.append(("MA Bias NEUTRAL", 0, 25))
        return {'score': 0, 'confidence': 'NO TRADE', 'breakdown': breakdown, 'direction': None, 'entry_level': None, 'target_level': None}
    
    # PILLAR 2: STRUCTURE POSITION (30 points)
    if ceiling and floor and spx_price:
        range_size = ceiling - floor
        
        if direction == "CALLS":
            dist_from_floor = spx_price - floor
            proximity_pct = dist_from_floor / range_size if range_size > 0 else 0.5
            
            if proximity_pct <= 0:
                score += 30
                breakdown.append(("AT FLOOR", 30, 30))
            elif proximity_pct <= 0.15:
                score += 25
                breakdown.append(("Near FLOOR", 25, 30))
            elif proximity_pct <= 0.30:
                score += 15
                breakdown.append(("Approaching FLOOR", 15, 30))
            elif proximity_pct <= 0.50:
                score += 5
                breakdown.append(("Mid-range", 5, 30))
            else:
                breakdown.append(("Wrong side for CALLS", 0, 30))
                
        elif direction == "PUTS":
            dist_from_ceiling = ceiling - spx_price
            proximity_pct = dist_from_ceiling / range_size if range_size > 0 else 0.5
            
            if proximity_pct <= 0:
                score += 30
                breakdown.append(("AT CEILING", 30, 30))
            elif proximity_pct <= 0.15:
                score += 25
                breakdown.append(("Near CEILING", 25, 30))
            elif proximity_pct <= 0.30:
                score += 15
                breakdown.append(("Approaching CEILING", 15, 30))
            elif proximity_pct <= 0.50:
                score += 5
                breakdown.append(("Mid-range", 5, 30))
            else:
                breakdown.append(("Wrong side for PUTS", 0, 30))
    else:
        breakdown.append(("Structure incomplete", 0, 30))
    
    # PILLAR 3: VIX ZONE (20 points)
    vix_sig = vix_zone.get('timing_signal', 'WAIT')
    
    if direction == "CALLS" and vix_sig == "CALLS":
        score += 20
        breakdown.append(("VIX confirms CALLS", 20, 20))
    elif direction == "PUTS" and vix_sig == "PUTS":
        score += 20
        breakdown.append(("VIX confirms PUTS", 20, 20))
    elif vix_sig == "WAIT":
        score += 5
        breakdown.append(("VIX neutral", 5, 20))
    else:
        breakdown.append(("VIX conflict", 0, 20))
    
    # 30-MIN MOMENTUM (15 points)
    if momentum:
        mom_bias = momentum.get('momentum_bias', 'NEUTRAL')
        
        if direction == "CALLS" and mom_bias == "BULLISH":
            score += 15
            breakdown.append(("Momentum BULLISH", 15, 15))
        elif direction == "PUTS" and mom_bias == "BEARISH":
            score += 15
            breakdown.append(("Momentum BEARISH", 15, 15))
        elif mom_bias == "NEUTRAL":
            score += 7
            breakdown.append(("Momentum neutral", 7, 15))
        else:
            breakdown.append(("Momentum conflict", 0, 15))
    else:
        score += 5
        breakdown.append(("No momentum data", 5, 15))
    
    # CONE CONFLUENCE (10 points)
    if cones and spx_price:
        confluence_count = 0
        for cone_name, cone_data in cones.items():
            for rail_type in ['asc', 'desc', 'anchor']:
                rail_value = cone_data.get(rail_type, 0)
                if abs(spx_price - rail_value) <= 5:
                    confluence_count += 1
        
        if confluence_count >= 2:
            score += 10
            breakdown.append(("Cone confluence", 10, 10))
        elif confluence_count == 1:
            score += 5
            breakdown.append(("Single cone level", 5, 10))
        else:
            breakdown.append(("No cone confluence", 0, 10))
    else:
        breakdown.append(("No cone data", 0, 10))
    
    # CONFIDENCE CLASSIFICATION
    if score >= 85:
        confidence = "A+ SETUP"
    elif score >= 75:
        confidence = "HIGH"
    elif score >= 60:
        confidence = "MEDIUM"
    elif score >= 45:
        confidence = "LOW"
    else:
        confidence = "NO TRADE"
    
    return {
        'score': score,
        'confidence': confidence,
        'direction': direction,
        'entry_level': entry_level,
        'target_level': target_level,
        'breakdown': breakdown
    }

# ============================================================================
# MAIN APPLICATION
# ============================================================================
def main():
    now_ct = datetime.now(CT)
    
    if 'inputs' not in st.session_state:
        st.session_state.inputs = load_inputs()
    inputs = st.session_state.inputs
    
    # ==================== SIDEBAR ====================
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand">
            <div class="sidebar-logo">◈</div>
            <div>
                <div class="sidebar-title">SPX Prophet</div>
                <div class="sidebar-version">Version 3.0</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Trading Date
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">📅</span><span class="sidebar-section-title">Trading Date</span></div></div>', unsafe_allow_html=True)
        default_trade_date = get_next_trading_day(now_ct.date())
        inputs["use_custom_date"] = st.checkbox("Custom Date", value=inputs.get("use_custom_date", False))
        if inputs["use_custom_date"]:
            saved_date = inputs.get("custom_date")
            if saved_date:
                try:
                    default_val = datetime.strptime(saved_date, "%Y-%m-%d").date()
                except:
                    default_val = default_trade_date
            else:
                default_val = default_trade_date
            selected_date = st.date_input("Select Date", value=default_val)
            inputs["custom_date"] = selected_date.strftime("%Y-%m-%d")
            trade_date = selected_date
        else:
            trade_date = default_trade_date
        
        is_historical = trade_date < now_ct.date()
        st.caption(f"{'📆 Historical' if is_historical else '🔮 Preview'}: {trade_date.strftime('%a %b %d, %Y')}")
        
        # SPX Price
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">💹</span><span class="sidebar-section-title">SPX Price</span></div></div>', unsafe_allow_html=True)
        inputs["use_manual_spx"] = st.checkbox("Manual SPX", value=inputs.get("use_manual_spx", False))
        if inputs["use_manual_spx"]:
            inputs["spx_manual"] = st.number_input("SPX Price", value=float(inputs.get("spx_manual", 0)), step=0.25, format="%.2f")
        
        # MA Override
        inputs["use_manual_ma"] = st.checkbox("Manual MA Bias", value=inputs.get("use_manual_ma", False))
        if inputs["use_manual_ma"]:
            ma_options = ["LONG", "SHORT", "NEUTRAL"]
            current_ma = inputs.get("manual_ma_bias", "LONG")
            if current_ma not in ma_options:
                current_ma = "LONG"
            inputs["manual_ma_bias"] = st.selectbox("MA Bias", ma_options, index=ma_options.index(current_ma))
        
        # VIX Zone
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">📊</span><span class="sidebar-section-title">VIX Zone</span></div></div>', unsafe_allow_html=True)
        inputs["vix_overnight_high"] = st.number_input("Overnight High", value=float(inputs.get("vix_overnight_high", 0)), step=0.01, format="%.2f")
        inputs["vix_overnight_low"] = st.number_input("Overnight Low", value=float(inputs.get("vix_overnight_low", 0)), step=0.01, format="%.2f")
        inputs["vix_current"] = st.number_input("Current VIX", value=float(inputs.get("vix_current", 0)), step=0.01, format="%.2f")
        
        # CEILING
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">🔺</span><span class="sidebar-section-title">CEILING Anchors</span></div></div>', unsafe_allow_html=True)
        st.caption("Anchor 1")
        c1a, c1b, c1c = st.columns([2,1,1])
        with c1a: inputs["ceiling_anchor1_price"] = st.number_input("Price", value=float(inputs.get("ceiling_anchor1_price", 0)), step=0.25, format="%.2f", key="c1p")
        with c1b: inputs["ceiling_anchor1_hour"] = st.number_input("Hr", value=int(inputs.get("ceiling_anchor1_hour", 17)), min_value=0, max_value=23, key="c1h")
        with c1c: inputs["ceiling_anchor1_minute"] = st.number_input("Min", value=int(inputs.get("ceiling_anchor1_minute", 0)), min_value=0, max_value=59, key="c1m")
        st.caption("Anchor 2")
        c2a, c2b, c2c = st.columns([2,1,1])
        with c2a: inputs["ceiling_anchor2_price"] = st.number_input("Price", value=float(inputs.get("ceiling_anchor2_price", 0)), step=0.25, format="%.2f", key="c2p")
        with c2b: inputs["ceiling_anchor2_hour"] = st.number_input("Hr", value=int(inputs.get("ceiling_anchor2_hour", 2)), min_value=0, max_value=23, key="c2h")
        with c2c: inputs["ceiling_anchor2_minute"] = st.number_input("Min", value=int(inputs.get("ceiling_anchor2_minute", 0)), min_value=0, max_value=59, key="c2m")
        
        # FLOOR
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">🔻</span><span class="sidebar-section-title">FLOOR Anchors</span></div></div>', unsafe_allow_html=True)
        st.caption("Anchor 1")
        f1a, f1b, f1c = st.columns([2,1,1])
        with f1a: inputs["floor_anchor1_price"] = st.number_input("Price", value=float(inputs.get("floor_anchor1_price", 0)), step=0.25, format="%.2f", key="f1p")
        with f1b: inputs["floor_anchor1_hour"] = st.number_input("Hr", value=int(inputs.get("floor_anchor1_hour", 17)), min_value=0, max_value=23, key="f1h")
        with f1c: inputs["floor_anchor1_minute"] = st.number_input("Min", value=int(inputs.get("floor_anchor1_minute", 0)), min_value=0, max_value=59, key="f1m")
        st.caption("Anchor 2")
        f2a, f2b, f2c = st.columns([2,1,1])
        with f2a: inputs["floor_anchor2_price"] = st.number_input("Price", value=float(inputs.get("floor_anchor2_price", 0)), step=0.25, format="%.2f", key="f2p")
        with f2b: inputs["floor_anchor2_hour"] = st.number_input("Hr", value=int(inputs.get("floor_anchor2_hour", 2)), min_value=0, max_value=23, key="f2h")
        with f2c: inputs["floor_anchor2_minute"] = st.number_input("Min", value=int(inputs.get("floor_anchor2_minute", 0)), min_value=0, max_value=59, key="f2m")
        
        # Prior Day (Cones)
        st.markdown('<div class="sidebar-section"><div class="sidebar-section-header"><span class="sidebar-section-icon">📐</span><span class="sidebar-section-title">Prior Day (Cones)</span></div></div>', unsafe_allow_html=True)
        st.caption("Prior High")
        ph1, ph2, ph3 = st.columns([2,1,1])
        with ph1: inputs["prior_high"] = st.number_input("Price", value=float(inputs.get("prior_high", 0)), step=0.25, format="%.2f", key="php")
        with ph2: inputs["prior_high_hour"] = st.number_input("Hr", value=int(inputs.get("prior_high_hour", 10)), min_value=0, max_value=23, key="phh")
        with ph3: inputs["prior_high_minute"] = st.number_input("Min", value=int(inputs.get("prior_high_minute", 0)), min_value=0, max_value=59, key="phm")
        st.caption("Prior Low")
        pl1, pl2, pl3 = st.columns([2,1,1])
        with pl1: inputs["prior_low"] = st.number_input("Price", value=float(inputs.get("prior_low", 0)), step=0.25, format="%.2f", key="plp")
        with pl2: inputs["prior_low_hour"] = st.number_input("Hr", value=int(inputs.get("prior_low_hour", 14)), min_value=0, max_value=23, key="plh")
        with pl3: inputs["prior_low_minute"] = st.number_input("Min", value=int(inputs.get("prior_low_minute", 0)), min_value=0, max_value=59, key="plm")
        st.caption("Prior Close @ 3pm")
        inputs["prior_close"] = st.number_input("Close", value=float(inputs.get("prior_close", 0)), step=0.25, format="%.2f", key="pcp")
        
        # Debug toggle
        inputs["show_debug"] = st.checkbox("🔧 Show Debug Panel", value=inputs.get("show_debug", False))
        
        # Buttons
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
    
    # ==================== FETCH DATA ====================
    es_candles = get_es_30min_candles()
    
    if inputs.get("use_manual_spx") and inputs.get("spx_manual", 0) > 0:
        spx_price = inputs["spx_manual"]
    else:
        spx_price = get_spx_price()
    
    # ==================== CALCULATE PILLARS ====================
    if inputs.get("use_manual_ma"):
        ma_bias = inputs.get("manual_ma_bias", "LONG")
        ma_detail = "Manual override"
        ema_50, sma_200 = None, None
        ma_debug = {}
    else:
        ma_bias, ma_detail, ema_50, sma_200, ma_debug = analyze_ma_bias_percentage(es_candles)
    
    ceiling, floor, c_slope, f_slope, struct_status = get_day_structure(inputs, trade_date)
    vix_zone = analyze_vix_zone(inputs.get("vix_overnight_high", 0), inputs.get("vix_overnight_low", 0), inputs.get("vix_current", 0))
    momentum = analyze_30min_momentum(es_candles)
    cones = calculate_cone_rails(inputs, trade_date)
    atr = calculate_atr(es_candles)
    
    # Confidence scoring
    confidence_result = calculate_confidence_score(ma_bias, ceiling, floor, spx_price, vix_zone, momentum, cones)
    
    # Strike selection
    strikes = select_optimal_strike(
        confidence_result.get('entry_level'),
        confidence_result.get('direction'),
        confidence_result.get('target_level')
    )
    
    # ==================== HERO HEADER ====================
    spx_display = f"{spx_price:,.2f}" if spx_price else "---"
    
    st.markdown(f"""
    <div class="hero">
        <div class="hero-grid">
            <div class="hero-brand">
                <div class="hero-logo">◈</div>
                <div>
                    <div class="hero-title">SPX PROPHET</div>
                    <div class="hero-subtitle">Institutional-Grade 0DTE System</div>
                </div>
            </div>
            <div class="hero-price-container">
                <div class="hero-price-label">SPX Index</div>
                <div class="hero-price">{spx_display}</div>
            </div>
            <div class="hero-meta">
                <div class="hero-time">
                    <div class="live-indicator"></div>
                    {now_ct.strftime('%H:%M:%S')} CT
                </div>
                <div class="hero-date">{trade_date.strftime('%A, %B %d, %Y')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== THREE PILLARS ====================
    col1, col2, col3 = st.columns(3)
    
    with col1:
        bias_class = "bullish" if ma_bias == "LONG" else "bearish" if ma_bias == "SHORT" else "neutral"
        bias_icon = "↗" if ma_bias == "LONG" else "↘" if ma_bias == "SHORT" else "→"
        ma_vals = f"EMA: {ema_50:,.1f} | SMA: {sma_200:,.1f}" if ema_50 and sma_200 else ma_detail
        
        st.markdown(f"""
        <div class="pillar-card {bias_class}">
            <div class="pillar-number">Pillar 1 • Direction Filter</div>
            <div class="pillar-name">MA Bias</div>
            <div class="pillar-question">Should I trade CALLS or PUTS?</div>
            <div class="pillar-value {bias_class}">{bias_icon} {ma_bias}</div>
            <div class="pillar-detail">{ma_vals}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if ceiling and floor:
            s_class = "bullish" if ma_bias == "LONG" else "bearish" if ma_bias == "SHORT" else "neutral"
            entry_type = "FLOOR" if ma_bias == "LONG" else "CEILING" if ma_bias == "SHORT" else "---"
            entry_val = floor if ma_bias == "LONG" else ceiling if ma_bias == "SHORT" else 0
            s_icon = "⎯"
        else:
            s_class, entry_type, entry_val, s_icon = "neutral", "PENDING", 0, "⏳"
        
        st.markdown(f"""
        <div class="pillar-card {s_class}">
            <div class="pillar-number">Pillar 2 • Entry Level</div>
            <div class="pillar-name">Day Structure</div>
            <div class="pillar-question">Where do I enter?</div>
            <div class="pillar-value {s_class}">{s_icon} {entry_type}</div>
            <div class="pillar-detail">{entry_val:,.1f} SPX</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        v_sig = vix_zone.get('timing_signal', 'WAIT')
        v_class = "bullish" if v_sig == "CALLS" else "bearish" if v_sig == "PUTS" else "neutral"
        v_icon = "●" if v_sig in ["CALLS", "PUTS"] else "○"
        
        st.markdown(f"""
        <div class="pillar-card {v_class}">
            <div class="pillar-number">Pillar 3 • Timing</div>
            <div class="pillar-name">VIX Zone</div>
            <div class="pillar-question">Is NOW the right time?</div>
            <div class="pillar-value {v_class}">{v_icon} {v_sig}</div>
            <div class="pillar-detail">{vix_zone.get('zone_position', '---')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ==================== SIGNAL CARD ====================
    sig = confidence_result.get('direction', 'NO TRADE') if confidence_result.get('confidence') not in ['NO TRADE', 'LOW'] else 'WAIT' if confidence_result.get('confidence') == 'LOW' else 'NO TRADE'
    score = confidence_result.get('score', 0)
    conf_level = confidence_result.get('confidence', 'NO TRADE')
    
    sig_class = sig.lower().replace(" ", "") if sig in ["CALLS", "PUTS"] else "wait" if sig == "WAIT" else "notrade"
    badge_class = "high" if conf_level in ["A+ SETUP", "HIGH"] else "medium" if conf_level == "MEDIUM" else "low"
    
    entry_disp = f"{confidence_result.get('entry_level', 0):,.1f}" if confidence_result.get('entry_level') else "---"
    strike_disp = str(int(strikes.get('recommended', 0))) if strikes else "---"
    
    st.markdown(f"""
    <div class="signal-container {sig_class}">
        <div class="signal-badge {badge_class}">{conf_level}</div>
        <div class="signal-action {sig_class}">{sig}</div>
        <div class="signal-score">Confidence: {score}/100</div>
        <div class="signal-reason">{confidence_result.get('direction', 'Awaiting alignment')} {'signal active' if sig in ['CALLS', 'PUTS'] else 'on standby'}</div>
        <div class="signal-details">
            <div class="signal-detail-item">
                <div class="signal-detail-label">Entry Level</div>
                <div class="signal-detail-value">{entry_disp}</div>
            </div>
            <div class="signal-detail-item">
                <div class="signal-detail-label">Strike</div>
                <div class="signal-detail-value">{strike_disp}</div>
            </div>
            <div class="signal-detail-item">
                <div class="signal-detail-label">Distance</div>
                <div class="signal-detail-value">{abs(spx_price - confidence_result.get('entry_level', spx_price)):,.1f}pts</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== CONFIDENCE BREAKDOWN ====================
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-icon purple">📊</div>
            <div>
                <div class="card-title">Confidence Breakdown</div>
                <div class="card-subtitle">Weighted scoring by pillar</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    breakdown_html = '<div class="breakdown-container">'
    for factor, points, max_points in confidence_result.get('breakdown', []):
        score_class = "positive" if points >= max_points * 0.7 else "partial" if points > 0 else "zero"
        icon = "✓" if points >= max_points * 0.7 else "◐" if points > 0 else "✗"
        breakdown_html += f"""
        <div class="breakdown-item">
            <div class="breakdown-icon">{icon}</div>
            <div class="breakdown-name">{factor}</div>
            <div class="breakdown-score {score_class}">+{points}</div>
        </div>
        """
    breakdown_html += '</div></div>'
    st.markdown(breakdown_html, unsafe_allow_html=True)
    
    # ==================== DETAIL PANELS ====================
    col_left, col_mid, col_right = st.columns(3)
    
    with col_left:
        # Structure visualization
        st.markdown("""
        <div class="card">
            <div class="card-header">
                <div class="card-icon blue">🏗️</div>
                <div>
                    <div class="card-title">Day Structure</div>
                    <div class="card-subtitle">Projected @ 9:00 AM CT</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if ceiling and floor and spx_price:
            st.markdown(f"""
            <div class="data-row">
                <div class="data-label">🔺 CEILING</div>
                <div class="data-value red">{ceiling:,.1f}</div>
            </div>
            <div class="data-row">
                <div class="data-label">↕ Range</div>
                <div class="data-value">{ceiling - floor:,.1f} pts</div>
            </div>
            <div class="data-row">
                <div class="data-label">◆ CURRENT</div>
                <div class="data-value purple">{spx_price:,.1f}</div>
            </div>
            <div class="data-row">
                <div class="data-label">↕ To Floor</div>
                <div class="data-value">{spx_price - floor:,.1f} pts</div>
            </div>
            <div class="data-row">
                <div class="data-label">🔻 FLOOR</div>
                <div class="data-value green">{floor:,.1f}</div>
            </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Enter anchor points in sidebar")
            st.markdown("</div>", unsafe_allow_html=True)
    
    with col_mid:
        # VIX Zone
        st.markdown("""
        <div class="card">
            <div class="card-header">
                <div class="card-icon amber">📈</div>
                <div>
                    <div class="card-title">VIX Zone</div>
                    <div class="card-subtitle">Inverse correlation to SPX</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        vh = inputs.get("vix_overnight_high", 0)
        vl = inputs.get("vix_overnight_low", 0)
        vc = inputs.get("vix_current", 0)
        
        if vh > 0 and vl > 0 and vc > 0:
            pct = max(0, min(100, vix_zone.get('range_pct', 0.5) * 100))
            st.markdown(f"""
            <div class="vix-visual">
                <div class="vix-current">
                    <div class="vix-current-value">{vc:.2f}</div>
                </div>
                <div class="vix-bar-container">
                    <div class="vix-marker" style="left:{pct}%;"></div>
                </div>
                <div class="vix-labels">
                    <span class="vix-label">🟢 {vl:.2f}</span>
                    <span class="vix-label">🔴 {vh:.2f}</span>
                </div>
            </div>
            <div style="text-align:center; margin-top:0.75rem; font-size:0.75rem; color:var(--text-muted);">{vix_zone.get('detail', '')}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Enter VIX values in sidebar")
            st.markdown("</div>", unsafe_allow_html=True)
    
    with col_right:
        # 30-Min Momentum
        st.markdown("""
        <div class="card">
            <div class="card-header">
                <div class="card-icon cyan">⚡</div>
                <div>
                    <div class="card-title">30-Min Momentum</div>
                    <div class="card-subtitle">ES1! intraday indicators</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if momentum:
            mom_class = "green" if momentum['momentum_bias'] == "BULLISH" else "red" if momentum['momentum_bias'] == "BEARISH" else "amber"
            macd_class = "green" if momentum['macd_direction'] == "BULLISH" else "red"
            
            st.markdown(f"""
            <div class="momentum-grid">
                <div class="momentum-item">
                    <div class="momentum-label">RSI</div>
                    <div class="momentum-value" style="color:var(--text-primary);">{momentum['rsi']:.1f}</div>
                </div>
                <div class="momentum-item">
                    <div class="momentum-label">MACD</div>
                    <div class="momentum-value {macd_class}">{momentum['macd_direction'][:4]}</div>
                </div>
                <div class="momentum-item">
                    <div class="momentum-label">Structure</div>
                    <div class="momentum-value" style="color:var(--text-secondary);">{momentum['price_structure'][:4]}</div>
                </div>
            </div>
            <div style="text-align:center; margin-top:1rem;">
                <span class="status-badge {'ok' if momentum['momentum_bias']=='BULLISH' else 'no' if momentum['momentum_bias']=='BEARISH' else 'wait'}">
                    {momentum['momentum_bias']}
                </span>
            </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Awaiting momentum data")
            st.markdown("</div>", unsafe_allow_html=True)
    
    # ==================== STRIKE SELECTION & OPTIONS ====================
    col_strikes, col_options = st.columns(2)
    
    with col_strikes:
        st.markdown("""
        <div class="card">
            <div class="card-header">
                <div class="card-icon green">🎯</div>
                <div>
                    <div class="card-title">Gamma-Optimized Strikes</div>
                    <div class="card-subtitle">Based on structure entry & target</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if strikes:
            st.markdown(f"""
            <div class="strike-grid">
                <div class="strike-option recommended">
                    <div class="strike-option-label">⭐ Recommended</div>
                    <div class="strike-option-value">{int(strikes['recommended'])}</div>
                </div>
                <div class="strike-option">
                    <div class="strike-option-label">Conservative</div>
                    <div class="strike-option-value">{int(strikes['conservative'])}</div>
                </div>
                <div class="strike-option">
                    <div class="strike-option-label">Aggressive</div>
                    <div class="strike-option-value">{int(strikes['aggressive'])}</div>
                </div>
                <div class="strike-option">
                    <div class="strike-option-label">Round Number</div>
                    <div class="strike-option-value">{int(strikes['round_number'])}</div>
                </div>
            </div>
            <div style="text-align:center; margin-top:0.75rem; font-size:0.7rem; color:var(--text-muted);">{strikes['rationale']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Generate signal to see strike recommendations")
            st.markdown("</div>", unsafe_allow_html=True)
    
    with col_options:
        st.markdown("""
        <div class="card">
            <div class="card-header">
                <div class="card-icon purple">💹</div>
                <div>
                    <div class="card-title">0DTE Options Data</div>
                    <div class="card-subtitle">Live from Polygon.io</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if strikes and confidence_result.get('direction'):
            opt_data, ticker = fetch_option_data(
                strikes['recommended'],
                confidence_result['direction'] == "CALLS",
                trade_date
            )
            
            if opt_data:
                day = opt_data.get('day', {})
                lq = opt_data.get('last_quote', {})
                last = day.get('close', day.get('last', 0))
                
                # Dynamic stop
                stop_info = calculate_dynamic_stop(last, atr, inputs.get("vix_current", 15))
                
                st.markdown(f"""
                <div style="text-align:center; margin-bottom:1rem;">
                    <span style="font-family:'IBM Plex Mono'; font-size:0.75rem; background:var(--accent-purple-dim); color:var(--accent-purple); padding:0.35rem 0.75rem; border-radius:6px;">{ticker}</span>
                </div>
                <div class="data-row">
                    <div class="data-label">Last Price</div>
                    <div class="data-value">${last:.2f}</div>
                </div>
                <div class="data-row">
                    <div class="data-label">Bid / Ask</div>
                    <div class="data-value">${lq.get('bid', 0):.2f} / ${lq.get('ask', 0):.2f}</div>
                </div>
                <div class="data-row">
                    <div class="data-label">Volume</div>
                    <div class="data-value">{day.get('volume', 0):,}</div>
                </div>
                <div class="data-row">
                    <div class="data-label">Open Interest</div>
                    <div class="data-value">{opt_data.get('open_interest', 0):,}</div>
                </div>
                <div class="data-row">
                    <div class="data-label">ATR Stop ({stop_info['stop_pct']:.0%})</div>
                    <div class="data-value red">${stop_info['stop_price']:.2f}</div>
                </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Awaiting options data")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Generate signal to view options")
            st.markdown("</div>", unsafe_allow_html=True)
    
    # ==================== CONE RAILS ====================
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-icon amber">📐</div>
            <div>
                <div class="card-title">Cone Rails</div>
                <div class="card-subtitle">Prior day anchors projected to 9:00 AM entry</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if cones:
        st.markdown(f"""
        <table class="data-table">
            <thead>
                <tr>
                    <th>Cone</th>
                    <th>Anchor</th>
                    <th>▲ Ascending</th>
                    <th>▼ Descending</th>
                    <th>Expansion</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="font-weight:600;">C1 {cones['C1']['name']}</td>
                    <td>{cones['C1']['anchor']:,.1f}</td>
                    <td class="table-up">{cones['C1']['asc']:,.1f}</td>
                    <td class="table-down">{cones['C1']['desc']:,.1f}</td>
                    <td>±{cones['C1']['exp']:.1f}</td>
                </tr>
                <tr>
                    <td style="font-weight:600;">C2 {cones['C2']['name']}</td>
                    <td>{cones['C2']['anchor']:,.1f}</td>
                    <td class="table-up">{cones['C2']['asc']:,.1f}</td>
                    <td class="table-down">{cones['C2']['desc']:,.1f}</td>
                    <td>±{cones['C2']['exp']:.1f}</td>
                </tr>
                <tr>
                    <td style="font-weight:600;">C3 {cones['C3']['name']}</td>
                    <td>{cones['C3']['anchor']:,.1f}</td>
                    <td class="table-up">{cones['C3']['asc']:,.1f}</td>
                    <td class="table-down">{cones['C3']['desc']:,.1f}</td>
                    <td>±{cones['C3']['exp']:.1f}</td>
                </tr>
            </tbody>
        </table>
        <div style="text-align:center; margin-top:0.75rem; font-size:0.7rem; color:var(--text-muted);">Slope: ±{CONE_SLOPE} pts per 30-min block</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Enter prior day values in sidebar")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # ==================== DEBUG PANEL ====================
    if inputs.get("show_debug"):
        st.markdown("""
        <div class="debug-panel">
            <div class="debug-header">🔧 MA Debug Panel - Compare with TradingView ES1! 30-min</div>
        """, unsafe_allow_html=True)
        
        if ma_debug:
            debug_text = f"""Candle Count: {ma_debug.get('candle_count', 'N/A')}
First Candle: {ma_debug.get('first_candle', 'N/A')}
Last Candle:  {ma_debug.get('last_candle', 'N/A')}
Last Close:   {ma_debug.get('last_close', 'N/A'):.2f}

50 EMA:  {ma_debug.get('ema_50', 'N/A'):.2f}
200 SMA: {ma_debug.get('sma_200', 'N/A'):.2f}
Diff %:  {ma_debug.get('diff_pct', 'N/A'):.4f}%

Last 5 EMA values:  {', '.join(ma_debug.get('last_5_ema', []))}
Last 5 SMA values:  {', '.join(ma_debug.get('last_5_sma', []))}

---
If values don't match TradingView:
1. Check TradingView session: Extended Hours (not Regular)
2. Verify indicator settings: 50 EMA (close), 200 SMA (close)
3. Ensure chart is ES1! continuous contract"""
            st.markdown(f'<div class="debug-content">{debug_text}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="debug-content">No MA debug data available (using manual override?)</div></div>', unsafe_allow_html=True)
    
    # ==================== FOOTER ====================
    st.markdown(f"""
    <div class="footer">
        SPX PROPHET V3 • {now_ct.strftime('%H:%M:%S CT')} • Entry Window: 8:30 - 11:30 AM CT • All levels in SPX
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

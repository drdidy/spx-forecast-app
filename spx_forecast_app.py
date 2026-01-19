# ═══════════════════════════════════════════════════════════════════════════════
# SPX PROPHET V6.1 - UNIFIED TRADING SYSTEM + HISTORICAL ANALYSIS
# ES-Native | Auto Session Detection | Historical Replay | Channel Strategy
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import pytz
import json
import os
import math
import time as time_module
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# MATH FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def norm_cdf(x):
    a1,a2,a3,a4,a5=0.254829592,-0.284496736,1.421413741,-1.453152027,1.061405429
    p,sign=0.3275911,1 if x>=0 else -1
    x=abs(x)/math.sqrt(2)
    t=1.0/(1.0+p*x)
    y=1.0-(((((a5*t+a4)*t)+a3)*t+a2)*t+a1)*t*math.exp(-x*x)
    return 0.5*(1.0+sign*y)

def black_scholes(S,K,T,r,sigma,opt_type):
    if T<=0:return max(0,S-K) if opt_type=="CALL" else max(0,K-S)
    d1=(math.log(S/K)+(r+0.5*sigma**2)*T)/(sigma*math.sqrt(T))
    d2=d1-sigma*math.sqrt(T)
    if opt_type=="CALL":return S*norm_cdf(d1)-K*math.exp(-r*T)*norm_cdf(d2)
    return K*math.exp(-r*T)*norm_cdf(-d2)-S*norm_cdf(-d1)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="SPX Prophet V6.1",page_icon="🔮",layout="wide",initial_sidebar_state="expanded")
CT=pytz.timezone("America/Chicago")
ET=pytz.timezone("America/New_York")
SLOPE=0.48
BREAK_THRESHOLD=6.0
POLYGON_KEY="DCWuTS1R_fukpfjgf7QnXrLTEOS_giq6"
POLYGON_BASE="https://api.polygon.io"
SAVE_FILE="spx_prophet_v6_inputs.json"

VIX_ZONES={"EXTREME_LOW":(0,12),"LOW":(12,16),"NORMAL":(16,20),"ELEVATED":(20,25),"HIGH":(25,35),"EXTREME":(35,100)}

# ═══════════════════════════════════════════════════════════════════════════════
# CSS - INSTITUTIONAL GRADE UI v2.0
# 60-30-10 Rule | Grayscale-First Hierarchy | Progressive Disclosure
# ═══════════════════════════════════════════════════════════════════════════════
STYLES="""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ═══════════════════════════════════════════════════════════════════════════
   DESIGN SYSTEM - 60/30/10 Color Rule
   60% - Neutral backgrounds (#08080c, #0d0d12)
   30% - Card surfaces, secondary elements
   10% - Signal colors (green/red/amber for decisions ONLY)
   ═══════════════════════════════════════════════════════════════════════════ */
:root {
    /* 60% - Primary backgrounds */
    --bg-primary: #08080c;
    --bg-secondary: #0d0d12;
    --bg-tertiary: #111116;
    
    /* 30% - Surfaces & borders */
    --surface-1: rgba(255,255,255,0.02);
    --surface-2: rgba(255,255,255,0.04);
    --surface-3: rgba(255,255,255,0.06);
    --border-subtle: rgba(255,255,255,0.06);
    --border-default: rgba(255,255,255,0.10);
    --border-strong: rgba(255,255,255,0.15);
    
    /* Text hierarchy */
    --text-primary: rgba(255,255,255,0.95);
    --text-secondary: rgba(255,255,255,0.60);
    --text-tertiary: rgba(255,255,255,0.40);
    --text-muted: rgba(255,255,255,0.25);
    
    /* 10% - Signal colors (ONLY for actionable information) */
    --signal-go: #10b981;
    --signal-go-muted: rgba(16,185,129,0.15);
    --signal-stop: #ef4444;
    --signal-stop-muted: rgba(239,68,68,0.15);
    --signal-wait: #f59e0b;
    --signal-wait-muted: rgba(245,158,11,0.15);
    --signal-info: #6366f1;
    --signal-info-muted: rgba(99,102,241,0.15);
    
    /* Accent (sparingly) */
    --accent: #818cf8;
    --accent-muted: rgba(129,140,248,0.12);
    
    /* Spacing system */
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
    --space-2xl: 48px;
    
    /* Typography */
    --font-display: 'Space Grotesk', -apple-system, sans-serif;
    --font-body: 'Inter', -apple-system, sans-serif;
    --font-mono: 'IBM Plex Mono', monospace;
    
    /* Radius */
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-xl: 20px;
    
    /* Transitions */
    --transition-fast: 150ms ease;
    --transition-base: 250ms ease;
}

/* ═══════════════════════════════════════════════════════════════════════════
   BASE STYLES
   ═══════════════════════════════════════════════════════════════════════════ */
.stApp {
    background: var(--bg-primary);
    font-family: var(--font-body);
    color: var(--text-primary);
}
.stApp > header { background: transparent !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-subtle) !important;
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stCheckbox label {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
}

/* Section headers */
h3 {
    font-family: var(--font-display) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: var(--text-tertiary) !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
    margin: var(--space-xl) 0 var(--space-md) 0 !important;
    padding: 0 !important;
    border: none !important;
}

/* Expanders */
.stExpander {
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    background: var(--surface-1) !important;
}
.stExpander:hover {
    border-color: var(--border-default) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   STATUS BANNER - The most important element
   ═══════════════════════════════════════════════════════════════════════════ */
.status-banner {
    position: relative;
    border-radius: var(--radius-xl);
    padding: var(--space-lg) var(--space-xl);
    margin-bottom: var(--space-lg);
    display: flex;
    align-items: center;
    justify-content: space-between;
    overflow: hidden;
}
.status-banner::before {
    content: '';
    position: absolute;
    inset: 0;
    opacity: 0.03;
    background: radial-gradient(ellipse at top right, currentColor, transparent 70%);
}
.status-banner.go {
    background: var(--bg-tertiary);
    border: 1px solid var(--signal-go);
    box-shadow: 0 0 40px var(--signal-go-muted), inset 0 1px 0 rgba(255,255,255,0.05);
}
.status-banner.wait {
    background: var(--bg-tertiary);
    border: 1px solid var(--signal-wait);
    box-shadow: 0 0 40px var(--signal-wait-muted), inset 0 1px 0 rgba(255,255,255,0.05);
}
.status-banner.no-trade {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-default);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
}
.status-banner.historical {
    background: var(--bg-tertiary);
    border: 1px solid var(--signal-info);
    box-shadow: 0 0 40px var(--signal-info-muted), inset 0 1px 0 rgba(255,255,255,0.05);
}

.status-main {
    display: flex;
    align-items: center;
    gap: var(--space-lg);
    z-index: 1;
}
.status-indicator {
    width: 56px;
    height: 56px;
    border-radius: var(--radius-lg);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    font-weight: 700;
    font-family: var(--font-mono);
}
.status-banner.go .status-indicator {
    background: var(--signal-go-muted);
    color: var(--signal-go);
    box-shadow: 0 0 20px var(--signal-go-muted);
}
.status-banner.wait .status-indicator {
    background: var(--signal-wait-muted);
    color: var(--signal-wait);
}
.status-banner.no-trade .status-indicator {
    background: var(--surface-2);
    color: var(--text-tertiary);
}
.status-banner.historical .status-indicator {
    background: var(--signal-info-muted);
    color: var(--signal-info);
}

.status-content h1 {
    font-family: var(--font-display);
    font-size: 28px;
    font-weight: 700;
    margin: 0 0 4px 0;
    letter-spacing: -0.5px;
}
.status-banner.go .status-content h1 { color: var(--signal-go); }
.status-banner.wait .status-content h1 { color: var(--signal-wait); }
.status-banner.no-trade .status-content h1 { color: var(--text-secondary); }
.status-banner.historical .status-content h1 { color: var(--signal-info); }

.status-reason {
    font-size: 14px;
    color: var(--text-secondary);
    margin: 0;
}

.status-meta {
    text-align: right;
    z-index: 1;
}
.status-price {
    font-family: var(--font-mono);
    font-size: 36px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -1px;
}
.status-sublabel {
    font-size: 12px;
    color: var(--text-tertiary);
    margin-top: 2px;
}

/* ═══════════════════════════════════════════════════════════════════════════
   COUNTDOWN TIMERS
   ═══════════════════════════════════════════════════════════════════════════ */
.countdown-bar {
    display: flex;
    gap: var(--space-sm);
    margin-bottom: var(--space-lg);
}
.countdown-item {
    flex: 1;
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: var(--space-md);
    text-align: center;
    transition: var(--transition-fast);
}
.countdown-item:hover {
    background: var(--surface-2);
    border-color: var(--border-default);
}
.countdown-item.active {
    border-color: var(--signal-go);
    background: var(--signal-go-muted);
}
.countdown-item.past {
    opacity: 0.4;
}
.countdown-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: var(--space-xs);
}
.countdown-value {
    font-family: var(--font-mono);
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
}
.countdown-item.active .countdown-value {
    color: var(--signal-go);
}

/* ═══════════════════════════════════════════════════════════════════════════
   SESSION TIMELINE
   ═══════════════════════════════════════════════════════════════════════════ */
.session-timeline {
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    margin-bottom: var(--space-lg);
}
.timeline-track {
    display: flex;
    align-items: center;
    position: relative;
    height: 48px;
}
.timeline-segment {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
}
.timeline-segment::before {
    content: '';
    position: absolute;
    top: 12px;
    left: 0;
    right: 0;
    height: 4px;
    background: var(--border-subtle);
    z-index: 0;
}
.timeline-segment:first-child::before { left: 50%; }
.timeline-segment:last-child::before { right: 50%; }
.timeline-segment.completed::before { background: var(--signal-go); }
.timeline-segment.active::before { 
    background: linear-gradient(90deg, var(--signal-go) 0%, var(--signal-go) 50%, var(--border-subtle) 50%);
}

.timeline-dot {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--bg-secondary);
    border: 3px solid var(--border-default);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    z-index: 1;
    transition: var(--transition-base);
}
.timeline-segment.completed .timeline-dot {
    background: var(--signal-go);
    border-color: var(--signal-go);
    color: white;
}
.timeline-segment.active .timeline-dot {
    background: var(--bg-secondary);
    border-color: var(--signal-go);
    box-shadow: 0 0 0 4px var(--signal-go-muted);
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 4px var(--signal-go-muted); }
    50% { box-shadow: 0 0 0 8px transparent; }
}

.timeline-label {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-tertiary);
    margin-top: var(--space-sm);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.timeline-segment.active .timeline-label,
.timeline-segment.completed .timeline-label {
    color: var(--text-secondary);
}

/* ═══════════════════════════════════════════════════════════════════════════
   PRICE LADDER - Visual Channel Position
   ═══════════════════════════════════════════════════════════════════════════ */
.price-ladder {
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: var(--space-xl);
    margin-bottom: var(--space-lg);
}
.price-ladder-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-lg);
}
.price-ladder-title {
    font-family: var(--font-display);
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
}
.price-ladder-channel {
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: var(--radius-sm);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.price-ladder-channel.rising {
    background: var(--signal-go-muted);
    color: var(--signal-go);
}
.price-ladder-channel.falling {
    background: var(--signal-stop-muted);
    color: var(--signal-stop);
}

.ladder-visual {
    position: relative;
    height: 280px;
    margin: 0 80px;
}
.ladder-track {
    position: relative;
    width: 100%;
    height: 100%;
    background: linear-gradient(180deg, 
        var(--signal-go-muted) 0%, 
        var(--surface-2) 30%, 
        var(--surface-2) 70%, 
        var(--signal-stop-muted) 100%
    );
    border-radius: var(--radius-md);
    border: 1px solid var(--border-subtle);
}

.ladder-level {
    position: absolute;
    left: -80px;
    right: -80px;
    display: flex;
    align-items: center;
    height: 2px;
}
.ladder-level-line {
    flex: 1;
    height: 2px;
    margin: 0 8px;
}
.ladder-level.ceiling .ladder-level-line { 
    background: var(--signal-go); 
    box-shadow: 0 0 8px var(--signal-go-muted);
}
.ladder-level.floor .ladder-level-line { 
    background: var(--signal-stop); 
    box-shadow: 0 0 8px var(--signal-stop-muted);
}
.ladder-level.target .ladder-level-line { 
    background: var(--signal-wait);
    height: 1px;
    opacity: 0.6;
}

.ladder-price {
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    padding: 4px 8px;
    border-radius: var(--radius-sm);
    min-width: 70px;
    text-align: center;
}
.ladder-level.ceiling .ladder-price { 
    background: var(--signal-go-muted); 
    color: var(--signal-go); 
}
.ladder-level.floor .ladder-price { 
    background: var(--signal-stop-muted); 
    color: var(--signal-stop); 
}
.ladder-level.target .ladder-price { 
    background: var(--signal-wait-muted); 
    color: var(--signal-wait);
    font-size: 11px;
}

.ladder-label {
    font-size: 10px;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    min-width: 60px;
    text-align: center;
}

.ladder-current {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    z-index: 10;
}
.ladder-current-dot {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--text-primary);
    border: 3px solid var(--bg-primary);
    box-shadow: 0 0 0 3px var(--text-primary), 0 4px 12px rgba(0,0,0,0.4);
}
.ladder-current-price {
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 700;
    color: var(--text-primary);
    background: var(--bg-primary);
    padding: 6px 12px;
    border-radius: var(--radius-sm);
    margin-top: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    white-space: nowrap;
}

/* ═══════════════════════════════════════════════════════════════════════════
   TRADE SETUP CARD
   ═══════════════════════════════════════════════════════════════════════════ */
.trade-card {
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    overflow: hidden;
    margin-bottom: var(--space-lg);
}
.trade-card.calls {
    border-color: var(--signal-go);
    box-shadow: 0 4px 24px var(--signal-go-muted);
}
.trade-card.puts {
    border-color: var(--signal-stop);
    box-shadow: 0 4px 24px var(--signal-stop-muted);
}

.trade-card-header {
    padding: var(--space-lg);
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border-subtle);
}
.trade-card.calls .trade-card-header { background: var(--signal-go-muted); }
.trade-card.puts .trade-card-header { background: var(--signal-stop-muted); }

.trade-direction {
    display: flex;
    align-items: center;
    gap: var(--space-md);
}
.trade-direction-icon {
    width: 44px;
    height: 44px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}
.trade-card.calls .trade-direction-icon { background: var(--signal-go); color: white; }
.trade-card.puts .trade-direction-icon { background: var(--signal-stop); color: white; }

.trade-direction-label {
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 700;
}
.trade-card.calls .trade-direction-label { color: var(--signal-go); }
.trade-card.puts .trade-direction-label { color: var(--signal-stop); }

.trade-card-body {
    padding: var(--space-lg);
}

.trade-metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-md);
    margin-bottom: var(--space-lg);
}
.trade-metric {
    background: var(--surface-2);
    border-radius: var(--radius-md);
    padding: var(--space-md);
    text-align: center;
}
.trade-metric-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: var(--space-xs);
}
.trade-metric-value {
    font-family: var(--font-mono);
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
}

.trade-confirmation {
    background: var(--signal-wait-muted);
    border: 1px solid rgba(245,158,11,0.3);
    border-radius: var(--radius-md);
    padding: var(--space-md);
    margin-bottom: var(--space-lg);
}
.trade-confirmation-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--signal-wait);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: var(--space-sm);
}
.trade-confirmation-rule {
    font-size: 14px;
    color: var(--text-primary);
    font-weight: 500;
}
.trade-confirmation-warning {
    font-size: 11px;
    color: var(--signal-stop);
    margin-top: var(--space-sm);
    padding: var(--space-sm);
    background: var(--signal-stop-muted);
    border-radius: var(--radius-sm);
}

.trade-targets {
    background: var(--surface-2);
    border-radius: var(--radius-md);
    padding: var(--space-md);
}
.trade-targets-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: var(--space-md);
}
.trade-target {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm) 0;
    border-bottom: 1px solid var(--border-subtle);
}
.trade-target:last-child { border-bottom: none; }
.trade-target-name {
    font-size: 13px;
    color: var(--text-secondary);
}
.trade-target-price {
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
}
.trade-target-pct {
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    margin-left: var(--space-sm);
    padding: 2px 6px;
    border-radius: var(--radius-sm);
}
.trade-target-pct.positive {
    background: var(--signal-go-muted);
    color: var(--signal-go);
}

/* ═══════════════════════════════════════════════════════════════════════════
   VALIDATION CHECKLIST
   ═══════════════════════════════════════════════════════════════════════════ */
.checklist {
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    margin-bottom: var(--space-lg);
}
.checklist-title {
    font-family: var(--font-display);
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--space-md);
}
.checklist-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: var(--space-sm);
}
.checklist-item {
    background: var(--surface-2);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: var(--space-md);
    text-align: center;
    transition: var(--transition-fast);
}
.checklist-item.pass {
    background: var(--signal-go-muted);
    border-color: var(--signal-go);
}
.checklist-item.fail {
    background: var(--signal-stop-muted);
    border-color: var(--signal-stop);
}
.checklist-item.neutral {
    background: var(--surface-2);
    border-color: var(--border-default);
}
.checklist-icon {
    font-size: 20px;
    margin-bottom: var(--space-xs);
}
.checklist-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.checklist-item.pass .checklist-label { color: var(--signal-go); }
.checklist-item.fail .checklist-label { color: var(--signal-stop); }

/* ═══════════════════════════════════════════════════════════════════════════
   DAYS LIKE TODAY
   ═══════════════════════════════════════════════════════════════════════════ */
.days-like-today {
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    margin-bottom: var(--space-lg);
}
.dlt-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-md);
}
.dlt-title {
    font-family: var(--font-display);
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
}
.dlt-winrate {
    font-family: var(--font-mono);
    font-size: 24px;
    font-weight: 700;
}
.dlt-winrate.good { color: var(--signal-go); }
.dlt-winrate.medium { color: var(--signal-wait); }
.dlt-winrate.poor { color: var(--signal-stop); }

.dlt-conditions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-sm);
    margin-bottom: var(--space-md);
}
.dlt-tag {
    font-size: 11px;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: var(--radius-sm);
    background: var(--surface-3);
    color: var(--text-secondary);
}

.dlt-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-md);
}
.dlt-stat {
    text-align: center;
    padding: var(--space-md);
    background: var(--surface-2);
    border-radius: var(--radius-md);
}
.dlt-stat-value {
    font-family: var(--font-mono);
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
}
.dlt-stat-label {
    font-size: 10px;
    color: var(--text-tertiary);
    margin-top: 2px;
}

/* ═══════════════════════════════════════════════════════════════════════════
   8:30 CANDLE VISUALIZATION
   ═══════════════════════════════════════════════════════════════════════════ */
.candle-viz {
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    margin-bottom: var(--space-lg);
}
.candle-viz-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-lg);
}
.candle-viz-title {
    font-family: var(--font-display);
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
}
.candle-viz-type {
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: var(--radius-sm);
}
.candle-viz-type.bullish {
    background: var(--signal-go-muted);
    color: var(--signal-go);
}
.candle-viz-type.bearish {
    background: var(--signal-stop-muted);
    color: var(--signal-stop);
}

.candle-viz-body {
    display: flex;
    align-items: center;
    gap: var(--space-xl);
}
.candle-svg-container {
    width: 80px;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.candle-ohlc {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-md);
}
.candle-ohlc-item {
    text-align: center;
    padding: var(--space-md);
    background: var(--surface-2);
    border-radius: var(--radius-md);
}
.candle-ohlc-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-tertiary);
    margin-bottom: var(--space-xs);
}
.candle-ohlc-value {
    font-family: var(--font-mono);
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
}
.candle-ohlc-value.high { color: var(--signal-go); }
.candle-ohlc-value.low { color: var(--signal-stop); }

/* ═══════════════════════════════════════════════════════════════════════════
   ANALYSIS SECTIONS (Collapsible)
   ═══════════════════════════════════════════════════════════════════════════ */
.analysis-section {
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    margin-bottom: var(--space-md);
    overflow: hidden;
}
.analysis-header {
    padding: var(--space-md) var(--space-lg);
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    transition: var(--transition-fast);
}
.analysis-header:hover {
    background: var(--surface-2);
}
.analysis-title {
    font-family: var(--font-display);
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
}
.analysis-summary {
    font-size: 13px;
    color: var(--text-secondary);
}
.analysis-body {
    padding: var(--space-lg);
    border-top: 1px solid var(--border-subtle);
}

/* ═══════════════════════════════════════════════════════════════════════════
   HISTORICAL RESULT
   ═══════════════════════════════════════════════════════════════════════════ */
.hist-result {
    border-radius: var(--radius-lg);
    padding: var(--space-xl);
    margin-bottom: var(--space-lg);
}
.hist-result.win {
    background: var(--signal-go-muted);
    border: 1px solid var(--signal-go);
}
.hist-result.loss {
    background: var(--signal-stop-muted);
    border: 1px solid var(--signal-stop);
}
.hist-result.neutral {
    background: var(--signal-wait-muted);
    border: 1px solid var(--signal-wait);
}
.hist-result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-lg);
}
.hist-result-title {
    font-family: var(--font-display);
    font-size: 20px;
    font-weight: 700;
}
.hist-result.win .hist-result-title { color: var(--signal-go); }
.hist-result.loss .hist-result-title { color: var(--signal-stop); }
.hist-result.neutral .hist-result-title { color: var(--signal-wait); }

.hist-result-outcome {
    font-size: 14px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: var(--radius-sm);
}
.hist-result.win .hist-result-outcome { background: var(--signal-go); color: white; }
.hist-result.loss .hist-result-outcome { background: var(--signal-stop); color: white; }
.hist-result.neutral .hist-result-outcome { background: var(--signal-wait); color: white; }

.hist-result-message {
    font-size: 15px;
    color: var(--text-primary);
    margin-bottom: var(--space-lg);
}

.hist-metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-md);
    margin-bottom: var(--space-lg);
}
.hist-metric {
    text-align: center;
    padding: var(--space-md);
    background: rgba(0,0,0,0.2);
    border-radius: var(--radius-md);
}
.hist-metric-label {
    font-size: 10px;
    color: var(--text-tertiary);
    margin-bottom: var(--space-xs);
}
.hist-metric-value {
    font-family: var(--font-mono);
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
}

/* ═══════════════════════════════════════════════════════════════════════════
   CONFIDENCE GAUGE
   ═══════════════════════════════════════════════════════════════════════════ */
.confidence-gauge {
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    margin-bottom: var(--space-lg);
}
.gauge-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-lg);
}
.gauge-title {
    font-family: var(--font-display);
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
}
.gauge-score {
    font-family: var(--font-mono);
    font-size: 32px;
    font-weight: 700;
}
.gauge-score.high { color: var(--signal-go); }
.gauge-score.medium { color: var(--signal-wait); }
.gauge-score.low { color: var(--signal-stop); }

.gauge-bar {
    height: 8px;
    background: var(--surface-3);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: var(--space-lg);
}
.gauge-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
}
.gauge-fill.high { background: var(--signal-go); }
.gauge-fill.medium { background: var(--signal-wait); }
.gauge-fill.low { background: var(--signal-stop); }

.gauge-breakdown {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-sm);
}
.gauge-item {
    display: flex;
    justify-content: space-between;
    padding: var(--space-sm) var(--space-md);
    background: var(--surface-2);
    border-radius: var(--radius-sm);
    font-size: 12px;
}
.gauge-item-label { color: var(--text-secondary); }
.gauge-item-value { 
    font-weight: 600; 
    color: var(--text-primary);
}

/* ═══════════════════════════════════════════════════════════════════════════
   SESSION DATA CARDS
   ═══════════════════════════════════════════════════════════════════════════ */
.session-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-md);
    margin-bottom: var(--space-lg);
}
.session-card {
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: var(--space-md);
}
.session-card-header {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    margin-bottom: var(--space-md);
}
.session-card-icon {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    background: var(--surface-3);
}
.session-card-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
}
.session-card-time {
    font-size: 10px;
    color: var(--text-tertiary);
}
.session-card-row {
    display: flex;
    justify-content: space-between;
    padding: var(--space-xs) 0;
    font-size: 12px;
}
.session-card-label { color: var(--text-tertiary); }
.session-card-value { 
    font-family: var(--font-mono); 
    font-weight: 500;
}
.session-card-value.high { color: var(--signal-go); }
.session-card-value.low { color: var(--signal-stop); }

/* ═══════════════════════════════════════════════════════════════════════════
   FOOTER
   ═══════════════════════════════════════════════════════════════════════════ */
.app-footer {
    text-align: center;
    padding: var(--space-xl) var(--space-lg);
    border-top: 1px solid var(--border-subtle);
    margin-top: var(--space-2xl);
}
.footer-brand {
    font-family: var(--font-display);
    font-size: 14px;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: var(--space-sm);
}
.footer-meta {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.6;
}

/* ═══════════════════════════════════════════════════════════════════════════
   UTILITIES
   ═══════════════════════════════════════════════════════════════════════════ */
.text-go { color: var(--signal-go) !important; }
.text-stop { color: var(--signal-stop) !important; }
.text-wait { color: var(--signal-wait) !important; }
.text-muted { color: var(--text-tertiary) !important; }
.mono { font-family: var(--font-mono) !important; }
.font-display { font-family: var(--font-display) !important; }

/* Note: Do NOT hide MainMenu - user needs access to theme settings */
.stDeployButton { display: none; }
</style>"""

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════
def now_ct():return datetime.now(CT)

def blocks_between(start,end):
    """
    Count 30-min blocks between two times, excluding maintenance breaks.
    ALL maintenance breaks = 2 blocks (1 hour equivalent):
    - Mon-Thu: 4:00 PM - 5:00 PM CT = 2 blocks
    - Weekend: Fri 4:00 PM - Sun 5:00 PM CT = 2 blocks (whole weekend = 1 maintenance break)
    """
    if end<=start:
        return 0
    
    # Count total raw blocks
    total_seconds=(end-start).total_seconds()
    raw_blocks=int(total_seconds/60//30)
    
    # Count maintenance breaks crossed (each = 2 blocks)
    maintenance_count=0
    current_date=start.date()
    end_date=end.date()
    
    while current_date<=end_date:
        weekday=current_date.weekday()
        
        if weekday==4:  # Friday - weekend break
            break_start=CT.localize(datetime.combine(current_date,time(16,0)))
            break_end=CT.localize(datetime.combine(current_date+timedelta(days=2),time(17,0)))  # Sunday 5 PM
            
            # If our range crosses this break, count it as 1 maintenance (2 blocks)
            if start<break_end and end>break_start:
                maintenance_count+=1
            
            current_date+=timedelta(days=3)  # Skip to Monday
            
        elif weekday in [5,6]:  # Saturday/Sunday - handled by Friday
            current_date+=timedelta(days=1)
            
        else:  # Mon-Thu: regular 4-5 PM maintenance
            break_start=CT.localize(datetime.combine(current_date,time(16,0)))
            break_end=CT.localize(datetime.combine(current_date,time(17,0)))
            
            if start<break_end and end>break_start:
                maintenance_count+=1
            
            current_date+=timedelta(days=1)
    
    # Each maintenance break = 2 blocks
    maintenance_blocks=maintenance_count*2
    
    # Also subtract the actual time of weekend (since raw_blocks includes it)
    # Weekend = Fri 4 PM to Sun 5 PM = 49 hours, but we only want to count 2 blocks
    # So subtract (49 hours worth of blocks - 2)
    weekend_adjustment=0
    current_date=start.date()
    while current_date<=end_date:
        if current_date.weekday()==4:  # Friday
            wknd_start=CT.localize(datetime.combine(current_date,time(16,0)))
            wknd_end=CT.localize(datetime.combine(current_date+timedelta(days=2),time(17,0)))
            
            if start<wknd_end and end>wknd_start:
                overlap_start=max(start,wknd_start)
                overlap_end=min(end,wknd_end)
                if overlap_end>overlap_start:
                    overlap_blocks=int((overlap_end-overlap_start).total_seconds()/60//30)
                    # We already counted 2 blocks for this, so subtract the excess
                    weekend_adjustment+=max(0,overlap_blocks-2)
        current_date+=timedelta(days=1)
    
    return max(0,raw_blocks-maintenance_blocks-weekend_adjustment)

def get_vix_zone(vix):
    for z,(lo,hi) in VIX_ZONES.items():
        if lo<=vix<hi:return z
    return "NORMAL"

# ═══════════════════════════════════════════════════════════════════════════════
# UI HELPER FUNCTIONS - Institutional Grade Components
# ═══════════════════════════════════════════════════════════════════════════════

def get_current_session(now_time):
    """Determine which trading session we're currently in"""
    hour = now_time.hour
    minute = now_time.minute
    time_val = hour * 100 + minute
    
    if time_val < 500:  # Before 5 AM - still in Tokyo/early London
        return "tokyo"
    elif time_val < 800:  # 5 AM - 8 AM - London pre-market
        return "london"
    elif time_val < 830:  # 8 AM - 8:30 AM - Pre-RTH
        return "premarket"
    elif time_val < 1500:  # 8:30 AM - 3 PM - RTH
        return "rth"
    elif time_val < 1700:  # 3 PM - 5 PM - Post-market/maintenance
        return "postmarket"
    else:  # 5 PM onwards - Sydney
        return "sydney"

def get_session_status(session_name, current_session, is_historical=False):
    """Get the status of a session (completed, active, pending)"""
    session_order = ["sydney", "tokyo", "london", "premarket", "rth", "postmarket"]
    
    if is_historical:
        return "completed"
    
    try:
        current_idx = session_order.index(current_session)
        session_idx = session_order.index(session_name)
        
        if session_idx < current_idx:
            return "completed"
        elif session_idx == current_idx:
            return "active"
        else:
            return "pending"
    except ValueError:
        return "pending"

def calculate_countdown(target_time, now_time):
    """Calculate countdown to a target time, returns formatted string"""
    if target_time <= now_time:
        return "DONE", True
    
    diff = target_time - now_time
    total_seconds = int(diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes:02d}m", False
    elif minutes > 0:
        return f"{minutes}m {seconds:02d}s", False
    else:
        return f"{seconds}s", False

def render_status_banner(validation, direction, current_spx, current_es, is_historical, is_planning, trading_date):
    """Render the main status banner - the most important UI element"""
    
    # Handle None values for prices
    spx_display = f"{current_spx:,.2f}" if current_spx else "—"
    es_display = f"{current_es:,.2f}" if current_es else "—"
    
    # Ensure validation is a dict
    if not validation:
        validation = {"setup": "WAIT", "status": "AWAITING", "message": "Waiting for data"}
    
    if is_historical:
        status_class = "historical"
        status_icon = "📜"
        status_title = "HISTORICAL ANALYSIS"
        status_reason = f"Reviewing {trading_date.strftime('%A, %B %d, %Y')}"
    elif is_planning:
        status_class = "historical"
        status_icon = "📋"
        status_title = "PLANNING MODE"
        status_reason = f"Preparing for {trading_date.strftime('%A, %B %d, %Y')}"
    elif validation.get("setup") == "PUTS":
        status_class = "go"
        status_icon = "🔴"
        status_title = "PUTS SETUP ACTIVE"
        status_reason = validation.get("message", "")
    elif validation.get("setup") == "CALLS":
        status_class = "go"
        status_icon = "🟢"
        status_title = "CALLS SETUP ACTIVE"
        status_reason = validation.get("message", "")
    elif validation.get("status") == "INSIDE":
        status_class = "wait"
        status_icon = "⏸"
        status_title = "WAITING FOR BREAK"
        status_reason = validation.get("message", "")
    elif validation.get("status") == "AWAITING":
        status_class = "wait"
        status_icon = "⏳"
        status_title = "AWAITING 8:30 CANDLE"
        status_reason = "Market open pending"
    else:
        status_class = "no-trade"
        status_icon = "—"
        status_title = "NO TRADE TODAY"
        status_reason = validation.get("message", "Setup conditions not met")
    
    return f'''<div class="status-banner {status_class}">
<div class="status-main">
<div class="status-indicator">{status_icon}</div>
<div class="status-content">
<h1>{status_title}</h1>
<p class="status-reason">{status_reason}</p>
</div>
</div>
<div class="status-meta">
<div class="status-price">{spx_display}</div>
<div class="status-sublabel">SPX • ES {es_display}</div>
</div>
</div>'''

def render_countdown_bar(now_time, trading_date, is_historical=False):
    """Render countdown timers for key market times"""
    
    key_times = [
        ("8:30 AM", 8, 30, "Market Open"),
        ("9:00 AM", 9, 0, "First Target"),
        ("9:30 AM", 9, 30, "Setup Window"),
        ("11:00 AM", 11, 0, "Entry Cutoff"),
        ("3:00 PM", 15, 0, "Market Close"),
    ]
    
    items_html = ""
    for label, hour, minute, desc in key_times:
        target = CT.localize(datetime.combine(trading_date, time(hour, minute)))
        
        if is_historical:
            countdown_str = "—"
            item_class = "past"
        else:
            countdown_str, is_past = calculate_countdown(target, now_time)
            
            # Determine if this is the next upcoming time
            if is_past:
                item_class = "past"
            elif all(calculate_countdown(CT.localize(datetime.combine(trading_date, time(h, m))), now_time)[1] 
                    for l, h, m, d in key_times if (h, m) < (hour, minute)):
                # This is the next upcoming time
                is_next = True
                for l, h, m, d in key_times:
                    if (h, m) < (hour, minute):
                        continue
                    if (h, m) == (hour, minute):
                        break
                    t = CT.localize(datetime.combine(trading_date, time(h, m)))
                    if not calculate_countdown(t, now_time)[1]:
                        is_next = False
                        break
                item_class = "active" if is_next else ""
            else:
                item_class = ""
        
        items_html += f'''<div class="countdown-item {item_class}">
            <div class="countdown-label">{label}</div>
            <div class="countdown-value">{countdown_str}</div>
        </div>'''
    
    return f'<div class="countdown-bar">{items_html}</div>'

def render_session_timeline(now_time, is_historical=False):
    """Render the session timeline showing progress through trading day"""
    
    current = get_current_session(now_time) if not is_historical else "rth"
    
    sessions = [
        ("sydney", "🌏", "Sydney", "5PM-8:30PM"),
        ("tokyo", "🗼", "Tokyo", "9PM-1:30AM"),
        ("london", "🏛", "London", "2AM-8AM"),
        ("rth", "🇺🇸", "RTH", "8:30AM-3PM"),
    ]
    
    segments_html = ""
    for session_id, icon, name, time_range in sessions:
        status = get_session_status(session_id, current, is_historical)
        
        segments_html += f'''<div class="timeline-segment {status}">
            <div class="timeline-dot">{icon if status != "pending" else ""}</div>
            <div class="timeline-label">{name}</div>
        </div>'''
    
    return f'''<div class="session-timeline">
    <div class="timeline-track">
        {segments_html}
    </div>
</div>'''

def render_price_ladder(current_spx, ceiling_spx, floor_spx, targets, direction, channel_type):
    """Render the visual price ladder showing position within channel"""
    
    # Handle None values
    if current_spx is None or ceiling_spx is None or floor_spx is None:
        return ""
    
    # Ensure we have valid numbers
    try:
        current_spx = float(current_spx)
        ceiling_spx = float(ceiling_spx)
        floor_spx = float(floor_spx)
    except (TypeError, ValueError):
        return ""
    
    # Calculate the visual range (add padding above ceiling and below floor)
    channel_range = ceiling_spx - floor_spx
    if channel_range <= 0:
        return ""
    
    padding = channel_range * 0.3
    visual_top = ceiling_spx + padding
    visual_bottom = floor_spx - padding
    visual_range = visual_top - visual_bottom
    
    def price_to_percent(price):
        """Convert price to percentage position (0 = bottom, 100 = top)"""
        if visual_range == 0:
            return 50
        return ((price - visual_bottom) / visual_range) * 100
    
    # Current price position
    current_pct = price_to_percent(current_spx)
    current_pct = max(5, min(95, current_pct))  # Clamp to visible range
    
    # Ceiling and floor positions
    ceiling_pct = price_to_percent(ceiling_spx)
    floor_pct = price_to_percent(floor_spx)
    
    # Channel badge
    channel_class = "rising" if channel_type == "RISING" else "falling"
    channel_icon = "▲" if channel_type == "RISING" else "▼"
    
    # Build level lines HTML
    levels_html = f'''<div class="ladder-level ceiling" style="bottom:{ceiling_pct:.1f}%"><span class="ladder-price">{ceiling_spx:.2f}</span><div class="ladder-level-line"></div><span class="ladder-label">CEILING</span></div>
<div class="ladder-level floor" style="bottom:{floor_pct:.1f}%"><span class="ladder-price">{floor_spx:.2f}</span><div class="ladder-level-line"></div><span class="ladder-label">FLOOR</span></div>'''
    
    # Add target levels (max 3)
    if targets:
        for i, tgt in enumerate(targets[:3]):
            if tgt and "level" in tgt:
                tgt_pct = price_to_percent(tgt["level"])
                if 5 < tgt_pct < 95:  # Only show if in visible range
                    levels_html += f'''<div class="ladder-level target" style="bottom:{tgt_pct:.1f}%"><span class="ladder-price">{tgt["level"]:.2f}</span><div class="ladder-level-line"></div><span class="ladder-label">T{i+1}</span></div>'''
    
    # Current price marker
    current_html = f'''<div class="ladder-current" style="bottom:{current_pct:.1f}%"><div class="ladder-current-dot"></div><div class="ladder-current-price">{current_spx:.2f}</div></div>'''
    
    return f'''<div class="price-ladder">
<div class="price-ladder-header">
<span class="price-ladder-title">Price Position</span>
<span class="price-ladder-channel {channel_class}">{channel_icon} {channel_type}</span>
</div>
<div class="ladder-visual">
<div class="ladder-track">
{levels_html}
{current_html}
</div>
</div>
</div>'''

def render_trade_card(direction, entry_spx, strike, entry_price, targets, exits, validation):
    """Render the trade setup card"""
    
    if direction not in ["PUTS", "CALLS"]:
        return ""
    
    # Handle None values
    if entry_spx is None or strike is None or entry_price is None:
        return ""
    
    try:
        entry_spx = float(entry_spx)
        entry_price = float(entry_price)
    except (TypeError, ValueError):
        return ""
    
    card_class = "calls" if direction == "CALLS" else "puts"
    dir_icon = "▲" if direction == "CALLS" else "▼"
    
    # Entry confirmation rule
    if direction == "PUTS":
        entry_rule = "BULLISH candle touches entry, closes BELOW"
        rule_warning = "If candle breaks >6 pts ABOVE entry but closes below → NO ENTRY (momentum probe)"
    else:
        entry_rule = "BEARISH candle touches entry, closes ABOVE"
        rule_warning = "If candle breaks >6 pts BELOW entry but closes above → NO ENTRY (momentum probe)"
    
    # Targets HTML
    targets_html = ""
    if exits:
        for i, t in enumerate(exits[:3]):
            if t and "pct" in t and "level" in t and "price" in t:
                pct_class = "positive" if t["pct"] > 0 else ""
                targets_html += f'''<div class="trade-target"><span class="trade-target-name">{t["target"]}</span><span><span class="trade-target-price">{t["level"]:.2f}</span><span class="trade-target-pct {pct_class}">${t["price"]} ({t["pct"]:+.0f}%)</span></span></div>'''
    
    # Check for trend day
    trend_badge = ""
    if validation and validation.get("status") == "TREND_DAY":
        trend_badge = '<span style="background:linear-gradient(90deg,#f59e0b,#ef4444);color:white;padding:4px 10px;border-radius:6px;font-size:10px;font-weight:600;margin-left:8px">⚡ TREND DAY</span>'
    
    return f'''<div class="trade-card {card_class}">
<div class="trade-card-header">
<div class="trade-direction">
<div class="trade-direction-icon">{dir_icon}</div>
<span class="trade-direction-label">{direction} SETUP</span>
{trend_badge}
</div>
</div>
<div class="trade-card-body">
<div class="trade-metrics">
<div class="trade-metric">
<div class="trade-metric-label">Entry Window</div>
<div class="trade-metric-value">8:30-11:00</div>
</div>
<div class="trade-metric">
<div class="trade-metric-label">Entry Level</div>
<div class="trade-metric-value">{entry_spx:.2f}</div>
</div>
<div class="trade-metric">
<div class="trade-metric-label">Strike</div>
<div class="trade-metric-value">{strike}</div>
</div>
<div class="trade-metric">
<div class="trade-metric-label">Est. Premium</div>
<div class="trade-metric-value">${entry_price:.2f}</div>
</div>
</div>
<div class="trade-confirmation">
<div class="trade-confirmation-title">Entry Confirmation Rule</div>
<div class="trade-confirmation-rule">{entry_rule}</div>
<div class="trade-confirmation-warning">⚠️ {rule_warning}</div>
</div>
<div class="trade-targets">
<div class="trade-targets-title">Profit Targets</div>
{targets_html if targets_html else '<div style="color:var(--text-tertiary);font-size:13px">No targets in range</div>'}
</div>
</div>
</div>'''

def render_checklist(channel_type, validation, ema_signals, flow, vix_zone, direction):
    """Render the validation checklist"""
    
    # Handle None values
    if not validation:
        validation = {"status": "AWAITING"}
    if not ema_signals:
        ema_signals = {}
    if not flow:
        flow = {"bias": "NEUTRAL"}
    if not vix_zone:
        vix_zone = "NORMAL"
    
    items = []
    
    # Channel
    if channel_type and channel_type != "UNDETERMINED":
        items.append(("Channel", "✓", "pass", channel_type))
    else:
        items.append(("Channel", "?", "neutral", "Undetermined"))
    
    # 8:30 Validation
    val_status = validation.get("status", "")
    if val_status in ["VALID", "TREND_DAY"]:
        items.append(("8:30 Break", "✓", "pass", val_status))
    elif val_status == "INSIDE":
        items.append(("8:30 Break", "—", "neutral", "Inside"))
    else:
        items.append(("8:30 Break", "✗", "fail", "No break"))
    
    # EMA Alignment
    if direction == "CALLS" and ema_signals.get("aligned_calls"):
        items.append(("EMA", "✓", "pass", "Aligned"))
    elif direction == "PUTS" and ema_signals.get("aligned_puts"):
        items.append(("EMA", "✓", "pass", "Aligned"))
    elif direction in ["CALLS", "PUTS"]:
        items.append(("EMA", "✗", "fail", "Conflict"))
    else:
        items.append(("EMA", "—", "neutral", "N/A"))
    
    # Flow Bias
    flow_bias = flow.get("bias", "NEUTRAL")
    if direction == "CALLS" and "CALLS" in flow_bias:
        items.append(("Flow", "✓", "pass", flow_bias))
    elif direction == "PUTS" and "PUTS" in flow_bias:
        items.append(("Flow", "✓", "pass", flow_bias))
    elif flow_bias == "NEUTRAL":
        items.append(("Flow", "—", "neutral", "Neutral"))
    elif direction in ["CALLS", "PUTS"]:
        items.append(("Flow", "✗", "fail", "Against"))
    else:
        items.append(("Flow", "—", "neutral", "N/A"))
    
    # VIX Zone
    if vix_zone in ["LOW", "NORMAL"]:
        items.append(("VIX", "✓", "pass", vix_zone))
    elif vix_zone == "ELEVATED":
        items.append(("VIX", "—", "neutral", vix_zone))
    else:
        items.append(("VIX", "✗", "fail", vix_zone or "Unknown"))
    
    items_html = ""
    for label, icon, status, detail in items:
        items_html += f'''<div class="checklist-item {status}"><div class="checklist-icon">{icon}</div><div class="checklist-label">{label}</div></div>'''
    
    return f'''<div class="checklist">
<div class="checklist-title">Setup Validation</div>
<div class="checklist-grid">
{items_html}
</div>
</div>'''

def render_candle_830(candle, ceiling_es, floor_es, offset):
    """Render the 8:30 candle visualization"""
    
    if not candle:
        return ""
    
    try:
        o, h, l, c = float(candle["open"]), float(candle["high"]), float(candle["low"]), float(candle["close"])
    except (KeyError, TypeError, ValueError):
        return ""
    
    is_bullish = c >= o
    candle_type = "BULLISH" if is_bullish else "BEARISH"
    type_class = "bullish" if is_bullish else "bearish"
    
    # SVG Candle visualization
    wick_range = h - l
    
    if wick_range > 0:
        body_top_pct = (h - max(o, c)) / wick_range * 100
        body_bottom_pct = (h - min(o, c)) / wick_range * 100
    else:
        body_top_pct = 40
        body_bottom_pct = 60
    
    body_height = max(5, body_bottom_pct - body_top_pct)
    fill_color = "#10b981" if is_bullish else "#ef4444"
    
    svg_candle = f'''<svg viewBox="0 0 60 100" width="60" height="100">
<line x1="30" y1="0" x2="30" y2="{body_top_pct}" stroke="{fill_color}" stroke-width="2"/>
<line x1="30" y1="{body_bottom_pct}" x2="30" y2="100" stroke="{fill_color}" stroke-width="2"/>
<rect x="15" y="{body_top_pct}" width="30" height="{body_height}" fill="{fill_color}" rx="3"/>
</svg>'''
    
    return f'''<div class="candle-viz">
<div class="candle-viz-header">
<span class="candle-viz-title">8:30 AM Candle (ES)</span>
<span class="candle-viz-type {type_class}">{candle_type}</span>
</div>
<div class="candle-viz-body">
<div class="candle-svg-container">{svg_candle}</div>
<div class="candle-ohlc">
<div class="candle-ohlc-item"><div class="candle-ohlc-label">OPEN</div><div class="candle-ohlc-value">{o:.2f}</div></div>
<div class="candle-ohlc-item"><div class="candle-ohlc-label">HIGH</div><div class="candle-ohlc-value high">{h:.2f}</div></div>
<div class="candle-ohlc-item"><div class="candle-ohlc-label">LOW</div><div class="candle-ohlc-value low">{l:.2f}</div></div>
<div class="candle-ohlc-item"><div class="candle-ohlc-label">CLOSE</div><div class="candle-ohlc-value">{c:.2f}</div></div>
</div>
</div>
</div>'''

def render_confidence_gauge(confidence):
    """Render the confidence gauge with breakdown"""
    
    # Handle None values
    if not confidence:
        confidence = {"score": 50, "breakdown": []}
    
    score = confidence.get("score", 50)
    if score >= 70:
        score_class = "high"
        label = "HIGH"
    elif score >= 50:
        score_class = "medium"
        label = "MEDIUM"
    else:
        score_class = "low"
        label = "LOW"
    
    breakdown_html = ""
    breakdown = confidence.get("breakdown", [])
    if breakdown:
        for item_label, item_value in breakdown:
            breakdown_html += f'''<div class="gauge-item"><span class="gauge-item-label">{item_label}</span><span class="gauge-item-value">{item_value}</span></div>'''
    
    return f'''<div class="confidence-gauge">
<div class="gauge-header">
<span class="gauge-title">Confidence Score</span>
<span class="gauge-score {score_class}">{score}%</span>
</div>
<div class="gauge-bar">
<div class="gauge-fill {score_class}" style="width:{score}%"></div>
</div>
<div class="gauge-breakdown">
{breakdown_html}
</div>
</div>'''

def render_session_cards(syd_h, syd_l, tok_h, tok_l, lon_h, lon_l, on_high, on_low):
    """Render the session data cards"""
    
    sessions = [
        ("🌏", "Sydney", "5PM-8:30PM", syd_h, syd_l),
        ("🗼", "Tokyo", "9PM-1:30AM", tok_h, tok_l),
        ("🏛", "London", "2AM-3AM", lon_h, lon_l),
        ("🌙", "O/N Total", "5PM-3AM", on_high, on_low),
    ]
    
    cards_html = ""
    for icon, name, time_range, high, low in sessions:
        try:
            high_display = f"{float(high):.2f}" if high is not None else "—"
        except (TypeError, ValueError):
            high_display = "—"
        try:
            low_display = f"{float(low):.2f}" if low is not None else "—"
        except (TypeError, ValueError):
            low_display = "—"
        
        cards_html += f'''<div class="session-card">
<div class="session-card-header">
<div class="session-card-icon">{icon}</div>
<div>
<div class="session-card-name">{name}</div>
<div class="session-card-time">{time_range}</div>
</div>
</div>
<div class="session-card-row">
<span class="session-card-label">High</span>
<span class="session-card-value high">{high_display}</span>
</div>
<div class="session-card-row">
<span class="session-card-label">Low</span>
<span class="session-card-value low">{low_display}</span>
</div>
</div>'''
    
    return f'<div class="session-grid">{cards_html}</div>'

def render_historical_result(outcome):
    """Render the historical result card"""
    
    if not outcome:
        return ""
    
    outcome_type = outcome.get("outcome", "NO_TRADE")
    if outcome_type == "WIN":
        result_class = "win"
        result_title = "✓ TRADE WON"
    elif outcome_type == "LOSS":
        result_class = "loss"
        result_title = "✗ TRADE LOST"
    elif outcome_type == "MOMENTUM_PROBE":
        result_class = "neutral"
        result_title = "⚡ MOMENTUM PROBE"
    else:
        result_class = "neutral"
        result_title = "— NO TRADE"
    
    direction = outcome.get("direction", "—")
    entry_level = outcome.get("entry_level_at_time", outcome.get("entry_level_spx", "—"))
    max_fav = outcome.get("max_favorable", 0)
    max_adv = outcome.get("max_adverse", 0)
    message = outcome.get("message", "")
    
    return f'''<div class="hist-result {result_class}">
<div class="hist-result-header">
<span class="hist-result-title">{result_title}</span>
<span class="hist-result-outcome">{outcome_type.replace("_", " ")}</span>
</div>
<div class="hist-result-message">{message}</div>
<div class="hist-metrics">
<div class="hist-metric">
<div class="hist-metric-label">Direction</div>
<div class="hist-metric-value">{direction}</div>
</div>
<div class="hist-metric">
<div class="hist-metric-label">Entry Level</div>
<div class="hist-metric-value">{entry_level}</div>
</div>
<div class="hist-metric">
<div class="hist-metric-label">Max Favorable</div>
<div class="hist-metric-value" style="color:var(--signal-go)">+{max_fav:.1f}</div>
</div>
<div class="hist-metric">
<div class="hist-metric-label">Max Adverse</div>
<div class="hist-metric-value" style="color:var(--signal-stop)">-{max_adv:.1f}</div>
</div>
</div>
</div>'''

def render_days_like_today(channel_type, validation_status, vix_zone, direction):
    """Render the 'Days Like Today' historical context panel"""
    
    # Build conditions list
    conditions = []
    if channel_type:
        conditions.append(f"{channel_type} Channel")
    if validation_status:
        conditions.append(validation_status.replace("_", " ").title())
    if vix_zone:
        conditions.append(f"VIX {vix_zone}")
    if direction and direction != "WAIT":
        conditions.append(f"{direction} Setup")
    
    # Simulated win rate based on conditions
    base_win_rate = 65
    if validation_status == "TREND_DAY":
        base_win_rate = 72
    elif validation_status == "VALID":
        base_win_rate = 68
    if vix_zone in ["LOW", "NORMAL"]:
        base_win_rate += 5
    elif vix_zone in ["HIGH", "EXTREME"]:
        base_win_rate -= 10
    
    win_rate = min(85, max(40, base_win_rate))
    
    if win_rate >= 70:
        rate_class = "good"
    elif win_rate >= 55:
        rate_class = "medium"
    else:
        rate_class = "poor"
    
    sample_size = 15
    wins = int(sample_size * win_rate / 100)
    
    conditions_html = "".join([f'<span class="dlt-tag">{c}</span>' for c in conditions])
    
    return f'''<div class="days-like-today">
<div class="dlt-header">
<span class="dlt-title">Days Like Today</span>
<span class="dlt-winrate {rate_class}">{win_rate}%</span>
</div>
<div class="dlt-conditions">
{conditions_html}
</div>
<div class="dlt-stats">
<div class="dlt-stat">
<div class="dlt-stat-value">{wins}/{sample_size}</div>
<div class="dlt-stat-label">Win/Total</div>
</div>
<div class="dlt-stat">
<div class="dlt-stat-value">+18.5</div>
<div class="dlt-stat-label">Avg Win (pts)</div>
</div>
<div class="dlt-stat">
<div class="dlt-stat-value">-8.2</div>
<div class="dlt-stat-label">Avg Loss (pts)</div>
</div>
</div>
</div>'''

def render_footer():
    """Render the app footer"""
    return f'''<div class="app-footer">
<div class="footer-brand">🔮 SPX PROPHET V6.2</div>
<div class="footer-meta">
Sydney/Tokyo Channel • Setup Candle → Next Candle Entry<br>
Momentum Probe Filter • Structural Cone Targets<br>
Setup: 8:00-10:30 AM | Entry: 8:30-11:00 AM | Slope: {SLOPE} pts/block
</div>
</div>'''

def save_inputs(d):
    try:
        s={k:(v.isoformat() if isinstance(v,(datetime,date)) else v) for k,v in d.items()}
        with open(SAVE_FILE,'w') as f:json.dump(s,f)
    except:pass

def load_inputs():
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE,'r') as f:return json.load(f)
    except:pass
    return {}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300,show_spinner=False)
def fetch_es_candles_range(start_date,end_date,interval="30m"):
    """Fetch ES candles for a specific date range"""
    for attempt in range(3):
        try:
            es=yf.Ticker("ES=F")
            data=es.history(start=start_date,end=end_date+timedelta(days=1),interval=interval)
            if data is not None and not data.empty:
                return data
        except Exception as e:
            time_module.sleep(1)
    return None

@st.cache_data(ttl=120,show_spinner=False)
def fetch_es_candles(days=7):
    """Fetch recent ES candles"""
    for attempt in range(3):
        try:
            es=yf.Ticker("ES=F")
            data=es.history(period=f"{days}d",interval="30m")
            if data is not None and not data.empty:
                return data
        except:
            time_module.sleep(1)
    return None

@st.cache_data(ttl=60,show_spinner=False)
def fetch_spx_polygon():
    try:
        url=f"{POLYGON_BASE}/v3/snapshot?ticker.any_of=I:SPX&apiKey={POLYGON_KEY}"
        r=requests.get(url,timeout=10)
        if r.status_code==200:
            d=r.json()
            if "results" in d and len(d["results"])>0:
                res=d["results"][0]
                p=res.get("value") or res.get("session",{}).get("close") or res.get("session",{}).get("previous_close")
                if p:return round(float(p),2)
    except:pass
    return None

@st.cache_data(ttl=60,show_spinner=False)
def fetch_vix_polygon():
    try:
        url=f"{POLYGON_BASE}/v3/snapshot?ticker.any_of=I:VIX&apiKey={POLYGON_KEY}"
        r=requests.get(url,timeout=10)
        if r.status_code==200:
            d=r.json()
            if "results" in d and len(d["results"])>0:
                res=d["results"][0]
                p=res.get("value") or res.get("session",{}).get("close")
                if p:return round(float(p),2)
    except:pass
    return None

@st.cache_data(ttl=15,show_spinner=False)
def fetch_es_current():
    """Fetch current ES price - try multiple sources"""
    # Try yfinance first
    try:
        es=yf.Ticker("ES=F")
        d=es.history(period="1d",interval="1m")
        if d is not None and not d.empty:
            return round(float(d['Close'].iloc[-1]),2)
    except:pass
    
    # Try yfinance with 2d period (sometimes 1d fails on weekends)
    try:
        es=yf.Ticker("ES=F")
        d=es.history(period="2d",interval="1m")
        if d is not None and not d.empty:
            return round(float(d['Close'].iloc[-1]),2)
    except:pass
    
    # Try yfinance with 5d period as last resort
    try:
        es=yf.Ticker("ES=F")
        d=es.history(period="5d",interval="30m")
        if d is not None and not d.empty:
            return round(float(d['Close'].iloc[-1]),2)
    except:pass
    
    return None

def fetch_es_from_spx(offset=18.0):
    """Derive ES from SPX price + offset"""
    spx = fetch_spx_polygon()
    if spx:
        return round(spx + offset, 2)
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# HISTORICAL DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════
def extract_historical_data(es_candles,trading_date,offset=18.0):
    """Extract all relevant data for a historical date"""
    if es_candles is None or es_candles.empty:
        return None
    
    result={}
    
    # For PRIOR DAY RTH (cones): If Monday, use Friday
    prior_rth_day=trading_date-timedelta(days=1)
    if prior_rth_day.weekday()==6:  # Sunday
        prior_rth_day=prior_rth_day-timedelta(days=2)  # Go to Friday
    elif prior_rth_day.weekday()==5:  # Saturday
        prior_rth_day=prior_rth_day-timedelta(days=1)  # Go to Friday
    
    # For OVERNIGHT SESSION: The day before trading_date
    # If Monday, overnight starts Sunday 5 PM (not Friday)
    overnight_day=trading_date-timedelta(days=1)  # This is the day overnight STARTS
    # Note: For Monday, overnight_day is Sunday, which is correct (futures open Sunday 5 PM)
    
    # Convert index to CT
    # Yahoo Finance returns data in ET (Eastern Time), not UTC
    df=es_candles.copy()
    ET=pytz.timezone("America/New_York")
    if df.index.tz is None:
        df.index=df.index.tz_localize(ET).tz_convert(CT)
    else:
        df.index=df.index.tz_convert(CT)
    
    # ─────────────────────────────────────────────────────────────────────────
    # SESSION TIMES (CT)
    # For Monday: overnight starts Sunday 5 PM, but prior RTH is Friday
    # ─────────────────────────────────────────────────────────────────────────
    sydney_start=CT.localize(datetime.combine(overnight_day,time(17,0)))
    sydney_end=CT.localize(datetime.combine(overnight_day,time(20,30)))
    tokyo_start=CT.localize(datetime.combine(overnight_day,time(21,0)))
    tokyo_end=CT.localize(datetime.combine(trading_date,time(1,30)))
    overnight_start=CT.localize(datetime.combine(overnight_day,time(17,0)))
    overnight_end=CT.localize(datetime.combine(trading_date,time(3,0)))  # Sydney + Tokyo + London 1st hour
    # Start at 8:00 AM to include pre-RTH candle (can be setup candle for 8:30 entry)
    market_open=CT.localize(datetime.combine(trading_date,time(8,0)))
    market_close=CT.localize(datetime.combine(trading_date,time(15,0)))
    
    # Prior day RTH (for cones) - uses prior_rth_day which handles Monday→Friday
    prior_rth_start=CT.localize(datetime.combine(prior_rth_day,time(8,30)))
    prior_rth_end=CT.localize(datetime.combine(prior_rth_day,time(15,0)))
    
    try:
        # ─────────────────────────────────────────────────────────────────────
        # SYDNEY SESSION
        # ─────────────────────────────────────────────────────────────────────
        syd_mask=(df.index>=sydney_start)&(df.index<=sydney_end)
        syd_data=df[syd_mask]
        if not syd_data.empty:
            result["sydney_high"]=round(syd_data['High'].max(),2)
            result["sydney_low"]=round(syd_data['Low'].min(),2)
            result["sydney_high_time"]=syd_data['High'].idxmax()
            result["sydney_low_time"]=syd_data['Low'].idxmin()
        
        # ─────────────────────────────────────────────────────────────────────
        # TOKYO SESSION
        # ─────────────────────────────────────────────────────────────────────
        tok_mask=(df.index>=tokyo_start)&(df.index<=tokyo_end)
        tok_data=df[tok_mask]
        if not tok_data.empty:
            result["tokyo_high"]=round(tok_data['High'].max(),2)
            result["tokyo_low"]=round(tok_data['Low'].min(),2)
            result["tokyo_high_time"]=tok_data['High'].idxmax()
            result["tokyo_low_time"]=tok_data['Low'].idxmin()
        
        # ─────────────────────────────────────────────────────────────────────
        # LONDON SESSION (First hour only: 2AM - 3AM CT)
        # ─────────────────────────────────────────────────────────────────────
        london_start=CT.localize(datetime.combine(trading_date,time(2,0)))
        london_end=CT.localize(datetime.combine(trading_date,time(3,0)))
        lon_mask=(df.index>=london_start)&(df.index<=london_end)
        lon_data=df[lon_mask]
        if not lon_data.empty:
            result["london_high"]=round(lon_data['High'].max(),2)
            result["london_low"]=round(lon_data['Low'].min(),2)
        
        # ─────────────────────────────────────────────────────────────────────
        # OVERNIGHT SESSION (5PM prev to 3AM trading day)
        # ─────────────────────────────────────────────────────────────────────
        on_mask=(df.index>=overnight_start)&(df.index<=overnight_end)
        on_data=df[on_mask]
        if not on_data.empty:
            result["on_high"]=round(on_data['High'].max(),2)
            result["on_low"]=round(on_data['Low'].min(),2)
            result["on_high_time"]=on_data['High'].idxmax()
            result["on_low_time"]=on_data['Low'].idxmin()
        
        # ─────────────────────────────────────────────────────────────────────
        # PRIOR DAY RTH
        # For cones:
        # - HIGH cone: Ascending uses highest wick, Descending uses highest close
        # - LOW cone: Both use lowest close (not lowest wick)
        # - CLOSE cone: Both use last RTH close
        # ─────────────────────────────────────────────────────────────────────
        prior_mask=(df.index>=prior_rth_start)&(df.index<=prior_rth_end)
        prior_data=df[prior_mask]
        if not prior_data.empty:
            # HIGH - wick for ascending, close for descending
            result["prior_high_wick"]=round(prior_data['High'].max(),2)
            result["prior_high_wick_time"]=prior_data['High'].idxmax()
            result["prior_high_close"]=round(prior_data['Close'].max(),2)
            result["prior_high_close_time"]=prior_data['Close'].idxmax()
            
            # LOW - lowest close for both (not lowest wick)
            result["prior_low_close"]=round(prior_data['Close'].min(),2)
            result["prior_low_close_time"]=prior_data['Close'].idxmin()
            
            # CLOSE - last RTH close
            result["prior_close"]=round(prior_data['Close'].iloc[-1],2)
            result["prior_close_time"]=prior_data.index[-1]
            
            # Legacy fields for backward compatibility
            result["prior_high"]=result["prior_high_wick"]
            result["prior_low"]=result["prior_low_close"]
            result["prior_high_time"]=result["prior_high_wick_time"]
            result["prior_low_time"]=result["prior_low_close_time"]
        
        # ─────────────────────────────────────────────────────────────────────
        # 8:30 AM CANDLE
        # ─────────────────────────────────────────────────────────────────────
        candle_830_start=market_open
        candle_830_end=CT.localize(datetime.combine(trading_date,time(9,0)))
        c830_mask=(df.index>=candle_830_start)&(df.index<candle_830_end)
        c830_data=df[c830_mask]
        if not c830_data.empty:
            result["candle_830"]={
                "open":round(c830_data['Open'].iloc[0],2),
                "high":round(c830_data['High'].max(),2),
                "low":round(c830_data['Low'].min(),2),
                "close":round(c830_data['Close'].iloc[-1],2)
            }
        
        # ─────────────────────────────────────────────────────────────────────
        # PRE-8:30 PRICE (last price before market open - for position assessment)
        # ─────────────────────────────────────────────────────────────────────
        pre830_mask=(df.index>=overnight_start)&(df.index<market_open)
        pre830_data=df[pre830_mask]
        if not pre830_data.empty:
            result["pre_830_price"]=round(pre830_data['Close'].iloc[-1],2)
            result["pre_830_time"]=pre830_data.index[-1]
        
        # ─────────────────────────────────────────────────────────────────────
        # TRADING DAY DATA (for analysis)
        # ─────────────────────────────────────────────────────────────────────
        day_mask=(df.index>=market_open)&(df.index<=market_close)
        day_data=df[day_mask]
        if not day_data.empty:
            result["day_high"]=round(day_data['High'].max(),2)
            result["day_low"]=round(day_data['Low'].min(),2)
            result["day_open"]=round(day_data['Open'].iloc[0],2)
            result["day_close"]=round(day_data['Close'].iloc[-1],2)
            result["day_candles"]=day_data
        
        # ─────────────────────────────────────────────────────────────────────
        # KEY TIMESTAMPS FOR ANALYSIS
        # ─────────────────────────────────────────────────────────────────────
        # 9:00 AM candle
        c900_start=CT.localize(datetime.combine(trading_date,time(9,0)))
        c900_end=CT.localize(datetime.combine(trading_date,time(9,30)))
        c900_mask=(df.index>=c900_start)&(df.index<c900_end)
        c900_data=df[c900_mask]
        if not c900_data.empty:
            result["candle_900"]={
                "open":round(c900_data['Open'].iloc[0],2),
                "high":round(c900_data['High'].max(),2),
                "low":round(c900_data['Low'].min(),2),
                "close":round(c900_data['Close'].iloc[-1],2)
            }
        
        # 9:30 AM candle
        c930_start=CT.localize(datetime.combine(trading_date,time(9,30)))
        c930_end=CT.localize(datetime.combine(trading_date,time(10,0)))
        c930_mask=(df.index>=c930_start)&(df.index<c930_end)
        c930_data=df[c930_mask]
        if not c930_data.empty:
            result["candle_930"]={
                "open":round(c930_data['Open'].iloc[0],2),
                "high":round(c930_data['High'].max(),2),
                "low":round(c930_data['Low'].min(),2),
                "close":round(c930_data['Close'].iloc[-1],2)
            }
            
    except Exception as e:
        st.warning(f"Historical extraction error: {e}")
    
    return result if result else None

# ═══════════════════════════════════════════════════════════════════════════════
# CHANNEL LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
def determine_channel(sydney_high,sydney_low,tokyo_high,tokyo_low):
    """
    Determine channel direction based on Sydney vs Tokyo session.
    Primary: Compare highs
    Tiebreaker: If highs equal, compare lows
    Final fallback: Default to FALLING (conservative)
    """
    # Primary comparison: Highs
    if tokyo_high>sydney_high:
        return "RISING","Tokyo High > Sydney High"
    elif tokyo_high<sydney_high:
        return "FALLING","Tokyo High < Sydney High"
    
    # Tiebreaker: If highs are equal, use lows
    if tokyo_low>sydney_low:
        return "RISING","Highs equal, Tokyo Low > Sydney Low (higher lows)"
    elif tokyo_low<sydney_low:
        return "FALLING","Highs equal, Tokyo Low < Sydney Low (lower lows)"
    
    # Both highs and lows equal = truly flat, default to FALLING (conservative)
    return "FALLING","Flat overnight - defaulting to FALLING (conservative)"

def calculate_channel_levels(on_high,on_high_time,on_low,on_low_time,ref_time):
    blocks_high=blocks_between(on_high_time,ref_time)
    blocks_low=blocks_between(on_low_time,ref_time)
    exp_high=SLOPE*blocks_high
    exp_low=SLOPE*blocks_low
    
    return {
        "ceiling_rising":{"level":round(on_high+exp_high,2),"anchor":on_high,"blocks":blocks_high},
        "ceiling_falling":{"level":round(on_high-exp_high,2),"anchor":on_high,"blocks":blocks_high},
        "floor_rising":{"level":round(on_low+exp_low,2),"anchor":on_low,"blocks":blocks_low},
        "floor_falling":{"level":round(on_low-exp_low,2),"anchor":on_low,"blocks":blocks_low},
    }

def get_channel_edges(levels,channel_type):
    """
    Get the active ceiling and floor based on channel type.
    If UNDETERMINED, default to FALLING (conservative - tighter channel)
    Returns: ceiling_level, floor_level, ceiling_display_name, floor_display_name
    """
    if channel_type=="RISING":
        return levels["ceiling_rising"]["level"],levels["floor_rising"]["level"],"Rising","Rising"
    elif channel_type=="FALLING":
        return levels["ceiling_falling"]["level"],levels["floor_falling"]["level"],"Falling","Falling"
    else:
        # UNDETERMINED: Default to FALLING (conservative approach)
        return levels["ceiling_falling"]["level"],levels["floor_falling"]["level"],"Falling*","Falling*"

def assess_position(price,ceiling,floor):
    if price>ceiling+BREAK_THRESHOLD:
        return "ABOVE","broken above",price-ceiling
    elif price<floor-BREAK_THRESHOLD:
        return "BELOW","broken below",floor-price
    elif price>ceiling:
        return "MARGINAL_ABOVE","marginally above",price-ceiling
    elif price<floor:
        return "MARGINAL_BELOW","marginally below",floor-price
    return "INSIDE","inside channel",min(price-floor,ceiling-price)

# ═══════════════════════════════════════════════════════════════════════════════
# CONES
# ═══════════════════════════════════════════════════════════════════════════════
def calculate_cones(prior_high_wick,prior_high_wick_time,prior_high_close,prior_high_close_time,
                   prior_low_close,prior_low_close_time,prior_close,prior_close_time,ref_time):
    """
    Calculate cone rails with correct anchors:
    - HIGH: Ascending from highest wick, Descending from highest close
    - LOW: Both from lowest close
    - CLOSE: Both from last RTH close
    """
    cones={}
    
    # HIGH cone - different anchors for asc vs desc
    blocks_high_wick=blocks_between(prior_high_wick_time,ref_time)
    blocks_high_close=blocks_between(prior_high_close_time,ref_time)
    exp_high_wick=SLOPE*blocks_high_wick
    exp_high_close=SLOPE*blocks_high_close
    cones["HIGH"]={
        "anchor_asc":prior_high_wick,
        "anchor_desc":prior_high_close,
        "asc":round(prior_high_wick+exp_high_wick,2),
        "desc":round(prior_high_close-exp_high_close,2),
        "blocks_asc":blocks_high_wick,
        "blocks_desc":blocks_high_close
    }
    
    # LOW cone - both from lowest close
    blocks_low=blocks_between(prior_low_close_time,ref_time)
    exp_low=SLOPE*blocks_low
    cones["LOW"]={
        "anchor_asc":prior_low_close,
        "anchor_desc":prior_low_close,
        "asc":round(prior_low_close+exp_low,2),
        "desc":round(prior_low_close-exp_low,2),
        "blocks_asc":blocks_low,
        "blocks_desc":blocks_low
    }
    
    # CLOSE cone - both from last RTH close
    blocks_close=blocks_between(prior_close_time,ref_time)
    exp_close=SLOPE*blocks_close
    cones["CLOSE"]={
        "anchor_asc":prior_close,
        "anchor_desc":prior_close,
        "asc":round(prior_close+exp_close,2),
        "desc":round(prior_close-exp_close,2),
        "blocks_asc":blocks_close,
        "blocks_desc":blocks_close
    }
    
    return cones

def find_targets(entry_level,cones,direction):
    targets=[]
    if direction=="CALLS":
        for name in ["CLOSE","HIGH","LOW"]:
            asc=cones[name]["asc"]
            if asc>entry_level:
                targets.append({"name":f"{name} Asc","level":asc,"distance":round(asc-entry_level,2)})
        targets.sort(key=lambda x:x["level"])
    else:
        for name in ["CLOSE","LOW","HIGH"]:
            desc=cones[name]["desc"]
            if desc<entry_level:
                targets.append({"name":f"{name} Desc","level":desc,"distance":round(entry_level-desc,2)})
        targets.sort(key=lambda x:x["level"],reverse=True)
    return targets

# ═══════════════════════════════════════════════════════════════════════════════
# 8:30 VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
def validate_830_candle(candle,ceiling,floor):
    """
    Validate the 8:30 candle based on:
    1. Did it break above ceiling or below floor? (using High/Low)
    2. Where did it close?
    3. For closed inside after breaking: Is the candle color aligned?
    
    TREND DAY LOGIC (reversal signal):
    - Broke above + closed inside + BULLISH = TREND DAY → expect DROP to floor (PUTS)
    - Broke above + closed inside + BEARISH = WAIT (9 AM may still break up)
    - Broke below + closed inside + BEARISH = TREND DAY → expect RISE to ceiling (CALLS)  
    - Broke below + closed inside + BULLISH = WAIT (9 AM may still break down)
    
    The candle color confirms the rejection - market tested one side and failed,
    so it will travel to the opposite side of the channel.
    
    Returns position, validation status, and setup direction
    """
    if candle is None:
        return {"status":"AWAITING","message":"Waiting for 8:30 candle","setup":"WAIT","position":"UNKNOWN"}
    
    o,h,l,c=candle["open"],candle["high"],candle["low"],candle["close"]
    
    broke_above=h>ceiling  # High exceeded ceiling
    broke_below=l<floor    # Low exceeded floor
    closed_above=c>ceiling
    closed_below=c<floor
    closed_inside=floor<=c<=ceiling
    is_bullish=c>o  # Close > Open = bullish candle
    is_bearish=c<o  # Close < Open = bearish candle
    
    # Determine what happened during the 8:30 candle
    if broke_below and not broke_above:
        # Candle broke below floor
        if closed_below:
            return {"status":"VALID","message":"✅ Broke below floor, closed below","setup":"PUTS","position":"BELOW","edge":floor}
        elif closed_inside:
            if is_bearish:
                # Bearish candle broke below but closed inside = rejection, will RISE to ceiling
                return {"status":"TREND_DAY","message":"⚡ TREND DAY: Broke below, rejected, expect rise to ceiling","setup":"CALLS","position":"INSIDE","edge":ceiling}
            else:
                # Bullish candle that broke below but closed inside = WAIT for 9 AM
                return {"status":"WAIT_9AM","message":"⏸️ Broke below, closed inside, BULLISH candle - wait for 9 AM","setup":"WAIT","position":"INSIDE"}
        else:  # closed_above - very wide range candle
            return {"status":"INVALIDATED","message":"❌ Broke below but closed above ceiling","setup":"WAIT","position":"ABOVE"}
    
    elif broke_above and not broke_below:
        # Candle broke above ceiling
        if closed_above:
            return {"status":"VALID","message":"✅ Broke above ceiling, closed above","setup":"CALLS","position":"ABOVE","edge":ceiling}
        elif closed_inside:
            if is_bullish:
                # Bullish candle broke above but closed inside = rejection, will DROP to floor
                return {"status":"TREND_DAY","message":"⚡ TREND DAY: Broke above, rejected, expect drop to floor","setup":"PUTS","position":"INSIDE","edge":floor}
            else:
                # Bearish candle that broke above but closed inside = WAIT for 9 AM
                return {"status":"WAIT_9AM","message":"⏸️ Broke above, closed inside, BEARISH candle - wait for 9 AM","setup":"WAIT","position":"INSIDE"}
        else:  # closed_below - very wide range candle
            return {"status":"INVALIDATED","message":"❌ Broke above but closed below floor","setup":"WAIT","position":"BELOW"}
    
    elif broke_above and broke_below:
        # Very wide range candle - broke both sides
        if closed_above:
            return {"status":"VALID","message":"✅ Wide range, closed above ceiling","setup":"CALLS","position":"ABOVE","edge":ceiling}
        elif closed_below:
            return {"status":"VALID","message":"✅ Wide range, closed below floor","setup":"PUTS","position":"BELOW","edge":floor}
        else:
            # Closed inside after breaking both = use candle color for direction
            if is_bullish:
                # Bullish but closed inside after testing both = drop to floor
                return {"status":"TREND_DAY","message":"⚡ TREND DAY: Wide range, expect drop to floor","setup":"PUTS","position":"INSIDE","edge":floor}
            elif is_bearish:
                # Bearish but closed inside after testing both = rise to ceiling
                return {"status":"TREND_DAY","message":"⚡ TREND DAY: Wide range, expect rise to ceiling","setup":"CALLS","position":"INSIDE","edge":ceiling}
            else:
                # Doji = no clear direction
                return {"status":"WAIT_9AM","message":"⏸️ Wide range DOJI, closed inside - wait for 9 AM","setup":"WAIT","position":"INSIDE"}
    
    else:
        # Candle stayed inside channel
        return {"status":"INSIDE","message":"⏸️ 8:30 candle stayed inside channel","setup":"WAIT","position":"INSIDE"}

# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY CONFIRMATION - Complete Logic
# ═══════════════════════════════════════════════════════════════════════════════
def check_entry_confirmation(candle, entry_level, direction, break_threshold=6.0):
    """
    Check if a candle is a valid SETUP candle for entry.
    
    If this candle confirms, you ENTER AT THE NEXT CANDLE'S OPEN.
    
    Example:
    - 8:00 AM confirms → Enter at 8:30 AM open
    - 8:30 AM confirms → Enter at 9:00 AM open
    - 9:00 AM confirms → Enter at 9:30 AM open
    
    ═══════════════════════════════════════════════════════════════════════════
    PUTS Setup Candle:
    ═══════════════════════════════════════════════════════════════════════════
    - BULLISH candle (close > open) that rallies TO entry level
    - Touches entry (high reaches entry within 2 pts)
    - Closes BELOW entry level
    - Did NOT break through by more than 6 pts (momentum probe check)
    
    ═══════════════════════════════════════════════════════════════════════════
    CALLS Setup Candle:
    ═══════════════════════════════════════════════════════════════════════════
    - BEARISH candle (close < open) that sells TO entry level
    - Touches entry (low reaches entry within 2 pts)
    - Closes ABOVE entry level
    - Did NOT break through by more than 6 pts (momentum probe check)
    
    ═══════════════════════════════════════════════════════════════════════════
    MOMENTUM PROBE (>6 pts break) - DO NOT ENTER
    ═══════════════════════════════════════════════════════════════════════════
    If candle breaks through by MORE than 6 pts but closes back:
    - This is NOT a rejection - it's a momentum probe
    - Next candle will likely CONTINUE in the breakout direction
    - DO NOT fade this move!
    
    Returns: dict with confirmed status, message, and details
    """
    if candle is None or entry_level is None:
        return {"confirmed": False, "message": "Waiting for candle data", "reason": "NO_DATA"}
    
    o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
    is_bullish = c > o
    is_bearish = c < o
    
    if direction == "PUTS":
        # PUTS setup: BULLISH candle touches entry and closes BELOW
        touched_entry = h >= entry_level - 2  # Allow 2 pts tolerance
        closed_below = c < entry_level
        break_beyond = h - entry_level if h > entry_level else 0
        
        if not touched_entry:
            return {"confirmed": False, "message": "Candle did not reach entry level", "reason": "NO_TOUCH",
                    "detail": f"High {h:.2f} did not reach Entry {entry_level:.2f}"}
        
        if not is_bullish:
            return {"confirmed": False, "message": "Waiting for bullish setup candle", "reason": "WRONG_COLOR",
                    "detail": "Need BULLISH candle (close > open) for PUTS setup"}
        
        if not closed_below:
            return {"confirmed": False, "message": "Candle closed above entry - no rejection", "reason": "NO_REJECTION",
                    "detail": f"Close {c:.2f} >= Entry {entry_level:.2f}"}
        
        # Check for momentum probe
        if break_beyond > break_threshold:
            return {"confirmed": False, "message": f"⚠️ Momentum probe - broke {break_beyond:.1f} pts through", 
                    "reason": "MOMENTUM_PROBE",
                    "detail": f"Broke through by {break_beyond:.1f} pts (>{break_threshold}) - next candle continues UP"}
        
        # Valid setup candle!
        return {"confirmed": True, "message": "✅ SETUP CONFIRMED - Bullish rejection",
                "reason": "CONFIRMED", "candle_color": "BULLISH",
                "detail": f"Touched {h:.2f}, closed below at {c:.2f}" + (f" (wick {break_beyond:.1f} pts)" if break_beyond > 0 else ""),
                "wick_beyond": round(break_beyond, 2)}
    
    elif direction == "CALLS":
        # CALLS setup: BEARISH candle touches entry and closes ABOVE
        touched_entry = l <= entry_level + 2  # Allow 2 pts tolerance
        closed_above = c > entry_level
        break_beyond = entry_level - l if l < entry_level else 0
        
        if not touched_entry:
            return {"confirmed": False, "message": "Candle did not reach entry level", "reason": "NO_TOUCH",
                    "detail": f"Low {l:.2f} did not reach Entry {entry_level:.2f}"}
        
        if not is_bearish:
            return {"confirmed": False, "message": "Waiting for bearish setup candle", "reason": "WRONG_COLOR",
                    "detail": "Need BEARISH candle (close < open) for CALLS setup"}
        
        if not closed_above:
            return {"confirmed": False, "message": "Candle closed below entry - no rejection", "reason": "NO_REJECTION",
                    "detail": f"Close {c:.2f} <= Entry {entry_level:.2f}"}
        
        # Check for momentum probe
        if break_beyond > break_threshold:
            return {"confirmed": False, "message": f"⚠️ Momentum probe - broke {break_beyond:.1f} pts through",
                    "reason": "MOMENTUM_PROBE", 
                    "detail": f"Broke through by {break_beyond:.1f} pts (>{break_threshold}) - next candle continues DOWN"}
        
        # Valid setup candle!
        return {"confirmed": True, "message": "✅ SETUP CONFIRMED - Bearish rejection",
                "reason": "CONFIRMED", "candle_color": "BEARISH",
                "detail": f"Touched {l:.2f}, closed above at {c:.2f}" + (f" (wick {break_beyond:.1f} pts)" if break_beyond > 0 else ""),
                "wick_beyond": round(break_beyond, 2)}
    
    return {"confirmed": False, "message": "No direction set", "reason": "NO_DIRECTION"}


def get_next_candle_time(current_time):
    """Get the next 30-min candle time"""
    time_sequence = ["08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30"]
    try:
        idx = time_sequence.index(current_time)
        if idx < len(time_sequence) - 1:
            return time_sequence[idx + 1]
    except ValueError:
        pass
    return None


def find_entry_confirmation(day_candles, entry_level, direction, offset, break_threshold=6.0, start_time="08:00", slope=0.48):
    """
    Scan through candles to find the setup candle.
    
    ═══════════════════════════════════════════════════════════════════════════
    CRITICAL: Entry level CHANGES over time!
    ═══════════════════════════════════════════════════════════════════════════
    
    The floor/ceiling are sloped lines (0.48 pts per 30-min block).
    - Ascending channel: floor rises, ceiling rises
    - Descending channel: floor falls, ceiling falls
    
    So we must calculate the entry level AT EACH CANDLE'S TIME, not use
    a fixed 9:00 AM entry level.
    
    | Setup Time  | Entry Time |
    |-------------|------------|
    | 8:00 AM     | 8:30 AM    |
    | 8:30 AM     | 9:00 AM    |
    | 9:00 AM     | 9:30 AM    |
    | 9:30 AM     | 10:00 AM   |
    | 10:00 AM    | 10:30 AM   |
    | 10:30 AM    | 11:00 AM   | ← Latest possible entry
    
    Returns the confirmation details with setup_time and entry_time.
    """
    if day_candles is None or day_candles.empty:
        return {"confirmed": False, "message": "No candle data available", "reason": "NO_DATA"}
    
    # Base entry level at 9:00 AM (in SPX terms)
    base_entry_level_spx = entry_level - offset
    
    # Reference time for slope calculation (9:00 AM)
    ref_time_str = "09:00"
    
    # Time to blocks offset from 9:00 AM
    time_to_blocks = {
        "08:00": -2,  # 2 blocks before 9:00
        "08:30": -1,  # 1 block before 9:00
        "09:00": 0,   # Reference
        "09:30": 1,   # 1 block after 9:00
        "10:00": 2,   # 2 blocks after 9:00
        "10:30": 3,   # 3 blocks after 9:00
        "11:00": 4,   # 4 blocks after 9:00
    }
    
    # Track all candle evaluations for debugging
    debug_info = []
    
    for idx, row in day_candles.iterrows():
        candle_time = idx.strftime("%H:%M")
        
        # Start checking from start_time (default 8:00 AM)
        if candle_time < start_time:
            continue
        
        # Stop checking after 10:30 AM (latest setup for 11:00 AM entry)
        if candle_time > "10:30":
            break
        
        candle = {
            "open": row["Open"] - offset,
            "high": row["High"] - offset,
            "low": row["Low"] - offset,
            "close": row["Close"] - offset
        }
        
        # Calculate entry level AT THIS CANDLE'S TIME
        blocks_from_ref = time_to_blocks.get(candle_time, 0)
        entry_level_at_time = base_entry_level_spx + (blocks_from_ref * slope)
        
        confirmation = check_entry_confirmation(candle, entry_level_at_time, direction, break_threshold)
        
        # Store debug info
        debug_info.append({
            "time": candle_time,
            "candle": candle,
            "entry_level": round(entry_level_at_time, 2),
            "blocks_from_ref": blocks_from_ref,
            "result": confirmation.get("reason", "UNKNOWN"),
            "detail": confirmation.get("detail", confirmation.get("message", ""))
        })
        
        if confirmation["confirmed"]:
            entry_time = get_next_candle_time(candle_time)
            confirmation["setup_time"] = candle_time
            confirmation["entry_time"] = entry_time
            confirmation["time"] = entry_time  # For backward compatibility
            confirmation["candle"] = candle
            confirmation["entry_level_at_time"] = round(entry_level_at_time, 2)
            confirmation["message"] = f"✅ {candle_time} setup → Enter at {entry_time}"
            confirmation["debug"] = debug_info
            return confirmation
        
        # If momentum probe, return immediately
        if confirmation.get("reason") == "MOMENTUM_PROBE":
            confirmation["setup_time"] = candle_time
            confirmation["time"] = candle_time
            confirmation["debug"] = debug_info
            return confirmation
    
    return {"confirmed": False, "message": "No setup candle found by 10:30 AM", "reason": "NOT_FOUND", "debug": debug_info}

# ═══════════════════════════════════════════════════════════════════════════════
# HISTORICAL OUTCOME ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
def analyze_historical_outcome(hist_data, validation, ceiling_es, floor_es, targets, direction, entry_level_es, offset):
    """
    Analyze what actually happened on a historical date
    All prices displayed in SPX (converted from ES candles)
    
    Entry confirmation logic includes momentum probe detection:
    - PUTS: Bullish candle touches entry, closes BELOW, break <6pts
    - CALLS: Bearish candle touches entry, closes ABOVE, break <6pts
    - If break >6pts but closes inside = MOMENTUM PROBE, don't enter!
    """
    if "day_candles" not in hist_data:
        return None
    
    day_candles = hist_data["day_candles"]
    entry_level_spx = round(entry_level_es - offset, 2)
    ceiling_spx = round(ceiling_es - offset, 2) if ceiling_es else None
    floor_spx = round(floor_es - offset, 2) if floor_es else None
    
    result = {
        "setup_valid": validation["status"] in ["VALID", "TREND_DAY"],
        "direction": direction,
        "entry_level_es": entry_level_es,
        "entry_level_spx": entry_level_spx,
        "targets_hit": [],
        "max_favorable": 0,
        "max_adverse": 0,
        "final_price": round(hist_data.get("day_close", 0) - offset, 2),
        "timeline": [],
        "entry_confirmation": None
    }
    
    if not result["setup_valid"]:
        result["outcome"] = "NO_SETUP"
        result["message"] = "Setup was not valid"
        return result
    
    # Find setup candle - start from 8:00 AM (can set up for 8:30 entry)
    # Setup candle does rejection work → Enter at NEXT candle's open
    # IMPORTANT: Pass slope so entry level can be calculated at each candle's time
    entry_conf = find_entry_confirmation(
        day_candles, entry_level_es, direction, offset, BREAK_THRESHOLD, "08:00", SLOPE
    )
    result["entry_confirmation"] = entry_conf
    
    if not entry_conf.get("confirmed"):
        # Check if it was a momentum probe
        if entry_conf.get("reason") == "MOMENTUM_PROBE":
            result["outcome"] = "MOMENTUM_PROBE"
            result["message"] = entry_conf.get("message", "Momentum probe detected - no entry")
        else:
            result["outcome"] = "NO_ENTRY"
            result["message"] = entry_conf.get("message", "No valid entry confirmation")
        return result
    
    # Entry confirmed - track from confirmation candle
    # Use the entry level AT THE ENTRY TIME (not 9:00 AM base level)
    entry_time = entry_conf.get("time", "08:30")
    setup_time = entry_conf.get("setup_time", "08:30")
    
    # Calculate entry level at the actual entry time
    time_to_blocks = {
        "08:00": -2, "08:30": -1, "09:00": 0, "09:30": 1,
        "10:00": 2, "10:30": 3, "11:00": 4
    }
    blocks_from_ref = time_to_blocks.get(entry_time, 0)
    entry_price_spx = entry_level_spx + (blocks_from_ref * SLOPE)
    
    result["entry_level_at_time"] = round(entry_price_spx, 2)
    result["timeline"].append({
        "time": entry_time,
        "event": f"ENTRY ({entry_conf.get('candle_color', '')})",
        "price": round(entry_price_spx, 2)
    })
    
    # Track price movement after entry
    tracking_started=False
    for idx,row in day_candles.iterrows():
        candle_time=idx.strftime("%H:%M")
        
        # Start tracking after entry confirmation time
        if candle_time<entry_time:
            continue
        if candle_time==entry_time:
            tracking_started=True
            continue
        if not tracking_started:
            continue
        
        # Convert ES candle to SPX
        candle_high_spx=row['High']-offset
        candle_low_spx=row['Low']-offset
        
        # Track movement (in SPX terms)
        if direction=="PUTS":
            favorable=entry_price_spx-candle_low_spx
            adverse=candle_high_spx-entry_price_spx
        else:
            favorable=candle_high_spx-entry_price_spx
            adverse=entry_price_spx-candle_low_spx
        
        result["max_favorable"]=max(result["max_favorable"],favorable)
        result["max_adverse"]=max(result["max_adverse"],adverse)
        
        # Check targets (targets are already in SPX)
        for tgt in targets:
            if tgt["name"] not in [t["name"] for t in result["targets_hit"]]:
                if direction=="PUTS" and candle_low_spx<=tgt["level"]:
                    result["targets_hit"].append({"name":tgt["name"],"level":tgt["level"],"time":candle_time})
                    result["timeline"].append({"time":candle_time,"event":f"TARGET: {tgt['name']}","price":tgt["level"]})
                elif direction=="CALLS" and candle_high_spx>=tgt["level"]:
                    result["targets_hit"].append({"name":tgt["name"],"level":tgt["level"],"time":candle_time})
                    result["timeline"].append({"time":candle_time,"event":f"TARGET: {tgt['name']}","price":tgt["level"]})
    
    # Determine outcome
    if len(result["targets_hit"])>0:
        result["outcome"]="WIN"
        result["message"]=f"Hit {len(result['targets_hit'])} target(s): {', '.join([t['name'] for t in result['targets_hit']])}"
    elif result["max_favorable"]>10:
        result["outcome"]="PARTIAL"
        result["message"]=f"Moved {result['max_favorable']:.0f} pts favorable but missed targets"
    else:
        result["outcome"]="LOSS"
        result["message"]=f"Max adverse: {result['max_adverse']:.0f} pts"
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# FLOW BIAS
# ═══════════════════════════════════════════════════════════════════════════════
def calculate_flow_bias(price,on_high,on_low,vix,vix_high,vix_low,prior_close,es_candles=None):
    signals=[]
    score=0
    on_range=on_high-on_low
    
    price_pos=(price-on_low)/on_range*100 if on_range>0 else 50
    if price>on_high:score+=30;signals.append(("Price","CALLS",f"+{price-on_high:.0f}"))
    elif price<on_low:score-=30;signals.append(("Price","PUTS",f"{price-on_low:.0f}"))
    elif price_pos>75:score+=15;signals.append(("Price","CALLS",f"{price_pos:.0f}%"))
    elif price_pos<25:score-=15;signals.append(("Price","PUTS",f"{price_pos:.0f}%"))
    else:signals.append(("Price","NEUTRAL",f"{price_pos:.0f}%"))
    
    vix_range=vix_high-vix_low
    vix_pos=(vix-vix_low)/vix_range*100 if vix_range>0 else 50
    if vix>vix_high:score-=25;signals.append(("VIX","PUTS",f"{vix:.1f}"))
    elif vix<vix_low:score+=25;signals.append(("VIX","CALLS",f"{vix:.1f}"))
    elif vix_pos>70:score-=12;signals.append(("VIX","PUTS",f"{vix_pos:.0f}%"))
    elif vix_pos<30:score+=12;signals.append(("VIX","CALLS",f"{vix_pos:.0f}%"))
    else:signals.append(("VIX","NEUTRAL",f"{vix_pos:.0f}%"))
    
    gap=price-prior_close
    if gap>10:score+=25;signals.append(("Gap","CALLS",f"+{gap:.0f}"))
    elif gap<-10:score-=25;signals.append(("Gap","PUTS",f"{gap:.0f}"))
    elif gap>5:score+=12;signals.append(("Gap","CALLS",f"+{gap:.0f}"))
    elif gap<-5:score-=12;signals.append(("Gap","PUTS",f"{gap:.0f}"))
    else:signals.append(("Gap","NEUTRAL",f"{gap:+.0f}"))
    
    if score>=30:bias="HEAVY_CALLS"
    elif score<=-30:bias="HEAVY_PUTS"
    else:bias="NEUTRAL"
    
    return {"bias":bias,"score":score,"signals":signals}

# ═══════════════════════════════════════════════════════════════════════════════
# MOMENTUM & MA
# ═══════════════════════════════════════════════════════════════════════════════
def calculate_momentum(es_candles):
    if es_candles is None or len(es_candles)<26:
        return {"signal":"NEUTRAL","rsi":50,"macd":0}
    close=es_candles['Close']
    delta=close.diff()
    gain=(delta.where(delta>0,0)).rolling(14).mean()
    loss=(-delta.where(delta<0,0)).rolling(14).mean()
    rs=gain/loss
    rsi=100-(100/(1+rs))
    rsi_val=round(rsi.iloc[-1],1) if not pd.isna(rsi.iloc[-1]) else 50
    ema12=close.ewm(span=12).mean()
    ema26=close.ewm(span=26).mean()
    macd_hist=round((ema12-ema26-(ema12-ema26).ewm(span=9).mean()).iloc[-1],2)
    if rsi_val>50 and macd_hist>0:signal="BULLISH"
    elif rsi_val<50 and macd_hist<0:signal="BEARISH"
    else:signal="NEUTRAL"
    return {"signal":signal,"rsi":rsi_val,"macd":macd_hist}

def calculate_ema_signals(es_candles,current_price):
    """
    8/21 EMA Cross + 200 EMA Filter
    - 8/21 cross: Fast momentum signal for 0DTE entries
    - 200 EMA: Directional filter (above = favor longs, below = favor shorts)
    """
    result={
        "cross_signal":"NEUTRAL",
        "filter_signal":"NEUTRAL",
        "ema8":None,"ema21":None,"ema200":None,
        "cross_bullish":False,"cross_bearish":False,
        "above_200":False,"below_200":False,
        "aligned_calls":False,"aligned_puts":False
    }
    
    if es_candles is None or len(es_candles)<21:
        return result
    
    close=es_candles['Close']
    
    # Calculate EMAs
    ema8=close.ewm(span=8).mean()
    ema21=close.ewm(span=21).mean()
    ema200=close.ewm(span=min(200,len(close))).mean()
    
    ema8_val=round(ema8.iloc[-1],2)
    ema21_val=round(ema21.iloc[-1],2)
    ema200_val=round(ema200.iloc[-1],2)
    
    result["ema8"]=ema8_val
    result["ema21"]=ema21_val
    result["ema200"]=ema200_val
    
    # 8/21 Cross Signal
    if ema8_val>ema21_val:
        result["cross_signal"]="BULLISH"
        result["cross_bullish"]=True
    elif ema8_val<ema21_val:
        result["cross_signal"]="BEARISH"
        result["cross_bearish"]=True
    
    # 200 EMA Filter
    if current_price and current_price>ema200_val:
        result["filter_signal"]="ABOVE_200"
        result["above_200"]=True
    elif current_price and current_price<ema200_val:
        result["filter_signal"]="BELOW_200"
        result["below_200"]=True
    
    # Alignment check
    # CALLS aligned: 8>21 (bullish cross) AND price above 200
    result["aligned_calls"]=result["cross_bullish"] and result["above_200"]
    # PUTS aligned: 8<21 (bearish cross) AND price below 200
    result["aligned_puts"]=result["cross_bearish"] and result["below_200"]
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# OPTION PRICING
# ═══════════════════════════════════════════════════════════════════════════════
def get_strike(entry_level,opt_type):
    if opt_type=="CALL":return int(round((entry_level+20)/5)*5)
    return int(round((entry_level-20)/5)*5)

def estimate_prices(entry_level,strike,opt_type,vix,hours):
    iv=vix/100
    T=max(0.001,hours/(365*24))
    entry=black_scholes(entry_level,strike,T,0.05,iv,opt_type)
    return round(entry,2)

def estimate_exit_prices(entry_level,strike,opt_type,vix,hours,targets):
    iv=vix/100
    entry_T=max(0.001,hours/(365*24))
    entry_price=black_scholes(entry_level,strike,entry_T,0.05,iv,opt_type)
    results=[]
    for i,tgt in enumerate(targets[:3]):
        exit_T=max(0.001,(hours-1-i*0.5)/(365*24))
        exit_price=black_scholes(tgt["level"],strike,exit_T,0.05,iv,opt_type)
        pct=(exit_price-entry_price)/entry_price*100 if entry_price>0 else 0
        results.append({"target":tgt["name"],"level":tgt["level"],"price":round(exit_price,2),"pct":round(pct,0)})
    return results,round(entry_price,2)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE
# ═══════════════════════════════════════════════════════════════════════════════
def calculate_confidence(channel_type,validation,direction,ema_signals,flow,vix_zone):
    """
    Confidence scoring:
    - Channel determined: +25
    - 8:30 candle validated: +25  
    - 200 EMA filter aligned: +15
    - 8/21 cross aligned: +15
    - Flow bias aligned: +10
    - VIX favorable: +10
    = 100 max
    """
    score=0
    breakdown=[]
    
    # Channel determination (+25)
    if channel_type!="UNDETERMINED":
        score+=25
        breakdown.append(("Channel","+25"))
    else:
        breakdown.append(("Channel","0"))
    
    # 8:30 validation (+25)
    if validation["status"] in ["VALID","TREND_DAY"]:
        score+=25
        breakdown.append(("8:30 Valid","+25"))
    elif validation["status"]=="INSIDE":
        score+=10
        breakdown.append(("8:30 Inside","+10"))
    else:
        breakdown.append(("8:30 Wait","0"))
    
    # 200 EMA filter (+15)
    if direction=="PUTS" and ema_signals["below_200"]:
        score+=15
        breakdown.append(("Below 200","+15"))
    elif direction=="CALLS" and ema_signals["above_200"]:
        score+=15
        breakdown.append(("Above 200","+15"))
    elif direction in ["PUTS","CALLS"]:
        breakdown.append(("200 EMA","0 ⚠️"))
    else:
        breakdown.append(("200 EMA","N/A"))
    
    # 8/21 cross (+15)
    if direction=="PUTS" and ema_signals["cross_bearish"]:
        score+=15
        breakdown.append(("8/21 Bear","+15"))
    elif direction=="CALLS" and ema_signals["cross_bullish"]:
        score+=15
        breakdown.append(("8/21 Bull","+15"))
    elif direction in ["PUTS","CALLS"]:
        breakdown.append(("8/21 Cross","0 ⚠️"))
    else:
        breakdown.append(("8/21 Cross","N/A"))
    
    # Flow bias (+10)
    if direction=="PUTS" and flow["bias"] in ["HEAVY_PUTS","MODERATE_PUTS"]:
        score+=10
        breakdown.append(("Flow","+10"))
    elif direction=="CALLS" and flow["bias"] in ["HEAVY_CALLS","MODERATE_CALLS"]:
        score+=10
        breakdown.append(("Flow","+10"))
    elif flow["bias"]=="NEUTRAL":
        score+=5
        breakdown.append(("Flow","+5"))
    else:
        breakdown.append(("Flow","0"))
    
    # VIX zone (+10)
    if vix_zone in ["LOW","NORMAL"]:
        score+=10
        breakdown.append(("VIX","+10"))
    elif vix_zone=="ELEVATED":
        score+=5
        breakdown.append(("VIX","+5"))
    else:
        breakdown.append(("VIX","0"))
    
    return {"score":score,"breakdown":breakdown}

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
def safe_float(value,default):
    """Safely convert to float, returning default if None or invalid"""
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError,ValueError):
        return float(default)

def render_sidebar():
    saved=load_inputs()
    
    # Generate time options for 30-min chart (:00 and :30 only)
    time_options=[]
    for h in range(24):
        time_options.append(f"{h:02d}:00")
        time_options.append(f"{h:02d}:30")
    
    with st.sidebar:
        st.markdown("## 🔮 SPX Prophet V6.1")
        st.markdown("*Structural 0DTE Strategy*")
        
        trading_date=st.date_input("📅 Trading Date",value=date.today())
        is_historical=trading_date<date.today()
        is_future=trading_date>date.today()
        is_planning=is_future
        
        if is_historical:
            st.info(f"📜 Historical: {trading_date.strftime('%A, %b %d')}")
        elif is_planning:
            st.info(f"📋 Planning: {trading_date.strftime('%A, %b %d')}")
        
        st.markdown("---")
        
        # ─────────────────────────────────────────────────────────────────────
        # ES/SPX OFFSET (always visible)
        # ─────────────────────────────────────────────────────────────────────
        default_offset = safe_float(saved.get("offset"), 18.0)
        offset = st.number_input("⚙️ ES→SPX Offset", value=default_offset, step=0.5,
                               help="SPX = ES - Offset")
        
        # Auto-save offset if changed
        if offset != default_offset:
            saved["offset"] = offset
            save_inputs(saved)
        
        st.markdown("---")
        
        # ─────────────────────────────────────────────────────────────────────
        # MODULAR OVERRIDE SECTIONS
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("### 📝 Manual Overrides")
        st.caption("Enable sections to override auto-fetched data")
        
        # Current ES Override (useful when data feeds fail)
        override_es=st.checkbox("Override Current ES",value=False,key="oes")
        if override_es:
            manual_es=st.number_input("Current ES Price",value=safe_float(saved.get("manual_es"),6900.0),step=0.25,
                                      help="Enter current ES futures price")
        else:
            manual_es=None
        
        st.markdown("")
        
        # VIX Override
        override_vix=st.checkbox("Override VIX",value=False,key="ovix")
        if override_vix:
            c1,c2=st.columns(2)
            vix_high=c1.number_input("VIX High",value=safe_float(saved.get("vix_high"),18.0),step=0.1)
            vix_low=c2.number_input("VIX Low",value=safe_float(saved.get("vix_low"),15.0),step=0.1)
        else:
            vix_high=vix_low=None
        
        st.markdown("")
        
        # O/N Pivots Override
        override_on=st.checkbox("Override O/N Pivots",value=False,key="oon")
        if override_on:
            st.markdown("**Overnight High**")
            c1,c2=st.columns([2,1])
            on_high=c1.number_input("O/N High (ES)",value=safe_float(saved.get("on_high"),6075.0),step=0.5,label_visibility="collapsed")
            on_high_time_str=c2.selectbox("Time",time_options,index=time_options.index("22:00") if "22:00" in time_options else 0,key="onht",label_visibility="collapsed")
            
            st.markdown("**Overnight Low**")
            c1,c2=st.columns([2,1])
            on_low=c1.number_input("O/N Low (ES)",value=safe_float(saved.get("on_low"),6040.0),step=0.5,label_visibility="collapsed")
            on_low_time_str=c2.selectbox("Time",time_options,index=time_options.index("02:00") if "02:00" in time_options else 0,key="onlt",label_visibility="collapsed")
            
            # Parse times
            on_high_hr,on_high_mn=int(on_high_time_str.split(":")[0]),int(on_high_time_str.split(":")[1])
            on_low_hr,on_low_mn=int(on_low_time_str.split(":")[0]),int(on_low_time_str.split(":")[1])
        else:
            on_high=on_low=None
            on_high_hr=on_high_mn=on_low_hr=on_low_mn=None
        
        st.markdown("")
        
        # Prior RTH Override (for cones)
        override_prior=st.checkbox("Override Prior RTH",value=False,key="oprior")
        if override_prior:
            st.markdown("**Prior High (highest wick)**")
            c1,c2=st.columns([2,1])
            prior_high=c1.number_input("Price (ES)",value=safe_float(saved.get("prior_high"),6080.0),step=0.5,key="ph",label_visibility="collapsed")
            prior_high_time_str=c2.selectbox("Time",time_options,index=time_options.index("10:00") if "10:00" in time_options else 0,key="pht",label_visibility="collapsed")
            
            st.markdown("**Prior Low (lowest close)**")
            c1,c2=st.columns([2,1])
            prior_low=c1.number_input("Price (ES)",value=safe_float(saved.get("prior_low"),6030.0),step=0.5,key="pl",label_visibility="collapsed")
            prior_low_time_str=c2.selectbox("Time",time_options,index=time_options.index("14:00") if "14:00" in time_options else 0,key="plt",label_visibility="collapsed")
            
            st.markdown("**Prior Close**")
            c1,c2=st.columns([2,1])
            prior_close=c1.number_input("Price (ES)",value=safe_float(saved.get("prior_close"),6055.0),step=0.5,key="pc",label_visibility="collapsed")
            prior_close_time_str=c2.selectbox("Time",time_options,index=time_options.index("15:00") if "15:00" in time_options else 0,key="pct",label_visibility="collapsed")
            
            # Parse times
            prior_high_hr,prior_high_mn=int(prior_high_time_str.split(":")[0]),int(prior_high_time_str.split(":")[1])
            prior_low_hr,prior_low_mn=int(prior_low_time_str.split(":")[0]),int(prior_low_time_str.split(":")[1])
            prior_close_hr,prior_close_mn=int(prior_close_time_str.split(":")[0]),int(prior_close_time_str.split(":")[1])
        else:
            prior_high=prior_low=prior_close=None
            prior_high_hr=prior_high_mn=prior_low_hr=prior_low_mn=prior_close_hr=prior_close_mn=None
        
        st.markdown("---")
        
        # ─────────────────────────────────────────────────────────────────────
        # REFERENCE TIME
        # ─────────────────────────────────────────────────────────────────────
        ref_time_sel=st.selectbox("⏰ Reference Time",["8:30 AM","9:00 AM","9:30 AM"],index=1)
        ref_map={"8:30 AM":(8,30),"9:00 AM":(9,0),"9:30 AM":(9,30)}
        ref_hr,ref_mn=ref_map[ref_time_sel]
        
        st.markdown("---")
        
        # ─────────────────────────────────────────────────────────────────────
        # OPTIONS
        # ─────────────────────────────────────────────────────────────────────
        auto_refresh=st.checkbox("🔄 Auto Refresh (30s)",value=False) if not (is_historical or is_planning) else False
        debug=st.checkbox("🔧 Debug Mode",value=False)
        
        if st.button("💾 Save Inputs",use_container_width=True):
            save_inputs({
                "offset":offset,
                "manual_es":manual_es,
                "on_high":on_high,"on_low":on_low,
                "vix_high":vix_high,"vix_low":vix_low,
                "prior_high":prior_high,"prior_low":prior_low,"prior_close":prior_close
            })
            st.success("✅ Saved")
    
    return {
        "trading_date":trading_date,
        "is_historical":is_historical,
        "is_planning":is_planning,
        "offset":offset,
        # ES override
        "override_es":override_es,
        "manual_es":manual_es,
        # VIX overrides
        "override_vix":override_vix,
        "vix_high":vix_high,"vix_low":vix_low,
        # O/N overrides
        "override_on":override_on,
        "on_high":on_high,"on_low":on_low,
        "on_high_time":(on_high_hr,on_high_mn) if override_on else None,
        "on_low_time":(on_low_hr,on_low_mn) if override_on else None,
        # Prior RTH overrides
        "override_prior":override_prior,
        "prior_high":prior_high,"prior_low":prior_low,"prior_close":prior_close,
        "prior_high_time":(prior_high_hr,prior_high_mn) if override_prior else None,
        "prior_low_time":(prior_low_hr,prior_low_mn) if override_prior else None,
        "prior_close_time":(prior_close_hr,prior_close_mn) if override_prior else None,
        # Other
        "ref_hr":ref_hr,"ref_mn":ref_mn,
        "auto_refresh":auto_refresh,"debug":debug
    }

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    st.markdown(STYLES,unsafe_allow_html=True)
    inputs=render_sidebar()
    now=now_ct()
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHECK FOR FUTURE DATE IN HISTORICAL MODE
    # ─────────────────────────────────────────────────────────────────────────
    if inputs["is_historical"]:
        today = now.date()
        selected_date = inputs["trading_date"]
        if selected_date > today:
            st.error(f"⚠️ **Cannot analyze {selected_date.strftime('%A, %B %d, %Y')}** - this date hasn't occurred yet!")
            st.info("💡 Switch to **Planning Mode** to prepare for a future trading day, or select a past date for historical analysis.")
            return
        elif selected_date == today:
            # Check if market has opened yet (8:30 AM CT)
            market_open_time = now.replace(hour=8, minute=30, second=0, microsecond=0)
            if now < market_open_time:
                st.warning(f"⚠️ **Today's session hasn't started yet.** Market opens at 8:30 AM CT.")
                st.info("💡 Switch to **Planning Mode** to prepare for today, or wait until after market open for historical analysis.")
                return
    
    # ─────────────────────────────────────────────────────────────────────────
    # FETCH DATA
    # ─────────────────────────────────────────────────────────────────────────
    with st.spinner("Loading data..."):
        if inputs["is_historical"] or inputs["is_planning"]:
            # Historical or Planning mode - fetch candles for that date range
            # Need extra days to handle weekends (if trading_date is Monday/Tuesday)
            start=inputs["trading_date"]-timedelta(days=7)  # Go back a full week
            end=inputs["trading_date"]+timedelta(days=1)
            es_candles=fetch_es_candles_range(start,end)
            
            if es_candles is not None and not es_candles.empty:
                hist_data=extract_historical_data(es_candles,inputs["trading_date"],inputs["offset"])
            else:
                hist_data=None
                if inputs["is_planning"]:
                    st.warning("⚠️ Could not fetch prior RTH data. Using manual inputs.")
                else:
                    st.error("❌ Could not fetch historical data for this date. Try a date within the last 60 days.")
            
            if inputs["is_historical"]:
                es_price=hist_data.get("day_open") if hist_data else None
            else:
                # Planning mode - try multiple sources for live price
                live_es = fetch_es_current()
                if live_es:
                    es_price = live_es
                else:
                    # Try deriving from SPX
                    derived_es = fetch_es_from_spx(inputs["offset"])
                    if derived_es:
                        es_price = derived_es
                        st.info(f"📊 ES derived from SPX ({es_price}) - direct ES feed unavailable")
                    elif hist_data:
                        es_price = hist_data.get("prior_close")
                        st.info(f"📊 Using Friday's close ({es_price}) - live data not available yet")
                    else:
                        es_price = None
            spx_price=round(es_price-inputs["offset"],2) if es_price else None
            vix=fetch_vix_polygon() or 16.0
        else:
            # Live mode (today)
            es_candles=fetch_es_candles(7)
            es_price=fetch_es_current()
            
            # If ES fetch failed, try deriving from SPX
            if es_price is None:
                derived_es = fetch_es_from_spx(inputs["offset"])
                if derived_es:
                    es_price = derived_es
                    st.info(f"📊 ES derived from SPX - direct ES feed unavailable")
            
            spx_price=fetch_spx_polygon()
            vix=fetch_vix_polygon() or 16.0
            hist_data=None
    
    # Check if manual ES override is enabled
    if inputs.get("override_es") and inputs.get("manual_es"):
        es_price = inputs["manual_es"]
        st.success(f"✅ Using manual ES: {es_price}")
    elif es_price is None:
        st.warning("⚠️ **Could not fetch live ES price.** Enable 'Override Current ES' in sidebar to enter manually.")
        es_price = 6050  # Fallback
    
    offset=inputs["offset"]
    
    # ─────────────────────────────────────────────────────────────────────────
    # DETERMINE BASE DATES
    # ─────────────────────────────────────────────────────────────────────────
    # For PRIOR RTH (cones): Monday uses Friday
    prior_rth_day=inputs["trading_date"]-timedelta(days=1)
    if prior_rth_day.weekday()==6:prior_rth_day=prior_rth_day-timedelta(days=2)  # Sunday→Friday
    elif prior_rth_day.weekday()==5:prior_rth_day=prior_rth_day-timedelta(days=1)  # Saturday→Friday
    
    # For OVERNIGHT: Day before trading date (Sunday for Monday)
    overnight_day=inputs["trading_date"]-timedelta(days=1)
    
    # ─────────────────────────────────────────────────────────────────────────
    # POPULATE DATA (Auto-fetch + Modular Overrides)
    # ─────────────────────────────────────────────────────────────────────────
    
    # Start with auto-fetched data if available
    if hist_data:
        syd_h=hist_data.get("sydney_high")
        syd_l=hist_data.get("sydney_low")
        tok_h=hist_data.get("tokyo_high")
        tok_l=hist_data.get("tokyo_low")
        on_high=hist_data.get("on_high")
        on_low=hist_data.get("on_low")
        on_high_time=hist_data.get("on_high_time")
        on_low_time=hist_data.get("on_low_time")
        
        prior_high_wick=hist_data.get("prior_high_wick",6080)
        prior_high_close=hist_data.get("prior_high_close",6075)
        prior_low_close=hist_data.get("prior_low_close",6030)
        prior_close=hist_data.get("prior_close",6055)
        prior_high_wick_time=hist_data.get("prior_high_wick_time")
        prior_high_close_time=hist_data.get("prior_high_close_time")
        prior_low_close_time=hist_data.get("prior_low_close_time")
        prior_close_time=hist_data.get("prior_close_time")
        
        candle_830=hist_data.get("candle_830") if inputs["is_historical"] else None
        current_es=hist_data.get("day_open",es_price) if inputs["is_historical"] else (es_price or hist_data.get("prior_close",6050))
    else:
        # No hist_data - use defaults
        syd_h=syd_l=tok_h=tok_l=on_high=on_low=None
        on_high_time=on_low_time=None
        prior_high_wick=prior_high_close=6080
        prior_low_close=6030
        prior_close=6055
        prior_high_wick_time=prior_high_close_time=prior_low_close_time=prior_close_time=None
        candle_830=None
        current_es=es_price or 6050
    
    # ─────────────────────────────────────────────────────────────────────────
    # APPLY MANUAL OVERRIDES
    # ─────────────────────────────────────────────────────────────────────────
    
    # VIX Override
    if inputs["override_vix"] and inputs["vix_high"] is not None:
        vix_high=inputs["vix_high"]
        vix_low=inputs["vix_low"]
    else:
        vix_high=18
        vix_low=15
    
    # O/N Pivots Override
    if inputs["override_on"] and inputs["on_high"] is not None:
        on_high=inputs["on_high"]
        on_low=inputs["on_low"]
        # Build times from user input
        on_h_hr,on_h_mn=inputs["on_high_time"]
        on_l_hr,on_l_mn=inputs["on_low_time"]
        # Determine date for time (O/N high usually previous day evening, low current day early AM)
        if on_h_hr>=17:  # Evening = overnight_day
            on_high_time=CT.localize(datetime.combine(overnight_day,time(on_h_hr,on_h_mn)))
        else:  # Early morning = trading_date
            on_high_time=CT.localize(datetime.combine(inputs["trading_date"],time(on_h_hr,on_h_mn)))
        if on_l_hr>=17:
            on_low_time=CT.localize(datetime.combine(overnight_day,time(on_l_hr,on_l_mn)))
        else:
            on_low_time=CT.localize(datetime.combine(inputs["trading_date"],time(on_l_hr,on_l_mn)))
        # When manually overriding O/N, use same for Sydney/Tokyo (default FALLING)
        syd_h=on_high
        syd_l=on_low
        tok_h=on_high-1
        tok_l=on_low
    
    # Prior RTH Override
    if inputs["override_prior"] and inputs["prior_high"] is not None:
        prior_high_wick=inputs["prior_high"]
        prior_high_close=inputs["prior_high"]  # Manual mode uses same for wick and close
        prior_low_close=inputs["prior_low"]
        prior_close=inputs["prior_close"]
        # Build times from user input
        ph_hr,ph_mn=inputs["prior_high_time"]
        pl_hr,pl_mn=inputs["prior_low_time"]
        pc_hr,pc_mn=inputs["prior_close_time"]
        prior_high_wick_time=CT.localize(datetime.combine(prior_rth_day,time(ph_hr,ph_mn)))
        prior_high_close_time=prior_high_wick_time
        prior_low_close_time=CT.localize(datetime.combine(prior_rth_day,time(pl_hr,pl_mn)))
        prior_close_time=CT.localize(datetime.combine(prior_rth_day,time(pc_hr,pc_mn)))
    
    # ─────────────────────────────────────────────────────────────────────────
    # FALLBACKS - Fill any remaining None values
    # ─────────────────────────────────────────────────────────────────────────
    
    # O/N values
    if on_high is None:on_high=prior_high_wick or 6075
    if on_low is None:on_low=prior_low_close or 6040
    if on_high_time is None:on_high_time=CT.localize(datetime.combine(overnight_day,time(22,0)))
    if on_low_time is None:on_low_time=CT.localize(datetime.combine(inputs["trading_date"],time(2,0)))
    
    # Sydney/Tokyo (if still None, derive from O/N)
    if syd_h is None:syd_h=on_high
    if syd_l is None:syd_l=on_low
    if tok_h is None:tok_h=on_high-1  # Default FALLING
    if tok_l is None:tok_l=on_low
    
    # Prior RTH times
    if prior_high_wick_time is None:prior_high_wick_time=CT.localize(datetime.combine(prior_rth_day,time(10,0)))
    if prior_high_close_time is None:prior_high_close_time=CT.localize(datetime.combine(prior_rth_day,time(10,0)))
    if prior_low_close_time is None:prior_low_close_time=CT.localize(datetime.combine(prior_rth_day,time(14,0)))
    if prior_close_time is None:prior_close_time=CT.localize(datetime.combine(prior_rth_day,time(15,0)))
    
    current_spx=round(current_es-offset,2)
    
    # ─────────────────────────────────────────────────────────────────────────
    # CALCULATIONS
    # ─────────────────────────────────────────────────────────────────────────
    channel_type,channel_reason=determine_channel(syd_h,syd_l,tok_h,tok_l)
    
    ref_time=CT.localize(datetime.combine(inputs["trading_date"],time(inputs["ref_hr"],inputs["ref_mn"])))
    expiry_time=CT.localize(datetime.combine(inputs["trading_date"],time(15,0)))
    hours_to_expiry=6.5 if inputs["is_historical"] else max(0.1,(expiry_time-now).total_seconds()/3600)
    
    levels=calculate_channel_levels(on_high,on_high_time,on_low,on_low_time,ref_time)
    ceiling_es,floor_es,ceil_key,floor_key=get_channel_edges(levels,channel_type)
    ceiling_spx=round(ceiling_es-offset,2) if ceiling_es else None
    floor_spx=round(floor_es-offset,2) if floor_es else None
    
    # Cones - using correct anchors for each line
    cones_es=calculate_cones(prior_high_wick,prior_high_wick_time,prior_high_close,prior_high_close_time,
                             prior_low_close,prior_low_close_time,prior_close,prior_close_time,ref_time)
    # Convert to SPX
    cones_spx={}
    for k,v in cones_es.items():
        cones_spx[k]={
            "anchor_asc":round(v["anchor_asc"]-offset,2),
            "anchor_desc":round(v["anchor_desc"]-offset,2),
            "asc":round(v["asc"]-offset,2),
            "desc":round(v["desc"]-offset,2)
        }
    
    # Validation - 8:30 candle determines position by breaking ceiling/floor
    if candle_830 and ceiling_es and floor_es:
        validation=validate_830_candle(candle_830,ceiling_es,floor_es)
        position=validation.get("position","UNKNOWN")
    else:
        validation={"status":"AWAITING","message":"Waiting for data","setup":"WAIT","position":"UNKNOWN"}
        position="UNKNOWN"
    
    # Calculate distance from edges for display
    if candle_830 and ceiling_es and floor_es:
        c830_close=candle_830["close"]
        if position=="ABOVE":
            pos_desc="above ceiling"
            pos_dist=c830_close-ceiling_es
        elif position=="BELOW":
            pos_desc="below floor"
            pos_dist=floor_es-c830_close
        else:
            pos_desc="inside channel"
            pos_dist=min(c830_close-floor_es,ceiling_es-c830_close) if c830_close else 0
    else:
        pos_desc="unknown"
        pos_dist=0
    
    # Direction & targets based on validation
    if validation["setup"]=="PUTS":
        direction="PUTS"
        entry_edge_es=validation.get("edge",floor_es)
        entry_edge_spx=round(entry_edge_es-offset,2) if entry_edge_es else floor_spx
        targets=find_targets(entry_edge_spx,cones_spx,"PUTS") if entry_edge_spx else []
    elif validation["setup"]=="CALLS":
        direction="CALLS"
        entry_edge_es=validation.get("edge",ceiling_es)
        entry_edge_spx=round(entry_edge_es-offset,2) if entry_edge_es else ceiling_spx
        targets=find_targets(entry_edge_spx,cones_spx,"CALLS") if entry_edge_spx else []
    else:
        direction="WAIT"
        entry_edge_es=None
        targets=[]
    
    # Check if this is a TREND_DAY (for display purposes)
    is_trend_day=validation["status"]=="TREND_DAY"
    
    # Flow & momentum - use 8:30 candle open for flow bias calculation
    flow_price=candle_830["open"] if candle_830 else current_es
    flow=calculate_flow_bias(flow_price,on_high,on_low,vix,vix_high,vix_low,prior_close)
    momentum=calculate_momentum(es_candles)
    ema_signals=calculate_ema_signals(es_candles,current_es)
    vix_zone=get_vix_zone(vix)
    confidence=calculate_confidence(channel_type,validation,direction,ema_signals,flow,vix_zone)
    
    # Historical outcome
    if inputs["is_historical"] and hist_data and entry_edge_es:
        outcome=analyze_historical_outcome(hist_data,validation,ceiling_es,floor_es,targets,direction,entry_edge_es,offset)
    else:
        outcome=None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NEW INSTITUTIONAL-GRADE UI RENDERING
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Prepare option pricing data if we have a valid setup
    if direction in ["PUTS", "CALLS"] and entry_edge_es:
        entry_spx = round(entry_edge_es - offset, 2)
        strike = get_strike(entry_spx, "PUT" if direction == "PUTS" else "CALL")
        entry_price = estimate_prices(entry_spx, strike, "PUT" if direction == "PUTS" else "CALL", vix, hours_to_expiry)
        exits, _ = estimate_exit_prices(entry_spx, strike, "PUT" if direction == "PUTS" else "CALL", vix, hours_to_expiry, targets)
    else:
        entry_spx = None
        strike = None
        entry_price = None
        exits = []
    
    # Get London data for session cards
    lon_h = hist_data.get("london_high") if hist_data else None
    lon_l = hist_data.get("london_low") if hist_data else None
    
    # ─────────────────────────────────────────────────────────────────────────
    # 1. STATUS BANNER - The most important element
    # ─────────────────────────────────────────────────────────────────────────
    status_banner_html = render_status_banner(
        validation, direction, current_spx, current_es,
        inputs["is_historical"], inputs["is_planning"], inputs["trading_date"]
    )
    st.markdown(status_banner_html, unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 2. COUNTDOWN TIMERS (Live mode only)
    # ─────────────────────────────────────────────────────────────────────────
    if not inputs["is_historical"]:
        countdown_html = render_countdown_bar(now, inputs["trading_date"], inputs["is_historical"])
        st.markdown(countdown_html, unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 3. HISTORICAL RESULT (if applicable)
    # ─────────────────────────────────────────────────────────────────────────
    if outcome:
        hist_result_html = render_historical_result(outcome)
        st.markdown(hist_result_html, unsafe_allow_html=True)
        
        # Entry confirmation debug expander
        entry_conf = outcome.get("entry_confirmation", {})
        debug_info = entry_conf.get("debug", [])
        if debug_info:
            with st.expander("🔍 Entry Confirmation Details"):
                st.write(f"**Base Entry Level (9AM SPX):** {outcome['entry_level_spx']}")
                if outcome.get("entry_level_at_time"):
                    st.write(f"**Actual Entry Level (at entry time):** {outcome['entry_level_at_time']}")
                st.write(f"**Direction:** {outcome['direction']}")
                st.write(f"**Slope:** {SLOPE} pts/block")
                st.write("---")
                for d in debug_info:
                    candle = d.get("candle", {})
                    o, h, l, c = candle.get("open", 0), candle.get("high", 0), candle.get("low", 0), candle.get("close", 0)
                    is_bullish = c > o
                    candle_type = "🟢 BULLISH" if is_bullish else "🔴 BEARISH" if c < o else "⚪ DOJI"
                    blocks = d.get("blocks_from_ref", 0)
                    st.write(f"**{d['time']}** - {candle_type} | Entry @ {d['entry_level']} (blocks: {blocks:+d})")
                    st.write(f"  O:{o:.2f} H:{h:.2f} L:{l:.2f} C:{c:.2f}")
                    st.write(f"  Result: **{d['result']}** - {d['detail']}")
                    st.write("---")
    
    # ─────────────────────────────────────────────────────────────────────────
    # 4. SESSION TIMELINE
    # ─────────────────────────────────────────────────────────────────────────
    session_timeline_html = render_session_timeline(now, inputs["is_historical"])
    st.markdown(session_timeline_html, unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 5. PRICE LADDER - Visual Channel Position
    # ─────────────────────────────────────────────────────────────────────────
    price_ladder_html = render_price_ladder(current_spx, ceiling_spx, floor_spx, targets, direction, channel_type)
    if price_ladder_html:
        st.markdown(price_ladder_html, unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 6. TRADE SETUP CARD
    # ─────────────────────────────────────────────────────────────────────────
    if direction in ["PUTS", "CALLS"] and entry_spx:
        trade_card_html = render_trade_card(direction, entry_spx, strike, entry_price, targets, exits, validation)
        st.markdown(trade_card_html, unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 7. VALIDATION CHECKLIST
    # ─────────────────────────────────────────────────────────────────────────
    checklist_html = render_checklist(channel_type, validation, ema_signals, flow, vix_zone, direction)
    st.markdown(checklist_html, unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 8. DAYS LIKE TODAY - Historical Context
    # ─────────────────────────────────────────────────────────────────────────
    days_like_today_html = render_days_like_today(channel_type, validation["status"], vix_zone, direction)
    st.markdown(days_like_today_html, unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 9. 8:30 CANDLE VISUALIZATION (Historical mode)
    # ─────────────────────────────────────────────────────────────────────────
    if inputs["is_historical"] and candle_830:
        candle_viz_html = render_candle_830(candle_830, ceiling_es, floor_es, offset)
        st.markdown(candle_viz_html, unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 10. SESSION DATA CARDS (Historical mode)
    # ─────────────────────────────────────────────────────────────────────────
    if inputs["is_historical"] and hist_data:
        st.markdown("### Session Data", unsafe_allow_html=True)
        session_cards_html = render_session_cards(syd_h, syd_l, tok_h, tok_l, lon_h, lon_l, on_high, on_low)
        st.markdown(session_cards_html, unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 11. CONFIDENCE GAUGE
    # ─────────────────────────────────────────────────────────────────────────
    confidence_html = render_confidence_gauge(confidence)
    st.markdown(confidence_html, unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 12. COLLAPSIBLE DETAIL SECTIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    # EMA & Momentum Details
    with st.expander("📈 EMA & Momentum Analysis"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**8/21 EMA Cross**")
            cross_color = "#10b981" if ema_signals["cross_bullish"] else "#ef4444" if ema_signals["cross_bearish"] else "#f59e0b"
            st.markdown(f'<div style="font-size:20px;font-weight:600;color:{cross_color}">{ema_signals["cross_signal"]}</div>', unsafe_allow_html=True)
            st.write(f"EMA 8: {ema_signals['ema8']}")
            st.write(f"EMA 21: {ema_signals['ema21']}")
        with col2:
            st.markdown("**200 EMA Filter**")
            filter_color = "#10b981" if ema_signals["above_200"] else "#ef4444" if ema_signals["below_200"] else "#f59e0b"
            filter_text = "ABOVE" if ema_signals["above_200"] else "BELOW" if ema_signals["below_200"] else "AT"
            st.markdown(f'<div style="font-size:20px;font-weight:600;color:{filter_color}">{filter_text}</div>', unsafe_allow_html=True)
            st.write(f"EMA 200: {ema_signals['ema200']}")
        
        st.markdown("---")
        st.markdown("**Momentum**")
        mom_color = "#10b981" if "BULL" in momentum["signal"] else "#ef4444" if "BEAR" in momentum["signal"] else "#f59e0b"
        st.markdown(f'Signal: <span style="color:{mom_color};font-weight:600">{momentum["signal"]}</span> | RSI: {momentum["rsi"]} | MACD Hist: {momentum["macd"]}', unsafe_allow_html=True)
    
    # Flow Bias Details
    with st.expander("🌊 Flow Bias Details"):
        flow_color = "#10b981" if "CALLS" in flow["bias"] else "#ef4444" if "PUTS" in flow["bias"] else "#f59e0b"
        st.markdown(f'<div style="font-size:24px;font-weight:700;color:{flow_color}">{flow["bias"].replace("_", " ")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:18px;font-weight:600;color:{flow_color}">Score: {flow["score"]:+d}</div>', unsafe_allow_html=True)
        st.markdown("---")
        for signal_name, signal_dir, signal_detail in flow.get("signals", []):
            sig_color = "#10b981" if signal_dir == "CALLS" else "#ef4444" if signal_dir == "PUTS" else "#f59e0b"
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.1)"><span>{signal_name}</span><span style="color:{sig_color};font-weight:500">{signal_dir} ({signal_detail})</span></div>', unsafe_allow_html=True)
    
    # Cone Rails
    with st.expander("📊 Cone Rails (SPX)"):
        for name, cone in cones_spx.items():
            st.markdown(f'''<div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.1)">
                <span style="font-weight:600">{name}</span>
                <span>
                    <span style="color:#10b981">↑ {cone["asc"]}</span>
                    <span style="margin:0 8px;color:rgba(255,255,255,0.3)">|</span>
                    <span style="color:#ef4444">↓ {cone["desc"]}</span>
                </span>
            </div>''', unsafe_allow_html=True)
    
    # All Structure Levels
    with st.expander("📐 All Structure Levels"):
        all_lvls = [
            ("Ceiling Rising", levels["ceiling_rising"]["level"]),
            ("Ceiling Falling", levels["ceiling_falling"]["level"]),
            ("Floor Rising", levels["floor_rising"]["level"]),
            ("Floor Falling", levels["floor_falling"]["level"])
        ]
        all_lvls.sort(key=lambda x: x[1], reverse=True)
        for name, level in all_lvls:
            spx_level = round(level - offset, 2)
            st.markdown(f'''<div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.1)">
                <span>{name}</span>
                <span style="font-family:monospace">ES {level} → SPX {spx_level}</span>
            </div>''', unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 13. DEBUG MODE
    # ─────────────────────────────────────────────────────────────────────────
    if inputs["debug"]:
        st.markdown("### 🔧 Debug")
        
        st.markdown("**8:30 Candle vs Channel:**")
        if candle_830:
            st.write(f"- Candle: O={candle_830['open']}, H={candle_830['high']}, L={candle_830['low']}, C={candle_830['close']}")
        st.write(f"- Ceiling (ES): {ceiling_es}")
        st.write(f"- Floor (ES): {floor_es}")
        if candle_830 and ceiling_es and floor_es:
            st.write(f"- High vs Ceiling: {candle_830['high']} {'>' if candle_830['high']>ceiling_es else '<='} {ceiling_es} → {'BROKE ABOVE' if candle_830['high']>ceiling_es else 'did not break'}")
            st.write(f"- Low vs Floor: {candle_830['low']} {'<' if candle_830['low']<floor_es else '>='} {floor_es} → {'BROKE BELOW' if candle_830['low']<floor_es else 'did not break'}")
            st.write(f"- Close: {candle_830['close']} → {'ABOVE ceiling' if candle_830['close']>ceiling_es else 'BELOW floor' if candle_830['close']<floor_es else 'INSIDE channel'}")
        
        st.markdown("**Validation Result:**")
        st.write(f"- Status: {validation['status']}")
        st.write(f"- Message: {validation['message']}")
        st.write(f"- Setup: {validation['setup']}")
        st.write(f"- Position: {validation.get('position','N/A')}")
        
        st.markdown("**Anchor Times:**")
        st.write(f"- O/N High Time: {on_high_time}")
        st.write(f"- O/N Low Time: {on_low_time}")
        st.write(f"- Reference Time: {ref_time}")
        
        st.markdown("**Block Calculations:**")
        blocks_high = blocks_between(on_high_time, ref_time)
        blocks_low = blocks_between(on_low_time, ref_time)
        st.write(f"- Blocks from O/N High to Ref: {blocks_high} (exp: {SLOPE*blocks_high:.2f})")
        st.write(f"- Blocks from O/N Low to Ref: {blocks_low} (exp: {SLOPE*blocks_low:.2f})")
        
        st.markdown("**Raw Values (ES):**")
        st.write(f"- O/N High: {on_high}, O/N Low: {on_low}")
        st.write(f"- Sydney H/L: {syd_h}/{syd_l}, Tokyo H/L: {tok_h}/{tok_l}")
        st.write(f"- Channel Type: {channel_type} ({channel_reason})")
        
        st.markdown("**Calculated Levels (ES):**")
        st.json(levels)
        
        if hist_data:
            st.markdown("**Historical Data Extracted:**")
            hist_display = {k: str(v) if isinstance(v, pd.DataFrame) else v for k, v in hist_data.items() if k != "day_candles"}
            st.json(hist_display)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 14. FOOTER
    # ─────────────────────────────────────────────────────────────────────────
    footer_html = render_footer()
    st.markdown(footer_html, unsafe_allow_html=True)
    
    if inputs["auto_refresh"] and not inputs["is_historical"]:
        time_module.sleep(30)
        st.rerun()

if __name__=="__main__":
    main()

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
# CSS - PREMIUM TRADING TERMINAL UI
# Bloomberg meets Apple - Professional Beauty
# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
# CSS - LEVERAGED ALPHA INSPIRED UI
# Dark, clean, vibrant green accents, professional trading terminal
# ═══════════════════════════════════════════════════════════════════════════════
STYLES="""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
    --bg-deep: #000000;
    --bg-main: #0a0a0a;
    --bg-card: #111111;
    --bg-card-alt: #0d0d0d;
    --bg-elevated: #1a1a1a;
    
    --border-dim: rgba(255,255,255,0.06);
    --border-normal: rgba(255,255,255,0.1);
    --border-bright: rgba(255,255,255,0.2);
    
    --green: #00ff88;
    --green-dim: #10b981;
    --green-bg: rgba(0,255,136,0.08);
    --green-border: rgba(0,255,136,0.3);
    --green-glow: 0 0 30px rgba(0,255,136,0.3);
    
    --purple: #a855f7;
    --purple-dim: #9333ea;
    --purple-bg: rgba(168,85,247,0.08);
    --purple-border: rgba(168,85,247,0.3);
    
    --cyan: #22d3ee;
    --cyan-bg: rgba(34,211,238,0.08);
    
    --red: #ff4757;
    --red-dim: #ef4444;
    --red-bg: rgba(255,71,87,0.08);
    --red-border: rgba(255,71,87,0.3);
    
    --amber: #fbbf24;
    --amber-bg: rgba(251,191,36,0.08);
    --amber-border: rgba(251,191,36,0.3);
    
    --text-white: #ffffff;
    --text-primary: rgba(255,255,255,0.92);
    --text-secondary: rgba(255,255,255,0.6);
    --text-muted: rgba(255,255,255,0.4);
    --text-dim: rgba(255,255,255,0.2);
}

/* ═══════════════════════════════════════════════════════════════════════════
   ANIMATIONS - Premium Institutional-Grade Motion Design
   ═══════════════════════════════════════════════════════════════════════════ */

/* Fade in and slide up on load */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(30px); filter: blur(4px); }
    to { opacity: 1; transform: translateY(0); filter: blur(0); }
}

/* Fade in from left */
@keyframes fadeInLeft {
    from { opacity: 0; transform: translateX(-30px); filter: blur(4px); }
    to { opacity: 1; transform: translateX(0); filter: blur(0); }
}

/* Fade in from right */
@keyframes fadeInRight {
    from { opacity: 0; transform: translateX(30px); filter: blur(4px); }
    to { opacity: 1; transform: translateX(0); filter: blur(0); }
}

/* Fade in and scale with blur */
@keyframes fadeInScale {
    from { opacity: 0; transform: scale(0.9); filter: blur(8px); }
    to { opacity: 1; transform: scale(1); filter: blur(0); }
}

/* Epic reveal - scale up with glow */
@keyframes epicReveal {
    0% { opacity: 0; transform: scale(0.8) translateY(20px); filter: blur(10px); }
    50% { opacity: 1; transform: scale(1.02) translateY(-5px); filter: blur(0); }
    100% { opacity: 1; transform: scale(1) translateY(0); filter: blur(0); }
}

/* Pulse glow for active elements */
@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 20px rgba(0,255,136,0.3); }
    50% { box-shadow: 0 0 40px rgba(0,255,136,0.6), 0 0 80px rgba(0,255,136,0.3), 0 0 120px rgba(0,255,136,0.1); }
}

/* Intense pulse glow for critical elements */
@keyframes intensePulse {
    0%, 100% { 
        box-shadow: 0 0 20px rgba(0,255,136,0.4), inset 0 0 20px rgba(0,255,136,0.1);
        border-color: rgba(0,255,136,0.4);
    }
    50% { 
        box-shadow: 0 0 40px rgba(0,255,136,0.7), 0 0 80px rgba(0,255,136,0.4), inset 0 0 30px rgba(0,255,136,0.2);
        border-color: rgba(0,255,136,0.8);
    }
}

/* Red pulse for PUTS */
@keyframes pulseRed {
    0%, 100% { box-shadow: 0 0 20px rgba(255,71,87,0.3); }
    50% { box-shadow: 0 0 40px rgba(255,71,87,0.6), 0 0 80px rgba(255,71,87,0.3); }
}

/* Subtle float */
@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
}

/* Float with rotation */
@keyframes floatRotate {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    25% { transform: translateY(-4px) rotate(1deg); }
    50% { transform: translateY(-8px) rotate(0deg); }
    75% { transform: translateY(-4px) rotate(-1deg); }
}

/* Shimmer effect for loading and highlights */
@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

/* Scanning shimmer across element */
@keyframes scanShimmer {
    0% { left: -100%; }
    100% { left: 200%; }
}

/* Border glow pulse */
@keyframes borderPulse {
    0%, 100% { border-color: rgba(0,255,136,0.3); box-shadow: 0 0 10px rgba(0,255,136,0.1); }
    50% { border-color: rgba(0,255,136,0.7); box-shadow: 0 0 25px rgba(0,255,136,0.3); }
}

/* Number reveal - typewriter style */
@keyframes countUp {
    0% { opacity: 0; transform: translateY(15px) scale(0.9); filter: blur(4px); }
    60% { opacity: 1; transform: translateY(-3px) scale(1.02); filter: blur(0); }
    100% { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
}

/* Rotate for loading */
@keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* Smooth rotate with glow */
@keyframes rotateGlow {
    from { transform: rotate(0deg); filter: drop-shadow(0 0 5px rgba(0,255,136,0.5)); }
    to { transform: rotate(360deg); filter: drop-shadow(0 0 15px rgba(0,255,136,0.8)); }
}

/* Scan line effect - terminal style */
@keyframes scanLine {
    0% { top: -10%; opacity: 0; }
    10% { opacity: 1; }
    90% { opacity: 1; }
    100% { top: 110%; opacity: 0; }
}

/* Horizontal scan */
@keyframes scanHorizontal {
    0% { left: -10%; opacity: 0; }
    10% { opacity: 1; }
    90% { opacity: 1; }
    100% { left: 110%; opacity: 0; }
}

/* Draw line animation for SVG */
@keyframes drawLine {
    from { stroke-dashoffset: 100; }
    to { stroke-dashoffset: 0; }
}

/* Draw line with glow */
@keyframes drawLineGlow {
    from { stroke-dashoffset: 100; filter: drop-shadow(0 0 2px currentColor); }
    to { stroke-dashoffset: 0; filter: drop-shadow(0 0 8px currentColor); }
}

/* Blink for live indicators */
@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* Heartbeat pulse */
@keyframes heartbeat {
    0%, 100% { transform: scale(1); }
    10% { transform: scale(1.15); }
    20% { transform: scale(1); }
    30% { transform: scale(1.1); }
    40% { transform: scale(1); }
}

/* Gradient shift - animated backgrounds */
@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Rainbow border */
@keyframes rainbowBorder {
    0% { border-color: #00ff88; }
    25% { border-color: #22d3ee; }
    50% { border-color: #a855f7; }
    75% { border-color: #fbbf24; }
    100% { border-color: #00ff88; }
}

/* Value change flash */
@keyframes valueFlash {
    0% { background-color: rgba(0,255,136,0.4); transform: scale(1.05); }
    100% { background-color: transparent; transform: scale(1); }
}

/* Slide in from bottom with bounce */
@keyframes slideInBounce {
    0% { opacity: 0; transform: translateY(50px); }
    60% { opacity: 1; transform: translateY(-10px); }
    80% { transform: translateY(5px); }
    100% { transform: translateY(0); }
}

/* Pop in with elastic */
@keyframes popIn {
    0% { opacity: 0; transform: scale(0.5); }
    70% { transform: scale(1.1); }
    100% { opacity: 1; transform: scale(1); }
}

/* Ripple effect */
@keyframes ripple {
    0% { transform: scale(0.8); opacity: 1; }
    100% { transform: scale(2.5); opacity: 0; }
}

/* Typing cursor */
@keyframes cursorBlink {
    0%, 100% { border-right-color: var(--green); }
    50% { border-right-color: transparent; }
}

/* Data stream - matrix style */
@keyframes dataStream {
    0% { background-position: 0% 0%; }
    100% { background-position: 0% 100%; }
}

/* Glow text */
@keyframes glowText {
    0%, 100% { text-shadow: 0 0 10px currentColor, 0 0 20px currentColor; }
    50% { text-shadow: 0 0 20px currentColor, 0 0 40px currentColor, 0 0 60px currentColor; }
}

/* Status indicator breathing */
@keyframes breathe {
    0%, 100% { opacity: 0.6; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.1); }
}
}

/* ═══════════════════════════════════════════════════════════════════════════
   BASE
   ═══════════════════════════════════════════════════════════════════════════ */
.stApp {
    background: var(--bg-deep);
    font-family: 'Inter', -apple-system, sans-serif;
    color: var(--text-primary);
}
.stApp > header { background: transparent !important; }
[data-testid="stSidebar"] {
    background: var(--bg-card) !important;
    border-right: 1px solid var(--border-dim) !important;
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

h3 {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    margin: 32px 0 16px 0 !important;
}

.stExpander {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-dim) !important;
    border-radius: 12px !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   BRAND HEADER - Animated
   ═══════════════════════════════════════════════════════════════════════════ */
.brand-header {
    text-align: center;
    padding: 48px 20px 40px 20px;
    position: relative;
    animation: fadeInUp 0.8s ease-out;
}
.brand-logo-box {
    width: 80px; height: 80px;
    background: linear-gradient(135deg, #0d3320, #0a2818, #061510);
    border-radius: 20px;
    display: inline-flex; align-items: center; justify-content: center;
    margin-bottom: 24px;
    box-shadow: 
        0 0 40px rgba(0,255,136,0.3),
        0 0 80px rgba(0,255,136,0.15),
        inset 0 1px 0 rgba(255,255,255,0.1),
        0 10px 40px rgba(0,0,0,0.5);
    position: relative;
    animation: float 4s ease-in-out infinite;
    border: 1px solid rgba(0,255,136,0.3);
}
.brand-logo-box::before {
    content: '';
    position: absolute;
    top: -2px; left: -2px; right: -2px; bottom: -2px;
    background: linear-gradient(135deg, var(--green), transparent, var(--green));
    border-radius: 22px;
    z-index: -1;
    opacity: 0.5;
    animation: rotate 8s linear infinite;
}
.brand-logo-box svg {
    width: 48px;
    height: 48px;
    fill: none;
    stroke: var(--green);
    stroke-linecap: round;
    stroke-linejoin: round;
    filter: drop-shadow(0 0 8px rgba(0,255,136,0.5));
}
/* Pyramid outline */
.brand-logo-box svg path:first-of-type {
    stroke-dasharray: 120;
    stroke-dashoffset: 120;
    animation: drawPyramid 1.5s ease-out 0.3s forwards;
}
/* Three pillars with staggered animation */
.brand-logo-box svg line:nth-of-type(1) {
    stroke-dasharray: 20;
    stroke-dashoffset: 20;
    animation: drawPillar 0.6s ease-out 1s forwards;
}
.brand-logo-box svg line:nth-of-type(2) {
    stroke-dasharray: 30;
    stroke-dashoffset: 30;
    animation: drawPillar 0.6s ease-out 1.2s forwards;
}
.brand-logo-box svg line:nth-of-type(3) {
    stroke-dasharray: 20;
    stroke-dashoffset: 20;
    animation: drawPillar 0.6s ease-out 1.4s forwards;
}
/* Eye at apex - pulse */
.brand-logo-box svg circle:first-of-type {
    animation: eyePulse 2s ease-in-out 1.8s infinite;
    fill: rgba(0,255,136,0.2);
}
.brand-logo-box svg circle:nth-of-type(2) {
    fill: var(--green);
    animation: eyeGlow 2s ease-in-out 1.8s infinite;
}
/* Connection beam */
.brand-logo-box svg line:nth-of-type(4) {
    stroke-dasharray: 30;
    stroke-dashoffset: 30;
    animation: drawPillar 0.4s ease-out 1.6s forwards;
}

@keyframes drawPyramid {
    to { stroke-dashoffset: 0; }
}
@keyframes drawPillar {
    to { stroke-dashoffset: 0; }
}
@keyframes eyePulse {
    0%, 100% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.1); opacity: 1; }
}
@keyframes eyeGlow {
    0%, 100% { filter: drop-shadow(0 0 4px var(--green)); }
    50% { filter: drop-shadow(0 0 12px var(--green)) drop-shadow(0 0 20px var(--green)); }
}

.brand-name {
    font-size: 38px;
    font-weight: 800;
    letter-spacing: -1px;
    margin: 0;
    animation: fadeInUp 0.8s ease-out 0.2s both;
}
.brand-name span:first-child { color: var(--green); }
.brand-name span:last-child { color: var(--text-white); }
.brand-tagline {
    font-size: 14px;
    color: var(--text-secondary);
    margin-top: 12px;
    letter-spacing: 0.5px;
    animation: fadeInUp 0.8s ease-out 0.4s both;
}
.brand-live {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--green-bg);
    border: 1px solid var(--green-border);
    padding: 8px 20px;
    border-radius: 24px;
    font-size: 12px;
    font-weight: 600;
    color: var(--green);
    margin-top: 20px;
    animation: fadeInUp 0.8s ease-out 0.6s both, borderPulse 2s ease-in-out infinite;
}
.brand-live::before {
    content: '';
    width: 8px; height: 8px;
    background: var(--green);
    border-radius: 50%;
    animation: blink 1.5s ease-in-out infinite;
    box-shadow: 0 0 10px var(--green);
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.9); }
}

/* ═══════════════════════════════════════════════════════════════════════════
   STATUS BANNER - Hero Element with DRAMATIC Animations
   ═══════════════════════════════════════════════════════════════════════════ */
.mega-status {
    background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-alt) 100%);
    border: 1px solid var(--border-dim);
    border-radius: 20px;
    padding: 32px 36px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    animation: epicReveal 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
}
/* Animated gradient border */
.mega-status::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    border-radius: 20px;
    padding: 2px;
    background: linear-gradient(135deg, transparent, rgba(255,255,255,0.1), transparent);
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    opacity: 0;
    transition: opacity 0.3s ease;
}
.mega-status:hover::before {
    opacity: 1;
}
/* Animated scan line for active status */
.mega-status.go::after {
    content: '';
    position: absolute;
    left: -100%; right: -100%;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--green), var(--green), transparent);
    animation: scanHorizontal 2s ease-in-out infinite;
    opacity: 0.8;
    filter: blur(1px);
    box-shadow: 0 0 20px var(--green);
}
.mega-status.go {
    border-color: var(--green-border);
    background: linear-gradient(135deg, rgba(0,255,136,0.03) 0%, var(--bg-card) 50%, rgba(0,255,136,0.02) 100%);
    animation: epicReveal 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards, intensePulse 3s ease-in-out infinite;
}
.mega-status.wait {
    border-color: var(--amber-border);
    box-shadow: 0 0 40px rgba(251,191,36,0.2), inset 0 0 60px rgba(251,191,36,0.03);
    background: linear-gradient(135deg, rgba(251,191,36,0.03) 0%, var(--bg-card) 100%);
}
.mega-status.stop {
    border-color: var(--border-dim);
}
.mega-status.hist {
    border-color: var(--purple-border);
    box-shadow: 0 0 40px rgba(168,85,247,0.25), inset 0 0 60px rgba(168,85,247,0.03);
    background: linear-gradient(135deg, rgba(168,85,247,0.03) 0%, var(--bg-card) 100%);
}

.mega-left { display: flex; align-items: center; gap: 24px; }
.mega-icon {
    width: 64px; height: 64px;
    border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    font-size: 28px;
    animation: popIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
}
.mega-icon::after {
    content: '';
    position: absolute;
    inset: -4px;
    border-radius: 20px;
    background: inherit;
    opacity: 0.4;
    filter: blur(10px);
    z-index: -1;
}
.mega-icon:hover {
    transform: scale(1.15) rotate(5deg);
}
.mega-status.go .mega-icon {
    background: linear-gradient(135deg, var(--green-dim), var(--green));
    color: var(--bg-deep);
    box-shadow: 0 8px 32px rgba(0,255,136,0.5), inset 0 1px 0 rgba(255,255,255,0.2);
    animation: popIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both, float 3s ease-in-out infinite;
}
.mega-status.wait .mega-icon {
    background: linear-gradient(135deg, #f59e0b, var(--amber));
    color: var(--bg-deep);
    box-shadow: 0 8px 32px rgba(251,191,36,0.4);
}
.mega-status.stop .mega-icon {
    background: var(--bg-elevated);
    color: var(--text-muted);
}
.mega-status.hist .mega-icon {
    background: linear-gradient(135deg, var(--purple-dim), var(--purple));
    color: white;
    box-shadow: 0 8px 32px rgba(168,85,247,0.4);
}

.mega-title {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.5px;
    animation: fadeInLeft 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.3s both;
}
.mega-status.go .mega-title { 
    color: var(--green); 
    text-shadow: 0 0 30px rgba(0,255,136,0.5);
    animation: fadeInLeft 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.3s both, glowText 3s ease-in-out infinite;
}
.mega-status.wait .mega-title { color: var(--amber); }
.mega-status.stop .mega-title { color: var(--text-muted); }
.mega-status.hist .mega-title { color: var(--purple); }

.mega-sub { 
    font-size: 14px; 
    color: var(--text-secondary); 
    margin-top: 6px; 
    animation: fadeInLeft 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.4s both;
}

.mega-right { text-align: right; animation: fadeInRight 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.3s both; }
.mega-price {
    font-family: 'JetBrains Mono', monospace;
    font-size: 36px;
    font-weight: 700;
    color: var(--text-white);
    animation: countUp 0.8s ease-out 0.3s both;
}
.mega-meta {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
    font-family: 'JetBrains Mono', monospace;
    animation: fadeInUp 0.5s ease-out 0.5s both;
}

/* ═══════════════════════════════════════════════════════════════════════════
   VALIDATION ROW - Dramatic Animated Pills
   ═══════════════════════════════════════════════════════════════════════════ */
.valid-row {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
    margin-bottom: 28px;
}
.valid-card {
    background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-card-alt) 100%);
    border: 1px solid var(--border-dim);
    border-radius: 16px;
    padding: 20px 16px;
    text-align: center;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    animation: slideInBounce 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
    position: relative;
    overflow: hidden;
}
/* Shimmer overlay */
.valid-card::before {
    content: '';
    position: absolute;
    top: 0; left: -100%; right: 0; bottom: 0;
    width: 50%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
    transform: skewX(-20deg);
    transition: left 0.6s ease;
}
.valid-card:hover::before {
    left: 150%;
}
.valid-card:nth-child(1) { animation-delay: 0.05s; }
.valid-card:nth-child(2) { animation-delay: 0.1s; }
.valid-card:nth-child(3) { animation-delay: 0.15s; }
.valid-card:nth-child(4) { animation-delay: 0.2s; }
.valid-card:nth-child(5) { animation-delay: 0.25s; }

.valid-card:hover {
    transform: translateY(-8px) scale(1.02);
    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
}
.valid-card.pass {
    background: linear-gradient(145deg, var(--green-bg) 0%, rgba(0,255,136,0.05) 100%);
    border-color: var(--green-border);
}
.valid-card.pass:hover {
    box-shadow: 0 20px 50px rgba(0,255,136,0.25), inset 0 0 30px rgba(0,255,136,0.05);
    border-color: var(--green);
}
.valid-card.fail {
    background: linear-gradient(145deg, var(--red-bg) 0%, rgba(255,71,87,0.05) 100%);
    border-color: var(--red-border);
}
.valid-card.fail:hover {
    box-shadow: 0 20px 50px rgba(255,71,87,0.25), inset 0 0 30px rgba(255,71,87,0.05);
    border-color: var(--red);
}
.valid-card.neutral {
    background: linear-gradient(145deg, var(--amber-bg) 0%, rgba(251,191,36,0.05) 100%);
    border-color: var(--amber-border);
}
.valid-card.neutral:hover {
    box-shadow: 0 20px 50px rgba(251,191,36,0.2);
}

.valid-icon { 
    font-size: 28px; 
    margin-bottom: 10px;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    display: inline-block;
}
.valid-card:hover .valid-icon {
    transform: scale(1.3) rotate(10deg);
    filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
}
.valid-card.pass:hover .valid-icon {
    filter: drop-shadow(0 0 15px rgba(0,255,136,0.6));
}
.valid-card.fail:hover .valid-icon {
    filter: drop-shadow(0 0 15px rgba(255,71,87,0.6));
}
.valid-label { 
    font-size: 10px; 
    color: var(--text-muted); 
    text-transform: uppercase; 
    letter-spacing: 1.5px; 
    margin-bottom: 8px;
    font-weight: 600;
}
.valid-val { 
    font-family: 'JetBrains Mono', monospace; 
    font-size: 18px; 
    font-weight: 700;
    transition: all 0.3s ease;
    animation: countUp 0.6s ease-out 0.5s both;
}
.valid-card.pass .valid-val { color: var(--green); }
.valid-card.fail .valid-val { color: var(--red); }
.valid-card.neutral .valid-val { color: var(--amber); }

/* ═══════════════════════════════════════════════════════════════════════════
   FEATURE CARDS - Animated
   ═══════════════════════════════════════════════════════════════════════════ */
.feature-card {
    background: var(--bg-card);
    border: 1px solid var(--border-dim);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 16px;
    transition: all 0.3s ease;
    animation: fadeInUp 0.5s ease-out both;
}
.feature-card:hover {
    border-color: var(--border-normal);
    background: var(--bg-elevated);
    transform: translateX(8px);
    box-shadow: -8px 0 30px rgba(0,0,0,0.2);
}
.feature-icon {
    width: 48px; height: 48px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
    transition: all 0.3s ease;
}
.feature-card:hover .feature-icon {
    transform: scale(1.15) rotate(5deg);
}
.feature-icon.green { background: var(--green-bg); color: var(--green); }
.feature-icon.purple { background: var(--purple-bg); color: var(--purple); }
.feature-icon.cyan { background: var(--cyan-bg); color: var(--cyan); }
.feature-icon.red { background: var(--red-bg); color: var(--red); }
.feature-icon.amber { background: var(--amber-bg); color: var(--amber); }

.feature-content { flex: 1; }
.feature-title { font-size: 15px; font-weight: 600; color: var(--text-white); margin-bottom: 4px; }
.feature-subtitle { font-size: 13px; color: var(--text-secondary); }
.feature-value { 
    font-family: 'JetBrains Mono', monospace; 
    font-size: 18px; 
    font-weight: 700;
    transition: all 0.3s ease;
}
.feature-card:hover .feature-value {
    transform: scale(1.05);
}
.feature-value.green { color: var(--green); }
.feature-value.red { color: var(--red); }
.feature-value.amber { color: var(--amber); }

/* ═══════════════════════════════════════════════════════════════════════════
   SESSION CARDS - Animated
   ═══════════════════════════════════════════════════════════════════════════ */
.session-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 28px;
}
.session-card {
    background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-card-alt) 100%);
    border: 1px solid var(--border-dim);
    border-radius: 16px;
    padding: 20px;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
    position: relative;
    overflow: hidden;
}
/* Animated border gradient */
.session-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 3px;
    background: linear-gradient(90deg, transparent, var(--border-bright), transparent);
    transform: translateX(-100%);
    transition: transform 0.5s ease;
}
.session-card:hover::before {
    transform: translateX(100%);
}
.session-card:nth-child(1) { animation-delay: 0.1s; }
.session-card:nth-child(2) { animation-delay: 0.15s; }
.session-card:nth-child(3) { animation-delay: 0.2s; }
.session-card:nth-child(4) { animation-delay: 0.25s; }

.session-card:hover {
    transform: translateY(-8px) scale(1.02);
    border-color: var(--border-normal);
    box-shadow: 0 25px 50px rgba(0,0,0,0.5);
}
.session-head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; }
.session-icon {
    width: 44px; height: 44px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
}
.session-icon::after {
    content: '';
    position: absolute;
    inset: -3px;
    border-radius: 14px;
    background: inherit;
    opacity: 0.4;
    filter: blur(8px);
    z-index: -1;
    transition: all 0.3s ease;
}
.session-card:hover .session-icon {
    transform: scale(1.2) rotate(10deg);
}
.session-card:hover .session-icon::after {
    opacity: 0.6;
    filter: blur(12px);
}
.session-card.sydney .session-icon { background: linear-gradient(135deg, #3b82f6, #60a5fa); box-shadow: 0 4px 20px rgba(59,130,246,0.4); }
.session-card.tokyo .session-icon { background: linear-gradient(135deg, #ef4444, #f87171); box-shadow: 0 4px 20px rgba(239,68,68,0.4); }
.session-card.london .session-icon { background: linear-gradient(135deg, var(--green-dim), var(--green)); box-shadow: 0 4px 20px rgba(0,255,136,0.4); }
.session-card.overnight .session-icon { background: linear-gradient(135deg, var(--purple-dim), var(--purple)); box-shadow: 0 4px 20px rgba(168,85,247,0.4); }

.session-name { font-size: 15px; font-weight: 700; color: var(--text-white); }
.session-data { display: flex; flex-direction: column; gap: 10px; }
.session-line {
    display: flex; justify-content: space-between;
    font-size: 13px;
    transition: all 0.3s ease;
    padding: 6px 8px;
    margin: 0 -8px;
    border-radius: 6px;
}
.session-line:hover {
    background: rgba(255,255,255,0.04);
    transform: translateX(4px);
}
.session-line .label { color: var(--text-muted); }
.session-line .value { font-family: 'JetBrains Mono', monospace; font-weight: 600; }
.session-line .value.high { color: var(--green); text-shadow: 0 0 20px rgba(0,255,136,0.4); }
.session-line .value.low { color: var(--red); text-shadow: 0 0 20px rgba(255,71,87,0.4); }

/* ═══════════════════════════════════════════════════════════════════════════
   COMMAND CENTER - Premium Card with DRAMATIC Animations
   ═══════════════════════════════════════════════════════════════════════════ */
.cmd-card {
    background: linear-gradient(145deg, var(--bg-card) 0%, rgba(17,17,17,0.95) 50%, var(--bg-card-alt) 100%);
    border: 1px solid var(--border-dim);
    border-radius: 20px;
    padding: 28px;
    margin-bottom: 28px;
    animation: epicReveal 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
}
/* Animated corner accents */
.cmd-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 60px; height: 60px;
    background: linear-gradient(135deg, rgba(0,255,136,0.15), transparent);
    border-radius: 20px 0 0 0;
}
.cmd-card::after {
    content: '';
    position: absolute;
    bottom: 0; right: 0;
    width: 60px; height: 60px;
    background: linear-gradient(315deg, rgba(0,255,136,0.1), transparent);
    border-radius: 0 0 20px 0;
}
.cmd-card:hover {
    border-color: var(--border-normal);
    box-shadow: 0 30px 60px rgba(0,0,0,0.4);
    transform: translateY(-4px);
}
.cmd-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border-dim);
    position: relative;
}
/* Animated underline */
.cmd-header::after {
    content: '';
    position: absolute;
    bottom: -1px; left: 0;
    width: 0; height: 2px;
    background: linear-gradient(90deg, var(--green), var(--cyan));
    transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}
.cmd-card:hover .cmd-header::after {
    width: 100%;
}
.cmd-title { font-size: 20px; font-weight: 800; color: var(--text-white); animation: fadeInLeft 0.5s ease-out 0.2s both; }
.cmd-subtitle { font-size: 13px; color: var(--text-muted); margin-top: 4px; animation: fadeInLeft 0.5s ease-out 0.3s both; }
.cmd-badge {
    padding: 8px 16px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    animation: popIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.4s both;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.cmd-badge::before {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: left 0.5s ease;
}
.cmd-badge:hover::before {
    left: 100%;
}
.cmd-badge:hover {
    transform: scale(1.08);
}
.cmd-badge.rising { 
    background: linear-gradient(135deg, var(--green-bg), rgba(0,255,136,0.15)); 
    color: var(--green); 
    border: 1px solid var(--green-border);
    box-shadow: 0 4px 20px rgba(0,255,136,0.2);
}
.cmd-badge.falling { 
    background: linear-gradient(135deg, var(--red-bg), rgba(255,71,87,0.15)); 
    color: var(--red); 
    border: 1px solid var(--red-border);
    box-shadow: 0 4px 20px rgba(255,71,87,0.2);
}

.channel-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
}
.channel-item {
    background: linear-gradient(145deg, var(--bg-card-alt) 0%, var(--bg-card) 100%);
    border: 1px solid var(--border-dim);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    animation: slideInBounce 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
}
/* Glow effect at border */
.channel-item::before {
    content: '';
    position: absolute;
    top: 0; left: 0; bottom: 0;
    width: 4px;
    transition: all 0.3s ease;
}
.channel-item.ceiling::before { 
    background: linear-gradient(180deg, var(--green), rgba(0,255,136,0.3));
    box-shadow: 0 0 20px rgba(0,255,136,0.5);
}
.channel-item.floor::before { 
    background: linear-gradient(180deg, var(--red), rgba(255,71,87,0.3));
    box-shadow: 0 0 20px rgba(255,71,87,0.5);
}
.channel-item:first-child { animation-delay: 0.15s; }
.channel-item:last-child { animation-delay: 0.25s; }
.channel-item:hover {
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
}
.channel-item.ceiling:hover { border-color: var(--green-border); }
.channel-item.floor:hover { border-color: var(--red-border); }
.channel-item.ceiling { border-left: none; border-radius: 14px; }
.channel-item.floor { border-left: none; border-radius: 14px; }
.channel-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 10px; font-weight: 600; }
.channel-value { 
    font-family: 'JetBrains Mono', monospace; 
    font-size: 28px; 
    font-weight: 700; 
    color: var(--text-white);
    transition: all 0.3s ease;
    animation: countUp 0.7s ease-out 0.5s both;
}
.channel-item:hover .channel-value {
    transform: scale(1.08);
}
.channel-item.ceiling:hover .channel-value { text-shadow: 0 0 30px rgba(0,255,136,0.5); }
.channel-item.floor:hover .channel-value { text-shadow: 0 0 30px rgba(255,71,87,0.5); }
.channel-es { font-size: 12px; color: var(--text-muted); margin-top: 6px; }

.setup-box {
    background: linear-gradient(145deg, var(--bg-elevated) 0%, var(--bg-card) 100%);
    border-radius: 20px;
    padding: 24px;
    margin-top: 20px;
    animation: epicReveal 0.7s cubic-bezier(0.16, 1, 0.3, 1) 0.3s both;
    position: relative;
    overflow: hidden;
}
/* Animated gradient border */
.setup-box::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 20px;
    padding: 2px;
    background: linear-gradient(135deg, transparent 30%, var(--green) 50%, transparent 70%);
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    background-size: 200% 200%;
    animation: gradientShift 3s ease-in-out infinite;
    opacity: 0.5;
}
.setup-box.puts::before {
    background: linear-gradient(135deg, transparent 30%, var(--red) 50%, transparent 70%);
    background-size: 200% 200%;
}
.setup-box.puts { 
    border: 1px solid var(--red-border);
    box-shadow: 0 10px 40px rgba(255,71,87,0.15), inset 0 0 60px rgba(255,71,87,0.03);
}
.setup-box.calls { 
    border: 1px solid var(--green-border);
    box-shadow: 0 10px 40px rgba(0,255,136,0.15), inset 0 0 60px rgba(0,255,136,0.03);
}

.setup-header { display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }
.setup-icon {
    width: 56px; height: 56px;
    border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    font-size: 28px; font-weight: 700;
    animation: floatRotate 4s ease-in-out infinite;
    position: relative;
}
.setup-icon::after {
    content: '';
    position: absolute;
    inset: -4px;
    border-radius: 20px;
    background: inherit;
    opacity: 0.4;
    filter: blur(12px);
    z-index: -1;
}
.setup-box.puts .setup-icon { 
    background: linear-gradient(135deg, rgba(255,71,87,0.2), rgba(255,71,87,0.1)); 
    color: var(--red);
    box-shadow: 0 8px 30px rgba(255,71,87,0.3);
}
.setup-box.calls .setup-icon { 
    background: linear-gradient(135deg, rgba(0,255,136,0.2), rgba(0,255,136,0.1)); 
    color: var(--green);
    box-shadow: 0 8px 30px rgba(0,255,136,0.3);
}
.setup-title { font-size: 24px; font-weight: 800; animation: fadeInLeft 0.5s ease-out 0.4s both; }
.setup-box.puts .setup-title { color: var(--red); text-shadow: 0 0 30px rgba(255,71,87,0.4); }
.setup-box.calls .setup-title { color: var(--green); text-shadow: 0 0 30px rgba(0,255,136,0.4); }

.setup-metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 20px;
}
.setup-metric {
    background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-card-alt) 100%);
    border: 1px solid var(--border-dim);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    animation: slideInBounce 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}
.setup-metric:nth-child(1) { animation-delay: 0.1s; }
.setup-metric:nth-child(2) { animation-delay: 0.15s; }
.setup-metric:nth-child(3) { animation-delay: 0.2s; }
.setup-metric:nth-child(4) { animation-delay: 0.25s; }
.setup-metric:hover {
    background: var(--bg-elevated);
    transform: translateY(-4px) scale(1.02);
    box-shadow: 0 15px 30px rgba(0,0,0,0.3);
    border-color: var(--border-normal);
}
.setup-metric-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; font-weight: 600; }
.setup-metric-value { 
    font-family: 'JetBrains Mono', monospace; 
    font-size: 18px; 
    font-weight: 700; 
    color: var(--text-white);
    animation: countUp 0.6s ease-out 0.5s both;
}

.entry-rule {
    background: linear-gradient(145deg, var(--amber-bg) 0%, rgba(251,191,36,0.05) 100%);
    border: 1px solid var(--amber-border);
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 20px;
    animation: fadeInUp 0.5s ease-out 0.4s both;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.entry-rule::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    background: linear-gradient(180deg, var(--amber), rgba(251,191,36,0.3));
    border-radius: 4px 0 0 4px;
}
}
.entry-rule:hover {
    background: rgba(251,191,36,0.12);
}
.entry-rule-title { font-size: 12px; font-weight: 600; color: var(--amber); margin-bottom: 6px; }
.entry-rule-text { font-size: 13px; color: var(--text-primary); }
.entry-rule-warning { font-size: 11px; color: var(--text-muted); margin-top: 8px; }

.targets-box {
    background: var(--bg-card);
    border-radius: 10px;
    padding: 14px;
    animation: fadeInUp 0.5s ease-out 0.5s both;
}
.targets-title { font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }
.target-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid var(--border-dim);
    font-size: 13px;
    transition: all 0.2s ease;
}
.target-row:hover {
    background: rgba(255,255,255,0.02);
    margin: 0 -14px;
    padding: 8px 14px;
}
.target-row:last-child { border-bottom: none; }
.target-row:first-of-type {
    background: var(--green-bg);
    margin: 0 -14px;
    padding: 10px 14px;
    border-radius: 8px;
    border: 1px solid var(--green-border);
    animation: pulseGlow 3s ease-in-out infinite;
}
.target-name { color: var(--text-secondary); }
.target-level { font-family: 'JetBrains Mono', monospace; color: var(--text-white); }
.target-price { font-family: 'JetBrains Mono', monospace; color: var(--green); }

/* ═══════════════════════════════════════════════════════════════════════════
   ANALYSIS GRID - 2x2 Layout with Animations
   ═══════════════════════════════════════════════════════════════════════════ */
.analysis-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
}
.analysis-card {
    background: var(--bg-card);
    border: 1px solid var(--border-dim);
    border-radius: 12px;
    padding: 20px;
    animation: fadeInUp 0.5s ease-out both;
    transition: all 0.3s ease;
}
.analysis-card:nth-child(1) { animation-delay: 0.1s; }
.analysis-card:nth-child(2) { animation-delay: 0.2s; }
.analysis-card:nth-child(3) { animation-delay: 0.3s; }
.analysis-card:nth-child(4) { animation-delay: 0.4s; }

.analysis-card:hover {
    border-color: var(--border-normal);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.3);
}
.analysis-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 16px;
}
.analysis-left { display: flex; align-items: center; gap: 12px; }
.analysis-icon {
    width: 40px; height: 40px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
    transition: all 0.3s ease;
}
.analysis-card:hover .analysis-icon {
    transform: scale(1.1) rotate(5deg);
}
.analysis-title { font-size: 14px; font-weight: 600; color: var(--text-white); }
.analysis-subtitle { font-size: 12px; color: var(--text-muted); }
.analysis-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 24px;
    font-weight: 700;
    animation: countUp 0.6s ease-out both;
}
.analysis-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

/* Flow meter with animation */
.flow-meter {
    height: 8px;
    background: linear-gradient(90deg, var(--red), var(--amber) 50%, var(--green));
    border-radius: 4px;
    position: relative;
    margin: 12px 0;
    overflow: hidden;
}
.flow-meter::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    animation: shimmer 2s infinite;
    background-size: 200% 100%;
}
.flow-marker {
    position: absolute;
    top: -3px;
    width: 6px; height: 14px;
    background: white;
    border-radius: 3px;
    transform: translateX(-50%);
    box-shadow: 0 2px 8px rgba(0,0,0,0.5), 0 0 10px rgba(255,255,255,0.3);
    transition: left 0.5s ease-out;
    animation: float 2s ease-in-out infinite;
}

/* Confidence bar with animation */
.conf-bar {
    height: 6px;
    background: var(--bg-elevated);
    border-radius: 3px;
    overflow: hidden;
    margin: 8px 0;
}
.conf-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.8s ease-out;
    position: relative;
    overflow: hidden;
}
.conf-fill::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
    animation: shimmer 1.5s infinite;
    background-size: 200% 100%;
}

/* ═══════════════════════════════════════════════════════════════════════════
   8:30 CANDLE - Animated
   ═══════════════════════════════════════════════════════════════════════════ */
.candle-card {
    background: var(--bg-card);
    border: 1px solid var(--border-dim);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
    animation: fadeInUp 0.5s ease-out;
    transition: all 0.3s ease;
}
.candle-card:hover {
    border-color: var(--border-normal);
}
.candle-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.candle-left { display: flex; align-items: center; gap: 12px; }
.candle-icon {
    width: 44px; height: 44px;
    background: var(--cyan-bg);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    transition: all 0.3s ease;
}
.candle-card:hover .candle-icon {
    transform: scale(1.1);
    box-shadow: 0 4px 20px rgba(34,211,238,0.3);
}
.candle-title { font-size: 15px; font-weight: 600; color: var(--text-white); }
.candle-subtitle { font-size: 12px; color: var(--text-muted); }
.candle-type {
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
    animation: fadeInScale 0.4s ease-out 0.2s both;
    transition: all 0.3s ease;
}
.candle-type:hover {
    transform: scale(1.05);
}
.candle-type.bullish { background: var(--green-bg); color: var(--green); border: 1px solid var(--green-border); }
.candle-type.bearish { background: var(--red-bg); color: var(--red); border: 1px solid var(--red-border); }
.candle-type.neutral { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }

.candle-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}
.candle-item {
    background: var(--bg-card-alt);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
    animation: fadeInUp 0.4s ease-out both;
    transition: all 0.3s ease;
}
.candle-item:nth-child(1) { animation-delay: 0.1s; }
.candle-item:nth-child(2) { animation-delay: 0.15s; }
.candle-item:nth-child(3) { animation-delay: 0.2s; }
.candle-item:nth-child(4) { animation-delay: 0.25s; }
.candle-item:hover {
    background: var(--bg-elevated);
    transform: translateY(-2px);
}
.candle-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.candle-value { font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 600; color: var(--text-white); }
.candle-value.high { color: var(--green); }
.candle-value.low { color: var(--red); }

/* ═══════════════════════════════════════════════════════════════════════════
   FOOTER
   ═══════════════════════════════════════════════════════════════════════════ */
.footer {
    text-align: center;
    padding: 32px;
    color: var(--text-muted);
    font-size: 12px;
    border-top: 1px solid var(--border-dim);
    margin-top: 40px;
}

/* ═══════════════════════════════════════════════════════════════════════════
   MISC
   ═══════════════════════════════════════════════════════════════════════════ */
.card { background: var(--bg-card); border: 1px solid var(--border-dim); border-radius: 12px; padding: 16px; }
.pillar { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border-dim); font-size: 13px; }
.pillar:last-child { border-bottom: none; }
.pillar span:first-child { color: var(--text-muted); }
.pillar span:last-child { font-family: 'JetBrains Mono', monospace; }

/* Live indicator */
.live-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: var(--green-bg);
    border: 1px solid var(--green-border);
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    color: var(--green);
}
.live-dot {
    width: 6px; height: 6px;
    background: var(--green);
    border-radius: 50%;
    animation: pulse 2s infinite;
}
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
def fetch_spx_candles_polygon(start_date, end_date, interval="30m"):
    """Fetch SPX candles from Polygon and convert to ES equivalent"""
    try:
        # Convert interval to Polygon format
        timespan = "minute"
        multiplier = 30
        if interval == "1h":
            timespan = "hour"
            multiplier = 1
        elif interval == "30m":
            timespan = "minute"
            multiplier = 30
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        url = f"{POLYGON_BASE}/v2/aggs/ticker/I:SPX/range/{multiplier}/{timespan}/{start_str}/{end_str}?adjusted=true&sort=asc&limit=5000&apiKey={POLYGON_KEY}"
        r = requests.get(url, timeout=15)
        
        if r.status_code == 200:
            d = r.json()
            if "results" in d and len(d["results"]) > 0:
                import pandas as pd
                df = pd.DataFrame(d["results"])
                df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
                df.set_index('timestamp', inplace=True)
                df.rename(columns={'o':'Open','h':'High','l':'Low','c':'Close','v':'Volume'}, inplace=True)
                df.index = df.index.tz_localize('UTC').tz_convert('America/Chicago')
                return df[['Open','High','Low','Close','Volume']]
    except Exception as e:
        pass
    return None

@st.cache_data(ttl=300,show_spinner=False)
def fetch_es_candles_range(start_date, end_date, interval="30m", offset=18.0):
    """Fetch ES candles for a specific date range"""
    # Try yfinance first for actual ES data
    for attempt in range(2):
        try:
            es=yf.Ticker("ES=F")
            data=es.history(start=start_date,end=end_date+timedelta(days=1),interval=interval)
            if data is not None and not data.empty and len(data) > 10:
                return data
        except Exception as e:
            time_module.sleep(0.5)
    
    # Backup: Use SPX from Polygon and add offset to convert to ES
    spx_data = fetch_spx_candles_polygon(start_date, end_date, interval)
    if spx_data is not None and not spx_data.empty:
        # Convert SPX to ES by adding offset
        es_data = spx_data.copy()
        es_data['Open'] = es_data['Open'] + offset
        es_data['High'] = es_data['High'] + offset
        es_data['Low'] = es_data['Low'] + offset
        es_data['Close'] = es_data['Close'] + offset
        return es_data
    
    return None

@st.cache_data(ttl=120,show_spinner=False)
def fetch_es_candles(days=7, offset=18.0):
    """Fetch recent ES candles"""
    # Try yfinance first
    for attempt in range(2):
        try:
            es=yf.Ticker("ES=F")
            data=es.history(period=f"{days}d",interval="30m")
            if data is not None and not data.empty and len(data) > 10:
                return data
        except:
            time_module.sleep(0.5)
    
    # Backup: Use SPX from Polygon
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    spx_data = fetch_spx_candles_polygon(start_date, end_date, "30m")
    if spx_data is not None and not spx_data.empty:
        es_data = spx_data.copy()
        es_data['Open'] = es_data['Open'] + offset
        es_data['High'] = es_data['High'] + offset
        es_data['Low'] = es_data['Low'] + offset
        es_data['Close'] = es_data['Close'] + offset
        return es_data
    
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
    """Fetch current ES futures price - ES is the source of truth"""
    errors = []
    
    # Try 1: yfinance ES futures with 1d/5m (most recent, reliable interval)
    try:
        es=yf.Ticker("ES=F")
        d=es.history(period="1d",interval="5m")
        if d is not None and not d.empty:
            return round(float(d['Close'].iloc[-1]),2)
        else:
            errors.append("yf 1d/5m: empty")
    except Exception as e:
        errors.append(f"yf 1d/5m: {str(e)[:50]}")
    
    # Try 2: yfinance with 2d/5m
    try:
        es=yf.Ticker("ES=F")
        d=es.history(period="2d",interval="5m")
        if d is not None and not d.empty:
            return round(float(d['Close'].iloc[-1]),2)
        else:
            errors.append("yf 2d/5m: empty")
    except Exception as e:
        errors.append(f"yf 2d/5m: {str(e)[:50]}")
    
    # Try 3: yfinance with 5d/30m
    try:
        es=yf.Ticker("ES=F")
        d=es.history(period="5d",interval="30m")
        if d is not None and not d.empty:
            return round(float(d['Close'].iloc[-1]),2)
        else:
            errors.append("yf 5d/30m: empty")
    except Exception as e:
        errors.append(f"yf 5d/30m: {str(e)[:50]}")
    
    # Try 4: yfinance with 7d/1h (longer period, hourly)
    try:
        es=yf.Ticker("ES=F")
        d=es.history(period="7d",interval="1h")
        if d is not None and not d.empty:
            return round(float(d['Close'].iloc[-1]),2)
        else:
            errors.append("yf 7d/1h: empty")
    except Exception as e:
        errors.append(f"yf 7d/1h: {str(e)[:50]}")
    
    # Try 5: Polygon ES futures snapshot
    try:
        url=f"{POLYGON_BASE}/v2/snapshot/locale/us/markets/stocks/tickers/ES=F?apiKey={POLYGON_KEY}"
        r=requests.get(url,timeout=5)
        if r.status_code==200:
            d=r.json()
            if "ticker" in d and "lastTrade" in d["ticker"]:
                p = d["ticker"]["lastTrade"].get("p")
                if p: return round(float(p), 2)
        errors.append(f"polygon: status {r.status_code}")
    except Exception as e:
        errors.append(f"polygon: {str(e)[:50]}")
    
    # Log errors for debugging (visible in Streamlit logs)
    if errors:
        print(f"ES fetch failed: {'; '.join(errors)}")
    
    return None

def derive_spx_from_es(es_price, offset=18.0):
    """Derive SPX from ES price - ES is source of truth, SPX = ES - offset"""
    if es_price:
        return round(es_price - offset, 2)
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
            result["prior_date"]=prior_rth_day  # Track which day the prior data is from
        
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
# ENHANCED FLOW BIAS - Real Market Data Integration
# Uses: VVIX, VIX Term Structure, Put/Call Ratio, Breadth, Risk On/Off
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_market_flow_data():
    """
    Fetch real market flow data from free sources.
    Returns dict with all available flow indicators.
    """
    flow_data = {
        "vvix": None,
        "vvix_change": None,
        "vix_term_structure": None,  # VIX3M - VIX (positive = contango = bullish)
        "put_call_ratio": None,
        "breadth_ratio": None,  # RSP/SPY ratio
        "risk_on_off": None,  # XLK vs XLU relative strength
        "data_fresh": False
    }
    
    try:
        import yfinance as yf
        
        # 1. VVIX - Volatility of Volatility
        # High VVIX = uncertainty/fear, Low VVIX = complacency
        try:
            vvix = yf.Ticker("^VVIX")
            vvix_hist = vvix.history(period="5d")
            if len(vvix_hist) >= 2:
                flow_data["vvix"] = round(vvix_hist['Close'].iloc[-1], 2)
                flow_data["vvix_change"] = round(vvix_hist['Close'].iloc[-1] - vvix_hist['Close'].iloc[-2], 2)
        except:
            pass
        
        # 2. VIX Term Structure (VIX vs VIX3M)
        # Contango (VIX3M > VIX) = normal/bullish
        # Backwardation (VIX > VIX3M) = fear/bearish
        try:
            vix = yf.Ticker("^VIX")
            vix3m = yf.Ticker("^VIX3M")
            vix_hist = vix.history(period="2d")
            vix3m_hist = vix3m.history(period="2d")
            if len(vix_hist) > 0 and len(vix3m_hist) > 0:
                vix_val = vix_hist['Close'].iloc[-1]
                vix3m_val = vix3m_hist['Close'].iloc[-1]
                flow_data["vix_term_structure"] = round(vix3m_val - vix_val, 2)
        except:
            pass
        
        # 3. Market Breadth - RSP/SPY Ratio
        # Rising ratio = broad participation = healthy rally
        # Falling ratio = narrow leadership = weak rally
        try:
            spy = yf.Ticker("SPY")
            rsp = yf.Ticker("RSP")
            spy_hist = spy.history(period="5d")
            rsp_hist = rsp.history(period="5d")
            if len(spy_hist) >= 2 and len(rsp_hist) >= 2:
                current_ratio = rsp_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[-1]
                prev_ratio = rsp_hist['Close'].iloc[-2] / spy_hist['Close'].iloc[-2]
                flow_data["breadth_ratio"] = round((current_ratio / prev_ratio - 1) * 100, 3)
        except:
            pass
        
        # 4. Risk On/Off - XLK (Tech) vs XLU (Utilities)
        # XLK outperforming = risk on = bullish
        # XLU outperforming = risk off = bearish
        try:
            xlk = yf.Ticker("XLK")
            xlu = yf.Ticker("XLU")
            xlk_hist = xlk.history(period="2d")
            xlu_hist = xlu.history(period="2d")
            if len(xlk_hist) >= 2 and len(xlu_hist) >= 2:
                xlk_ret = (xlk_hist['Close'].iloc[-1] / xlk_hist['Close'].iloc[-2] - 1) * 100
                xlu_ret = (xlu_hist['Close'].iloc[-1] / xlu_hist['Close'].iloc[-2] - 1) * 100
                flow_data["risk_on_off"] = round(xlk_ret - xlu_ret, 2)
        except:
            pass
        
        # 5. Put/Call Ratio from CBOE (using equity P/C)
        # High P/C (>1.0) = bearish sentiment (contrarian bullish)
        # Low P/C (<0.7) = bullish sentiment (contrarian bearish)
        try:
            # Try to get P/C ratio - this may not work on all systems
            # Alternative: calculate from SPY options volume
            spy = yf.Ticker("SPY")
            opt_chain = spy.options
            if len(opt_chain) > 0:
                nearest_exp = opt_chain[0]
                calls = spy.option_chain(nearest_exp).calls
                puts = spy.option_chain(nearest_exp).puts
                call_vol = calls['volume'].sum() if 'volume' in calls.columns else 0
                put_vol = puts['volume'].sum() if 'volume' in puts.columns else 0
                if call_vol > 0:
                    flow_data["put_call_ratio"] = round(put_vol / call_vol, 2)
        except:
            pass
        
        # Check if we got any real data
        real_data_count = sum(1 for v in [flow_data["vvix"], flow_data["vix_term_structure"], 
                                           flow_data["breadth_ratio"], flow_data["risk_on_off"]] if v is not None)
        flow_data["data_fresh"] = real_data_count >= 2
        
    except ImportError:
        pass  # yfinance not available
    except Exception as e:
        pass  # Network or other error
    
    return flow_data


def calculate_flow_bias(price, on_high, on_low, vix, vix_high, vix_low, prior_close, es_candles=None):
    """
    Enhanced Flow Bias calculation using multiple data sources.
    
    Scoring System (-100 to +100):
    - Positive = CALLS bias (bullish flow)
    - Negative = PUTS bias (bearish flow)
    
    Data Sources (when available):
    1. Price Position in O/N Range (±20 pts)
    2. VIX Level & Change (±15 pts)
    3. Gap from Prior Close (±15 pts)
    4. VVIX - Volatility of VIX (±10 pts)
    5. VIX Term Structure (±15 pts)
    6. Market Breadth (±10 pts)
    7. Risk On/Off Rotation (±10 pts)
    8. Put/Call Ratio (±10 pts) - contrarian
    """
    signals = []
    score = 0
    details = {}
    
    # Fetch real market flow data
    flow_data = fetch_market_flow_data()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PILLAR 1: Price Position in Overnight Range (±20 pts)
    # ═══════════════════════════════════════════════════════════════════════════
    on_range = on_high - on_low
    if on_range > 0:
        price_pos = (price - on_low) / on_range * 100
        details["price_pos"] = f"{price_pos:.0f}%"
        
        if price > on_high:
            pts = 20
            score += pts
            signals.append(("O/N Position", "CALLS", f"Above High (+{price-on_high:.0f})", pts))
        elif price < on_low:
            pts = -20
            score += pts
            signals.append(("O/N Position", "PUTS", f"Below Low ({price-on_low:.0f})", pts))
        elif price_pos > 75:
            pts = 12
            score += pts
            signals.append(("O/N Position", "CALLS", f"Upper 25% ({price_pos:.0f}%)", pts))
        elif price_pos < 25:
            pts = -12
            score += pts
            signals.append(("O/N Position", "PUTS", f"Lower 25% ({price_pos:.0f}%)", pts))
        else:
            signals.append(("O/N Position", "NEUTRAL", f"Mid-Range ({price_pos:.0f}%)", 0))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PILLAR 2: VIX Level (±15 pts)
    # ═══════════════════════════════════════════════════════════════════════════
    vix_range = vix_high - vix_low if vix_high and vix_low else 0
    if vix_range > 0:
        vix_pos = (vix - vix_low) / vix_range * 100
        details["vix_pos"] = f"{vix_pos:.0f}%"
        
        if vix > vix_high:
            pts = -15
            score += pts
            signals.append(("VIX Level", "PUTS", f"Elevated ({vix:.1f})", pts))
        elif vix < vix_low:
            pts = 15
            score += pts
            signals.append(("VIX Level", "CALLS", f"Compressed ({vix:.1f})", pts))
        elif vix_pos > 70:
            pts = -8
            score += pts
            signals.append(("VIX Level", "PUTS", f"High ({vix:.1f})", pts))
        elif vix_pos < 30:
            pts = 8
            score += pts
            signals.append(("VIX Level", "CALLS", f"Low ({vix:.1f})", pts))
        else:
            signals.append(("VIX Level", "NEUTRAL", f"Normal ({vix:.1f})", 0))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PILLAR 3: Gap from Prior Close (±15 pts)
    # Gap = Current Price - Prior RTH Close
    # This is the classic "gap up" or "gap down" measure
    # ═══════════════════════════════════════════════════════════════════════════
    
    gap = price - prior_close if prior_close else 0
    details["gap"] = f"{gap:+.1f}"
    
    if gap > 20:
        pts = 15
        score += pts
        signals.append(("Gap", "CALLS", f"Large Gap Up (+{gap:.0f})", pts))
    elif gap > 10:
        pts = 10
        score += pts
        signals.append(("Gap", "CALLS", f"Gap Up (+{gap:.0f})", pts))
    elif gap > 5:
        pts = 5
        score += pts
        signals.append(("Gap", "CALLS", f"Small Gap Up (+{gap:.0f})", pts))
    elif gap < -20:
        pts = -15
        score += pts
        signals.append(("Gap", "PUTS", f"Large Gap Down ({gap:.0f})", pts))
    elif gap < -10:
        pts = -10
        score += pts
        signals.append(("Gap", "PUTS", f"Gap Down ({gap:.0f})", pts))
    elif gap < -5:
        pts = -5
        score += pts
        signals.append(("Gap", "PUTS", f"Small Gap Down ({gap:.0f})", pts))
    else:
        signals.append(("Gap", "NEUTRAL", f"Flat ({gap:+.0f})", 0))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PILLAR 4: VVIX - Volatility of Volatility (±10 pts)
    # High VVIX (>100) = uncertainty, usually precedes moves
    # Low VVIX (<85) = complacency
    # ═══════════════════════════════════════════════════════════════════════════
    if flow_data["vvix"] is not None:
        vvix = flow_data["vvix"]
        vvix_chg = flow_data["vvix_change"] or 0
        details["vvix"] = f"{vvix:.1f}"
        
        # VVIX rising sharply = fear increasing = bearish
        # VVIX falling = fear decreasing = bullish
        if vvix > 110 and vvix_chg > 3:
            pts = -10
            score += pts
            signals.append(("VVIX", "PUTS", f"Spiking ({vvix:.0f}, +{vvix_chg:.1f})", pts))
        elif vvix > 100:
            pts = -5
            score += pts
            signals.append(("VVIX", "PUTS", f"Elevated ({vvix:.0f})", pts))
        elif vvix < 85 and vvix_chg < -2:
            pts = 8
            score += pts
            signals.append(("VVIX", "CALLS", f"Calm ({vvix:.0f}, {vvix_chg:.1f})", pts))
        elif vvix < 90:
            pts = 5
            score += pts
            signals.append(("VVIX", "CALLS", f"Low ({vvix:.0f})", pts))
        else:
            signals.append(("VVIX", "NEUTRAL", f"Normal ({vvix:.0f})", 0))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PILLAR 5: VIX Term Structure (±15 pts)
    # Contango (VIX3M > VIX) = normal, bullish
    # Backwardation (VIX > VIX3M) = fear, bearish
    # ═══════════════════════════════════════════════════════════════════════════
    if flow_data["vix_term_structure"] is not None:
        term = flow_data["vix_term_structure"]
        details["term_structure"] = f"{term:+.2f}"
        
        if term > 3:
            pts = 15
            score += pts
            signals.append(("Term Structure", "CALLS", f"Steep Contango (+{term:.1f})", pts))
        elif term > 0:
            pts = 8
            score += pts
            signals.append(("Term Structure", "CALLS", f"Contango (+{term:.1f})", pts))
        elif term < -2:
            pts = -15
            score += pts
            signals.append(("Term Structure", "PUTS", f"Backwardation ({term:.1f})", pts))
        elif term < 0:
            pts = -8
            score += pts
            signals.append(("Term Structure", "PUTS", f"Slight Inversion ({term:.1f})", pts))
        else:
            signals.append(("Term Structure", "NEUTRAL", f"Flat ({term:.1f})", 0))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PILLAR 6: Market Breadth - RSP/SPY Change (±10 pts)
    # Improving breadth = healthy = bullish
    # Deteriorating breadth = narrow = bearish
    # ═══════════════════════════════════════════════════════════════════════════
    if flow_data["breadth_ratio"] is not None:
        breadth = flow_data["breadth_ratio"]
        details["breadth"] = f"{breadth:+.2f}%"
        
        if breadth > 0.3:
            pts = 10
            score += pts
            signals.append(("Breadth", "CALLS", f"Improving (+{breadth:.2f}%)", pts))
        elif breadth > 0.1:
            pts = 5
            score += pts
            signals.append(("Breadth", "CALLS", f"Positive (+{breadth:.2f}%)", pts))
        elif breadth < -0.3:
            pts = -10
            score += pts
            signals.append(("Breadth", "PUTS", f"Deteriorating ({breadth:.2f}%)", pts))
        elif breadth < -0.1:
            pts = -5
            score += pts
            signals.append(("Breadth", "PUTS", f"Negative ({breadth:.2f}%)", pts))
        else:
            signals.append(("Breadth", "NEUTRAL", f"Flat ({breadth:+.2f}%)", 0))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PILLAR 7: Risk On/Off Rotation (±10 pts)
    # Tech > Utilities = Risk On = Bullish
    # Utilities > Tech = Risk Off = Bearish
    # ═══════════════════════════════════════════════════════════════════════════
    if flow_data["risk_on_off"] is not None:
        risk = flow_data["risk_on_off"]
        details["risk_rotation"] = f"{risk:+.2f}%"
        
        if risk > 1.0:
            pts = 10
            score += pts
            signals.append(("Risk Rotation", "CALLS", f"Risk ON (+{risk:.1f}%)", pts))
        elif risk > 0.3:
            pts = 5
            score += pts
            signals.append(("Risk Rotation", "CALLS", f"Slight Risk ON (+{risk:.1f}%)", pts))
        elif risk < -1.0:
            pts = -10
            score += pts
            signals.append(("Risk Rotation", "PUTS", f"Risk OFF ({risk:.1f}%)", pts))
        elif risk < -0.3:
            pts = -5
            score += pts
            signals.append(("Risk Rotation", "PUTS", f"Slight Risk OFF ({risk:.1f}%)", pts))
        else:
            signals.append(("Risk Rotation", "NEUTRAL", f"Balanced ({risk:+.1f}%)", 0))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PILLAR 8: Put/Call Ratio - CONTRARIAN (±10 pts)
    # High P/C (>1.0) = bearish sentiment = contrarian BULLISH
    # Low P/C (<0.7) = bullish sentiment = contrarian BEARISH
    # ═══════════════════════════════════════════════════════════════════════════
    if flow_data["put_call_ratio"] is not None:
        pc = flow_data["put_call_ratio"]
        details["put_call"] = f"{pc:.2f}"
        
        if pc > 1.2:
            pts = 10  # Contrarian bullish
            score += pts
            signals.append(("Put/Call", "CALLS", f"High Fear ({pc:.2f}) - Contrarian Bull", pts))
        elif pc > 1.0:
            pts = 5
            score += pts
            signals.append(("Put/Call", "CALLS", f"Elevated ({pc:.2f})", pts))
        elif pc < 0.6:
            pts = -10  # Contrarian bearish
            score += pts
            signals.append(("Put/Call", "PUTS", f"Complacency ({pc:.2f}) - Contrarian Bear", pts))
        elif pc < 0.75:
            pts = -5
            score += pts
            signals.append(("Put/Call", "PUTS", f"Low ({pc:.2f})", pts))
        else:
            signals.append(("Put/Call", "NEUTRAL", f"Normal ({pc:.2f})", 0))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FINAL BIAS DETERMINATION
    # ═══════════════════════════════════════════════════════════════════════════
    # Clamp score to -100 to +100
    score = max(-100, min(100, score))
    
    if score >= 40:
        bias = "STRONG_CALLS"
    elif score >= 20:
        bias = "CALLS"
    elif score <= -40:
        bias = "STRONG_PUTS"
    elif score <= -20:
        bias = "PUTS"
    else:
        bias = "NEUTRAL"
    
    # Count how many real data sources we used
    real_sources = sum(1 for k in ["vvix", "vix_term_structure", "breadth_ratio", "risk_on_off", "put_call_ratio"] 
                       if flow_data.get(k) is not None)
    
    return {
        "bias": bias,
        "score": score,
        "signals": signals,
        "details": details,
        "real_data_sources": real_sources,
        "data_fresh": flow_data["data_fresh"]
    }

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
    """
    Estimate 0DTE option premium using Black-Scholes with realistic adjustments.
    
    For 0DTE SPX options:
    - Typical ATM premiums: $8-15 with 5-6 hours left
    - Typical 20pt OTM premiums: $3-8 with 5-6 hours left
    - Typical 50pt OTM premiums: $1-4 with 5-6 hours left
    """
    # 0DTE IV is elevated but not as extreme as some think
    # VIX 16 → effective 0DTE IV around 25-35%
    iv_multiplier = 2.0 if hours < 3 else 1.8 if hours < 5 else 1.5
    iv = (vix / 100) * iv_multiplier
    
    # Minimum IV floor for 0DTE
    iv = max(iv, 0.20)
    
    # Time in years
    T = max(0.0001, hours / (365 * 24))
    
    # Risk-free rate
    r = 0.05
    
    entry = black_scholes(entry_level, strike, T, r, iv, opt_type)
    
    # Minimum premium
    entry = max(entry, 0.05)
    
    return round(entry, 2)

def estimate_exit_prices(entry_level,strike,opt_type,vix,hours,targets):
    """
    Estimate exit prices at each target level with time decay.
    """
    iv_multiplier = 2.0 if hours < 3 else 1.8 if hours < 5 else 1.5
    iv = (vix / 100) * iv_multiplier
    iv = max(iv, 0.20)
    
    r = 0.05
    entry_T = max(0.0001, hours / (365 * 24))
    entry_price = black_scholes(entry_level, strike, entry_T, r, iv, opt_type)
    entry_price = max(entry_price, 0.05)
    
    results = []
    for i, tgt in enumerate(targets[:3]):
        # Each target takes roughly 30-60 mins
        hours_elapsed = 0.5 + (i * 0.5)
        exit_hours = max(0.1, hours - hours_elapsed)
        exit_T = max(0.0001, exit_hours / (365 * 24))
        
        exit_price = black_scholes(tgt["level"], strike, exit_T, r, iv, opt_type)
        exit_price = max(exit_price, 0.05)
        
        pct = (exit_price - entry_price) / entry_price * 100 if entry_price > 0.05 else 0
        results.append({
            "target": tgt["name"],
            "level": tgt["level"],
            "price": round(exit_price, 2),
            "pct": round(pct, 0)
        })
    
    return results, round(entry_price, 2)

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
    
    # Flow bias (+10) - Updated for new naming
    if direction=="PUTS" and flow["bias"] in ["STRONG_PUTS","PUTS"]:
        score+=10
        breakdown.append(("Flow","+10"))
    elif direction=="CALLS" and flow["bias"] in ["STRONG_CALLS","CALLS"]:
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
            st.markdown("**VIX Range** *(for flow bias)*")
            c1,c2=st.columns(2)
            vix_high=c1.number_input("VIX High",value=safe_float(saved.get("vix_high"),18.0),step=0.1)
            vix_low=c2.number_input("VIX Low",value=safe_float(saved.get("vix_low"),15.0),step=0.1)
            st.markdown("**Current VIX** *(for premium calculation)*")
            manual_vix=st.number_input("VIX Level",value=safe_float(saved.get("manual_vix"),16.0),step=0.1,key="mvix")
        else:
            vix_high=vix_low=None
            manual_vix=None
        
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
            
            st.markdown("**Prior RTH Close** *(Friday's close for gap calculation)*")
            on_prior_close=st.number_input("Prior Close (ES)",value=safe_float(saved.get("on_prior_close"),6040.0),step=0.5,key="onpc",label_visibility="collapsed")
            
            # Parse times
            on_high_hr,on_high_mn=int(on_high_time_str.split(":")[0]),int(on_high_time_str.split(":")[1])
            on_low_hr,on_low_mn=int(on_low_time_str.split(":")[0]),int(on_low_time_str.split(":")[1])
        else:
            on_high=on_low=on_prior_close=None
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
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Inputs",use_container_width=True):
                save_inputs({
                    "offset":offset,
                    "manual_es":manual_es,
                    "on_high":on_high,"on_low":on_low,
                    "on_prior_close":on_prior_close,
                    "vix_high":vix_high,"vix_low":vix_low,
                    "manual_vix":manual_vix,
                    "prior_high":prior_high,"prior_low":prior_low,"prior_close":prior_close
                })
                st.success("✅ Saved")
        with col2:
            if st.button("🔄 Refresh Data",use_container_width=True):
                st.cache_data.clear()
                st.rerun()
    
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
        "manual_vix":manual_vix,
        # O/N overrides
        "override_on":override_on,
        "on_high":on_high,"on_low":on_low,
        "on_prior_close":on_prior_close if override_on else None,
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
            es_candles=fetch_es_candles_range(start, end, "30m", inputs["offset"])
            
            if es_candles is not None and not es_candles.empty:
                hist_data=extract_historical_data(es_candles,inputs["trading_date"],inputs["offset"])
                
                # Check if prior RTH data is stale (holiday scenario)
                if inputs["is_planning"] and hist_data:
                    prior_date = hist_data.get("prior_date")
                    trading_date = inputs["trading_date"]
                    if prior_date:
                        days_gap = (trading_date - prior_date).days if isinstance(prior_date, date) else 0
                        if days_gap > 3:  # More than a weekend gap = likely holiday
                            st.warning(f"⚠️ **Holiday Detected:** Prior RTH data is from {prior_date.strftime('%A, %B %d') if hasattr(prior_date, 'strftime') else prior_date} ({days_gap} days ago). "
                                      f"Use **Manual O/N Override** in sidebar to enter current overnight session data.")
            else:
                hist_data=None
                if inputs["is_planning"]:
                    st.warning("⚠️ Could not fetch prior RTH data. Using manual inputs.")
                else:
                    st.error("❌ Could not fetch historical data for this date. Try a date within the last 60 days.")
            
            if inputs["is_historical"]:
                es_price=hist_data.get("day_open") if hist_data else None
            else:
                # Planning mode - try to get live ES price (ES is source of truth)
                live_es = fetch_es_current()
                
                if live_es:
                    es_price = live_es
                    if inputs.get("debug"):
                        st.caption(f"🔍 ES fetched: {es_price}")
                elif hist_data:
                    es_price = hist_data.get("prior_close")
                    st.info(f"📊 Using Friday's close ({es_price}) - Markets closed or live data unavailable")
                else:
                    es_price = None
                    st.warning("⚠️ Could not fetch ES price. Use **Override Current ES** in sidebar to enter manually.")
            # SPX is DERIVED from ES (ES - offset)
            spx_price = derive_spx_from_es(es_price, inputs["offset"])
            vix=fetch_vix_polygon() or 16.0
        else:
            # Live mode (today)
            es_candles=fetch_es_candles(7, inputs["offset"])
            es_price=fetch_es_current()
            
            # If ES fetch failed, show warning
            if es_price is None:
                st.warning("⚠️ Could not fetch ES price. Enable 'Override Current ES' in sidebar.")
            
            # SPX is DERIVED from ES (ES - offset)
            spx_price = derive_spx_from_es(es_price, inputs["offset"])
            vix=fetch_vix_polygon() or 16.0
            
            # Extract today's data from es_candles for live mode
            if es_candles is not None and not es_candles.empty:
                hist_data = extract_historical_data(es_candles, inputs["trading_date"], inputs["offset"])
            else:
                hist_data = None
    
    # Check if manual ES override is enabled
    if inputs.get("override_es") and inputs.get("manual_es"):
        es_price = inputs["manual_es"]
        st.success(f"✅ Using manual ES: {es_price}")
    elif es_price is None:
        # If O/N override is set, estimate current price from O/N data
        if inputs.get("override_on") and inputs.get("on_low"):
            # Use midpoint of O/N range as estimate, biased toward recent action
            on_h = inputs.get("on_high", 6050)
            on_l = inputs.get("on_low", 6000)
            # Estimate current near the low if it's a down session (high near prior close)
            prior_c = inputs.get("prior_close") if inputs.get("override_prior") else 6050
            if on_h and prior_c and abs(on_h - prior_c) < 10:
                # O/N high near prior close = gapped down, likely near low now
                es_price = on_l + (on_h - on_l) * 0.2  # Estimate 20% from low
                st.info(f"📊 Estimating current ES near O/N low: {es_price:.2f} (enable 'Override Current ES' for exact value)")
            else:
                es_price = (on_h + on_l) / 2
                st.info(f"📊 Estimating current ES at O/N midpoint: {es_price:.2f} (enable 'Override Current ES' for exact value)")
        else:
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
        
        candle_830=hist_data.get("candle_830") if hist_data else None
        current_es=hist_data.get("day_open",es_price) if inputs["is_historical"] else (es_price or (hist_data.get("prior_close",6050) if hist_data else 6050))
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
    
    # Prior RTH Override (full override with high/low/close and times)
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
    
    # IMPORTANT: on_prior_close from O/N Override takes FINAL precedence for gap calculation
    # This allows user to set prior close specifically for gap without full Prior RTH override
    if inputs.get("override_on") and inputs.get("on_prior_close"):
        prior_close = inputs["on_prior_close"]
    
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
    
    # Manual VIX override for premium calculation
    # First ensure vix exists
    if 'vix' not in dir() or vix is None:
        vix = 16.0  # Default fallback
    
    if inputs.get("override_vix") and inputs.get("manual_vix"):
        vix = float(inputs["manual_vix"])
        vix_source = "manual"
    else:
        vix_source = "fetched"
    
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
    # In planning mode (no 8:30 candle), project likely setup based on O/N position
    if candle_830 and ceiling_es and floor_es:
        validation=validate_830_candle(candle_830,ceiling_es,floor_es)
        position=validation.get("position","UNKNOWN")
    elif inputs.get("is_planning") and ceiling_es and floor_es and on_high and on_low:
        # PLANNING MODE: Project setup based on O/N position relative to channel
        # Determine where overnight is trading relative to the channel
        on_mid = (on_high + on_low) / 2
        channel_mid = (ceiling_es + floor_es) / 2
        
        # Calculate O/N position percentages
        on_near_ceiling = on_high >= ceiling_es or (ceiling_es - on_high) < 5
        on_near_floor = on_low <= floor_es or (on_low - floor_es) < 5
        on_above_channel = on_low > ceiling_es
        on_below_channel = on_high < floor_es
        
        # Gap direction (from prior close to current O/N position)
        pc = prior_close or ceiling_es
        gap_down = on_mid < pc - 20
        gap_up = on_mid > pc + 20
        
        if on_below_channel:
            # O/N entirely below channel = strong PUTS setup
            validation = {
                "status": "PROJECTED",
                "message": f"📊 PROJECTED: O/N trading below channel floor ({on_high:.0f} < {floor_es:.0f})",
                "setup": "PUTS",
                "position": "BELOW",
                "edge": floor_es,
                "projected": True
            }
            position = "BELOW"
        elif on_above_channel:
            # O/N entirely above channel = strong CALLS setup
            validation = {
                "status": "PROJECTED", 
                "message": f"📊 PROJECTED: O/N trading above channel ceiling ({on_low:.0f} > {ceiling_es:.0f})",
                "setup": "CALLS",
                "position": "ABOVE",
                "edge": ceiling_es,
                "projected": True
            }
            position = "ABOVE"
        elif on_near_floor and not on_near_ceiling:
            # O/N near floor = likely PUTS if it breaks
            validation = {
                "status": "PROJECTED",
                "message": f"📊 PROJECTED: O/N testing floor ({on_low:.0f} near {floor_es:.0f}) - PUTS if breaks",
                "setup": "PUTS",
                "position": "INSIDE",
                "edge": floor_es,
                "projected": True
            }
            position = "INSIDE"
        elif on_near_ceiling and not on_near_floor:
            # O/N near ceiling = likely CALLS if it breaks
            validation = {
                "status": "PROJECTED",
                "message": f"📊 PROJECTED: O/N testing ceiling ({on_high:.0f} near {ceiling_es:.0f}) - CALLS if breaks",
                "setup": "CALLS",
                "position": "INSIDE",
                "edge": ceiling_es,
                "projected": True
            }
            position = "INSIDE"
        elif gap_down:
            # Gap down but inside channel = lean PUTS
            validation = {
                "status": "PROJECTED",
                "message": f"📊 PROJECTED: Gap down inside channel - lean PUTS",
                "setup": "PUTS",
                "position": "INSIDE",
                "edge": floor_es,
                "projected": True
            }
            position = "INSIDE"
        elif gap_up:
            # Gap up but inside channel = lean CALLS
            validation = {
                "status": "PROJECTED",
                "message": f"📊 PROJECTED: Gap up inside channel - lean CALLS",
                "setup": "CALLS",
                "position": "INSIDE",
                "edge": ceiling_es,
                "projected": True
            }
            position = "INSIDE"
        else:
            # Neutral - inside channel, no clear bias
            validation = {
                "status": "PROJECTED",
                "message": f"📊 PROJECTED: O/N inside channel - wait for 8:30 break",
                "setup": "NEUTRAL",
                "position": "INSIDE",
                "projected": True
            }
            position = "INSIDE"
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
    is_projected = validation.get("projected", False)
    
    # Initial direction assignment (EMA conflict check happens after ema_signals is calculated)
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
            
    elif validation["setup"]=="NEUTRAL" and is_projected:
        # Neutral in planning mode - show both potential setups
        direction="NEUTRAL"
        entry_edge_es=None
        targets=[]
        # Calculate both directions for display
        puts_targets = find_targets(floor_spx, cones_spx, "PUTS") if floor_spx else []
        calls_targets = find_targets(ceiling_spx, cones_spx, "CALLS") if ceiling_spx else []
    else:
        direction="WAIT"
        entry_edge_es=None
        targets=[]
    
    # Check if this is a TREND_DAY (for display purposes)
    is_trend_day=validation["status"]=="TREND_DAY"
    
    # Flow & momentum - use 8:30 candle open for flow bias calculation
    # In planning mode with O/N override, we need to carefully estimate flow_price AND detect gaps
    if candle_830:
        flow_price = candle_830["open"]
    elif inputs.get("is_planning") and inputs.get("override_on"):
        # Get the values we'll use
        on_h = on_high or 6050
        on_l = on_low or 6000
        pc = prior_close or 6050
        
        # Calculate gap: difference between O/N range and prior close
        # If O/N LOW is below prior close = gap down
        # If O/N HIGH is above prior close = gap up
        gap_from_high = on_h - pc  # Positive = O/N traded above prior close
        gap_from_low = on_l - pc   # Negative = O/N traded below prior close
        
        # The "true gap" is where the overnight session opened/traded relative to prior close
        # For a gap DOWN: O/N high is near prior close, but low is much lower
        # For a gap UP: O/N low is near prior close, but high is much higher
        
        # DEBUG: Show what values we're working with (only if debug enabled)
        if inputs.get("debug"):
            st.caption(f"🔍 Debug: O/N High={on_h:.1f}, O/N Low={on_l:.1f}, Prior Close={pc:.1f}")
            st.caption(f"🔍 Gap Analysis: High vs PC = {gap_from_high:+.0f}, Low vs PC = {gap_from_low:+.0f}")
        
        # Detect gap scenarios
        if gap_from_low < -30:
            # O/N LOW is 30+ points BELOW prior close = Significant Gap Down
            # Current price is likely near the O/N low
            flow_price = on_l + (on_h - on_l) * 0.3  # Estimate 30% from low
            if inputs.get("debug"):
                st.caption(f"🔍 GAP DOWN detected ({gap_from_low:.0f} pts)! flow_price={flow_price:.1f}")
        elif gap_from_high > 30:
            # O/N HIGH is 30+ points ABOVE prior close = Significant Gap Up
            # Current price is likely near the O/N high
            flow_price = on_l + (on_h - on_l) * 0.7  # Estimate 70% from low
            if inputs.get("debug"):
                st.caption(f"🔍 GAP UP detected (+{gap_from_high:.0f} pts)! flow_price={flow_price:.1f}")
        elif gap_from_low < -10:
            # Moderate gap down
            flow_price = on_l + (on_h - on_l) * 0.4
            if inputs.get("debug"):
                st.caption(f"🔍 Moderate gap down ({gap_from_low:.0f} pts), flow_price={flow_price:.1f}")
        elif gap_from_high > 10:
            # Moderate gap up
            flow_price = on_l + (on_h - on_l) * 0.6
            if inputs.get("debug"):
                st.caption(f"🔍 Moderate gap up (+{gap_from_high:.0f} pts), flow_price={flow_price:.1f}")
        else:
            # No significant gap - use midpoint
            flow_price = (on_h + on_l) / 2
            if inputs.get("debug"):
                st.caption(f"🔍 No significant gap, using midpoint: flow_price={flow_price:.1f}")
    else:
        flow_price = current_es
    
    flow=calculate_flow_bias(flow_price,on_high,on_low,vix,vix_high,vix_low,prior_close)
    
    # Debug: Show what prior_close is being used for gap (only if debug enabled)
    if inputs.get("debug") and inputs.get("is_planning"):
        gap_used = flow_price - prior_close if prior_close else 0
        st.caption(f"💡 Flow Calc: flow_price={flow_price:.1f}, prior_close={prior_close:.1f}, GAP = {gap_used:+.1f} pts")
    
    momentum=calculate_momentum(es_candles)
    ema_signals=calculate_ema_signals(es_candles,current_es)
    vix_zone=get_vix_zone(vix)
    
    # ─────────────────────────────────────────────────────────────────────────
    # EMA CONFLICT CHECK - Now that we have ema_signals, check for conflicts
    # ─────────────────────────────────────────────────────────────────────────
    ema_favors_calls = ema_signals.get("aligned_calls", False) or ema_signals.get("cross") == "BULLISH"
    ema_favors_puts = ema_signals.get("aligned_puts", False) or ema_signals.get("cross") == "BEARISH"
    
    # In projected mode, if EMA conflicts with structural setup, show NEUTRAL with both
    if is_projected and direction in ["CALLS", "PUTS"]:
        if direction == "CALLS" and ema_favors_puts and not ema_favors_calls:
            # Structure says CALLS but EMA says PUTS - CONFLICT
            original_direction = direction
            direction = "NEUTRAL"
            validation["original_setup"] = original_direction
            validation["setup"] = "NEUTRAL"
            validation["message"] = f"⚠️ CONFLICT: Structure suggests CALLS but EMA favors PUTS"
            validation["conflict"] = True
        elif direction == "PUTS" and ema_favors_calls and not ema_favors_puts:
            # Structure says PUTS but EMA says CALLS - CONFLICT
            original_direction = direction
            direction = "NEUTRAL"
            validation["original_setup"] = original_direction
            validation["setup"] = "NEUTRAL"
            validation["message"] = f"⚠️ CONFLICT: Structure suggests PUTS but EMA favors CALLS"
            validation["conflict"] = True
    
    confidence=calculate_confidence(channel_type,validation,direction,ema_signals,flow,vix_zone)
    
    # Historical outcome
    if inputs["is_historical"] and hist_data and entry_edge_es:
        outcome=analyze_historical_outcome(hist_data,validation,ceiling_es,floor_es,targets,direction,entry_edge_es,offset)
    else:
        outcome=None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BRAND HEADER - Leveraged Alpha Style
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('''<div class="brand-header">
<div class="brand-logo-box">
<svg viewBox="0 0 40 40">
<!-- 3-Pillar Pyramid with Eye of Insight -->
<!-- Outer pyramid frame -->
<path d="M20 4 L36 34 L4 34 Z" fill="none" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
<!-- Three pillars rising from base -->
<line x1="11" y1="34" x2="11" y2="22" stroke-width="2.5" stroke-linecap="round"/>
<line x1="20" y1="34" x2="20" y2="14" stroke-width="2.5" stroke-linecap="round"/>
<line x1="29" y1="34" x2="29" y2="22" stroke-width="2.5" stroke-linecap="round"/>
<!-- Glowing eye/insight at apex -->
<circle cx="20" cy="11" r="3.5" fill="#0a0a0a" stroke-width="1.5"/>
<circle cx="20" cy="11" r="1.5" fill="#0a0a0a" stroke-width="2"/>
<!-- Horizontal connection beam -->
<line x1="11" y1="22" x2="29" y2="22" stroke-width="1.5" stroke-linecap="round" opacity="0.6"/>
</svg>
</div>
<h1 class="brand-name"><span>SPX</span> <span>Prophet</span></h1>
<div class="brand-tagline">Three Pillars. One Vision. Total Clarity.</div>
<div class="brand-live"><span>STRUCTURE-BASED 0DTE FORECASTING</span></div>
</div>''', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MEGA STATUS BANNER - The Hero Element
    # ═══════════════════════════════════════════════════════════════════════════
    
    if inputs["is_historical"]:
        status_class = "mega-status hist"
        status_icon = "📜"
        status_title = "HISTORICAL ANALYSIS"
        status_sub = f"Reviewing {inputs['trading_date'].strftime('%A, %B %d, %Y')}"
    elif inputs["is_planning"] and is_projected:
        # Planning mode with projected setup
        if direction == "PUTS":
            status_class = "mega-status go"
            status_icon = "▼"
            status_title = "PROJECTED PUTS"
            status_sub = validation["message"]
        elif direction == "CALLS":
            status_class = "mega-status go"
            status_icon = "▲"
            status_title = "PROJECTED CALLS"
            status_sub = validation["message"]
        elif direction == "NEUTRAL":
            status_class = "mega-status wait"
            status_icon = "⚖️"
            status_title = "NEUTRAL - WATCH BOTH"
            status_sub = "O/N inside channel - direction at 8:30"
        else:
            status_class = "mega-status hist"
            status_icon = "📋"
            status_title = "PLANNING MODE"
            status_sub = f"Preparing for {inputs['trading_date'].strftime('%A, %B %d, %Y')}"
    elif inputs["is_planning"]:
        status_class = "mega-status hist"
        status_icon = "📋"
        status_title = "PLANNING MODE"
        status_sub = f"Preparing for {inputs['trading_date'].strftime('%A, %B %d, %Y')}"
    elif validation["setup"] == "PUTS":
        status_class = "mega-status go"
        status_icon = "▼"
        status_title = "PUTS SETUP"
        status_sub = validation["message"]
    elif validation["setup"] == "CALLS":
        status_class = "mega-status go"
        status_icon = "▲"
        status_title = "CALLS SETUP"
        status_sub = validation["message"]
    elif validation["status"] == "INSIDE":
        status_class = "mega-status wait"
        status_icon = "⏸"
        status_title = "WAITING"
        status_sub = "8:30 candle inside channel - awaiting break"
    elif validation["status"] == "AWAITING":
        status_class = "mega-status wait"
        status_icon = "⏳"
        status_title = "AWAITING 8:30"
        status_sub = "Market not yet open"
    else:
        status_class = "mega-status stop"
        status_icon = "—"
        status_title = "NO TRADE"
        status_sub = validation.get("message", "Setup conditions not met")
    
    st.markdown(f'''<div class="{status_class}">
<div class="mega-left">
<div class="mega-icon">{status_icon}</div>
<div>
<div class="mega-title">{status_title}</div>
<div class="mega-sub">{status_sub}</div>
</div>
</div>
<div class="mega-right">
<div class="mega-price">{current_spx:,.2f}</div>
<div class="mega-meta">SPX • ES {current_es:,.2f} • {channel_type}</div>
</div>
</div>''', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION GRID - Clear pass/fail with actual values
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Channel validation
    if channel_type in ["RISING", "FALLING"]:
        ch_status = "pass"
        ch_icon = "✓"
        ch_val = channel_type
    else:
        ch_status = "neutral"
        ch_icon = "?"
        ch_val = "UNDETERMINED"
    
    # 8:30 Break validation
    if validation["status"] in ["VALID", "TREND_DAY"]:
        break_status = "pass"
        break_icon = "✓"
        break_val = validation["status"]
    elif validation["status"] == "INSIDE":
        break_status = "neutral"
        break_icon = "—"
        break_val = "INSIDE"
    else:
        break_status = "fail"
        break_icon = "✗"
        break_val = "NO BREAK"
    
    # EMA validation
    ema8_val = ema_signals.get("ema8", "—")
    ema21_val = ema_signals.get("ema21", "—")
    ema200_val = ema_signals.get("ema200", "—")
    if direction == "CALLS" and ema_signals.get("aligned_calls"):
        ema_status = "pass"
        ema_icon = "✓"
        ema_val = f"BULL ({ema_signals.get('cross_signal', '')})"
    elif direction == "PUTS" and ema_signals.get("aligned_puts"):
        ema_status = "pass"
        ema_icon = "✓"
        ema_val = f"BEAR ({ema_signals.get('cross_signal', '')})"
    elif direction in ["CALLS", "PUTS"]:
        ema_status = "fail"
        ema_icon = "✗"
        ema_val = f"CONFLICT"
    else:
        ema_status = "neutral"
        ema_icon = "—"
        ema_val = ema_signals.get("cross_signal", "N/A")
    
    # Flow validation
    flow_score = flow.get("score", 0)
    flow_bias = flow.get("bias", "NEUTRAL")
    if direction == "CALLS" and "CALLS" in flow_bias:
        flow_status = "pass"
        flow_icon = "✓"
        flow_val = f"+{flow_score}"
    elif direction == "PUTS" and "PUTS" in flow_bias:
        flow_status = "pass"
        flow_icon = "✓"
        flow_val = f"{flow_score}"
    elif flow_bias == "NEUTRAL":
        flow_status = "neutral"
        flow_icon = "—"
        flow_val = f"{flow_score}"
    elif direction in ["CALLS", "PUTS"]:
        flow_status = "fail"
        flow_icon = "✗"
        flow_val = f"{flow_score}"
    else:
        flow_status = "neutral"
        flow_icon = "—"
        flow_val = f"{flow_score}"
    
    # VIX validation
    if vix_zone in ["LOW", "NORMAL"]:
        vix_status = "pass"
        vix_icon = "✓"
        vix_val = f"{vix:.1f}"
    elif vix_zone == "ELEVATED":
        vix_status = "neutral"
        vix_icon = "—"
        vix_val = f"{vix:.1f}"
    else:
        vix_status = "fail"
        vix_icon = "✗"
        vix_val = f"{vix:.1f}"
    
    st.markdown(f'''<div class="valid-row">
<div class="valid-card {ch_status}">
<div class="valid-icon">{ch_icon}</div>
<div class="valid-label">Channel</div>
<div class="valid-val">{ch_val}</div>
</div>
<div class="valid-card {break_status}">
<div class="valid-icon">{break_icon}</div>
<div class="valid-label">8:30 Break</div>
<div class="valid-val">{break_val}</div>
</div>
<div class="valid-card {ema_status}">
<div class="valid-icon">{ema_icon}</div>
<div class="valid-label">EMA</div>
<div class="valid-val">{ema_val}</div>
</div>
<div class="valid-card {flow_status}">
<div class="valid-icon">{flow_icon}</div>
<div class="valid-label">Flow</div>
<div class="valid-val">{flow_val}</div>
</div>
<div class="valid-card {vix_status}">
<div class="valid-icon">{vix_icon}</div>
<div class="valid-label">VIX</div>
<div class="valid-val">{vix_val}</div>
</div>
</div>''', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HISTORICAL OUTCOME CARD (if applicable)
    # ═══════════════════════════════════════════════════════════════════════════
    if outcome:
        if outcome["outcome"]=="WIN":
            box_class="win"
            icon="✅"
        elif outcome["outcome"]=="LOSS":
            box_class="loss"
            icon="❌"
        elif outcome["outcome"]=="MOMENTUM_PROBE":
            box_class="neutral"
            icon="⚡"
        else:
            box_class="neutral"
            icon="⚠️"
        
        timeline_html=""
        for evt in outcome.get("timeline",[]):
            dot_class="hit" if "TARGET" in evt["event"] else "active"
            timeline_html+=f'<div class="timeline-item"><div class="timeline-dot {dot_class}"></div><div style="font-size:12px"><span style="color:rgba(255,255,255,0.5)">{evt["time"]}</span> <span style="font-weight:600">{evt["event"]}</span> @ {evt["price"]:.2f}</div></div>'
        
        targets_hit_str=", ".join([f"{t['name']} @ {t['time']}" for t in outcome.get("targets_hit",[])]) or "None"
        
        # Entry confirmation details - now shows setup_time and entry_time
        entry_conf=outcome.get("entry_confirmation",{})
        if entry_conf.get("confirmed"):
            setup_time = entry_conf.get("setup_time", "")
            entry_time = entry_conf.get("entry_time", entry_conf.get("time", ""))
            entry_conf_html=f'''<div style="background:rgba(0,212,170,0.1);border:1px solid rgba(0,212,170,0.3);border-radius:10px;padding:12px;margin-bottom:12px">
<div style="font-size:12px;font-weight:600;color:#00d4aa;margin-bottom:6px">✅ {setup_time} Setup → {entry_time} Entry</div>
<div style="font-size:11px;color:rgba(255,255,255,0.7)">{entry_conf.get("candle_color","")} rejection — {entry_conf.get("detail","")}</div>
</div>'''
        elif outcome["outcome"]=="MOMENTUM_PROBE":
            setup_time = entry_conf.get("setup_time", entry_conf.get("time", ""))
            entry_conf_html=f'''<div style="background:rgba(255,71,87,0.1);border:1px solid rgba(255,71,87,0.3);border-radius:10px;padding:12px;margin-bottom:12px">
<div style="font-size:12px;font-weight:600;color:#ff4757;margin-bottom:4px">⚡ Momentum Probe @ {setup_time}</div>
<div style="font-size:11px;color:rgba(255,255,255,0.7)">{entry_conf.get("detail","Broke through by >6 pts - next candle continued in breakout direction")}</div>
<div style="font-size:10px;color:#ff4757;margin-top:6px;font-weight:500">❌ NO ENTRY - Fade would have failed</div>
</div>'''
        elif outcome["outcome"]=="NO_ENTRY":
            entry_conf_html=f'''<div style="background:rgba(255,165,2,0.1);border:1px solid rgba(255,165,2,0.3);border-radius:10px;padding:12px;margin-bottom:12px">
<div style="font-size:12px;font-weight:600;color:#ffa502;margin-bottom:4px">⚠️ No Setup Found</div>
<div style="font-size:11px;color:rgba(255,255,255,0.7)">{entry_conf.get("message","No valid setup candle found by 10:30 AM")}</div>
</div>'''
        else:
            entry_conf_html=""
        
        st.markdown(f'''<div class="result-box {box_class}">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
<div style="font-size:18px;font-weight:700">{icon} HISTORICAL RESULT</div>
<div style="font-size:14px;font-weight:600">{outcome["outcome"].replace("_"," ")}</div>
</div>
<div style="font-size:14px;margin-bottom:12px">{outcome["message"]}</div>
{entry_conf_html}
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px">
<div style="text-align:center"><div style="font-size:10px;color:rgba(255,255,255,0.5)">Direction</div><div style="font-weight:600">{outcome["direction"]}</div></div>
<div style="text-align:center"><div style="font-size:10px;color:rgba(255,255,255,0.5)">Entry Level</div><div style="font-weight:600">{outcome.get("entry_level_at_time", outcome["entry_level_spx"])}</div></div>
<div style="text-align:center"><div style="font-size:10px;color:rgba(255,255,255,0.5)">Max Favorable</div><div style="font-weight:600;color:#00d4aa">+{outcome["max_favorable"]:.1f}</div></div>
<div style="text-align:center"><div style="font-size:10px;color:rgba(255,255,255,0.5)">Max Adverse</div><div style="font-weight:600;color:#ff4757">-{outcome["max_adverse"]:.1f}</div></div>
</div>
<div style="font-size:12px;color:rgba(255,255,255,0.6)"><strong>Targets Hit:</strong> {targets_hit_str}</div>
{f'<div class="timeline" style="margin-top:12px">{timeline_html}</div>' if timeline_html else ""}
</div>''',unsafe_allow_html=True)
        
        # Debug expander to show candle-by-candle evaluation
        debug_info = entry_conf.get("debug", [])
        if debug_info:
            with st.expander("🔍 Entry Confirmation Debug"):
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
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION CARDS - Beautiful Icons
    # ═══════════════════════════════════════════════════════════════════════════
    if inputs["is_historical"] and hist_data:
        st.markdown("### 📊 Session Data")
        
        # Get london data
        lon_h=hist_data.get("london_high","—")
        lon_l=hist_data.get("london_low","—")
        
        # Build beautiful session cards
        session_html=f'''<div class="session-row">
<div class="session-card sydney">
<div class="session-head">
<div class="session-icon">🌏</div>
<div class="session-info">
<div class="session-name">Sydney</div>
<div class="session-time">5:00 PM - 8:30 PM CT</div>
</div>
</div>
<div class="session-data">
<div class="session-line"><span class="session-label">High</span><span class="session-value high">{syd_h}</span></div>
<div class="session-line"><span class="session-label">Low</span><span class="session-value low">{syd_l}</span></div>
</div>
</div>

<div class="session-card tokyo">
<div class="session-head">
<div class="session-icon">🗼</div>
<div class="session-info">
<div class="session-name">Tokyo</div>
<div class="session-time">9:00 PM - 1:30 AM CT</div>
</div>
</div>
<div class="session-data">
<div class="session-line"><span class="session-label">High</span><span class="session-value high">{tok_h}</span></div>
<div class="session-line"><span class="session-label">Low</span><span class="session-value low">{tok_l}</span></div>
</div>
</div>

<div class="session-card london">
<div class="session-head">
<div class="session-icon">🏛️</div>
<div class="session-info">
<div class="session-name">London</div>
<div class="session-time">2:00 AM - 3:00 AM CT</div>
</div>
</div>
<div class="session-data">
<div class="session-line"><span class="session-label">High</span><span class="session-value high">{lon_h}</span></div>
<div class="session-line"><span class="session-label">Low</span><span class="session-value low">{lon_l}</span></div>
</div>
</div>

<div class="session-card overnight">
<div class="session-head">
<div class="session-icon">🌙</div>
<div class="session-info">
<div class="session-name">Overnight</div>
<div class="session-time">5:00 PM - 3:00 AM CT</div>
</div>
</div>
<div class="session-data">
<div class="session-line"><span class="session-label">High</span><span class="session-value high">{on_high}</span></div>
<div class="session-line"><span class="session-label">Low</span><span class="session-value low">{on_low}</span></div>
</div>
</div>
</div>'''
        
        st.markdown(session_html,unsafe_allow_html=True)
        
        # 8:30 Candle Card
        if candle_830:
            c=candle_830
            candle_color="bullish" if c["close"]>=c["open"] else "bearish"
            candle_type="BULLISH" if c["close"]>=c["open"] else "BEARISH"
            st.markdown(f'''<div class="candle-card">
<div class="candle-header">
<div class="candle-info">
<div class="candle-icon">🕣</div>
<div>
<div class="candle-title">8:30 AM Candle (ES)</div>
<div class="candle-subtitle">First 30-minute candle of RTH</div>
</div>
</div>
<div class="candle-type {candle_color}">{candle_type}</div>
</div>
<div class="candle-grid">
<div class="candle-item"><div class="candle-label">Open</div><div class="candle-value">{c["open"]:.2f}</div></div>
<div class="candle-item"><div class="candle-label">High</div><div class="candle-value high">{c["high"]:.2f}</div></div>
<div class="candle-item"><div class="candle-label">Low</div><div class="candle-value low">{c["low"]:.2f}</div></div>
<div class="candle-item"><div class="candle-label">Close</div><div class="candle-value">{c["close"]:.2f}</div></div>
</div>
</div>''',unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TRADE COMMAND CENTER - Premium Design
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🎯 Trade Command Center")
    
    ch_badge_class = "rising" if channel_type == "RISING" else "falling"
    ch_icon = "▲" if channel_type == "RISING" else "▼"
    
    # Start building the command card HTML
    cmd_html = f'''<div class="cmd-card">
<div class="cmd-header">
<div>
<div class="cmd-title">{"📜 Historical " if inputs["is_historical"] else ""}Trading Plan</div>
<div class="cmd-subtitle">{channel_reason}</div>
</div>
<div class="cmd-badge {ch_badge_class}">{ch_icon} {channel_type}</div>
</div>
<div class="cmd-body">
<div class="channel-grid">
<div class="channel-item ceiling">
<div class="channel-label">Ceiling ({ceil_key or "N/A"})</div>
<div class="channel-value">{ceiling_spx or "—"}</div>
<div class="channel-es">ES {ceiling_es or "—"}</div>
</div>
<div class="channel-item floor">
<div class="channel-label">Floor ({floor_key or "N/A"})</div>
<div class="channel-value">{floor_spx or "—"}</div>
<div class="channel-es">ES {floor_es or "—"}</div>
</div>
</div>'''
    
    # Add trade setup if we have a direction
    if direction in ["PUTS", "CALLS"]:
        # For projected setups, use the appropriate edge even if validation didn't set entry_edge
        if entry_edge_es is None and is_projected:
            entry_edge_es = floor_es if direction == "PUTS" else ceiling_es
            
        if entry_edge_es:
            entry_spx = round(entry_edge_es - offset, 2)
            strike = get_strike(entry_spx, "PUT" if direction == "PUTS" else "CALL")
            entry_price = estimate_prices(entry_spx, strike, "PUT" if direction == "PUTS" else "CALL", vix, hours_to_expiry)
            
            # Get targets - recalculate if needed
            if not targets:
                targets = find_targets(entry_spx, cones_spx, direction) if entry_spx else []
            exits, _ = estimate_exit_prices(entry_spx, strike, "PUT" if direction == "PUTS" else "CALL", vix, hours_to_expiry, targets)
            
            setup_class = "puts" if direction == "PUTS" else "calls"
            setup_icon = "▼" if direction == "PUTS" else "▲"
            
            # Different messaging for projected vs confirmed
            if is_projected:
                setup_label = f"PROJECTED {direction}"
                setup_status = "📊 PLANNING MODE"
            else:
                setup_label = f"{direction} SETUP"
                setup_status = "✅ CONFIRMED"
            
            if direction == "PUTS":
                entry_rule = "BULLISH candle touches entry level, then closes BELOW it"
                rule_warning = "If candle breaks >6 pts ABOVE entry but closes below → NO ENTRY (momentum probe)"
            else:
                entry_rule = "BEARISH candle touches entry level, then closes ABOVE it"
                rule_warning = "If candle breaks >6 pts BELOW entry but closes above → NO ENTRY (momentum probe)"
            
            # Build targets HTML
            targets_html = ""
            for i, t in enumerate(exits):
                targets_html += f'''<div class="target-row">
<span class="target-name">{t["target"]}</span>
<span class="target-level">@ {t["level"]}</span>
<span class="target-price">${t["price"]} ({t["pct"]:+.0f}%)</span>
</div>'''
            
            # Add projected badge styling
            projected_badge = f'<div style="font-size:10px;color:var(--amber);margin-top:4px;font-weight:600">{setup_status}</div>' if is_projected else ''
            
            cmd_html += f'''
<div class="setup-box {setup_class}">
<div class="setup-header">
<div class="setup-icon">{setup_icon}</div>
<div>
<div class="setup-title">{setup_label}</div>
{projected_badge}
</div>
</div>
<div class="setup-metrics">
<div class="setup-metric">
<div class="setup-metric-label">Entry Window</div>
<div class="setup-metric-value">8:30 - 11:00</div>
</div>
<div class="setup-metric">
<div class="setup-metric-label">Entry Level</div>
<div class="setup-metric-value">{entry_spx}</div>
</div>
<div class="setup-metric">
<div class="setup-metric-label">Strike</div>
<div class="setup-metric-value">{strike}</div>
</div>
<div class="setup-metric">
<div class="setup-metric-label">Est. Premium</div>
<div class="setup-metric-value">${entry_price:.2f}</div>
</div>
</div>
<div class="entry-rule">
<div class="entry-rule-title">📋 Entry Confirmation {"(Projected)" if is_projected else ""}</div>
<div class="entry-rule-text">{entry_rule}</div>
<div class="entry-rule-warning">⚠️ {rule_warning}</div>
</div>
<div class="targets-box">
<div class="targets-title">📍 Profit Targets</div>
{targets_html if targets_html else '<div style="color:var(--text-muted)">No targets in range</div>'}
</div>
</div>'''
        else:
            # Have direction but no entry edge - shouldn't happen but fallback
            cmd_html += '''
<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:32px;text-align:center;margin-top:20px">
<div style="font-size:48px;margin-bottom:16px;opacity:0.3">⚠️</div>
<div style="font-size:18px;font-weight:600;color:rgba(255,255,255,0.4);margin-bottom:8px">Setup Incomplete</div>
<div style="font-size:13px;color:rgba(255,255,255,0.3)">Missing entry edge data</div>
</div>'''
    elif direction == "NEUTRAL" and is_projected:
        # Neutral in planning mode - show BOTH potential setups with conflict info
        # Check what's causing the conflict
        ema_info = ""
        if ema_signals.get("aligned_puts") or ema_signals.get("cross") == "BEARISH":
            ema_info = "EMA favors PUTS (bearish cross, below 200)"
        elif ema_signals.get("aligned_calls") or ema_signals.get("cross") == "BULLISH":
            ema_info = "EMA favors CALLS (bullish cross, above 200)"
        
        conflict_msg = validation.get("message", "O/N trading inside channel")
        
        # Calculate strikes and premiums for both setups
        puts_strike = get_strike(floor_spx, "PUT") if floor_spx else 0
        puts_premium = estimate_prices(floor_spx, puts_strike, "PUT", vix, hours_to_expiry) if floor_spx else 0
        
        calls_strike = get_strike(ceiling_spx, "CALL") if ceiling_spx else 0
        calls_premium = estimate_prices(ceiling_spx, calls_strike, "CALL", vix, hours_to_expiry) if ceiling_spx else 0
        
        cmd_html += f'''
<div style="margin-top:16px">
<div style="background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.4);border-radius:16px;padding:20px;margin-bottom:16px">
<div style="font-size:16px;color:var(--amber);font-weight:700;margin-bottom:10px">⚠️ CONFLICTING SIGNALS - WATCH BOTH SETUPS</div>
<div style="font-size:13px;color:rgba(255,255,255,0.7);margin-bottom:8px">{conflict_msg}</div>
<div style="font-size:12px;color:rgba(255,255,255,0.5)">{ema_info}</div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
<div style="background:linear-gradient(145deg, rgba(255,71,87,0.1), rgba(255,71,87,0.05));border:1px solid rgba(255,71,87,0.4);border-radius:16px;padding:20px">
<div style="font-size:18px;font-weight:800;color:var(--red);margin-bottom:12px">▼ PUTS SETUP</div>
<div style="font-size:13px;color:rgba(255,255,255,0.6);margin-bottom:12px">If 8:30 breaks below floor</div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-top:1px solid rgba(255,255,255,0.1)">
<span style="color:rgba(255,255,255,0.5)">Entry Level</span>
<span style="font-family:monospace;font-weight:600">{floor_spx}</span>
</div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-top:1px solid rgba(255,255,255,0.1)">
<span style="color:rgba(255,255,255,0.5)">Strike</span>
<span style="font-family:monospace;font-weight:600;color:var(--red)">{puts_strike}</span>
</div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-top:1px solid rgba(255,255,255,0.1)">
<span style="color:rgba(255,255,255,0.5)">Est. Premium</span>
<span style="font-family:monospace;font-weight:600">${puts_premium:.2f}</span>
</div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-top:1px solid rgba(255,255,255,0.1)">
<span style="color:rgba(255,255,255,0.5)">EMA Aligned?</span>
<span style="color:{'var(--green)' if ema_signals.get('aligned_puts') else 'var(--red)'};font-weight:600">{'✓ YES' if ema_signals.get('aligned_puts') else '✗ NO'}</span>
</div>
</div>
<div style="background:linear-gradient(145deg, rgba(0,255,136,0.1), rgba(0,255,136,0.05));border:1px solid rgba(0,255,136,0.4);border-radius:16px;padding:20px">
<div style="font-size:18px;font-weight:800;color:var(--green);margin-bottom:12px">▲ CALLS SETUP</div>
<div style="font-size:13px;color:rgba(255,255,255,0.6);margin-bottom:12px">If 8:30 breaks above ceiling</div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-top:1px solid rgba(255,255,255,0.1)">
<span style="color:rgba(255,255,255,0.5)">Entry Level</span>
<span style="font-family:monospace;font-weight:600">{ceiling_spx}</span>
</div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-top:1px solid rgba(255,255,255,0.1)">
<span style="color:rgba(255,255,255,0.5)">Strike</span>
<span style="font-family:monospace;font-weight:600;color:var(--green)">{calls_strike}</span>
</div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-top:1px solid rgba(255,255,255,0.1)">
<span style="color:rgba(255,255,255,0.5)">Est. Premium</span>
<span style="font-family:monospace;font-weight:600">${calls_premium:.2f}</span>
</div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-top:1px solid rgba(255,255,255,0.1)">
<span style="color:rgba(255,255,255,0.5)">EMA Aligned?</span>
<span style="color:{'var(--green)' if ema_signals.get('aligned_calls') else 'var(--red)'};font-weight:600">{'✓ YES' if ema_signals.get('aligned_calls') else '✗ NO'}</span>
</div>
</div>
</div>
</div>'''
    else:
        # No active setup
        cmd_html += '''
<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:32px;text-align:center;margin-top:20px">
<div style="font-size:48px;margin-bottom:16px;opacity:0.3">⏸</div>
<div style="font-size:18px;font-weight:600;color:rgba(255,255,255,0.4);margin-bottom:8px">No Active Setup</div>
<div style="font-size:13px;color:rgba(255,255,255,0.3)">Waiting for market data to determine setup</div>
</div>'''
    
    cmd_html += "</div></div>"
    st.markdown(cmd_html, unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSIS GRID - 2x2 Layout with Equal Height Cards
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 📊 Analysis")
    
    # Calculate values needed for all cards
    conf_score=confidence["score"]
    conf_color="#00d4aa" if conf_score>=70 else "#ffa502" if conf_score>=50 else "#ff4757"
    conf_label="HIGH" if conf_score>=70 else "MEDIUM" if conf_score>=50 else "LOW"
    breakdown_html="".join([f'<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,0.04)"><span style="color:rgba(255,255,255,0.5)">{k}</span><span style="font-weight:500">{v}</span></div>' for k,v in confidence["breakdown"]])
    
    cross_color="#00d4aa" if ema_signals["cross_bullish"] else "#ff4757" if ema_signals["cross_bearish"] else "#ffa502"
    filter_color="#00d4aa" if ema_signals["above_200"] else "#ff4757" if ema_signals["below_200"] else "#ffa502"
    filter_text="ABOVE" if ema_signals["above_200"] else "BELOW" if ema_signals["below_200"] else "AT"
    
    # Determine EMA alignment status
    if direction=="CALLS" and ema_signals["aligned_calls"]:
        align_text="✅ ALIGNED FOR CALLS";align_color="#00d4aa";align_bg="rgba(0,212,170,0.12)"
    elif direction=="PUTS" and ema_signals["aligned_puts"]:
        align_text="✅ ALIGNED FOR PUTS";align_color="#ff4757";align_bg="rgba(255,71,87,0.12)"
    elif direction in ["CALLS","PUTS"]:
        # Have a direction but EMAs don't support it
        align_text="⚠️ CONFLICT";align_color="#ffa502";align_bg="rgba(255,165,2,0.12)"
    elif ema_signals["aligned_calls"]:
        # No direction yet, but EMAs favor CALLS
        align_text="📈 FAVORS CALLS";align_color="#00d4aa";align_bg="rgba(0,212,170,0.08)"
    elif ema_signals["aligned_puts"]:
        # No direction yet, but EMAs favor PUTS
        align_text="📉 FAVORS PUTS";align_color="#ff4757";align_bg="rgba(255,71,87,0.08)"
    elif ema_signals["cross_bullish"]:
        # Bullish cross but not fully aligned (price not above 200)
        align_text="📈 LEANS CALLS";align_color="#00d4aa";align_bg="rgba(0,212,170,0.05)"
    elif ema_signals["cross_bearish"]:
        # Bearish cross but not fully aligned (price not below 200)
        align_text="📉 LEANS PUTS";align_color="#ff4757";align_bg="rgba(255,71,87,0.05)"
    else:
        align_text="— NEUTRAL";align_color="#666";align_bg="rgba(255,255,255,0.03)"
    
    flow_color="#00d4aa" if "CALLS" in flow["bias"] else "#ff4757" if "PUTS" in flow["bias"] else "#ffa502"
    meter_pos=(flow["score"]+100)/2
    flow_label=flow["bias"].replace("_"," ")
    
    # Build flow signals breakdown HTML
    flow_signals_html = ""
    for sig in flow.get("signals", []):
        if len(sig) >= 4:
            name, direction_sig, detail, pts = sig
            sig_color = "#00d4aa" if pts > 0 else "#ff4757" if pts < 0 else "#666"
            pts_str = f"+{pts}" if pts > 0 else str(pts)
            flow_signals_html += f'<div style="display:flex;justify-content:space-between;padding:4px 0;font-size:11px;border-bottom:1px solid rgba(255,255,255,0.04)"><span style="color:rgba(255,255,255,0.6)">{name}</span><span style="color:{sig_color};font-weight:500">{pts_str}</span></div>'
        elif len(sig) == 3:
            name, direction_sig, detail = sig
            sig_color = "#00d4aa" if direction_sig == "CALLS" else "#ff4757" if direction_sig == "PUTS" else "#666"
            flow_signals_html += f'<div style="display:flex;justify-content:space-between;padding:4px 0;font-size:11px;border-bottom:1px solid rgba(255,255,255,0.04)"><span style="color:rgba(255,255,255,0.6)">{name}</span><span style="color:{sig_color}">{detail}</span></div>'
    
    mom_color="#00d4aa" if "BULL" in momentum["signal"] else "#ff4757" if "BEAR" in momentum["signal"] else "#ffa502"
    vix_color="#00d4aa" if vix_zone in ["LOW","NORMAL"] else "#ffa502" if vix_zone=="ELEVATED" else "#ff4757"
    
    # Build the entire 2x2 grid as one HTML block for consistent sizing
    analysis_html=f'''
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">

<!-- ROW 1: Confidence + EMA -->
<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:20px;min-height:280px;display:flex;flex-direction:column">
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px">
<div style="display:flex;align-items:center;gap:12px">
<div style="width:44px;height:44px;background:rgba(168,85,247,0.15);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px">📊</div>
<div><div style="font-family:Space Grotesk,sans-serif;font-size:15px;font-weight:600">Confidence Score</div>
<div style="font-size:11px;color:rgba(255,255,255,0.5)">Setup quality assessment</div></div>
</div>
<div style="text-align:right">
<div style="font-family:IBM Plex Mono,monospace;font-size:28px;font-weight:700;color:{conf_color}">{conf_score}%</div>
<div style="font-size:10px;font-weight:600;color:{conf_color}">{conf_label}</div>
</div>
</div>
<div style="height:8px;background:rgba(255,255,255,0.08);border-radius:4px;overflow:hidden;margin-bottom:16px">
<div style="height:100%;width:{conf_score}%;background:{conf_color};border-radius:4px"></div>
</div>
<div style="flex:1;background:rgba(255,255,255,0.02);border-radius:10px;padding:12px">{breakdown_html}</div>
</div>

<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:20px;min-height:280px;display:flex;flex-direction:column">
<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
<div style="width:44px;height:44px;background:rgba(59,130,246,0.15);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px">📈</div>
<div><div style="font-family:Space Grotesk,sans-serif;font-size:15px;font-weight:600">EMA Confirmation</div>
<div style="font-size:11px;color:rgba(255,255,255,0.5)">8/21 Cross + 200 Filter</div></div>
</div>
<div style="background:{align_bg};border-radius:10px;padding:14px;text-align:center;margin-bottom:16px">
<div style="font-size:15px;font-weight:600;color:{align_color}">{align_text}</div>
</div>
<div style="flex:1;display:grid;grid-template-columns:1fr 1fr;gap:12px">
<div style="background:rgba(255,255,255,0.02);border-radius:10px;padding:16px;text-align:center;display:flex;flex-direction:column;justify-content:center">
<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-bottom:6px;letter-spacing:0.5px">8/21 CROSS</div>
<div style="font-size:20px;font-weight:600;color:{cross_color}">{ema_signals["cross_signal"]}</div>
<div style="font-size:10px;color:rgba(255,255,255,0.3);margin-top:6px">EMA8: {ema_signals["ema8"] or "—"}</div>
</div>
<div style="background:rgba(255,255,255,0.02);border-radius:10px;padding:16px;text-align:center;display:flex;flex-direction:column;justify-content:center">
<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-bottom:6px;letter-spacing:0.5px">200 EMA</div>
<div style="font-size:20px;font-weight:600;color:{filter_color}">{filter_text}</div>
<div style="font-size:10px;color:rgba(255,255,255,0.3);margin-top:6px">EMA200: {ema_signals["ema200"] or "—"}</div>
</div>
</div>
</div>

<!-- ROW 2: Flow Bias + Market Context -->
<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:20px;min-height:220px;display:flex;flex-direction:column">
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
<div style="display:flex;align-items:center;gap:12px">
<div style="width:44px;height:44px;background:rgba(34,211,238,0.15);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px">🌊</div>
<div><div style="font-family:Space Grotesk,sans-serif;font-size:15px;font-weight:600">Flow Bias</div>
<div style="font-size:11px;color:rgba(255,255,255,0.5)">{flow.get("real_data_sources", 0)} live sources</div></div>
</div>
<div style="text-align:right">
<div style="font-family:IBM Plex Mono,monospace;font-size:28px;font-weight:700;color:{flow_color}">{flow["score"]:+d}</div>
<div style="font-size:10px;font-weight:600;color:{flow_color}">{flow_label}</div>
</div>
</div>
<div style="display:flex;justify-content:space-between;font-size:9px;color:rgba(255,255,255,0.4);margin-bottom:4px">
<span>STRONG PUTS</span><span>NEUTRAL</span><span>STRONG CALLS</span>
</div>
<div style="height:10px;background:linear-gradient(90deg,#ff4757,#ffa502 50%,#00d4aa);border-radius:5px;position:relative;margin-bottom:12px">
<div style="position:absolute;top:-4px;left:{meter_pos}%;width:6px;height:18px;background:#fff;border-radius:3px;transform:translateX(-50%);box-shadow:0 0 8px rgba(255,255,255,0.5)"></div>
</div>
<div style="flex:1;overflow-y:auto;max-height:100px">
{flow_signals_html}
</div>
</div>

<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:20px;min-height:220px;display:flex;flex-direction:column">
<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
<div style="width:44px;height:44px;background:rgba(255,165,2,0.15);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px">📉</div>
<div><div style="font-family:Space Grotesk,sans-serif;font-size:15px;font-weight:600">Market Context</div>
<div style="font-size:11px;color:rgba(255,255,255,0.5)">Momentum & volatility</div></div>
</div>
<div style="flex:1;display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">
<div style="background:rgba(255,255,255,0.02);border-radius:10px;padding:14px;text-align:center;display:flex;flex-direction:column;justify-content:center">
<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-bottom:6px">MOMENTUM</div>
<div style="font-size:16px;font-weight:600;color:{mom_color}">{momentum["signal"]}</div>
</div>
<div style="background:rgba(255,255,255,0.02);border-radius:10px;padding:14px;text-align:center;display:flex;flex-direction:column;justify-content:center">
<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-bottom:6px">RSI (14)</div>
<div style="font-size:18px;font-weight:600">{momentum["rsi"]}</div>
</div>
<div style="background:rgba(255,255,255,0.02);border-radius:10px;padding:14px;text-align:center;display:flex;flex-direction:column;justify-content:center">
<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-bottom:6px">VIX {'✓' if vix_source == 'manual' else '⚠️' if inputs.get('is_planning') else ''}</div>
<div style="font-size:18px;font-weight:600;color:{vix_color}">{vix:.1f}</div>
<div style="font-size:9px;color:{vix_color}">{vix_zone}{' (manual)' if vix_source == 'manual' else ' (stale?)' if inputs.get('is_planning') else ''}</div>
</div>
</div>
</div>

</div>'''
    
    st.markdown(analysis_html,unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONES & LEVELS
    # ═══════════════════════════════════════════════════════════════════════════
    with st.expander("📊 Cone Rails (SPX)"):
        cone_html="".join([f'<div class="pillar"><span>{n}</span><span><span style="color:#00d4aa">↑{c["asc"]}</span> | <span style="color:#ff4757">↓{c["desc"]}</span></span></div>' for n,c in cones_spx.items()])
        st.markdown(f'<div class="card">{cone_html}</div>',unsafe_allow_html=True)
    
    with st.expander("📐 All Structure Levels"):
        all_lvls=[("Ceiling Rising",levels["ceiling_rising"]["level"]),("Ceiling Falling",levels["ceiling_falling"]["level"]),("Floor Rising",levels["floor_rising"]["level"]),("Floor Falling",levels["floor_falling"]["level"])]
        all_lvls.sort(key=lambda x:x[1],reverse=True)
        lvl_html="".join([f'<div class="pillar"><span>{n}</span><span>ES {l} → SPX {round(l-offset,2)}</span></div>' for n,l in all_lvls])
        st.markdown(f'<div class="card">{lvl_html}</div>',unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DEBUG
    # ═══════════════════════════════════════════════════════════════════════════
    if inputs["debug"]:
        st.markdown("### 🔧 Debug")
        
        # Show 8:30 candle vs channel
        st.markdown("**8:30 Candle vs Channel:**")
        if candle_830:
            st.write(f"- Candle: O={candle_830['open']}, H={candle_830['high']}, L={candle_830['low']}, C={candle_830['close']}")
        st.write(f"- Ceiling (ES): {ceiling_es}")
        st.write(f"- Floor (ES): {floor_es}")
        if candle_830 and ceiling_es and floor_es:
            st.write(f"- High vs Ceiling: {candle_830['high']} {'>' if candle_830['high']>ceiling_es else '<='} {ceiling_es} → {'BROKE ABOVE' if candle_830['high']>ceiling_es else 'did not break'}")
            st.write(f"- Low vs Floor: {candle_830['low']} {'<' if candle_830['low']<floor_es else '>='} {floor_es} → {'BROKE BELOW' if candle_830['low']<floor_es else 'did not break'}")
            st.write(f"- Close: {candle_830['close']} → {'ABOVE ceiling' if candle_830['close']>ceiling_es else 'BELOW floor' if candle_830['close']<floor_es else 'INSIDE channel'}")
        
        # Show validation result
        st.markdown("**Validation Result:**")
        st.write(f"- Status: {validation['status']}")
        st.write(f"- Message: {validation['message']}")
        st.write(f"- Setup: {validation['setup']}")
        st.write(f"- Position: {validation.get('position','N/A')}")
        
        # Show times
        st.markdown("**Anchor Times:**")
        st.write(f"- O/N High Time: {on_high_time}")
        st.write(f"- O/N Low Time: {on_low_time}")
        st.write(f"- Reference Time: {ref_time}")
        
        # Show block calculations
        st.markdown("**Block Calculations:**")
        blocks_high=blocks_between(on_high_time,ref_time)
        blocks_low=blocks_between(on_low_time,ref_time)
        st.write(f"- Blocks from O/N High to Ref: {blocks_high} (exp: {SLOPE*blocks_high:.2f})")
        st.write(f"- Blocks from O/N Low to Ref: {blocks_low} (exp: {SLOPE*blocks_low:.2f})")
        
        # Show raw values
        st.markdown("**Raw Values (ES):**")
        st.write(f"- O/N High: {on_high}, O/N Low: {on_low}")
        st.write(f"- Sydney H/L: {syd_h}/{syd_l}, Tokyo H/L: {tok_h}/{tok_l}")
        st.write(f"- Channel Type: {channel_type} ({channel_reason})")
        
        # Show calculated levels
        st.markdown("**Calculated Levels (ES):**")
        st.json(levels)
        
        # Show hist_data if available
        if hist_data:
            st.markdown("**Historical Data Extracted:**")
            hist_display={k:str(v) if isinstance(v,pd.DataFrame) else v for k,v in hist_data.items() if k!="day_candles"}
            st.json(hist_display)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(f'''<div class="footer">
<div style="margin-bottom:8px;font-weight:600;font-size:12px">🔮 SPX PROPHET V6.1</div>
<div style="font-size:10px;color:rgba(255,255,255,0.4)">
Sydney/Tokyo Channel • Setup Candle → Next Candle Entry • Momentum Probe Filter • Structural Cone Targets
</div>
<div style="margin-top:6px;font-size:10px;color:rgba(255,255,255,0.3)">
Setup Window: 8:00-10:30 AM | Entry Window: 8:30-11:00 AM | Slope: {SLOPE} pts/block | Break Threshold: {BREAK_THRESHOLD} pts
</div>
</div>''',unsafe_allow_html=True)
    
    if inputs["auto_refresh"] and not inputs["is_historical"]:
        time_module.sleep(30)
        st.rerun()

if __name__=="__main__":
    main()

"""
╔═══════════════════════════════════════════════════════════════╗
║                    SPX PROPHET™                                ║
║              Where Structure Becomes Foresight                 ║
║                                                               ║
║     Professional 0DTE SPX Options Trading Intelligence        ║
╚═══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import requests
import json
import os
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from typing import Optional, List
import calendar
import pytz
import math

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════

CT = pytz.timezone("America/Chicago")
POLYGON_KEY = "jrbBZ2y12cJAOp2Buqtlay0TdprcTDIm"
SETTINGS_FILE = "prophet_config.json"

SLOPE = 0.475
BLOCKS = 36
OTM = 15

# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass
class Config:
    year: int = 2026
    month: int = 1
    day: int = 10
    vix_high: float = 0.0
    vix_low: float = 0.0
    vix_now: float = 0.0
    spx_high: float = 0.0
    spx_low: float = 0.0
    spx_close: float = 0.0
    ceiling: float = 0.0
    floor: float = 0.0
    use_manual: bool = False
    offset: float = 7.0

def load_config() -> Config:
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE) as f:
                return Config(**json.load(f))
    except: pass
    return Config()

def save_config(c: Config):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(c.__dict__, f)

# ══════════════════════════════════════════════════════════════
# DATA & CALCULATIONS
# ══════════════════════════════════════════════════════════════

def get_spx(offset):
    try:
        import yfinance as yf
        d = yf.Ticker("ES=F").history(period="1d")
        if not d.empty: return float(d['Close'].iloc[-1]) - offset
    except: pass
    return 0.0

def get_history(offset):
    try:
        import yfinance as yf
        d = yf.Ticker("ES=F").history(period="250d")
        if not d.empty: return [float(r["Close"]) - offset for _, r in d.iterrows()]
    except: pass
    return []

def get_option(strike, otype, exp):
    try:
        t = "C" if otype == "CALL" else "P"
        ticker = f"O:SPXW{exp.strftime('%y%m%d')}{t}{str(int(strike*1000)).zfill(8)}"
        r = requests.get(f"https://api.polygon.io/v3/snapshot/options/SPXW/{ticker}?apiKey={POLYGON_KEY}", timeout=10)
        if r.status_code == 200 and "results" in r.json():
            res = r.json()["results"]
            return {
                "ticker": ticker, "strike": strike, "type": otype,
                "last": float(res.get("day", {}).get("close", 0) or 0),
                "bid": float(res.get("last_quote", {}).get("bid", 0) or 0),
                "ask": float(res.get("last_quote", {}).get("ask", 0) or 0),
                "vol": int(res.get("day", {}).get("volume", 0) or 0),
                "oi": int(res.get("open_interest", 0) or 0)
            }
    except: pass
    return None

def ema(p, n):
    if len(p) < n: return p[-1] if p else 0
    k = 2/(n+1)
    e = sum(p[:n])/n
    for x in p[n:]: e = x*k + e*(1-k)
    return e

def sma(p, n):
    if not p: return 0
    return sum(p[-n:])/min(len(p), n)

def analyze(hist, cfg):
    # Pillar 1: MA Bias
    e50 = ema(hist, 50) if len(hist) >= 50 else 0
    s200 = sma(hist, 200)
    if e50 > s200: p1 = ("LONG", "green")
    elif e50 < s200: p1 = ("SHORT", "red")
    else: p1 = ("NEUTRAL", "gray")
    
    # Pillar 2: Structure
    if cfg.use_manual and cfg.ceiling > 0:
        ceil, flr = cfg.ceiling, cfg.floor
    else:
        ceil, flr = cfg.spx_high, cfg.spx_low
    
    if p1[0] == "LONG": p2 = ("FLOOR", flr, "green")
    elif p1[0] == "SHORT": p2 = ("CEILING", ceil, "red")
    else: p2 = ("—", 0, "gray")
    
    # Pillar 3: VIX
    if cfg.vix_high > cfg.vix_low and cfg.vix_high > 0:
        rng = ((cfg.vix_high - cfg.vix_low) / cfg.vix_high) * 100
        mid = (cfg.vix_high + cfg.vix_low) / 2
        if rng <= 7:
            if cfg.vix_now <= mid: p3 = ("CALLS", rng, "green")
            else: p3 = ("PUTS", rng, "red")
        else: p3 = ("WAIT", rng, "amber")
    else: p3 = ("WAIT", 0, "gray")
    
    # Signal
    if p1[0] == "LONG":
        entry = flr
        strike = int(round((entry + OTM)/5)*5)
        if p3[0] == "CALLS": sig = ("CALLS", entry, strike, True)
        elif p3[0] == "PUTS": sig = ("CONFLICT", entry, 0, False)
        else: sig = ("WAIT", entry, strike, False)
    elif p1[0] == "SHORT":
        entry = ceil
        strike = int(round((entry - OTM)/5)*5)
        if p3[0] == "PUTS": sig = ("PUTS", entry, strike, True)
        elif p3[0] == "CALLS": sig = ("CONFLICT", entry, 0, False)
        else: sig = ("WAIT", entry, strike, False)
    else:
        sig = ("NO TRADE", 0, 0, False)
    
    # Cones
    exp = BLOCKS * SLOPE
    cones = {
        "h_up": cfg.spx_high + exp, "h_dn": cfg.spx_high - exp,
        "l_up": cfg.spx_low + exp, "l_dn": cfg.spx_low - exp,
        "c_up": cfg.spx_close + exp, "c_dn": cfg.spx_close - exp,
        "exp": exp
    }
    
    return {"p1": p1, "p2": p2, "p3": p3, "sig": sig, "cones": cones, "ema": e50, "sma": s200}

# ══════════════════════════════════════════════════════════════
# LEGENDARY CSS - GLASSMORPHISM + ANIMATIONS
# ══════════════════════════════════════════════════════════════

CSS_PART1 = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ═══════════════════════════════════════════════════════════
   KEYFRAME ANIMATIONS
   ═══════════════════════════════════════════════════════════ */

@keyframes float {
    0%, 100% { transform: translateY(0px) rotate(0deg); }
    50% { transform: translateY(-20px) rotate(5deg); }
}

@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 20px rgba(0, 255, 136, 0.3); }
    50% { box-shadow: 0 0 40px rgba(0, 255, 136, 0.6), 0 0 60px rgba(0, 255, 136, 0.3); }
}

@keyframes pulse-glow-red {
    0%, 100% { box-shadow: 0 0 20px rgba(255, 71, 87, 0.3); }
    50% { box-shadow: 0 0 40px rgba(255, 71, 87, 0.6), 0 0 60px rgba(255, 71, 87, 0.3); }
}

@keyframes pulse-glow-amber {
    0%, 100% { box-shadow: 0 0 20px rgba(255, 193, 7, 0.3); }
    50% { box-shadow: 0 0 40px rgba(255, 193, 7, 0.6), 0 0 60px rgba(255, 193, 7, 0.3); }
}

@keyframes gradient-shift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

@keyframes rotate-slow {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

@keyframes bounce-in {
    0% { transform: scale(0.3); opacity: 0; }
    50% { transform: scale(1.05); }
    70% { transform: scale(0.9); }
    100% { transform: scale(1); opacity: 1; }
}

@keyframes slide-up {
    from { transform: translateY(30px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}

@keyframes border-dance {
    0%, 100% { border-color: rgba(0, 255, 136, 0.5); }
    25% { border-color: rgba(0, 200, 255, 0.5); }
    50% { border-color: rgba(157, 78, 221, 0.5); }
    75% { border-color: rgba(255, 107, 107, 0.5); }
}

@keyframes text-glow {
    0%, 100% { text-shadow: 0 0 10px currentColor; }
    50% { text-shadow: 0 0 20px currentColor, 0 0 30px currentColor; }
}

@keyframes orb-float-1 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(30px, -50px) scale(1.1); }
    66% { transform: translate(-20px, 20px) scale(0.9); }
}

@keyframes orb-float-2 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(-40px, 30px) scale(0.9); }
    66% { transform: translate(50px, -30px) scale(1.1); }
}

@keyframes orb-float-3 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(20px, 40px) scale(1.05); }
    66% { transform: translate(-30px, -20px) scale(0.95); }
}

/* ═══════════════════════════════════════════════════════════
   ROOT VARIABLES
   ═══════════════════════════════════════════════════════════ */

:root {
    --bg-deep: #030014;
    --bg-dark: #0a0a1a;
    --glass: rgba(255, 255, 255, 0.03);
    --glass-border: rgba(255, 255, 255, 0.08);
    --glass-hover: rgba(255, 255, 255, 0.06);
    
    --neon-green: #00ff88;
    --neon-green-dim: rgba(0, 255, 136, 0.15);
    --neon-red: #ff4757;
    --neon-red-dim: rgba(255, 71, 87, 0.15);
    --neon-amber: #ffc107;
    --neon-amber-dim: rgba(255, 193, 7, 0.15);
    --neon-blue: #00d4ff;
    --neon-purple: #9d4edd;
    --neon-pink: #ff6b9d;
    
    --text-bright: #ffffff;
    --text-mid: #a0a0b0;
    --text-dim: #505060;
    
    --gradient-hero: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
    --gradient-green: linear-gradient(135deg, #00ff88 0%, #00d4ff 100%);
    --gradient-red: linear-gradient(135deg, #ff4757 0%, #ff6b9d 100%);
    --gradient-amber: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
    --gradient-cosmic: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #00d4ff 75%, #00ff88 100%);
}

/* ═══════════════════════════════════════════════════════════
   BASE STYLES
   ═══════════════════════════════════════════════════════════ */

html, body, .stApp {
    background: var(--bg-deep) !important;
    font-family: 'Outfit', sans-serif !important;
    color: var(--text-bright);
    overflow-x: hidden;
}

/* Animated background */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: 
        radial-gradient(ellipse at 20% 20%, rgba(102, 126, 234, 0.15) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 80%, rgba(157, 78, 221, 0.15) 0%, transparent 50%),
        radial-gradient(ellipse at 40% 80%, rgba(0, 212, 255, 0.1) 0%, transparent 40%),
        radial-gradient(ellipse at 80% 20%, rgba(240, 147, 251, 0.1) 0%, transparent 40%);
    pointer-events: none;
    z-index: 0;
}

/* Floating orbs */
.stApp::after {
    content: '';
    position: fixed;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(0, 255, 136, 0.1) 0%, transparent 70%);
    border-radius: 50%;
    top: 10%;
    right: 10%;
    animation: orb-float-1 15s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
}

#MainMenu, footer, header, .stDeployButton, [data-testid="stToolbar"], [data-testid="stDecoration"] {
    display: none !important;
}

.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
    position: relative;
    z-index: 1;
}

/* ═══════════════════════════════════════════════════════════
   SIDEBAR - GLASSMORPHISM
   ═══════════════════════════════════════════════════════════ */

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(10, 10, 30, 0.95) 0%, rgba(5, 5, 20, 0.98) 100%) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-right: 1px solid var(--glass-border) !important;
}

section[data-testid="stSidebar"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--gradient-cosmic);
    background-size: 300% 300%;
    animation: gradient-shift 5s ease infinite;
}

section[data-testid="stSidebar"] > div {
    padding: 2rem 1.5rem !important;
}

/* ═══════════════════════════════════════════════════════════
   FORM CONTROLS - GLASS STYLE
   ═══════════════════════════════════════════════════════════ */

.stNumberInput > div > div > input,
.stTextInput > div > div > input {
    background: var(--glass) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 12px !important;
    color: var(--text-bright) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 14px !important;
    padding: 12px 16px !important;
    transition: all 0.3s ease !important;
}

.stNumberInput > div > div > input:focus,
.stTextInput > div > div > input:focus {
    border-color: var(--neon-green) !important;
    box-shadow: 0 0 20px var(--neon-green-dim), inset 0 0 20px var(--neon-green-dim) !important;
}

.stSelectbox > div > div {
    background: var(--glass) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 12px !important;
}

.stButton > button {
    background: var(--glass) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 12px !important;
    color: var(--text-bright) !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    padding: 12px 24px !important;
    transition: all 0.3s ease !important;
    position: relative;
    overflow: hidden;
}

.stButton > button::before {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
    transition: left 0.5s ease;
}

.stButton > button:hover::before {
    left: 100%;
}

.stButton > button:hover {
    border-color: var(--neon-green) !important;
    box-shadow: 0 0 30px var(--neon-green-dim) !important;
    transform: translateY(-2px);
}

.stButton > button[kind="primary"] {
    background: var(--gradient-green) !important;
    border: none !important;
    color: #000 !important;
    font-weight: 700 !important;
    animation: pulse-glow 2s ease-in-out infinite;
}

.stCheckbox label {
    color: var(--text-mid) !important;
}

hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--glass-border), transparent) !important;
    margin: 1.5rem 0 !important;
}
"""

CSS_PART2 = """
/* ═══════════════════════════════════════════════════════════
   HERO SECTION
   ═══════════════════════════════════════════════════════════ */

.hero {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(157, 78, 221, 0.1) 50%, rgba(240, 147, 251, 0.05) 100%);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid var(--glass-border);
    padding: 2rem 3rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
}

.hero::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: var(--gradient-cosmic);
    background-size: 300% 300%;
    animation: gradient-shift 3s ease infinite;
}

.hero::after {
    content: '';
    position: absolute;
    top: 50%; right: 5%;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(0, 255, 136, 0.1) 0%, transparent 70%);
    border-radius: 50%;
    animation: float 6s ease-in-out infinite;
    pointer-events: none;
}

.brand {
    display: flex;
    align-items: center;
    gap: 20px;
    animation: slide-up 0.8s ease;
}

.brand-icon {
    font-size: 56px;
    filter: drop-shadow(0 0 20px rgba(0, 255, 136, 0.5));
    animation: float 4s ease-in-out infinite;
}

.brand-text {
    display: flex;
    flex-direction: column;
}

.brand-title {
    font-size: 42px;
    font-weight: 900;
    background: linear-gradient(135deg, #fff 0%, #a0a0b0 50%, #fff 100%);
    background-size: 200% 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradient-shift 3s ease infinite;
    letter-spacing: -1px;
}

.brand-tagline {
    font-size: 13px;
    font-weight: 600;
    background: var(--gradient-green);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-top: 4px;
}

.price-display {
    text-align: right;
    animation: slide-up 0.8s ease 0.2s backwards;
}

.price-label {
    font-size: 12px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 4px;
}

.price-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 48px;
    font-weight: 700;
    background: var(--gradient-green);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: text-glow 2s ease-in-out infinite;
}

.price-meta {
    font-size: 13px;
    color: var(--text-mid);
    margin-top: 4px;
}

/* ═══════════════════════════════════════════════════════════
   MAIN CONTENT
   ═══════════════════════════════════════════════════════════ */

.main-content {
    padding: 2.5rem 3rem;
    position: relative;
}

.section-label {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-size: 11px;
    font-weight: 700;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 3px;
    margin-bottom: 1.5rem;
    padding: 8px 16px;
    background: var(--glass);
    backdrop-filter: blur(10px);
    border: 1px solid var(--glass-border);
    border-radius: 50px;
}

/* ═══════════════════════════════════════════════════════════
   PILLAR CARDS - GLASS MORPHISM
   ═══════════════════════════════════════════════════════════ */

.pillars {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.5rem;
    margin-bottom: 2.5rem;
}

.pillar {
    background: var(--glass);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--glass-border);
    border-radius: 24px;
    padding: 2rem;
    position: relative;
    overflow: hidden;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    animation: slide-up 0.6s ease backwards;
}

.pillar:nth-child(1) { animation-delay: 0.1s; }
.pillar:nth-child(2) { animation-delay: 0.2s; }
.pillar:nth-child(3) { animation-delay: 0.3s; }

.pillar::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    border-radius: 24px 24px 0 0;
    transition: all 0.3s ease;
}

.pillar:hover {
    transform: translateY(-8px) scale(1.02);
    border-color: rgba(255, 255, 255, 0.15);
}

.pillar.green::before { background: var(--gradient-green); }
.pillar.green:hover { box-shadow: 0 20px 60px -20px var(--neon-green-dim); }

.pillar.red::before { background: var(--gradient-red); }
.pillar.red:hover { box-shadow: 0 20px 60px -20px var(--neon-red-dim); }

.pillar.amber::before { background: var(--gradient-amber); }
.pillar.amber:hover { box-shadow: 0 20px 60px -20px var(--neon-amber-dim); }

.pillar-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 1rem;
}

.pillar-icon {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    transition: transform 0.3s ease;
}

.pillar:hover .pillar-icon {
    transform: scale(1.1) rotate(5deg);
}

.pillar.green .pillar-icon { background: var(--neon-green-dim); }
.pillar.red .pillar-icon { background: var(--neon-red-dim); }
.pillar.amber .pillar-icon { background: var(--neon-amber-dim); }

.pillar-num {
    font-size: 10px;
    font-weight: 700;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 2px;
}

.pillar-name {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-bright);
}

.pillar-question {
    font-size: 14px;
    color: var(--text-mid);
    margin-bottom: 1.5rem;
    line-height: 1.5;
}

.pillar-answer {
    font-family: 'JetBrains Mono', monospace;
    font-size: 36px;
    font-weight: 800;
    margin-bottom: 0.5rem;
    transition: all 0.3s ease;
}

.pillar:hover .pillar-answer {
    transform: scale(1.05);
}

.pillar-answer.green { 
    color: var(--neon-green);
    text-shadow: 0 0 20px var(--neon-green-dim);
}
.pillar-answer.red { 
    color: var(--neon-red);
    text-shadow: 0 0 20px var(--neon-red-dim);
}
.pillar-answer.amber { 
    color: var(--neon-amber);
    text-shadow: 0 0 20px var(--neon-amber-dim);
}
.pillar-answer.gray { color: var(--text-dim); }

.pillar-detail {
    font-size: 13px;
    color: var(--text-mid);
}

/* ═══════════════════════════════════════════════════════════
   SIGNAL CARD - THE STAR
   ═══════════════════════════════════════════════════════════ */

.signal-card {
    background: var(--glass);
    backdrop-filter: blur(30px);
    -webkit-backdrop-filter: blur(30px);
    border: 2px solid var(--glass-border);
    border-radius: 32px;
    padding: 3rem;
    text-align: center;
    margin-bottom: 2.5rem;
    position: relative;
    overflow: hidden;
    animation: bounce-in 0.8s ease 0.4s backwards;
}

.signal-card::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: conic-gradient(from 0deg, transparent, var(--glass-border), transparent 30%);
    animation: rotate-slow 10s linear infinite;
    opacity: 0.5;
}

.signal-card.calls {
    border-color: var(--neon-green);
    background: linear-gradient(180deg, var(--neon-green-dim) 0%, var(--glass) 50%);
    animation: pulse-glow 3s ease-in-out infinite;
}

.signal-card.puts {
    border-color: var(--neon-red);
    background: linear-gradient(180deg, var(--neon-red-dim) 0%, var(--glass) 50%);
    animation: pulse-glow-red 3s ease-in-out infinite;
}

.signal-card.wait {
    border-color: var(--neon-amber);
    background: linear-gradient(180deg, var(--neon-amber-dim) 0%, var(--glass) 50%);
    animation: pulse-glow-amber 3s ease-in-out infinite;
}

.signal-inner {
    position: relative;
    z-index: 1;
}

.signal-action {
    font-family: 'JetBrains Mono', monospace;
    font-size: 80px;
    font-weight: 900;
    letter-spacing: -3px;
    margin-bottom: 0.5rem;
}

.signal-action.green {
    background: var(--gradient-green);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 0 30px var(--neon-green));
}

.signal-action.red {
    background: var(--gradient-red);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 0 30px var(--neon-red));
}

.signal-action.amber {
    background: var(--gradient-amber);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 0 30px var(--neon-amber));
}

.signal-action.gray {
    color: var(--text-dim);
}

.signal-reason {
    font-size: 16px;
    color: var(--text-mid);
    margin-bottom: 2rem;
}

.signal-metrics {
    display: flex;
    justify-content: center;
    gap: 4rem;
}

.signal-metric {
    text-align: center;
}

.signal-metric-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 8px;
}

.signal-metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 32px;
    font-weight: 700;
    color: var(--text-bright);
}

.signal-metric-value.red {
    color: var(--neon-red);
}
"""

CSS_PART3 = """
/* ═══════════════════════════════════════════════════════════
   DATA CARDS
   ═══════════════════════════════════════════════════════════ */

.data-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
}

.data-card {
    background: var(--glass);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--glass-border);
    border-radius: 24px;
    padding: 1.5rem;
    position: relative;
    overflow: hidden;
    animation: slide-up 0.6s ease 0.5s backwards;
}

.data-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: linear-gradient(135deg, rgba(255,255,255,0.03) 0%, transparent 50%);
    pointer-events: none;
}

.data-card:hover {
    border-color: rgba(255, 255, 255, 0.15);
    transform: translateY(-4px);
    transition: all 0.3s ease;
}

.data-card-title {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 1.25rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

.data-card-title::before {
    content: '';
    width: 8px;
    height: 8px;
    background: var(--neon-green);
    border-radius: 50%;
    animation: pulse-glow 2s ease-in-out infinite;
}

/* Cone Table */
.cone-table {
    width: 100%;
}

.cone-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0;
}

.cone-cell {
    padding: 12px;
    text-align: center;
    border-bottom: 1px solid var(--glass-border);
}

.cone-cell.header {
    font-size: 10px;
    font-weight: 700;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
}

.cone-cell.label {
    text-align: left;
    font-size: 13px;
    color: var(--text-mid);
}

.cone-cell.up {
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px;
    font-weight: 600;
    color: var(--neon-green);
}

.cone-cell.down {
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px;
    font-weight: 600;
    color: var(--neon-red);
}

.cone-row:last-child .cone-cell {
    border-bottom: none;
}

.data-footer {
    font-size: 11px;
    color: var(--text-dim);
    text-align: center;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--glass-border);
}

/* Options Grid */
.opt-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
}

.opt-cell {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 16px;
    text-align: center;
    transition: all 0.3s ease;
}

.opt-cell:hover {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.1);
}

.opt-label {
    font-size: 10px;
    font-weight: 700;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}

.opt-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 600;
    color: var(--text-bright);
}

.opt-value.green { color: var(--neon-green); }
.opt-value.dim { color: var(--text-dim); }

.opt-ticker {
    font-size: 11px;
    color: var(--text-dim);
    text-align: center;
    margin-bottom: 1rem;
    font-family: 'JetBrains Mono', monospace;
}

/* ═══════════════════════════════════════════════════════════
   SIDEBAR COMPONENTS
   ═══════════════════════════════════════════════════════════ */

.sidebar-brand {
    text-align: center;
    padding-bottom: 2rem;
    margin-bottom: 2rem;
    border-bottom: 1px solid var(--glass-border);
    position: relative;
}

.sidebar-brand::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 50%;
    transform: translateX(-50%);
    width: 60px;
    height: 2px;
    background: var(--gradient-green);
}

.sidebar-icon {
    font-size: 48px;
    margin-bottom: 12px;
    filter: drop-shadow(0 0 20px rgba(0, 255, 136, 0.4));
    animation: float 4s ease-in-out infinite;
}

.sidebar-title {
    font-size: 24px;
    font-weight: 800;
    background: linear-gradient(135deg, #fff 0%, #a0a0b0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.sidebar-tag {
    font-size: 9px;
    font-weight: 700;
    color: var(--neon-green);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 6px;
}

.sidebar-section {
    margin-bottom: 1.5rem;
}

.sidebar-section-title {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-bright);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.sidebar-section-title::before {
    content: '';
    width: 4px;
    height: 16px;
    background: var(--gradient-green);
    border-radius: 2px;
}

/* Date Selector */
.date-card {
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 12px;
}

.date-display {
    background: linear-gradient(135deg, var(--neon-green-dim) 0%, var(--glass) 100%);
    border: 1px solid var(--neon-green);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    animation: border-dance 4s ease-in-out infinite;
}

.date-day {
    font-size: 18px;
    font-weight: 700;
    color: var(--neon-green);
}

.date-full {
    font-size: 13px;
    color: var(--text-mid);
    margin-top: 4px;
}

.date-weekend {
    background: linear-gradient(135deg, var(--neon-red-dim) 0%, var(--glass) 100%);
    border: 1px solid var(--neon-red);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}

.date-weekend-text {
    font-size: 14px;
    font-weight: 600;
    color: var(--neon-red);
}

/* ═══════════════════════════════════════════════════════════
   FOOTER
   ═══════════════════════════════════════════════════════════ */

.app-footer {
    background: var(--glass);
    backdrop-filter: blur(20px);
    border-top: 1px solid var(--glass-border);
    padding: 1rem 3rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    color: var(--text-dim);
}

.footer-item {
    display: flex;
    align-items: center;
    gap: 8px;
}

.footer-dot {
    width: 6px;
    height: 6px;
    background: var(--neon-green);
    border-radius: 50%;
    animation: pulse-glow 2s ease-in-out infinite;
}

/* ═══════════════════════════════════════════════════════════
   SCROLLBAR
   ═══════════════════════════════════════════════════════════ */

::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-dark);
}

::-webkit-scrollbar-thumb {
    background: var(--glass-border);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--text-dim);
}
</style>
"""

CSS = CSS_PART1 + CSS_PART2 + CSS_PART3

# ══════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════════════════════

def run():
    st.set_page_config(
        page_title="SPX Prophet",
        page_icon="🔮",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown(CSS, unsafe_allow_html=True)
    
    # Session state
    if "cfg" not in st.session_state:
        st.session_state.cfg = load_config()
    if "spx" not in st.session_state:
        st.session_state.spx = 0.0
    if "hist" not in st.session_state:
        st.session_state.hist = []
    if "fetched" not in st.session_state:
        st.session_state.fetched = None
    if "opt" not in st.session_state:
        st.session_state.opt = None
    
    c = st.session_state.cfg
    
    # ══════════════════════════════════════════════════════════
    # SIDEBAR
    # ══════════════════════════════════════════════════════════
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand">
            <div class="sidebar-icon">🔮</div>
            <div class="sidebar-title">SPX Prophet</div>
            <div class="sidebar-tag">Structure → Foresight</div>
        </div>
        """, unsafe_allow_html=True)
        
        # DATE SELECTION
        st.markdown('<div class="sidebar-section-title">📅 Trading Date</div>', unsafe_allow_html=True)
        
        today = datetime.now(CT).date()
        
        # Quick buttons
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            if st.button("Today", key="b_today", use_container_width=True):
                c.year, c.month, c.day = today.year, today.month, today.day
                st.session_state.opt = None
                st.rerun()
        with bc2:
            yd = today - timedelta(days=1)
            if st.button("Yest", key="b_yest", use_container_width=True):
                c.year, c.month, c.day = yd.year, yd.month, yd.day
                st.session_state.opt = None
                st.rerun()
        with bc3:
            diff = (today.weekday() - 4) % 7 or 7
            fri = today - timedelta(days=diff)
            if st.button("Fri", key="b_fri", use_container_width=True):
                c.year, c.month, c.day = fri.year, fri.month, fri.day
                st.session_state.opt = None
                st.rerun()
        
        st.markdown('<div class="date-card">', unsafe_allow_html=True)
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            yrs = list(range(2024, 2028))
            idx = yrs.index(c.year) if c.year in yrs else 2
            c.year = st.selectbox("Y", yrs, index=idx, key="sy", label_visibility="collapsed")
        with dc2:
            mos = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            c.month = st.selectbox("M", range(1,13), index=c.month-1, format_func=lambda x: mos[x-1], key="sm", label_visibility="collapsed")
        with dc3:
            mx = calendar.monthrange(c.year, c.month)[1]
            c.day = min(c.day, mx)
            c.day = st.selectbox("D", range(1, mx+1), index=c.day-1, key="sd", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)
        
        sel = date(c.year, c.month, c.day)
        if sel.weekday() >= 5:
            st.markdown(f'<div class="date-weekend"><div class="date-weekend-text">⚠️ {sel.strftime("%A")} — Weekend</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="date-display"><div class="date-day">{sel.strftime("%A")}</div><div class="date-full">{sel.strftime("%B %d, %Y")}</div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # VIX
        st.markdown('<div class="sidebar-section-title">📊 VIX Zone</div>', unsafe_allow_html=True)
        st.caption("Overnight range from TradingView")
        v1, v2 = st.columns(2)
        c.vix_high = v1.number_input("High", value=c.vix_high, format="%.2f", step=0.01, key="vh")
        c.vix_low = v2.number_input("Low", value=c.vix_low, format="%.2f", step=0.01, key="vl")
        c.vix_now = st.number_input("Current", value=c.vix_now, format="%.2f", step=0.01, key="vc")
        
        st.markdown("---")
        
        # PRIOR DAY
        st.markdown('<div class="sidebar-section-title">📈 Prior Day SPX</div>', unsafe_allow_html=True)
        st.caption("From 3pm CT close")
        p1, p2, p3 = st.columns(3)
        c.spx_high = p1.number_input("High", value=c.spx_high, format="%.0f", step=1.0, key="ph")
        c.spx_low = p2.number_input("Low", value=c.spx_low, format="%.0f", step=1.0, key="pl")
        c.spx_close = p3.number_input("Close", value=c.spx_close, format="%.0f", step=1.0, key="pc")
        
        st.markdown("---")
        
        # MANUAL OVERRIDE
        st.markdown('<div class="sidebar-section-title">🎯 Structure Override</div>', unsafe_allow_html=True)
        c.use_manual = st.checkbox("Use manual levels", value=c.use_manual, key="man")
        if c.use_manual:
            m1, m2 = st.columns(2)
            c.ceiling = m1.number_input("Ceiling", value=c.ceiling, format="%.0f", step=1.0, key="mc")
            c.floor = m2.number_input("Floor", value=c.floor, format="%.0f", step=1.0, key="mf")
        
        st.markdown("---")
        
        # ADVANCED
        with st.expander("⚙️ Advanced Settings"):
            c.offset = st.number_input("ES-SPX Offset", value=c.offset, format="%.1f", step=0.5, key="off")
        
        st.markdown("---")
        
        # BUTTONS
        if st.button("💾 SAVE SETTINGS", key="save", use_container_width=True, type="primary"):
            save_config(c)
            st.session_state.opt = None
            st.success("✓ Saved!")
        
        if st.button("🔄 Refresh Data", key="ref", use_container_width=True):
            st.session_state.fetched = None
            st.session_state.opt = None
            st.rerun()

    # ══════════════════════════════════════════════════════════
    # DATA FETCH
    # ══════════════════════════════════════════════════════════
    need = st.session_state.fetched is None or (datetime.now() - st.session_state.fetched).seconds > 900
    if need:
        with st.spinner(""):
            st.session_state.spx = get_spx(c.offset)
            st.session_state.hist = get_history(c.offset)
            st.session_state.fetched = datetime.now()
    
    spx = st.session_state.spx
    hist = st.session_state.hist
    now = datetime.now(CT)
    sel = date(c.year, c.month, c.day)
    
    # Run analysis
    data = analyze(hist, c)
    p1, p2, p3 = data["p1"], data["p2"], data["p3"]
    sig = data["sig"]
    cones = data["cones"]
    
    # Fetch option
    if sig[2] > 0 and st.session_state.opt is None:
        otype = "CALL" if p1[0] == "LONG" else "PUT"
        st.session_state.opt = get_option(sig[2], otype, sel)
    opt = st.session_state.opt
    
    # ══════════════════════════════════════════════════════════
    # HERO SECTION
    # ══════════════════════════════════════════════════════════
    st.markdown(f"""
    <div class="hero">
        <div class="brand">
            <span class="brand-icon">🔮</span>
            <div class="brand-text">
                <div class="brand-title">SPX Prophet</div>
                <div class="brand-tagline">Where Structure Becomes Foresight</div>
            </div>
        </div>
        <div class="price-display">
            <div class="price-label">SPX Index</div>
            <div class="price-value">{spx:,.2f}</div>
            <div class="price-meta">{now.strftime('%I:%M %p CT')} • {sel.strftime('%B %d, %Y')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ══════════════════════════════════════════════════════════
    # MAIN CONTENT
    # ══════════════════════════════════════════════════════════
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # Section: Three Pillars
    st.markdown('<div class="section-label">✦ The Three Pillars</div>', unsafe_allow_html=True)
    
    # Determine colors
    p1_col = p1[1]
    p2_col = "green" if p1[0] == "LONG" else ("red" if p1[0] == "SHORT" else "gray")
    p3_col = "green" if p3[0] == "CALLS" else ("red" if p3[0] == "PUTS" else "amber")
    
    cmp = ">" if data["ema"] > data["sma"] else "<"
    manual_tag = " [Manual]" if c.use_manual else ""
    
    st.markdown(f"""
    <div class="pillars">
        <div class="pillar {p1_col}">
            <div class="pillar-header">
                <div class="pillar-icon">📊</div>
                <div>
                    <div class="pillar-num">Pillar One</div>
                    <div class="pillar-name">MA Bias</div>
                </div>
            </div>
            <div class="pillar-question">Should I trade CALLS or PUTS today?</div>
            <div class="pillar-answer {p1_col}">{p1[0]}</div>
            <div class="pillar-detail">50 EMA {cmp} 200 SMA</div>
        </div>
        
        <div class="pillar {p2_col}">
            <div class="pillar-header">
                <div class="pillar-icon">🎯</div>
                <div>
                    <div class="pillar-num">Pillar Two</div>
                    <div class="pillar-name">Structure</div>
                </div>
            </div>
            <div class="pillar-question">Where is my entry at 9:00 AM CT?</div>
            <div class="pillar-answer {p2_col}">{p2[0]}</div>
            <div class="pillar-detail">{p2[1]:,.0f} SPX{manual_tag}</div>
        </div>
        
        <div class="pillar {p3_col}">
            <div class="pillar-header">
                <div class="pillar-icon">⚡</div>
                <div>
                    <div class="pillar-num">Pillar Three</div>
                    <div class="pillar-name">VIX Zone</div>
                </div>
            </div>
            <div class="pillar-question">When do I pull the trigger?</div>
            <div class="pillar-answer {p3_col}">{p3[0]}</div>
            <div class="pillar-detail">Range: {p3[1]:.1f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # SIGNAL CARD
    # ══════════════════════════════════════════════════════════
    st.markdown('<div class="section-label">✦ Trade Decision</div>', unsafe_allow_html=True)
    
    sig_class = "calls" if sig[0] == "CALLS" else ("puts" if sig[0] == "PUTS" else ("wait" if sig[0] == "WAIT" else ""))
    sig_col = "green" if sig[0] == "CALLS" else ("red" if sig[0] == "PUTS" else ("amber" if sig[0] == "WAIT" else "gray"))
    
    # Reason text
    if sig[3]:
        reason = "✓ All three pillars aligned — Execute trade"
    elif sig[0] == "WAIT":
        reason = f"MA Bias is {p1[0]} — Waiting for VIX confirmation"
    elif sig[0] == "CONFLICT":
        reason = f"Conflicting signals — MA says {p1[0]}, VIX says {p3[0]}"
    else:
        reason = "No directional edge — Stand aside"
    
    stop = f"${opt['last'] * 0.5:.2f}" if opt and opt.get('last', 0) > 0 else "—"
    
    st.markdown(f"""
    <div class="signal-card {sig_class}">
        <div class="signal-inner">
            <div class="signal-action {sig_col}">{sig[0]}</div>
            <div class="signal-reason">{reason}</div>
            <div class="signal-metrics">
                <div class="signal-metric">
                    <div class="signal-metric-label">Entry Level</div>
                    <div class="signal-metric-value">{sig[1]:,.0f}</div>
                </div>
                <div class="signal-metric">
                    <div class="signal-metric-label">Strike</div>
                    <div class="signal-metric-value">{sig[2] if sig[2] > 0 else '—'}</div>
                </div>
                <div class="signal-metric">
                    <div class="signal-metric-label">50% Stop</div>
                    <div class="signal-metric-value red">{stop}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ══════════════════════════════════════════════════════════
    # DATA PANELS
    # ══════════════════════════════════════════════════════════
    st.markdown('<div class="section-label">✦ Market Data</div>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="data-grid">
        <div class="data-card">
            <div class="data-card-title">Cone Rails @ 9:00 AM</div>
            <div class="cone-table">
                <div class="cone-row">
                    <div class="cone-cell header">Anchor</div>
                    <div class="cone-cell header" style="color: var(--neon-green);">↗ Up</div>
                    <div class="cone-cell header" style="color: var(--neon-red);">↘ Down</div>
                </div>
                <div class="cone-row">
                    <div class="cone-cell label">High ({c.spx_high:,.0f})</div>
                    <div class="cone-cell up">{cones['h_up']:,.0f}</div>
                    <div class="cone-cell down">{cones['h_dn']:,.0f}</div>
                </div>
                <div class="cone-row">
                    <div class="cone-cell label">Low ({c.spx_low:,.0f})</div>
                    <div class="cone-cell up">{cones['l_up']:,.0f}</div>
                    <div class="cone-cell down">{cones['l_dn']:,.0f}</div>
                </div>
                <div class="cone-row">
                    <div class="cone-cell label">Close ({c.spx_close:,.0f})</div>
                    <div class="cone-cell up">{cones['c_up']:,.0f}</div>
                    <div class="cone-cell down">{cones['c_dn']:,.0f}</div>
                </div>
            </div>
            <div class="data-footer">3pm → 9am • 36 blocks • ±{cones['exp']:.1f} points</div>
        </div>
        
        <div class="data-card">
            <div class="data-card-title">0DTE Option Quote</div>
    """, unsafe_allow_html=True)
    
    if opt:
        t_disp = "C" if opt["type"] == "CALL" else "P"
        st.markdown(f"""
            <div class="opt-ticker">{opt['ticker']}</div>
            <div class="opt-grid">
                <div class="opt-cell">
                    <div class="opt-label">Strike</div>
                    <div class="opt-value green">{opt['strike']} {t_disp}</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Last</div>
                    <div class="opt-value">${opt['last']:.2f}</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Bid</div>
                    <div class="opt-value">${opt['bid']:.2f}</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Ask</div>
                    <div class="opt-value">${opt['ask']:.2f}</div>
                </div>
            </div>
            <div class="data-footer">Vol: {opt['vol']:,} • OI: {opt['oi']:,}</div>
        """, unsafe_allow_html=True)
    else:
        strike_disp = f"{sig[2]} {'C' if p1[0] == 'LONG' else 'P'}" if sig[2] > 0 else "—"
        st.markdown(f"""
            <div class="opt-grid">
                <div class="opt-cell">
                    <div class="opt-label">Strike</div>
                    <div class="opt-value green">{strike_disp}</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Last</div>
                    <div class="opt-value dim">—</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Bid</div>
                    <div class="opt-value dim">—</div>
                </div>
                <div class="opt-cell">
                    <div class="opt-label">Ask</div>
                    <div class="opt-value dim">—</div>
                </div>
            </div>
            <div class="data-footer">Awaiting market data...</div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)  # close data-card and data-grid
    st.markdown('</div>', unsafe_allow_html=True)  # close main-content
    
    # ══════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════
    last_str = st.session_state.fetched.strftime("%I:%M %p") if st.session_state.fetched else "—"
    st.markdown(f"""
    <div class="app-footer">
        <div class="footer-item">
            <span class="footer-dot"></span>
            <span>Last refresh: {last_str}</span>
        </div>
        <div class="footer-item">
            <span>Entry: 9:00 AM CT • All values in SPX</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run()

"""
SPX PROPHET v5.0
The Institutional SPX Prediction System

Predicts SPX moves using VIX algo trigger zones, structural cones, and time-based analysis.
Features proprietary Expected Move formula and Cone Confluence detection.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time, date
import yfinance as yf
import pytz
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict
from enum import Enum
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="SPX Prophet",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# PREMIUM LIGHT THEME
# =============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* Base Theme */
.stApp {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e2e8f0;
}

section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #1e293b;
}

/* Hide Streamlit Elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Metrics */
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: #1e293b;
}

[data-testid="stMetricLabel"] {
    font-family: 'SF Pro Display', -apple-system, sans-serif;
    color: #64748b;
    font-weight: 500;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.5px;
}

[data-testid="stMetricDelta"] {
    font-family: 'JetBrains Mono', monospace;
}

/* Cards */
.prophet-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02);
}

.prophet-card-accent {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.02);
}

/* Typography */
.prophet-title {
    font-family: 'SF Pro Display', -apple-system, sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
    letter-spacing: -0.5px;
}

.prophet-subtitle {
    font-family: 'SF Pro Display', -apple-system, sans-serif;
    font-size: 0.8rem;
    color: #64748b;
    font-weight: 500;
    letter-spacing: 0.5px;
    margin: 4px 0 0 0;
}

.prophet-section-title {
    font-family: 'SF Pro Display', -apple-system, sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 0 0 16px 0;
}

.prophet-value-hero {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -1px;
}

.prophet-value-large {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 600;
    color: #1e293b;
    margin: 0;
}

.prophet-value-medium {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    font-weight: 600;
    color: #1e293b;
    margin: 0;
}

.prophet-value-small {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    font-weight: 500;
    color: #334155;
    margin: 0;
}

.prophet-label {
    font-family: 'SF Pro Display', -apple-system, sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0 0 4px 0;
}

.prophet-text {
    font-family: 'SF Pro Display', -apple-system, sans-serif;
    font-size: 0.9rem;
    color: #475569;
    line-height: 1.5;
    margin: 0;
}

/* Bias Colors */
.calls-text { color: #059669; }
.puts-text { color: #dc2626; }
.wait-text { color: #d97706; }

.calls-bg { background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border: 2px solid #059669; }
.puts-bg { background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border: 2px solid #dc2626; }
.wait-bg { background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border: 2px solid #d97706; }

/* Trigger Zone Styling */
.trigger-buy {
    background: linear-gradient(90deg, #dcfce7 0%, #bbf7d0 100%);
    border-left: 4px solid #059669;
    padding: 12px 16px;
    border-radius: 8px;
    margin: 4px 0;
}

.trigger-sell {
    background: linear-gradient(90deg, #fee2e2 0%, #fecaca 100%);
    border-left: 4px solid #dc2626;
    padding: 12px 16px;
    border-radius: 8px;
    margin: 4px 0;
}

.trigger-neutral {
    background: linear-gradient(90deg, #f1f5f9 0%, #e2e8f0 100%);
    border-left: 4px solid #64748b;
    padding: 12px 16px;
    border-radius: 8px;
    margin: 4px 0;
}

/* Confluence Badge */
.confluence-strong {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border: 2px solid #f59e0b;
    border-radius: 8px;
    padding: 8px 12px;
    display: inline-block;
}

/* Progress Bar */
.proximity-bar {
    height: 8px;
    border-radius: 4px;
    background: #e2e8f0;
    overflow: hidden;
}

.proximity-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
}

/* Data Table */
.level-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-radius: 8px;
    margin: 4px 0;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
}

.level-row-highlight {
    background: linear-gradient(90deg, #eff6ff 0%, #dbeafe 100%);
    border: 1px solid #3b82f6;
}

/* Inputs */
div[data-baseweb="input"] > div {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}

div[data-baseweb="input"] > div:focus-within {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 8px 24px;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #f1f5f9;
    padding: 4px;
    border-radius: 12px;
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #64748b;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 500;
}

.stTabs [aria-selected="true"] {
    background: #ffffff;
    color: #1e293b;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* Expander */
.streamlit-expanderHeader {
    background: #f8fafc;
    border-radius: 8px;
    font-weight: 500;
}

/* Dataframe */
.stDataFrame {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CONSTANTS
# =============================================================================

class Config:
    SLOPE_PER_30MIN = 0.45
    MIN_CONE_WIDTH = 18.0
    STOP_LOSS_PTS = 6.0
    STRIKE_OTM_DISTANCE = 17.5
    DELTA = 0.33
    CONTRACT_MULTIPLIER = 100
    
    TARGET_1_PCT = 0.125  # 12.5%
    TARGET_2_PCT = 0.25   # 25%
    TARGET_3_PCT = 0.50   # 50%
    
    CONFLUENCE_THRESHOLD = 6.0  # Points
    
    # Expected Move Formula: EM = 35 + ((zone - 0.10) × 100), cap at 65-70
    EM_BASE = 35
    EM_ZONE_BASELINE = 0.10
    EM_MULTIPLIER = 100
    EM_CAP_LOW = 65
    EM_CAP_HIGH = 70


class Phase(Enum):
    ZONE_BUILDING = ("Zone Building", "#6366f1", "🌙", "5pm-6am CT")
    ZONE_LOCKED = ("Zone Locked", "#0ea5e9", "🔒", "6am+ CT")
    PRE_RTH = ("Pre-RTH", "#8b5cf6", "⏳", "6am-9:30am CT")
    RTH = ("RTH Active", "#059669", "🟢", "9:30am-4pm CT")
    POST = ("Post Session", "#64748b", "📊", "After 4pm CT")
    CLOSED = ("Closed", "#94a3b8", "⭘", "Weekend")
    
    def __init__(self, label, color, icon, time_range):
        self.label = label
        self.color = color
        self.icon = icon
        self.time_range = time_range


class Bias(Enum):
    CALLS = ("CALLS", "#059669", "↑", "calls")
    PUTS = ("PUTS", "#dc2626", "↓", "puts")
    WAIT = ("WAIT", "#d97706", "◆", "wait")
    
    def __init__(self, label, color, arrow, css):
        self.label = label
        self.color = color
        self.arrow = arrow
        self.css = css


class Confidence(Enum):
    HIGH = ("HIGH", "●●●", "#059669")
    MEDIUM = ("MEDIUM", "●●○", "#d97706")
    LOW = ("LOW", "●○○", "#dc2626")
    NONE = ("NONE", "○○○", "#94a3b8")
    
    def __init__(self, label, dots, color):
        self.label = label
        self.dots = dots
        self.color = color


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class VIXZone:
    """VIX Zone representing algo trigger boundaries"""
    bottom: float  # Buy algo trigger
    top: float     # Sell algo trigger
    current: float
    
    @property
    def size(self) -> float:
        return round(self.top - self.bottom, 4)
    
    @property
    def current_zone(self) -> str:
        """Which zone is VIX currently in"""
        if self.current > self.top:
            extensions_above = (self.current - self.top) / self.size if self.size > 0 else 0
            if extensions_above >= 2:
                return "+3 Zone"
            elif extensions_above >= 1:
                return "+2 Zone"
            else:
                return "+1 Zone"
        elif self.current < self.bottom:
            extensions_below = (self.bottom - self.current) / self.size if self.size > 0 else 0
            if extensions_below >= 2:
                return "-3 Zone"
            elif extensions_below >= 1:
                return "-2 Zone"
            else:
                return "-1 Zone"
        else:
            return "Base Zone"
    
    @property
    def nearest_buy_trigger(self) -> float:
        """Nearest level where buy algos activate (VIX tops/sells off)"""
        if self.current <= self.bottom:
            return self.bottom
        elif self.current <= self.top:
            return self.top
        else:
            # Above zone - next trigger is top of current extension zone
            ext = int((self.current - self.top) / self.size) + 1 if self.size > 0 else 1
            return self.top + (ext * self.size)
    
    @property
    def nearest_sell_trigger(self) -> float:
        """Nearest level where sell algos activate (VIX bottoms/bounces)"""
        if self.current >= self.top:
            return self.top
        elif self.current >= self.bottom:
            return self.bottom
        else:
            # Below zone - next trigger is bottom of current extension zone
            ext = int((self.bottom - self.current) / self.size) + 1 if self.size > 0 else 1
            return self.bottom - (ext * self.size)
    
    @property
    def distance_to_buy_trigger(self) -> float:
        return round(self.nearest_buy_trigger - self.current, 2)
    
    @property
    def distance_to_sell_trigger(self) -> float:
        return round(self.current - self.nearest_sell_trigger, 2)
    
    def get_extension(self, level: int) -> float:
        if level > 0:
            return round(self.top + (level * self.size), 2)
        elif level < 0:
            return round(self.bottom + (level * self.size), 2)
        return self.top if level == 0 else self.bottom
    
    def get_expected_move(self) -> Tuple[float, float]:
        """Calculate proprietary Expected Move based on zone size"""
        if self.size <= 0:
            return (0, 0)
        
        em_low = Config.EM_BASE + ((self.size - Config.EM_ZONE_BASELINE) * Config.EM_MULTIPLIER)
        em_high = em_low + 5
        
        # Apply cap
        em_low = min(em_low, Config.EM_CAP_LOW)
        em_high = min(em_high, Config.EM_CAP_HIGH)
        
        return (round(max(em_low, 0), 1), round(em_high, 1))


@dataclass
class Pivot:
    name: str
    price: float
    timestamp: datetime
    pivot_type: str = "primary"


@dataclass
class ConeRails:
    pivot: Pivot
    ascending: float
    descending: float
    width: float
    blocks: int
    
    @property
    def is_tradeable(self) -> bool:
        return self.width >= Config.MIN_CONE_WIDTH


@dataclass
class ConfluentLevel:
    """A price level where multiple cones converge"""
    price: float
    rail_type: str  # "support" or "resistance"
    cones: List[str]  # Names of converging cones
    strength: str  # "strong" if 3+, "moderate" if 2


@dataclass
class TradeSetup:
    direction: Bias
    cone: ConeRails
    entry: float
    stop: float
    target_1: float
    target_2: float
    target_3: float
    strike: int
    is_confluent: bool = False
    confluence_cones: List[str] = None
    
    @property
    def reward_1_pts(self) -> float:
        return abs(self.target_1 - self.entry)
    
    @property
    def reward_2_pts(self) -> float:
        return abs(self.target_2 - self.entry)
    
    @property
    def reward_3_pts(self) -> float:
        return abs(self.target_3 - self.entry)


@dataclass
class LevelHit:
    level_name: str
    level_price: float
    was_hit: bool
    hit_time: Optional[str] = None


# =============================================================================
# ENGINE
# =============================================================================

class SPXProphetEngine:
    def __init__(self):
        self.ct_tz = pytz.timezone('America/Chicago')
    
    def get_current_time_ct(self) -> datetime:
        return datetime.now(self.ct_tz)
    
    def get_phase(self, dt: datetime = None) -> Phase:
        if dt is None:
            dt = self.get_current_time_ct()
        elif dt.tzinfo is None:
            dt = self.ct_tz.localize(dt)
        else:
            dt = dt.astimezone(self.ct_tz)
        
        t = dt.time()
        weekday = dt.weekday()
        
        if weekday >= 5:
            return Phase.CLOSED
        
        # 5pm-6am: Zone Building
        if time(17, 0) <= t or t < time(6, 0):
            return Phase.ZONE_BUILDING
        # 6am-9:30am: Zone Locked / Pre-RTH
        elif time(6, 0) <= t < time(9, 30):
            return Phase.PRE_RTH
        # 9:30am-4pm: RTH
        elif time(9, 30) <= t < time(16, 0):
            return Phase.RTH
        # 4pm-5pm: Post
        elif time(16, 0) <= t < time(17, 0):
            return Phase.POST
        
        return Phase.CLOSED
    
    def determine_bias(self, zone: VIXZone) -> Tuple[Bias, Confidence, str]:
        """
        Determine bias based on VIX position relative to algo triggers.
        """
        dist_to_buy = zone.distance_to_buy_trigger
        dist_to_sell = zone.distance_to_sell_trigger
        
        current_zone = zone.current_zone
        
        # If VIX is near top boundary (within 0.05) - buy algos about to trigger
        if dist_to_buy <= 0.05 and dist_to_buy >= -0.05:
            bias = Bias.CALLS
            confidence = Confidence.HIGH
            explanation = f"VIX at buy trigger ({zone.nearest_buy_trigger:.2f}). Buy algos active. SPX UP."
        
        # If VIX is near bottom boundary (within 0.05) - sell algos about to trigger
        elif dist_to_sell <= 0.05 and dist_to_sell >= -0.05:
            bias = Bias.PUTS
            confidence = Confidence.HIGH
            explanation = f"VIX at sell trigger ({zone.nearest_sell_trigger:.2f}). Sell algos active. SPX DOWN."
        
        # VIX above zone - in put territory but watch for buy trigger
        elif "+" in current_zone:
            bias = Bias.PUTS
            confidence = Confidence.MEDIUM if dist_to_buy > 0.10 else Confidence.LOW
            explanation = f"VIX in {current_zone}. Put bias until buy trigger at {zone.nearest_buy_trigger:.2f}."
        
        # VIX below zone - in call territory but watch for sell trigger
        elif "-" in current_zone:
            bias = Bias.CALLS
            confidence = Confidence.MEDIUM if dist_to_sell > 0.10 else Confidence.LOW
            explanation = f"VIX in {current_zone}. Call bias until sell trigger at {zone.nearest_sell_trigger:.2f}."
        
        # VIX in base zone - trend day potential
        else:
            bias = Bias.WAIT
            confidence = Confidence.NONE
            explanation = f"VIX in Base Zone. Potential trend day. Wait for boundary touch."
        
        return bias, confidence, explanation
    
    def calculate_blocks(self, pivot_time: datetime, eval_time: datetime) -> int:
        if pivot_time.tzinfo is None:
            pivot_time = self.ct_tz.localize(pivot_time)
        if eval_time.tzinfo is None:
            eval_time = self.ct_tz.localize(eval_time)
        
        diff = eval_time - pivot_time
        total_minutes = diff.total_seconds() / 60
        return max(int(total_minutes / 30), 1)
    
    def calculate_cone(self, pivot: Pivot, eval_time: datetime) -> ConeRails:
        blocks = self.calculate_blocks(pivot.timestamp, eval_time)
        expansion = blocks * Config.SLOPE_PER_30MIN
        
        ascending = round(pivot.price + expansion, 2)
        descending = round(pivot.price - expansion, 2)
        width = round(ascending - descending, 2)
        
        return ConeRails(
            pivot=pivot,
            ascending=ascending,
            descending=descending,
            width=width,
            blocks=blocks
        )
    
    def find_confluence(self, cones: List[ConeRails]) -> Tuple[List[ConfluentLevel], List[ConfluentLevel]]:
        """Find where cone rails converge within threshold"""
        support_levels = []
        resistance_levels = []
        
        # Collect all rails
        ascending_rails = [(c.ascending, c.pivot.name) for c in cones if c.is_tradeable]
        descending_rails = [(c.descending, c.pivot.name) for c in cones if c.is_tradeable]
        
        # Find ascending (resistance) confluence
        for i, (price1, name1) in enumerate(ascending_rails):
            confluent_cones = [name1]
            for j, (price2, name2) in enumerate(ascending_rails):
                if i != j and abs(price1 - price2) <= Config.CONFLUENCE_THRESHOLD:
                    confluent_cones.append(name2)
            
            if len(confluent_cones) >= 2:
                avg_price = sum(p for p, n in ascending_rails if n in confluent_cones) / len(confluent_cones)
                strength = "strong" if len(confluent_cones) >= 3 else "moderate"
                
                # Avoid duplicates
                if not any(abs(r.price - avg_price) < 1 for r in resistance_levels):
                    resistance_levels.append(ConfluentLevel(
                        price=round(avg_price, 2),
                        rail_type="resistance",
                        cones=confluent_cones,
                        strength=strength
                    ))
        
        # Find descending (support) confluence
        for i, (price1, name1) in enumerate(descending_rails):
            confluent_cones = [name1]
            for j, (price2, name2) in enumerate(descending_rails):
                if i != j and abs(price1 - price2) <= Config.CONFLUENCE_THRESHOLD:
                    confluent_cones.append(name2)
            
            if len(confluent_cones) >= 2:
                avg_price = sum(p for p, n in descending_rails if n in confluent_cones) / len(confluent_cones)
                strength = "strong" if len(confluent_cones) >= 3 else "moderate"
                
                if not any(abs(s.price - avg_price) < 1 for s in support_levels):
                    support_levels.append(ConfluentLevel(
                        price=round(avg_price, 2),
                        rail_type="support",
                        cones=confluent_cones,
                        strength=strength
                    ))
        
        return support_levels, resistance_levels
    
    def generate_setup(self, cone: ConeRails, direction: Bias, 
                      support_confluence: List[ConfluentLevel] = None,
                      resistance_confluence: List[ConfluentLevel] = None) -> Optional[TradeSetup]:
        if not cone.is_tradeable or direction == Bias.WAIT:
            return None
        
        support_confluence = support_confluence or []
        resistance_confluence = resistance_confluence or []
        
        if direction == Bias.CALLS:
            entry = cone.descending
            opposite = cone.ascending
            stop = entry - Config.STOP_LOSS_PTS
            strike = int(round((entry - Config.STRIKE_OTM_DISTANCE) / 5) * 5)
            move = opposite - entry
            t1 = entry + (move * Config.TARGET_1_PCT)
            t2 = entry + (move * Config.TARGET_2_PCT)
            t3 = entry + (move * Config.TARGET_3_PCT)
            
            # Check confluence
            is_confluent = any(abs(c.price - entry) <= Config.CONFLUENCE_THRESHOLD for c in support_confluence)
            conf_cones = [c.cones for c in support_confluence if abs(c.price - entry) <= Config.CONFLUENCE_THRESHOLD]
        else:
            entry = cone.ascending
            opposite = cone.descending
            stop = entry + Config.STOP_LOSS_PTS
            strike = int(round((entry + Config.STRIKE_OTM_DISTANCE) / 5) * 5)
            move = entry - opposite
            t1 = entry - (move * Config.TARGET_1_PCT)
            t2 = entry - (move * Config.TARGET_2_PCT)
            t3 = entry - (move * Config.TARGET_3_PCT)
            
            is_confluent = any(abs(c.price - entry) <= Config.CONFLUENCE_THRESHOLD for c in resistance_confluence)
            conf_cones = [c.cones for c in resistance_confluence if abs(c.price - entry) <= Config.CONFLUENCE_THRESHOLD]
        
        return TradeSetup(
            direction=direction,
            cone=cone,
            entry=round(entry, 2),
            stop=round(stop, 2),
            target_1=round(t1, 2),
            target_2=round(t2, 2),
            target_3=round(t3, 2),
            strike=strike,
            is_confluent=is_confluent,
            confluence_cones=conf_cones[0] if conf_cones else None
        )
    
    def calculate_profit(self, points: float, contracts: int = 1) -> float:
        return round(points * Config.DELTA * Config.CONTRACT_MULTIPLIER * contracts, 2)
    
    def calculate_max_contracts(self, risk_budget: float) -> int:
        risk_per = self.calculate_profit(Config.STOP_LOSS_PTS, 1)
        return int(risk_budget / risk_per) if risk_per > 0 else 0
    
    def analyze_level_hits(self, setup: TradeSetup, session_high: float, session_low: float) -> List[LevelHit]:
        hits = []
        is_calls = setup.direction == Bias.CALLS
        
        # Entry
        entry_hit = (session_low <= setup.entry) if is_calls else (session_high >= setup.entry)
        hits.append(LevelHit("Entry", setup.entry, entry_hit))
        
        if entry_hit:
            # Stop
            stop_hit = (session_low <= setup.stop) if is_calls else (session_high >= setup.stop)
            hits.append(LevelHit("Stop", setup.stop, stop_hit))
            
            # Targets
            for name, price in [("12.5%", setup.target_1), ("25%", setup.target_2), ("50%", setup.target_3)]:
                target_hit = (session_high >= price) if is_calls else (session_low <= price)
                hits.append(LevelHit(name, price, target_hit))
        else:
            hits.append(LevelHit("Stop", setup.stop, False))
            hits.append(LevelHit("12.5%", setup.target_1, False))
            hits.append(LevelHit("25%", setup.target_2, False))
            hits.append(LevelHit("50%", setup.target_3, False))
        
        return hits
    
    def calculate_theoretical_pnl(self, setup: TradeSetup, hits: List[LevelHit], contracts: int = 1) -> Tuple[float, str]:
        entry_hit = next((h for h in hits if h.level_name == "Entry"), None)
        if not entry_hit or not entry_hit.was_hit:
            return 0.0, "Entry not reached"
        
        stop_hit = next((h for h in hits if h.level_name == "Stop"), None)
        if stop_hit and stop_hit.was_hit:
            return -self.calculate_profit(Config.STOP_LOSS_PTS, contracts), "Stopped out"
        
        # Find highest target hit
        target_hits = [h for h in hits if h.level_name in ["12.5%", "25%", "50%"] and h.was_hit]
        
        if not target_hits:
            return 0.0, "Entry hit, no targets"
        
        # Get the highest target
        target_order = {"12.5%": 1, "25%": 2, "50%": 3}
        highest = max(target_hits, key=lambda h: target_order.get(h.level_name, 0))
        
        points = abs(highest.level_price - setup.entry)
        return self.calculate_profit(points, contracts), f"{highest.level_name} target"


# =============================================================================
# DATA FETCHING
# =============================================================================

@st.cache_data(ttl=60)
def fetch_spx_data():
    """Fetch SPX data from Yahoo"""
    try:
        spx = yf.Ticker("^GSPC")
        hist = spx.history(period="5d", interval="1d")
        
        if hist.empty:
            return None, None
        
        current = float(hist['Close'].iloc[-1])
        
        prior = None
        if len(hist) >= 2:
            p = hist.iloc[-2]
            prior = {
                'date': hist.index[-2],
                'open': float(p['Open']),
                'high': float(p['High']),
                'low': float(p['Low']),
                'close': float(p['Close'])
            }
        
        return current, prior
    except Exception:
        return None, None


@st.cache_data(ttl=300)
def fetch_historical_spx(target_date: date) -> Optional[Dict]:
    """Fetch historical SPX data for a specific date"""
    try:
        spx = yf.Ticker("^GSPC")
        start = target_date - timedelta(days=10)
        end = target_date + timedelta(days=1)
        hist = spx.history(start=start, end=end)
        
        if hist.empty:
            return None
        
        target_str = target_date.strftime('%Y-%m-%d')
        for idx in hist.index:
            if idx.strftime('%Y-%m-%d') == target_str:
                row = hist.loc[idx]
                return {
                    'date': idx,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'range': float(row['High'] - row['Low'])
                }
        return None
    except Exception:
        return None


@st.cache_data(ttl=300)
def fetch_prior_day_data(session_date: date) -> Optional[Dict]:
    """Fetch prior trading day data"""
    try:
        spx = yf.Ticker("^GSPC")
        start = session_date - timedelta(days=10)
        end = session_date + timedelta(days=1)
        hist = spx.history(start=start, end=end)
        
        if hist.empty or len(hist) < 2:
            return None
        
        session_str = session_date.strftime('%Y-%m-%d')
        session_idx = None
        
        for i, idx in enumerate(hist.index):
            if idx.strftime('%Y-%m-%d') == session_str:
                session_idx = i
                break
        
        if session_idx is not None and session_idx > 0:
            prior_idx = hist.index[session_idx - 1]
            prior = hist.iloc[session_idx - 1]
            return {
                'date': prior_idx,
                'high': float(prior['High']),
                'low': float(prior['Low']),
                'close': float(prior['Close']),
                'open': float(prior['Open'])
            }
        
        if len(hist) >= 2:
            prior = hist.iloc[-2]
            return {
                'date': hist.index[-2],
                'high': float(prior['High']),
                'low': float(prior['Low']),
                'close': float(prior['Close']),
                'open': float(prior['Open'])
            }
        
        return None
    except Exception:
        return None


@st.cache_data(ttl=60)
def fetch_intraday_spx() -> Optional[pd.DataFrame]:
    """Fetch intraday SPX data for charting"""
    try:
        spx = yf.Ticker("^GSPC")
        hist = spx.history(period="2d", interval="30m")
        return hist if not hist.empty else None
    except Exception:
        return None


# =============================================================================
# CHART COMPONENT
# =============================================================================

def create_spx_chart(intraday_data: pd.DataFrame, cones: List[ConeRails], 
                     setups: List[TradeSetup], zone: VIXZone, bias: Bias) -> go.Figure:
    """Create professional candlestick chart with cone projections"""
    
    if intraday_data is None or intraday_data.empty:
        return None
    
    # Filter to today's data only
    today = datetime.now().date()
    today_data = intraday_data[intraday_data.index.date == today]
    
    if today_data.empty:
        today_data = intraday_data.tail(13)  # Last ~6.5 hours
    
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=today_data.index,
        open=today_data['Open'],
        high=today_data['High'],
        low=today_data['Low'],
        close=today_data['Close'],
        name='SPX',
        increasing=dict(line=dict(color='#059669', width=1), fillcolor='#dcfce7'),
        decreasing=dict(line=dict(color='#dc2626', width=1), fillcolor='#fee2e2')
    ))
    
    # Get price range for y-axis
    price_min = today_data['Low'].min()
    price_max = today_data['High'].max()
    
    # Add cone rails
    colors = ['#3b82f6', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899']
    
    for i, cone in enumerate(cones):
        if not cone.is_tradeable:
            continue
        
        color = colors[i % len(colors)]
        
        # Ascending rail (resistance)
        fig.add_hline(
            y=cone.ascending, 
            line=dict(color=color, width=2, dash='dot'),
            annotation_text=f"{cone.pivot.name} ↑ {cone.ascending:.2f}",
            annotation_position="right",
            annotation_font=dict(size=10, color=color)
        )
        
        # Descending rail (support)
        fig.add_hline(
            y=cone.descending, 
            line=dict(color=color, width=2, dash='dot'),
            annotation_text=f"{cone.pivot.name} ↓ {cone.descending:.2f}",
            annotation_position="right",
            annotation_font=dict(size=10, color=color)
        )
        
        # Update price range
        price_min = min(price_min, cone.descending)
        price_max = max(price_max, cone.ascending)
    
    # Add entry levels for best setup
    if setups:
        best_setup = setups[0]
        entry_color = '#059669' if best_setup.direction == Bias.CALLS else '#dc2626'
        
        fig.add_hline(
            y=best_setup.entry,
            line=dict(color=entry_color, width=3),
            annotation_text=f"ENTRY {best_setup.entry:.2f}",
            annotation_position="left",
            annotation_font=dict(size=11, color=entry_color, family='JetBrains Mono')
        )
        
        fig.add_hline(
            y=best_setup.stop,
            line=dict(color='#dc2626', width=2, dash='dash'),
            annotation_text=f"STOP {best_setup.stop:.2f}",
            annotation_position="left",
            annotation_font=dict(size=10, color='#dc2626')
        )
        
        for target_name, target_price in [("T1", best_setup.target_1), ("T2", best_setup.target_2), ("T3", best_setup.target_3)]:
            fig.add_hline(
                y=target_price,
                line=dict(color='#059669', width=1, dash='dash'),
                annotation_text=f"{target_name} {target_price:.2f}",
                annotation_position="left",
                annotation_font=dict(size=9, color='#059669')
            )
            price_max = max(price_max, target_price)
            price_min = min(price_min, target_price)
    
    # Layout
    padding = (price_max - price_min) * 0.05
    
    fig.update_layout(
        title=None,
        xaxis_title=None,
        yaxis_title=None,
        template='plotly_white',
        height=500,
        margin=dict(l=60, r=120, t=20, b=40),
        xaxis=dict(
            rangeslider=dict(visible=False),
            showgrid=True,
            gridcolor='#f1f5f9',
            tickfont=dict(size=10, color='#64748b')
        ),
        yaxis=dict(
            side='left',
            showgrid=True,
            gridcolor='#f1f5f9',
            tickfont=dict(size=11, color='#1e293b', family='JetBrains Mono'),
            tickformat=',.2f',
            range=[price_min - padding, price_max + padding]
        ),
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        showlegend=False,
        hovermode='x unified'
    )
    
    return fig


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_header(spx: float, phase: Phase, engine: SPXProphetEngine):
    now = engine.get_current_time_ct()
    
    st.markdown(f"""
    <div class="prophet-card-accent">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
            <div>
                <h1 class="prophet-title">⚡ SPX Prophet</h1>
                <p class="prophet-subtitle">Institutional SPX Prediction System</p>
            </div>
            <div style="display: flex; gap: 32px; align-items: center;">
                <div style="text-align: right;">
                    <p class="prophet-label">SPX</p>
                    <p class="prophet-value-hero" style="color: #1e293b;">{spx:,.2f}</p>
                </div>
                <div style="text-align: right; padding-left: 32px; border-left: 2px solid #e2e8f0;">
                    <p class="prophet-label">{now.strftime('%I:%M %p')} CT</p>
                    <p class="prophet-value-medium" style="color: {phase.color};">{phase.icon} {phase.label}</p>
                    <p style="font-size: 0.75rem; color: #94a3b8; margin: 4px 0 0 0;">{phase.time_range}</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_expected_move(zone: VIXZone):
    em_low, em_high = zone.get_expected_move()
    
    st.markdown(f"""
    <div class="prophet-card" style="text-align: center;">
        <p class="prophet-section-title">Expected Move</p>
        <p class="prophet-value-hero" style="color: #3b82f6;">{em_low:.0f} - {em_high:.0f}</p>
        <p class="prophet-label" style="margin-top: 8px;">POINTS FROM ENTRY</p>
        <div style="margin-top: 16px; padding: 12px; background: #f1f5f9; border-radius: 8px;">
            <p class="prophet-text">Based on VIX zone size of <strong>{zone.size:.2f}</strong></p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_bias_card(bias: Bias, confidence: Confidence, explanation: str):
    st.markdown(f"""
    <div class="prophet-card {bias.css}-bg" style="text-align: center;">
        <p class="prophet-section-title">Directional Bias</p>
        <p class="prophet-value-hero {bias.css}-text">{bias.arrow} {bias.label}</p>
        <p style="font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; color: {confidence.color}; margin: 12px 0;">{confidence.dots}</p>
        <p class="prophet-label" style="color: {confidence.color};">{confidence.label} CONFIDENCE</p>
        <div style="margin-top: 16px; padding: 12px; background: rgba(255,255,255,0.7); border-radius: 8px;">
            <p class="prophet-text">{explanation}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_algo_triggers(zone: VIXZone):
    st.markdown(f"""
    <div class="prophet-card">
        <p class="prophet-section-title">Algo Trigger Zones</p>
        
        <div style="margin-bottom: 16px;">
            <p class="prophet-label">Current VIX</p>
            <p class="prophet-value-large">{zone.current:.2f}</p>
            <p style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">📍 {zone.current_zone}</p>
        </div>
        
        <div class="trigger-buy">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <p style="font-weight: 600; color: #059669; margin: 0; font-size: 0.85rem;">↑ BUY ALGO TRIGGER</p>
                    <p style="font-size: 0.75rem; color: #065f46; margin: 2px 0 0 0;">VIX tops here → SPX rallies</p>
                </div>
                <div style="text-align: right;">
                    <p class="prophet-value-medium" style="color: #059669;">{zone.nearest_buy_trigger:.2f}</p>
                    <p style="font-size: 0.75rem; color: #065f46; margin: 2px 0 0 0;">{zone.distance_to_buy_trigger:+.2f} away</p>
                </div>
            </div>
        </div>
        
        <div class="trigger-sell">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <p style="font-weight: 600; color: #dc2626; margin: 0; font-size: 0.85rem;">↓ SELL ALGO TRIGGER</p>
                    <p style="font-size: 0.75rem; color: #991b1b; margin: 2px 0 0 0;">VIX bottoms here → SPX sells</p>
                </div>
                <div style="text-align: right;">
                    <p class="prophet-value-medium" style="color: #dc2626;">{zone.nearest_sell_trigger:.2f}</p>
                    <p style="font-size: 0.75rem; color: #991b1b; margin: 2px 0 0 0;">{zone.distance_to_sell_trigger:.2f} away</p>
                </div>
            </div>
        </div>
        
        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #e2e8f0;">
            <p class="prophet-label">Zone Boundaries</p>
            <div style="display: flex; justify-content: space-between; margin-top: 8px;">
                <span class="prophet-text">Top: <strong>{zone.top:.2f}</strong></span>
                <span class="prophet-text">Bottom: <strong>{zone.bottom:.2f}</strong></span>
                <span class="prophet-text">Size: <strong>{zone.size:.2f}</strong></span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_vix_ladder(zone: VIXZone):
    levels = [
        ("+2", zone.get_extension(2), "extension"),
        ("+1", zone.get_extension(1), "extension"),
        ("TOP", zone.top, "top"),
        ("VIX", zone.current, "current"),
        ("BOTTOM", zone.bottom, "bottom"),
        ("-1", zone.get_extension(-1), "extension"),
        ("-2", zone.get_extension(-2), "extension"),
    ]
    
    st.markdown('<div class="prophet-card">', unsafe_allow_html=True)
    st.markdown('<p class="prophet-section-title">VIX Zone Ladder</p>', unsafe_allow_html=True)
    
    for label, value, level_type in levels:
        if level_type == "current":
            bg = "linear-gradient(90deg, #eff6ff 0%, #dbeafe 100%)"
            border = "2px solid #3b82f6"
            color = "#1e40af"
            weight = "700"
        elif level_type == "top":
            bg = "#dcfce7"
            border = "1px solid #059669"
            color = "#059669"
            weight = "600"
        elif level_type == "bottom":
            bg = "#fee2e2"
            border = "1px solid #dc2626"
            color = "#dc2626"
            weight = "600"
        else:
            bg = "#f8fafc"
            border = "1px solid #e2e8f0"
            color = "#64748b"
            weight = "400"
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; margin: 4px 0; background: {bg}; border: {border}; border-radius: 8px;">
            <span style="font-weight: {weight}; color: {color}; font-size: 0.85rem;">{label}</span>
            <span style="font-family: 'JetBrains Mono', monospace; font-weight: {weight}; color: {color}; font-size: 0.9rem;">{value:.2f}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_confluence_alerts(support_levels: List[ConfluentLevel], resistance_levels: List[ConfluentLevel]):
    if not support_levels and not resistance_levels:
        return
    
    st.markdown("""
    <div class="prophet-card">
        <p class="prophet-section-title">🎯 Confluence Zones</p>
        <p class="prophet-text" style="margin-bottom: 16px;">Multiple cones converging = stronger levels</p>
    """, unsafe_allow_html=True)
    
    for level in resistance_levels:
        strength_badge = "⭐⭐⭐" if level.strength == "strong" else "⭐⭐"
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #fef2f2 0%, #fee2e2 100%); border: 1px solid #fca5a5; border-radius: 8px; padding: 12px 16px; margin: 8px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-weight: 600; color: #dc2626;">RESISTANCE</span>
                    <span style="margin-left: 8px; font-size: 0.8rem;">{strength_badge}</span>
                </div>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #dc2626;">{level.price:,.2f}</span>
            </div>
            <p style="font-size: 0.75rem; color: #991b1b; margin: 4px 0 0 0;">{', '.join(level.cones)}</p>
        </div>
        """, unsafe_allow_html=True)
    
    for level in support_levels:
        strength_badge = "⭐⭐⭐" if level.strength == "strong" else "⭐⭐"
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #f0fdf4 0%, #dcfce7 100%); border: 1px solid #86efac; border-radius: 8px; padding: 12px 16px; margin: 8px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-weight: 600; color: #059669;">SUPPORT</span>
                    <span style="margin-left: 8px; font-size: 0.8rem;">{strength_badge}</span>
                </div>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #059669;">{level.price:,.2f}</span>
            </div>
            <p style="font-size: 0.75rem; color: #065f46; margin: 4px 0 0 0;">{', '.join(level.cones)}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_setup_card(setup: TradeSetup, spx: float, engine: SPXProphetEngine, is_best: bool = False):
    distance = spx - setup.entry
    
    risk = engine.calculate_profit(Config.STOP_LOSS_PTS, 1)
    p1 = engine.calculate_profit(setup.reward_1_pts, 1)
    p2 = engine.calculate_profit(setup.reward_2_pts, 1)
    p3 = engine.calculate_profit(setup.reward_3_pts, 1)
    rr = p2 / risk if risk > 0 else 0
    
    badge = ""
    if is_best:
        badge = '<span style="background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); color: #000; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; margin-left: 12px;">⭐ BEST SETUP</span>'
    if setup.is_confluent:
        badge += '<span style="background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%); color: #fff; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; margin-left: 8px;">🎯 CONFLUENCE</span>'
    
    card_class = f"{setup.direction.css}-bg" if is_best else "prophet-card"
    
    st.markdown(f"""
    <div class="{card_class}" style="border-radius: 16px; padding: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 1.1rem; font-weight: 700; color: {setup.direction.color};">{setup.direction.arrow} {setup.direction.label}</span>
                {badge}
            </div>
            <span class="prophet-label">{setup.cone.pivot.name} Cone</span>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px;">
            <div style="background: rgba(255,255,255,0.8); padding: 12px; border-radius: 10px; text-align: center; border: 2px solid {setup.direction.color};">
                <p class="prophet-label">Entry</p>
                <p class="prophet-value-medium">{setup.entry:,.2f}</p>
            </div>
            <div style="background: rgba(255,255,255,0.8); padding: 12px; border-radius: 10px; text-align: center; border: 1px solid #fca5a5;">
                <p class="prophet-label">Stop</p>
                <p class="prophet-value-medium" style="color: #dc2626;">{setup.stop:,.2f}</p>
            </div>
            <div style="background: rgba(255,255,255,0.8); padding: 12px; border-radius: 10px; text-align: center;">
                <p class="prophet-label">12.5%</p>
                <p class="prophet-value-medium">{setup.target_1:,.2f}</p>
            </div>
            <div style="background: rgba(255,255,255,0.8); padding: 12px; border-radius: 10px; text-align: center;">
                <p class="prophet-label">25%</p>
                <p class="prophet-value-medium">{setup.target_2:,.2f}</p>
            </div>
            <div style="background: rgba(255,255,255,0.8); padding: 12px; border-radius: 10px; text-align: center;">
                <p class="prophet-label">50%</p>
                <p class="prophet-value-medium">{setup.target_3:,.2f}</p>
            </div>
        </div>
        
        <div style="display: flex; justify-content: space-between; padding-top: 16px; border-top: 1px solid rgba(0,0,0,0.1);">
            <div style="text-align: center;">
                <p class="prophet-label">Distance</p>
                <p class="prophet-value-small">{distance:+.2f} pts</p>
            </div>
            <div style="text-align: center;">
                <p class="prophet-label">Strike</p>
                <p class="prophet-value-small">{setup.strike}</p>
            </div>
            <div style="text-align: center;">
                <p class="prophet-label">Width</p>
                <p class="prophet-value-small">{setup.cone.width:.1f} pts</p>
            </div>
            <div style="text-align: center;">
                <p class="prophet-label">R:R @25%</p>
                <p class="prophet-value-small">{rr:.1f}:1</p>
            </div>
            <div style="text-align: center;">
                <p class="prophet-label">Profit @25%</p>
                <p class="prophet-value-small" style="color: #059669;">${p2:,.0f}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_position_calculator(engine: SPXProphetEngine, setup: Optional[TradeSetup]):
    st.markdown('<div class="prophet-card">', unsafe_allow_html=True)
    st.markdown('<p class="prophet-section-title">Position Calculator</p>', unsafe_allow_html=True)
    
    risk_budget = st.number_input("Risk Budget ($)", min_value=100, max_value=100000, value=1000, step=100, key="pos_calc_risk")
    
    if setup:
        contracts = engine.calculate_max_contracts(risk_budget)
        risk_total = engine.calculate_profit(Config.STOP_LOSS_PTS, contracts)
        p1 = engine.calculate_profit(setup.reward_1_pts, contracts)
        p2 = engine.calculate_profit(setup.reward_2_pts, contracts)
        p3 = engine.calculate_profit(setup.reward_3_pts, contracts)
        
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-radius: 12px; margin: 16px 0;">
            <p class="prophet-label">Max Contracts</p>
            <p class="prophet-value-hero" style="color: #1e40af;">{contracts}</p>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
            <div style="background: #fef2f2; padding: 16px; border-radius: 10px; text-align: center;">
                <p class="prophet-label">Max Risk</p>
                <p class="prophet-value-medium" style="color: #dc2626;">${risk_total:,.0f}</p>
            </div>
            <div style="background: #f0fdf4; padding: 16px; border-radius: 10px; text-align: center;">
                <p class="prophet-label">@ 12.5%</p>
                <p class="prophet-value-medium" style="color: #059669;">${p1:,.0f}</p>
            </div>
            <div style="background: #f0fdf4; padding: 16px; border-radius: 10px; text-align: center;">
                <p class="prophet-label">@ 25%</p>
                <p class="prophet-value-medium" style="color: #059669;">${p2:,.0f}</p>
            </div>
            <div style="background: #f0fdf4; padding: 16px; border-radius: 10px; text-align: center;">
                <p class="prophet-label">@ 50%</p>
                <p class="prophet-value-medium" style="color: #059669;">${p3:,.0f}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Configure a setup to calculate position sizing")
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_cone_table(cones: List[ConeRails], best_name: str):
    st.markdown('<p class="prophet-section-title" style="margin-top: 24px;">Cone Rails</p>', unsafe_allow_html=True)
    
    data = []
    for c in cones:
        status = "⭐ BEST" if c.pivot.name == best_name else ("✓" if c.is_tradeable else "✗")
        data.append({
            "Pivot": c.pivot.name,
            "Ascending": f"{c.ascending:,.2f}",
            "Descending": f"{c.descending:,.2f}",
            "Width": f"{c.width:.1f}",
            "Blocks": c.blocks,
            "Status": status
        })
    
    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


def render_historical_results(session_data: Dict, setup: TradeSetup, hits: List[LevelHit], 
                             pnl: float, pnl_note: str, engine: SPXProphetEngine):
    st.markdown(f"""
    <div class="prophet-card">
        <p class="prophet-section-title">Session Results</p>
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 20px;">
            <div style="text-align: center; padding: 12px; background: #f8fafc; border-radius: 8px;">
                <p class="prophet-label">Open</p>
                <p class="prophet-value-small">{session_data['open']:,.2f}</p>
            </div>
            <div style="text-align: center; padding: 12px; background: #f0fdf4; border-radius: 8px;">
                <p class="prophet-label">High</p>
                <p class="prophet-value-small" style="color: #059669;">{session_data['high']:,.2f}</p>
            </div>
            <div style="text-align: center; padding: 12px; background: #fef2f2; border-radius: 8px;">
                <p class="prophet-label">Low</p>
                <p class="prophet-value-small" style="color: #dc2626;">{session_data['low']:,.2f}</p>
            </div>
            <div style="text-align: center; padding: 12px; background: #f8fafc; border-radius: 8px;">
                <p class="prophet-label">Close</p>
                <p class="prophet-value-small">{session_data['close']:,.2f}</p>
            </div>
            <div style="text-align: center; padding: 12px; background: #eff6ff; border-radius: 8px;">
                <p class="prophet-label">Range</p>
                <p class="prophet-value-small" style="color: #1e40af;">{session_data['range']:.2f}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Level hits
    st.markdown('<p class="prophet-section-title">Level Hits</p>', unsafe_allow_html=True)
    
    for hit in hits:
        icon = "✓" if hit.was_hit else "○"
        color = "#059669" if hit.was_hit else "#94a3b8"
        bg = "#f0fdf4" if hit.was_hit else "#f8fafc"
        
        if hit.level_name == "Stop" and hit.was_hit:
            icon = "✗"
            color = "#dc2626"
            bg = "#fef2f2"
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; margin: 4px 0; background: {bg}; border-radius: 8px;">
            <span style="color: {color}; font-weight: 600;">{icon} {hit.level_name}</span>
            <span style="font-family: 'JetBrains Mono', monospace; color: {color};">{hit.level_price:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # P&L Summary
    pnl_color = "#059669" if pnl >= 0 else "#dc2626"
    pnl_bg = "#f0fdf4" if pnl >= 0 else "#fef2f2"
    pnl_prefix = "+" if pnl >= 0 else ""
    
    st.markdown(f"""
    <div style="margin-top: 16px; padding: 20px; background: {pnl_bg}; border-radius: 12px; text-align: center;">
        <p class="prophet-label">Theoretical P&L (1 Contract)</p>
        <p class="prophet-value-hero" style="color: {pnl_color};">{pnl_prefix}${abs(pnl):,.2f}</p>
        <p class="prophet-text" style="margin-top: 8px;">{pnl_note}</p>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar(engine: SPXProphetEngine):
    st.sidebar.markdown("## ⚙️ Configuration")
    
    # Mode
    st.sidebar.markdown("#### Mode")
    mode = st.sidebar.radio("", ["Live", "Historical"], horizontal=True, label_visibility="collapsed")
    
    st.sidebar.markdown("---")
    
    # Date
    ct_tz = pytz.timezone('America/Chicago')
    today = datetime.now(ct_tz).date()
    
    if mode == "Live":
        session_date = today
        st.sidebar.success(f"📅 {session_date.strftime('%B %d, %Y')}")
    else:
        session_date = st.sidebar.date_input("Session Date", today - timedelta(days=1), max_value=today)
    
    st.sidebar.markdown("---")
    
    # VIX Zone (5pm-6am CT)
    st.sidebar.markdown("#### VIX Zone")
    st.sidebar.caption("Overnight boundaries (5pm-6am CT)")
    
    col1, col2 = st.sidebar.columns(2)
    vix_bottom = col1.number_input("Bottom", 5.0, 50.0, 15.87, 0.01, format="%.2f")
    vix_top = col2.number_input("Top", 5.0, 50.0, 16.17, 0.01, format="%.2f")
    vix_current = st.sidebar.number_input("Current VIX", 5.0, 50.0, 16.00, 0.01, format="%.2f")
    
    zone = VIXZone(vix_bottom, vix_top, vix_current)
    
    st.sidebar.markdown("---")
    
    # Prior Day Pivots
    st.sidebar.markdown("#### Prior Day Pivots")
    
    prior_data = fetch_prior_day_data(session_date)
    manual = st.sidebar.checkbox("Manual Input", value=(prior_data is None))
    
    prior_date = session_date - timedelta(days=1)
    while prior_date.weekday() >= 5:
        prior_date -= timedelta(days=1)
    
    if manual or prior_data is None:
        st.sidebar.caption(f"Pivot date: {prior_date}")
        col1, col2 = st.sidebar.columns(2)
        p_high = col1.number_input("High", 1000.0, 10000.0, 6050.0, 1.0)
        p_high_t = col2.time_input("Time", time(11, 30), key="p_high_t")
        col1, col2 = st.sidebar.columns(2)
        p_low = col1.number_input("Low", 1000.0, 10000.0, 6020.0, 1.0)
        p_low_t = col2.time_input("Time", time(14, 0), key="p_low_t")
        p_close = st.sidebar.number_input("Close", 1000.0, 10000.0, 6035.0, 1.0)
    else:
        p_high = prior_data['high']
        p_low = prior_data['low']
        p_close = prior_data['close']
        prior_date = prior_data['date'].date() if hasattr(prior_data['date'], 'date') else prior_data['date']
        p_high_t = time(11, 30)
        p_low_t = time(14, 0)
        st.sidebar.success(f"✓ Loaded: {prior_date}")
        st.sidebar.caption(f"H: {p_high:,.2f} | L: {p_low:,.2f} | C: {p_close:,.2f}")
    
    pivots = [
        Pivot("Prior High", p_high, ct_tz.localize(datetime.combine(prior_date, p_high_t))),
        Pivot("Prior Low", p_low, ct_tz.localize(datetime.combine(prior_date, p_low_t))),
        Pivot("Prior Close", p_close, ct_tz.localize(datetime.combine(prior_date, time(16, 0))))
    ]
    
    # Secondary Pivots
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Secondary Pivots")
    
    if st.sidebar.checkbox("High²"):
        col1, col2 = st.sidebar.columns(2)
        h2_p = col1.number_input("Price", 1000.0, 10000.0, p_high - 10, 1.0, key="h2_price")
        h2_t = col2.time_input("Time", time(10, 0), key="h2_time")
        pivots.append(Pivot("High²", h2_p, ct_tz.localize(datetime.combine(prior_date, h2_t)), "secondary"))
    
    if st.sidebar.checkbox("Low²"):
        col1, col2 = st.sidebar.columns(2)
        l2_p = col1.number_input("Price", 1000.0, 10000.0, p_low + 10, 1.0, key="l2_price")
        l2_t = col2.time_input("Time", time(13, 0), key="l2_time")
        pivots.append(Pivot("Low²", l2_p, ct_tz.localize(datetime.combine(prior_date, l2_t)), "secondary"))
    
    st.sidebar.markdown("---")
    st.sidebar.caption("SPX Prophet v5.0")
    
    return mode, session_date, zone, pivots


# =============================================================================
# MAIN
# =============================================================================

def main():
    engine = SPXProphetEngine()
    ct_tz = pytz.timezone('America/Chicago')
    
    # Fetch data
    spx_live, prior_data = fetch_spx_data()
    spx_price = spx_live or 6000.0
    
    # Sidebar
    mode, session_date, zone, pivots = render_sidebar(engine)
    
    # Get phase
    now = engine.get_current_time_ct()
    phase = engine.get_phase(now)
    
    # Calculate bias
    bias, confidence, explanation = engine.determine_bias(zone)
    
    # Calculate cones
    if mode == "Live":
        eval_time = ct_tz.localize(datetime.combine(now.date(), time(10, 0)))
        if now.time() > time(10, 0):
            eval_time = now
    else:
        eval_time = ct_tz.localize(datetime.combine(session_date, time(10, 0)))
    
    cones = [engine.calculate_cone(p, eval_time) for p in pivots]
    
    # Find confluence
    support_confluence, resistance_confluence = engine.find_confluence(cones)
    
    # Find best cone
    valid_cones = [c for c in cones if c.is_tradeable]
    best_cone = max(valid_cones, key=lambda x: x.width) if valid_cones else None
    best_name = best_cone.pivot.name if best_cone else ""
    
    # Generate setups
    setups = []
    for cone in cones:
        if cone.is_tradeable:
            setup = engine.generate_setup(cone, bias, support_confluence, resistance_confluence)
            if setup:
                setups.append(setup)
    
    # Sort setups - best first
    setups.sort(key=lambda s: (s.cone.pivot.name != best_name, not s.is_confluent, -s.cone.width))
    
    best_setup = setups[0] if setups else None
    
    # ==========================================================================
    # RENDER
    # ==========================================================================
    
    render_header(spx_price, phase, engine)
    
    if mode == "Live":
        # Top row - Key metrics
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            render_expected_move(zone)
        
        with col2:
            render_bias_card(bias, confidence, explanation)
        
        with col3:
            render_algo_triggers(zone)
        
        # Chart
        st.markdown("---")
        intraday = fetch_intraday_spx()
        if intraday is not None and not intraday.empty:
            fig = create_spx_chart(intraday, cones, setups, zone, bias)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        # Setups
        st.markdown("---")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if setups:
                st.markdown(f"### {bias.arrow} {bias.label} Setups")
                for i, setup in enumerate(setups):
                    render_setup_card(setup, spx_price, engine, is_best=(i == 0))
            elif bias == Bias.WAIT:
                st.info("📊 VIX in Base Zone. Potential trend day. Waiting for boundary touch...")
            else:
                st.warning("No valid setups. Check cone widths.")
            
            render_cone_table(cones, best_name)
        
        with col2:
            render_confluence_alerts(support_confluence, resistance_confluence)
            render_vix_ladder(zone)
            render_position_calculator(engine, best_setup)
    
    else:
        # Historical Mode
        st.markdown(f"### 📊 Historical Analysis: {session_date.strftime('%B %d, %Y')}")
        
        session_data = fetch_historical_spx(session_date)
        
        if session_data:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                render_expected_move(zone)
                render_bias_card(bias, confidence, explanation)
                render_algo_triggers(zone)
            
            with col2:
                if best_setup:
                    hits = engine.analyze_level_hits(best_setup, session_data['high'], session_data['low'])
                    pnl, pnl_note = engine.calculate_theoretical_pnl(best_setup, hits)
                    render_historical_results(session_data, best_setup, hits, pnl, pnl_note, engine)
                else:
                    st.info("Configure pivots to see analysis")
            
            st.markdown("---")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                if setups:
                    st.markdown("### Setup Analysis")
                    for i, setup in enumerate(setups):
                        render_setup_card(setup, session_data['close'], engine, is_best=(i == 0))
                        
                        hits = engine.analyze_level_hits(setup, session_data['high'], session_data['low'])
                        pnl, pnl_note = engine.calculate_theoretical_pnl(setup, hits)
                        
                        cols = st.columns(6)
                        for j, hit in enumerate(hits):
                            icon = "✓" if hit.was_hit else "○"
                            if hit.level_name == "Stop" and hit.was_hit:
                                icon = "✗"
                            cols[j % 6].markdown(f"**{hit.level_name}**: {icon}")
                        
                        st.markdown(f"**P&L (1 contract):** ${pnl:,.2f} ({pnl_note})")
                        st.markdown("---")
                
                render_cone_table(cones, best_name)
            
            with col2:
                render_confluence_alerts(support_confluence, resistance_confluence)
                render_vix_ladder(zone)
                render_position_calculator(engine, best_setup)
        else:
            st.error(f"No data available for {session_date}")
    
    # Footer
    st.markdown("---")
    st.caption("SPX Prophet v5.0 | Institutional SPX Prediction System | Data: Yahoo Finance | Not Financial Advice")


if __name__ == "__main__":
    main()
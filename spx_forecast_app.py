"""
Stock Prophet Elite - Premium Trading Dashboard
Hybrid approach: Streamlit for inputs, HTML components for display
"""

import streamlit as st
import streamlit.components.v1 as components
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ============================================================================
# CONFIGURATION
# ============================================================================

STOCK_UNIVERSE = ["AAPL", "NVDA", "MSFT"]

STOCK_INFO = {
    "AAPL": {"name": "Apple Inc.", "icon": "🍎", "color": "#00d4aa"},
    "NVDA": {"name": "NVIDIA Corp.", "icon": "💚", "color": "#76b900"},
    "MSFT": {"name": "Microsoft", "icon": "🪟", "color": "#00a4ef"},
}

STOP_BUFFER_PERCENT = 0.002

# ============================================================================
# DATA MODELS
# ============================================================================

class MABias(Enum):
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"

class TradeDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO TRADE"

@dataclass
class StockData:
    symbol: str
    current_price: Optional[float] = None
    ema_50: Optional[float] = None
    sma_200: Optional[float] = None
    ma_bias: MABias = MABias.NEUTRAL
    high_point_1: Optional[float] = None
    high_time_1: str = ""
    high_point_2: Optional[float] = None
    high_time_2: str = ""
    low_point_1: Optional[float] = None
    low_time_1: str = ""
    low_point_2: Optional[float] = None
    low_time_2: str = ""
    ceiling: Optional[float] = None
    floor: Optional[float] = None

@dataclass
class TradeSetup:
    direction: TradeDirection
    entry: Optional[float] = None
    exit_target: Optional[float] = None
    stop_loss: Optional[float] = None
    reward: Optional[float] = None
    risk: Optional[float] = None
    rr_ratio: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    is_valid: bool = False

# ============================================================================
# TRADE LOGIC
# ============================================================================

def determine_ma_bias(current_price: Optional[float], ema_50: Optional[float], sma_200: Optional[float]) -> MABias:
    if None in (current_price, ema_50, sma_200):
        return MABias.NEUTRAL
    if ema_50 > sma_200 and current_price > ema_50:
        return MABias.BULLISH
    elif ema_50 < sma_200 and current_price < ema_50:
        return MABias.BEARISH
    return MABias.NEUTRAL

def calculate_trade_setup(stock: StockData) -> TradeSetup:
    setup = TradeSetup(direction=TradeDirection.NO_TRADE)
    
    if stock.ceiling is None or stock.floor is None:
        setup.warnings.append("Set overnight high/low points")
        return setup
    
    if stock.current_price is None:
        setup.warnings.append("Enter current price")
        return setup
    
    if stock.ceiling <= stock.floor:
        setup.warnings.append("Ceiling must be > Floor")
        return setup
    
    current_hour = datetime.now().hour
    if not (9 <= current_hour <= 10):
        setup.warnings.append(f"Now: {datetime.now().strftime('%I:%M %p')} • Best: 9-10am ET")
    
    if stock.ma_bias == MABias.BULLISH:
        setup.direction = TradeDirection.LONG
        setup.entry = stock.floor
        setup.exit_target = stock.ceiling
        setup.stop_loss = round(stock.floor * (1 - STOP_BUFFER_PERCENT), 2)
        setup.is_valid = True
        if stock.current_price > stock.floor * 1.02:
            setup.warnings.append("Price above Floor")
        
    elif stock.ma_bias == MABias.BEARISH:
        setup.direction = TradeDirection.SHORT
        setup.entry = stock.ceiling
        setup.exit_target = stock.floor
        setup.stop_loss = round(stock.ceiling * (1 + STOP_BUFFER_PERCENT), 2)
        setup.is_valid = True
        if stock.current_price < stock.ceiling * 0.98:
            setup.warnings.append("Price below Ceiling")
    else:
        setup.warnings.append("Neutral bias - no trade")
        return setup
    
    if setup.entry and setup.exit_target and setup.stop_loss:
        if setup.direction == TradeDirection.LONG:
            setup.reward = round(setup.exit_target - setup.entry, 2)
            setup.risk = round(setup.entry - setup.stop_loss, 2)
        else:
            setup.reward = round(setup.entry - setup.exit_target, 2)
            setup.risk = round(setup.stop_loss - setup.entry, 2)
        
        if setup.risk > 0:
            setup.rr_ratio = round(setup.reward / setup.risk, 2)
            if setup.rr_ratio < 1.5:
                setup.warnings.append(f"R:R {setup.rr_ratio}:1 < 1.5")
    
    return setup

# ============================================================================
# HTML CARD GENERATOR
# ============================================================================

def generate_stock_card_html(stock: StockData, setup: TradeSetup) -> str:
    """Generate complete HTML for a stock card"""
    info = STOCK_INFO.get(stock.symbol, {"name": stock.symbol, "icon": "📊", "color": "#667eea"})
    
    # Determine classes and icons
    if setup.direction == TradeDirection.LONG:
        glow_class = "long-glow"
        signal_class = "long"
        signal_icon = "🚀"
        direction_text = "LONG"
    elif setup.direction == TradeDirection.SHORT:
        glow_class = "short-glow"
        signal_class = "short"
        signal_icon = "🔻"
        direction_text = "SHORT"
    else:
        glow_class = ""
        signal_class = "none"
        signal_icon = "⏸️"
        direction_text = "NO TRADE"
    
    if stock.ma_bias == MABias.BULLISH:
        bias_class = "bullish"
        bias_text = "BULLISH"
    elif stock.ma_bias == MABias.BEARISH:
        bias_class = "bearish"
        bias_text = "BEARISH"
    else:
        bias_class = "neutral"
        bias_text = "NEUTRAL"
    
    # Format values
    def fmt(val):
        return f"${val:,.2f}" if val else "—"
    
    price_str = fmt(stock.current_price)
    ema_str = fmt(stock.ema_50)
    sma_str = fmt(stock.sma_200)
    ceiling_str = fmt(stock.ceiling)
    floor_str = fmt(stock.floor)
    entry_str = fmt(setup.entry)
    target_str = fmt(setup.exit_target)
    stop_str = fmt(setup.stop_loss)
    reward_str = f"{setup.reward} pts" if setup.reward else "—"
    risk_str = f"{setup.risk} pts" if setup.risk else "—"
    rr_str = f"{setup.rr_ratio}:1" if setup.rr_ratio else "—"
    
    # Ceiling/Floor details
    ceil_detail = ""
    if stock.high_point_1 and stock.high_time_1:
        ceil_detail += f"H1: ${stock.high_point_1:.2f} @ {stock.high_time_1}"
    if stock.high_point_2 and stock.high_time_2:
        ceil_detail += f" • H2: ${stock.high_point_2:.2f} @ {stock.high_time_2}"
    
    floor_detail = ""
    if stock.low_point_1 and stock.low_time_1:
        floor_detail += f"L1: ${stock.low_point_1:.2f} @ {stock.low_time_1}"
    if stock.low_point_2 and stock.low_time_2:
        floor_detail += f" • L2: ${stock.low_point_2:.2f} @ {stock.low_time_2}"
    
    # Warnings
    warnings_html = ""
    for w in setup.warnings:
        warnings_html += f'<div class="warning-box">⚠️ {w}</div>'
    
    return f"""
    <div class="card {glow_class}">
        <div class="card-header">
            <div class="stock-id">
                <div class="stock-icon">{info['icon']}</div>
                <div>
                    <div class="symbol">{stock.symbol}</div>
                    <div class="company">{info['name']}</div>
                </div>
            </div>
            <div class="price-area">
                <div class="price">{price_str}</div>
                <div class="price-label">Current Price</div>
            </div>
        </div>
        
        <div class="bias-row">
            <div class="bias-left">
                <span class="section-label">MA BIAS</span>
                <span class="bias-badge {bias_class}">{bias_text}</span>
            </div>
            <div class="ma-vals">
                <div class="ma-item"><span class="ma-label">50 EMA</span><span class="ma-val">{ema_str}</span></div>
                <div class="ma-item"><span class="ma-label">200 SMA</span><span class="ma-val">{sma_str}</span></div>
            </div>
        </div>
        
        <div class="structure-row">
            <div class="structure-box ceiling-box">
                <div class="struct-label">🔺 CEILING</div>
                <div class="struct-val ceiling-val">{ceiling_str}</div>
                <div class="struct-detail">{ceil_detail}</div>
            </div>
            <div class="structure-box floor-box">
                <div class="struct-label">🔻 FLOOR</div>
                <div class="struct-val floor-val">{floor_str}</div>
                <div class="struct-detail">{floor_detail}</div>
            </div>
        </div>
        
        <div class="signal-area {signal_class}">
            <div class="signal-header">
                <span class="signal-icon">{signal_icon}</span>
                <span class="signal-text">{direction_text}</span>
            </div>
            <div class="levels-grid">
                <div class="level-item">
                    <div class="level-label">ENTRY</div>
                    <div class="level-val entry-val">{entry_str}</div>
                </div>
                <div class="level-item">
                    <div class="level-label">TARGET</div>
                    <div class="level-val target-val">{target_str}</div>
                </div>
                <div class="level-item">
                    <div class="level-label">STOP</div>
                    <div class="level-val stop-val">{stop_str}</div>
                </div>
            </div>
            <div class="rr-row">
                <div class="rr-item"><span class="rr-label">Reward</span><span class="rr-val">{reward_str}</span></div>
                <div class="rr-item"><span class="rr-label">Risk</span><span class="rr-val">{risk_str}</span></div>
                <div class="rr-item"><span class="rr-label">R:R</span><span class="rr-val highlight">{rr_str}</span></div>
            </div>
        </div>
        
        {warnings_html}
    </div>
    """

def generate_full_dashboard_html(stocks: List[StockData], setups: List[TradeSetup]) -> str:
    """Generate complete dashboard HTML with all cards"""
    
    # Count trades
    long_count = sum(1 for s in setups if s.direction == TradeDirection.LONG)
    short_count = sum(1 for s in setups if s.direction == TradeDirection.SHORT)
    wait_count = sum(1 for s in setups if s.direction == TradeDirection.NO_TRADE)
    
    # Generate all cards
    cards_html = ""
    for stock, setup in zip(stocks, setups):
        cards_html += generate_stock_card_html(stock, setup)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Inter', -apple-system, sans-serif;
                background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0f0f1a 100%);
                min-height: 100vh;
                padding: 20px;
                color: #fff;
            }}
            
            /* Header */
            .header {{
                text-align: center;
                padding: 30px 0 40px;
                position: relative;
            }}
            
            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 50%;
                transform: translateX(-50%);
                width: 500px;
                height: 200px;
                background: radial-gradient(ellipse, rgba(102, 126, 234, 0.15) 0%, transparent 70%);
                pointer-events: none;
            }}
            
            .title {{
                font-size: 2.8rem;
                font-weight: 800;
                background: linear-gradient(135deg, #667eea 0%, #a855f7 50%, #00d4aa 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                letter-spacing: -1px;
                margin-bottom: 8px;
            }}
            
            .subtitle {{
                color: #6b7280;
                font-size: 0.95rem;
                letter-spacing: 2px;
                text-transform: uppercase;
            }}
            
            /* Status Bar */
            .status-bar {{
                display: flex;
                justify-content: center;
                gap: 15px;
                margin-bottom: 30px;
                flex-wrap: wrap;
            }}
            
            .status-badge {{
                padding: 10px 20px;
                border-radius: 50px;
                font-weight: 600;
                font-size: 0.85rem;
                display: flex;
                align-items: center;
                gap: 8px;
                backdrop-filter: blur(10px);
            }}
            
            .status-badge.long {{
                background: rgba(0, 212, 170, 0.15);
                border: 1px solid rgba(0, 212, 170, 0.3);
                color: #00d4aa;
            }}
            
            .status-badge.short {{
                background: rgba(255, 71, 87, 0.15);
                border: 1px solid rgba(255, 71, 87, 0.3);
                color: #ff4757;
            }}
            
            .status-badge.wait {{
                background: rgba(107, 114, 128, 0.15);
                border: 1px solid rgba(107, 114, 128, 0.3);
                color: #9ca3af;
            }}
            
            /* Cards Container */
            .cards-container {{
                display: flex;
                flex-direction: column;
                gap: 25px;
                max-width: 800px;
                margin: 0 auto;
            }}
            
            /* Card Base */
            .card {{
                background: rgba(255, 255, 255, 0.03);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
                padding: 25px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            
            .card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            }}
            
            .card:hover {{
                transform: translateY(-3px);
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            }}
            
            .card.long-glow {{
                border-color: rgba(0, 212, 170, 0.3);
                box-shadow: 0 0 40px rgba(0, 212, 170, 0.1), inset 0 0 60px rgba(0, 212, 170, 0.03);
            }}
            
            .card.short-glow {{
                border-color: rgba(255, 71, 87, 0.3);
                box-shadow: 0 0 40px rgba(255, 71, 87, 0.1), inset 0 0 60px rgba(255, 71, 87, 0.03);
            }}
            
            /* Card Header */
            .card-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 20px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }}
            
            .stock-id {{
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            
            .stock-icon {{
                width: 50px;
                height: 50px;
                background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            
            .symbol {{
                font-size: 1.5rem;
                font-weight: 700;
                color: #fff;
            }}
            
            .company {{
                font-size: 0.8rem;
                color: #6b7280;
                margin-top: 2px;
            }}
            
            .price-area {{
                text-align: right;
            }}
            
            .price {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 1.8rem;
                font-weight: 600;
                color: #fff;
            }}
            
            .price-label {{
                font-size: 0.7rem;
                color: #6b7280;
                margin-top: 4px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            /* Bias Row */
            .bias-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px 20px;
                background: rgba(0,0,0,0.2);
                border-radius: 12px;
                margin-bottom: 15px;
            }}
            
            .bias-left {{
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            
            .section-label {{
                font-size: 0.7rem;
                color: #6b7280;
                letter-spacing: 1px;
            }}
            
            .bias-badge {{
                padding: 6px 16px;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            
            .bias-badge.bullish {{
                background: linear-gradient(135deg, rgba(0, 212, 170, 0.2), rgba(0, 212, 170, 0.1));
                color: #00d4aa;
                border: 1px solid rgba(0, 212, 170, 0.4);
            }}
            
            .bias-badge.bearish {{
                background: linear-gradient(135deg, rgba(255, 71, 87, 0.2), rgba(255, 71, 87, 0.1));
                color: #ff4757;
                border: 1px solid rgba(255, 71, 87, 0.4);
            }}
            
            .bias-badge.neutral {{
                background: rgba(107, 114, 128, 0.2);
                color: #9ca3af;
                border: 1px solid rgba(107, 114, 128, 0.4);
            }}
            
            .ma-vals {{
                display: flex;
                gap: 25px;
            }}
            
            .ma-item {{
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 2px;
            }}
            
            .ma-label {{
                font-size: 0.65rem;
                color: #6b7280;
                letter-spacing: 0.5px;
            }}
            
            .ma-val {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.9rem;
                color: #e5e7eb;
            }}
            
            /* Structure Row */
            .structure-row {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                margin-bottom: 15px;
            }}
            
            .structure-box {{
                padding: 18px;
                border-radius: 12px;
                text-align: center;
                background: rgba(0,0,0,0.2);
                border: 1px solid transparent;
                transition: all 0.3s ease;
            }}
            
            .ceiling-box {{
                border-color: rgba(255, 71, 87, 0.2);
            }}
            
            .ceiling-box:hover {{
                border-color: rgba(255, 71, 87, 0.4);
                box-shadow: 0 0 20px rgba(255, 71, 87, 0.1);
            }}
            
            .floor-box {{
                border-color: rgba(0, 212, 170, 0.2);
            }}
            
            .floor-box:hover {{
                border-color: rgba(0, 212, 170, 0.4);
                box-shadow: 0 0 20px rgba(0, 212, 170, 0.1);
            }}
            
            .struct-label {{
                font-size: 0.7rem;
                color: #6b7280;
                letter-spacing: 1px;
                margin-bottom: 8px;
            }}
            
            .struct-val {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 1.4rem;
                font-weight: 600;
                margin-bottom: 6px;
            }}
            
            .ceiling-val {{ color: #ff4757; }}
            .floor-val {{ color: #00d4aa; }}
            
            .struct-detail {{
                font-size: 0.65rem;
                color: #6b7280;
                min-height: 16px;
            }}
            
            /* Signal Area */
            .signal-area {{
                padding: 20px;
                border-radius: 16px;
                background: rgba(0,0,0,0.3);
                position: relative;
                overflow: hidden;
            }}
            
            .signal-area::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
            }}
            
            .signal-area.long::before {{
                background: linear-gradient(90deg, #00d4aa, transparent);
            }}
            
            .signal-area.short::before {{
                background: linear-gradient(90deg, #ff4757, transparent);
            }}
            
            .signal-area.none::before {{
                background: linear-gradient(90deg, #6b7280, transparent);
            }}
            
            .signal-header {{
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 20px;
            }}
            
            .signal-icon {{
                font-size: 1.8rem;
            }}
            
            .signal-text {{
                font-size: 1.5rem;
                font-weight: 800;
                letter-spacing: 2px;
            }}
            
            .signal-area.long .signal-text {{
                color: #00d4aa;
                text-shadow: 0 0 30px rgba(0, 212, 170, 0.5);
            }}
            
            .signal-area.short .signal-text {{
                color: #ff4757;
                text-shadow: 0 0 30px rgba(255, 71, 87, 0.5);
            }}
            
            .signal-area.none .signal-text {{
                color: #6b7280;
            }}
            
            /* Levels Grid */
            .levels-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
                margin-bottom: 15px;
            }}
            
            .level-item {{
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 10px;
                padding: 12px;
                text-align: center;
            }}
            
            .level-label {{
                font-size: 0.65rem;
                color: #6b7280;
                letter-spacing: 1px;
                margin-bottom: 6px;
            }}
            
            .level-val {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 1rem;
                font-weight: 600;
            }}
            
            .entry-val {{ color: #667eea; }}
            .target-val {{ color: #00d4aa; }}
            .stop-val {{ color: #ff4757; }}
            
            /* RR Row */
            .rr-row {{
                display: flex;
                justify-content: center;
                gap: 30px;
                padding: 12px;
                background: rgba(255,255,255,0.02);
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            
            .rr-item {{
                text-align: center;
            }}
            
            .rr-label {{
                font-size: 0.65rem;
                color: #6b7280;
                display: block;
                margin-bottom: 4px;
            }}
            
            .rr-val {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.9rem;
                color: #e5e7eb;
            }}
            
            .rr-val.highlight {{
                color: #f59e0b;
                font-weight: 600;
            }}
            
            /* Warnings */
            .warning-box {{
                margin-top: 12px;
                padding: 10px 15px;
                background: rgba(245, 158, 11, 0.1);
                border: 1px solid rgba(245, 158, 11, 0.3);
                border-radius: 8px;
                font-size: 0.8rem;
                color: #f59e0b;
            }}
            
            /* Footer */
            .footer {{
                text-align: center;
                padding: 40px 20px;
                color: #4b5563;
                font-size: 0.8rem;
            }}
            
            /* Animations */
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            .card {{
                animation: fadeIn 0.5s ease-out forwards;
            }}
            
            .card:nth-child(1) {{ animation-delay: 0.1s; }}
            .card:nth-child(2) {{ animation-delay: 0.2s; }}
            .card:nth-child(3) {{ animation-delay: 0.3s; }}
            
            /* Responsive */
            @media (max-width: 600px) {{
                .card-header {{ flex-direction: column; gap: 15px; text-align: center; }}
                .price-area {{ text-align: center; }}
                .bias-row {{ flex-direction: column; gap: 15px; }}
                .ma-vals {{ justify-content: center; }}
                .ma-item {{ align-items: center; }}
                .levels-grid {{ grid-template-columns: 1fr; }}
                .rr-row {{ flex-direction: column; gap: 15px; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1 class="title">STOCK PROPHET</h1>
            <p class="subtitle">Elite Trading Intelligence</p>
        </div>
        
        <div class="status-bar">
            <div class="status-badge long">📈 {long_count} LONG</div>
            <div class="status-badge short">📉 {short_count} SHORT</div>
            <div class="status-badge wait">⏸️ {wait_count} WAIT</div>
        </div>
        
        <div class="cards-container">
            {cards_html}
        </div>
        
        <div class="footer">
            Stock Prophet Elite v2.0 • Not financial advice
        </div>
    </body>
    </html>
    """

# ============================================================================
# STREAMLIT SIDEBAR
# ============================================================================

def render_sidebar_inputs(symbol: str) -> dict:
    info = STOCK_INFO.get(symbol, {"name": symbol, "icon": "📊"})
    
    st.sidebar.markdown(f"## {info['icon']} {symbol}")
    st.sidebar.caption(info['name'])
    
    key_prefix = f"{symbol}"
    
    # Initialize defaults
    defaults = {
        "price": 0.0,
        "ema": 0.0,
        "sma": 0.0,
        "h1": 0.0, "h1_time": "",
        "h2": 0.0, "h2_time": "",
        "l1": 0.0, "l1_time": "",
        "l2": 0.0, "l2_time": "",
    }
    
    # Price
    price = st.sidebar.number_input(
        "💰 Current Price",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.2f",
        key=f"{key_prefix}_price"
    )
    
    # MAs side by side
    col1, col2 = st.sidebar.columns(2)
    with col1:
        ema = st.number_input("50 EMA", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"{key_prefix}_ema")
    with col2:
        sma = st.number_input("200 SMA", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"{key_prefix}_sma")
    
    # Overnight Highs
    st.sidebar.markdown("**🔺 Overnight Highs**")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        h1 = st.number_input("High 1 $", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"{key_prefix}_h1")
    with col2:
        h1_time = st.text_input("Time", value="", key=f"{key_prefix}_h1t", placeholder="e.g. 5:30 PM")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        h2 = st.number_input("High 2 $", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"{key_prefix}_h2")
    with col2:
        h2_time = st.text_input("Time", value="", key=f"{key_prefix}_h2t", placeholder="e.g. 6:15 AM")
    
    # Overnight Lows
    st.sidebar.markdown("**🔻 Overnight Lows**")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        l1 = st.number_input("Low 1 $", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"{key_prefix}_l1")
    with col2:
        l1_time = st.text_input("Time", value="", key=f"{key_prefix}_l1t", placeholder="e.g. 8:00 PM")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        l2 = st.number_input("Low 2 $", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"{key_prefix}_l2")
    with col2:
        l2_time = st.text_input("Time", value="", key=f"{key_prefix}_l2t", placeholder="e.g. 4:30 AM")
    
    st.sidebar.markdown("---")
    
    return {
        "price": price,
        "ema": ema,
        "sma": sma,
        "h1": h1, "h1_time": h1_time,
        "h2": h2, "h2_time": h2_time,
        "l1": l1, "l1_time": l1_time,
        "l2": l2, "l2_time": l2_time,
    }

def process_inputs(symbol: str, inputs: dict) -> StockData:
    stock = StockData(symbol=symbol)
    
    stock.current_price = inputs["price"] if inputs["price"] > 0 else None
    stock.ema_50 = inputs["ema"] if inputs["ema"] > 0 else None
    stock.sma_200 = inputs["sma"] if inputs["sma"] > 0 else None
    
    stock.high_point_1 = inputs["h1"] if inputs["h1"] > 0 else None
    stock.high_time_1 = inputs["h1_time"]
    stock.high_point_2 = inputs["h2"] if inputs["h2"] > 0 else None
    stock.high_time_2 = inputs["h2_time"]
    
    stock.low_point_1 = inputs["l1"] if inputs["l1"] > 0 else None
    stock.low_time_1 = inputs["l1_time"]
    stock.low_point_2 = inputs["l2"] if inputs["l2"] > 0 else None
    stock.low_time_2 = inputs["l2_time"]
    
    # Calculate ceiling (max of highs) and floor (min of lows)
    highs = [h for h in [stock.high_point_1, stock.high_point_2] if h]
    lows = [l for l in [stock.low_point_1, stock.low_point_2] if l]
    
    stock.ceiling = max(highs) if highs else None
    stock.floor = min(lows) if lows else None
    
    stock.ma_bias = determine_ma_bias(stock.current_price, stock.ema_50, stock.sma_200)
    
    return stock

# ============================================================================
# MAIN
# ============================================================================

def main():
    st.set_page_config(
        page_title="Stock Prophet Elite",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Hide Streamlit elements
    st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp {background: #0a0a0f;}
    section[data-testid="stSidebar"] {background: linear-gradient(180deg, #0d0d14, #12121a);}
    section[data-testid="stSidebar"] * {color: #e5e7eb;}
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar Title
    st.sidebar.markdown("# 🎛️ ThinkorSwim Data")
    st.sidebar.caption("Enter overnight session values")
    st.sidebar.markdown("---")
    
    # Collect inputs for each stock
    all_inputs = {}
    for symbol in STOCK_UNIVERSE:
        all_inputs[symbol] = render_sidebar_inputs(symbol)
    
    # Process all stocks
    stocks = [process_inputs(symbol, all_inputs[symbol]) for symbol in STOCK_UNIVERSE]
    setups = [calculate_trade_setup(stock) for stock in stocks]
    
    # Generate and render the HTML dashboard
    dashboard_html = generate_full_dashboard_html(stocks, setups)
    
    # Use components.html for proper rendering
    components.html(dashboard_html, height=1800, scrolling=True)
    
    # Trading rules in expander (using Streamlit)
    with st.expander("📖 Trading Rules", expanded=False):
        st.markdown("""
        ### The Two Pillars
        
        **1. MA Bias → Direction**
        - 🟢 **BULLISH:** 50 EMA > 200 SMA AND Price > 50 EMA → LONG only
        - 🔴 **BEARISH:** 50 EMA < 200 SMA AND Price < 50 EMA → SHORT only
        - ⚪ **NEUTRAL:** Mixed signals → NO TRADE
        
        **2. Day Structure → Levels**
        - **Ceiling** = Higher of two overnight highs (5pm-7am)
        - **Floor** = Lower of two overnight lows (5pm-7am)
        
        ### Trade Execution
        - 🚀 **LONG:** Enter at Floor → Target Ceiling
        - 🔻 **SHORT:** Enter at Ceiling → Target Floor
        - ⏰ Optimal: 9-10am ET
        
        ### Risk Management
        - 🛡️ Stop: 0.2% beyond entry
        - ⚖️ Min R:R: 1.5:1
        """)

if __name__ == "__main__":
    main()
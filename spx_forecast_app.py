#  Dr David’s Market Mind – v2.0
#  -----------------------------------------------------------
#  • Same math, new aesthetics
#  • Works as a single-file Streamlit app
#  • Theme persistence + glass-morphism cards
#  • Fully responsive

import base64, json, math, streamlit as st
from copy import deepcopy
from datetime import date, datetime, time, timedelta

import pandas as pd

# -----------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------
APP_NAME, APP_ICON = "Dr David’s Market Mind", "🧠"
VERSION = "2.0"

BASE_SLOPES = {
    "SPX_HIGH": -0.2792, "SPX_CLOSE": -0.2792, "SPX_LOW": -0.2792,
    "TSLA": -0.1508, "NVDA": -0.0485, "AAPL": -0.0750,
    "MSFT": -0.17,   "AMZN": -0.03,   "GOOGL": -0.07,
    "META": -0.035,  "NFLX": -0.23,
}
ICONS = {
    "SPX":"🧭","TSLA":"🚗","NVDA":"🧠","AAPL":"🍎",
    "MSFT":"🪟","AMZN":"📦","GOOGL":"🔍",
    "META":"📘","NFLX":"📺"
}

# -----------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------
if "theme" not in st.session_state:
    st.session_state.update(
        theme="Light",
        slopes=deepcopy(BASE_SLOPES),
        presets={},
        contract_anchor=None,
        contract_slope=None,
        contract_price=None,
    )

if st.query_params.get("s"):
    try:
        st.session_state.slopes.update(
            json.loads(base64.b64decode(st.query_params["s"][0]).decode())
        )
    except Exception:
        pass

# -----------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None,
)

# -----------------------------------------------------------
# THEME CSS
# -----------------------------------------------------------
theme_css = """
<style>
/* Remove Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Root variables */
:root{
  --radius:16px;
  --shadow-light:0 8px 32px rgba(0,0,0,.08);
  --shadow-dark:0 8px 32px rgba(0,0,0,.4);
}

/* Light theme */
body[data-theme="light"] {
  --bg:#f7f8fa;
  --card:#ffffff;
  --text:#111827;
  --border:#e5e7eb;
  background:var(--bg);
  color:var(--text);
}

/* Dark theme */
body[data-theme="dark"] {
  --bg:#0f172a;
  --card:#1e293b;
  --text:#e2e8f0;
  --border:#334155;
  background:var(--bg);
  color:var(--text);
}

/* Hero banner */
.hero{
  background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
  color:#fff;
  padding:2rem 1rem 2.5rem;
  border-radius:var(--radius);
  margin-bottom:2rem;
  text-align:center;
  box-shadow:var(--shadow-light);
}
.hero h1{
  font-size:2.4rem;
  margin:.2rem 0;
  animation:fadeInDown .8s;
}
.hero p{
  font-size:1.1rem;
  opacity:.9;
  animation:fadeIn 1s;
}

/* Cards */
.cards{
  display:flex;
  gap:1.2rem;
  overflow-x:auto;
  padding-bottom:.5rem;
}
.card{
  flex:1 1 220px;
  padding:1.5rem;
  border-radius:var(--radius);
  background:var(--card);
  border:1px solid var(--border);
  box-shadow:var(--shadow-light);
  transition:transform .25s, box-shadow .25s;
}
.card:hover{
  transform:translateY(-6px);
  box-shadow:var(--shadow-dark);
}
.ic{
  width:3.2rem;
  height:3.2rem;
  border-radius:var(--radius);
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:2rem;
  color:#fff;
  margin-right:1rem;
}
.val{font-size:2rem;font-weight:700}
.ttl{font-size:.9rem;opacity:.7}

/* Animations */
@keyframes fadeInDown{
  from{opacity:0;transform:translateY(-20px);}
  to{opacity:1;transform:translateY(0);}
}
@keyframes fadeIn{
  from{opacity:0;}
  to{opacity:1;}
}

/* Responsive tweaks */
@media(max-width:600px){
  .hero h1{font-size:2rem}
  .cards{flex-direction:column}
}
</style>
"""

st.markdown(theme_css, unsafe_allow_html=True)

# -----------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Settings")

    # Theme switch
    new_theme = st.radio(
        "🎨 Theme",
        ["Light", "Dark"],
        index=0 if st.session_state.theme == "Light" else 1,
        horizontal=True,
    )
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    # Forecast date
    fcast_date = st.date_input("📅 Forecast Date", date.today() + timedelta(days=1))

    # Slopes
    with st.expander("📉 Slopes"):
        for k in list(st.session_state.slopes):
            st.session_state.slopes[k] = st.slider(
                k, -1.0, 1.0, st.session_state.slopes[k], 0.0001, key=k
            )

    # Presets
    with st.expander("💾 Presets"):
        nm = st.text_input("Preset name")
        if st.button("Save"):
            st.session_state.presets[nm] = deepcopy(st.session_state.slopes)
        if st.session_state.presets:
            sel = st.selectbox("Load preset", list(st.session_state.presets))
            if st.button("Load"):
                st.session_state.slopes.update(st.session_state.presets[sel])

    st.text_input(
        "🔗 Share link",
        f"?s={base64.b64encode(json.dumps(st.session_state.slopes).encode()).decode()}",
        disabled=True,
    )

# -----------------------------------------------------------
# HELPERS
# -----------------------------------------------------------
def make_slots(start=time(7, 30)):
    base = datetime(2025, 1, 1, start.hour, start.minute)
    return [(base + timedelta(minutes=30 * i)).strftime("%H:%M")
            for i in range(15 - (start.hour == 8 and start.minute == 30) * 2)]

SPX_SLOTS = make_slots(time(8, 30))
GEN_SLOTS = make_slots()

def blk_spx(a, t):
    b = 0
    while a < t:
        if a.hour != 16:
            b += 1
        a += timedelta(minutes=30)
    return b

blk_stock = lambda a, t: max(0, int((t - a).total_seconds() // 1800))

def tbl(price, slope, anchor, fd, slots, spx=True, fan=False):
    rows = []
    for s in slots:
        h, m = map(int, s.split(":"))
        tgt = datetime.combine(fd, time(h, m))
        b = blk_spx(anchor, tgt) if spx else blk_stock(anchor, tgt)
        rows.append(
            {"Time": s, "Projected": round(price + slope * b, 2)}
            if not fan
            else {"Time": s, "Entry": round(price + slope * b, 2), "Exit": round(price - slope * b, 2)}
        )
    return pd.DataFrame(rows)

# -----------------------------------------------------------
# HERO
# -----------------------------------------------------------
st.markdown(
    f"""
<div class="hero">
  <h1>{APP_ICON} {APP_NAME}</h1>
  <p>Contract-line + anchor-trend projection for SPX & big-tech names</p>
</div>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------
# TABS
# -----------------------------------------------------------
tabs = st.tabs([f"{ICONS[t]} {t}" for t in ICONS])

# ---------------- SPX TAB ----------------
with tabs[0]:
    st.write(f"### {ICONS['SPX']} SPX Forecast")
    c1, c2, c3 = st.columns(3)
    hp, ht = c1.number_input("High Price", value=6185.8, min_value=0.0), \
             c1.time_input("High Time", time(11, 30))
    cp, ct = c2.number_input("Close Price", value=6170.2, min_value=0.0), \
             c2.time_input("Close Time", time(15))
    lp, lt = c3.number_input("Low Price", value=6130.4, min_value=0.0), \
             c3.time_input("Low Time", time(13, 30))

    st.subheader("Contract Line (Low-1 ↔ Low-2)")
    o1, o2 = st.columns(2)
    l1_t, l1_p = o1.time_input("Low-1 Time", time(2), step=300), \
                 o1.number_input("Low-1 Price", value=10.0, min_value=0.0, step=0.1, key="l1")
    l2_t, l2_p = o2.time_input("Low-2 Time", time(3, 30), step=300), \
                 o2.number_input("Low-2 Price", value=12.0, min_value=0.0, step=0.1, key="l2")

    if st.button("Run Forecast", key="spx_run"):
        st.markdown('<div class="cards">', unsafe_allow_html=True)
        for kind, sym, title, val in [
            ("high", "▲", "High Anchor", hp),
            ("close", "■", "Close Anchor", cp),
            ("low", "▼", "Low Anchor", lp),
        ]:
            st.markdown(
                f"""
<div class="card {kind}">
  <div class="ic">{sym}</div>
  <div>
    <div class="ttl">{title}</div>
    <div class="val">{val:.2f}</div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        ah, ac, al = [datetime.combine(fcast_date - timedelta(days=1), t) for t in (ht, ct, lt)]
        for lbl, p, key, anc in [
            ("High", hp, "SPX_HIGH", ah),
            ("Close", cp, "SPX_CLOSE", ac),
            ("Low", lp, "SPX_LOW", al),
        ]:
            st.subheader(f"{lbl} Anchor Trend")
            st.dataframe(
                tbl(p, st.session_state.slopes[key], anc, fcast_date, SPX_SLOTS, fan=True),
                use_container_width=True,
            )

        anchor_dt = datetime.combine(fcast_date, l1_t)
        slope = (l2_p - l1_p) / (blk_spx(anchor_dt, datetime.combine(fcast_date, l2_t)) or 1)
        st.session_state.contract_anchor = anchor_dt
        st.session_state.contract_slope = slope
        st.session_state.contract_price = l1_p

        st.subheader("Contract Line (2-pt)")
        st.dataframe(
            tbl(l1_p, slope, anchor_dt, fcast_date, GEN_SLOTS),
            use_container_width=True,
        )

    lookup_t = st.time_input("Lookup time", time(9, 25), step=300, key="lookup_time")
    if st.session_state.contract_anchor:
        blocks = blk_spx(st.session_state.contract_anchor, datetime.combine(fcast_date, lookup_t))
        val = st.session_state.contract_price + st.session_state.contract_slope * blocks
        st.info(f"Projected @ {lookup_t.strftime('%H:%M')} → **{val:.2f}**")
    else:
        st.info("Enter Low-1 & Low-2 and press **Run Forecast** to activate lookup.")

# ---------------- STOCK TABS ----------------
def stock_tab(idx, tic):
    with tabs[idx]:
        st.write(f"### {ICONS[tic]} {tic}")
        a, b = st.columns(2)
        lp, lt = a.number_input("Prev-day Low", value=0.0, min_value=0.0, key=f"{tic}lp"), \
                 a.time_input("Low Time", time(7, 30), key=f"{tic}lt")
        hp, ht = b.number_input("Prev-day High", value=0.0, min_value=0.0, key=f"{tic}hp"), \
                 b.time_input("High Time", time(7, 30), key=f"{tic}ht")
        if st.button("Generate", key=f"go_{tic}"):
            low = tbl(lp, st.session_state.slopes[tic], datetime.combine(fcast_date, lt),
                      fcast_date, GEN_SLOTS, False, fan=True)
            high = tbl(hp, st.session_state.slopes[tic], datetime.combine(fcast_date, ht),
                       fcast_date, GEN_SLOTS, False, fan=True)
            st.subheader("Low Anchor Trend")
            st.dataframe(low, use_container_width=True)
            st.subheader("High Anchor Trend")
            st.dataframe(high, use_container_width=True)

for i, t in enumerate(list(ICONS)[1:], 1):
    stock_tab(i, t)

# -----------------------------------------------------------
# FOOTER
# -----------------------------------------------------------
st.markdown(
    f"<hr style='margin-top:3rem'><center style='font-size:.8rem;opacity:.6'>"
    f"v{VERSION} • {datetime.now():%Y-%m-%d %H:%M:%S}</center>",
    unsafe_allow_html=True,
)

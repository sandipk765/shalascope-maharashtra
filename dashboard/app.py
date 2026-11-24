# -*- coding: utf-8 -*-
"""
ShalaScope Maharashtra  |  Obsidian Premium Theme  (Audit 1)
Left-sidebar navigation -- strict single-page rendering.
Real UDISE+ data only. No synthetic values. No source mutation.
M3 = Total Student Enrolment. M5 = Classroom Infra Quality Trend (Proxy).
"""
from __future__ import annotations
from html import escape
from pathlib import Path
import re
import warnings

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# ROOT DETECTION
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_CANDIDATES = (
    [SCRIPT_DIR.parent, SCRIPT_DIR, *SCRIPT_DIR.parent.parents]
    if SCRIPT_DIR.name.lower() == "dashboard"
    else [SCRIPT_DIR, *SCRIPT_DIR.parents]
)
ROOT = next(
    (c for c in ROOT_CANDIDATES if (c / "data" / "processed" / "district_year").is_dir()),
    SCRIPT_DIR.parent if SCRIPT_DIR.name.lower() == "dashboard" else SCRIPT_DIR,
)

HISTORICAL_FILE = ROOT / "data/processed/district_year/maharashtra_district_year_shala_score_v1.csv"
FORECAST_FILE   = ROOT / "data/processed/district_year/maharashtra_district_year_forecast_2026_27.csv"
V2_FILE         = ROOT / "data/processed/district_year/maharashtra_district_year_shala_score_v2.csv"
GEOJSON_FILE    = ROOT / "assets/maharashtra_districts.geojson"
MODELS_DIR      = ROOT / "reports/models"
SHAP_DIR        = ROOT / "reports/explainability"

# ---------------------------------------------------------------------------
# OBSIDIAN PREMIUM PALETTE
# ---------------------------------------------------------------------------
# Surfaces
OBS_BG      = "#0A0F1E"   # page background  -- deep obsidian navy
OBS_SURFACE = "#111827"   # card surface      -- dark slate
OBS_RAISED  = "#1A2236"   # raised card       -- slightly lighter
OBS_BORDER  = "#1E2D45"   # border            -- subtle separation
OBS_HOVER   = "#1E293B"   # hover state

# Accent
ACCENT      = "#38BDF8"   # sky-blue primary  -- crisp, high-contrast
ACCENT_DARK = "#0EA5E9"   # deeper sky

# Status colours
SUCCESS     = "#34D399"   # emerald green
WARNING     = "#FBBF24"   # amber
DANGER      = "#F87171"   # rose red
INFO        = "#818CF8"   # indigo

# Text
TEXT_HI     = "#F1F5F9"   # headings
TEXT_MED    = "#CBD5E1"   # body
TEXT_LO     = "#64748B"   # captions / muted

# Chart grid
GRID        = "rgba(255,255,255,0.05)"
BORDER      = OBS_BORDER

# Legacy aliases kept for helper functions
TEAL_DARK   = ACCENT_DARK
TEAL        = ACCENT
AMBER       = WARNING
CRIMSON     = DANGER
VIOLET      = INFO
SLATE_MID   = "#334155"
SLATE_SOFT  = TEXT_LO
SAFFRON     = ACCENT
GOLD        = WARNING
GREEN       = SUCCESS
CORAL       = DANGER
BLUE        = "#60A5FA"
TERRA       = "#F97316"
TEXT        = TEXT_HI

PILLARS = {
    "Teacher Strength": "pillar_teacher_strength",
    "Infrastructure":   "pillar_infrastructure",
    "Digital Readiness":"pillar_digital_readiness",
}
PILLAR_COLORS = {
    "Teacher Strength": ACCENT_DARK,
    "Infrastructure":   WARNING,
    "Digital Readiness":"#60A5FA",
}
PILLAR_MEANING = {
    "Teacher Strength": "how well schools are staffed with teachers",
    "Infrastructure": "working toilets and classrooms in good condition",
    "Digital Readiness": "digital devices available in schools",
}
ALL = "All Maharashtra"

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ShalaScope Maharashtra",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS  -- Obsidian Premium Theme
# ---------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {
  --bg:       #0A0F1E;
  --surface:  #111827;
  --raised:   #1A2236;
  --border:   #1E2D45;
  --accent:   #38BDF8;
  --accent-d: #0EA5E9;
  --success:  #34D399;
  --warn:     #FBBF24;
  --danger:   #F87171;
  --info:     #818CF8;
  --hi:       #F1F5F9;
  --med:      #CBD5E1;
  --lo:       #64748B;
  --shadow:   0 2px 12px rgba(0,0,0,.45);
  --shadow-lg:0 4px 24px rgba(0,0,0,.60);
  --radius:   10px;
  --fs-title: 22px;
  --fs-sec:   15px;
  --fs-body:  13px;
  --fs-cap:   11.5px;
  --fs-label: 9.5px;
}

/* ── App shell ── */
html,body,[class*="css"] {
  font-family: Inter,"Segoe UI",system-ui,sans-serif;
  font-feature-settings:"tnum";
}
.stApp { background: var(--bg); color: var(--hi); }
.block-container,[data-testid="stMainBlockContainer"] {
  padding-top: 1.4rem !important;
  max-width: 1560px;
  padding-bottom: 3rem;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"], [data-testid="stSidebar"] * { color: var(--med) !important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,[data-testid="stSidebar"] strong {
  color: var(--hi) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"]>div {
  background: var(--raised) !important;
  border-color: var(--border) !important;
  color: var(--hi) !important;
}
[data-testid="stSidebar"] [data-baseweb="option"] {
  background: var(--surface) !important;
  color: var(--med) !important;
}

/* ── Sidebar nav rail (button-based, zero native widgets) ── */

/* Collapse Streamlit's per-element vertical margin around each nav button */
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.stButton) {
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
[data-testid="stSidebar"] .stButton {
  margin: 0 !important;
  padding: 0 !important;
}

/* The button element itself */
[data-testid="stSidebar"] .stButton > button {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  width: 100% !important;
  box-sizing: border-box !important;
  padding: 5px 10px 5px 12px !important;
  border-radius: 5px !important;
  border: none !important;
  border-left: 3px solid transparent !important;
  background: transparent !important;
  color: #94A3B8 !important;
  font-size: 11.5px !important;
  font-weight: 500 !important;
  line-height: 1.2 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  cursor: pointer !important;
  min-height: 28px !important;
  max-height: 30px !important;
  letter-spacing: 0 !important;
  text-align: left !important;
  transition: background .08s ease, color .08s ease, border-color .08s ease !important;
}

/* Inner div Streamlit wraps text in */
[data-testid="stSidebar"] .stButton > button > div {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  width: 100% !important;
  text-align: left !important;
  overflow: hidden !important;
}

/* The <p> inside the button */
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span {
  margin: 0 !important;
  text-align: left !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  font-size: 11.5px !important;
  font-weight: inherit !important;
  color: inherit !important;
  line-height: 1.2 !important;
}

/* Hover */
[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(56,189,248,.07) !important;
  color: #CBD5E1 !important;
  border-left-color: rgba(56,189,248,.30) !important;
}
[data-testid="stSidebar"] .stButton > button:hover p,
[data-testid="stSidebar"] .stButton > button:hover span {
  color: #CBD5E1 !important;
}

/* Kill focus ring */
[data-testid="stSidebar"] .stButton > button:focus,
[data-testid="stSidebar"] .stButton > button:focus-visible {
  box-shadow: none !important;
  outline: none !important;
}

/* Sidebar filter labels */
[data-testid="stSidebar"] .obs-filter-label {
  font-size: 9px;
  letter-spacing: 1.8px;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
  padding: 8px 0 4px;
  display: block;
}

/* ── Sidebar selectbox ── */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: #1A2236 !important;
  border: 1px solid #1E2D45 !important;
  border-radius: 7px !important;
  color: #E2E8F0 !important;
  font-size: 12.5px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] input {
  color: #E2E8F0 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg {
  fill: #38BDF8 !important;
}
[data-testid="stSidebar"] [data-baseweb="option"] {
  background: #111827 !important;
  color: #CBD5E1 !important;
  font-size: 12.5px !important;
}
[data-testid="stSidebar"] [data-baseweb="option"]:hover {
  background: #1A2236 !important;
}

/* ── Type ── */
h1,h2,h3,h4 { color: var(--hi) !important; font-weight: 700; letter-spacing: -.3px; }
p,label,.stMarkdown,[data-testid="stCaptionContainer"] { color: var(--med); }
[data-testid="stCaptionContainer"] { font-size: var(--fs-cap); color: var(--lo) !important; }
footer { visibility: hidden; }
hr { border-color: var(--border); margin: 14px 0; }
[data-testid="stHeader"] { background: transparent !important; border-bottom: none !important; }

/* ── Top app header ── */
.obs-header {
  background: #0A0F1E;
  border-bottom: 1px solid var(--border);
  padding: 8px 28px;
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 10px;
}
.obs-header-left { display: flex; flex-direction: column; gap: 2px; }
.obs-eyebrow {
  font-size: 9px; letter-spacing: 2.5px; font-weight: 700;
  color: var(--accent); text-transform: uppercase;
}
.obs-badge {
  display: inline-flex; align-items: center; gap: 5px;
  background: rgba(56,189,248,.10); border: 1px solid rgba(56,189,248,.25);
  color: var(--accent); border-radius: 5px; padding: 3px 10px;
  font-size: 10px; font-weight: 700; letter-spacing: .3px;
}

/* ── Section headings ── */
.section-heading,.sd-section-head {
  font-size: var(--fs-sec); font-weight: 700; color: var(--hi);
  margin: 18px 0 6px; padding-left: 10px;
  border-left: 3px solid var(--accent);
}
.section-sub,.sd-section-sub {
  font-size: var(--fs-body); color: var(--lo);
  margin: 0 0 14px 13px; line-height: 1.55;
}

/* ── Metric / KPI cards ── */
.metric-card,.sd-kpi {
  background: var(--raised); border: 1px solid var(--border);
  border-top: 2px solid var(--border);
  border-radius: var(--radius); padding: 14px 16px; min-height: 86px;
  box-shadow: var(--shadow); margin-bottom: 8px;
  display: flex; flex-direction: column;
}
.metric-label,.sd-kpi-label {
  font-size: var(--fs-label); letter-spacing: 1px; font-weight: 700;
  color: var(--lo); text-transform: uppercase;
}
.metric-value,.sd-kpi-value {
  font-size: 22px; font-weight: 800;
  color: var(--hi); margin-top: 6px; line-height: 1.2;
  font-variant-numeric: tabular-nums;
}
.metric-caption,.sd-kpi-caption {
  font-size: var(--fs-cap); color: var(--med); margin-top: 5px;
  font-variant-numeric: tabular-nums;
}

/* ── Insight / info cards ── */
.insight-card,.sd-card {
  background: var(--raised); border: 1px solid var(--border);
  border-left: 4px solid var(--accent,var(--accent));
  border-radius: 8px; padding: 10px 14px; margin-bottom: 7px;
  box-shadow: var(--shadow);
}
.insight-title,.sd-card-title {
  font-size: var(--fs-label); letter-spacing: 1px; font-weight: 700;
  color: var(--accent,var(--accent)); text-transform: uppercase;
}
.insight-text,.sd-card-body {
  font-size: var(--fs-body); color: var(--med); margin-top: 4px;
  line-height: 1.55; font-variant-numeric: tabular-nums;
}

/* ── Badges ── */
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 10px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase;
}
.badge-pass   { background: rgba(52,211,153,.15); color: #34D399; }
.badge-concern{ background: rgba(251,191,36,.15);  color: #FBBF24; }
.badge-critical{background: rgba(248,113,113,.15); color: #F87171; }
.badge-info   { background: rgba(129,140,248,.15); color: #818CF8; }

/* ── Step flow labels ── */
.step-flow { display:flex; align-items:center; gap:9px; margin-bottom:10px; }
.step-flow-num {
  width:22px; height:22px; border-radius:6px;
  background: var(--accent); color: var(--bg);
  font-size: var(--fs-cap); font-weight: 800;
  display:flex; align-items:center; justify-content:center; flex-shrink:0;
}
.step-flow-label { font-size:12px; font-weight:700; color: var(--hi); }

/* ── Score gauge ── */
.score-gauge-wrap {
  background: var(--raised); border: 1px solid var(--border);
  border-radius: var(--radius); padding:14px 16px;
  box-shadow: var(--shadow); margin-bottom:8px;
}
.score-gauge-label {
  font-size: var(--fs-label); letter-spacing:1px; font-weight:700;
  color: var(--lo); text-transform:uppercase; margin-bottom:6px;
}
.score-gauge-row { display:flex; align-items:baseline; gap:4px; margin-bottom:8px; }
.score-gauge-value {
  font-size: var(--fs-title); font-weight:800;
  color: var(--accent,var(--accent)); font-variant-numeric:tabular-nums; line-height:1;
}
.score-gauge-denom { font-size: var(--fs-body); color: var(--lo); }
.score-gauge-bar-bg {
  position:relative; background: var(--border); border-radius:999px;
  height:10px; overflow:visible;
}
.score-gauge-bar-fill {
  height:100%; border-radius:999px;
  background: var(--accent,var(--accent));
}
.score-gauge-avg {
  position:absolute; top:-3px; width:2px; height:16px;
  background: var(--hi); border-radius:1px;
}
.score-gauge-avg-label {
  position:absolute; top:14px; font-size:var(--fs-cap);
  color: var(--lo); white-space:nowrap; transform:translateX(-50%);
}
.score-gauge-caption { margin-top:6px; font-size:var(--fs-cap); color:var(--lo); }

/* ── Ratio bar ── */
.ratio-bar-wrap {
  background: var(--raised); border:1px solid var(--border);
  border-radius: var(--radius); padding:12px 14px; margin-bottom:7px;
  box-shadow: var(--shadow);
}
.ratio-bar-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
.ratio-bar-label {
  font-size: var(--fs-label); letter-spacing:1px; font-weight:700;
  color: var(--lo); text-transform:uppercase;
}
.ratio-bar-chip {
  font-size:9px; padding:1px 7px; border-radius:4px;
  font-weight:700; text-transform:uppercase; letter-spacing:.5px;
}
.ratio-bar-value-row { display:flex; align-items:baseline; gap:3px; margin-bottom:6px; }
.ratio-bar-value {
  font-size:22px; font-weight:800; font-variant-numeric:tabular-nums;
  color: var(--accent,var(--accent));
}
.ratio-bar-unit { font-size: var(--fs-cap); color: var(--lo); }
.ratio-bar-track {
  position:relative; background: var(--border); border-radius:999px; height:8px;
}
.ratio-bar-fill { height:100%; border-radius:999px; }
.ratio-bar-threshold {
  position:absolute; top:-3px; width:2px; height:14px;
  background: var(--hi); border-radius:1px;
}
.ratio-bar-threshold-label {
  position:absolute; top:12px; font-size:10px; color: var(--lo);
  white-space:nowrap; transform:translateX(-50%);
}
.ratio-bar-state { margin-top:5px; font-size:var(--fs-cap); color:var(--lo); }

/* ── Result card ── */
.result-card,.sd-result {
  background: var(--raised); border:1px solid var(--border);
  border-left:4px solid var(--accent,var(--accent));
  border-radius: var(--radius); padding:14px 17px; min-height:110px;
  box-shadow: var(--shadow);
}
.result-label { font-size:var(--fs-label); font-weight:700; letter-spacing:1px; text-transform:uppercase; color:var(--lo); }
.result-value { font-size:26px; font-weight:800; color:var(--accent,var(--accent)); margin-top:7px; font-variant-numeric:tabular-nums; }
.result-note  { font-size:11.5px; color:var(--lo); margin-top:6px; line-height:1.5; }

/* ── Prediction banner ── */
.prediction-banner,.sd-banner {
  background: var(--raised); border:1px solid var(--border);
  border-left:5px solid var(--accent,var(--accent));
  border-radius: var(--radius); padding:14px 18px; margin:5px 0 12px;
  box-shadow: var(--shadow);
}
.prediction-banner .kicker { font-size:9px; letter-spacing:1.5px; font-weight:700; color:var(--accent,var(--accent)); text-transform:uppercase; }
.prediction-banner .title  { font-size:18px; font-weight:800; color:var(--hi); margin-top:3px; line-height:1.3; }
.prediction-banner .desc   { font-size:12px; color:var(--lo); margin-top:4px; }

/* ── Root-cause cards ── */
.rc-card {
  background: var(--raised); border:1px solid var(--border);
  border-left:4px solid var(--accent,var(--accent));
  border-radius:8px; padding:10px 13px; margin-bottom:6px;
  box-shadow: var(--shadow);
}
.rc-title  { font-size:9px; letter-spacing:1px; font-weight:700; color:var(--accent,var(--accent)); text-transform:uppercase; display:flex; align-items:center; justify-content:space-between; }
.rc-value  { font-size:17px; font-weight:800; color:var(--accent,var(--accent)); font-variant-numeric:tabular-nums; margin-top:3px; line-height:1.2; }
.rc-state  { font-size:var(--fs-cap); color:var(--lo); font-variant-numeric:tabular-nums; }
.rc-explain{ font-size:var(--fs-body); color:var(--med); margin-top:5px; line-height:1.5; border-top:1px solid var(--border); padding-top:5px; }

/* ── Step cards ── */
.step {
  display:flex; gap:11px; align-items:flex-start;
  background: var(--raised); border:1px solid var(--border);
  border-radius:9px; padding:11px 14px; margin-bottom:7px;
  box-shadow: var(--shadow);
}
.step-no {
  min-width:26px; height:26px; border-radius:7px;
  background:rgba(56,189,248,.15); color:var(--accent);
  font-weight:800; display:flex; align-items:center; justify-content:center;
  font-size:12px; flex-shrink:0;
}
.step-body { color:var(--med); font-size:12.5px; line-height:1.6; }
.step-body b { color:var(--accent); }

/* -- District headline -- */
.dist-headline {
  background: var(--raised); border-radius: var(--radius);
  padding:14px 18px 12px; margin-bottom:14px; border:1px solid var(--border);
}
.dist-headline .dh-eyebrow { font-size:9px; letter-spacing:2px; font-weight:700; color:var(--accent); text-transform:uppercase; margin-bottom:3px; }
.dist-headline .dh-name    { font-size:22px; font-weight:800; color:var(--hi); letter-spacing:-.4px; line-height:1.2; }
.dist-headline .dh-sub     { font-size:11.5px; color:var(--lo); margin-top:4px; }

/* ── Right panel sticky ── */
.right-panel-sticky {
  position:sticky; top:4rem; max-height:calc(100vh - 5rem); overflow-y:auto; padding-right:4px;
}
.right-panel-sticky::-webkit-scrollbar { width:4px; }
.right-panel-sticky::-webkit-scrollbar-thumb { background:var(--border); border-radius:2px; }

/* ── Streamlit native overrides ── */
[data-testid="stMetric"] { background: var(--raised); border:1px solid var(--border); border-radius:9px; padding:11px 13px; }
[data-testid="stMetricLabel"] { color: var(--lo) !important; }
[data-testid="stMetricValue"] { color: var(--accent) !important; }
[data-testid="stDataFrame"],[data-testid="stTable"] {
  border:1px solid var(--border); border-radius:9px; overflow:hidden;
  background: var(--raised);
}
[data-testid="stPlotlyChart"] {
  background: var(--raised); border:1px solid var(--border);
  border-radius: var(--radius); padding:5px 7px 1px;
  box-shadow: var(--shadow); overflow:hidden; margin-top:4px;
}
[data-baseweb="menu"] *         { color:var(--hi) !important; background:var(--surface) !important; }
[data-baseweb="popover"]        { background:var(--surface) !important; }
[data-baseweb="select"]>div,[data-baseweb="input"]>div {
  background:var(--raised) !important; border:1px solid var(--border) !important;
  color:var(--hi) !important; border-radius:7px !important;
}
[data-baseweb="select"] input   { color:var(--hi) !important; }
[data-baseweb="select"] svg     { fill:var(--accent) !important; }
[data-testid="stForm"] {
  background:var(--raised); border:1px solid var(--border);
  border-radius: var(--radius); padding:14px 16px; box-shadow:var(--shadow);
}
[data-testid="stAlert"] {
  background:rgba(56,189,248,.08); border:1px solid rgba(56,189,248,.20);
  color:var(--accent); border-radius:7px;
}
.stButton>button,[data-testid="stFormSubmitButton"]>button {
  border-radius:7px !important; border:1px solid var(--accent) !important;
  background:var(--accent) !important; color:var(--bg) !important;
  font-weight:700 !important; min-height:38px !important;
}
.stButton>button:hover { background:var(--accent-d) !important; border-color:var(--accent-d) !important; }
.stSlider [data-baseweb="slider"] div[role="slider"] {
  background:var(--accent) !important; border-color:var(--accent) !important;
}
[data-testid="stExpander"] { background:var(--raised); border:1px solid var(--border); border-radius:9px; }

@media(max-width:700px) {
  .block-container { padding-left:.75rem !important; padding-right:.75rem !important; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def load_csv(path: Path):
    return _load_csv_cached(str(path))


@st.cache_data(show_spinner=False)
def _load_csv_cached(path_str: str):
    p = Path(path_str)
    if not p.exists():
        return None
    try:
        return pd.read_csv(p, low_memory=False)
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def prepare_data(df):
    if df is None:
        return None
    df = df.copy()
    if "district" in df.columns:
        df["district"] = df["district"].astype("string").str.strip()
    if "academic_year" in df.columns:
        df["academic_year"] = df["academic_year"].astype(str).str.strip()
        df["_year_order"] = pd.to_numeric(
            df["academic_year"].str.extract(r"^(\d{4})")[0], errors="coerce"
        )
    return df


def numeric(series):
    return pd.to_numeric(series, errors="coerce")


def safe_mean(df, col):
    if col not in df.columns:
        return np.nan
    vals = numeric(df[col]).dropna()
    return float(vals.mean()) if not vals.empty else np.nan


def fmt(value, decimals=1):
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except Exception:
        pass
    return f"{value:,.{decimals}f}"


def slug(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def normalize_district(value):
    if value is None or pd.isna(value):
        return ""
    value = str(value).strip().lower().replace("&", "and")
    value = re.sub(r"\b(district|city)\b", "", value)
    value = re.sub(r"[-_]+", " ", value)
    value = re.sub(r"[()]", "", value)
    return " ".join(value.split())


def metric_card(label, value, caption="", accent=None):
    if accent is None:
        accent = ACCENT
    st.html(
        f'<div class="metric-card" style="--accent:{accent}">'
        f'<div class="metric-label">{escape(str(label))}</div>'
        f'<div class="metric-value">{escape(str(value))}</div>'
        f'<div class="metric-caption">{escape(str(caption))}</div></div>'
    )


def insight_card(title, text, accent=None):
    if accent is None:
        accent = ACCENT
    st.html(
        f'<div class="insight-card" style="--accent:{accent}">'
        f'<div class="insight-title">{escape(title)}</div>'
        f'<div class="insight-text">{escape(text)}</div></div>'
    )


def heading(title, subtitle=""):
    st.html(f'<div class="section-heading">{escape(title)}</div>')
    if subtitle:
        st.html(f'<div class="section-sub">{escape(subtitle)}</div>')


def step_flow(num, label):
    st.html(
        f'<div class="step-flow">'
        f'<div class="step-flow-num">{num}</div>'
        f'<div class="step-flow-label">{escape(label)}</div>'
        f'</div>'
    )


def score_gauge(label, value, state_avg, out_of=100, accent=None):
    if accent is None:
        accent = ACCENT
    if pd.isna(value):
        st.html(
            f'<div class="score-gauge-wrap" style="--accent:{accent}">'
            f'<div class="score-gauge-label">{escape(label)}</div>'
            f'<div class="score-gauge-value">—</div></div>'
        )
        return
    pct   = max(0.0, min(100.0, float(value))) / out_of * 100
    avg_p = max(0.0, min(100.0, float(state_avg))) / out_of * 100 if pd.notna(state_avg) else None
    avg_html = ""
    if avg_p is not None:
        avg_html = (
            f'<div class="score-gauge-avg" style="left:{avg_p:.1f}%">'
            f'<div class="score-gauge-avg-label">State {state_avg:.1f}</div></div>'
        )
    diff = float(value) - float(state_avg) if pd.notna(state_avg) else None
    diff_str = (f"({diff:+.1f} vs state)" if diff is not None else "")
    st.html(
        f'<div class="score-gauge-wrap" style="--accent:{accent}">'
        f'<div class="score-gauge-label">{escape(label)}</div>'
        f'<div class="score-gauge-row">'
        f'<span class="score-gauge-value">{float(value):.1f}</span>'
        f'<span class="score-gauge-denom"> / {out_of}</span></div>'
        f'<div class="score-gauge-bar-bg">'
        f'<div class="score-gauge-bar-fill" style="width:{pct:.1f}%;background:{accent}"></div>'
        f'{avg_html}</div>'
        f'<div class="score-gauge-caption">{escape(diff_str)}</div>'
        f'</div>'
    )


def ratio_bar(label, value, unit, state_avg,
              threshold_ok, threshold_crit,
              lower_is_better=False, accent_ok=None, accent_crit=None, bar_max=None):
    if accent_ok   is None: accent_ok   = SUCCESS
    if accent_crit is None: accent_crit = DANGER
    is_missing = value is None or (isinstance(value, float) and pd.isna(value))
    if is_missing:
        status_txt, chip_color = "DATA MISSING", TEXT_LO
    else:
        v = float(value)
        if lower_is_better:
            status_txt, chip_color = (("ADEQUATE", accent_ok) if v <= threshold_ok
                                      else ("CONCERN", WARNING) if v <= threshold_crit
                                      else ("CRITICAL", accent_crit))
        else:
            status_txt, chip_color = (("ADEQUATE", accent_ok) if v >= threshold_ok
                                      else ("CONCERN", WARNING) if v >= threshold_crit
                                      else ("CRITICAL", accent_crit))
    if is_missing:
        st.html(
            f'<div class="ratio-bar-wrap" style="--accent:{accent_ok}">'
            f'<div class="ratio-bar-header">'
            f'<span class="ratio-bar-label">{escape(label)}</span>'
            f'<span class="ratio-bar-chip" style="background:{chip_color}22;color:{chip_color}">'
            f'{escape(status_txt)}</span></div>'
            f'<div class="ratio-bar-value-row">'
            f'<span class="ratio-bar-value" style="color:{chip_color}">—</span>'
            f'<span class="ratio-bar-unit"> {escape(unit)}</span></div></div>'
        )
        return
    v = float(value)
    if bar_max is None:
        bar_max = max(v * 1.2, (threshold_crit or threshold_ok) * 1.1) if lower_is_better else 100.0
    bar_max = max(bar_max, 1)
    fill_pct  = max(0.0, min(100.0, v / bar_max * 100))
    thr_ok_p  = max(0.0, min(100.0, threshold_ok  / bar_max * 100))
    thr_crit_p = max(0.0, min(100.0, threshold_crit / bar_max * 100)) if threshold_crit else None
    avg_p  = max(0.0, min(100.0, float(state_avg) / bar_max * 100)) if pd.notna(state_avg) else None
    thr_html = f'<div class="ratio-bar-threshold" style="left:{thr_ok_p:.1f}%"><div class="ratio-bar-threshold-label">Threshold {threshold_ok}{unit}</div></div>'
    if thr_crit_p:
        thr_html += f'<div class="ratio-bar-threshold" style="left:{thr_crit_p:.1f}%;background:{accent_crit}"></div>'
    avg_html = f'<div class="ratio-bar-threshold" style="left:{avg_p:.1f}%;background:{TEXT_LO};width:1px"></div>' if avg_p else ""
    state_cap = f"State avg: {float(state_avg):.1f} {unit}" if pd.notna(state_avg) else ""
    st.html(
        f'<div class="ratio-bar-wrap" style="--accent:{chip_color}">'
        f'<div class="ratio-bar-header">'
        f'<span class="ratio-bar-label">{escape(label)}</span>'
        f'<span class="ratio-bar-chip" style="background:{chip_color}22;color:{chip_color}">{escape(status_txt)}</span>'
        f'</div>'
        f'<div class="ratio-bar-value-row">'
        f'<span class="ratio-bar-value" style="color:{chip_color}">{v:.1f}</span>'
        f'<span class="ratio-bar-unit"> {escape(unit)}</span></div>'
        f'<div class="ratio-bar-track">'
        f'<div class="ratio-bar-fill" style="width:{fill_pct:.1f}%;background:{chip_color}"></div>'
        f'{thr_html}{avg_html}</div>'
        + (f'<div class="ratio-bar-state">{escape(state_cap)}</div>' if state_cap else "")
        + f'</div>'
    )


def rc_card(indicator, value_str, state_str, status, explanation, accent):
    st.html(
        f'<div class="rc-card" style="--accent:{accent}">'
        f'<div class="rc-title"><span>{escape(indicator)}</span>'
        f'<span style="font-size:9px;padding:1px 7px;border-radius:4px;background:{accent}22;color:{accent};font-weight:700;text-transform:uppercase;letter-spacing:.5px">{escape(status)}</span>'
        f'</div>'
        f'<div class="rc-value">{escape(value_str)}</div>'
        + (f'<div class="rc-state">{escape(state_str)}</div>' if state_str else "")
        + (f'<div class="rc-explain">{escape(explanation)}</div>' if explanation else "")
        + "</div>"
    )


def chart_style(fig, height=360, horizontal=False):
    fig.update_layout(
        template="plotly_dark", height=height, autosize=True,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter,Segoe UI,system-ui,sans-serif", color=TEXT_MED, size=12),
        margin=dict(l=36, r=36, t=40, b=44),
        hoverlabel=dict(bgcolor="#0A0F1E", bordercolor="#1E2D45",
                        font_size=12, font_color="#F1F5F9"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(color=TEXT_MED, size=11), bgcolor="rgba(0,0,0,0)", title_text=""),
    )
    fig.update_xaxes(
        showgrid=horizontal, gridcolor=GRID, showline=True,
        linecolor=OBS_BORDER, linewidth=1,
        tickfont=dict(color=TEXT_LO, size=11),
        title_font=dict(color=TEXT_LO, size=12),
        automargin=True, zeroline=False,
    )
    fig.update_yaxes(
        showgrid=not horizontal, gridcolor=GRID, zeroline=False,
        tickfont=dict(color=TEXT_LO, size=11),
        title_font=dict(color=TEXT_LO, size=12),
        automargin=True,
    )
    return fig


def show(fig, height=360, horizontal=False, key=None):
    st.plotly_chart(
        chart_style(fig, height, horizontal),
        theme=None, config={"displaylogo": False}, key=key,
    )


def focus_area(row):
    vals = {k: row.get(v) for k, v in PILLARS.items()}
    vals = {k: float(x) for k, x in vals.items() if x is not None and not pd.isna(x)}
    return min(vals, key=vals.get) if vals else None

# ---------------------------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------------------------
historical    = prepare_data(load_csv(HISTORICAL_FILE))
forecast      = prepare_data(load_csv(FORECAST_FILE))
historical_v2 = prepare_data(load_csv(V2_FILE))


def _missing_file_help(label, path):
    st.error(f"{label} not found. Expected: {path}")
    st.stop()


if historical is None:
    _missing_file_help("Historical dataset (v1)", HISTORICAL_FILE)
if forecast is None:
    _missing_file_help("Forecast dataset", FORECAST_FILE)

required_historical = ["district", "academic_year", "shala_score_v1",
                       "pillar_teacher_strength", "pillar_infrastructure", "pillar_digital_readiness"]
required_forecast   = ["district", "forecast_shala_score_v1", "forecast_relative_performance_band",
                       "forecast_enrollment", "forecast_teachers", "forecast_functional_toilet_pct",
                       "forecast_good_classroom_pct", "forecast_digital_devices_per_school"]
missing_h = [c for c in required_historical if c not in historical.columns]
missing_f = [c for c in required_forecast   if c not in forecast.columns]
if missing_h or missing_f:
    if missing_h: st.error(f"Historical dataset missing columns: {missing_h}")
    if missing_f: st.error(f"Forecast dataset missing columns: {missing_f}")
    st.stop()

for c in historical.columns:
    if c not in {"district", "academic_year", "management"} and historical[c].dtype != "object":
        historical[c] = numeric(historical[c])
for c in forecast.columns:
    if c not in {"district", "source_academic_year", "forecast_academic_year",
                 "forecast_relative_performance_band", "forecast_error_range_type",
                 "forecast_score_method", "forecast_risk_interpretation"}:
        forecast[c] = numeric(forecast[c])

# ---------------------------------------------------------------------------
# SIDEBAR  -- navigation + filters
# ---------------------------------------------------------------------------
with st.sidebar:

    # Brand block
    st.html(
        '<div style="padding:16px 4px 10px 4px">'
        '<div style="font-size:20px;font-weight:800;color:#38BDF8;'
        'letter-spacing:-.6px;line-height:1">ShalaScope</div>'
        '<div style="font-size:8.5px;letter-spacing:3px;font-weight:700;'
        'color:#334155;text-transform:uppercase;margin-top:3px">'
        'Maharashtra &nbsp; Education</div>'
        '</div>'
    )
    st.html('<div style="height:1px;background:linear-gradient(90deg,#38BDF8 0%,transparent 70%);margin:0 0 8px"></div>')

    # Nav label
    st.html('<span class="obs-filter-label">Navigate</span>')

    # 6 objective-aligned pages
    NAV_LABELS = [
        "Overview",
        "Region Comparison",
        "District Explorer",
        "District Grouping",
        "Predictive Intelligence",
        "Data & Methodology",
    ]
    _LABEL_TO_PAGE = {
        "Overview":               "Overview",
        "Region Comparison":      "Region Comparison",
        "District Explorer":      "District Explorer",
        "District Grouping":      "District Grouping",
        "Predictive Intelligence":"Predictive Intelligence",
        "Data & Methodology":     "Data Quality & Methodology",
    }
    _VALID_PAGES = set(_LABEL_TO_PAGE.values())

    # Safe fallback: if session_state holds a stale/removed page name, reset to Overview
    if st.session_state.get("nav_page") not in _VALID_PAGES:
        st.session_state["nav_page"] = "Overview"

    _active_page = st.session_state["nav_page"]

    for _lbl in NAV_LABELS:
        _pg = _LABEL_TO_PAGE[_lbl]
        if st.button(_lbl, key=f"nav_btn_{_lbl}"):
            st.session_state["nav_page"] = _pg
            st.rerun()

    # Active button highlight (plum accent)
    _active_lbl = next((l for l, p in _LABEL_TO_PAGE.items() if p == _active_page), "Overview")
    _sel_btn    = f'[data-testid="stSidebar"] button[aria-label="{_active_lbl}"]'
    st.html(
        f'<style>'
        f'{_sel_btn} {{'
        f'  background: rgba(92,29,61,.12) !important;'
        f'  color: #5C1D3D !important;'
        f'  font-weight: 700 !important;'
        f'  border-left: 3px solid #5C1D3D !important;'
        f'}}'
        f'{_sel_btn} p, {_sel_btn} span, {_sel_btn} div {{'
        f'  color: #5C1D3D !important;'
        f'  font-weight: 700 !important;'
        f'}}'
        f'</style>'
    )

    page = _active_page

    # ── Global Filters (immediately below nav, always visible) ───────────
    st.html('<div style="height:1px;background:#1E2D45;margin:10px 0 4px"></div>')
    st.html('<span class="obs-filter-label">Filters</span>')

    districts_all = sorted(historical["district"].dropna().astype(str).unique().tolist())
    _yr_opts = sorted(
        historical["academic_year"].dropna().unique(),
        key=lambda x: int(str(x)[:4]) if re.match(r"^\d{4}", str(x)) else 0,
    )
    if not _yr_opts:
        st.error("No academic year records available.")
        st.stop()
    years = _yr_opts

    selected_year   = st.selectbox("Academic Year", years, index=len(years) - 1, key="sb_year")
    _pune_def = ([ALL] + districts_all).index("PUNE") if "PUNE" in districts_all else 0
    district_choice = st.selectbox("District", [ALL] + districts_all, index=_pune_def, key="sb_district")
    is_all    = district_choice == ALL
    highlight = None if is_all else district_choice

    # CSV uploader (collapsed by default to save space)
    st.html('<div style="height:1px;background:#1E2D45;margin:10px 0 4px"></div>')
    with st.expander("Upload New Year CSV"):
        st.caption("Upload a district-year CSV matching the Shala Score schema to add to the session.")
        uploaded_csv = st.file_uploader("Choose CSV", type=["csv"], key="sidebar_csv_upload")
        if uploaded_csv is not None:
            try:
                up_df = pd.read_csv(uploaded_csv, low_memory=False)
                if "district" in up_df.columns and "academic_year" in up_df.columns:
                    up_df["district"] = up_df["district"].astype("string").str.strip()
                    up_df["academic_year"] = up_df["academic_year"].astype(str).str.strip()
                    before = len(up_df)
                    up_df  = up_df.drop_duplicates(subset=["district","academic_year"], keep="first")
                    up_df  = prepare_data(up_df)
                    historical = pd.concat([historical, up_df], ignore_index=True)
                    years = sorted(
                        historical["academic_year"].dropna().unique(),
                        key=lambda x: int(str(x)[:4]) if re.match(r"^\d{4}", str(x)) else 0,
                    )
                    districts_all = sorted(historical["district"].dropna().astype(str).unique().tolist())
                    st.success(f"Loaded {len(up_df)} rows ({before - len(up_df)} dupes removed).")
                else:
                    st.error("CSV must have 'district' and 'academic_year' columns.")
            except Exception as exc:
                st.error(f"Could not read CSV: {exc}")

    # Footer
    st.html(
        f'<div style="padding:10px 4px 2px;font-size:10px;color:#334155;line-height:1.6">'
        f'{years[0]} &ndash; {years[-1]} &nbsp;|&nbsp; 36 districts'
        f'</div>'
    )

# ---------------------------------------------------------------------------
# SHARED DERIVED STATE  (computed once, used by all pages)
# ---------------------------------------------------------------------------
year_data    = historical[historical["academic_year"] == selected_year].copy()
if year_data.empty:
    st.error("No records for the selected year.")
    st.stop()
districts    = districts_all
view_data    = year_data if is_all else year_data[year_data["district"] == district_choice]
valid_scores = year_data.dropna(subset=["shala_score_v1"]).sort_values("shala_score_v1", ascending=False)
state_avg    = safe_mean(year_data, "shala_score_v1")
state_pillars= {k: safe_mean(year_data, v) for k, v in PILLARS.items()}
prev_year    = years[years.index(selected_year) - 1] if years.index(selected_year) > 0 else None

_forecast_yr_label = (
    str(forecast["forecast_academic_year"].iloc[0])
    if forecast is not None and "forecast_academic_year" in forecast.columns
    else "Upcoming Year"
)

# ---------------------------------------------------------------------------
# TOP HEADER BAR
# ---------------------------------------------------------------------------
st.html(
    '<div class="obs-header">'
    '<span class="obs-eyebrow" style="letter-spacing:3px;font-size:9px">'
    'MAHARASHTRA SCHOOL EDUCATION INTELLIGENCE</span>'
    f'<span class="obs-badge">Forecast: {escape(_forecast_yr_label)}</span>'
    '</div>'
)

# ===========================================================================
# PAGE: HOME
# ===========================================================================
if page == "Home":

    # ── Full-width hero banner ────────────────────────────────────────────
    st.html(
        '<div style="'
        'background:linear-gradient(135deg,#0D1424 0%,#0F1E38 55%,#091628 100%);'
        'border:1px solid #1E2D45;border-radius:12px;'
        'padding:36px 40px 32px;margin-bottom:4px;">'

        '<div style="font-size:9px;letter-spacing:3px;font-weight:700;'
        'color:#38BDF8;text-transform:uppercase;margin-bottom:12px">'
        'Maharashtra School Education Intelligence</div>'

        '<h1 style="font-size:clamp(28px,4vw,46px);font-weight:800;'
        'color:#F1F5F9;line-height:1.1;margin:0 0 14px;letter-spacing:-.6px">'
        'ShalaScope Maharashtra</h1>'

        '<p style="font-size:14px;color:#94A3B8;line-height:1.65;'
        'max-width:680px;margin:0 0 20px">'
        'District-level school education analytics for all 36 Maharashtra districts, '
        'built on official UDISE+ government data (2018&#8209;19 to 2025&#8209;26). '
        'Real data only &mdash; no synthetic values, no source mutation.'
        '</p>'

        '<div style="display:flex;gap:8px;flex-wrap:wrap">'
        '<span style="background:rgba(56,189,248,.12);border:1px solid rgba(56,189,248,.30);'
        'color:#38BDF8;border-radius:6px;padding:5px 13px;font-size:10.5px;font-weight:700;letter-spacing:.3px">'
        '36 Districts</span>'
        '<span style="background:rgba(56,189,248,.12);border:1px solid rgba(56,189,248,.30);'
        'color:#38BDF8;border-radius:6px;padding:5px 13px;font-size:10.5px;font-weight:700;letter-spacing:.3px">'
        '4 Regions</span>'
        '<span style="background:rgba(52,211,153,.12);border:1px solid rgba(52,211,153,.30);'
        'color:#34D399;border-radius:6px;padding:5px 13px;font-size:10.5px;font-weight:700;letter-spacing:.3px">'
        'Real Data Only</span>'
        '<span style="background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.30);'
        'color:#FBBF24;border-radius:6px;padding:5px 13px;font-size:10.5px;font-weight:700;letter-spacing:.3px">'
        '5 ML Models &amp; SHAP</span>'
        '<span style="background:rgba(129,140,248,.12);border:1px solid rgba(129,140,248,.30);'
        'color:#818CF8;border-radius:6px;padding:5px 13px;font-size:10.5px;font-weight:700;letter-spacing:.3px">'
        '2019&#8209;20 &ndash; 2024&#8209;25 Spec Window</span>'
        '</div>'

        '</div>'
    )

    # ── Live KPI strip ────────────────────────────────────────────────────
    _k1, _k2, _k3, _k4, _k5 = st.columns(5, gap="medium")
    _ts  = year_data["school_count"].sum()                      if "school_count"                      in year_data.columns else np.nan
    _te  = year_data["enrollment_reported_student_total"].sum() if "enrollment_reported_student_total" in year_data.columns else np.nan
    _tt  = year_data["score_teacher_total_derived"].sum()       if "score_teacher_total_derived"       in year_data.columns else np.nan
    _ptr = safe_mean(year_data, "ptr_students_per_teacher_raw")
    with _k1: metric_card("Districts",  "36",                                           "Maharashtra",   ACCENT)
    with _k2: metric_card("Schools",    f"{int(_ts):,}" if pd.notna(_ts) else "—",      selected_year,   BLUE)
    with _k3: metric_card("Enrolment",  f"{int(_te):,}" if pd.notna(_te) else "—",      "Total",         WARNING)
    with _k4: metric_card("Teachers",   f"{int(_tt):,}" if pd.notna(_tt) else "—",      "M + F + T",     SUCCESS)
    with _k5: metric_card("Avg. PTR",   fmt(_ptr, 1),
                          "Above RTE norm" if pd.notna(_ptr) and _ptr > 30 else "Within RTE norm",
                          DANGER if pd.notna(_ptr) and _ptr > 30 else SUCCESS)

    # ── v2 score strip ────────────────────────────────────────────────────
    if historical_v2 is not None and "shala_score_v2" in historical_v2.columns:
        _v2yr  = historical_v2[historical_v2["academic_year"] == selected_year]
        _v2avg = safe_mean(_v2yr, "shala_score_v2")
        if "risk_tier_v2" in _v2yr.columns:
            _tc    = _v2yr["risk_tier_v2"].value_counts()
            _crit  = int(_tc.get("Critical", 0))
            _tier_note = (
                f"{_crit} Critical  |  {int(_tc.get('At-Risk',0))} At-Risk  "
                f"|  {int(_tc.get('Stable',0))} Stable  |  {int(_tc.get('Thriving',0))} Thriving"
            )
        else:
            _tier_note, _crit = "v2 score active", 0
        _va, _vb = st.columns(2, gap="medium")
        with _va: metric_card("Avg. Shala Score v2", fmt(_v2avg, 1), "5-pillar weighted  |  Learning = MISSING_IN_SOURCE", ACCENT)
        with _vb: metric_card("Risk Tier Distribution", _tier_note,
                              "Shala Score v2 quartile bands  |  72 districts per tier",
                              DANGER if _crit > 0 else WARNING)

    st.divider()

    # ── Navigation guide ──────────────────────────────────────────────────
    heading("Dashboard pages", "Choose any page from the left sidebar.")
    _NAV_INFO = [
        ("Overview",                  "State-wide KPIs, priority matrix, district map, Shala Score v2 badges.",       ACCENT),
        ("Region Comparison",         "Konkan / W. Maharashtra / Marathwada / Vidarbha -- scores, tiers, pillars.",    BLUE),
        ("District Explorer",         "Full district profile: v2 risk tier, SHAP top driver, ratio bars, forecast.",   WARNING),
        ("Predictive Intelligence",   "M1-M5 model outputs + non-destructive What-If simulator (6 scenarios).",        SUCCESS),
        ("Education Analytics",       "Per-indicator bar / trend charts and relationship explorer.",                   INFO),
        ("Data Quality & Methodology","AVAILABLE vs MISSING_IN_SOURCE audit, coverage heatmap, methodology.",          TEXT_LO),
        ("Risk Factor Analysis",      "Random Forest feature importance for Shala Score prediction.",                  TERRA),
        ("District Grouping",         "K-Means clusters, elbow/silhouette, cluster profiles.",                         BLUE),
        ("Educational Audit",         "District diagnostic report card vs state benchmarks.",                          DANGER),
    ]
    _nc = st.columns(3, gap="medium")
    for i, (pg, desc, col) in enumerate(_NAV_INFO):
        with _nc[i % 3]:
            st.html(
                f'<div class="insight-card" style="--accent:{col};margin-bottom:8px">'
                f'<div class="insight-title" style="font-size:10px">{escape(pg)}</div>'
                f'<div class="insight-text" style="font-size:12px">{escape(desc)}</div>'
                f'</div>'
            )

    st.divider()

    # ── Data principles ───────────────────────────────────────────────────
    heading("Data principles & guardrails")
    _left_p, _right_p = st.columns(2, gap="large")
    _PRINCIPLES_L = [
        ("Real Government Data",       "Every value comes from the official UDISE+ extract. No synthetic or imputed data."),
        ("No Source Mutation",         "Raw and processed CSVs are read-only during all dashboard runs and What-If simulations."),
        ("No Double-Counting",         "facility_classrooms_good_condition_pct is in Infrastructure pillar only. Learning Outcomes = MISSING_IN_SOURCE."),
    ]
    _PRINCIPLES_R = [
        ("Leakage-Free Models",        "Chronological split: train 2018-24, test 2024-25. Forecast horizon 2025-26/2026-27 never seen."),
        ("Proportional Redistribution","When a pillar's data is absent, its weight is redistributed across available pillars -- not a fixed rescale."),
        ("M2 / M5 Proxy Labels",       "M2 uses classroom-quality trend as SUBSTITUTE_PROXY. M5 = Classroom Infrastructure Quality Trend (Documented Proxy)."),
    ]
    with _left_p:
        for _pt, _pb in _PRINCIPLES_L:
            st.html(f'<div class="step"><div class="step-no">OK</div><div class="step-body"><b>{escape(_pt)}.</b> {escape(_pb)}</div></div>')
    with _right_p:
        for _pt, _pb in _PRINCIPLES_R:
            st.html(f'<div class="step"><div class="step-no">OK</div><div class="step-body"><b>{escape(_pt)}.</b> {escape(_pb)}</div></div>')


# ===========================================================================
# PAGE: OVERVIEW
# ===========================================================================
elif page == "Overview":
    heading("Maharashtra at a glance",
            "The big picture for the selected academic year.")

    prev_avg = safe_mean(historical[historical["academic_year"] == prev_year], "shala_score_v1") if prev_year else np.nan
    yoy = state_avg - prev_avg if pd.notna(prev_avg) and pd.notna(state_avg) else np.nan
    pm  = {k: v for k, v in state_pillars.items() if pd.notna(v)}
    top_row = valid_scores.iloc[0]  if not valid_scores.empty else None
    low_row = valid_scores.iloc[-1] if not valid_scores.empty else None

    _total_schools  = year_data["school_count"].sum()                        if "school_count"                        in year_data.columns else np.nan
    _total_enroll   = year_data["enrollment_reported_student_total"].sum()   if "enrollment_reported_student_total"   in year_data.columns else np.nan
    _total_teachers = year_data["score_teacher_total_derived"].sum()         if "score_teacher_total_derived"         in year_data.columns else np.nan
    _ptr_ov         = safe_mean(year_data, "ptr_students_per_teacher_raw")

    k1, k2, k3, k4, k5 = st.columns(5, gap="medium")
    with k1: metric_card("Districts",    str(int(year_data["district"].nunique())), f"Coverage {selected_year}", ACCENT)
    with k2: metric_card("Schools",      f"{int(_total_schools):,}"  if pd.notna(_total_schools)  else "—", "Reporting", BLUE)
    with k3: metric_card("Enrolment",    f"{int(_total_enroll):,}"   if pd.notna(_total_enroll)   else "—", "Total students", WARNING)
    with k4: metric_card("Teachers",     f"{int(_total_teachers):,}" if pd.notna(_total_teachers) else "—", "M+F+T", SUCCESS)
    with k5: metric_card("Avg. PTR",     fmt(_ptr_ov,1),
                         "Above RTE norm" if pd.notna(_ptr_ov) and _ptr_ov > 30 else "Within RTE norm",
                         DANGER if pd.notna(_ptr_ov) and _ptr_ov > 30 else SUCCESS)

    # v2 strip
    if historical_v2 is not None and "shala_score_v2" in historical_v2.columns:
        _v2yr  = historical_v2[historical_v2["academic_year"] == selected_year]
        _v2avg = safe_mean(_v2yr, "shala_score_v2")
        if "risk_tier_v2" in _v2yr.columns:
            _tc   = _v2yr["risk_tier_v2"].value_counts()
            _crit = int(_tc.get("Critical",0))
            _tn   = f"{_crit} Critical | {int(_tc.get('At-Risk',0))} At-Risk | {int(_tc.get('Stable',0))} Stable | {int(_tc.get('Thriving',0))} Thriving"
        else:
            _tn, _crit = "v2 active", 0
        _va, _vb = st.columns(2, gap="medium")
        with _va: metric_card("Avg Shala Score v2", fmt(_v2avg,1), "5-pillar weighted", ACCENT)
        with _vb: metric_card("Risk Tiers (v2)", _tn, "72 districts per tier", DANGER if _crit > 0 else WARNING)

    heading("What the data says")
    i1, i2, i3 = st.columns(3, gap="medium")
    with i1:
        if pd.notna(yoy):
            word = "rose" if yoy > 0 else "fell" if yoy < 0 else "held steady"
            insight_card("Trend", f"Maharashtra average {word}" + ("" if yoy == 0 else f" by {abs(yoy):.2f} pts") + f" vs {prev_year}.", ACCENT)
        else:
            insight_card("Trend", "First year in dataset -- no prior year to compare.", ACCENT)
    with i2:
        if pm:
            strongest = max(pm, key=pm.get); weakest = min(pm, key=pm.get)
            insight_card("Pillars", f"{strongest} leads ({pm[strongest]:.1f}). {weakest} has the most room to improve ({pm[weakest]:.1f}).", INFO)
    with i3:
        if top_row is not None and low_row is not None:
            insight_card("Gap", f"Highest to lowest: {top_row['shala_score_v1'] - low_row['shala_score_v1']:.2f} points.", WARNING)

    st.divider()

    if valid_scores.empty:
        st.warning("No valid Shala Score values for this year.")
    else:
        top10 = valid_scores.nlargest(10, "shala_score_v1").sort_values("shala_score_v1", ascending=True).copy()
        bot10 = valid_scores.nsmallest(10, "shala_score_v1").sort_values("shala_score_v1", ascending=False).copy()
        for d in (top10, bot10):
            d["district"] = d["district"].astype(str)
            d["_g"] = np.where(d["district"] == highlight, "Selected", "Other")

        rl, rr = st.columns(2, gap="large")
        for col_ui, data, title, sub, base_color in [
            (rl, top10, "Top-performing districts", "Ten highest Shala Scores.", SUCCESS),
            (rr, bot10, "Districts needing support", "Ten lowest Shala Scores.", DANGER),
        ]:
            with col_ui:
                heading(title, sub)
                fig = px.bar(data, x="shala_score_v1", y="district", orientation="h",
                             text="shala_score_v1", color="_g",
                             color_discrete_map={"Other": base_color, "Selected": WARNING},
                             labels={"shala_score_v1": "Shala Score", "district": ""})
                fig.update_traces(texttemplate="%{text:.1f}", textposition="outside",
                                  cliponaxis=False, marker_line_width=0)
                fig.update_layout(showlegend=False, bargap=0.28,
                                  xaxis_range=[0, max(108, float(data["shala_score_v1"].max())*1.16)])
                if pd.notna(state_avg):
                    fig.add_vline(x=float(state_avg), line_dash="dot", line_width=1.5,
                                  line_color=TEXT_LO, annotation_text="State avg",
                                  annotation_font_color=TEXT_LO)
                show(fig, 420, horizontal=True)

    st.divider()
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        heading("Score trend", "Average district Shala Score across all available years.")
        trend = historical.groupby("academic_year", as_index=False)["shala_score_v1"].mean()
        trend["_s"] = trend["academic_year"].apply(lambda x: int(str(x)[:4]) if re.match(r"^\d{4}", str(x)) else 0)
        trend = trend.sort_values("_s")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend["academic_year"], y=trend["shala_score_v1"],
            mode="lines+markers+text", name="Maharashtra average",
            line=dict(color=ACCENT, width=3), marker=dict(color=WARNING, size=9, line=dict(color=OBS_BG, width=2)),
            text=trend["shala_score_v1"].map(lambda v: f"{v:.1f}"), textposition="top center",
            textfont=dict(color=TEXT_MED, size=11), fill="tozeroy", fillcolor="rgba(56,189,248,0.07)",
        ))
        if not is_all:
            dh = historical[historical["district"] == district_choice].sort_values("_year_order")
            fig.add_trace(go.Scatter(
                x=dh["academic_year"], y=dh["shala_score_v1"], mode="lines+markers", name=district_choice,
                line=dict(color=WARNING, width=3), marker=dict(size=9, color=WARNING, line=dict(color=OBS_BG, width=2)),
            ))
        fig.update_xaxes(categoryorder="array", categoryarray=years)
        fig.update_layout(showlegend=not is_all, yaxis_title="Shala Score (0-100)")
        show(fig, 340, horizontal=True)

    with right:
        heading("Pillar profile", "Average pillar score (0-100)" + ("" if is_all else f" in {district_choice}") + ".")
        pdata = pd.DataFrame({"Pillar": list(PILLARS), "Score": [safe_mean(view_data, v) for v in PILLARS.values()]}).dropna()
        if pdata.empty:
            st.info("Pillar scores not available for this selection.")
        else:
            fig = px.bar(pdata, x="Score", y="Pillar", orientation="h", text="Score", color="Pillar",
                         color_discrete_map=PILLAR_COLORS)
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False, marker_line_width=0)
            fig.update_layout(showlegend=False, bargap=0.42, xaxis_range=[0, 112])
            show(fig, 340, horizontal=True)

    # Priority matrix
    st.divider()
    heading("District priority matrix", "Score level vs year-on-year change.")
    if prev_year is None:
        st.info("Needs at least two years of data.")
    else:
        cur = year_data[["district","shala_score_v1"]].drop_duplicates("district").rename(columns={"shala_score_v1":"score"})
        prv = historical[historical["academic_year"] == prev_year][["district","shala_score_v1"]].drop_duplicates("district").rename(columns={"shala_score_v1":"prev"})
        m   = cur.merge(prv, on="district").dropna()
        m["change"] = m["score"] - m["prev"]
        m["district"] = m["district"].astype(str)
        hi_score = m["score"] >= state_avg
        up = m["change"] >= 0
        m["Group"] = np.select(
            [hi_score & up, hi_score & ~up, ~hi_score & up],
            ["Strong and improving","Strong but slipping","Below avg but improving"],
            default="Below avg and slipping",
        )
        gcol = {"Strong and improving": SUCCESS, "Strong but slipping": WARNING,
                "Below avg but improving": BLUE, "Below avg and slipping": DANGER}
        fig = px.scatter(m, x="score", y="change", color="Group", color_discrete_map=gcol,
                         hover_name="district",
                         labels={"score": f"Shala Score {selected_year}", "change": f"Change since {prev_year}"})
        fig.update_traces(marker=dict(size=12, line=dict(color=OBS_BG, width=1.5)))
        if pd.notna(state_avg): fig.add_vline(x=float(state_avg), line_dash="dot", line_color=TEXT_LO, line_width=1.5)
        fig.add_hline(y=0, line_dash="dot", line_color=TEXT_LO, line_width=1.5)
        show(fig, 450, horizontal=True)

    # Choropleth map
    st.divider()
    heading("Maharashtra district map", f"Shala Scores for {selected_year}.")
    if GEOJSON_FILE.exists():
        try:
            import json
            with open(GEOJSON_FILE, encoding="utf-8") as gf:
                geojson_data = json.load(gf)
            _GEO_ALIAS = {
                "ahmadnagar":"ahilyanagar","bid":"beed","aurangabad":"chhatrapati sambhajinagar",
                "osmanabad":"dharashiv","gondiya":"gondia","mumbai":"mumbai ii","raigarh":"raigad",
            }
            for feat in geojson_data.get("features",[]):
                props = feat.get("properties",{})
                raw_norm = normalize_district(props.get("dtname",""))
                props["dtname_norm"] = _GEO_ALIAS.get(raw_norm, raw_norm)
                feat["properties"] = props
            map_df = year_data[["district","shala_score_v1"]].copy()
            map_df["district"] = map_df["district"].astype(str)
            map_df["district_norm"] = map_df["district"].apply(normalize_district)
            try:
                fig_map = px.choropleth_map(
                    map_df, geojson=geojson_data, locations="district_norm",
                    featureidkey="properties.dtname_norm", color="shala_score_v1",
                    color_continuous_scale=["#0A0F1E","#1E2D45","#0EA5E9","#38BDF8","#7DD3FC"],
                    range_color=(0,100), map_style="carto-darkmatter",
                    zoom=5.6, center={"lat":19.5,"lon":76.5}, opacity=0.80,
                    labels={"shala_score_v1":"Shala Score"}, hover_name="district",
                    hover_data={"shala_score_v1":":.1f","district_norm":False},
                )
            except AttributeError:
                fig_map = px.choropleth_mapbox(
                    map_df, geojson=geojson_data, locations="district_norm",
                    featureidkey="properties.dtname_norm", color="shala_score_v1",
                    color_continuous_scale=["#0A0F1E","#1E2D45","#0EA5E9","#38BDF8","#7DD3FC"],
                    range_color=(0,100), mapbox_style="carto-darkmatter",
                    zoom=5.6, center={"lat":19.5,"lon":76.5}, opacity=0.80,
                    labels={"shala_score_v1":"Shala Score"}, hover_name="district",
                    hover_data={"shala_score_v1":":.1f","district_norm":False},
                )
            fig_map.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=500,
                                   paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_map, config={"displaylogo":False})
        except Exception as exc:
            st.info(f"Map unavailable: {exc}")
    else:
        st.info("GeoJSON not found at assets/maharashtra_districts.geojson")

# ===========================================================================
# PAGE: DISTRICT EXPLORER
# ===========================================================================
elif page == "District Explorer":
    heading("District Explorer", "Full district profile, comparison, historical trends, and forecast.")

    if is_all:
        focus = st.selectbox("Choose a district", districts, key="explorer_district")
    else:
        focus = district_choice
        st.caption(f"District from sidebar: **{focus}**")

    dh  = historical[historical["district"] == focus].sort_values("_year_order")
    dc  = dh[dh["academic_year"] == selected_year]
    dfc = forecast[forecast["district"] == focus] if forecast is not None else pd.DataFrame()

    if dc.empty:
        st.warning("No record for this district and year.")
    else:
        cur      = dc.iloc[0]
        names    = valid_scores["district"].astype(str).tolist()
        rank_num = names.index(focus) + 1 if focus in names else None
        rank_txt = f"{rank_num} / {len(names)}" if rank_num else "—"

        st.html(
            f'<div class="dist-headline">'
            f'<div class="dh-eyebrow">District Profile · {escape(str(selected_year))}</div>'
            f'<div class="dh-name">{escape(focus)}</div>'
            + (f'<div class="dh-sub">Rank {rank_txt}</div>' if rank_txt != "—" else "")
            + "</div>"
        )

        # v2 risk tier badge
        if historical_v2 is not None and "risk_tier_v2" in historical_v2.columns:
            _v2row = historical_v2[
                (historical_v2["district"] == focus) &
                (historical_v2["academic_year"] == selected_year)
            ]
            if not _v2row.empty:
                _tier = str(_v2row.iloc[0].get("risk_tier_v2","—"))
                _v2sc = _v2row.iloc[0].get("shala_score_v2", np.nan)
                _TC   = {"Thriving": SUCCESS, "Stable": BLUE, "At-Risk": WARNING, "Critical": DANGER}
                _tc   = _TC.get(_tier, TEXT_LO)
                st.html(
                    f'<div style="display:flex;gap:10px;align-items:center;margin-bottom:8px;flex-wrap:wrap">'
                    f'<span class="badge" style="background:{_tc}22;color:{_tc};border:1px solid {_tc}44;'
                    f'font-size:11px;padding:4px 12px">Shala Score v2 Risk Tier: {escape(_tier)}</span>'
                    + (f'<span style="font-size:12px;color:{TEXT_LO}">v2 Score: {_v2sc:.1f} / 100</span>'
                       if pd.notna(_v2sc) else "")
                    + '</div>'
                )

        # SHAP top driver
        _shap_top_path = SHAP_DIR / "m5_shap_top_driver.csv"
        _shap_top = load_csv(_shap_top_path)
        if _shap_top is not None:
            _sd = _shap_top[_shap_top["district"].astype(str) == str(focus)]
            if not _sd.empty:
                _READABLE = {
                    "pillar2_participation":"Student Participation","pillar2_infrastructure":"Infrastructure Score",
                    "pillar2_digital":"Digital Readiness","pillar2_teacher_ptr":"Teacher PTR Score",
                    "ptr_students_per_teacher_raw":"Pupil-Teacher Ratio","school_count":"School Count",
                    "enrollment_reported_student_total":"Student Enrolment","year_num":"Year Trend",
                }
                _top_feat = str(_sd.iloc[0]["top_driver"])
                _top_shap = float(_sd.iloc[0]["top_shap_abs"])
                _feat_lbl = _READABLE.get(_top_feat, _top_feat)
                insight_card("M5 SHAP -- Top Risk Driver",
                             f"{_feat_lbl}  (|SHAP|={_top_shap:.4f}) -- strongest feature for {focus}.",
                             ACCENT)

        # Two-column grid
        _ml, _mr = st.columns([1.4, 1], gap="medium")
        with _ml:
            step_flow(1, "Score & Rank")
            score_gauge("Shala Score v1", cur.get("shala_score_v1"), state_avg, accent=ACCENT)
            metric_card("Statewide Rank", rank_txt, f"{len(valid_scores)} districts scored  {selected_year}", BLUE)

            step_flow(2, "Pillar Scores")
            _p1, _p2, _p3 = st.columns(3, gap="small")
            for _pc, (pname, pcol, pacc) in zip(
                [_p1, _p2, _p3],
                [("Teacher Strength","pillar_teacher_strength",ACCENT),
                 ("Infrastructure","pillar_infrastructure",WARNING),
                 ("Digital","pillar_digital_readiness",BLUE)],
            ):
                with _pc:
                    _pv = cur.get(pcol)
                    _ps = state_pillars.get(pname, np.nan)
                    _pd = (float(_pv) - float(_ps)) if pd.notna(_pv) and pd.notna(_ps) else np.nan
                    metric_card(pname, fmt(_pv, 1),
                                f"State {fmt(_ps,1)}" + (f" ({_pd:+.1f})" if pd.notna(_pd) else ""),
                                pacc)

            step_flow(3, "Ratio Indicators")
            ratio_bar("Pupil-Teacher Ratio",        cur.get("ptr_students_per_teacher_raw"),        "students/teacher",
                      safe_mean(year_data,"ptr_students_per_teacher_raw"),        30, 35, True,  bar_max=50)
            ratio_bar("Functional Toilet Coverage", cur.get("functional_toilet_pct_raw"),           "%",
                      safe_mean(year_data,"functional_toilet_pct_raw"),           90, 85, False)
            ratio_bar("Good-Condition Classrooms",  cur.get("good_classroom_pct_raw"),              "%",
                      safe_mean(year_data,"good_classroom_pct_raw"),              90, 75, False)
            ratio_bar("Digital Devices / School",   cur.get("digital_devices_per_school_raw"),      "devices",
                      safe_mean(year_data,"digital_devices_per_school_raw"),      5,  2,  False, bar_max=50)

        with _mr:
            st.html('<div class="right-panel-sticky">')
            step_flow(4, "Diagnostic Indicators")
            RC_PATH = ROOT / "reports/rootcause/educational_rootcause_indicators.csv"
            _rc_all = load_csv(RC_PATH)
            if _rc_all is not None:
                _rc_dist = _rc_all[
                    (_rc_all["district"].astype(str) == str(focus)) &
                    (_rc_all["academic_year"].astype(str) == str(selected_year))
                ].copy()
                _SC = {"ADEQUATE": SUCCESS,"CONCERN": WARNING,"CRITICAL": DANGER,"DATA MISSING": TEXT_LO}
                if _rc_dist.empty:
                    st.info(f"No diagnostic data for {focus} in {selected_year}.")
                else:
                    _rc_dist["value"] = numeric(_rc_dist["value"])
                    for _, irow in _rc_dist.iterrows():
                        _acc = _SC.get(str(irow["status"]), TEXT_LO)
                        _sm  = numeric(pd.Series([irow["state_mean"]])).iloc[0]
                        rc_card(str(irow["indicator"]),
                                f"{irow['value']:.1f} {irow['unit']}" if pd.notna(irow["value"]) else "No data",
                                f"State avg: {_sm:.1f} {irow['unit']}" if pd.notna(_sm) else "",
                                str(irow["status"]), str(irow["explanation"]), _acc)
            else:
                fa = focus_area(cur)
                if fa:
                    insight_card("Weakest pillar", f"{fa} is {focus}'s weakest pillar ({cur[PILLARS[fa]]:.1f}/100).", TERRA)
                st.caption("Run build_rootcause_indicators.py for full diagnostics.")
            st.html('</div>')

        st.divider()
        step_flow(5, "Score History & Comparison")
        a, b = st.columns(2, gap="large")
        with a:
            heading("Pillar comparison", f"{focus} vs Maharashtra average in {selected_year}.")
            comp_p = pd.DataFrame({
                "Pillar": list(PILLARS) * 2,
                "Group":  [focus]*3 + ["Maharashtra avg"]*3,
                "Score":  [cur.get(v) for v in PILLARS.values()] + [state_pillars[k] for k in PILLARS],
            })
            fig = px.bar(comp_p, x="Pillar", y="Score", color="Group", barmode="group", text="Score",
                         color_discrete_map={focus: ACCENT, "Maharashtra avg": TEXT_LO})
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False, marker_line_width=0)
            fig.update_layout(yaxis_range=[0, 112], bargap=0.3)
            show(fig, 320)
        with b:
            heading("Score history", f"{focus} vs state average.")
            tr = historical.groupby("academic_year", as_index=False)["shala_score_v1"].mean()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dh["academic_year"], y=dh["shala_score_v1"],
                                     mode="lines+markers", name=focus,
                                     line=dict(color=ACCENT, width=3),
                                     marker=dict(size=9, color=ACCENT, line=dict(color=OBS_BG, width=2))))
            fig.add_trace(go.Scatter(x=tr["academic_year"], y=tr["shala_score_v1"],
                                     mode="lines+markers", name="Maharashtra avg",
                                     line=dict(color=TEXT_LO, width=2, dash="dot"),
                                     marker=dict(size=7)))
            fig.update_xaxes(categoryorder="array", categoryarray=years)
            show(fig, 320)

        # Forecast section
        if not dfc.empty:
            f_row = dfc.iloc[0]
            step_flow(6, "Upcoming Year Forecast")
            f1, f2, f3 = st.columns(3, gap="medium")
            with f1:
                d = f_row["forecast_shala_score_v1"] - cur["shala_score_v1"] if pd.notna(f_row["forecast_shala_score_v1"]) and pd.notna(cur["shala_score_v1"]) else np.nan
                metric_card("Forecast Shala Score", fmt(f_row["forecast_shala_score_v1"],1),
                            ("—" if pd.isna(d) else f"{d:+.1f} vs {selected_year}"), ACCENT)
            with f2:
                metric_card("Forecast Teachers", fmt(f_row.get("forecast_teachers",np.nan),0), "Persistence baseline", SUCCESS)
            with f3:
                metric_card("Performance Band", str(f_row["forecast_relative_performance_band"]),
                            "Past score quartile", INFO)
            st.caption("Enrollment/Teachers/Toilets/Classrooms: Persistence baseline. Digital: district trend. Experimental only.")

        st.divider()
        heading("Compare districts", "Up to 5 districts side by side.")
        pick = st.multiselect("Districts", districts, default=[focus] if focus in districts else [], max_selections=5, key="compare_districts")
        if pick:
            cd   = year_data[year_data["district"].isin(pick)]
            long = cd.melt(id_vars="district", value_vars=list(PILLARS.values()), var_name="Pillar", value_name="Score")
            long["Pillar"] = long["Pillar"].map({v:k for k,v in PILLARS.items()})
            fig = px.bar(long, x="Pillar", y="Score", color="district", barmode="group", text="Score",
                         color_discrete_sequence=[ACCENT,WARNING,SUCCESS,INFO,DANGER],
                         labels={"district":"District"})
            fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False, marker_line_width=0)
            fig.update_layout(yaxis_range=[0,112], bargap=0.3)
            show(fig, 360)

        st.divider()
        heading("All districts heatmap", "Every district and pillar sorted by Shala Score.")
        if not valid_scores.empty:
            hm = valid_scores[["district"]+list(PILLARS.values())].copy().set_index("district")
            hm.columns = list(PILLARS)
            fig = px.imshow(hm, aspect="auto", text_auto=".0f", zmin=0, zmax=100,
                            color_continuous_scale=["#0A0F1E","#1E2D45","#0EA5E9","#38BDF8","#7DD3FC"])
            fig.update_xaxes(side="top")
            show(fig, max(380, 24*len(hm)+100))

# ===========================================================================
# PAGE: EDUCATION ANALYTICS
# ===========================================================================
elif page == "Education Analytics":
    heading("Education Analytics", "One indicator at a time, plus a relationship explorer.")

    indicator_options = {
        "Teacher Strength score":           ("pillar_teacher_strength",           True,  "Score 0-100 for teacher staffing."),
        "Infrastructure score":             ("pillar_infrastructure",             True,  "Score 0-100 for toilets and classrooms."),
        "Digital Readiness score":          ("pillar_digital_readiness",          True,  "Score 0-100 for digital devices."),
        "Reported student enrolment":       ("enrollment_reported_student_total", True,  "Total students reported by schools."),
        "Total teachers (derived)":         ("score_teacher_total_derived",       True,  "Number of teachers in the district."),
        "Students per teacher":             ("ptr_students_per_teacher_raw",      False, "Lower = more attention per student."),
        "Functional toilets (%)":           ("functional_toilet_pct_raw",         True,  "Share of toilets that are working."),
        "Good-condition classrooms (%)":    ("good_classroom_pct_raw",            True,  "Share of classrooms in good condition."),
        "Digital devices / reporting school":("digital_devices_per_school_raw",   True,  "Average devices in schools that report."),
        "School count":                     ("school_count",                      True,  "Number of schools in the district."),
    }
    available = {k: v for k, v in indicator_options.items() if v[0] in year_data.columns}

    if not available:
        st.warning("No supported indicators found in the dataset.")
    else:
        c_a, c_b = st.columns([1.4, 1], gap="large")
        with c_a:
            chosen_label = st.selectbox("Choose an indicator", list(available), key="analytics_indicator")
        with c_b:
            view_mode = st.radio("Show", ["Best 10","Weakest 10","All"], horizontal=True, key="analytics_view")
        chosen_col, higher_better, meaning = available[chosen_label]

        tmp = year_data[["district", chosen_col]].copy()
        tmp["district"] = tmp["district"].astype(str)
        tmp[chosen_col] = numeric(tmp[chosen_col])
        tmp = tmp.dropna(subset=[chosen_col]).sort_values(chosen_col, ascending=not higher_better)

        if tmp.empty:
            st.info("No valid values for this indicator.")
        else:
            st.caption(meaning)
            best, worst = tmp.iloc[0], tmp.iloc[-1]
            k1,k2,k3,k4 = st.columns(4, gap="medium")
            with k1: metric_card("Maharashtra avg", fmt(tmp[chosen_col].mean(),2), chosen_label, ACCENT)
            with k2: metric_card("Best district",   str(best["district"]),         fmt(best[chosen_col],2),  SUCCESS)
            with k3: metric_card("Needs support",   str(worst["district"]),        fmt(worst[chosen_col],2), DANGER)
            with k4: metric_card("Districts w/ data", f"{len(tmp):,}", f"Year {selected_year}", BLUE)

            n = len(tmp); third = max(1, n//3)
            tmp["_rank"] = range(1,n+1)
            tmp["Group"] = np.where(tmp["_rank"]<=third, "Strongest", np.where(tmp["_rank"]>n-third, "Weakest", "Middle"))
            shown = (tmp.head(10) if view_mode=="Best 10" else tmp.tail(10) if view_mode=="Weakest 10" else tmp).copy()
            shown = shown.sort_values(chosen_col, ascending=higher_better)
            shown["Group"] = np.where(shown["district"]==highlight, "Selected", shown["Group"])

            fig = px.bar(shown, x=chosen_col, y="district", orientation="h", text=chosen_col, color="Group",
                         color_discrete_map={"Strongest":SUCCESS,"Middle":WARNING,"Weakest":DANGER,"Selected":ACCENT},
                         labels={chosen_col: chosen_label, "district":""})
            fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside", cliponaxis=False, marker_line_width=0)
            xmax = float(shown[chosen_col].max())
            fig.update_layout(xaxis_range=[min(0.0, float(shown[chosen_col].min())), xmax*1.2 if xmax>0 else 1], bargap=0.3)
            fig.add_vline(x=float(tmp[chosen_col].mean()), line_dash="dot", line_color=TEXT_LO, line_width=1.5,
                          annotation_text="Maharashtra mean", annotation_font_color=TEXT_LO)
            if chosen_col == "ptr_students_per_teacher_raw":
                fig.add_vline(x=30, line_dash="dash", line_color=DANGER, line_width=2,
                              annotation_text="RTE Norm 30:1", annotation_font_color=DANGER)
            show(fig, max(400, 28*len(shown)+100), horizontal=True)

            heading("Trend over time")
            t = historical.groupby("academic_year", as_index=False)[chosen_col].mean()
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=t["academic_year"], y=t[chosen_col], mode="lines+markers",
                                      name="Maharashtra avg", line=dict(color=ACCENT, width=3),
                                      marker=dict(size=8, color=WARNING, line=dict(color=OBS_BG,width=2))))
            if not is_all:
                dd = historical[historical["district"]==district_choice].sort_values("_year_order")
                fig2.add_trace(go.Scatter(x=dd["academic_year"], y=dd[chosen_col], mode="lines+markers",
                                          name=district_choice, line=dict(color=WARNING, width=3),
                                          marker=dict(size=8, color=WARNING)))
            fig2.update_xaxes(categoryorder="array", categoryarray=years)
            show(fig2, 320, horizontal=True)

        st.divider()
        heading("Relationship explorer", "How two indicators relate across districts.")
        labels = list(available)
        r1, r2 = st.columns(2, gap="large")
        with r1: x_label = st.selectbox("Horizontal axis", labels, index=0, key="rel_x")
        with r2: y_label = st.selectbox("Vertical axis",   labels, index=min(1,len(labels)-1), key="rel_y")
        xc, yc = available[x_label][0], available[y_label][0]
        if xc == yc:
            st.info("Choose two different indicators.")
        else:
            rel = year_data[["district",xc,yc]].copy()
            rel["district"] = rel["district"].astype(str)
            rel[xc] = numeric(rel[xc]); rel[yc] = numeric(rel[yc])
            rel = rel.dropna()
            if len(rel) < 3:
                st.info("Not enough districts with both values.")
            else:
                r = float(np.corrcoef(rel[xc], rel[yc])[0,1])
                rel["Group"] = np.where(rel["district"]==highlight, "Selected", "Other")
                fig3 = px.scatter(rel, x=xc, y=yc, color="Group", hover_name="district",
                                  color_discrete_map={"Other": ACCENT, "Selected": WARNING},
                                  labels={xc:x_label, yc:y_label})
                fig3.update_traces(marker=dict(size=12, line=dict(color=OBS_BG,width=1.5)))
                show(fig3, 420, horizontal=True)
                strength = "strong" if abs(r)>=0.6 else "moderate" if abs(r)>=0.3 else "weak"
                st.caption(f"r = {r:.2f} ({strength} {'positive' if r>=0 else 'negative'} relationship, {len(rel)} districts). Correlation is not causation.")

# ===========================================================================
# PAGE: PREDICTIVE INTELLIGENCE
# ===========================================================================
elif page == "Predictive Intelligence":
    heading("Predictive Intelligence Studio",
            "M1-M5 model outputs and a non-destructive What-If simulator.")

    fvalid = forecast.dropna(subset=["forecast_shala_score_v1"])
    if not fvalid.empty:
        fh, fl = fvalid.loc[fvalid["forecast_shala_score_v1"].idxmax()], fvalid.loc[fvalid["forecast_shala_score_v1"].idxmin()]
        s1,s2,s3,s4 = st.columns(4, gap="medium")
        with s1: metric_card("Districts forecast",   f"{forecast['district'].nunique():,}", "Upcoming year", ACCENT)
        with s2: metric_card("Avg forecast score",   fmt(fvalid["forecast_shala_score_v1"].mean(),2), f"Actual avg {fmt(state_avg,2)}", BLUE)
        with s3: metric_card("Highest forecast",     str(fh["district"]),  fmt(fh["forecast_shala_score_v1"],2), SUCCESS)
        with s4: metric_card("Lowest forecast",      str(fl["district"]),  fmt(fl["forecast_shala_score_v1"],2), DANGER)

    # ── M1-M5 model outputs ───────────────────────────────────────────────
    st.divider()
    heading("Trained Model Results (M1-M5)",
            "Outputs from models trained on 2018-2024, evaluated on 2024-25.")

    _mt = st.tabs(["M1 Enrolment","M2 Learning Proxy","M3 Total Enrolment","M4 Teacher Risk","M5 Infra Proxy","All Metrics"])

    with _mt[0]:
        st.markdown("**M1 -- Enrolment / Decline Trend** (LinearRegression, R2=0.7784)")
        _m1f = load_csv(MODELS_DIR / "m1_enrolment_forecast.csv")
        _m1t = load_csv(MODELS_DIR / "m1_test_predictions.csv")
        if _m1f is not None:
            _m1f["forecast_enrolment"] = numeric(_m1f["forecast_enrolment"])
            _flt = _m1f if is_all else _m1f[_m1f["district"] == district_choice]
            if not _flt.empty:
                fig = px.bar(_flt, x="district", y="forecast_enrolment", color="forecast_year",
                             barmode="group", color_discrete_sequence=[ACCENT, WARNING],
                             labels={"forecast_enrolment":"Forecast Enrolment"})
                fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside", cliponaxis=False)
                fig.update_layout(xaxis_tickangle=-45, bargap=0.3)
                show(fig, 380)
        else:
            st.info("Run src/models/run_prediction_modules.py to generate M1 outputs.")
        if _m1t is not None:
            _flt2 = _m1t if is_all else _m1t[_m1t["district"] == district_choice]
            st.dataframe(_flt2, hide_index=True)

    with _mt[1]:
        st.markdown("**M2 -- Learning Outcome (SUBSTITUTE_PROXY)**")
        st.warning("No NAS/ASER/GER/dropout data exists in UDISE+. M2 uses classroom-quality trend (pillar2_infrastructure) as a **documented substitute proxy**. NOT a learning outcome score. Ridge R2=0.5204.")
        _m2p = load_csv(MODELS_DIR / "m2_learning_proxy_predictions.csv")
        if _m2p is not None:
            _flt3 = _m2p if is_all else _m2p[_m2p["district"] == district_choice]
            st.dataframe(_flt3[["district","academic_year","actual_infra_score","predicted_infra_score","NOTE"]], hide_index=True)
        else:
            st.info("Run src/models/run_prediction_modules.py to generate M2 outputs.")

    with _mt[2]:
        st.markdown("**M3 -- Total Student Enrolment Forecast** (Holt-Winters per district, R2=0.9967)")
        st.caption("Target: enrollment_reported_student_total. 36/36 districts fitted. 2-year horizon.")
        _m3f = load_csv(MODELS_DIR / "m3_total_enrolment_forecast.csv")
        _m3t = load_csv(MODELS_DIR / "m3_total_enrolment_test.csv")
        if _m3f is not None:
            _m3f["forecast_total_enrolment"] = numeric(_m3f["forecast_total_enrolment"])
            _flt4 = _m3f if is_all else _m3f[_m3f["district"] == district_choice]
            if not _flt4.empty:
                fig = px.bar(_flt4, x="district", y="forecast_total_enrolment", color="forecast_year",
                             barmode="group", color_discrete_sequence=[ACCENT, WARNING],
                             labels={"forecast_total_enrolment":"Forecast Total Enrolment"})
                fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside", cliponaxis=False)
                fig.update_layout(xaxis_tickangle=-45, bargap=0.3)
                show(fig, 380)
        else:
            st.info("Run src/models/run_prediction_modules.py to generate M3 outputs.")
        if _m3t is not None:
            _flt5 = _m3t if is_all else _m3t[_m3t["district"] == district_choice]
            st.dataframe(_flt5, hide_index=True)

    with _mt[3]:
        st.markdown("**M4 -- Teacher Shortage Risk** (RandomForest, Acc=0.972, F1=0.973)")
        st.caption("Target: PTR > 30 (RTE norm). PTR excluded from features.")
        _m4p = load_csv(MODELS_DIR / "m4_teacher_shortage_predictions.csv")
        _m4fi= load_csv(MODELS_DIR / "m4_feature_importance.csv")
        if _m4p is not None:
            _m4p["predicted_proba_risk"] = numeric(_m4p["predicted_proba_risk"])
            _flt6 = (_m4p if is_all else _m4p[_m4p["district"] == district_choice]).sort_values("predicted_proba_risk", ascending=False)
            if not _flt6.empty:
                fig = px.bar(_flt6, x="district", y="predicted_proba_risk",
                             color="predicted_shortage_risk",
                             color_discrete_map={1: DANGER, 0: SUCCESS},
                             labels={"predicted_proba_risk":"Risk Probability","predicted_shortage_risk":"Shortage Risk"})
                fig.add_hline(y=0.5, line_dash="dot", line_color=TEXT_LO, annotation_text="Decision threshold 0.5")
                fig.update_layout(xaxis_tickangle=-45)
                show(fig, 380)
        else:
            st.info("Run src/models/run_prediction_modules.py to generate M4 outputs.")
        if _m4fi is not None:
            st.caption("Feature importance:"); st.dataframe(_m4fi, hide_index=True)

    with _mt[4]:
        st.markdown("**M5 -- Classroom Infrastructure Quality Trend (Documented Proxy)**")
        st.warning("Target: risk_tier_v2 (derived from infrastructure-quality pillar scores). NOT a learning-outcome or dropout predictor. shala_score_v2 excluded from features (leakage guard). Acc=0.694, F1=0.671.")
        _m5p  = load_csv(MODELS_DIR / "m5_risk_class_predictions.csv")
        _m5fi = load_csv(MODELS_DIR / "m5_feature_importance.csv")
        if _m5p is not None:
            _TC2 = {"Thriving": SUCCESS, "Stable": BLUE, "At-Risk": WARNING, "Critical": DANGER}
            _flt7 = _m5p if is_all else _m5p[_m5p["district"] == district_choice]
            if not _flt7.empty:
                _flt7 = _flt7.copy(); _flt7["predicted_risk_tier"] = _flt7["predicted_risk_tier"].astype(str)
                fig = px.bar(_flt7, x="district", y="shala_score_v2", color="predicted_risk_tier",
                             color_discrete_map=_TC2,
                             labels={"shala_score_v2":"Shala Score v2","predicted_risk_tier":"Predicted Risk Tier"})
                fig.update_layout(xaxis_tickangle=-45)
                show(fig, 380)
        else:
            st.info("Run src/models/run_prediction_modules.py to generate M5 outputs.")
        if _m5fi is not None:
            st.caption("Feature importance:"); st.dataframe(_m5fi, hide_index=True)

    with _mt[5]:
        st.markdown("**All Modules -- Metrics Summary**")
        _all = load_csv(MODELS_DIR / "all_modules_metrics_summary.csv")
        if _all is not None:
            for c in ["mae","rmse","r2","accuracy","f1_weighted"]:
                if c in _all.columns: _all[c] = numeric(_all[c]).round(4)
            st.dataframe(_all, hide_index=True)
        else:
            st.info("Run src/models/run_prediction_modules.py to generate the summary.")
        st.caption("M1-M3: regression (MAE, RMSE, R2). M4-M5: classification (Acc, F1). Train 2018-19 to 2023-24. Test 2024-25.")

    # ── What-If simulator ─────────────────────────────────────────────────
    st.divider()
    heading("What-If Simulator",
            "Non-destructive in-memory scenario. No source CSVs are written.")

    prediction_specs = [
        ("Shala Score",       "forecast_shala_score_v1",         "Shala Score scenario",
         "Combine three pillar sliders using the existing score formula.",
         ACCENT, "gauge", "shala_score_v1",         None, "/ 100"),
        ("Student Enrolment", "forecast_enrollment",             "Enrolment scenario",
         "Apply an assumed % change to the forecast baseline.",
         WARNING, "bar",   "enrollment_reported_student_total",
         ("forecast_enrollment_lower_p10","forecast_enrollment_upper_p90"), "Students"),
        ("Teacher Strength",  "forecast_teachers",               "Teacher deployment scenario",
         "Add or remove teachers against the existing baseline.",
         SUCCESS, "bar",   "score_teacher_total_derived",
         ("forecast_teachers_lower_p10","forecast_teachers_upper_p90"), "Teachers"),
        ("Functional Toilets","forecast_functional_toilet_pct",  "Toilet scenario",
         "Percentage-point improvement over the forecast baseline.",
         INFO,   "gauge", "functional_toilet_pct_raw",
         ("forecast_toilet_lower_p10","forecast_toilet_upper_p90"), "%"),
        ("Classroom Quality", "forecast_good_classroom_pct",     "Classroom quality scenario",
         "Improvement in share of good-condition classrooms.",
         BLUE,   "gauge", "good_classroom_pct_raw",
         ("forecast_classroom_lower_p10","forecast_classroom_upper_p90"), "%"),
        ("Digital Readiness", "forecast_digital_devices_per_school","Digital readiness scenario",
         "Additional devices per reporting school over the forecast baseline.",
         TERRA,  "bar",   "digital_devices_per_school_raw",
         ("forecast_digital_lower_p10","forecast_digital_upper_p90"), "Devices/school"),
    ]
    pred_tabs = st.tabs([s[0] for s in prediction_specs])

    def _scenario_chart(title, baseline, scenario, accent, kind, unit=""):
        base_ok = baseline is not None and pd.notna(baseline)
        scen_ok = scenario is not None and pd.notna(scenario)
        if not base_ok and not scen_ok: return
        if kind == "gauge":
            shown = float(scenario if scen_ok else baseline)
            gauge = {"axis":{"range":[0,100]},"bar":{"color":accent,"thickness":0.28},
                     "bgcolor":OBS_RAISED,"borderwidth":0,"steps":[{"range":[0,100],"color":OBS_RAISED}]}
            if base_ok and scen_ok:
                gauge["threshold"] = {"line":{"color":WARNING,"width":4},"thickness":0.80,"value":float(baseline)}
            fig = go.Figure(go.Indicator(mode="gauge+number", value=shown,
                                         number={"valueformat":".1f","font":{"size":40,"color":TEXT_HI}},
                                         title={"text":title,"font":{"size":13,"color":TEXT_MED}}, gauge=gauge))
            fig.update_layout(height=280, margin=dict(l=22,r=22,t=50,b=20), paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_MED))
        else:
            names, vals, colors = [], [], []
            if base_ok:  names.append("CSV forecast"); vals.append(float(baseline)); colors.append(TEXT_LO)
            if scen_ok:  names.append("Your scenario"); vals.append(float(scenario)); colors.append(accent)
            labels = [f"{v:,.1f}" if abs(v)<10000 else f"{v:,.0f}" for v in vals]
            fig = go.Figure(go.Bar(x=names, y=vals, marker_color=colors, text=labels,
                                   textposition="outside", cliponaxis=False, marker_line_width=0,
                                   hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>"))
            ymax = max(vals) if vals else 1
            fig.update_layout(height=280, yaxis_title=unit or "Value", bargap=0.42,
                              yaxis_range=[0, ymax*1.25 if ymax>0 else 1],
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color=TEXT_MED))
        st.plotly_chart(fig, theme=None, config={"displaylogo":False})

    for idx, (pred_tab, spec) in enumerate(zip(pred_tabs, prediction_specs)):
        label, col, display, explanation, accent, visual_kind, acol, rng, unit_label = spec
        with pred_tab:
            st.html(f'<div class="prediction-banner" style="--accent:{accent}">'
                    f'<div class="kicker">WHAT-IF WORKSPACE 0{idx+1}/06</div>'
                    f'<div class="title">{escape(display)}</div>'
                    f'<div class="desc">{escape(explanation)}</div></div>')
            if col not in forecast.columns:
                st.warning(f"Forecast column '{col}' not in forecast dataset.")
                continue

            data = forecast[["district",col]].copy()
            data[col] = numeric(data[col])
            data = data.dropna(subset=[col]).drop_duplicates("district")
            if not is_all: data = data[data["district"] == district_choice]
            if data.empty:
                st.info("No forecast values for this district filter.")
                continue

            scenario_district = district_choice if not is_all else st.selectbox(
                "Choose district", sorted(data["district"].astype(str).unique()), key=f"sd_{idx}")
            row_match  = forecast[forecast["district"].astype(str) == str(scenario_district)]
            baseline_v = float(numeric(row_match[col]).dropna().iloc[0]) if not row_match.empty and col in row_match.columns and not numeric(row_match[col]).dropna().empty else np.nan
            hist_match = historical[historical["district"].astype(str) == str(scenario_district)].sort_values("_year_order")
            hist_row   = hist_match.iloc[-1] if not hist_match.empty else pd.Series(dtype=object)
            dkey = slug(scenario_district)
            rkey = f"sr_{idx}_{dkey}"
            dec  = 0 if idx in (1,2) else 2

            left2, right2 = st.columns([1.02, 0.98], gap="large")
            with left2:
                st.markdown("#### Set assumptions")
                with st.form(f"wf_{idx}_{dkey}"):
                    submitted = False
                    if idx == 0:
                        def _def(key): v = pd.to_numeric(pd.Series([hist_row.get(key,50)]),errors="coerce").iloc[0]; return float(np.clip(50.0 if pd.isna(v) else v,0,100))
                        t_val = st.slider("Teacher Strength", 0.0, 100.0, _def("pillar_teacher_strength"), 0.5)
                        i_val = st.slider("Infrastructure",   0.0, 100.0, _def("pillar_infrastructure"),   0.5)
                        d_val = st.slider("Digital Readiness",0.0, 100.0, _def("pillar_digital_readiness"), 0.5)
                        submitted = st.form_submit_button("Calculate")
                        if submitted: st.session_state[rkey] = {"value":(t_val+i_val+d_val)/3.0,"baseline":baseline_v,"detail":f"T={t_val:.1f} I={i_val:.1f} D={d_val:.1f}"}
                    elif idx == 1:
                        growth = st.number_input("Enrolment change (%)", min_value=-50.0, max_value=100.0, value=0.0, step=1.0)
                        submitted = st.form_submit_button("Calculate")
                        if submitted and pd.notna(baseline_v): st.session_state[rkey] = {"value":max(0.0,baseline_v*(1+growth/100)),"baseline":baseline_v,"detail":f"Change: {growth:+.1f}%"}
                    elif idx == 2:
                        change = st.number_input("Additional / fewer teachers", min_value=-10000, max_value=10000, value=0, step=1)
                        submitted = st.form_submit_button("Calculate")
                        if submitted and pd.notna(baseline_v): st.session_state[rkey] = {"value":max(0.0,baseline_v+change),"baseline":baseline_v,"detail":f"Adjustment: {change:+,}"}
                    elif idx in (3,4):
                        change = st.slider("Improvement (ppts)", -30.0, 30.0, 0.0, 1.0)
                        submitted = st.form_submit_button("Calculate")
                        if submitted and pd.notna(baseline_v): st.session_state[rkey] = {"value":float(np.clip(baseline_v+change,0,100)),"baseline":baseline_v,"detail":f"Adjustment: {change:+.1f} ppts"}
                    else:
                        add_dev = st.number_input("Additional devices/school", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                        submitted = st.form_submit_button("Calculate")
                        if submitted and pd.notna(baseline_v): st.session_state[rkey] = {"value":baseline_v+add_dev,"baseline":baseline_v,"detail":f"Added: +{add_dev:.1f}"}

            with right2:
                st.markdown("#### Scenario output")
                result = st.session_state.get(rkey)
                if result:
                    rv  = float(result["value"]); bv = result.get("baseline")
                    dt  = f"{rv - float(bv):+,.{dec}f} vs CSV forecast" if bv is not None and pd.notna(bv) else "Calculated"
                    st.html(f'<div class="result-card" style="--accent:{accent}">'
                            f'<div class="result-label">{escape(scenario_district)} SCENARIO</div>'
                            f'<div class="result-value">{rv:,.{dec}f}</div>'
                            f'<div class="result-note">{escape(dt)}<br>{escape(str(result.get("detail","")))}</div></div>')
                    _scenario_chart(f"{label} {scenario_district}", bv, rv, accent, visual_kind, unit_label)
                else:
                    btxt = "—" if pd.isna(baseline_v) else f"{baseline_v:,.{dec}f}"
                    st.html(f'<div class="result-card" style="--accent:{accent}">'
                            f'<div class="result-label">{escape(scenario_district)} BASELINE</div>'
                            f'<div class="result-value">{btxt}</div>'
                            f'<div class="result-note">Set assumptions and press Calculate.</div></div>')
                    if pd.notna(baseline_v): _scenario_chart(f"{label} baseline", baseline_v, None, accent, visual_kind, unit_label)

    st.info("What-If outputs are transparent in-memory scenarios applied to the saved CSV forecast baseline. No models are retrained and no source files are written.")

    # ── Auto-Optimize Top 3 Interventions ─────────────────────────────────
    st.divider()
    heading(
        "Auto-Optimize Top 3 Interventions",
        "Uses the Prescriptive Engine to find the 3 controllable inputs with "
        "the highest projected Shala Score gain. Non-destructive -- no source "
        "files are written and no models are retrained.",
    )

    _ao_district = district_choice if not is_all else st.selectbox(
        "Choose district for Auto-Optimize",
        sorted(districts),
        key="ao_district_select",
    )

    if st.button("Auto-Optimize Top 3 Interventions", key="ao_run_btn"):
        try:
            import sys as _ao_sys
            _ao_sys.path.insert(0, str(ROOT))
            from src.prescriptive import recommend_top_interventions as _rec

            # Build district row from latest available year
            _ao_hist = historical_v2 if historical_v2 is not None else historical
            _ao_rows = _ao_hist[
                (_ao_hist["district"] == _ao_district) &
                (_ao_hist["academic_year"] == selected_year)
            ]
            if _ao_rows.empty:
                st.warning(f"No data for {_ao_district} in {selected_year}.")
                st.stop()

            _ao_row  = _ao_rows.iloc[0].to_dict()
            _ao_bm   = {
                c: float(pd.to_numeric(_ao_hist[c], errors="coerce").mean())
                for c in [
                    "ptr_students_per_teacher_raw",
                    "functional_toilet_pct_raw",
                    "good_classroom_pct_raw",
                    "digital_devices_per_school_raw",
                ]
                if c in _ao_hist.columns
            }

            _ao_recs = _rec(_ao_row, _ao_bm, top_n=3)

            if not _ao_recs:
                st.info("No improvement opportunities found for this district in this year.")
            else:
                # Store in session state so results persist across reruns
                st.session_state["ao_results"] = {
                    "district": _ao_district,
                    "year":     selected_year,
                    "recs":     _ao_recs,
                }

        except Exception as _ao_exc:
            st.error(f"Auto-Optimize error: {_ao_exc}")

    # Render results if available in session state
    _ao_stored = st.session_state.get("ao_results")
    if _ao_stored and _ao_stored.get("district") == _ao_district:
        _ao_recs = _ao_stored["recs"]
        _ao_yr   = _ao_stored["year"]

        st.markdown(
            f"**Top {len(_ao_recs)} interventions for {_ao_district} ({_ao_yr})**  "
            f"— sorted by projected Shala Score gain"
        )

        # Score-lift bar chart
        import plotly.graph_objects as _ao_go

        _ao_labels   = [r["label"] for r in _ao_recs]
        _ao_deltas   = [r["delta_shala_score"] for r in _ao_recs]
        _ao_new_sc   = [r["new_shala_score"]   for r in _ao_recs]
        _ao_tiers    = [r["new_risk_tier"]      for r in _ao_recs]
        _TIER_CLRS   = {
            "Thriving": SUCCESS, "Stable": BLUE,
            "At-Risk":  WARNING, "Critical": DANGER,
        }
        _ao_colors = [_TIER_CLRS.get(t, ACCENT) for t in _ao_tiers]

        fig_ao = _ao_go.Figure(
            _ao_go.Bar(
                x=_ao_labels, y=_ao_deltas,
                marker_color=_ao_colors,
                text=[f"+{d:.2f} pts" for d in _ao_deltas],
                textposition="outside", cliponaxis=False, marker_line_width=0,
                hovertemplate="<b>%{x}</b><br>Score lift: +%{y:.2f} pts<extra></extra>",
            )
        )
        fig_ao.update_layout(
            height=320, bargap=0.4, yaxis_title="Projected Shala Score Lift (+pts)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_MED), margin=dict(l=30, r=30, t=30, b=80),
        )
        fig_ao.update_xaxes(tickfont=dict(size=11), automargin=True)
        st.plotly_chart(fig_ao, theme=None,
                        config={"displaylogo": False})

        # Detail cards for each recommendation
        for _ao_i, _ao_r in enumerate(_ao_recs, 1):
            _ao_tier_col = _TIER_CLRS.get(_ao_r["new_risk_tier"], ACCENT)
            st.html(
                f'<div class="insight-card" style="--accent:{_ao_tier_col}">'
                f'<div class="insight-title">#{_ao_i} &nbsp; {escape(_ao_r["label"])}</div>'
                f'<div class="insight-text">'
                f'Current: <b>{_ao_r["current_value"]:.1f}</b> &rarr; '
                f'Target: <b>{_ao_r["target_value"]:.1f}</b> '
                f'({_ao_r["improvement_pct_pt"]:+.1f} change) &nbsp;|&nbsp; '
                f'Score lift: <b>+{_ao_r["delta_shala_score"]:.3f} pts</b> &nbsp;|&nbsp; '
                f'New score: <b>{_ao_r["new_shala_score"]:.1f}</b> &nbsp;|&nbsp; '
                f'Tier: <b style="color:{_ao_tier_col}">{escape(_ao_r["new_risk_tier"])}</b>'
                f'</div></div>'
            )

        st.caption(
            "Score lift estimates use a conservative linear pillar-proxy model (~25% weight per pillar). "
            "Actual gains depend on implementation quality and other district factors. "
            "Not an official government projection. No source CSVs are modified."
        )

# ===========================================================================
# PAGE: DATA QUALITY & METHODOLOGY
# ===========================================================================
elif page == "Data Quality & Methodology":
    heading("Data Quality & Methodology",
            "Why ShalaScope exists, how complete the data is, and what it cannot tell you.")

    heading("Problem and approach")
    for n_, t_, b_ in [
        ("1","The problem", f"Maharashtra has {len(districts)} districts with very different school conditions. Planners need one comparable view of where support is needed most."),
        ("2","Shala Score v2","Teacher PTR, Infrastructure, Participation, and Digital Readiness are scored 0-100 and combined with proportional weighting. Learning Outcomes = MISSING_IN_SOURCE."),
        ("3","Looking ahead","Holt-Winters and Random Forest models produce district-level forecasts and risk classifications. What-If scenarios let you test assumptions non-destructively."),
    ]:
        st.html(f'<div class="step"><div class="step-no">{n_}</div><div class="step-body"><b>{escape(t_)}.</b> {escape(b_)}</div></div>')

    st.divider()
    heading("Dataset health", f"Coverage of main indicators in {selected_year}.")
    quality_fields = {
        "school_count":"Schools","enrollment_reported_student_total":"Enrolment",
        "score_teacher_total_derived":"Teachers","ptr_students_per_teacher_raw":"PTR",
        "functional_toilet_pct_raw":"Toilets %","good_classroom_pct_raw":"Classrooms %",
        "digital_devices_per_school_raw":"Devices/school","shala_score_v1":"Shala Score v1",
    }
    present = {c:l for c,l in quality_fields.items() if c in historical.columns}
    h1,h2,h3,h4 = st.columns(4, gap="medium")
    with h1: metric_card("Historical rows", f"{len(historical):,}", f"{historical['district'].nunique()} districts", ACCENT)
    with h2: metric_card("Academic years",  f"{historical['academic_year'].nunique()}", f"{years[0]} to {years[-1]}", INFO)
    with h3: metric_card("Forecast districts", f"{forecast['district'].nunique()}", "Upcoming year file", WARNING)
    cov_year = [numeric(year_data[c]).notna().mean()*100 for c in present if len(year_data)>0]
    with h4: metric_card("Avg coverage",   f"{np.mean(cov_year):.1f}%" if cov_year else "NA", f"Main indicators {selected_year}", SUCCESS)

    if present:
        cov = pd.DataFrame(
            {lab: [numeric(historical[historical["academic_year"]==y][c]).notna().mean()*100 for y in years]
             for c,lab in present.items()},
            index=years,
        )
        st.markdown("**Completeness by indicator and year (%)**")
        fig = px.imshow(cov, aspect="auto", text_auto=".0f", zmin=0, zmax=100,
                        color_continuous_scale=["#0A0F1E","#1E2D45","#0EA5E9","#38BDF8","#7DD3FC"])
        fig.update_xaxes(side="top")
        show(fig, max(300, 54*len(years)+120))
        st.caption("Bright = almost complete. Dark = missing data.")

    qrows = []
    for c,lab in present.items():
        vals = numeric(year_data[c])
        qrows.append({"Indicator":lab,"Records":len(vals),"Available":int(vals.notna().sum()),
                      "Missing":int(vals.isna().sum()),"Coverage (%)":round(float(vals.notna().mean()*100),2)})
    if qrows:
        st.markdown(f"**Coverage in {selected_year}**")
        st.dataframe(pd.DataFrame(qrows), hide_index=True)

    st.markdown("**MISSING_IN_SOURCE columns -- never fabricated**")
    _MISS = ["electricity_pct","drinking_water_pct","library_pct","ramp_pct","internet_pct",
             "learning_outcome","ger","dropout_rate","aser_score","nas_score"]
    miss_rows = [{"Column":c,"Status":"ABSENT (confirmed MISSING_IN_SOURCE)"} for c in _MISS]
    st.dataframe(pd.DataFrame(miss_rows), hide_index=True)

    st.divider()
    heading("Shala Score v2 methodology")
    st.latex(r"S_{v2} = \sum_{i \in available} w_i^{eff} \cdot p_i")
    st.markdown("""
- **p_i** = pillar score 0-100 (min-max normalised on P5-P95 of train data)
- **w_i_eff** = w_i / sum(w_j for available j)  -- proportional redistribution
- Learning Outcomes pillar weight = 0% (MISSING_IN_SOURCE; no NAS/ASER/GER/dropout data in UDISE+)
- No double-counting: `facility_classrooms_good_condition_pct` is in Infrastructure **only**
""")

    for item in [
        "M3 targets total student enrolment (enrollment_reported_student_total), not girls-only.",
        "M5 predicts risk_tier_v2 -- labelled Classroom Infrastructure Quality Trend (Documented Proxy). NOT dropout or learning outcome.",
        "Forecast P10-P90 ranges are empirical historical error ranges, not confidence intervals.",
        "Shala Score is not a government-certified ranking.",
    ]:
        st.markdown(f"- {item}")

# ===========================================================================
# PAGE: RISK FACTOR ANALYSIS
# ===========================================================================
elif page == "Risk Factor Analysis":
    heading("Risk Factor Analysis",
            "Random Forest feature importance for predicting Shala Score. Statistical association only -- not causal.")

    RF_DIR = ROOT / "reports/rf_risk_factor"
    rf_fi  = load_csv(RF_DIR / "rf_feature_importance.csv")
    rf_eval= load_csv(RF_DIR / "rf_evaluation.csv")
    _rf_meta = {}
    _rf_meta_p = RF_DIR / "rf_metadata.json"
    if _rf_meta_p.exists():
        import json as _json
        try: _rf_meta = _json.loads(_rf_meta_p.read_text(encoding="utf-8"))
        except Exception: pass

    if rf_fi is None:
        st.info("Random Forest outputs not found. Run `src/models/run_rf_risk_factor_analysis.py` to generate them.")
    else:
        _cv_mae = _rf_meta.get("cv_mean_mae", np.nan)
        _cv_r2  = _rf_meta.get("cv_mean_r2",  np.nan)
        kc1,kc2,kc3,kc4 = st.columns(4, gap="medium")
        with kc1: metric_card("Target Variable",    "Shala Score",           "Educational condition index 0-100", ACCENT)
        with kc2: metric_card("CV MAE",  f"{_cv_mae:.2f}" if pd.notna(_cv_mae) else "NA", "Mean Absolute Error", BLUE)
        with kc3: metric_card("CV R2",   f"{_cv_r2:.4f}" if pd.notna(_cv_r2)  else "NA", "5-fold KFold", SUCCESS)
        with kc4: metric_card("Samples", f"{_rf_meta.get('n_samples',288)}",  f"{_rf_meta.get('n_features',12)} features", INFO)

        heading("Feature importance ranking")
        fi = rf_fi.copy()
        FEAT_LBL = {
            "good_classroom_pct_raw":"Good-Condition Classrooms (%)",
            "facility_classrooms_needing_repair_pct":"Classrooms Needing Repair (%)",
            "functional_toilet_pct_raw":"Functional Toilet Coverage (%)",
            "ptr_students_per_teacher_raw":"Pupil-Teacher Ratio",
            "digital_devices_per_school_raw":"Digital Devices / School",
            "district_female_teacher_pct":"Female Teacher Share (%)",
            "school_count":"Number of Schools",
            "enrollment_reported_student_total":"Student Enrolment",
            "score_teacher_total_derived":"Total Teachers",
        }
        fi["label"] = fi["feature"].astype(str).map(FEAT_LBL).fillna(fi["feature"])
        fi = fi.sort_values("importance", ascending=True)
        fi["_top"] = fi["importance"] >= fi["importance"].nlargest(5).min()
        fig = px.bar(fi, x="importance", y="label", orientation="h", text="importance",
                     color="_top", color_discrete_map={True: ACCENT, False: TEXT_LO},
                     labels={"importance":"Feature Importance","label":""})
        fig.update_traces(texttemplate="%{text:.4f}", textposition="outside", cliponaxis=False, marker_line_width=0)
        fig.update_layout(showlegend=False, bargap=0.3)
        show(fig, max(380, 30*len(fi)+80), horizontal=True)
        st.caption("Accent bars = top 5. This predicts Shala Score (infrastructure index) -- not student dropout. No dropout data exists in UDISE+.")
        st.info("**Important:** These findings indicate statistical association, not causal relationships. No dropout data exists in UDISE+. This model predicts an infrastructure-quality composite score.")

# ===========================================================================
# PAGE: DISTRICT GROUPING
# ===========================================================================
elif page == "District Grouping":
    heading("District Risk Grouping",
            "K-Means clustering groups districts with similar educational conditions.")

    KM_DIR = ROOT / "reports/kmeans_grouping"
    km_assign  = load_csv(KM_DIR / "kmeans_cluster_assignments.csv")
    km_summary = load_csv(KM_DIR / "kmeans_cluster_summary.csv")
    km_elbow   = load_csv(KM_DIR / "kmeans_elbow_silhouette.csv")
    _km_meta = {}
    _km_meta_p = KM_DIR / "kmeans_metadata.json"
    if _km_meta_p.exists():
        import json as _json2
        try: _km_meta = _json2.loads(_km_meta_p.read_text(encoding="utf-8"))
        except Exception: pass

    if km_assign is None:
        st.info("K-Means outputs not found. Run `src/models/run_kmeans_district_grouping.py` to generate them.")
    else:
        _optimal_k = int(_km_meta.get("optimal_k", 2))
        _best_sil  = float(_km_meta.get("best_silhouette", 0))
        kk1,kk2,kk3,kk4 = st.columns(4, gap="medium")
        with kk1: metric_card("Optimal Clusters",    str(_optimal_k), "By silhouette score", ACCENT)
        with kk2: metric_card("Best Silhouette",     f"{_best_sil:.4f}", ">0.5=strong, >0.25=moderate", BLUE)
        with kk3:
            strong_n = len(km_assign[km_assign["cluster_label"]=="Strong Educational Conditions"]) if km_assign is not None else 0
            metric_card("Strong Conditions", str(strong_n), "Districts in top cluster", SUCCESS)
        with kk4:
            priority_n = len(km_assign[km_assign["cluster_label"]=="Priority Support Required"]) if km_assign is not None else 0
            metric_card("Priority Support", str(priority_n), "Districts needing most attention", DANGER)

        if km_elbow is not None:
            heading("Cluster count evaluation")
            km_elbow["k"] = numeric(km_elbow["k"]).astype(int)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=km_elbow["k"], y=numeric(km_elbow["inertia"]),
                                     mode="lines+markers", name="Inertia", line=dict(color=ACCENT,width=2.5), yaxis="y1"))
            fig.add_trace(go.Scatter(x=km_elbow["k"], y=numeric(km_elbow["silhouette"]),
                                     mode="lines+markers", name="Silhouette", line=dict(color=WARNING,width=2.5,dash="dot"), yaxis="y2"))
            fig.add_vline(x=_optimal_k, line_dash="dot", line_color=ACCENT,
                          annotation_text=f"Optimal k={_optimal_k}", annotation_font_color=ACCENT)
            fig.update_layout(xaxis_title="Number of Clusters (k)",
                              yaxis=dict(title="Inertia",color=ACCENT,side="left"),
                              yaxis2=dict(title="Silhouette",color=WARNING,overlaying="y",side="right"),
                              legend=dict(x=0.5,y=1.1,orientation="h"))
            show(fig, 320)

        if km_summary is not None:
            st.divider()
            heading("Cluster profiles")
            CDISP = {"descriptive_label":"Cluster","district_count":"Districts","mean_shala_score":"Mean Score",
                     "ptr_students_per_teacher_raw":"PTR","functional_toilet_pct_raw":"Toilet %",
                     "good_classroom_pct_raw":"Good Classroom %","digital_devices_per_school_raw":"Devices/School"}
            km_disp = km_summary.rename(columns=CDISP)
            show_cols = [c for c in CDISP.values() if c in km_disp.columns]
            st.dataframe(km_disp[show_cols].reset_index(drop=True), hide_index=True)

        if km_assign is not None:
            st.divider()
            heading("District cluster membership")
            CMAP = {"Strong Educational Conditions":SUCCESS,"Priority Support Required":DANGER,
                    "Moderate Educational Conditions":WARNING,"Above Average Conditions":ACCENT}
            for lbl, grp in km_assign.sort_values(["cluster_label","district"]).groupby("cluster_label"):
                acc = CMAP.get(str(lbl), INFO)
                st.html(f'<div class="insight-card" style="--accent:{acc}">'
                        f'<div class="insight-title">{escape(str(lbl))} ({len(grp)} districts)</div>'
                        f'<div class="insight-text">{escape(", ".join(sorted(grp["district"].astype(str).tolist())))}</div></div>')

        st.info("Cluster labels are assigned by ranked mean Shala Score after clustering -- descriptive categories, not official risk grades.")

# ===========================================================================
# PAGE: EDUCATIONAL AUDIT
# ===========================================================================
elif page == "Educational Audit":
    heading("Educational Audit",
            "District diagnostic: observed indicators vs state benchmarks. Not confirmed dropout causes.")

    RC_DIR  = ROOT / "reports/rootcause"
    rc_df   = load_csv(RC_DIR / "educational_rootcause_indicators.csv")
    bench_df= load_csv(RC_DIR / "rootcause_state_benchmarks.csv")

    if rc_df is None:
        st.info("Root-cause outputs not found. Run `src/models/build_rootcause_indicators.py` to generate them.")
    else:
        rc_df["value"]          = numeric(rc_df["value"])
        rc_df["state_mean"]     = numeric(rc_df["state_mean"])
        rc_df["delta_vs_state"] = numeric(rc_df["delta_vs_state"])

        heading("Maharashtra Education Overview", f"State-wide totals for {selected_year}.")
        ok1,ok2,ok3,ok4,ok5 = st.columns(5, gap="medium")
        with ok1: metric_card("Districts",    str(year_data["district"].nunique()), "Maharashtra", ACCENT)
        with ok2: metric_card("Avg Schools",  fmt(safe_mean(year_data,"school_count"),0),         "Per district", BLUE)
        _te2 = year_data["enrollment_reported_student_total"].sum() if "enrollment_reported_student_total" in year_data.columns else np.nan
        _tt2 = year_data["score_teacher_total_derived"].sum()       if "score_teacher_total_derived"       in year_data.columns else np.nan
        with ok3: metric_card("Total Enrolment", f"{_te2:,.0f}" if pd.notna(_te2) else "NA", f"{selected_year}", WARNING)
        with ok4: metric_card("Total Teachers",  f"{_tt2:,.0f}" if pd.notna(_tt2) else "NA", "M+F+T", SUCCESS)
        with ok5: metric_card("State PTR",       fmt(safe_mean(year_data,"ptr_students_per_teacher_raw"),1), "Students per teacher", AMBER)

        st.divider()
        heading("Districts with concerns by indicator and year")
        rc_concern = rc_df[rc_df["status"].isin(["CONCERN","CRITICAL"])].copy()
        hm_data = (rc_concern.groupby(["academic_year","indicator"])["district"].count().reset_index().rename(columns={"district":"count"}))
        if not hm_data.empty:
            hm_pivot = hm_data.pivot(index="indicator", columns="academic_year", values="count").fillna(0)
            yr_sorted = sorted(hm_pivot.columns, key=lambda x: int(str(x)[:4]) if re.match(r"^\d{4}", str(x)) else 0)
            hm_pivot = hm_pivot[yr_sorted]
            fig = px.imshow(hm_pivot, aspect="auto", text_auto=True,
                            color_continuous_scale=["#0A0F1E","#F97316","#F87171"])
            fig.update_xaxes(side="top")
            show(fig, 280)
            st.caption("Deeper colour = more districts flagged.")

        st.divider()
        heading("District diagnostic report card")
        audit_district = (
            st.selectbox("Choose district", districts, index=districts.index(district_choice) if district_choice in districts else 0, key="audit_ds")
            if is_all else district_choice
        )
        audit_rows = rc_df[(rc_df["district"].astype(str)==str(audit_district)) & (rc_df["academic_year"].astype(str)==str(selected_year))].copy()
        if audit_rows.empty:
            st.info(f"No diagnostic data for {audit_district} in {selected_year}.")
        else:
            SC = {"ADEQUATE":SUCCESS,"CONCERN":WARNING,"CRITICAL":DANGER,"DATA MISSING":TEXT_LO}
            n_crit = int((audit_rows["status"]=="CRITICAL").sum())
            n_conc = int((audit_rows["status"]=="CONCERN").sum())
            n_adq  = int((audit_rows["status"]=="ADEQUATE").sum())
            overall = "CRITICAL" if n_crit>0 else "CONCERN" if n_conc>0 else "ADEQUATE"
            bc = SC[overall]
            st.html(f'<div class="insight-card" style="--accent:{bc}">'
                    f'<div class="insight-title">{escape(audit_district)} {escape(selected_year)} -- OVERALL: {escape(overall)}</div>'
                    f'<div class="insight-text">{n_adq} adequate  {n_conc} concern  {n_crit} critical</div></div>')
            for _, irow in audit_rows.iterrows():
                acc     = SC.get(str(irow["status"]), TEXT_LO)
                val_str = f"{irow['value']:.2f} {irow['unit']}" if pd.notna(irow["value"]) else "Data not available"
                _sm     = irow["state_mean"]
                st.html(f'<div class="insight-card" style="--accent:{acc}">'
                        f'<div class="insight-title">{escape(str(irow["indicator"]))} -- {escape(str(irow["status"]))}</div>'
                        f'<div class="insight-text"><b>{escape(val_str)}</b>'
                        + (f'<br>State mean: {_sm:.2f} {irow["unit"]}' if pd.notna(_sm) else "")
                        + f'<br><span style="color:{TEXT_LO}">{escape(str(irow["explanation"]))}</span></div></div>')

        if bench_df is not None:
            st.divider()
            heading("State benchmark reference")
            for c in ["state_mean","state_median","state_p10","state_p90"]:
                if c in bench_df.columns: bench_df[c] = numeric(bench_df[c]).round(3)
            st.dataframe(bench_df.drop(columns=["column"],errors="ignore"), hide_index=True)

        st.info("These diagnostics flag potential infrastructure and staffing concerns. They are not predictions of student dropout. Thresholds are project-defined.")

# ===========================================================================
# PAGE: REGION COMPARISON
# ===========================================================================
elif page == "Region Comparison":
    heading("Region Comparison",
            "Konkan, Western Maharashtra, Marathwada, Vidarbha -- scores, trends, risk tiers, pillars.")

    _reg_df = historical_v2 if historical_v2 is not None else historical
    if "region" not in _reg_df.columns:
        _RMAP = {
            "MUMBAI II":"Konkan","MUMBAI (SUBURBAN)":"Konkan","THANE":"Konkan","PALGHAR":"Konkan",
            "RAIGAD":"Konkan","RATNAGIRI":"Konkan","SINDHUDURG":"Konkan",
            "PUNE":"Western Maharashtra","NASHIK":"Western Maharashtra","AHILYANAGAR":"Western Maharashtra",
            "SOLAPUR":"Western Maharashtra","SATARA":"Western Maharashtra","SANGLI":"Western Maharashtra",
            "KOLHAPUR":"Western Maharashtra","DHULE":"Western Maharashtra","JALGAON":"Western Maharashtra",
            "NANDURBAR":"Western Maharashtra",
            "CHHATRAPATI SAMBHAJINAGAR":"Marathwada","JALNA":"Marathwada","BEED":"Marathwada",
            "LATUR":"Marathwada","DHARASHIV":"Marathwada","NANDED":"Marathwada",
            "HINGOLI":"Marathwada","PARBHANI":"Marathwada",
            "NAGPUR":"Vidarbha","WARDHA":"Vidarbha","YAVATMAL":"Vidarbha","AMRAVATI":"Vidarbha",
            "AKOLA":"Vidarbha","WASHIM":"Vidarbha","BULDHANA":"Vidarbha","CHANDRAPUR":"Vidarbha",
            "GADCHIROLI":"Vidarbha","GONDIA":"Vidarbha","BHANDARA":"Vidarbha",
        }
        _reg_df = _reg_df.copy()
        _reg_df["region"] = _reg_df["district"].astype(str).str.upper().map(_RMAP).fillna("Other")

    _reg_yr    = _reg_df[_reg_df["academic_year"] == selected_year].copy()
    _score_col = "shala_score_v2" if "shala_score_v2" in _reg_yr.columns else "shala_score_v1"
    _slabel    = "Shala Score v2"  if _score_col == "shala_score_v2"       else "Shala Score v1"

    REGIONS    = ["Konkan","Western Maharashtra","Marathwada","Vidarbha"]
    RCOLS      = {
        "Konkan":              ACCENT,
        "Western Maharashtra": BLUE,
        "Marathwada":          WARNING,
        "Vidarbha":            DANGER,
    }

    # KPI strip
    _rk = st.columns(4, gap="medium")
    for i, reg in enumerate(REGIONS):
        with _rk[i]:
            _sub = _reg_yr[_reg_yr["region"] == reg]
            metric_card(reg, fmt(safe_mean(_sub, _score_col), 1),
                        f"{int(_sub['district'].nunique())} districts  {_slabel}", RCOLS[reg])

    st.divider()
    heading(f"Average {_slabel} by region", selected_year)
    _rm = (_reg_yr[_reg_yr["region"].isin(REGIONS)].groupby("region")[_score_col].mean()
           .reset_index().rename(columns={_score_col:"mean_score"}))
    if not _rm.empty:
        fig = px.bar(_rm.sort_values("mean_score", ascending=True), x="mean_score", y="region",
                     orientation="h", text="mean_score", color="region", color_discrete_map=RCOLS,
                     labels={"mean_score":_slabel,"region":"Region"})
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False, marker_line_width=0)
        _sv = safe_mean(_reg_yr, _score_col)
        if pd.notna(_sv): fig.add_vline(x=float(_sv), line_dash="dot", line_color=TEXT_LO,
                                         annotation_text=f"State avg {_sv:.1f}", annotation_font_color=TEXT_LO)
        fig.update_layout(showlegend=False, bargap=0.4, xaxis_range=[0, max(100, float(_rm["mean_score"].max())*1.15)])
        show(fig, 300, horizontal=True)

    st.divider()
    heading(f"{_slabel} trend by region", "Annual average across all available years.")
    _rt = (_reg_df[_reg_df["region"].isin(REGIONS)].groupby(["academic_year","region"])[_score_col].mean().reset_index())
    _rt["_yr"] = _rt["academic_year"].str[:4].astype(int)
    _rt = _rt.sort_values("_yr")
    if not _rt.empty:
        fig = px.line(_rt, x="academic_year", y=_score_col, color="region", color_discrete_map=RCOLS,
                      markers=True, labels={_score_col:_slabel,"academic_year":"Academic Year","region":"Region"})
        fig.update_traces(line_width=2.5, marker_size=8)
        fig.update_xaxes(categoryorder="array", categoryarray=sorted(_rt["academic_year"].unique(), key=lambda x: int(str(x)[:4])))
        show(fig, 360, horizontal=True)

    st.divider()
    heading("District scores within each region", f"{selected_year}")
    _rc2 = st.columns(2, gap="large")
    for i, reg in enumerate(REGIONS):
        with _rc2[i%2]:
            _sub = _reg_yr[_reg_yr["region"]==reg][["district",_score_col]].copy()
            _sub["district"] = _sub["district"].astype(str)
            _sub[_score_col] = numeric(_sub[_score_col])
            _sub = _sub.dropna(subset=[_score_col]).sort_values(_score_col, ascending=True)
            if _sub.empty: st.info(f"No data for {reg}."); continue
            _acc = RCOLS[reg]
            fig = px.bar(_sub, x=_score_col, y="district", orientation="h", text=_score_col,
                         color_discrete_sequence=[_acc], labels={_score_col:_slabel,"district":""})
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False, marker_line_width=0)
            fig.update_layout(title=dict(text=reg,font=dict(size=13,color=_acc)),
                              showlegend=False, bargap=0.3, xaxis_range=[0, max(100, float(_sub[_score_col].max())*1.15)],
                              margin=dict(l=10,r=10,t=36,b=10))
            show(fig, max(260, 28*len(_sub)+60), horizontal=True)

    if "risk_tier_v2" in _reg_yr.columns:
        st.divider()
        heading("Risk tier distribution by region")
        _tr = (_reg_yr[_reg_yr["region"].isin(REGIONS)]
               .groupby(["region","risk_tier_v2"])["district"].count().reset_index().rename(columns={"district":"count"}))
        fig = px.bar(_tr, x="region", y="count", color="risk_tier_v2", barmode="stack",
                     color_discrete_map={"Thriving":SUCCESS,"Stable":BLUE,"At-Risk":WARNING,"Critical":DANGER},
                     category_orders={"risk_tier_v2":["Thriving","Stable","At-Risk","Critical"]},
                     labels={"count":"Districts","region":"Region","risk_tier_v2":"Risk Tier"})
        fig.update_layout(bargap=0.3)
        show(fig, 320)
        st.caption("Risk tiers from Shala Score v2 quartile bands (72 each). Not official classifications.")

    _PCOLS = {"pillar2_teacher_ptr":"Teacher PTR","pillar2_infrastructure":"Infrastructure",
              "pillar2_participation":"Participation","pillar2_digital":"Digital"}
    _avp = {k:v for k,v in _PCOLS.items() if k in _reg_yr.columns}
    if _avp:
        st.divider()
        heading("Pillar scores by region")
        _pr = (_reg_yr[_reg_yr["region"].isin(REGIONS)].groupby("region")[list(_avp)].mean()
               .rename(columns=_avp).reindex([r for r in REGIONS if r in _reg_yr["region"].unique()]))
        if not _pr.empty:
            fig = px.imshow(_pr.T, aspect="auto", text_auto=".1f", zmin=0, zmax=100,
                            color_continuous_scale=["#0A0F1E","#1E2D45","#0EA5E9","#38BDF8","#7DD3FC"],
                            labels=dict(x="Region",y="Pillar",color="Score"))
            fig.update_xaxes(side="top")
            show(fig, 280)

    st.info("Konkan=7 districts, Western Maharashtra=10, Marathwada=8, Vidarbha=11. Source: UDISE+ extract.")

# ===========================================================================
# FOOTER
# ===========================================================================
st.divider()
st.html(
    '<div style="text-align:center;padding:14px;color:#64748B;font-size:12px;line-height:2">'
    '<b style="color:#38BDF8;letter-spacing:1px">SHALASCOPE MAHARASHTRA</b><br>'
    'District-Level Education Intelligence &amp; Predictive Analytics<br>'
    '<span style="color:#1E2D45">Real UDISE+ Data Only  |  No Synthetic Values  |  No Source Mutation</span>'
    '</div>'
)

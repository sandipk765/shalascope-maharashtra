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
# COSMIC NEBULA DARK GLASS PALETTE
# ---------------------------------------------------------------------------
# Surfaces
OBS_BG      = "#0B0B1A"   # page background  -- deep space
OBS_SURFACE = "#0F0F24"   # card surface      -- dark nebula
OBS_RAISED  = "#151530"   # raised card       -- glass layer
OBS_BORDER  = "#2A2A4A"   # border            -- subtle separation
OBS_HOVER   = "#1E1E3A"   # hover state

# Accent
ACCENT      = "#C084FC"   # violet-purple primary
ACCENT_DARK = "#A855F7"   # deeper violet

# Status colours
SUCCESS     = "#34D399"   # emerald green
WARNING     = "#FBBF24"   # amber
DANGER      = "#F87171"   # rose red
INFO        = "#7DD3FC"   # sky blue

# Text
TEXT_HI     = "#E9E4FF"   # headings     -- soft lavender white
TEXT_MED    = "#C4BAF0"   # body         -- muted lavender
TEXT_LO     = "#6B6A9A"   # captions     -- dim purple-grey

# Chart grid
GRID        = "rgba(192,132,252,0.06)"
BORDER      = OBS_BORDER

# Legacy aliases kept for helper functions
TEAL_DARK   = ACCENT_DARK
TEAL        = ACCENT
AMBER       = WARNING
CRIMSON     = DANGER
VIOLET      = INFO
SLATE_MID   = "#3A3A6A"
SLATE_SOFT  = TEXT_LO
SAFFRON     = ACCENT
GOLD        = WARNING
GREEN       = SUCCESS
CORAL       = DANGER
BLUE        = "#7DD3FC"
TERRA       = "#FB923C"
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
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg:         #0B0B1A;
  --surface:    #0F0F24;
  --raised:     #151530;
  --border:     #2A2A4A;
  --hover:      #1E1E3A;
  --accent:     #C084FC;
  --accent-d:   #A855F7;
  --accent-glow:rgba(192,132,252,0.18);
  --sky:        #7DD3FC;
  --success:    #34D399;
  --warn:       #FBBF24;
  --danger:     #F87171;
  --hi:         #E9E4FF;
  --med:        #C4BAF0;
  --lo:         #6B6A9A;
  --shadow:     0 2px 16px rgba(11,11,26,.70);
  --shadow-lg:  0 4px 32px rgba(11,11,26,.85);
  --glow:       0 0 24px rgba(192,132,252,.22);
  --radius:     12px;
  --radius-sm:  8px;
  --fs-title:   22px;
  --fs-sec:     15px;
  --fs-body:    13px;
  --fs-cap:     11.5px;
  --fs-label:   9.5px;
}

/* ── App shell ── */
html, body, [class*="css"] {
  font-family: 'Outfit', 'Segoe UI', system-ui, sans-serif;
  font-feature-settings: "tnum";
}
.stApp { background: var(--bg); color: var(--hi); }
.block-container, [data-testid="stMainBlockContainer"] {
  padding-top: 1.4rem !important;
  max-width: 1560px;
  padding-bottom: 3rem;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: #0F0F24 !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"], [data-testid="stSidebar"] * { color: var(--med) !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] strong { color: var(--hi) !important; }

/* ── Sidebar nav rail ── */
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.stButton) {
  margin-top: 0 !important; margin-bottom: 0 !important;
  padding-top: 0 !important; padding-bottom: 0 !important;
}
[data-testid="stSidebar"] .stButton { margin: 0 !important; padding: 0 !important; }

[data-testid="stSidebar"] .stButton > button {
  display: flex !important; align-items: center !important;
  justify-content: flex-start !important; width: 100% !important;
  box-sizing: border-box !important; padding: 7px 10px 7px 14px !important;
  border-radius: var(--radius-sm) !important; border: none !important;
  border-left: 3px solid transparent !important; background: transparent !important;
  color: var(--lo) !important; font-size: 12px !important; font-weight: 500 !important;
  font-family: 'Outfit', sans-serif !important; line-height: 1.25 !important;
  white-space: nowrap !important; overflow: hidden !important;
  text-overflow: ellipsis !important; cursor: pointer !important;
  min-height: 32px !important; max-height: 34px !important;
  letter-spacing: .2px !important; text-align: left !important;
  transition: background .10s ease, color .10s ease, border-color .10s ease !important;
}
[data-testid="stSidebar"] .stButton > button > div {
  display: flex !important; align-items: center !important;
  justify-content: flex-start !important; width: 100% !important;
  text-align: left !important; overflow: hidden !important;
}
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span {
  margin: 0 !important; text-align: left !important; white-space: nowrap !important;
  overflow: hidden !important; text-overflow: ellipsis !important;
  font-size: 12px !important; font-weight: inherit !important;
  color: inherit !important; line-height: 1.25 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--accent-glow) !important;
  color: var(--accent) !important;
  border-left-color: rgba(192,132,252,.40) !important;
}
[data-testid="stSidebar"] .stButton > button:hover p,
[data-testid="stSidebar"] .stButton > button:hover span { color: var(--accent) !important; }
[data-testid="stSidebar"] .stButton > button:focus,
[data-testid="stSidebar"] .stButton > button:focus-visible {
  box-shadow: none !important; outline: none !important;
}

/* ── Sidebar selectbox & filter labels ── */
[data-testid="stSidebar"] .obs-filter-label {
  font-size: 9px; letter-spacing: 2px; font-weight: 700;
  color: var(--accent); text-transform: uppercase;
  padding: 8px 0 4px; display: block; font-family: 'Outfit', sans-serif;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
  color: var(--med) !important; font-weight: 600 !important; font-size: 12px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: var(--hover) !important; border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important; color: var(--hi) !important; font-size: 12.5px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] [data-testid="stSelectboxValue"],
[data-testid="stSidebar"] [data-baseweb="select"] > div > div > div {
  color: var(--hi) !important; font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] input { color: var(--hi) !important; }
[data-testid="stSidebar"] [data-baseweb="select"] svg { fill: var(--accent) !important; }
[data-testid="stSidebar"] [data-baseweb="option"] {
  background: var(--surface) !important; color: var(--med) !important; font-size: 12.5px !important;
}
[data-testid="stSidebar"] [data-baseweb="option"]:hover {
  background: var(--accent-glow) !important; color: var(--accent) !important;
}
[data-testid="stSidebar"] [data-baseweb="option"][aria-selected="true"] {
  background: rgba(192,132,252,.15) !important; color: var(--accent) !important; font-weight: 700 !important;
}
[data-testid="stSidebar"] .obs-sidebar-footer {
  font-size: 10px; color: var(--lo); padding: 10px 4px 2px; line-height: 1.6;
}

/* ── Type ── */
h1, h2, h3, h4 { color: var(--hi) !important; font-weight: 700; letter-spacing: -.3px; }
p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color: var(--med); }
[data-testid="stCaptionContainer"] { font-size: var(--fs-cap); color: var(--lo) !important; }
footer { visibility: hidden; }
hr { border-color: var(--border); margin: 14px 0; }
[data-testid="stHeader"] { background: transparent !important; border-bottom: none !important; }

/* ── Top app header ── */
.obs-header {
  background: linear-gradient(135deg, #0B0B1A 0%, #12103A 100%);
  border-bottom: 1px solid var(--border);
  padding: 8px 28px;
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 10px;
}
.obs-eyebrow {
  font-size: 9px; letter-spacing: 2.5px; font-weight: 700;
  color: var(--accent); text-transform: uppercase;
}
.obs-badge {
  display: inline-flex; align-items: center; gap: 5px;
  background: rgba(192,132,252,.10); border: 1px solid rgba(192,132,252,.25);
  color: var(--accent); border-radius: 6px; padding: 3px 10px;
  font-size: 10px; font-weight: 700; letter-spacing: .3px;
}

/* ── Section headings ── */
.section-heading, .sd-section-head {
  font-size: var(--fs-sec); font-weight: 700; color: var(--hi);
  margin: 18px 0 6px; padding-left: 10px;
  border-left: 3px solid var(--accent);
}
.section-sub, .sd-section-sub {
  font-size: var(--fs-body); color: var(--lo); margin: 0 0 14px 13px; line-height: 1.55;
}

/* ── Metric / KPI cards ── */
.metric-card, .sd-kpi {
  background: var(--raised); border: 1px solid var(--border);
  border-top: 2px solid var(--border);
  border-radius: var(--radius);
  /* Right padding clears the 34px icon badge (right:11px) + 9px breathing room */
  padding: 14px 54px 14px 16px;
  min-height: 100px;
  box-shadow: var(--shadow); margin-bottom: 8px;
  display: flex; flex-direction: column;
  transition: box-shadow .15s ease;
  box-sizing: border-box;
}
.metric-card:hover { box-shadow: var(--glow); }
.metric-label, .sd-kpi-label {
  font-size: var(--fs-label); letter-spacing: 1.2px; font-weight: 700;
  color: var(--lo); text-transform: uppercase;
  /* Single line — ellipsis on overflow so tall-label cards don't stretch */
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  line-height: 1.3;
}
.metric-value, .sd-kpi-value {
  font-size: 20px; font-weight: 700; color: var(--hi);
  margin-top: 5px; line-height: 1.2;
  font-variant-numeric: tabular-nums;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.metric-caption, .sd-kpi-caption {
  font-size: var(--fs-cap); color: var(--lo); margin-top: 4px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* ── Insight / info cards ── */
.insight-card, .sd-card {
  background: var(--raised); border: 1px solid var(--border);
  border-left: 4px solid var(--accent,var(--accent));
  border-radius: var(--radius-sm); padding: 10px 14px; margin-bottom: 7px;
  box-shadow: var(--shadow);
}
.insight-title, .sd-card-title {
  font-size: var(--fs-label); letter-spacing: 1px; font-weight: 700;
  color: var(--accent,var(--accent)); text-transform: uppercase;
}
.insight-text, .sd-card-body {
  font-size: var(--fs-body); color: var(--med); margin-top: 4px;
  line-height: 1.55; font-variant-numeric: tabular-nums;
}

/* ── Badges ── */
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 10px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase;
}
.badge-pass    { background: rgba(52,211,153,.15); color: #34D399; }
.badge-concern { background: rgba(251,191,36,.15);  color: #FBBF24; }
.badge-critical{ background: rgba(248,113,113,.15); color: #F87171; }
.badge-info    { background: rgba(125,211,252,.15); color: #7DD3FC; }

/* ── Step flow labels ── */
.step-flow { display: flex; align-items: center; gap: 9px; margin-bottom: 10px; }
.step-flow-num {
  width: 22px; height: 22px; border-radius: 6px;
  background: var(--accent-glow); color: var(--accent);
  border: 1px solid rgba(192,132,252,.35);
  font-size: var(--fs-cap); font-weight: 800;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.step-flow-label { font-size: 12px; font-weight: 700; color: var(--hi); }

/* ── Score gauge ── */
.score-gauge-wrap {
  background: var(--raised); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 14px 16px; box-shadow: var(--shadow); margin-bottom: 8px;
}
.score-gauge-label {
  font-size: var(--fs-label); letter-spacing: 1px; font-weight: 700;
  color: var(--lo); text-transform: uppercase; margin-bottom: 6px;
}
.score-gauge-row { display: flex; align-items: baseline; gap: 4px; margin-bottom: 8px; }
.score-gauge-value {
  font-size: var(--fs-title); font-weight: 700; color: var(--accent,var(--accent));
  font-variant-numeric: tabular-nums; line-height: 1;
}
.score-gauge-denom { font-size: var(--fs-body); color: var(--lo); }
.score-gauge-bar-bg {
  position: relative; background: rgba(42,42,74,.8);
  border-radius: 999px; height: 10px; overflow: visible;
}
.score-gauge-bar-fill {
  height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, var(--accent-d), var(--accent));
}
.score-gauge-avg {
  position: absolute; top: -3px; width: 2px; height: 16px;
  background: var(--hi); border-radius: 1px;
}
.score-gauge-avg-label {
  position: absolute; top: 14px; font-size: var(--fs-cap);
  color: var(--lo); white-space: nowrap; transform: translateX(-50%);
}
.score-gauge-caption { margin-top: 6px; font-size: var(--fs-cap); color: var(--lo); }

/* ── Ratio bar ── */
.ratio-bar-wrap {
  background: var(--raised); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 12px 14px; margin-bottom: 7px; box-shadow: var(--shadow);
}
.ratio-bar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.ratio-bar-label { font-size: var(--fs-label); letter-spacing: 1px; font-weight: 700; color: var(--lo); text-transform: uppercase; }
.ratio-bar-chip { font-size: 9px; padding: 1px 7px; border-radius: 4px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; }
.ratio-bar-value-row { display: flex; align-items: baseline; gap: 3px; margin-bottom: 6px; }
.ratio-bar-value { font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--accent,var(--accent)); }
.ratio-bar-unit { font-size: var(--fs-cap); color: var(--lo); }
.ratio-bar-track { position: relative; background: rgba(42,42,74,.8); border-radius: 999px; height: 8px; }
.ratio-bar-fill { height: 100%; border-radius: 999px; }
.ratio-bar-threshold { position: absolute; top: -3px; width: 2px; height: 14px; background: var(--hi); border-radius: 1px; }
.ratio-bar-threshold-label { position: absolute; top: 12px; font-size: 10px; color: var(--lo); white-space: nowrap; transform: translateX(-50%); }
.ratio-bar-state { margin-top: 5px; font-size: var(--fs-cap); color: var(--lo); }

/* ── Result card ── */
.result-card, .sd-result {
  background: var(--raised); border: 1px solid var(--border);
  border-left: 4px solid var(--accent,var(--accent));
  border-radius: var(--radius); padding: 14px 17px; min-height: 110px; box-shadow: var(--shadow);
}
.result-label { font-size: var(--fs-label); font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: var(--lo); }
.result-value { font-size: 26px; font-weight: 700; color: var(--accent,var(--accent)); margin-top: 7px; font-variant-numeric: tabular-nums; }
.result-note  { font-size: 11.5px; color: var(--lo); margin-top: 6px; line-height: 1.5; }

/* ── Prediction banner ── */
.prediction-banner, .sd-banner {
  background: linear-gradient(135deg, var(--raised) 0%, rgba(192,132,252,.06) 100%);
  border: 1px solid var(--border); border-left: 5px solid var(--accent,var(--accent));
  border-radius: var(--radius); padding: 14px 18px; margin: 5px 0 12px; box-shadow: var(--shadow);
}
.prediction-banner .kicker { font-size: 9px; letter-spacing: 1.5px; font-weight: 700; color: var(--accent,var(--accent)); text-transform: uppercase; }
.prediction-banner .title  { font-size: 18px; font-weight: 700; color: var(--hi); margin-top: 3px; line-height: 1.3; }
.prediction-banner .desc   { font-size: 12px; color: var(--lo); margin-top: 4px; }

/* ── Root-cause cards ── */
.rc-card {
  background: var(--raised); border: 1px solid var(--border);
  border-left: 4px solid var(--accent,var(--accent));
  border-radius: var(--radius-sm); padding: 10px 13px; margin-bottom: 6px; box-shadow: var(--shadow);
}
.rc-title  { font-size: 9px; letter-spacing: 1px; font-weight: 700; color: var(--accent,var(--accent)); text-transform: uppercase; display: flex; align-items: center; justify-content: space-between; }
.rc-value  { font-size: 17px; font-weight: 700; color: var(--accent,var(--accent)); font-variant-numeric: tabular-nums; margin-top: 3px; line-height: 1.2; }
.rc-state  { font-size: var(--fs-cap); color: var(--lo); font-variant-numeric: tabular-nums; }
.rc-explain{ font-size: var(--fs-body); color: var(--med); margin-top: 5px; line-height: 1.5; border-top: 1px solid var(--border); padding-top: 5px; }

/* ── Step cards ── */
.step {
  display: flex; gap: 11px; align-items: flex-start;
  background: var(--raised); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 11px 14px; margin-bottom: 7px; box-shadow: var(--shadow);
}
.step-no {
  min-width: 26px; height: 26px; border-radius: 7px;
  background: rgba(192,132,252,.12); color: var(--accent);
  border: 1px solid rgba(192,132,252,.30);
  font-weight: 800; display: flex; align-items: center; justify-content: center; font-size: 12px; flex-shrink: 0;
}
.step-body { color: var(--med); font-size: 12.5px; line-height: 1.6; }
.step-body b { color: var(--accent); }

/* ── District headline ── */
.dist-headline {
  background: linear-gradient(135deg, var(--raised) 0%, rgba(192,132,252,.08) 100%);
  border-radius: var(--radius); padding: 14px 18px 12px; margin-bottom: 14px;
  border: 1px solid var(--border);
}
.dist-headline .dh-eyebrow { font-size: 9px; letter-spacing: 2px; font-weight: 700; color: var(--accent); text-transform: uppercase; margin-bottom: 3px; }
.dist-headline .dh-name    { font-size: 22px; font-weight: 700; color: var(--hi); letter-spacing: -.4px; line-height: 1.2; }
.dist-headline .dh-sub     { font-size: 11.5px; color: var(--lo); margin-top: 4px; }

/* ── Right panel sticky ── */
.right-panel-sticky {
  position: sticky; top: 4rem; max-height: calc(100vh - 5rem); overflow-y: auto; padding-right: 4px;
}
.right-panel-sticky::-webkit-scrollbar { width: 4px; }
.right-panel-sticky::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

/* ── Streamlit native overrides ── */
[data-testid="stMetric"] { background: var(--raised); border: 1px solid var(--border); border-radius: var(--radius); padding: 11px 13px; }
[data-testid="stMetricLabel"] { color: var(--lo) !important; }
[data-testid="stMetricValue"] { color: var(--accent) !important; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; background: var(--raised); }
[data-testid="stPlotlyChart"] { background: var(--raised); border: 1px solid var(--border); border-radius: var(--radius); padding: 5px 7px 1px; box-shadow: var(--shadow); overflow: hidden; margin-top: 4px; }
[data-baseweb="menu"] *         { color: var(--hi) !important; background: var(--surface) !important; }
[data-baseweb="popover"]        { background: var(--surface) !important; }
[data-baseweb="select"] > div, [data-baseweb="input"] > div { background: var(--hover) !important; border: 1px solid var(--border) !important; color: var(--hi) !important; border-radius: var(--radius-sm) !important; }
[data-baseweb="select"] input   { color: var(--hi) !important; }
[data-baseweb="select"] svg     { fill: var(--accent) !important; }
[data-testid="stForm"] { background: var(--raised); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px; box-shadow: var(--shadow); }
[data-testid="stAlert"] { background: rgba(192,132,252,.08); border: 1px solid rgba(192,132,252,.20); color: var(--accent); border-radius: var(--radius-sm); }
.stButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: var(--radius-sm) !important; border: 1px solid var(--accent) !important;
  background: var(--accent) !important; color: #0B0B1A !important;
  font-weight: 700 !important; min-height: 38px !important; font-family: 'Outfit', sans-serif !important;
}
.stButton > button:hover { background: var(--accent-d) !important; border-color: var(--accent-d) !important; }
.stSlider [data-baseweb="slider"] div[role="slider"] { background: var(--accent) !important; border-color: var(--accent) !important; }
[data-testid="stExpander"] { background: var(--raised); border: 1px solid var(--border); border-radius: var(--radius); }
[data-testid="stTabs"] [role="tablist"] { border-bottom: 1px solid var(--border) !important; }
[data-testid="stTabs"] button[role="tab"] { color: var(--lo) !important; font-family: 'Outfit', sans-serif !important; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color: var(--accent) !important; border-bottom: 2px solid var(--accent) !important; }

@media(max-width:700px) {
  .block-container { padding-left: .75rem !important; padding-right: .75rem !important; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Icon structural CSS only — no external font dependency
st.html(
    '<style>'
    '.kpi-icon{'
    'position:absolute;top:50%;right:12px;'
    'transform:translateY(-50%);'
    'width:34px;height:34px;border-radius:10px;'
    'display:flex;align-items:center;justify-content:center;'
    'flex-shrink:0;line-height:1;}'
    '.metric-card{position:relative;overflow:hidden;}'
    '.brand-icon{display:inline-flex;align-items:center;'
    'filter:drop-shadow(0 0 5px rgba(125,211,252,.50));'
    'margin-right:8px;vertical-align:-5px;flex-shrink:0;}'
    '</style>'
)

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


# ---------------------------------------------------------------------------
# Inline SVG icon library — 18×18 render, 24-unit viewBox, explicit stroke
# No currentColor — explicit hex so icons show regardless of CSS inheritance
# ---------------------------------------------------------------------------
def _svg(paths: str, colour: str, w: int = 18, vb: str = "0 0 24 24") -> str:
    """Return a self-contained inline SVG string."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{w}" '
        f'viewBox="{vb}" fill="none" stroke="{colour}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
    )

_KPI_SVG = {
    "bi-geo-alt": lambda c: _svg(
        '<path d="M12 2a7 7 0 0 1 7 7c0 5-7 13-7 13S5 14 5 9a7 7 0 0 1 7-7z"/>'
        '<circle cx="12" cy="9" r="2.5"/>',
        c),
    "bi-building": lambda c: _svg(
        '<rect x="3" y="3" width="18" height="18" rx="1"/>'
        '<path d="M9 3v18M15 3v18M3 9h18M3 15h18"/>',
        c),
    "bi-people": lambda c: _svg(
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
        '<path d="M21 21v-2a4 4 0 0 0-3-3.87"/>',
        c),
    "bi-person-badge": lambda c: _svg(
        '<circle cx="12" cy="8" r="4"/>'
        '<rect x="8" y="2" width="8" height="5" rx="1"/>'
        '<path d="M4 20v-1a8 8 0 0 1 16 0v1"/>',
        c),
    "bi-graph-up-arrow": lambda c: _svg(
        '<polyline points="2,18 8,12 13,15 20,6"/>'
        '<polyline points="16,6 20,6 20,10"/>',
        c),
    "bi-award": lambda c: _svg(
        '<circle cx="12" cy="9" r="6"/>'
        '<path d="M8.56 15.37 7 22l5-3 5 3-1.56-6.63"/>',
        c),
    "bi-shield-exclamation": lambda c: _svg(
        '<path d="M12 2 3 6v6c0 5 3.6 8.5 9 10 5.4-1.5 9-5 9-10V6z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/>'
        '<circle cx="12" cy="16.5" r=".8" fill="' + c + '" stroke="none"/>',
        c),
}

_BRAND_SVG = _svg(
    '<path d="M3 22h18M3 12h18M12 2 2 12h20L12 2z"/>'
    '<rect x="7" y="12" width="3" height="10"/>'
    '<rect x="10.5" y="12" width="3" height="10"/>'
    '<rect x="14" y="12" width="3" height="10"/>',
    "#7DD3FC", w=22,
)


def metric_card(label, value, caption="", accent=None, icon=""):
    if accent is None:
        accent = ACCENT
    if icon and icon in _KPI_SVG:
        svg_str = _KPI_SVG[icon](accent)
        icon_html = (
            f'<div class="kpi-icon" style="background:{accent}1A">'
            f'{svg_str}</div>'
        )
    else:
        icon_html = ""
    # st.markdown renders into the main DOM; st.html renders into a sandboxed
    # iframe where CSS variables and currentColor do not inherit correctly.
    st.markdown(
        f'<div class="metric-card" style="--accent:{accent}">'
        f'{icon_html}'
        f'<div class="metric-label">{escape(str(label))}</div>'
        f'<div class="metric-value">{escape(str(value))}</div>'
        f'<div class="metric-caption">{escape(str(caption))}</div></div>',
        unsafe_allow_html=True,
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
        font=dict(family="'Outfit',sans-serif", color=TEXT_MED, size=12),
        margin=dict(l=36, r=36, t=40, b=44),
        hoverlabel=dict(bgcolor="#12103A", bordercolor="#2A2A4A",
                        font_size=12, font_color="#E9E4FF"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(color=TEXT_MED, size=11), bgcolor="rgba(0,0,0,0)", title_text=""),
    )
    fig.update_xaxes(
        showgrid=horizontal, gridcolor="rgba(42,42,74,.8)", showline=True,
        linecolor=OBS_BORDER, linewidth=1,
        tickfont=dict(color=TEXT_LO, size=11),
        title_font=dict(color=TEXT_LO, size=12),
        automargin=True, zeroline=False,
    )
    fig.update_yaxes(
        showgrid=not horizontal, gridcolor="rgba(42,42,74,.8)", zeroline=False,
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
# ---------------------------------------------------------------------------
# SIDEBAR  -- reference-image faithful nav + filters
# ---------------------------------------------------------------------------
with st.sidebar:

    # Brand header
    st.markdown(
        '<div style="padding:18px 6px 12px 6px">'
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
        '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"'
        ' fill="none" stroke="#7DD3FC" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 22h18M3 12h18M12 2 2 12h20L12 2z"/>'
        '<rect x="7" y="12" width="3" height="10"/>'
        '<rect x="10.5" y="12" width="3" height="10"/>'
        '<rect x="14" y="12" width="3" height="10"/>'
        '</svg>'
        '<span style="font-size:21px;font-weight:800;color:#C084FC;letter-spacing:-.5px;line-height:1">'
        'ShalaScope</span>'
        '</div>'
        '<div style="font-size:8.5px;letter-spacing:3px;font-weight:700;color:#6B6A9A;'
        'text-transform:uppercase;padding-left:30px">Maharashtra Education</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.html('<div style="height:1px;background:linear-gradient(90deg,#C084FC,transparent);margin:0 0 10px"></div>')

    # Navigation
    st.html('<span style="font-size:9px;letter-spacing:2px;font-weight:700;color:#C084FC;text-transform:uppercase;padding:6px 0 4px;display:block">Navigation</span>')

    NAV_LABELS = [
        "Overview",
        "School Infrastructure",
        "Enrollment Trends",
        "Teacher & Resource Analytics",
        "ML Risk & Dropout Predictor",
        "District Comparison",
    ]
    _PAGE_KEYS = {
        "Overview":                      "Overview",
        "School Infrastructure":         "School Infrastructure",
        "Enrollment Trends":             "Enrollment Trends",
        "Teacher & Resource Analytics":  "Teacher & Resource Analytics",
        "ML Risk & Dropout Predictor":   "ML Risk & Dropout Predictor",
        "District Comparison":           "District Comparison",
    }
    _VALID_PAGES = set(_PAGE_KEYS.values())

    if st.session_state.get("nav_page") not in _VALID_PAGES:
        st.session_state["nav_page"] = "Overview"

    _active_page = st.session_state["nav_page"]

    for _lbl in NAV_LABELS:
        if st.button(_lbl, key=f"nav_btn_{_lbl}"):
            st.session_state["nav_page"] = _PAGE_KEYS[_lbl]
            st.rerun()

    # Active button highlight
    _active_lbl = next((l for l,p in _PAGE_KEYS.items() if p == _active_page), "Overview")
    _sel = f'[data-testid="stSidebar"] button[aria-label="{_active_lbl}"]'
    st.html(
        f'<style>'
        f'{_sel}{{background:rgba(192,132,252,.14)!important;color:#C084FC!important;'
        f'font-weight:700!important;border-left:3px solid #C084FC!important;}}'
        f'{_sel} p,{_sel} span,{_sel} div{{color:#C084FC!important;font-weight:700!important;}}'
        f'</style>'
    )

    page = _active_page

    # Filters
    st.html('<div style="height:1px;background:#2A2A4A;margin:12px 0 4px"></div>')
    st.html('<span style="font-size:9px;letter-spacing:2px;font-weight:700;color:#C084FC;text-transform:uppercase;padding:4px 0;display:block">Filters</span>')

    districts_all = sorted(historical["district"].dropna().astype(str).unique().tolist())
    _yr_opts = sorted(
        historical["academic_year"].dropna().unique(),
        key=lambda x: int(str(x)[:4]) if re.match(r"^\d{4}", str(x)) else 0,
    )
    if not _yr_opts:
        st.error("No academic year records available.")
        st.stop()
    years = _yr_opts

    # Default to 2023-24 if available (matches reference image)
    _yr_default = years.index("2023-24") if "2023-24" in years else len(years) - 1
    selected_year   = st.selectbox("Academic Year", years, index=_yr_default, key="sb_year")
    _pune_def = ([ALL] + districts_all).index("PUNE") if "PUNE" in districts_all else 0
    district_choice = st.selectbox("District", [ALL] + districts_all, index=_pune_def, key="sb_district")
    is_all    = district_choice == ALL
    highlight = None if is_all else district_choice

    st.html(
        f'<div style="font-size:10px;color:#6B6A9A;padding:12px 0 2px;line-height:1.6">'
        f'{years[0]} &ndash; {years[-1]} &nbsp;|&nbsp; 36 districts</div>'
    )

# ---------------------------------------------------------------------------
# SHARED STATE
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

# Focus district for district-centric pages
focus_district = district_choice if not is_all else "PUNE"
# v2 data for the focus district
_v2 = historical_v2 if historical_v2 is not None else historical
_fd = _v2[_v2["district"] == focus_district].sort_values("_year_order") if "district" in _v2.columns else pd.DataFrame()
_fd_cur = _fd[_fd["academic_year"] == selected_year]
_fd_prev = _fd[_fd["academic_year"] == prev_year] if prev_year else pd.DataFrame()


def _get(df_row, col, default=np.nan):
    """Safe column getter from a single-row DataFrame."""
    if df_row.empty or col not in df_row.columns:
        return default
    v = df_row.iloc[0][col]
    return default if pd.isna(v) else v


def _yoy_str(cur, prv, fmt_fn=None, reverse=False):
    """Return a YoY delta string.  reverse=True means lower is better."""
    if pd.isna(cur) or pd.isna(prv) or prv == 0:
        return ""
    delta = cur - prv
    if fmt_fn:
        return f"{'+' if delta>=0 else ''}{fmt_fn(delta)}"
    return f"{'+' if delta>=0 else ''}{delta:,.0f} YoY"


# ---------------------------------------------------------------------------
# SHARED DISTRICT METRICS  (computed once — used by Overview, Teacher, ML pages)
# ---------------------------------------------------------------------------
_schools_cur  = _get(_fd_cur, "school_count")
_schools_prv  = _get(_fd_prev, "school_count")
_enrol_cur    = _get(_fd_cur, "enrollment_reported_student_total")
_enrol_prv    = _get(_fd_prev, "enrollment_reported_student_total")
_teach_cur    = _get(_fd_cur, "score_teacher_total_derived")
_teach_prv    = _get(_fd_prev, "score_teacher_total_derived")
_infra_cur    = _get(_fd_cur, "pillar_infrastructure")
_digital_cur  = _get(_fd_cur, "pillar_digital_readiness")
_digital_prv  = _get(_fd_prev, "pillar_digital_readiness")
_ptr_cur      = _get(_fd_cur, "ptr_students_per_teacher_raw")
_ptr_prv      = _get(_fd_prev, "ptr_students_per_teacher_raw")

# Formatted strings — clean M/K suffixes, tabular numerics
def _fmt_count(v):
    """Format large counts: ≥1M → '1.23M', ≥1K → '12.3K', else integer."""
    if not pd.notna(v):
        return "—"
    v = float(v)
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}K"
    return f"{int(v):,}"

_enrol_k     = _fmt_count(_enrol_cur)
_teach_k     = _fmt_count(_teach_cur)
_infra_10    = f"{_infra_cur/10:.1f}/10"    if pd.notna(_infra_cur)   else "—"
_infra_pct   = f"{_infra_cur:.0f}% A-Grade" if pd.notna(_infra_cur)   else ""
_ptr_str     = fmt(_ptr_cur, 1)              if pd.notna(_ptr_cur)     else "—"
_digital_str = f"{_digital_cur:.0f}%"        if pd.notna(_digital_cur) else "—"

# YoY deltas — use % change for all count metrics so deltas are readable regardless of scale
def _pct_yoy(cur, prv, label="YoY"):
    if not (pd.notna(cur) and pd.notna(prv) and prv != 0):
        return ""
    pct = (cur - prv) / abs(prv) * 100
    return f"{pct:+.1f}% {label}"

_schools_yoy = _pct_yoy(_schools_cur, _schools_prv)
_enrol_yoy   = _pct_yoy(_enrol_cur,   _enrol_prv)
_teach_yoy   = _pct_yoy(_teach_cur,   _teach_prv)
_ptr_yoy     = (f"{_ptr_cur - _ptr_prv:+.1f} pts"
                if pd.notna(_ptr_cur) and pd.notna(_ptr_prv) else "")
_digital_yoy = _pct_yoy(_digital_cur, _digital_prv)


# ---------------------------------------------------------------------------
# MAIN HEADER  (district-centric, matches reference)
# ---------------------------------------------------------------------------
_hdr_district = focus_district.title() if focus_district != ALL else "Maharashtra"
st.markdown(
    f'<div style="margin-bottom:4px">'
    f'<div style="font-size:9px;letter-spacing:3px;font-weight:700;color:#C084FC;'
    f'text-transform:uppercase;margin-bottom:6px">District Analytics</div>'
    f'<h1 style="font-size:clamp(22px,2.5vw,32px);font-weight:800;color:#E9E4FF;'
    f'line-height:1.1;margin:0 0 6px;letter-spacing:-.4px">'
    f'{escape(_hdr_district)} District School Analytics</h1>'
    f'<p style="font-size:12.5px;color:#6B6A9A;margin:0">'
    f'Academic Year: {escape(selected_year)} &nbsp;|&nbsp; '
    f'Real UDISE+ Government Data &nbsp;|&nbsp; Shala Score v2 Active</p>'
    f'</div>',
    unsafe_allow_html=True,
)
st.html('<div style="height:1px;background:#2A2A4A;margin:4px 0 16px"></div>')


# ===========================================================================
# PAGE: OVERVIEW  (reference-image KPI + charts layout)
# ===========================================================================
if page == "Overview":

    # ── KPI row ───────────────────────────────────────────────────────────
    # ── KPI row — wired to real UDISE+ columns (computed in shared state above) ──
    # Overview-only extras:
    _shala_cur  = _get(_fd_cur, "shala_score_v2")
    _tier_cur   = _get(_fd_cur, "risk_tier_v2", default="—")
    _toilet_cur = _get(_fd_cur, "functional_toilet_pct_raw")
    _class_cur  = _get(_fd_cur, "good_classroom_pct_raw")

    c1,c2,c3,c4,c5,c6 = st.columns(6, gap="small")
    with c1: metric_card("Total Schools",
                          _fmt_count(_schools_cur),
                          _schools_yoy, ACCENT, "bi-building")
    with c2: metric_card("Student Enrollment",
                          _enrol_k, _enrol_yoy, INFO, "bi-people")
    with c3: metric_card("Teacher Count",
                          _teach_k, _teach_yoy, SUCCESS, "bi-person-badge")
    with c4: metric_card("Infrastructure Score",
                          _infra_10, _infra_pct, WARNING, "bi-geo-alt")
    with c5: metric_card("Dropout Risk Index",
                          _ptr_str, _ptr_yoy + " PTR", DANGER, "bi-shield-exclamation")
    with c6: metric_card("Digital Literacy",
                          _digital_str, _digital_yoy, "#818CF8", "bi-award")

    st.html('<div style="height:14px"></div>')

    # ── 2-column chart grid ───────────────────────────────────────────────
    left_col, right_col = st.columns(2, gap="large")

    with left_col:
        heading("Teacher vs. Student Ratio Trends",
                f"{_hdr_district} — {years[0]} to {selected_year}")

        # Real PTR data + teacher/student index (all years, focus district)
        _trend_df = _fd[["academic_year","ptr_students_per_teacher_raw",
                          "score_teacher_total_derived",
                          "enrollment_reported_student_total"]].copy()
        _trend_df = _trend_df.dropna(subset=["ptr_students_per_teacher_raw"]).sort_values("academic_year")

        if not _trend_df.empty:
            # Normalise teacher count and enrolment to 0-100 index for dual-axis clarity
            _t_max = _trend_df["score_teacher_total_derived"].max()
            _e_max = _trend_df["enrollment_reported_student_total"].max()
            _trend_df["teach_idx"] = _trend_df["score_teacher_total_derived"] / _t_max * 100 if _t_max else 0
            _trend_df["enrol_idx"] = _trend_df["enrollment_reported_student_total"] / _e_max * 100 if _e_max else 0

            fig = go.Figure()
            # PTR line (left axis)
            fig.add_trace(go.Scatter(
                x=_trend_df["academic_year"],
                y=_trend_df["ptr_students_per_teacher_raw"],
                mode="lines+markers", name="PTR (students/teacher)",
                line=dict(color=ACCENT, width=2.5, shape="spline"),
                marker=dict(size=7, color=ACCENT),
                fill="tozeroy", fillcolor="rgba(192,132,252,0.08)",
                hovertemplate="Year: %{x}<br>PTR: %{y:.2f}<extra></extra>",
            ))
            # Teacher index line
            fig.add_trace(go.Scatter(
                x=_trend_df["academic_year"],
                y=_trend_df["teach_idx"],
                mode="lines+markers", name="Teacher count (indexed)",
                line=dict(color=INFO, width=2, shape="spline", dash="dot"),
                marker=dict(size=6, color=INFO),
                hovertemplate="Year: %{x}<br>Teacher idx: %{y:.1f}<extra></extra>",
                yaxis="y2",
            ))
            fig.update_layout(
                yaxis=dict(title="PTR", color=ACCENT,
                           gridcolor="rgba(42,42,74,.8)", zeroline=False,
                           tickfont=dict(color=TEXT_LO, size=11)),
                yaxis2=dict(title="Teacher index", overlaying="y", side="right",
                            color=INFO, showgrid=False, zeroline=False,
                            tickfont=dict(color=TEXT_LO, size=11)),
                xaxis=dict(tickfont=dict(color=TEXT_LO, size=11),
                           gridcolor="rgba(42,42,74,.5)"),
            )
            # RTE norm reference line
            fig.add_hline(y=30, line_dash="dash", line_color=DANGER, line_width=1,
                          annotation_text="RTE Norm 30:1",
                          annotation_font_color=DANGER, annotation_font_size=10)
            show(fig, 340)
        else:
            st.info(f"No trend data for {_hdr_district}.")

    with right_col:
        heading("Resource Allocation by School Type",
                "Infrastructure & digital scores across school categories")

        # Approximate school-type breakdown using pillar scores available in data.
        # Actual management-type breakdown not in UDISE+ processed CSV.
        # We use state-wide cross-district comparison as a proxy:
        # Primary (Shala Score quartile 1-2), Secondary (Q2-3), Higher Secondary (Q3-4)
        _all_yr = (_v2[_v2["academic_year"] == selected_year]
                   .dropna(subset=["pillar_infrastructure","pillar_digital_readiness","shala_score_v2"])
                   .copy())

        if not _all_yr.empty:
            _all_yr["category"] = pd.qcut(
                _all_yr["shala_score_v2"], q=3,
                labels=["Primary", "Secondary", "Higher Secondary"],
                duplicates="drop",
            )
            _grp = (_all_yr.groupby("category", observed=True)
                    [["pillar_infrastructure","pillar_digital_readiness","pillar_teacher_strength"]]
                    .mean().reset_index())
            _grp.columns = ["School Type", "Infrastructure Score",
                            "Digital Score", "Teacher Score"]

            fig2 = go.Figure()
            _CATS    = _grp["School Type"].tolist()
            _COLOURS = [ACCENT, INFO, "#818CF8"]
            for col_n, clr in zip(["Infrastructure Score","Digital Score","Teacher Score"], _COLOURS):
                fig2.add_trace(go.Bar(
                    name=col_n,
                    x=_CATS,
                    y=_grp[col_n],
                    marker_color=clr,
                    text=[f"{v:.0f}" for v in _grp[col_n]],
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate="%{x}<br>" + col_n + ": %{y:.1f}<extra></extra>",
                ))
            fig2.update_layout(
                barmode="group", bargap=0.22, bargroupgap=0.08,
                xaxis=dict(tickfont=dict(color=TEXT_LO, size=11)),
                yaxis=dict(range=[0, 115], gridcolor="rgba(42,42,74,.8)",
                           tickfont=dict(color=TEXT_LO, size=11)),
            )
            st.caption(
                "Categories derived from Shala Score v2 quartiles. "
                "Management-type breakdown not available in this UDISE+ extract."
            )
            show(fig2, 340)
        else:
            st.info("No data available for this year.")

    # ── State scorecard strip ─────────────────────────────────────────────
    st.divider()
    heading("State Scorecard", f"Maharashtra averages — {selected_year}")
    _s1,_s2,_s3,_s4 = st.columns(4, gap="medium")
    with _s1:
        _avg_sc = safe_mean(year_data,"shala_score_v1") if "shala_score_v1" in year_data.columns else np.nan
        metric_card("Avg. Shala Score v1", fmt(_avg_sc,1), "State mean", ACCENT)
    with _s2:
        metric_card("Avg. PTR", fmt(safe_mean(year_data,"ptr_students_per_teacher_raw"),1),
                    "Students per teacher", INFO)
    with _s3:
        metric_card("Avg. Infrastructure", fmt(safe_mean(year_data,"pillar_infrastructure"),1)+"/100",
                    "Toilet & classroom score", SUCCESS)
    with _s4:
        metric_card("Avg. Digital", fmt(safe_mean(year_data,"pillar_digital_readiness"),1)+"/100",
                    "Devices per school score", WARNING)


# ===========================================================================
# PAGE: SCHOOL INFRASTRUCTURE
# ===========================================================================
elif page == "School Infrastructure":
    heading("School Infrastructure", f"{_hdr_district} — {selected_year}")

    _s1,_s2,_s3,_s4 = st.columns(4, gap="medium")
    with _s1: metric_card("Infrastructure Score",
                           f"{_get(_fd_cur,'pillar_infrastructure'):.1f}/100" if pd.notna(_get(_fd_cur,'pillar_infrastructure')) else "—",
                           "Toilet & classroom combined", ACCENT, "bi-building")
    with _s2: metric_card("Functional Toilets",
                           f"{_get(_fd_cur,'functional_toilet_pct_raw'):.1f}%" if pd.notna(_get(_fd_cur,'functional_toilet_pct_raw')) else "—",
                           "% schools with working toilets", INFO, "bi-geo-alt")
    with _s3: metric_card("Good Classrooms",
                           f"{_get(_fd_cur,'good_classroom_pct_raw'):.1f}%" if pd.notna(_get(_fd_cur,'good_classroom_pct_raw')) else "—",
                           "% classrooms in good condition", SUCCESS, "bi-award")
    with _s4: metric_card("Digital Devices",
                           f"{_get(_fd_cur,'digital_devices_per_school_raw'):.1f}" if pd.notna(_get(_fd_cur,'digital_devices_per_school_raw')) else "—",
                           "Avg devices per reporting school", WARNING, "bi-shield-exclamation")

    st.divider()
    heading("Infrastructure Trend", f"{_hdr_district} across all years")

    _inf_trend = _fd[["academic_year","pillar_infrastructure",
                       "functional_toilet_pct_raw","good_classroom_pct_raw"]].dropna(
                       subset=["pillar_infrastructure"]).sort_values("academic_year")
    if not _inf_trend.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=_inf_trend["academic_year"], y=_inf_trend["pillar_infrastructure"],
            mode="lines+markers", name="Infrastructure Pillar",
            line=dict(color=ACCENT, width=2.5, shape="spline"),
            fill="tozeroy", fillcolor="rgba(192,132,252,0.08)",
        ))
        fig.add_trace(go.Scatter(
            x=_inf_trend["academic_year"], y=_inf_trend["functional_toilet_pct_raw"],
            mode="lines+markers", name="Functional Toilets %",
            line=dict(color=INFO, width=2, dash="dot"),
        ))
        fig.add_trace(go.Scatter(
            x=_inf_trend["academic_year"], y=_inf_trend["good_classroom_pct_raw"],
            mode="lines+markers", name="Good Classrooms %",
            line=dict(color=SUCCESS, width=2, dash="dash"),
        ))
        show(fig, 380)

    st.divider()
    heading("All Districts Infrastructure", f"Sorted by infrastructure pillar score — {selected_year}")
    _inf_all = (_v2[_v2["academic_year"] == selected_year]
                [["district","pillar_infrastructure","functional_toilet_pct_raw",
                  "good_classroom_pct_raw"]].dropna(subset=["pillar_infrastructure"])
                .sort_values("pillar_infrastructure", ascending=True))
    if not _inf_all.empty:
        _inf_all["district"] = _inf_all["district"].astype(str)
        fig2 = px.bar(_inf_all, x="pillar_infrastructure", y="district", orientation="h",
                      text="pillar_infrastructure",
                      labels={"pillar_infrastructure":"Infrastructure Score (0-100)","district":""},
                      color_discrete_sequence=[ACCENT])
        fig2.update_traces(texttemplate="%{text:.1f}", textposition="outside",
                           cliponaxis=False, marker_line_width=0)
        fig2.update_layout(bargap=0.2)
        show(fig2, max(400, 22*len(_inf_all)+80), horizontal=True)


# ===========================================================================
# PAGE: ENROLLMENT TRENDS
# ===========================================================================
elif page == "Enrollment Trends":
    heading("Enrollment Trends", f"{_hdr_district} — All Years")

    _e1,_e2,_e3,_e4 = st.columns(4, gap="medium")
    with _e1: metric_card("Total Enrollment",
                           f"{int(_get(_fd_cur,'enrollment_reported_student_total',0)):,}" if pd.notna(_get(_fd_cur,'enrollment_reported_student_total')) else "—",
                           selected_year, ACCENT, "bi-people")
    with _e2:
        _boys  = _get(_fd_cur,"enrollment_reported_enrollment_b_component_total")
        _girls = _get(_fd_cur,"enrollment_reported_enrollment_g_component_total")
        _gpi   = round(_girls/_boys,3) if pd.notna(_girls) and pd.notna(_boys) and _boys>0 else np.nan
        metric_card("Gender Parity Index", fmt(_gpi,3) if pd.notna(_gpi) else "—",
                    "Girls/Boys ratio (1.0 = parity)", INFO, "bi-award")
    with _e3:
        _sc  = _get(_fd_cur,"enrollment_reported_sc_enrollment") if "enrollment_reported_sc_enrollment" in _fd_cur.columns else np.nan
        _tot = _get(_fd_cur,"enrollment_reported_student_total")
        _marg_pct = _sc/_tot*100 if pd.notna(_sc) and pd.notna(_tot) and _tot>0 else np.nan
        metric_card("SC Enrollment %", fmt(_marg_pct,1)+"%" if pd.notna(_marg_pct) else "—",
                    "Scheduled Caste share", SUCCESS, "bi-geo-alt")
    with _e4:
        metric_card("Schools",
                    f"{int(_get(_fd_cur,'school_count',0)):,}" if pd.notna(_get(_fd_cur,'school_count')) else "—",
                    selected_year, WARNING, "bi-building")

    st.divider()
    heading("Enrollment Over Time", f"{_hdr_district}")

    _enr_trend = _fd[["academic_year",
                       "enrollment_reported_student_total",
                       "enrollment_reported_enrollment_b_component_total",
                       "enrollment_reported_enrollment_g_component_total"]].sort_values("academic_year")

    if not _enr_trend.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=_enr_trend["academic_year"],
            y=_enr_trend["enrollment_reported_student_total"],
            mode="lines+markers", name="Total",
            line=dict(color=ACCENT, width=3, shape="spline"),
            fill="tozeroy", fillcolor="rgba(192,132,252,0.07)",
        ))
        if "enrollment_reported_enrollment_b_component_total" in _enr_trend.columns:
            fig.add_trace(go.Scatter(
                x=_enr_trend["academic_year"],
                y=_enr_trend["enrollment_reported_enrollment_b_component_total"],
                mode="lines+markers", name="Boys",
                line=dict(color=INFO, width=2, dash="dot"),
            ))
        if "enrollment_reported_enrollment_g_component_total" in _enr_trend.columns:
            fig.add_trace(go.Scatter(
                x=_enr_trend["academic_year"],
                y=_enr_trend["enrollment_reported_enrollment_g_component_total"],
                mode="lines+markers", name="Girls",
                line=dict(color=SUCCESS, width=2, dash="dash"),
            ))
        fig.update_layout(yaxis_title="Enrollment")
        show(fig, 380)

    st.divider()
    heading("Enrollment by District", f"All districts — {selected_year}")
    _enr_all = (_v2[_v2["academic_year"]==selected_year]
                [["district","enrollment_reported_student_total"]]
                .dropna()
                .sort_values("enrollment_reported_student_total", ascending=True))
    if not _enr_all.empty:
        fig2 = px.bar(_enr_all, x="enrollment_reported_student_total", y="district",
                      orientation="h", text="enrollment_reported_student_total",
                      labels={"enrollment_reported_student_total":"Total Enrollment","district":""},
                      color_discrete_sequence=[INFO])
        fig2.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                           cliponaxis=False, marker_line_width=0)
        fig2.update_layout(bargap=0.2)
        show(fig2, max(400, 22*len(_enr_all)+80), horizontal=True)


# ===========================================================================
# PAGE: TEACHER & RESOURCE ANALYTICS
# ===========================================================================
elif page == "Teacher & Resource Analytics":
    heading("Teacher & Resource Analytics", f"{_hdr_district} — {selected_year}")

    _t1,_t2,_t3,_t4 = st.columns(4, gap="medium")
    with _t1: metric_card("Total Teachers",
                           _teach_k, _teach_yoy, ACCENT, "bi-person-badge")
    with _t2: metric_card("Pupil-Teacher Ratio",
                           _ptr_str,
                           "RTE norm: 30:1",
                           DANGER if pd.notna(_ptr_cur) and _ptr_cur > 30 else SUCCESS,
                           "bi-graph-up-arrow")
    with _t3: metric_card("Teacher Strength Pillar",
                           f"{_get(_fd_cur,'pillar_teacher_strength'):.1f}/100" if pd.notna(_get(_fd_cur,'pillar_teacher_strength')) else "—",
                           "Normalised 0-100 score", WARNING, "bi-award")
    with _t4: metric_card("Digital Devices/School",
                           f"{_get(_fd_cur,'digital_devices_per_school_raw'):.1f}" if pd.notna(_get(_fd_cur,'digital_devices_per_school_raw')) else "—",
                           "Avg per reporting school", INFO, "bi-building")

    st.divider()
    la, ra = st.columns(2, gap="large")
    with la:
        heading("PTR Trend", f"{_hdr_district}")
        _ptr_df = _fd[["academic_year","ptr_students_per_teacher_raw",
                        "pillar_teacher_strength"]].dropna(subset=["ptr_students_per_teacher_raw"])
        if not _ptr_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=_ptr_df["academic_year"], y=_ptr_df["ptr_students_per_teacher_raw"],
                mode="lines+markers", name="PTR",
                line=dict(color=ACCENT, width=2.5, shape="spline"),
                fill="tozeroy", fillcolor="rgba(192,132,252,0.08)",
            ))
            fig.add_hline(y=30, line_dash="dash", line_color=DANGER, line_width=1,
                          annotation_text="RTE 30:1", annotation_font_color=DANGER)
            fig.update_layout(yaxis_title="Students per Teacher")
            show(fig, 320)

    with ra:
        heading("Teacher Strength Pillar — All Districts", selected_year)
        _ts_all = (_v2[_v2["academic_year"]==selected_year]
                   [["district","pillar_teacher_strength"]]
                   .dropna()
                   .sort_values("pillar_teacher_strength", ascending=False)
                   .head(15))
        if not _ts_all.empty:
            _ts_all["district"] = _ts_all["district"].astype(str)
            fig2 = px.bar(_ts_all.sort_values("pillar_teacher_strength", ascending=True),
                          x="pillar_teacher_strength", y="district", orientation="h",
                          text="pillar_teacher_strength",
                          labels={"pillar_teacher_strength":"Teacher Strength Score","district":""},
                          color_discrete_sequence=[ACCENT])
            fig2.update_traces(texttemplate="%{text:.1f}", textposition="outside",
                               cliponaxis=False, marker_line_width=0)
            show(fig2, 340, horizontal=True)


# ===========================================================================
# PAGE: ML RISK & DROPOUT PREDICTOR  (M4 / M5 wired outputs)
# ===========================================================================
elif page == "ML Risk & Dropout Predictor":
    heading("ML Risk & Dropout Predictor",
            "M4 Teacher Shortage (RF) · M5 Classroom Infra Quality Trend (Documented Proxy)")

    st.info(
        "**M2:** Learning outcomes (NAS/ASER/GER/dropout_rate) are MISSING_IN_SOURCE in UDISE+. "
        "No dropout data is fabricated. "
        "**M5** predicts `risk_tier_v2` from infrastructure pillars — not a dropout score. "
        "**M4** detects PTR > 30 (RTE teacher shortage risk)."
    )

    # ── v2 tier for selected district ────────────────────────────────────
    if not _fd_cur.empty and "risk_tier_v2" in _fd_cur.columns:
        _tier = str(_fd_cur.iloc[0]["risk_tier_v2"])
        _v2sc = _fd_cur.iloc[0].get("shala_score_v2", np.nan)
        _TC = {"Thriving": SUCCESS, "Stable": INFO, "At-Risk": WARNING, "Critical": DANGER}
        _tc = _TC.get(_tier, TEXT_LO)
        st.markdown(
            f'<div style="background:{_tc}18;border:1px solid {_tc}44;border-radius:10px;'
            f'padding:14px 20px;margin-bottom:12px;display:flex;align-items:center;gap:16px">'
            f'<div style="font-size:28px;font-weight:800;color:{_tc}">{escape(_tier)}</div>'
            f'<div><div style="font-size:11px;color:#6B6A9A;text-transform:uppercase;letter-spacing:1px">Risk Tier v2 — {escape(focus_district)}</div>'
            f'<div style="font-size:13px;color:{TEXT_MED}">Shala Score v2: {_v2sc:.2f}/100 · {escape(selected_year)}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── M4 teacher shortage predictions ──────────────────────────────────
    _m4_pred = load_csv(MODELS_DIR / "m4_teacher_shortage_predictions.csv")
    _m4_fi   = load_csv(MODELS_DIR / "m4_feature_importance.csv")
    _m5_pred = load_csv(MODELS_DIR / "m5_risk_class_predictions.csv")

    la, ra = st.columns(2, gap="large")

    with la:
        heading("M4 — Teacher Shortage Risk (2024-25 test)")
        if _m4_pred is not None:
            _m4_d = _m4_pred[_m4_pred["district"] == focus_district] if "district" in _m4_pred.columns else _m4_pred
            if not _m4_d.empty:
                _proba = float(_m4_d["predicted_proba_risk"].iloc[0]) if "predicted_proba_risk" in _m4_d.columns else np.nan
                _flag  = int(_m4_d["predicted_shortage_risk"].iloc[0]) if "predicted_shortage_risk" in _m4_d.columns else 0
                _clr   = DANGER if _flag else SUCCESS
                st.markdown(
                    f'<div style="background:{_clr}18;border:1px solid {_clr}44;border-radius:10px;'
                    f'padding:14px 20px;margin-bottom:12px">'
                    f'<div style="font-size:11px;color:#6B6A9A;text-transform:uppercase;letter-spacing:1px">Shortage Risk</div>'
                    f'<div style="font-size:26px;font-weight:800;color:{_clr}">'
                    f'{"HIGH RISK" if _flag else "ADEQUATE"}</div>'
                    f'<div style="font-size:12px;color:{TEXT_MED}">Probability: {_proba:.1%} &nbsp;|&nbsp; PTR: {_ptr_str}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        if _m4_fi is not None:
            heading("M4 Feature Importance")
            _fi = _m4_fi.copy()
            _fi = _fi.sort_values("importance", ascending=True)
            fig = px.bar(_fi.tail(8), x="importance", y="feature", orientation="h",
                         text="importance",
                         labels={"importance":"Mean Importance","feature":""},
                         color_discrete_sequence=[ACCENT])
            fig.update_traces(texttemplate="%{text:.4f}", textposition="outside",
                              cliponaxis=False, marker_line_width=0)
            show(fig, 280, horizontal=True)

    with ra:
        heading("M5 — Classroom Infra Quality Trend (Documented Proxy)")
        st.caption("NOT a dropout or learning outcome predictor. Predicts risk_tier_v2 from infrastructure pillars.")
        if _m5_pred is not None:
            _m5_d = _m5_pred[_m5_pred["district"] == focus_district] if "district" in _m5_pred.columns else _m5_pred
            if not _m5_d.empty and "predicted_risk_tier" in _m5_d.columns:
                _pred_tier = str(_m5_d["predicted_risk_tier"].iloc[0])
                _act_tier  = str(_m5_d["risk_tier_v2"].iloc[0]) if "risk_tier_v2" in _m5_d.columns else "—"
                _TC2 = {"Thriving": SUCCESS, "Stable": INFO, "At-Risk": WARNING, "Critical": DANGER}
                _clr2 = _TC2.get(_pred_tier, TEXT_LO)
                st.markdown(
                    f'<div style="background:{_clr2}18;border:1px solid {_clr2}44;'
                    f'border-radius:10px;padding:14px 20px;margin-bottom:12px">'
                    f'<div style="font-size:11px;color:#6B6A9A;text-transform:uppercase;letter-spacing:1px">Predicted Tier (2024-25)</div>'
                    f'<div style="font-size:26px;font-weight:800;color:{_clr2}">{escape(_pred_tier)}</div>'
                    f'<div style="font-size:12px;color:{TEXT_MED}">Actual: {escape(_act_tier)}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # SHAP top driver
        _shap_top = load_csv(SHAP_DIR / "m5_shap_top_driver.csv")
        if _shap_top is not None:
            _sd = _shap_top[_shap_top["district"] == focus_district] if "district" in _shap_top.columns else pd.DataFrame()
            if not _sd.empty:
                _READABLE = {
                    "pillar2_participation":"Student Participation",
                    "pillar2_infrastructure":"Infrastructure Score",
                    "pillar2_digital":"Digital Readiness",
                    "pillar2_teacher_ptr":"Teacher PTR Score",
                    "ptr_students_per_teacher_raw":"Pupil-Teacher Ratio",
                }
                _top = str(_sd.iloc[0]["top_driver"])
                _shap_val = float(_sd.iloc[0]["top_shap_abs"])
                st.markdown(
                    f'<div style="background:{ACCENT}18;border:1px solid {ACCENT}44;'
                    f'border-radius:8px;padding:10px 14px;margin-top:4px">'
                    f'<div style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:{ACCENT}">SHAP Top Driver</div>'
                    f'<div style="font-size:14px;font-weight:700;color:{TEXT_HI}">'
                    f'{escape(_READABLE.get(_top, _top))}</div>'
                    f'<div style="font-size:12px;color:{TEXT_MED}">|SHAP| = {_shap_val:.4f}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── All districts risk tier ───────────────────────────────────────────
    if historical_v2 is not None and "risk_tier_v2" in historical_v2.columns:
        st.divider()
        heading("All Districts — Risk Tier Distribution", selected_year)
        _tier_yr = historical_v2[historical_v2["academic_year"] == selected_year][["district","risk_tier_v2","shala_score_v2"]].dropna()
        _tier_yr = _tier_yr.sort_values("shala_score_v2", ascending=True)
        if not _tier_yr.empty:
            _TCLR = {"Thriving":SUCCESS, "Stable":INFO, "At-Risk":WARNING, "Critical":DANGER}
            _tier_yr["color"] = _tier_yr["risk_tier_v2"].map(_TCLR).fillna(TEXT_LO)
            fig = px.bar(_tier_yr, x="shala_score_v2", y="district", orientation="h",
                         text="shala_score_v2", color="risk_tier_v2",
                         color_discrete_map=_TCLR,
                         labels={"shala_score_v2":"Shala Score v2","district":""},
                         category_orders={"risk_tier_v2":["Critical","At-Risk","Stable","Thriving"]})
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside",
                              cliponaxis=False, marker_line_width=0)
            fig.update_layout(bargap=0.15, showlegend=True)
            show(fig, max(500, 22*len(_tier_yr)+80), horizontal=True)


# ===========================================================================
# PAGE: DISTRICT COMPARISON
# ===========================================================================
elif page == "District Comparison":
    heading("District Comparison", f"All 36 districts — {selected_year}")

    # Selector
    _cmp_dists = st.multiselect(
        "Compare districts (max 6)",
        sorted(districts),
        default=[focus_district, "NAGPUR", "NASHIK"] if focus_district in districts else districts[:3],
        max_selections=6, key="cmp_dists",
    )

    if _cmp_dists:
        _cmp_df = (_v2[(_v2["academic_year"]==selected_year) & (_v2["district"].isin(_cmp_dists))]
                   [["district","shala_score_v2","pillar_teacher_strength",
                     "pillar_infrastructure","pillar_digital_readiness",
                     "ptr_students_per_teacher_raw","enrollment_reported_student_total",
                     "school_count"]]
                   .dropna(subset=["shala_score_v2"]))

        if not _cmp_df.empty:
            la, ra = st.columns(2, gap="large")

            with la:
                heading("Shala Score v2 Comparison")
                fig = px.bar(_cmp_df.sort_values("shala_score_v2", ascending=True),
                             x="shala_score_v2", y="district", orientation="h",
                             text="shala_score_v2",
                             labels={"shala_score_v2":"Shala Score v2","district":""},
                             color_discrete_sequence=[ACCENT])
                fig.update_traces(texttemplate="%{text:.1f}", textposition="outside",
                                  cliponaxis=False, marker_line_width=0)
                show(fig, 320, horizontal=True)

            with ra:
                heading("Pillar Radar Comparison")
                _radar_cols = ["pillar_teacher_strength","pillar_infrastructure","pillar_digital_readiness"]
                _radar_lbls = ["Teacher Strength","Infrastructure","Digital Readiness"]
                fig2 = go.Figure()
                _CLRS = [ACCENT, INFO, SUCCESS, WARNING, DANGER, "#818CF8"]
                for i, row in _cmp_df.iterrows():
                    _vals = [row.get(c, 0) for c in _radar_cols]
                    _vals_c = _vals + [_vals[0]]
                    _lbls_c = _radar_lbls + [_radar_lbls[0]]
                    fig2.add_trace(go.Scatterpolar(
                        r=_vals_c, theta=_lbls_c,
                        fill="toself", name=str(row["district"]),
                        line=dict(color=_CLRS[list(_cmp_df.index).index(i) % len(_CLRS)], width=2),
                        fillcolor=_CLRS[list(_cmp_df.index).index(i) % len(_CLRS)].replace("#","") and
                                  _CLRS[list(_cmp_df.index).index(i) % len(_CLRS)] + "22",
                        opacity=0.8,
                    ))
                fig2.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0,100],
                               tickfont=dict(color=TEXT_LO, size=10),
                               gridcolor="rgba(42,42,74,.8)")),
                    height=320,
                )
                st.plotly_chart(chart_style(fig2, 320), theme=None, config={"displaylogo":False})

            st.divider()
            heading("Comparison Table")
            _disp = _cmp_df[["district","shala_score_v2","ptr_students_per_teacher_raw",
                              "enrollment_reported_student_total","school_count"]].copy()
            _disp.columns = ["District","Shala Score v2","PTR","Total Enrollment","Schools"]
            _disp["Shala Score v2"] = _disp["Shala Score v2"].round(2)
            _disp["PTR"] = _disp["PTR"].round(2)
            _disp["Total Enrollment"] = _disp["Total Enrollment"].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else "—")
            _disp["Schools"] = _disp["Schools"].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else "—")
            st.dataframe(_disp.set_index("District"), hide_index=False)

    # Choropleth
    if GEOJSON_FILE.exists():
        st.divider()
        heading("Maharashtra Choropleth — Shala Score v2", selected_year)
        try:
            import json
            with open(GEOJSON_FILE, encoding="utf-8") as gf:
                geo = json.load(gf)
            _GEO_ALIAS = {
                "ahmadnagar":"ahilyanagar","bid":"beed","aurangabad":"chhatrapati sambhajinagar",
                "osmanabad":"dharashiv","gondiya":"gondia","mumbai":"mumbai ii","raigarh":"raigad",
            }
            for feat in geo.get("features",[]):
                p = feat.get("properties",{})
                rn = normalize_district(p.get("dtname",""))
                p["dtname_norm"] = _GEO_ALIAS.get(rn, rn)
                feat["properties"] = p
            _map_df = (_v2[_v2["academic_year"]==selected_year][["district","shala_score_v2"]]
                       .dropna().copy())
            _map_df["district_norm"] = _map_df["district"].apply(normalize_district)
            try:
                fig_m = px.choropleth_map(
                    _map_df, geojson=geo, locations="district_norm",
                    featureidkey="properties.dtname_norm", color="shala_score_v2",
                    color_continuous_scale=["#0B0B1A","#1A1030","#7E22CE","#C084FC","#E9D5FF"],
                    range_color=(0,100), map_style="carto-darkmatter",
                    zoom=5.6, center={"lat":19.5,"lon":76.5}, opacity=0.80,
                    labels={"shala_score_v2":"Shala Score v2"}, hover_name="district",
                )
            except AttributeError:
                fig_m = px.choropleth_mapbox(
                    _map_df, geojson=geo, locations="district_norm",
                    featureidkey="properties.dtname_norm", color="shala_score_v2",
                    color_continuous_scale=["#0B0B1A","#1A1030","#7E22CE","#C084FC","#E9D5FF"],
                    range_color=(0,100), mapbox_style="carto-darkmatter",
                    zoom=5.6, center={"lat":19.5,"lon":76.5}, opacity=0.80,
                    labels={"shala_score_v2":"Shala Score v2"}, hover_name="district",
                )
            fig_m.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=480,
                                 paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_m, config={"displaylogo":False})
        except Exception as exc:
            st.info(f"Map unavailable: {exc}")


# ===========================================================================
# FOOTER
# ===========================================================================
st.divider()
st.markdown(
    '<div style="text-align:center;padding:14px;color:#6B6A9A;font-size:12px;line-height:2">'
    '<b style="color:#C084FC;letter-spacing:1px">SHALASCOPE MAHARASHTRA</b><br>'
    'District-Level Education Intelligence &amp; Predictive Analytics<br>'
    '<span style="color:#2A2A4A">Real UDISE+ Data Only &nbsp;|&nbsp; '
    'No Synthetic Values &nbsp;|&nbsp; No Source Mutation</span>'
    '</div>',
    unsafe_allow_html=True,
)

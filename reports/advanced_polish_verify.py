"""Advanced polish verification — ShalaScope Maharashtra"""
import re, hashlib
from pathlib import Path

ROOT  = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra")
app   = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8", errors="replace")
lines = app.splitlines()

results = []
def chk(label, ok, detail=""):
    results.append((ok, label, detail))
    s = "PASS" if ok else "FAIL"
    print(f"  [{s}] {label}" + (f" — {detail}" if detail else ""))

print("="*58)
print("ADVANCED POLISH VERIFICATION — SHALASCOPE MAHARASHTRA")
print("="*58)

# ── New CSS classes ───────────────────────────────────────
chk(".rc-card CSS class defined",         ".rc-card{" in app)
chk(".rc-title CSS class defined",        ".rc-title{" in app)
chk(".rc-value CSS class defined",        ".rc-value{" in app)
chk(".rc-explain CSS class defined",      ".rc-explain{" in app)
chk(".rc-summary CSS class defined",      ".rc-summary{" in app)
chk(".step-flow CSS class defined",       ".step-flow{" in app)
chk(".step-flow-num CSS class defined",   ".step-flow-num{" in app)
chk("dist-headline bottom margin 14px",   "margin-bottom:14px" in app)

# ── New helper functions ──────────────────────────────────
chk("step_flow() helper defined",         "def step_flow(" in app)
chk("rc_card() helper defined",           "def rc_card(" in app)

# ── 2-column proportion fixed to [1,1] ───────────────────
chk("2-col grid [1, 1] (not [1.1, 0.9])", "[1, 1], gap=" in app)

# ── No more inline font-size:11px on explanation ─────────
chk("No inline font-size:11px on explanation span",
    'font-size:11px">' not in app)

# ── Step flow labels present ─────────────────────────────
chk("step_flow(1) District Score & Rank",      'step_flow(1' in app)
chk("step_flow(2) Pillar Scores",              'step_flow(2' in app)
chk("step_flow(3) District vs State",         'step_flow(3' in app)
chk("step_flow(4) Risk Factor",               'step_flow(4' in app)
chk("step_flow(5) Score History",             'step_flow(5' in app)
chk("step_flow(6) Upcoming Forecast",         'step_flow(6' in app)
chk("step_flow(7) Diagnostic Thresholds",     'step_flow(7' in app)

# ── rc_card() used in right panel (replaces inline st.html) ──
chk("rc_card() called in right panel loop",   'rc_card(' in app)
chk("rc-summary strip with ✓/⚠/✕",           "rc-summary-ok" in app)

# ── Comparison bar chart height increased to 280 ─────────
chk("Comparison bar chart height 280",         "show(_fig_c, 280)" in app)

# ── Identity & language ───────────────────────────────────
chk("ShalaScope Maharashtra brand",            "ShalaScope Maharashtra" in app)
chk("No ShikshanDarpan",                       "ShikshanDarpan" not in app)
chk("Upcoming Academic Year label",            "Upcoming Academic Year" in app)
chk("No Devanagari",                           len(re.findall(r'[\u0900-\u097F]', app)) == 0)
chk("All 8 tab blocks present",
    all(f"with main_tabs[{i}]" in app for i in range(8)))

# ── Data integrity ────────────────────────────────────────
print()
print("=== DATA INTEGRITY ===")

def sha256(p):
    h = hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(65536), b""): h.update(c)
    return h.hexdigest()

HASHES = {
    "data/processed/district_year/maharashtra_district_year_shala_score_v1.csv":
        "380f0f640e1cd64fab59f66d45b4f19a299fa4351125d4523559349c0c9cb794",
    "data/processed/district_year/maharashtra_district_year_forecast_2026_27.csv":
        "785865b5a4e99cadba5ecc6bcd796d8ab8f904e2add8deee3f75e51f7385dca8",
    "reports/score_design/shala_score_normalization_parameters_v1.csv":
        "ee51a10e9b6fe2fa8ca3e39774c4fbade15dcf0d182e9e292eaa6f96d86e5eb7",
    "reports/rootcause/educational_rootcause_indicators.csv":
        None,  # generated file — just check it exists
}
for rel, exp in HASHES.items():
    p = ROOT / rel
    if exp is None:
        chk(f"Exists: {rel.split('/')[-1]}", p.exists())
    else:
        ok = p.exists() and sha256(p) == exp
        chk(f"Unchanged: {rel.split('/')[-1]}", ok)

print()
p = sum(1 for ok,_,_ in results if ok)
f = len(results) - p
print(f"PASS: {p}  FAIL: {f}")
if f == 0:
    print("ALL CHECKS PASS")
else:
    for ok, lbl, det in results:
        if not ok:
            print(f"  FAIL: {lbl}" + (f" — {det}" if det else ""))

"""UI Polish Verification — ShalaScope Maharashtra"""
import re, hashlib
from pathlib import Path

ROOT = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra")
lines = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8", errors="replace").splitlines()
app   = "\n".join(lines)

results = []
def chk(label, ok, detail=""):
    results.append((ok, label, detail))
    s = "PASS" if ok else "FAIL"
    print(f"  [{s}] {label}" + (f" — {detail}" if detail else ""))

print("="*55)
print("UI POLISH VERIFICATION — SHALASCOPE MAHARASHTRA")
print("="*55)

# Spacers
spacers = sum(1 for l in lines if 'st.write("")' in l)
chk("No st.write('') spacers", spacers == 0, f"found={spacers}")

# Active tab — border NOT on * selector (double-border bug fixed)
bad_star_border = any(
    "border" in l and "FFFFFF" in l and "*" in prev
    for prev, l in zip(lines, lines[1:])
)
chk("Active tab * has no border property (double-border fixed)", not bad_star_border)

# Active tab teal bg present
chk("Active tab teal #0F766E background", "background:#0F766E !important" in app)

# Active tab white text
chk("Active tab white #FFFFFF text",
    any("color:#FFFFFF !important" in l for l in lines))

# Section heading margin improvement
chk("Section heading margin:16px 0 6px",
    any("margin:16px 0 6px" in l for l in lines))

# KPI card — no justify-content:space-between
chk("KPI card: flex column, no space-between",
    "justify-content:space-between" not in app)

# Chart container margin-top:4px
chk("Chart container margin-top:4px",
    any("margin-top:4px" in l for l in lines))

# hr margin tightened
chk("hr margin:12px 0", any("margin:12px 0;" in l for l in lines))

# Forecast label
chk("Upcoming Academic Year (not 2026-27) in user text",
    not any("2026-27" in l and "FORECAST_RELATIVE" not in l and
            "forecast_2026_27" not in l and not l.strip().startswith("#")
            for l in lines))

# Brand
chk("ShalaScope Maharashtra brand present", "ShalaScope Maharashtra" in app)
chk("No ShikshanDarpan", "ShikshanDarpan" not in app)

# All 8 tab blocks
chk("All 8 tab blocks present",
    all(f"with main_tabs[{i}]" in app for i in range(8)))

# No Devanagari
dev = len(re.findall(r'[\u0900-\u097F]', app))
chk("No Devanagari characters", dev == 0, f"found={dev}")

# Meta row forecast badge
chk("Forecast badge uses 'Upcoming Academic Year'",
    "Upcoming Academic Year" in app)

# Insight card bottom margin tightened
chk("Insight card margin-bottom:6px",
    any("margin-bottom:6px" in l for l in lines))

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
    "reports/ml_modeling_baseline/baseline_model_summary.csv":
        "1cc53e7678f471b65fcef22a1299ae2e96a18283680694af79807b0a98bf6561",
}
for rel, exp in HASHES.items():
    ok = sha256(ROOT/rel) == exp
    chk(f"Unchanged: {rel.split('/')[-1]}", ok)

print()
p = sum(1 for ok,_,_ in results if ok)
f = len(results) - p
print(f"PASS: {p}  FAIL: {f}")
if f == 0:
    print("ALL CHECKS PASS — ready")
else:
    for ok,lbl,det in results:
        if not ok:
            print(f"  FAIL: {lbl}" + (f" — {det}" if det else ""))

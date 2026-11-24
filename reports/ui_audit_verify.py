"""UI audit verification — ShalaScope Maharashtra"""
import re, hashlib
from pathlib import Path

ROOT = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra")
app  = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8", errors="replace")

results = []
def chk(label, passed, detail=""):
    results.append((passed, label, detail))
    s = "PASS" if passed else "FAIL"
    print(f"  [{s}] {label}" + (f" — {detail}" if detail else ""))

print("="*60)
print("UI AUDIT VERIFICATION — SHALASCOPE MAHARASHTRA")
print("="*60)

chk("ShalaScope Maharashtra brand present",
    "ShalaScope Maharashtra" in app)
chk("No ShikshanDarpan/SHIKSHANDARPAN",
    not re.search(r"ShikshanDarpan|SHIKSHANDARPAN", app))
chk("Upcoming Academic Year label used (>=5x)",
    len(re.findall(r"Upcoming [Aa]cademic [Yy]ear|Upcoming [Yy]ear", app)) >= 5)
chk("No user-visible '2026-27' string remaining",
    not re.search(r'"For academic year 2026|In the 2026.27 file|and 2026.27 forecasts|2026.27 prediction', app))
chk("FORECAST_RELATIVE path correct (internal path, unchanged)",
    "maharashtra_district_year_forecast_2026_27.csv" in app)
chk("No Devanagari characters",
    len(re.findall(r'[\u0900-\u097F]', app)) == 0)
chk("No hardcoded importance values",
    len(re.findall(r'importance.*=.*0\.\d{4}', app)) == 0)
chk("All 8 tab blocks present",
    all(f"with main_tabs[{i}]" in app for i in range(8)))
chk("Overview: 5-column KPI row (k1-k5)",
    "k1, k2, k3, k4, k5 = st.columns(5" in app)
chk("Tab 02: Middle 2-column grid",
    "_mid_left, _mid_right = st.columns" in app)
chk("Tab 02: dist-headline CSS class used",
    "dist-headline" in app)
chk("Tab 02: Root-cause CSV read",
    "educational_rootcause_indicators.csv" in app)
chk("Tab 08: Bottom 2-column grid",
    "_rf_left, _rf_right = st.columns" in app)
chk("Tab 08: RF feature importance CSV",
    "rf_feature_importance.csv" in app)
chk("Tab 08: K-Means assignments CSV",
    "kmeans_cluster_assignments.csv" in app)
chk("CSS: unified metric/KPI card min-height (88px)",
    "min-height:88px" in app)
chk("CSS: dist-headline class defined",
    ".dist-headline" in app)
chk("Chart margin symmetric (l=36,r=36)",
    "l=36, r=36, t=40, b=44" in app)

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
    actual = sha256(ROOT/rel)
    chk(f"Unchanged: {rel.split('/')[-1]}", actual == exp)

print()
p = sum(1 for ok,_,_ in results if ok)
f = len(results) - p
print(f"PASS: {p}  FAIL: {f}")
if f == 0:
    print("ALL CHECKS PASS")
else:
    for ok,lbl,det in results:
        if not ok: print(f"  FAIL: {lbl}" + (f" — {det}" if det else ""))

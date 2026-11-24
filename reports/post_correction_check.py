"""Post-correction verification — confirms all audit findings are resolved."""
import pandas as pd
import re
from pathlib import Path

ROOT = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra")

results = []

def check(label, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((status, label, detail))
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))

print("="*65)
print("POST-CORRECTION VERIFICATION")
print("="*65)

# F1: Repair % threshold
rc = pd.read_csv(ROOT/"reports/rootcause/educational_rootcause_indicators.csv")
repair = rc[rc["indicator"] == "Classrooms Needing Repair"].copy()
repair["value"] = pd.to_numeric(repair["value"], errors="coerce")

sindhudurg_2526 = repair[(repair["district"]=="SINDHUDURG") & (repair["academic_year"]=="2025-26")]
val = float(sindhudurg_2526["value"].iloc[0])
status = str(sindhudurg_2526["status"].iloc[0])
check("F1: Sindhudurg 2025-26 (27.0%) classified CRITICAL not ADEQUATE",
      status == "CRITICAL", f"value={val:.1f}%, status={status}")

repair_adequate_max = float(repair[repair["status"]=="ADEQUATE"]["value"].max())
check("F1: Repair ADEQUATE max is < 20% (threshold_concern)",
      repair_adequate_max < 20, f"max ADEQUATE repair={repair_adequate_max:.2f}%")

repair_concern_rows = len(repair[repair["status"]=="CONCERN"])
repair_critical_rows = len(repair[repair["status"]=="CRITICAL"])
check("F1: Repair CONCERN rows > 0", repair_concern_rows > 0, f"CONCERN rows={repair_concern_rows}")
check("F1: Repair CRITICAL rows > 0", repair_critical_rows > 0, f"CRITICAL rows={repair_critical_rows}")

# W2: Baseline comparison in RF parameters
rf_params = (ROOT/"reports/rf_risk_factor/rf_model_parameters.txt").read_text(encoding="utf-8")
check("W2: Baseline comparison text in rf_model_parameters.txt",
      "77.2%" in rf_params and "Naive baseline" in rf_params)

# W2: Self-confirmation bias documented
check("W2: Self-confirmation bias documented in rf_model_parameters.txt",
      "Self-Confirmation" in rf_params or "self-confirming" in rf_params.lower())

# W4: Documentation causal language
doc = (ROOT/"reports/shikshandarpan_documentation.md").read_text(encoding="utf-8")
causal = doc.lower().count("predict dropout") + doc.lower().count("causes dropout")
check("W4: 'predict dropout' causal claims in documentation = 0",
      causal == 0, f"causal claims found={causal}")
check("W4: 'does not predict dropout' disclaimer present",
      "does not predict" in doc.lower())

# W5: PTR counterintuition note in dashboard
app = (ROOT/"dashboard/app.py").read_text(encoding="utf-8")
check("W5: PTR counterintuition note in Tab 07",
      "32.6" in app or "PTR" in app and "urban" in app.lower())

# Dashboard: 8 tabs, no errors
tab_refs = re.findall(r'with main_tabs\[(\d+)\]', app)
check("Dashboard: all 8 tab blocks present",
      sorted(set(int(x) for x in tab_refs)) == list(range(8)))
check("Dashboard: no Devanagari characters",
      len(re.findall(r'[\u0900-\u097F]', app)) == 0)
check("Dashboard: no hardcoded importance values",
      len(re.findall(r'importance.*=.*0\.\d{4}', app)) == 0)

# Root-cause record count
check("Root-cause: 1440 records (288×5)",
      len(rc) == 1440, f"records={len(rc)}")
dups = rc.duplicated(subset=["district","academic_year","indicator"]).sum()
check("Root-cause: 0 duplicate records", dups == 0, f"dups={dups}")

# Original data files unchanged
import hashlib
def sha256(p):
    h = hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()

ORIGINAL_HASHES = {
    "data/processed/district_year/maharashtra_district_year_shala_score_v1.csv":
        "380f0f640e1cd64fab59f66d45b4f19a299fa4351125d4523559349c0c9cb794",
    "data/processed/district_year/maharashtra_district_year_forecast_2026_27.csv":
        "785865b5a4e99cadba5ecc6bcd796d8ab8f904e2add8deee3f75e51f7385dca8",
    "reports/ml_modeling_baseline/baseline_model_summary.csv":
        "1cc53e7678f471b65fcef22a1299ae2e96a18283680694af79807b0a98bf6561",
    "reports/score_design/shala_score_normalization_parameters_v1.csv":
        "ee51a10e9b6fe2fa8ca3e39774c4fbade15dcf0d182e9e292eaa6f96d86e5eb7",
}
for rel, expected_hash in ORIGINAL_HASHES.items():
    actual = sha256(ROOT/rel)
    check(f"Data integrity: {rel.split('/')[-1]} unchanged",
          actual == expected_hash, f"hash match={'YES' if actual==expected_hash else 'NO'}")

print()
print("="*65)
print("SUMMARY")
print("="*65)
pass_count = sum(1 for r in results if r[0]=="PASS")
fail_count = sum(1 for r in results if r[0]=="FAIL")
print(f"  PASS: {pass_count}")
print(f"  FAIL: {fail_count}")
if fail_count == 0:
    print("  ALL CHECKS PASS — ready for submission")
else:
    print("  REMAINING FAILURES:")
    for status, label, detail in results:
        if status == "FAIL":
            print(f"    - {label}: {detail}")

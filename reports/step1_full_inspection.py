"""
Step 1 — Full workspace inspection script.
READ-ONLY. Prints every fact needed to plan the upgrade.
"""
import sys, json
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra")
MASTER = ROOT / "data/processed/district_year/maharashtra_district_year_shala_score_v1.csv"

print("=" * 70)
print("SECTION 1 — SRC/ MODULE LIST")
print("=" * 70)
for f in sorted(ROOT.glob("src/**/*.py")):
    rel = f.relative_to(ROOT)
    print(f"  {rel}")

print("\n" + "=" * 70)
print("SECTION 2 — MODELS/ AND NOTEBOOKS/ CONTENTS")
print("=" * 70)
for d in ["models", "notebooks", "src/core", "src/explainability"]:
    p = ROOT / d
    files = list(p.rglob("*")) if p.exists() else []
    files = [f for f in files if f.is_file()]
    print(f"  {d}/  ({len(files)} files): {[f.name for f in files]}")

print("\n" + "=" * 70)
print("SECTION 3 — DATASET SHAPE & YEAR/DISTRICT COVERAGE")
print("=" * 70)
df = pd.read_csv(MASTER, low_memory=False)
print(f"  Shape: {df.shape}")
print(f"  Years: {sorted(df['academic_year'].unique())}")
print(f"  Districts ({df['district'].nunique()}): {sorted(df['district'].unique())}")
print(f"  Duplicate (district, year) rows: {df.duplicated(['district','academic_year']).sum()}")

print("\n" + "=" * 70)
print("SECTION 4 — COLUMN AVAILABILITY: SPEC PILLARS")
print("=" * 70)

PILLARS = {
    "Teacher/PTR": [
        "score_teacher_total_derived",
        "ptr_students_per_teacher_raw",
        "male_teachers_sum",
        "female_teachers_sum",
        "transgender_teachers_sum",
        "district_female_teacher_pct",
    ],
    "GPI (Participation)": [
        "enrollment_reported_enrollment_b_component_total",
        "enrollment_reported_enrollment_g_component_total",
        "enrollment_reported_student_total",
        "enrollment_reported_sc_enrollment",
        "enrollment_reported_st_enrollment",
        "enrollment_reported_obc_enrollment",
        "enrollment_reported_general_enrollment",
    ],
    "Infrastructure": [
        "facility_functional_toilet_pct",
        "facility_classrooms_good_condition_pct",
        "facility_classrooms_needing_repair_pct",
        "facility_pucca_building_block_pct",
        "functional_toilet_pct_raw",
        "good_classroom_pct_raw",
    ],
    "Infrastructure_MISSING": [
        "electricity_pct", "drinking_water_pct",
        "library_pct", "ramp_pct",
    ],
    "Digital": [
        "facility_avg_digital_devices_per_reporting_school",
        "facility_total_digital_devices",
        "facility_digital_device_coverage_pct",
        "digital_devices_per_school_raw",
        "district_computer_trained_teacher_pct",
    ],
    "Digital_MISSING": [
        "internet_pct", "internet_connectivity_pct",
    ],
    "Learning_MISSING": [
        "learning_outcome", "ger", "dropout_rate",
        "literacy_rate", "aser_score", "nas_score",
    ],
    "Existing_Shala": [
        "shala_score_v1",
        "pillar_teacher_strength",
        "pillar_infrastructure",
        "pillar_digital_readiness",
        "relative_risk_class_v1",
    ],
}

cols = set(df.columns)
for grp, col_list in PILLARS.items():
    for c in col_list:
        present = c in cols
        null_pct = f"{df[c].isna().mean()*100:.1f}% null" if present else "—"
        status = "✓ PRESENT" if present else "✗ ABSENT"
        print(f"  [{status}] {c:55s} {null_pct}")
    print()

print("=" * 70)
print("SECTION 5 — NUMERIC RANGE CHECKS ON KEY COLUMNS")
print("=" * 70)
CHECK = [
    "ptr_students_per_teacher_raw",
    "facility_functional_toilet_pct",
    "facility_classrooms_good_condition_pct",
    "facility_avg_digital_devices_per_reporting_school",
    "enrollment_reported_enrollment_b_component_total",
    "enrollment_reported_enrollment_g_component_total",
    "shala_score_v1",
]
for c in CHECK:
    if c in cols:
        s = df[c].dropna()
        print(f"  {c[:55]:55s} min={s.min():.2f}  max={s.max():.2f}  null={df[c].isna().sum()}")

print("\n" + "=" * 70)
print("SECTION 6 — REQUIREMENTS.TXT")
print("=" * 70)
req = ROOT / "requirements.txt"
print(req.read_text())

print("=" * 70)
print("SECTION 7 — EXISTING DASHBOARD TABS")
print("=" * 70)
app_text = (ROOT / "dashboard/app.py").read_text(encoding="utf-8", errors="replace")
import re
tabs_match = re.search(r'main_tabs = st\.tabs\(\[(.*?)\]\)', app_text, re.DOTALL)
if tabs_match:
    print(tabs_match.group(0)[:600])

print("\n" + "=" * 70)
print("SECTION 8 — WHAT EXISTING SCORE SCRIPT USES (build_shala_score_v1.py)")
print("=" * 70)
score_src = (ROOT / "src/features/build_shala_score_v1.py").read_text()
# Print just the FEATURES/specs section
for line in score_src.splitlines():
    stripped = line.strip()
    if any(k in stripped for k in ["normalize", "LOWER_IS_BETTER", "HIGHER_IS_BETTER",
                                    "pillar_teacher", "pillar_infra", "pillar_digital",
                                    "shala_score", "mean(axis", "skipna"]):
        print(f"  {line.rstrip()}")

print("\n" + "=" * 70)
print("SECTION 9 — FORECAST OUTPUT COLUMNS AVAILABLE")
print("=" * 70)
fore_path = ROOT / "data/processed/district_year/maharashtra_district_year_forecast_2026_27.csv"
if fore_path.exists():
    fdf = pd.read_csv(fore_path)
    print(f"  Shape: {fdf.shape}")
    print(f"  Columns: {fdf.columns.tolist()}")
else:
    print("  FORECAST FILE NOT FOUND")

print("\n" + "=" * 70)
print("SECTION 10 — DOCS/ DIRECTORY")
print("=" * 70)
docs = ROOT / "docs"
for f in sorted(docs.rglob("*")):
    if f.is_file():
        print(f"  {f.relative_to(ROOT)}")

print("\nINSPECTION COMPLETE")

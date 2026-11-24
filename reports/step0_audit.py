"""STEP 0 — Data audit: every metric displayed vs its source column."""
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra")
hist  = pd.read_csv(ROOT/"data/processed/district_year/maharashtra_district_year_shala_score_v1.csv", low_memory=False)
fore  = pd.read_csv(ROOT/"data/processed/district_year/maharashtra_district_year_forecast_2026_27.csv", low_memory=False)
rc    = pd.read_csv(ROOT/"reports/rootcause/educational_rootcause_indicators.csv", low_memory=False)
rfi   = pd.read_csv(ROOT/"reports/rf_risk_factor/rf_feature_importance.csv", low_memory=False)
kma   = pd.read_csv(ROOT/"reports/kmeans_grouping/kmeans_cluster_assignments.csv", low_memory=False)
norm  = pd.read_csv(ROOT/"reports/score_design/shala_score_normalization_parameters_v1.csv", low_memory=False)

for c in ["shala_score_v1","pillar_teacher_strength","pillar_infrastructure",
          "pillar_digital_readiness","ptr_students_per_teacher_raw",
          "functional_toilet_pct_raw","good_classroom_pct_raw",
          "digital_devices_per_school_raw","enrollment_reported_student_total",
          "score_teacher_total_derived","school_count"]:
    hist[c] = pd.to_numeric(hist[c], errors="coerce")

rows = []
def add(label, file, col, series, unit=""):
    s = pd.to_numeric(series, errors="coerce").dropna()
    rows.append({
        "Display Label": label,
        "Source File": file,
        "Column": col,
        "Min": f"{s.min():.2f}" if len(s) else "N/A",
        "Max": f"{s.max():.2f}" if len(s) else "N/A",
        "Nulls": int(series.isna().sum()),
        "Total": len(series),
        "Unit": unit,
        "OK?": "YES" if len(s) > 0 else "EMPTY"
    })

add("Shala Score",          "shala_score_v1.csv", "shala_score_v1",         hist["shala_score_v1"],         "0–100")
add("Teacher Strength Pillar","shala_score_v1.csv","pillar_teacher_strength", hist["pillar_teacher_strength"], "0–100")
add("Infrastructure Pillar",  "shala_score_v1.csv","pillar_infrastructure",   hist["pillar_infrastructure"],   "0–100")
add("Digital Readiness Pillar","shala_score_v1.csv","pillar_digital_readiness",hist["pillar_digital_readiness"],"0–100")
add("PTR (students/teacher)", "shala_score_v1.csv","ptr_students_per_teacher_raw",hist["ptr_students_per_teacher_raw"],"ratio")
add("Functional Toilet %",    "shala_score_v1.csv","functional_toilet_pct_raw",hist["functional_toilet_pct_raw"],"%")
add("Good Classroom %",       "shala_score_v1.csv","good_classroom_pct_raw",  hist["good_classroom_pct_raw"],  "%")
add("Digital Devices/School", "shala_score_v1.csv","digital_devices_per_school_raw",hist["digital_devices_per_school_raw"],"devices")
add("Enrollment",             "shala_score_v1.csv","enrollment_reported_student_total",hist["enrollment_reported_student_total"],"students")
add("Teachers",               "shala_score_v1.csv","score_teacher_total_derived",hist["score_teacher_total_derived"],"count")
add("School Count",           "shala_score_v1.csv","school_count",            hist["school_count"],            "count")

add("Forecast Enrollment",    "forecast_2026_27.csv","forecast_enrollment",   fore["forecast_enrollment"],    "students")
add("Forecast Teachers",      "forecast_2026_27.csv","forecast_teachers",      fore["forecast_teachers"],      "count")
add("Forecast Toilet %",      "forecast_2026_27.csv","forecast_functional_toilet_pct",fore["forecast_functional_toilet_pct"],"%")
add("Forecast Classroom %",   "forecast_2026_27.csv","forecast_good_classroom_pct",fore["forecast_good_classroom_pct"],"%")
add("Forecast Digital Devs",  "forecast_2026_27.csv","forecast_digital_devices_per_school",fore["forecast_digital_devices_per_school"],"devices")
add("Forecast Shala Score",   "forecast_2026_27.csv","forecast_shala_score_v1",fore["forecast_shala_score_v1"],"0–100")
add("Forecast Perf Band",     "forecast_2026_27.csv","forecast_relative_performance_band",fore["forecast_relative_performance_band"],"text")

rc["value"] = pd.to_numeric(rc["value"], errors="coerce")
add("RC Indicators (all)",    "educational_rootcause_indicators.csv","value",rc["value"],"mixed")

rfi["importance"] = pd.to_numeric(rfi["importance"], errors="coerce")
add("RF Feature Importance",  "rf_feature_importance.csv","importance",rfi["importance"],"0–1")

kma_cluster = pd.to_numeric(kma["cluster"], errors="coerce")
add("K-Means Cluster",        "kmeans_cluster_assignments.csv","cluster",kma_cluster,"0 or 1")

df = pd.DataFrame(rows)
print(df.to_string(index=False))

print("\n--- CHECK 1: Shala Score 0-100? ---")
bad = hist[(hist["shala_score_v1"]<0)|(hist["shala_score_v1"]>100)]
print(f"Out-of-range: {len(bad)} rows | Min={hist['shala_score_v1'].min():.2f} Max={hist['shala_score_v1'].max():.2f}")

print("\n--- CHECK 2: Pillar weights equal? ---")
# S = (T + I + D)/3 — verify sample
sample = hist[["shala_score_v1","pillar_teacher_strength","pillar_infrastructure","pillar_digital_readiness"]].dropna()
sample["computed"] = (sample["pillar_teacher_strength"]+sample["pillar_infrastructure"]+sample["pillar_digital_readiness"])/3
err = (sample["shala_score_v1"] - sample["computed"]).abs()
print(f"Max formula error: {err.max():.6f} (should be ~0)")

print("\n--- CHECK 3: Rank per year ---")
for yr, grp in hist.groupby("academic_year"):
    n_valid = grp["shala_score_v1"].notna().sum()
    print(f"  {yr}: {len(grp)} districts, {n_valid} scored")

print("\n--- CHECK 4: Root-cause 5 indicators per district-year ---")
rc_counts = rc.groupby(["district","academic_year"])["indicator"].count()
bad_rc = rc_counts[rc_counts != 5]
print(f"District-years with !=5 indicators: {len(bad_rc)}")
print(f"Unique indicators: {sorted(rc['indicator'].unique().tolist())}")
print(f"Status values: {sorted(rc['status'].unique().tolist())}")

print("\n--- CHECK 5: Forecast model per target ---")
for col in ["forecast_enrollment_model","forecast_teacher_model","forecast_toilet_model",
            "forecast_classroom_model","forecast_digital_model"]:
    if col in fore.columns:
        print(f"  {col}: {fore[col].iloc[0]}")

print("\n--- CHECK 6: RF target and K-Means k ---")
import json
rf_meta = json.loads((ROOT/"reports/rf_risk_factor/rf_metadata.json").read_text(encoding="utf-8"))
km_meta = json.loads((ROOT/"reports/kmeans_grouping/kmeans_metadata.json").read_text(encoding="utf-8"))
print(f"  RF target: {rf_meta.get('target')}")
print(f"  RF CV R2: {rf_meta.get('cv_mean_r2'):.4f}")
print(f"  K-Means k: {km_meta.get('optimal_k')}, silhouette: {km_meta.get('best_silhouette'):.4f}")
print(f"  K-Means cluster labels: {km_meta.get('cluster_labels')}")

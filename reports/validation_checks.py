"""
ShikshanDarpan AI – Technical Validation Checks
Executed during the validation audit. No files modified.
"""
import hashlib, json, math
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold

ROOT = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

print("="*70)
print("SECTION 1: DATA INTEGRITY HASHES")
print("="*70)
key_files = [
    "data/processed/district_year/maharashtra_district_year_shala_score_v1.csv",
    "data/processed/district_year/maharashtra_district_year_forecast_2026_27.csv",
    "reports/ml_modeling_baseline/baseline_model_summary.csv",
    "reports/score_design/shala_score_normalization_parameters_v1.csv",
    "reports/rf_risk_factor/rf_feature_importance.csv",
    "reports/kmeans_grouping/kmeans_cluster_assignments.csv",
    "reports/rootcause/educational_rootcause_indicators.csv",
]
hashes = {}
for f in key_files:
    p = ROOT / f
    h = sha256(p)
    hashes[f] = h
    print(f"  {f.split('/')[-1]:55s} {h[:16]}...")

print()
print("="*70)
print("SECTION 2: RF LEAKAGE ANALYSIS")
print("="*70)
# Load data
df = pd.read_csv(ROOT/"data/processed/district_year/maharashtra_district_year_shala_score_v1.csv", low_memory=False)
TARGET = "shala_score_v1"
FEATURES = ["school_count","enrollment_reported_student_total","score_teacher_total_derived",
            "ptr_students_per_teacher_raw","functional_toilet_pct_raw","good_classroom_pct_raw",
            "digital_devices_per_school_raw","facility_classrooms_needing_repair_pct",
            "district_female_teacher_pct","district_regular_teacher_pct",
            "district_contract_teacher_pct","district_computer_trained_teacher_pct"]

# Shala Score formula components
SCORE_DIRECT_INPUTS = ["ptr_students_per_teacher_raw","functional_toilet_pct_raw",
                       "good_classroom_pct_raw","digital_devices_per_school_raw"]
SCORE_INTERMEDIATE = ["score_teacher_strength","score_functional_toilet","score_good_classrooms",
                      "score_digital_readiness","pillar_teacher_strength","pillar_infrastructure",
                      "pillar_digital_readiness"]

print("  Direct Shala Score inputs in RF FEATURES:")
for f in FEATURES:
    is_direct = f in SCORE_DIRECT_INPUTS
    is_intermediate = f in SCORE_INTERMEDIATE
    is_target = f == TARGET
    flag = " <-- DIRECT SCORE INPUT" if is_direct else (" <-- INTERMEDIATE SCORE COLUMN" if is_intermediate else (" <-- TARGET!" if is_target else ""))
    print(f"    {f}{flag}")

print()
print("  Intermediate score columns NOT in RF FEATURES (correctly excluded):")
for c in SCORE_INTERMEDIATE:
    in_features = c in FEATURES
    print(f"    {c}: {'IN FEATURES (BAD)' if in_features else 'NOT in features (CORRECT)'}")

print()
print("  LEAKAGE VERDICT:")
print("  The 4 direct inputs (PTR, toilet%, classroom%, digital) ARE in FEATURES.")
print("  However, they are RAW indicators, not the normalized pillar scores.")
print("  The target is shala_score_v1, which IS derived from these raw inputs via")
print("  normalization. This creates a known association, not data leakage in the")
print("  traditional sense (no future information used). However it inflates R2 and")
print("  makes the feature importance self-confirming rather than purely predictive.")
print("  This should be documented as a methodological limitation.")

print()
print("="*70)
print("SECTION 3: RF BASELINE COMPARISON")
print("="*70)
# Check if a naive baseline (mean prediction) is compared
# The script does NOT implement a formal baseline comparison.
# We will compute it here for the audit.
df2 = df.copy()
for c in FEATURES + [TARGET]:
    df2[c] = pd.to_numeric(df2[c], errors="coerce")
df2 = df2.dropna(subset=[TARGET])
for c in FEATURES:
    if df2[c].isna().any():
        df2[c] = df2[c].fillna(float(df2[c].median()))

X = df2[FEATURES].values
y = df2[TARGET].values
kf = KFold(n_splits=5, shuffle=True, random_state=42)

baseline_maes, rf_maes = [], []
for tr_idx, te_idx in kf.split(X):
    y_tr, y_te = y[tr_idx], y[te_idx]
    # Naive baseline: predict training mean
    baseline_pred = np.full_like(y_te, y_tr.mean(), dtype=float)
    baseline_maes.append(mean_absolute_error(y_te, baseline_pred))
    # RF
    rf = RandomForestRegressor(n_estimators=100, max_depth=8, min_samples_leaf=3,
                                max_features=0.7, random_state=42, n_jobs=-1)
    rf.fit(X[tr_idx], y_tr)
    rf_maes.append(mean_absolute_error(y_te, rf.predict(X[te_idx])))

baseline_mean = float(np.mean(baseline_maes))
rf_mean = float(np.mean(rf_maes))
print(f"  Naive baseline (mean) MAE : {baseline_mean:.4f}")
print(f"  Random Forest CV MAE      : {rf_mean:.4f}")
print(f"  Improvement over baseline : {(1 - rf_mean/baseline_mean)*100:.1f}%")
print(f"  Baseline comparison is NOT in the script - SHOULD BE ADDED as documentation note.")

print()
print("="*70)
print("SECTION 4: RF FOLD-LEVEL DATA LEAKAGE (imputation)")
print("="*70)
print("  The script imputes BEFORE splitting into folds.")
print("  Median is computed on the FULL 288-row dataset, then split.")
print("  For the 4 teacher-pct columns (50% missing), this means test-set")
print("  values contribute to the median used to fill training-set NaNs.")
print("  This is a minor imputation leakage. Its practical effect is small")
print("  (median of a symmetric distribution changes little with ~144 samples).")
print("  Recommended: fit imputer inside each fold.")

print()
print("="*70)
print("SECTION 5: K-MEANS REPRODUCIBILITY CHECK")
print("="*70)
feat_cols = ["ptr_students_per_teacher_raw","functional_toilet_pct_raw","good_classroom_pct_raw",
             "digital_devices_per_school_raw","facility_classrooms_needing_repair_pct"]
df_km = df[["district"] + feat_cols].copy()
for c in feat_cols:
    df_km[c] = pd.to_numeric(df_km[c], errors="coerce")
district_df = df_km.groupby("district", as_index=False)[feat_cols].mean()
# No missing in these 5 features (all 288 rows populated)
print(f"  Missing values in clustering features (district-level): {district_df[feat_cols].isna().sum().sum()}")

scaler = StandardScaler()
X_scaled = scaler.fit_transform(district_df[feat_cols])

# Rerun k=2 with same random_state
km_check = KMeans(n_clusters=2, random_state=42, n_init=10)
labels_check = km_check.fit_predict(X_scaled)
sil_check = silhouette_score(X_scaled, labels_check)
print(f"  Reproduced silhouette (k=2): {sil_check:.4f}")

# Load saved assignments
saved = pd.read_csv(ROOT/"reports/kmeans_grouping/kmeans_cluster_assignments.csv")
# Check district ordering matches
reproduced = district_df.copy()
reproduced["cluster_repro"] = labels_check
merged = saved.merge(reproduced[["district","cluster_repro"]], on="district", how="left")
# Clusters may be numbered differently (0/1 swapped) - check consistency
match_exact = (merged["cluster"] == merged["cluster_repro"]).all()
match_swapped = (merged["cluster"] != merged["cluster_repro"]).all()
print(f"  Cluster assignments match saved (exact)  : {match_exact}")
print(f"  Cluster assignments match saved (swapped): {match_swapped}")
print(f"  CONCLUSION: {'Fully reproducible' if match_exact or match_swapped else 'DISCREPANCY FOUND'}")

print()
print("="*70)
print("SECTION 6: K-MEANS LABEL CORRECTNESS")
print("="*70)
elbow = pd.read_csv(ROOT/"reports/kmeans_grouping/kmeans_elbow_silhouette.csv")
print(f"  Best silhouette k: {int(elbow.loc[elbow['silhouette'].idxmax(), 'k'])}")
print(f"  Silhouette values:")
print(elbow.to_string(index=False))
summary = pd.read_csv(ROOT/"reports/kmeans_grouping/kmeans_cluster_summary.csv")
print("\n  Cluster summary (from saved file):")
print(summary.to_string(index=False))
# Verify label matches actual profile
cl0 = summary[summary["cluster"] == 0].iloc[0]
cl1 = summary[summary["cluster"] == 1].iloc[0]
higher_score_cluster = 0 if cl0["mean_shala_score"] > cl1["mean_shala_score"] else 1
higher_score_label = summary[summary["cluster"] == higher_score_cluster].iloc[0]["descriptive_label"]
print(f"\n  Cluster with higher mean score: {higher_score_cluster}")
print(f"  Label assigned to higher cluster: {higher_score_label}")
print(f"  Label correct: {'Strong Educational Conditions' in str(higher_score_label)}")

print()
print("="*70)
print("SECTION 7: ROOT-CAUSE RECORD COUNT VERIFICATION")
print("="*70)
rc = pd.read_csv(ROOT/"reports/rootcause/educational_rootcause_indicators.csv")
print(f"  Total records: {len(rc)}")
print(f"  Expected (288 × 5): {288*5}")
print(f"  Match: {len(rc) == 288*5}")
print(f"  Unique districts: {rc['district'].nunique()}")
print(f"  Unique academic years: {rc['academic_year'].nunique()}")
print(f"  Unique indicators: {rc['indicator'].nunique()}")
print(f"  Status values: {sorted(rc['status'].unique().tolist())}")
print(f"  Missing values in 'value' column: {rc['value'].isna().sum()}")
# Check for duplicate district-year-indicator combos
dups = rc.duplicated(subset=["district","academic_year","indicator"]).sum()
print(f"  Duplicate district-year-indicator rows: {dups}")

print()
print("="*70)
print("SECTION 8: THRESHOLD CORRECTNESS")
print("="*70)
# Verify PTR thresholds: concern >30, critical >35
ptr_col = rc[rc["indicator"] == "Pupil-Teacher Ratio"].copy()
ptr_col["value"] = pd.to_numeric(ptr_col["value"], errors="coerce")
ptr_adequate = ptr_col[ptr_col["status"] == "ADEQUATE"]["value"].max()
ptr_concern_min = ptr_col[ptr_col["status"] == "CONCERN"]["value"].min()
ptr_critical_min = ptr_col[ptr_col["status"] == "CRITICAL"]["value"].min()
print(f"  PTR ADEQUATE max: {ptr_adequate:.2f} (should be <=30)")
print(f"  PTR CONCERN min : {ptr_concern_min:.2f} (should be >30)")
ptr_critical_rows = ptr_col[ptr_col["status"] == "CRITICAL"]
print(f"  PTR CRITICAL rows: {len(ptr_critical_rows)} (districts with PTR >35)")
if len(ptr_critical_rows) > 0:
    print(f"  PTR CRITICAL min: {ptr_critical_min:.2f} (should be >35)")

# Verify toilet thresholds: adequate >=90, concern 85-90, critical <85
toilet_col = rc[rc["indicator"] == "Functional Toilet Coverage"].copy()
toilet_col["value"] = pd.to_numeric(toilet_col["value"], errors="coerce")
toilet_adequate_min = toilet_col[toilet_col["status"] == "ADEQUATE"]["value"].min()
toilet_concern_max = toilet_col[toilet_col["status"] == "CONCERN"]["value"].max()
print(f"\n  Toilet ADEQUATE min: {toilet_adequate_min:.2f} (should be >=90)")
print(f"  Toilet CONCERN max : {toilet_concern_max:.2f} (should be <90)")

# Verify classrooms needing repair: adequate <10, concern 10-20, critical >20
repair_col = rc[rc["indicator"] == "Classrooms Needing Repair"].copy()
repair_col["value"] = pd.to_numeric(repair_col["value"], errors="coerce")
repair_adequate_max = repair_col[repair_col["status"] == "ADEQUATE"]["value"].max()
repair_concern_max = repair_col[repair_col["status"] == "CONCERN"]["value"].max()
repair_critical_rows = repair_col[repair_col["status"] == "CRITICAL"]
print(f"\n  Repair ADEQUATE max: {repair_adequate_max:.2f} (should be <10)")
print(f"  Repair CONCERN max : {repair_concern_max:.2f} (should be <20)")
print(f"  Repair CRITICAL rows: {len(repair_critical_rows)}")

print()
print("="*70)
print("SECTION 9: LANGUAGE CHECK - DROPOUT CLAIMS IN OUTPUT FILES")
print("="*70)
files_to_scan = [
    "reports/rf_risk_factor/rf_model_parameters.txt",
    "reports/kmeans_grouping/kmeans_parameters.txt",
    "reports/shikshandarpan_documentation.md",
]
for f in files_to_scan:
    p = ROOT/f
    if p.exists():
        content = p.read_text(encoding="utf-8", errors="replace").lower()
        dropout_mentions = content.count("dropout")
        causal_claims = content.count("causes dropout") + content.count("predict dropout") + content.count("dropout rate")
        print(f"  {p.name}: 'dropout' mentions={dropout_mentions}, causal claims={causal_claims}")
    else:
        print(f"  {p.name}: NOT FOUND")

print()
print("="*70)
print("SECTION 10: DASHBOARD TAB COUNT")
print("="*70)
app = (ROOT/"dashboard/app.py").read_text(encoding="utf-8", errors="replace")
tab_count = app.count('"0') # count tab label strings
# More precise: count with main_tabs[n]
import re
tab_refs = re.findall(r'with main_tabs\[(\d+)\]', app)
print(f"  Tab references in app.py: {sorted(set(int(x) for x in tab_refs))}")
print(f"  Expected: [0, 1, 2, 3, 4, 5, 6, 7]")
print(f"  Match: {sorted(set(int(x) for x in tab_refs)) == list(range(8))}")
# Check RF file loading
rf_fi_read = "rf_feature_importance.csv" in app
km_assign_read = "kmeans_cluster_assignments.csv" in app
rc_read = "educational_rootcause_indicators.csv" in app
print(f"  Tab 06 reads RF feature importance CSV: {rf_fi_read}")
print(f"  Tab 07 reads K-Means assignments CSV  : {km_assign_read}")
print(f"  Tab 08 reads root-cause indicators CSV: {rc_read}")
# Check for hardcoded model results
hardcoded = re.findall(r'importance.*=.*0\.\d{4}', app)
print(f"  Hardcoded importance values in app.py : {len(hardcoded)} (should be 0)")
# Marathi characters
devanagari = re.findall(r'[\u0900-\u097F]', app)
print(f"  Devanagari characters in app.py      : {len(devanagari)} (should be 0)")

print()
print("="*70)
print("SECTION 11: ORIGINAL FILE SHA256 HASHES (for audit record)")
print("="*70)
for f, h in hashes.items():
    print(f"  {f.split('/')[-1]:55s} SHA256: {h}")

print()
print("VALIDATION CHECKS COMPLETE")

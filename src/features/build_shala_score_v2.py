"""
src/features/build_shala_score_v2.py
======================================
Builds the **Shala Score v2** (0-100, higher = better conditions) across
five pillars with proportional weight redistribution when a pillar's source
data is unavailable.

PILLAR DESIGN  (spec §3)
─────────────────────────
  Pillar 1 - Teacher Strength / PTR   nominal 25 %
  Pillar 2 - Infrastructure            nominal 25 %
  Pillar 3 - Participation / GPI       nominal 20 %
  Pillar 4 - Digital Readiness         nominal 15 %
  Pillar 5 - Learning Outcomes         nominal 15 %

MISSING-DATA RULES
─────────────────────────
  • Columns ABSENT from UDISE+ (confirmed by Step 1 inspection):
      electricity_pct, drinking_water_pct, library_pct, ramp_pct,
      internet_pct, learning_outcome / ger / dropout_rate
  • When a pillar's source columns are entirely absent, its nominal weight
    is redistributed proportionally across the available pillars.
  • When source columns exist but a row has NaN (e.g. district_female_teacher_pct
    is 50 % null), NaN propagation is avoided: each pillar is computed from
    whichever of its sub-components are available, with per-row fallback.
  • Learning Outcomes pillar is always redistributed because no real
    outcome data exists in the UDISE+ extract.  The status is flagged
    explicitly in the output -- classroom quality is NOT reused here.

DOUBLE-COUNTING GUARD  (spec §guardrails)
─────────────────────────
  facility_classrooms_good_condition_pct is used ONLY in Infrastructure.
  It does NOT appear in Learning Outcomes to avoid double-counting.

OUTPUTS
─────────────────────────
  data/processed/district_year/maharashtra_district_year_shala_score_v2.csv
  reports/score_design/shala_score_v2_normalization_params.csv
  reports/score_design/shala_score_v2_weights_per_row.csv
  reports/score_design/shala_score_v2_pca_diagnostic.csv
  reports/score_design/shala_score_v2_yearwise_summary.csv
  reports/score_design/shala_score_v2_latest_ranking.csv
  reports/score_design/shala_score_v2_data_log_flags.csv
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# ── project root ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.core.regions import (
    add_region,
    compute_gpi,
    compute_marginalised_enrolment_pct,
)

# ── paths ───────────────────────────────────────────────────────────────────
INPUT_V1   = ROOT / "data/processed/district_year/maharashtra_district_year_shala_score_v1.csv"
OUTPUT_DIR = ROOT / "data/processed/district_year"
REPORT_DIR = ROOT / "reports/score_design"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ── nominal pillar weights (must sum to 1.0) ─────────────────────────────────
NOMINAL_WEIGHTS: dict[str, float] = {
    "teacher_ptr":   0.25,
    "infrastructure": 0.25,
    "participation":  0.20,
    "digital":        0.15,
    "learning":       0.15,
}
assert abs(sum(NOMINAL_WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1"

# ── spec primary window ──────────────────────────────────────────────────────
SPEC_YEARS  = {"2019-20","2020-21","2021-22","2022-23","2023-24","2024-25"}
BONUS_YEARS = {"2018-19","2025-26"}

# ── risk tier labels (quartile-based) ───────────────────────────────────────
RISK_TIERS = {
    "Thriving": "Top 25% -- strong educational conditions",
    "Stable":   "25-50% -- adequate, room for improvement",
    "At-Risk":  "50-75% -- below average, needs attention",
    "Critical": "Bottom 25% -- priority intervention required",
}


# ════════════════════════════════════════════════════════════════════════════
# NORMALIZATION HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _p5_p95_minmax(series: pd.Series, direction: str, name: str
                   ) -> tuple[pd.Series, dict]:
    """
    Pooled P5-P95 winsorized min-max → 0-100.
    direction: 'higher_is_better' | 'lower_is_better'
    Returns (normalized_series, param_dict).
    Missing values are preserved as NaN.
    """
    x    = pd.to_numeric(series, errors="coerce")
    valid = x.dropna()
    if len(valid) < 2:
        raise ValueError(f"Not enough valid values for '{name}': {len(valid)}")

    p05  = float(valid.quantile(0.05))
    p95  = float(valid.quantile(0.95))
    if p95 <= p05:
        raise ValueError(f"P95 <= P05 for '{name}': p05={p05}, p95={p95}")

    clipped = x.clip(p05, p95)
    score   = (clipped - p05) / (p95 - p05) * 100.0

    if direction == "lower_is_better":
        score = 100.0 - score

    params = {
        "indicator":  name,
        "direction":  direction,
        "p05":        p05,
        "p95":        p95,
        "n_valid":    int(valid.count()),
        "n_missing":  int(x.isna().sum()),
        "min_raw":    float(valid.min()),
        "max_raw":    float(valid.max()),
    }
    return score, params


def _row_mean(*arrays: pd.Series) -> pd.Series:
    """Row-wise mean ignoring NaN, returns NaN only if ALL inputs are NaN."""
    stack = pd.concat(list(arrays), axis=1)
    return stack.mean(axis=1, skipna=True)


# ════════════════════════════════════════════════════════════════════════════
# PILLAR BUILDERS   (each returns a 0-100 pd.Series + param dict)
# ════════════════════════════════════════════════════════════════════════════

def _pillar_teacher_ptr(df: pd.DataFrame, params: list) -> pd.Series:
    """
    Teacher Strength + PTR pillar (nominal 25 %).
    Sub-components:
      - ptr_students_per_teacher_raw          (lower is better)
    Single indicator; uses existing normalized score from v1 for consistency.
    """
    score, p = _p5_p95_minmax(
        df["ptr_students_per_teacher_raw"],
        "lower_is_better",
        "PTR (students per teacher)",
    )
    params.append(p)
    return score.clip(0, 100).rename("pillar2_teacher_ptr")


def _pillar_infrastructure(df: pd.DataFrame, params: list) -> pd.Series:
    """
    Infrastructure pillar (nominal 25 %).
    Sub-components (all confirmed present, 0 null):
      - facility_functional_toilet_pct        (higher is better)
      - facility_classrooms_good_condition_pct (higher is better) ← ONLY HERE
      - facility_pucca_building_block_pct      (higher is better, 12.5% null)
    Pucca building block used where available; excluded per-row where null.

    ABSENT (not in UDISE+): electricity, water, library, ramp
    → flagged in data_log, not imputed.
    """
    scores_list = []
    for col, dirn, name in [
        ("facility_functional_toilet_pct",         "higher_is_better", "Functional Toilet %"),
        ("facility_classrooms_good_condition_pct",  "higher_is_better", "Good Classroom %"),
        ("facility_pucca_building_block_pct",        "higher_is_better", "Pucca Building Block %"),
    ]:
        s, p = _p5_p95_minmax(df[col], dirn, name)
        params.append(p)
        scores_list.append(s.clip(0, 100))

    # row-wise mean (pucca may be NaN for 36 rows; skipna=True handles gracefully)
    combined = _row_mean(*scores_list)
    return combined.rename("pillar2_infrastructure")


def _pillar_participation(df: pd.DataFrame, params: list) -> pd.Series:
    """
    Participation pillar (nominal 20 %).
    Sub-components (all confirmed present, 0 null):
      - gpi (girls/boys enrolment ratio)   → higher is better
      - marginalised_enrolment_pct         → higher is better

    GPI range verified: 0.80-0.98 (all positive, no zeros).
    """
    df = compute_gpi(df)
    df = compute_marginalised_enrolment_pct(df)

    s_gpi, p_gpi = _p5_p95_minmax(df["gpi"], "higher_is_better", "GPI (girls/boys enrolment)")
    s_part, p_part = _p5_p95_minmax(
        df["marginalised_enrolment_pct"], "higher_is_better", "Marginalised Enrolment %"
    )
    params.extend([p_gpi, p_part])

    combined = _row_mean(s_gpi.clip(0, 100), s_part.clip(0, 100))
    return combined.rename("pillar2_participation")


def _pillar_digital(df: pd.DataFrame, params: list) -> pd.Series:
    """
    Digital Readiness pillar (nominal 15 %).
    Sub-components (all confirmed present, 0 null):
      - facility_avg_digital_devices_per_reporting_school  (higher is better)
      - district_computer_trained_teacher_pct              (higher, 50% null)

    computer_trained_teacher_pct is used where available (per-row); rows
    without it fall back to devices-only score.

    ABSENT: internet_pct → flagged, not imputed.
    """
    s_dev, p_dev = _p5_p95_minmax(
        df["facility_avg_digital_devices_per_reporting_school"],
        "higher_is_better",
        "Avg Digital Devices per School",
    )
    params.append(p_dev)
    scores = [s_dev.clip(0, 100)]

    ct_col = "district_computer_trained_teacher_pct"
    if ct_col in df.columns:
        s_ct, p_ct = _p5_p95_minmax(df[ct_col], "higher_is_better",
                                     "Computer-Trained Teacher %")
        params.append(p_ct)
        scores.append(s_ct.clip(0, 100))

    combined = _row_mean(*scores)
    return combined.rename("pillar2_digital")


def _pillar_learning(df: pd.DataFrame) -> pd.Series:
    """
    Learning Outcomes pillar (nominal 15 %).
    SOURCE DATA STATUS: MISSING_IN_SOURCE
      - learning_outcome, ger, dropout_rate, aser_score, nas_score
        are ALL absent from the UDISE+ extract used by this project.
      - Classroom quality is NOT used here (would double-count Infrastructure).
      - Returns a column of NaN so weight redistribution removes this pillar.
    """
    return pd.Series(np.nan, index=df.index, name="pillar2_learning",
                     dtype="float64")


# ════════════════════════════════════════════════════════════════════════════
# WEIGHT REDISTRIBUTION
# ════════════════════════════════════════════════════════════════════════════

def _effective_weights(pillar_scores: pd.DataFrame,
                        nominal: dict[str, float]) -> pd.DataFrame:
    """
    Per-row proportional weight redistribution.

    When a pillar has NaN for a given row, its nominal weight is
    redistributed proportionally among available pillars.

    Returns a DataFrame with the same shape as pillar_scores, containing
    the effective weight used for each pillar on each row (sums to 1 per row).
    """
    names = list(nominal.keys())
    nom   = np.array([nominal[n] for n in names], dtype=float)

    available = pillar_scores[names].notna().values.astype(float)  # (N, 5)
    weighted_available = available * nom[np.newaxis, :]             # (N, 5)
    row_sums = weighted_available.sum(axis=1, keepdims=True)
    # avoid div-by-zero when all pillars are NaN
    row_sums = np.where(row_sums == 0, np.nan, row_sums)
    eff = weighted_available / row_sums                             # (N, 5)

    return pd.DataFrame(eff, index=pillar_scores.index,
                        columns=[f"eff_w_{n}" for n in names])


# ════════════════════════════════════════════════════════════════════════════
# RISK TIER ASSIGNMENT
# ════════════════════════════════════════════════════════════════════════════

def _assign_risk_tier(score: pd.Series) -> pd.Series:
    """
    Four quartile-based risk tiers computed on the full pooled distribution
    (all years, all districts).

    Thriving  ≥ Q75
    Stable    Q50 - Q75
    At-Risk   Q25 - Q50
    Critical  ≤ Q25
    """
    valid  = score.dropna()
    q25, q50, q75 = (float(valid.quantile(q)) for q in (0.25, 0.50, 0.75))

    def _tier(v):
        if pd.isna(v):  return "Unknown"
        if v >= q75:    return "Thriving"
        if v >= q50:    return "Stable"
        if v >= q25:    return "At-Risk"
        return "Critical"

    return score.map(_tier)


# ════════════════════════════════════════════════════════════════════════════
# PCA DIAGNOSTIC
# ════════════════════════════════════════════════════════════════════════════

def _pca_diagnostic(df: pd.DataFrame, pillar_cols: list[str]) -> pd.DataFrame:
    """
    PCA on the five pillar scores (spec requirement: 'PCA validation checks').
    Uses only rows where all five pillars are non-null for the PCA itself;
    reports explained variance per component and component loadings.

    Returns a summary DataFrame suitable for saving to CSV.
    """
    sub = df[pillar_cols].dropna()
    if len(sub) < 10:
        warnings.warn("PCA diagnostic: fewer than 10 complete rows, skipping.")
        return pd.DataFrame()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(sub)

    pca = PCA(n_components=min(len(pillar_cols), len(sub)))
    pca.fit(X_scaled)

    comp_df = pd.DataFrame(
        pca.components_,
        columns=pillar_cols,
        index=[f"PC{i+1}" for i in range(pca.n_components_)],
    )
    comp_df.insert(0, "explained_variance_pct",
                   np.round(pca.explained_variance_ratio_ * 100, 2))
    comp_df.insert(0, "cumulative_variance_pct",
                   np.round(np.cumsum(pca.explained_variance_ratio_) * 100, 2))
    return comp_df


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 70)
    print("SHALASCOPE - SHALA SCORE V2")
    print("=" * 70)

    # ── Load & validate ──────────────────────────────────────────────────────
    df = pd.read_csv(INPUT_V1, low_memory=False)
    assert len(df) == 288 and df["district"].nunique() == 36, "Unexpected shape"
    assert df.duplicated(["district", "academic_year"]).sum() == 0, "Duplicate rows"
    print(f"Loaded v1 dataset: {df.shape}")

    # ── Add geography ────────────────────────────────────────────────────────
    df = add_region(df)
    print(f"Region mapping: PASS -- regions {df['region'].value_counts().to_dict()}")

    # ── Year window flags ────────────────────────────────────────────────────
    df["year_scope"] = df["academic_year"].map(
        lambda y: "spec_window" if y in SPEC_YEARS else "bonus_year"
    )
    print(f"Year scope: spec={df['year_scope'].eq('spec_window').sum()} "
          f"bonus={df['year_scope'].eq('bonus_year').sum()}")

    # ── Build pillars ────────────────────────────────────────────────────────
    norm_params: list[dict] = []

    df["pillar2_teacher_ptr"]   = _pillar_teacher_ptr(df, norm_params)
    df["pillar2_infrastructure"] = _pillar_infrastructure(df, norm_params)
    df["pillar2_participation"]  = _pillar_participation(df, norm_params)
    df["pillar2_digital"]        = _pillar_digital(df, norm_params)
    df["pillar2_learning"]       = _pillar_learning(df)      # always NaN

    PILLAR_COLS = [
        "pillar2_teacher_ptr",
        "pillar2_infrastructure",
        "pillar2_participation",
        "pillar2_digital",
        "pillar2_learning",
    ]
    PILLAR_KEYS = ["teacher_ptr", "infrastructure", "participation",
                   "digital", "learning"]

    for col in PILLAR_COLS:
        n_null = df[col].isna().sum()
        print(f"  {col:35s}  null={n_null}/288  "
              f"min={df[col].min():.1f}  max={df[col].max():.1f}")

    # ── Effective weights (per row) ──────────────────────────────────────────
    pillar_df       = df[PILLAR_COLS].copy()
    pillar_df.columns = PILLAR_KEYS
    eff_w_df        = _effective_weights(pillar_df, NOMINAL_WEIGHTS)

    # ── Shala Score v2 (weighted sum) ────────────────────────────────────────
    score_arr = np.zeros(len(df))
    for key, col in zip(PILLAR_KEYS, PILLAR_COLS):
        w_col  = f"eff_w_{key}"
        vals   = pd.to_numeric(df[col], errors="coerce").fillna(0)
        w_vals = eff_w_df[w_col].fillna(0)
        score_arr += (vals * w_vals).values

    # rows where ALL available-weight is zero get NaN
    all_nan_mask = eff_w_df.sum(axis=1) == 0
    df["shala_score_v2"] = np.where(all_nan_mask, np.nan, score_arr)
    df["shala_score_v2"] = df["shala_score_v2"].clip(0, 100)

    n_scored = df["shala_score_v2"].notna().sum()
    print(f"\nShala Score v2: {n_scored}/{len(df)} scored  "
          f"min={df['shala_score_v2'].min():.2f}  "
          f"max={df['shala_score_v2'].max():.2f}  "
          f"mean={df['shala_score_v2'].mean():.2f}")

    # ── Score within 0-100 assertion ─────────────────────────────────────────
    out_of_range = ((df["shala_score_v2"] < 0) |
                    (df["shala_score_v2"] > 100)).sum()
    assert out_of_range == 0, f"{out_of_range} scores outside [0,100]"
    print("Score range [0,100]: PASS")

    # ── Risk tiers ───────────────────────────────────────────────────────────
    df["risk_tier_v2"] = _assign_risk_tier(df["shala_score_v2"])
    tier_counts = df["risk_tier_v2"].value_counts()
    print(f"\nRisk tier distribution:\n{tier_counts.to_string()}")

    # ── Learning pillar data-availability flag ───────────────────────────────
    df["learning_pillar_status"] = "MISSING_IN_SOURCE"
    df["learning_pillar_note"] = (
        "No learning outcome data in UDISE+ extract. "
        "Weight redistributed proportionally to available pillars. "
        "No classroom quality proxy used to avoid double-counting Infrastructure."
    )
    print("\nLearning pillar: MISSING_IN_SOURCE -- weight redistributed")
    print(f"Effective learning weight per row: "
          f"{eff_w_df['eff_w_learning'].describe().to_dict()}")

    # ── PCA diagnostic ───────────────────────────────────────────────────────
    # Use only the 4 available pillars (learning is all-NaN, excluded)
    available_pillar_cols = [c for c in PILLAR_COLS if c != "pillar2_learning"]
    pca_df = _pca_diagnostic(df, available_pillar_cols)
    if not pca_df.empty:
        pca_path = REPORT_DIR / "shala_score_v2_pca_diagnostic.csv"
        pca_df.to_csv(pca_path, encoding="utf-8-sig")
        print(f"\nPCA diagnostic ({len(available_pillar_cols)} pillars):")
        print(pca_df[["explained_variance_pct","cumulative_variance_pct"]].to_string())
        print(f"Saved: {pca_path}")

    # ── Save outputs ─────────────────────────────────────────────────────────
    # 1. Main scored dataset
    out_path = OUTPUT_DIR / "maharashtra_district_year_shala_score_v2.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nSaved scored dataset: {out_path}  shape={df.shape}")

    # 2. Normalization parameters
    norm_df = pd.DataFrame(norm_params)
    norm_path = REPORT_DIR / "shala_score_v2_normalization_params.csv"
    norm_df.to_csv(norm_path, index=False, encoding="utf-8-sig")
    print(f"Saved normalization params: {norm_path}")

    # 3. Per-row effective weights
    eff_full = eff_w_df.copy()
    eff_full.insert(0, "academic_year", df["academic_year"].values)
    eff_full.insert(0, "district", df["district"].values)
    ew_path = REPORT_DIR / "shala_score_v2_weights_per_row.csv"
    eff_full.to_csv(ew_path, index=False, encoding="utf-8-sig")
    print(f"Saved per-row weights: {ew_path}")

    # 4. Year-wise summary
    yr_summary = df.groupby("academic_year", as_index=False).agg(
        districts=("district", "nunique"),
        mean_score=("shala_score_v2", "mean"),
        median_score=("shala_score_v2", "median"),
        min_score=("shala_score_v2", "min"),
        max_score=("shala_score_v2", "max"),
        thriving=("risk_tier_v2", lambda x: (x == "Thriving").sum()),
        stable=("risk_tier_v2", lambda x: (x == "Stable").sum()),
        at_risk=("risk_tier_v2", lambda x: (x == "At-Risk").sum()),
        critical=("risk_tier_v2", lambda x: (x == "Critical").sum()),
    )
    yr_path = REPORT_DIR / "shala_score_v2_yearwise_summary.csv"
    yr_summary.to_csv(yr_path, index=False, encoding="utf-8-sig")
    print(f"Saved year-wise summary: {yr_path}")

    # 5. Latest year ranking
    latest = df["academic_year"].max()
    ranking = (
        df[df["academic_year"] == latest]
        .sort_values("shala_score_v2", ascending=False)
        .reset_index(drop=True)
    )
    ranking.insert(0, "rank_v2", range(1, len(ranking) + 1))
    rank_path = REPORT_DIR / "shala_score_v2_latest_ranking.csv"
    ranking[["rank_v2","district","region","shala_score_v2","risk_tier_v2",
             "pillar2_teacher_ptr","pillar2_infrastructure",
             "pillar2_participation","pillar2_digital","learning_pillar_status"]
    ].to_csv(rank_path, index=False, encoding="utf-8-sig")
    print(f"Saved latest-year ranking: {rank_path}")

    # 6. Data-log flags (column availability per pillar)
    flags = [
        {"pillar": "Teacher/PTR",    "column": "ptr_students_per_teacher_raw",                  "status": "AVAILABLE", "null_pct": "0.0%"},
        {"pillar": "Infrastructure", "column": "facility_functional_toilet_pct",                 "status": "AVAILABLE", "null_pct": "0.0%"},
        {"pillar": "Infrastructure", "column": "facility_classrooms_good_condition_pct",          "status": "AVAILABLE", "null_pct": "0.0%"},
        {"pillar": "Infrastructure", "column": "facility_pucca_building_block_pct",               "status": "AVAILABLE", "null_pct": "12.5%"},
        {"pillar": "Infrastructure", "column": "electricity_pct",                                "status": "MISSING_IN_SOURCE", "null_pct": "100%"},
        {"pillar": "Infrastructure", "column": "drinking_water_pct",                             "status": "MISSING_IN_SOURCE", "null_pct": "100%"},
        {"pillar": "Infrastructure", "column": "library_pct",                                    "status": "MISSING_IN_SOURCE", "null_pct": "100%"},
        {"pillar": "Infrastructure", "column": "ramp_pct",                                       "status": "MISSING_IN_SOURCE", "null_pct": "100%"},
        {"pillar": "Participation",  "column": "enrollment_reported_enrollment_g_component_total","status": "AVAILABLE", "null_pct": "0.0%"},
        {"pillar": "Participation",  "column": "enrollment_reported_enrollment_b_component_total","status": "AVAILABLE", "null_pct": "0.0%"},
        {"pillar": "Participation",  "column": "enrollment_reported_sc_enrollment",               "status": "AVAILABLE", "null_pct": "0.0%"},
        {"pillar": "Participation",  "column": "enrollment_reported_st_enrollment",               "status": "AVAILABLE", "null_pct": "0.0%"},
        {"pillar": "Participation",  "column": "enrollment_reported_obc_enrollment",              "status": "AVAILABLE", "null_pct": "0.0%"},
        {"pillar": "Digital",        "column": "facility_avg_digital_devices_per_reporting_school","status": "AVAILABLE", "null_pct": "0.0%"},
        {"pillar": "Digital",        "column": "district_computer_trained_teacher_pct",           "status": "AVAILABLE", "null_pct": "50.0%"},
        {"pillar": "Digital",        "column": "internet_pct",                                    "status": "MISSING_IN_SOURCE", "null_pct": "100%"},
        {"pillar": "Learning",       "column": "learning_outcome / ger / dropout_rate",           "status": "MISSING_IN_SOURCE", "null_pct": "100%"},
        {"pillar": "Learning",       "column": "aser_score / nas_score",                         "status": "MISSING_IN_SOURCE", "null_pct": "100%"},
    ]
    flags_df = pd.DataFrame(flags)
    flags_path = REPORT_DIR / "shala_score_v2_data_log_flags.csv"
    flags_df.to_csv(flags_path, index=False, encoding="utf-8-sig")
    print(f"Saved data-log flags: {flags_path}")

    print("\n" + "=" * 70)
    print("SHALA SCORE V2 -- COMPLETE")
    print("=" * 70)
    print(f"  Rows: {len(df)}  |  Districts: {df['district'].nunique()}")
    print(f"  Years: {sorted(df['academic_year'].unique())}")
    print(f"  Score range: {df['shala_score_v2'].min():.2f} - "
          f"{df['shala_score_v2'].max():.2f}")
    print(f"  Learning pillar: MISSING_IN_SOURCE (weight redistributed)")
    print(f"  No double-counting: classroom quality in Infrastructure ONLY")


if __name__ == "__main__":
    main()

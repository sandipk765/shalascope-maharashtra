
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "data" / "processed" / "district_year"
    / "maharashtra_district_year_shala_score_v1.csv"
)

OUT = ROOT / "reports" / "ml_readiness"
PAIR_OUT = OUT / "training_pairs"

PILLARS = [
    "pillar_teacher_strength",
    "pillar_infrastructure",
    "pillar_digital_readiness"
]

CORRELATION_PAIRS = [
    ("pillar_teacher_strength", "pillar_infrastructure"),
    ("pillar_teacher_strength", "pillar_digital_readiness"),
    ("pillar_infrastructure", "pillar_digital_readiness")
]

# These are current-year features used to forecast next-year targets.
BASE_FEATURES = [
    "school_count",
    "enrollment_reported_student_total",
    "score_teacher_total_derived",
    "functional_toilet_pct_raw",
    "good_classroom_pct_raw",
    "digital_devices_per_school_raw"
]

TARGETS = {
    "student_enrollment": {
        "target": "enrollment_reported_student_total",
        "description": "Next academic year's reported student total"
    },
    "teacher_forecast": {
        "target": "score_teacher_total_derived",
        "description": "Next academic year's teacher headcount"
    },
    "infrastructure_toilet": {
        "target": "functional_toilet_pct_raw",
        "description": "Next academic year's functional toilet percentage"
    },
    "infrastructure_classroom": {
        "target": "good_classroom_pct_raw",
        "description": "Next academic year's good-condition classroom percentage"
    },
    "digital_readiness": {
        "target": "digital_devices_per_school_raw",
        "description": "Next academic year's digital devices per reporting school"
    }
}


def save_csv(data, path):
    data.to_csv(path, index=False, encoding="utf-8-sig")
    print("Saved:", path)


def safe_corr(a, b, method="pearson"):
    pair = pd.concat(
        [
            pd.to_numeric(a, errors="coerce"),
            pd.to_numeric(b, errors="coerce")
        ],
        axis=1
    ).dropna()

    if len(pair) < 3:
        return np.nan, len(pair)

    if pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return np.nan, len(pair)

    return pair.iloc[:, 0].corr(
        pair.iloc[:, 1],
        method=method
    ), len(pair)


def main():

    if not INPUT.exists():
        raise FileNotFoundError(f"Input not found: {INPUT}")

    OUT.mkdir(parents=True, exist_ok=True)
    PAIR_OUT.mkdir(parents=True, exist_ok=True)

    print("=" * 68)
    print("SHALASCOPE - ML TARGET & FEATURE READINESS AUDIT")
    print("=" * 68)

    df = pd.read_csv(INPUT, low_memory=False)

    required = [
        "academic_year",
        "district",
        *PILLARS,
        *BASE_FEATURES
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(f"Required columns missing: {missing}")

    df["academic_year"] = df["academic_year"].astype(str)
    df["district"] = df["district"].astype(str)

    df["year_start"] = pd.to_numeric(
        df["academic_year"].str.extract(r"^(\d{4})")[0],
        errors="coerce"
    )

    if df["year_start"].isna().any():
        raise ValueError("Could not parse academic year")

    numeric_columns = list(set(
        PILLARS + BASE_FEATURES + [
            "ptr_students_per_teacher_raw",
            "shala_score_v1"
        ]
    ))

    for c in numeric_columns:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # --------------------------------------------------
    # STEP 1: STRUCTURAL VALIDATION
    # --------------------------------------------------

    if len(df) != 288:
        raise ValueError(f"Expected 288 rows, found {len(df)}")

    if df["district"].nunique() != 36:
        raise ValueError("Expected 36 districts")

    if df["academic_year"].nunique() != 8:
        raise ValueError("Expected 8 academic years")

    if df.duplicated(["district", "year_start"]).any():
        raise ValueError("Duplicate district-year keys")

    print("Dataset validation: PASS")
    print("Rows:", len(df))
    print("Districts:", df["district"].nunique())
    print("Years:", df["academic_year"].nunique())

    # --------------------------------------------------
    # STEP 2: YEAR-WISE PILLAR CORRELATION
    # --------------------------------------------------

    print("\nYEAR-WISE PILLAR CORRELATION")

    yearly_corr = []

    for year, group in df.groupby("academic_year"):

        row = {
            "academic_year": year,
            "districts": group["district"].nunique()
        }

        for left, right in CORRELATION_PAIRS:

            corr, n = safe_corr(
                group[left],
                group[right]
            )

            row[f"{left}_vs_{right}_pearson"] = corr
            row[f"{left}_vs_{right}_n"] = n

        yearly_corr.append(row)

    yearly_corr_df = pd.DataFrame(yearly_corr)

    save_csv(
        yearly_corr_df,
        OUT / "pillar_correlation_yearwise.csv"
    )

    # --------------------------------------------------
    # STEP 3: DISTRICT-WISE 8-YEAR CORRELATION
    # --------------------------------------------------

    print("\nDISTRICT-WISE PILLAR CORRELATION")

    district_corr = []

    for district, group in df.groupby("district"):

        row = {"district": district}

        for left, right in CORRELATION_PAIRS:

            corr, n = safe_corr(
                group[left],
                group[right]
            )

            row[f"{left}_vs_{right}_pearson"] = corr
            row[f"{left}_vs_{right}_n"] = n

        district_corr.append(row)

    district_corr_df = pd.DataFrame(district_corr)

    save_csv(
        district_corr_df,
        OUT / "pillar_correlation_districtwise.csv"
    )

    # --------------------------------------------------
    # STEP 4: CORRELATION OF YEAR-TO-YEAR CHANGES
    # --------------------------------------------------

    print("\nYEAR-TO-YEAR CHANGE CORRELATION")

    change_df = df.sort_values(
        ["district", "year_start"]
    ).copy()

    for pillar in PILLARS:
        change_df[f"change_{pillar}"] = (
            change_df.groupby("district")[pillar].diff()
        )

    change_rows = []

    for left, right in CORRELATION_PAIRS:

        corr, n = safe_corr(
            change_df[f"change_{left}"],
            change_df[f"change_{right}"]
        )

        change_rows.append({
            "pillar_pair": f"{left} vs {right}",
            "first_difference_pearson": corr,
            "valid_district_year_changes": n,
            "interpretation": (
                "Correlation of annual changes; "
                "not a causal relationship"
            )
        })

    save_csv(
        pd.DataFrame(change_rows),
        OUT / "pillar_change_correlation.csv"
    )

    # --------------------------------------------------
    # STEP 5: TARGET COVERAGE BY YEAR
    # --------------------------------------------------

    print("\nTARGET AVAILABILITY BY YEAR")

    target_coverage = []

    for task, info in TARGETS.items():

        target = info["target"]

        for year, group in df.groupby("academic_year"):

            values = pd.to_numeric(
                group[target],
                errors="coerce"
            )

            valid = values.dropna()

            target_coverage.append({
                "prediction": task,
                "academic_year": year,
                "target_column": target,
                "districts": len(group),
                "available_targets": int(valid.count()),
                "missing_targets": int(values.isna().sum()),
                "coverage_pct": round(
                    values.notna().mean() * 100, 2
                ),
                "minimum": (
                    valid.min() if len(valid) else np.nan
                ),
                "median": (
                    valid.median() if len(valid) else np.nan
                ),
                "maximum": (
                    valid.max() if len(valid) else np.nan
                )
            })

    save_csv(
        pd.DataFrame(target_coverage),
        OUT / "ml_target_coverage_by_year.csv"
    )

    # --------------------------------------------------
    # STEP 6: ONE-YEAR-AHEAD TRAINING PAIRS
    # --------------------------------------------------

    print("\nBUILDING ONE-YEAR-AHEAD TRAINING PAIRS")

    data = df.sort_values(
        ["district", "year_start"]
    ).copy()

    grouped = data.groupby("district", sort=False)

    data["next_year_start"] = grouped["year_start"].shift(-1)

    for task, info in TARGETS.items():

        target = info["target"]
        target_next = f"target_next_{task}"

        data[target_next] = grouped[target].shift(-1)

    all_pair_summaries = []
    feature_coverage = []

    task_frames = {}

    for task, info in TARGETS.items():

        target_next = f"target_next_{task}"

        pair = data[
            [
                "district",
                "academic_year",
                "year_start",
                "next_year_start",
                *BASE_FEATURES,
                target_next
            ]
        ].copy()

        # Only consecutive academic years are valid one-year-ahead pairs.
        pair = pair[
            pair["next_year_start"] == pair["year_start"] + 1
        ].copy()

        pair = pair.rename(columns={
            "academic_year": "feature_academic_year",
            "year_start": "feature_year_start",
            "next_year_start": "target_year_start",
            target_next: "target_next_year"
        })

        pair["target_academic_year"] = (
            pair["target_year_start"].astype("Int64").astype(str)
        )

        pair["prediction"] = task

        target_valid = pair["target_next_year"].notna()

        # District and year are preserved as categorical/time features.
        numeric_features = BASE_FEATURES

        complete_features = pair[numeric_features].notna().all(axis=1)

        model_ready = target_valid & complete_features

        pair["target_available"] = target_valid
        pair["features_complete"] = complete_features
        pair["model_ready"] = model_ready

        all_file = PAIR_OUT / f"{task}_pairs_all.csv"
        ready_file = PAIR_OUT / f"{task}_pairs_complete.csv"

        save_csv(pair, all_file)
        save_csv(pair[model_ready].copy(), ready_file)

        task_frames[task] = pair

        all_pair_summaries.append({
            "prediction": task,
            "target_column": info["target"],
            "description": info["description"],
            "possible_transitions": len(pair),
            "target_available": int(target_valid.sum()),
            "complete_feature_rows": int(complete_features.sum()),
            "model_ready_rows": int(model_ready.sum()),
            "rows_excluded": int((~model_ready).sum()),
            "status": (
                "READY FOR MODEL DESIGN"
                if model_ready.sum() > 0
                else "INSUFFICIENT COMPLETE DATA"
            )
        })

        for feature in ["district", "feature_year_start"] + numeric_features:

            if feature == "district":
                coverage = pair[feature].notna().mean() * 100
            elif feature == "feature_year_start":
                coverage = pair[feature].notna().mean() * 100
            else:
                coverage = pair[feature].notna().mean() * 100

            feature_coverage.append({
                "prediction": task,
                "feature": feature,
                "available_rows": int(pair[feature].notna().sum()),
                "transition_rows": len(pair),
                "coverage_pct": round(coverage, 2)
            })

    save_csv(
        pd.DataFrame(all_pair_summaries),
        OUT / "ml_training_pair_summary.csv"
    )

    save_csv(
        pd.DataFrame(feature_coverage),
        OUT / "ml_candidate_feature_coverage.csv"
    )

    # --------------------------------------------------
    # STEP 7: FIVE-MODEL METHODOLOGY NOTES
    # --------------------------------------------------

    notes = [
        "SHALASCOPE - ML READINESS NOTES",
        "",
        "1. Forecast next academic year using current-year information.",
        "2. Do not use future-year predictors.",
        "3. Keep district as a categorical feature.",
        "4. Use chronological / rolling-origin validation.",
        "5. Compare against persistence and simple trend baselines.",
        "6. Fit imputers, scalers, encoders and feature selection on training folds only.",
        "7. Do not use full-period V1 pillar scores as leakage-free ML features.",
        "8. Future Shala Score should be recomputed from predicted raw pillars.",
        "9. Infrastructure has two outcomes: functional toilets and good-condition classrooms.",
        "10. Missing targets must not be replaced with zero.",
        "11. Only one-year-ahead transitions with consecutive academic years are retained.",
        "12. District-year panel has at most 252 one-year-ahead pairs per target.",
        "",
        "Candidate model families:",
        "- Baseline: Persistence (next year = current year)",
        "- Baseline: District-wise linear trend",
        "- Regularized Linear Regression / Ridge",
        "- Random Forest (small depth, conservative tuning)",
        "- Gradient Boosting only if rolling validation justifies it",
        "",
        "Deep learning is not recommended for 288 district-year observations.",
        "These are forecasting candidates, not yet validated production models."
    ]

    notes_path = OUT / "ml_modeling_methodology_notes.txt"
    notes_path.write_text("\n".join(notes), encoding="utf-8")

    # --------------------------------------------------
    # STEP 8: PRINT FINAL SUMMARY
    # --------------------------------------------------

    print("\n" + "=" * 68)
    print("ML TARGET & FEATURE AUDIT RESULT")
    print("=" * 68)

    print("YEAR-WISE CORRELATION:")
    print(yearly_corr_df.to_string(index=False))

    print("\nPILLAR CHANGE CORRELATION:")
    print(pd.DataFrame(change_rows).to_string(index=False))

    print("\nTRAINING PAIR SUMMARY:")
    print(pd.DataFrame(all_pair_summaries).to_string(index=False))

    print("\nOUTPUT FOLDER:")
    print(OUT)

    print("\nSTATUS: AUDIT COMPLETED")
    print("No ML model has been trained yet.")


if __name__ == "__main__":
    main()

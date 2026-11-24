
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

INPUT = ROOT / "data/processed/district_year/maharashtra_district_year_final_master.csv"
OUT_DATA = ROOT / "data/processed/district_year"
OUT_REPORTS = ROOT / "reports/score_design"


def normalize(values, name, source, direction):
    """Pooled P5-P95 winsorized min-max; preserves missing values."""
    x = pd.to_numeric(values, errors="coerce")
    valid = x.dropna()

    if len(valid) < 2:
        raise ValueError(f"Not enough values to normalize: {name}")

    p05, p95 = float(valid.quantile(.05)), float(valid.quantile(.95))

    if not np.isfinite(p05) or not np.isfinite(p95) or p95 <= p05:
        raise ValueError(f"Invalid P5/P95 range for {name}: {p05}, {p95}")

    clipped = x.clip(p05, p95)
    score = (clipped - p05) / (p95 - p05) * 100

    if direction == "LOWER_IS_BETTER":
        score = 100 - score
    elif direction != "HIGHER_IS_BETTER":
        raise ValueError(f"Unknown direction: {direction}")

    info = {
        "indicator": name,
        "source_or_formula": source,
        "direction": direction,
        "valid_records": int(valid.count()),
        "missing_records": int(x.isna().sum()),
        "minimum": float(valid.min()),
        "p05": p05,
        "median": float(valid.median()),
        "p95": p95,
        "maximum": float(valid.max()),
        "values_clipped_below_p05": int((valid < p05).sum()),
        "values_clipped_above_p95": int((valid > p95).sum()),
        "normalization": "Pooled P5-P95 winsorized min-max across all 8 years"
    }

    return score, info


def main():

    if not INPUT.exists():
        raise FileNotFoundError(f"Input not found: {INPUT}")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_REPORTS.mkdir(parents=True, exist_ok=True)

    print("=" * 68)
    print("SHALASCOPE - SHALA SCORE V1")
    print("=" * 68)

    df = pd.read_csv(INPUT, low_memory=False)

    required = [
        "academic_year",
        "district",
        "school_count",
        "enrollment_reported_student_total",
        "male_teachers_sum",
        "female_teachers_sum",
        "transgender_teachers_sum",
        "facility_functional_toilet_pct",
        "facility_classrooms_good_condition_pct",
        "facility_avg_digital_devices_per_reporting_school"
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # --------------------------------------------------
    # STEP 1: DATASET VALIDATION
    # --------------------------------------------------

    if (
        len(df) != 288
        or df["district"].nunique() != 36
        or df["academic_year"].nunique() != 8
    ):
        raise ValueError(
            f"Unexpected dataset shape: rows={len(df)}, "
            f"districts={df['district'].nunique()}, "
            f"years={df['academic_year'].nunique()}"
        )

    if df[["academic_year", "district"]].isna().any().any():
        raise ValueError("Missing district or academic-year key")

    if df.duplicated(["academic_year", "district"]).any():
        raise ValueError("Duplicate District-Year records detected")

    year_counts = df.groupby("academic_year")["district"].nunique()

    if not (year_counts == 36).all():
        raise ValueError("One or more academic years do not contain 36 districts")

    print("Structure validation: PASS (288 records, 36 districts, 8 years)")

    numeric_cols = required[3:]

    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # --------------------------------------------------
    # STEP 2: TEACHER TOTAL
    # --------------------------------------------------

    teacher_cols = [
        "male_teachers_sum",
        "female_teachers_sum",
        "transgender_teachers_sum"
    ]

    df["score_teacher_total_derived"] = df[teacher_cols].sum(
        axis=1,
        min_count=3
    )

    # Reconcile with official total wherever available.
    recon = {
        "records_compared": 0,
        "exact_matches": 0,
        "mismatches": 0,
        "max_absolute_difference": np.nan,
        "status": "NOT AVAILABLE"
    }

    if "teacher_total_sum" in df.columns:

        official = pd.to_numeric(
            df["teacher_total_sum"],
            errors="coerce"
        )

        mask = (
            official.notna()
            & df["score_teacher_total_derived"].notna()
        )

        if mask.any():

            diff = (
                official[mask]
                - df.loc[mask, "score_teacher_total_derived"]
            ).abs()

            exact = int(np.isclose(diff, 0, atol=1e-9).sum())

            recon = {
                "records_compared": int(len(diff)),
                "exact_matches": exact,
                "mismatches": int(len(diff) - exact),
                "max_absolute_difference": float(diff.max()),
                "status": "PASS" if exact == len(diff)
                          else "REVIEW REQUIRED"
            }

    pd.DataFrame([recon]).to_csv(
        OUT_REPORTS / "shala_score_teacher_reconciliation_v1.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"Teacher-total cross-check: "
        f"{recon['exact_matches']}/{recon['records_compared']} exact matches"
    )

    # --------------------------------------------------
    # STEP 3: RAW INDICATORS
    # --------------------------------------------------

    df["ptr_students_per_teacher_raw"] = (
        df["enrollment_reported_student_total"]
        / df["score_teacher_total_derived"].where(
            df["score_teacher_total_derived"] > 0
        )
    )

    df["functional_toilet_pct_raw"] = (
        df["facility_functional_toilet_pct"]
    )

    df["good_classroom_pct_raw"] = (
        df["facility_classrooms_good_condition_pct"]
    )

    df["digital_devices_per_school_raw"] = (
        df["facility_avg_digital_devices_per_reporting_school"]
    )

    raw_cols = [
        "ptr_students_per_teacher_raw",
        "functional_toilet_pct_raw",
        "good_classroom_pct_raw",
        "digital_devices_per_school_raw"
    ]

    for c in raw_cols:
        if (df[c].dropna() < 0).any():
            raise ValueError(f"Negative values found in {c}")

    for c in [
        "functional_toilet_pct_raw",
        "good_classroom_pct_raw"
    ]:

        bad = df[c].notna() & ~df[c].between(0, 100)

        if bad.any():
            raise ValueError(
                f"Percentage outside 0-100 in {c}: {int(bad.sum())}"
            )

    # --------------------------------------------------
    # STEP 4: NORMALIZATION
    # --------------------------------------------------

    specs = [

        (
            "Students per teacher",
            "ptr_students_per_teacher_raw",
            "score_teacher_strength",
            "LOWER_IS_BETTER",
            "Enrollment total / (Male + Female + Transgender teachers)"
        ),

        (
            "Functional toilet percentage",
            "functional_toilet_pct_raw",
            "score_functional_toilet",
            "HIGHER_IS_BETTER",
            "facility_functional_toilet_pct"
        ),

        (
            "Good-condition classroom percentage",
            "good_classroom_pct_raw",
            "score_good_classrooms",
            "HIGHER_IS_BETTER",
            "facility_classrooms_good_condition_pct"
        ),

        (
            "Digital devices per reporting school",
            "digital_devices_per_school_raw",
            "score_digital_readiness",
            "HIGHER_IS_BETTER",
            "facility_avg_digital_devices_per_reporting_school"
        )
    ]

    params = []

    for name, raw, score_col, direction, source in specs:

        df[score_col], info = normalize(
            df[raw],
            name,
            source,
            direction
        )

        params.append(info)

    # --------------------------------------------------
    # STEP 5: PILLAR SCORE CALCULATION
    # --------------------------------------------------

    # Pillar 1: Teacher Strength
    df["pillar_teacher_strength"] = (
        df["score_teacher_strength"]
    )

    # Pillar 2: Infrastructure
    # Both indicators receive 50% weight.
    df["pillar_infrastructure"] = df[
        [
            "score_functional_toilet",
            "score_good_classrooms"
        ]
    ].mean(axis=1, skipna=False)

    # Pillar 3: Digital Readiness
    df["pillar_digital_readiness"] = (
        df["score_digital_readiness"]
    )

    # --------------------------------------------------
    # STEP 6: FINAL SHALA SCORE
    # --------------------------------------------------

    pillar_cols = [
        "pillar_teacher_strength",
        "pillar_infrastructure",
        "pillar_digital_readiness"
    ]

    df["shala_score_v1"] = df[pillar_cols].mean(
        axis=1,
        skipna=False
    )

    df["score_input_completeness_pct"] = (
        df[raw_cols].notna().mean(axis=1) * 100
    )

    df["score_status"] = np.where(
        df["shala_score_v1"].notna(),
        "COMPLETE",
        "NOT SCORED - MISSING INPUT"
    )

    # --------------------------------------------------
    # STEP 7: RELATIVE RISK CLASSIFICATION
    # --------------------------------------------------

    scores = df["shala_score_v1"].dropna()

    if len(scores) < 4:
        raise ValueError("Insufficient scores for quartile classification")

    q25, q50, q75 = [
        float(scores.quantile(q))
        for q in (.25, .50, .75)
    ]

    def risk_band(value):

        if pd.isna(value):
            return "NOT SCORED"

        if value <= q25:
            return "CRITICAL"

        if value <= q50:
            return "HIGH"

        if value <= q75:
            return "MODERATE"

        return "LOW"

    df["relative_risk_class_v1"] = (
        df["shala_score_v1"].apply(risk_band)
    )

    # --------------------------------------------------
    # STEP 8: CONTEXT-ONLY INDICATORS
    # --------------------------------------------------

    # These are excluded from Shala Score V1.
    student_total = df["enrollment_reported_student_total"].where(
        df["enrollment_reported_student_total"] > 0
    )

    context_ratios = [
        (
            "free_textbooks_beneficiaries_total_sum",
            "context_textbook_beneficiaries_per_100_students"
        ),
        (
            "free_uniform_beneficiaries_total_sum",
            "context_uniform_beneficiaries_per_100_students"
        )
    ]

    for source, target in context_ratios:

        if source in df.columns:

            df[target] = (
                pd.to_numeric(df[source], errors="coerce")
                / student_total * 100
            )

    # --------------------------------------------------
    # STEP 9: SAVE MAIN DATASET
    # --------------------------------------------------

    main_output = (
        OUT_DATA / "maharashtra_district_year_shala_score_v1.csv"
    )

    df.to_csv(
        main_output,
        index=False,
        encoding="utf-8-sig"
    )

    pd.DataFrame(params).to_csv(
        OUT_REPORTS / "shala_score_normalization_parameters_v1.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # STEP 10: SAVE RISK THRESHOLDS
    # --------------------------------------------------

    thresholds = pd.DataFrame([

        {
            "class": "CRITICAL",
            "rule": f"Score <= {q25:.4f}",
            "meaning": "Lowest historical score quartile"
        },

        {
            "class": "HIGH",
            "rule": f"{q25:.4f} < Score <= {q50:.4f}",
            "meaning": "Second-lowest historical score quartile"
        },

        {
            "class": "MODERATE",
            "rule": f"{q50:.4f} < Score <= {q75:.4f}",
            "meaning": "Third historical score quartile"
        },

        {
            "class": "LOW",
            "rule": f"Score > {q75:.4f}",
            "meaning": "Highest historical score quartile"
        }

    ])

    thresholds.to_csv(
        OUT_REPORTS / "shala_score_relative_risk_thresholds_v1.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # STEP 11: YEAR-WISE SUMMARY
    # --------------------------------------------------

    year_summary = df.groupby(
        "academic_year",
        as_index=False
    ).agg(

        districts=("district", "nunique"),
        records=("district", "size"),

        mean_score=("shala_score_v1", "mean"),
        median_score=("shala_score_v1", "median"),
        min_score=("shala_score_v1", "min"),
        max_score=("shala_score_v1", "max"),

        mean_teacher_score=("pillar_teacher_strength", "mean"),
        mean_infrastructure_score=("pillar_infrastructure", "mean"),
        mean_digital_score=("pillar_digital_readiness", "mean"),

        scored_records=("shala_score_v1", "count")
    )

    year_summary.to_csv(
        OUT_REPORTS / "shala_score_yearwise_summary_v1.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # STEP 12: LATEST YEAR DISTRICT RANKING
    # --------------------------------------------------

    latest_year = sorted(
        df["academic_year"].astype(str).unique()
    )[-1]

    latest = df[
        df["academic_year"].astype(str) == latest_year
    ].sort_values(
        "shala_score_v1",
        ascending=False,
        na_position="last"
    ).copy()

    latest.insert(
        0,
        "score_rank_v1",
        range(1, len(latest) + 1)
    )

    latest.to_csv(
        OUT_REPORTS / "shala_score_latest_year_district_ranking_v1.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # STEP 13: METHODOLOGY REPORT
    # --------------------------------------------------

    methodology = pd.DataFrame([

        [
            "Scope",
            "Relative school-conditions index; not a government score or learning-outcome measure"
        ],

        [
            "Teacher Strength",
            "Students per teacher; lower is better; teacher total derived from sex-wise teacher totals"
        ],

        [
            "Infrastructure",
            "Mean of normalized functional toilet % and good-condition classroom %"
        ],

        [
            "Digital Readiness",
            "Average digital devices per reporting school; not proof of functionality or student access"
        ],

        [
            "Pillar weights",
            "Teacher 33.33%; Infrastructure 33.33%; Digital 33.33%"
        ],

        [
            "Infrastructure sub-weights",
            "Functional toilets 50%; good-condition classrooms 50%"
        ],

        [
            "Normalization",
            "Pooled P5-P95 winsorized min-max across 288 District-Year rows"
        ],

        [
            "Missing data",
            "No zero imputation; missing required inputs prevent affected score calculation"
        ],

        [
            "Student support",
            "Textbook/uniform ratios are context-only until eligible-student denominator is verified"
        ],

        [
            "Governance",
            "Inspections/visits remain context-only; more visits are not automatically better outcomes"
        ],

        [
            "Relative risk classes",
            "Pooled historical score quartiles; descriptive classes, not predicted probabilities"
        ],

        [
            "Future ML validation",
            "Fit normalization on training data only to prevent temporal data leakage"
        ]

    ], columns=["item", "method"])

    methodology.to_csv(
        OUT_REPORTS / "shala_score_methodology_v1.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # STEP 14: FINAL RESULT
    # --------------------------------------------------

    print("\n" + "=" * 68)
    print("SHALA SCORE V1 - BUILD RESULT")
    print("=" * 68)

    print("Rows:", len(df))
    print("Districts:", df["district"].nunique())
    print("Academic years:", df["academic_year"].nunique())

    print("Scores calculated:", int(df["shala_score_v1"].notna().sum()))
    print("Scores missing:", int(df["shala_score_v1"].isna().sum()))

    print(
        f"Mean score: {df['shala_score_v1'].mean():.2f}"
    )

    print(
        f"Median score: {df['shala_score_v1'].median():.2f}"
    )

    print(
        f"Quartile thresholds: Q25={q25:.2f}, "
        f"Q50={q50:.2f}, Q75={q75:.2f}"
    )

    print("\nRelative class counts:")
    print(
        df["relative_risk_class_v1"].value_counts().to_string()
    )

    print("\nYear-wise summary:")
    print(year_summary.to_string(index=False))

    print("\nMAIN OUTPUT:")
    print(main_output)

    print("\nREPORT FOLDER:")
    print(OUT_REPORTS)

    print("\nSTATUS: PASS")
    print(
        "Note: relative descriptive index only; "
        "not learning performance or risk probability."
    )


if __name__ == "__main__":
    main()

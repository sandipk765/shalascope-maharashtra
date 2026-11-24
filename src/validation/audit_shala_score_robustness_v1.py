
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "data" / "processed" / "district_year"
    / "maharashtra_district_year_shala_score_v1.csv"
)

OUT = ROOT / "reports" / "score_design" / "robustness_audit_v1"

PILLARS = [
    "pillar_teacher_strength",
    "pillar_infrastructure",
    "pillar_digital_readiness"
]

INDICATORS = [
    {
        "name": "Students per Teacher",
        "raw": "ptr_students_per_teacher_raw",
        "score": "score_teacher_strength",
        "direction": "LOWER_IS_BETTER"
    },
    {
        "name": "Functional Toilets",
        "raw": "functional_toilet_pct_raw",
        "score": "score_functional_toilet",
        "direction": "HIGHER_IS_BETTER"
    },
    {
        "name": "Good Condition Classrooms",
        "raw": "good_classroom_pct_raw",
        "score": "score_good_classrooms",
        "direction": "HIGHER_IS_BETTER"
    },
    {
        "name": "Digital Devices per School",
        "raw": "digital_devices_per_school_raw",
        "score": "score_digital_readiness",
        "direction": "HIGHER_IS_BETTER"
    }
]

WEIGHTS = {
    "equal_33_33_33": [1/3, 1/3, 1/3],
    "teacher_50_25_25": [0.50, 0.25, 0.25],
    "infrastructure_25_50_25": [0.25, 0.50, 0.25],
    "digital_25_25_50": [0.25, 0.25, 0.50],
    "balanced_40_40_20": [0.40, 0.40, 0.20]
}

NORMALIZATION_METHODS = {
    "P5_P95": (0.05, 0.95),
    "P1_P99": (0.01, 0.99),
    "P2_5_P97_5": (0.025, 0.975)
}


def save_report(data, filename):
    path = OUT / filename
    data.to_csv(path, index=False, encoding="utf-8-sig")
    print("Saved:", path.name)


def normalize(values, lower_q, upper_q, direction):
    x = pd.to_numeric(values, errors="coerce")
    valid = x.dropna()

    if len(valid) < 2:
        raise ValueError("Insufficient valid values for normalization")

    low = float(valid.quantile(lower_q))
    high = float(valid.quantile(upper_q))

    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        raise ValueError(
            f"Invalid normalization range: low={low}, high={high}"
        )

    clipped = x.clip(lower=low, upper=high)
    result = (clipped - low) / (high - low) * 100

    if direction == "LOWER_IS_BETTER":
        result = 100 - result

    return result, low, high


def make_ranks(group, score_column):
    return group[score_column].rank(
        method="min",
        ascending=False
    )


def spearman_corr(a, b):
    return pd.Series(a).rank().corr(
        pd.Series(b).rank(),
        method="pearson"
    )


def calculate_risk_class(score, q25, q50, q75):
    if pd.isna(score):
        return "NOT SCORED"
    if score <= q25:
        return "CRITICAL"
    if score <= q50:
        return "HIGH"
    if score <= q75:
        return "MODERATE"
    return "LOW"


def main():

    if not INPUT.exists():
        raise FileNotFoundError(f"Dataset not found: {INPUT}")

    OUT.mkdir(parents=True, exist_ok=True)

    print("=" * 68)
    print("SHALASCOPE - SCORE ROBUSTNESS AUDIT V1")
    print("=" * 68)

    df = pd.read_csv(INPUT, low_memory=False)

    required = [
        "academic_year",
        "district",
        "shala_score_v1",
        *PILLARS
    ]

    required += [x["raw"] for x in INDICATORS]
    required += [x["score"] for x in INDICATORS]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["academic_year"] = df["academic_year"].astype(str)
    df["district"] = df["district"].astype(str)

    for c in required:
        if c not in ["academic_year", "district"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # --------------------------------------------------
    # 1. STRUCTURAL VALIDATION
    # --------------------------------------------------

    checks = []

    def add_check(name, actual, expected, passed, note=""):
        checks.append({
            "check": name,
            "actual": actual,
            "expected": expected,
            "status": "PASS" if passed else "REVIEW",
            "notes": note
        })

    duplicate_count = int(
        df.duplicated(["academic_year", "district"]).sum()
    )

    year_counts = (
        df.groupby("academic_year")["district"].nunique()
    )

    add_check(
        "Total District-Year rows",
        len(df),
        288,
        len(df) == 288
    )

    add_check(
        "Unique districts",
        df["district"].nunique(),
        36,
        df["district"].nunique() == 36
    )

    add_check(
        "Academic years",
        df["academic_year"].nunique(),
        8,
        df["academic_year"].nunique() == 8
    )

    add_check(
        "Duplicate District-Year records",
        duplicate_count,
        0,
        duplicate_count == 0
    )

    add_check(
        "36 districts per year",
        bool((year_counts == 36).all()),
        True,
        bool((year_counts == 36).all())
    )

    add_check(
        "Complete final scores",
        int(df["shala_score_v1"].notna().sum()),
        len(df),
        df["shala_score_v1"].notna().all()
    )

    print("\nSTRUCTURAL VALIDATION")
    print("Rows:", len(df))
    print("Districts:", df["district"].nunique())
    print("Academic years:", df["academic_year"].nunique())
    print("Duplicate keys:", duplicate_count)

    # --------------------------------------------------
    # 2. RECHECK NORMALIZATION AND SCORE FORMULA
    # --------------------------------------------------

    print("\nRECHECKING SCORE CALCULATIONS")

    recomputed_components = {}
    normalization_rows = []

    for item in INDICATORS:

        score, low, high = normalize(
            df[item["raw"]],
            0.05,
            0.95,
            item["direction"]
        )

        recomputed_components[item["score"]] = score

        actual = df[item["score"]]
        difference = (actual - score).abs()

        max_difference = (
            float(difference.max())
            if difference.notna().any()
            else np.nan
        )

        normalization_rows.append({
            "indicator": item["name"],
            "raw_column": item["raw"],
            "score_column": item["score"],
            "p05_recalculated": low,
            "p95_recalculated": high,
            "maximum_score_difference": max_difference,
            "records_compared": int(difference.notna().sum()),
            "status": (
                "PASS"
                if difference.notna().all()
                and max_difference <= 0.000001
                else "REVIEW"
            )
        })

    save_report(
        pd.DataFrame(normalization_rows),
        "score_normalization_recalculation_v1.csv"
    )

    # Recalculate all 3 pillars.
    teacher_recalc = recomputed_components[
        "score_teacher_strength"
    ]

    infrastructure_recalc = pd.concat(
        [
            recomputed_components["score_functional_toilet"],
            recomputed_components["score_good_classrooms"]
        ],
        axis=1
    ).mean(axis=1, skipna=False)

    digital_recalc = recomputed_components[
        "score_digital_readiness"
    ]

    final_recalc = pd.concat(
        [
            teacher_recalc,
            infrastructure_recalc,
            digital_recalc
        ],
        axis=1
    ).mean(axis=1, skipna=False)

    formula_checks = [
        (
            "Teacher pillar formula",
            df["pillar_teacher_strength"],
            teacher_recalc
        ),
        (
            "Infrastructure pillar formula",
            df["pillar_infrastructure"],
            infrastructure_recalc
        ),
        (
            "Digital pillar formula",
            df["pillar_digital_readiness"],
            digital_recalc
        ),
        (
            "Final Shala Score formula",
            df["shala_score_v1"],
            final_recalc
        )
    ]

    for name, actual, expected in formula_checks:

        diff = (actual - expected).abs()
        max_diff = float(diff.max())

        add_check(
            name,
            max_diff,
            "<= 0.000001",
            bool(max_diff <= 0.000001),
            "Recalculated from raw indicators"
        )

    add_check(
        "Pillar scores within 0-100",
        bool(
            df[PILLARS].ge(0).all().all()
            and df[PILLARS].le(100).all().all()
        ),
        True,
        bool(
            df[PILLARS].ge(0).all().all()
            and df[PILLARS].le(100).all().all()
        )
    )

    add_check(
        "Final score within 0-100",
        bool(
            df["shala_score_v1"].between(0, 100).all()
        ),
        True,
        bool(
            df["shala_score_v1"].between(0, 100).all()
        )
    )

    # --------------------------------------------------
    # 3. TEACHER RECONCILIATION
    # --------------------------------------------------

    teacher_report = []

    gender_columns = [
        "male_teachers_sum",
        "female_teachers_sum",
        "transgender_teachers_sum"
    ]

    if all(c in df.columns for c in gender_columns):

        derived = df[gender_columns].sum(
            axis=1,
            min_count=3
        )

        if "teacher_total_sum" in df.columns:

            official = pd.to_numeric(
                df["teacher_total_sum"],
                errors="coerce"
            )

            valid = derived.notna() & official.notna()

            diff = (derived[valid] - official[valid]).abs()

            exact = int(np.isclose(diff, 0, atol=1e-9).sum())

            teacher_report.append({
                "compared_records": int(valid.sum()),
                "exact_matches": exact,
                "mismatches": int(valid.sum() - exact),
                "max_absolute_difference": (
                    float(diff.max()) if len(diff) else np.nan
                ),
                "status": (
                    "PASS" if len(diff) and exact == len(diff)
                    else "REVIEW"
                )
            })

    if teacher_report:
        save_report(
            pd.DataFrame(teacher_report),
            "score_teacher_reconciliation_robustness_v1.csv"
        )

    # --------------------------------------------------
    # 4. PILLAR CORRELATION
    # --------------------------------------------------

    print("\nPILLAR CORRELATION ANALYSIS")

    correlation_rows = []

    for pillar in PILLARS:

        correlation_rows.append({
            "pillar": pillar,
            "records": int(
                df[[pillar, "shala_score_v1"]].dropna().shape[0]
            ),
            "pearson_with_final_score": df[pillar].corr(
                df["shala_score_v1"],
                method="pearson"
            ),
            "spearman_with_final_score": df[pillar].corr(
                df["shala_score_v1"],
                method="spearman"
            ),
            "note": (
                "Part-whole correlation: pillar is included in final score"
            )
        })

    save_report(
        pd.DataFrame(correlation_rows),
        "score_pillar_correlation_v1.csv"
    )

    corr_matrix = df[
        PILLARS + ["shala_score_v1"]
    ].corr(method="pearson")

    corr_matrix.to_csv(
        OUT / "score_pillar_correlation_matrix_v1.csv",
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # 5. WEIGHT SENSITIVITY - ALL 288 RECORDS
    # --------------------------------------------------

    print("\nWEIGHT SENSITIVITY ANALYSIS")

    weight_year_rows = []
    weight_latest_rows = []

    scenario_scores = {}

    latest_year = sorted(
        df["academic_year"].unique()
    )[-1]

    latest_source = df[
        df["academic_year"] == latest_year
    ].copy()

    latest_ranking = latest_source[
        ["academic_year", "district", "shala_score_v1"]
        + PILLARS
    ].copy()

    latest_ranking["current_rank"] = make_ranks(
        latest_ranking,
        "shala_score_v1"
    ).astype(int)

    latest_ranking["current_risk_band"] = (
        latest_ranking["shala_score_v1"]
        .apply(lambda x: calculate_risk_class(
            x,
            df["shala_score_v1"].quantile(.25),
            df["shala_score_v1"].quantile(.50),
            df["shala_score_v1"].quantile(.75)
        ))
    )

    all_year_records = []

    for scenario, weights in WEIGHTS.items():

        new_score = (
            df[PILLARS].to_numpy()
            * np.array(weights)
        ).sum(axis=1)

        score_column = f"score_{scenario}"
        df[score_column] = new_score

        scenario_scores[scenario] = new_score

        # Year-wise ranking sensitivity.
        for year, group in df.groupby("academic_year"):

            current_rank = make_ranks(
                group,
                "shala_score_v1"
            )

            alternative_rank = make_ranks(
                group,
                score_column
            )

            rank_change = (
                alternative_rank - current_rank
            ).abs()

            corr = spearman_corr(
                current_rank,
                alternative_rank
            )

            current_top = set(
                group.loc[current_rank <= 5, "district"]
            )

            alt_top = set(
                group.loc[alternative_rank <= 5, "district"]
            )

            current_bottom = set(
                group.loc[current_rank >= 32, "district"]
            )

            alt_bottom = set(
                group.loc[alternative_rank >= 32, "district"]
            )

            weight_year_rows.append({
                "scenario": scenario,
                "academic_year": year,
                "teacher_weight": weights[0],
                "infrastructure_weight": weights[1],
                "digital_weight": weights[2],
                "spearman_vs_current": corr,
                "mean_absolute_rank_change": rank_change.mean(),
                "maximum_absolute_rank_change": rank_change.max(),
                "top_5_overlap": len(current_top & alt_top),
                "bottom_5_overlap": len(current_bottom & alt_bottom),
                "mean_scenario_score": new_score[group.index].mean()
            })

            for idx in group.index:
                all_year_records.append({
                    "academic_year": year,
                    "district": df.loc[idx, "district"],
                    "scenario": scenario,
                    "scenario_score": new_score[idx],
                    "current_score": df.loc[idx, "shala_score_v1"],
                    "score_difference": (
                        new_score[idx] - df.loc[idx, "shala_score_v1"]
                    ),
                    "current_rank": int(current_rank.loc[idx]),
                    "scenario_rank": int(alternative_rank.loc[idx]),
                    "absolute_rank_change": int(rank_change.loc[idx])
                })

        # Latest-year rank scenario.
        latest_ranking[f"{scenario}_score"] = (
            new_score[latest_source.index]
        )

        latest_ranking[f"{scenario}_rank"] = (
            latest_ranking[f"{scenario}_score"]
            .rank(method="min", ascending=False)
            .astype(int)
        )

        alt_latest = latest_ranking[
            ["district", f"{scenario}_score", f"{scenario}_rank"]
        ]

        for _, row in alt_latest.iterrows():
            weight_latest_rows.append({
                "scenario": scenario,
                "district": row["district"],
                "scenario_score": row[f"{scenario}_score"],
                "scenario_rank": row[f"{scenario}_rank"]
            })

    save_report(
        pd.DataFrame(weight_year_rows),
        "score_weight_sensitivity_by_year_v1.csv"
    )

    save_report(
        pd.DataFrame(all_year_records),
        "score_weight_sensitivity_all_district_years_v1.csv"
    )

    save_report(
        latest_ranking.sort_values("current_rank"),
        "score_weight_sensitivity_latest_year_v1.csv"
    )

    save_report(
        pd.DataFrame(weight_latest_rows),
        "score_weight_sensitivity_latest_scenarios_long_v1.csv"
    )

    # --------------------------------------------------
    # 6. NORMALIZATION SENSITIVITY
    # --------------------------------------------------

    print("\nNORMALIZATION SENSITIVITY ANALYSIS")

    norm_summary = []
    norm_year_summary = []

    current_rank_all = (
        df.groupby("academic_year")["shala_score_v1"]
        .rank(method="min", ascending=False)
    )

    for method, (low_q, high_q) in NORMALIZATION_METHODS.items():

        component_scores = {}

        for item in INDICATORS:

            result, low, high = normalize(
                df[item["raw"]],
                low_q,
                high_q,
                item["direction"]
            )

            component_scores[item["score"]] = result

        teacher = component_scores["score_teacher_strength"]

        infrastructure = pd.concat(
            [
                component_scores["score_functional_toilet"],
                component_scores["score_good_classrooms"]
            ],
            axis=1
        ).mean(axis=1, skipna=False)

        digital = component_scores["score_digital_readiness"]

        alternative_score = pd.concat(
            [teacher, infrastructure, digital],
            axis=1
        ).mean(axis=1, skipna=False)

        difference = (
            alternative_score - df["shala_score_v1"]
        ).abs()

        # Same year ranking comparison.
        method_ranks = (
            pd.DataFrame({
                "academic_year": df["academic_year"],
                "score": alternative_score
            })
            .groupby("academic_year")["score"]
            .rank(method="min", ascending=False)
        )

        rank_change = (
            method_ranks - current_rank_all
        ).abs()

        norm_summary.append({
            "normalization_method": method,
            "lower_quantile": low_q,
            "upper_quantile": high_q,
            "mean_score": alternative_score.mean(),
            "median_score": alternative_score.median(),
            "mean_absolute_score_change": difference.mean(),
            "maximum_absolute_score_change": difference.max(),
            "mean_absolute_rank_change": rank_change.mean(),
            "maximum_absolute_rank_change": rank_change.max(),
            "spearman_rank_correlation": spearman_corr(
                current_rank_all,
                method_ranks
            )
        })

        for year in sorted(df["academic_year"].unique()):

            mask = df["academic_year"] == year

            norm_year_summary.append({
                "normalization_method": method,
                "academic_year": year,
                "mean_alternative_score": alternative_score[mask].mean(),
                "mean_absolute_score_change": difference[mask].mean(),
                "maximum_absolute_rank_change": rank_change[mask].max(),
                "spearman_rank_correlation": spearman_corr(
                    current_rank_all[mask],
                    method_ranks[mask]
                )
            })

    save_report(
        pd.DataFrame(norm_summary),
        "score_normalization_sensitivity_v1.csv"
    )

    save_report(
        pd.DataFrame(norm_year_summary),
        "score_normalization_sensitivity_by_year_v1.csv"
    )

    # --------------------------------------------------
    # 7. OUTLIER REVIEW
    # --------------------------------------------------

    print("\nOUTLIER REVIEW")

    outlier_rows = []
    outlier_details = []

    for item in INDICATORS:

        raw = df[item["raw"]]
        valid = raw.dropna()

        p05 = float(valid.quantile(.05))
        p95 = float(valid.quantile(.95))

        below = raw < p05
        above = raw > p95

        outlier_rows.append({
            "indicator": item["name"],
            "records": len(valid),
            "minimum": valid.min(),
            "p05": p05,
            "median": valid.median(),
            "p95": p95,
            "maximum": valid.max(),
            "below_p05_count": int(below.sum()),
            "above_p95_count": int(above.sum()),
            "missing_count": int(raw.isna().sum())
        })

        for idx in df.index[below.fillna(False)]:
            outlier_details.append({
                "academic_year": df.loc[idx, "academic_year"],
                "district": df.loc[idx, "district"],
                "indicator": item["name"],
                "raw_value": raw.loc[idx],
                "p05": p05,
                "p95": p95,
                "tail": "BELOW_P05"
            })

        for idx in df.index[above.fillna(False)]:
            outlier_details.append({
                "academic_year": df.loc[idx, "academic_year"],
                "district": df.loc[idx, "district"],
                "indicator": item["name"],
                "raw_value": raw.loc[idx],
                "p05": p05,
                "p95": p95,
                "tail": "ABOVE_P95"
            })

    save_report(
        pd.DataFrame(outlier_rows),
        "score_outlier_review_v1.csv"
    )

    save_report(
        pd.DataFrame(outlier_details),
        "score_outlier_flagged_records_v1.csv"
    )

    # --------------------------------------------------
    # 8. RISK BAND SENSITIVITY
    # --------------------------------------------------

    risk_rows = []

    for scenario, values in scenario_scores.items():

        s = pd.Series(values, index=df.index)

        q25 = float(s.quantile(.25))
        q50 = float(s.quantile(.50))
        q75 = float(s.quantile(.75))

        classes = s.apply(
            lambda x: calculate_risk_class(x, q25, q50, q75)
        )

        counts = classes.value_counts()

        risk_rows.append({
            "scenario": scenario,
            "q25": q25,
            "q50": q50,
            "q75": q75,
            "critical_records": int(counts.get("CRITICAL", 0)),
            "high_records": int(counts.get("HIGH", 0)),
            "moderate_records": int(counts.get("MODERATE", 0)),
            "low_records": int(counts.get("LOW", 0)),
            "interpretation": "Relative historical quartile bands"
        })

    save_report(
        pd.DataFrame(risk_rows),
        "score_risk_band_sensitivity_v1.csv"
    )

    # --------------------------------------------------
    # 9. LATEST YEAR PILLAR PROFILE
    # --------------------------------------------------

    latest_profile = latest_source[
        [
            "academic_year",
            "district",
            "shala_score_v1",
            "pillar_teacher_strength",
            "pillar_infrastructure",
            "pillar_digital_readiness",
            "ptr_students_per_teacher_raw",
            "functional_toilet_pct_raw",
            "good_classroom_pct_raw",
            "digital_devices_per_school_raw"
        ]
    ].copy()

    latest_profile = latest_profile.sort_values(
        "shala_score_v1",
        ascending=False
    )

    latest_profile.insert(
        0,
        "score_rank",
        range(1, len(latest_profile) + 1)
    )

    save_report(
        latest_profile,
        "score_latest_year_pillar_profile_v1.csv"
    )

    # --------------------------------------------------
    # 10. SAVE INTEGRITY REPORT
    # --------------------------------------------------

    check_df = pd.DataFrame(checks)

    save_report(
        check_df,
        "score_robustness_integrity_v1.csv"
    )

    # --------------------------------------------------
    # 11. FINAL SUMMARY
    # --------------------------------------------------

    print("\n" + "=" * 68)
    print("SHALASCOPE - ROBUSTNESS AUDIT RESULT")
    print("=" * 68)

    print("Total records:", len(df))
    print("Districts:", df["district"].nunique())
    print("Academic years:", df["academic_year"].nunique())
    print("Latest year:", latest_year)

    print("\nINTEGRITY CHECKS")
    print(check_df.to_string(index=False))

    print("\nPILLAR CORRELATION")
    print(
        pd.DataFrame(correlation_rows).to_string(index=False)
    )

    print("\nWEIGHT SENSITIVITY - YEAR-WISE")
    print(
        pd.DataFrame(weight_year_rows).to_string(index=False)
    )

    print("\nNORMALIZATION SENSITIVITY")
    print(
        pd.DataFrame(norm_summary).to_string(index=False)
    )

    print("\nOUTLIER REVIEW")
    print(
        pd.DataFrame(outlier_rows).to_string(index=False)
    )

    failed = int((check_df["status"] != "PASS").sum())

    print("\nReports saved in:")
    print(OUT)

    print("\nIntegrity checks needing review:", failed)

    if failed == 0:
        print("\nSTATUS: PASS")
    else:
        print("\nSTATUS: REVIEW REQUIRED")

    print(
        "\nNOTE: This is a descriptive score robustness audit, "
        "not an ML prediction or causal validation."
    )


if __name__ == "__main__":
    main()

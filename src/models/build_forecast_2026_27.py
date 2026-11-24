
from pathlib import Path
import warnings

import numpy as np
import pandas as pd


# ============================================================
# SHALASCOPE MAHARASHTRA
# 2026-27 DISTRICT FORECAST ENGINE
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

# Main historical dataset
SCORE_INPUT = (
    ROOT / "data" / "processed" / "district_year"
    / "maharashtra_district_year_shala_score_v1.csv"
)

# Baseline model evaluation results
MODEL_SUMMARY_INPUT = (
    ROOT / "reports" / "ml_modeling_baseline"
    / "baseline_model_summary.csv"
)

OOF_INPUT = (
    ROOT / "reports" / "ml_modeling_baseline"
    / "baseline_oof_predictions.csv"
)

# Digital district trend training pairs
DIGITAL_PAIRS_INPUT = (
    ROOT / "reports" / "ml_readiness"
    / "training_pairs"
    / "digital_readiness_pairs_complete.csv"
)

# Frozen historical Shala Score normalization parameters
NORMALIZATION_INPUT = (
    ROOT / "reports" / "score_design"
    / "shala_score_normalization_parameters_v1.csv"
)

# Output paths
MAIN_OUTPUT = (
    ROOT / "data" / "processed" / "district_year"
    / "maharashtra_district_year_forecast_2026_27.csv"
)

OUT = ROOT / "reports" / "forecast_2026_27"

OUT.mkdir(parents=True, exist_ok=True)


# ============================================================
# 1. FORECAST TASK CONFIGURATION
# ============================================================

TASKS = {
    "student_enrollment": {
        "source_column": "enrollment_reported_student_total",
        "model_target": "target_next_year",
        "model": "persistence",
        "output_column": "forecast_enrollment",
        "lower_column": "forecast_enrollment_lower_p10",
        "upper_column": "forecast_enrollment_upper_p90",
        "lower_bound": 0,
        "upper_bound": None,
        "unit": "students"
    },

    "teacher_forecast": {
        "source_column": "score_teacher_total_derived",
        "model_target": "target_next_year",
        "model": "persistence",
        "output_column": "forecast_teachers",
        "lower_column": "forecast_teachers_lower_p10",
        "upper_column": "forecast_teachers_upper_p90",
        "lower_bound": 0,
        "upper_bound": None,
        "unit": "teachers"
    },

    "infrastructure_toilet": {
        "source_column": "functional_toilet_pct_raw",
        "model_target": "target_next_year",
        "model": "persistence",
        "output_column": "forecast_functional_toilet_pct",
        "lower_column": "forecast_toilet_lower_p10",
        "upper_column": "forecast_toilet_upper_p90",
        "lower_bound": 0,
        "upper_bound": 100,
        "unit": "percentage points"
    },

    "infrastructure_classroom": {
        "source_column": "good_classroom_pct_raw",
        "model_target": "target_next_year",
        "model": "persistence",
        "output_column": "forecast_good_classroom_pct",
        "lower_column": "forecast_classroom_lower_p10",
        "upper_column": "forecast_classroom_upper_p90",
        "lower_bound": 0,
        "upper_bound": 100,
        "unit": "percentage points"
    },

    "digital_readiness": {
        "source_column": "digital_devices_per_school_raw",
        "model_target": "target_next_year",
        "model": "district_linear_trend",
        "output_column": "forecast_digital_devices_per_school",
        "lower_column": "forecast_digital_lower_p10",
        "upper_column": "forecast_digital_upper_p90",
        "lower_bound": 0,
        "upper_bound": None,
        "unit": "devices per reporting school"
    }
}


# ============================================================
# 2. FILE VALIDATION
# ============================================================

def check_file(path):

    if not path.exists():
        raise FileNotFoundError(
            f"Required input file not found:\n{path}"
        )


def load_csv(path):

    check_file(path)

    return pd.read_csv(
        path,
        low_memory=False
    )


# ============================================================
# 3. NUMERIC CONSTRAINTS
# ============================================================

def apply_bounds(values, low, high):

    values = np.asarray(
        values,
        dtype=float
    )

    values = np.where(
        np.isfinite(values),
        values,
        np.nan
    )

    if high is None:
        return np.maximum(values, low)

    return np.clip(
        values,
        low,
        high
    )


# ============================================================
# 4. SELECT MODELS USING OOF VALIDATION
# ============================================================

def select_models(summary):

    required = [
        "prediction",
        "model",
        "mae",
        "skill_vs_persistence",
        "validation_folds_won_vs_persistence",
        "total_validation_folds"
    ]

    missing = [
        c for c in required
        if c not in summary.columns
    ]

    if missing:
        raise ValueError(
            f"Model summary missing columns: {missing}"
        )

    summary = summary.copy()

    for column in [
        "mae",
        "skill_vs_persistence",
        "validation_folds_won_vs_persistence",
        "total_validation_folds"
    ]:
        summary[column] = pd.to_numeric(
            summary[column],
            errors="coerce"
        )

    selected = []

    for task in TASKS:

        group = summary[
            summary["prediction"] == task
        ].copy()

        if group.empty:
            raise ValueError(
                f"No model evaluation results for {task}"
            )

        persistence = group[
            group["model"] == "persistence"
        ]

        if len(persistence) != 1:
            raise ValueError(
                f"Expected one Persistence row for {task}"
            )

        # Conservative selection criterion:
        # positive skill against persistence and >=4/5 folds won.
        eligible = group[
            (group["model"] != "persistence")
            & (group["model"] != "district_historical_mean")
            & (group["skill_vs_persistence"] > 0)
            & (
                group["validation_folds_won_vs_persistence"] >= 4
            )
            & (group["total_validation_folds"] == 5)
        ].copy()

        if eligible.empty:

            winner = persistence.iloc[0]
            reason = (
                "No complex model met the positive-skill "
                "and four-of-five-fold stability rule; "
                "Persistence selected."
            )

        else:

            winner = eligible.sort_values(
                ["mae", "skill_vs_persistence"],
                ascending=[True, False]
            ).iloc[0]

            reason = (
                "Positive MAE skill and at least "
                "four validation folds won against Persistence."
            )

        selected.append({
            "prediction": task,
            "selected_model": winner["model"],
            "selected_mae": winner["mae"],
            "skill_vs_persistence": winner["skill_vs_persistence"],
            "validation_folds_won": int(
                winner["validation_folds_won_vs_persistence"]
            ),
            "total_validation_folds": int(
                winner["total_validation_folds"]
            ),
            "selection_reason": reason
        })

    result = pd.DataFrame(selected)

    result.to_csv(
        OUT / "forecast_model_selection_2026_27.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return dict(
        zip(
            result["prediction"],
            result["selected_model"]
        )
    ), result


# ============================================================
# 5. EMPIRICAL HISTORICAL ERROR RANGES
# ============================================================

def build_error_ranges(oof, selected_models):

    required = [
        "prediction",
        "model",
        "residual",
        "actual",
        "predicted",
        "validation_target_year"
    ]

    missing = [
        c for c in required
        if c not in oof.columns
    ]

    if missing:
        raise ValueError(
            f"OOF file missing columns: {missing}"
        )

    error_info = {}
    rows = []

    for task, config in TASKS.items():

        selected_model = selected_models[task]

        subset = oof[
            (oof["prediction"] == task)
            & (oof["model"] == selected_model)
        ].copy()

        subset["residual"] = pd.to_numeric(
            subset["residual"],
            errors="coerce"
        )

        residuals = subset["residual"].dropna()

        if len(residuals) < 30:
            raise ValueError(
                f"Insufficient historical OOF residuals "
                f"for {task}: {len(residuals)}"
            )

        q10 = float(residuals.quantile(0.10))
        q50 = float(residuals.quantile(0.50))
        q90 = float(residuals.quantile(0.90))

        error_info[task] = {
            "q10": q10,
            "q50": q50,
            "q90": q90,
            "count": len(residuals)
        }

        rows.append({
            "prediction": task,
            "selected_model": selected_model,
            "oof_residual_records": len(residuals),
            "residual_p10": q10,
            "residual_p50": q50,
            "residual_p90": q90,
            "unit": config["unit"],
            "method": (
                "Historical signed OOF residual P10-P90. "
                "Empirical error range, not a formal "
                "or guaranteed prediction interval."
            )
        })

    report = pd.DataFrame(rows)

    report.to_csv(
        OUT / "forecast_empirical_error_ranges_2026_27.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return error_info


# ============================================================
# 6. DISTRICT LINEAR TREND FOR DIGITAL READINESS
# ============================================================

def forecast_digital_trend(
    pairs,
    forecast_year,
    district_list
):

    required = [
        "district",
        "target_year_start",
        "target_next_year"
    ]

    missing = [
        c for c in required
        if c not in pairs.columns
    ]

    if missing:
        raise ValueError(
            f"Digital pair file missing columns: {missing}"
        )

    pairs = pairs.copy()

    pairs["district"] = (
        pairs["district"]
        .astype("string")
        .str.strip()
    )

    pairs["target_year_start"] = pd.to_numeric(
        pairs["target_year_start"],
        errors="coerce"
    )

    pairs["target_next_year"] = pd.to_numeric(
        pairs["target_next_year"],
        errors="coerce"
    )

    pairs = pairs.dropna(
        subset=[
            "district",
            "target_year_start",
            "target_next_year"
        ]
    )

    results = []

    for district in district_list:

        history = pairs[
            pairs["district"] == district
        ].copy()

        history = history.groupby(
            "target_year_start",
            as_index=False
        )["target_next_year"].mean()

        history = history.sort_values(
            "target_year_start"
        )

        if (
            len(history) < 3
            or history["target_year_start"].nunique() < 3
        ):
            raise ValueError(
                f"Insufficient digital trend history "
                f"for district: {district}"
            )

        x = history[
            "target_year_start"
        ].to_numpy(dtype=float)

        y = history[
            "target_next_year"
        ].to_numpy(dtype=float)

        slope, intercept = np.polyfit(
            x,
            y,
            1
        )

        prediction = (
            slope * float(forecast_year)
            + intercept
        )

        prediction = max(
            0.0,
            float(prediction)
        )

        results.append({
            "district": district,
            "forecast_digital_devices_per_school": prediction,
            "digital_trend_slope": float(slope),
            "digital_trend_history_years": len(history),
            "digital_trend_first_target_year": int(
                history["target_year_start"].min()
            ),
            "digital_trend_last_target_year": int(
                history["target_year_start"].max()
            )
        })

    return pd.DataFrame(results)


# ============================================================
# 7. LOAD FROZEN NORMALIZATION PARAMETERS
# ============================================================

def load_normalization_parameters():

    params = load_csv(
        NORMALIZATION_INPUT
    )

    required = [
        "indicator",
        "direction",
        "p05",
        "p95"
    ]

    missing = [
        c for c in required
        if c not in params.columns
    ]

    if missing:
        raise ValueError(
            f"Normalization parameter columns missing: {missing}"
        )

    params = params.copy()

    params["p05"] = pd.to_numeric(
        params["p05"],
        errors="coerce"
    )

    params["p95"] = pd.to_numeric(
        params["p95"],
        errors="coerce"
    )

    required_indicators = [
        "Students per teacher",
        "Functional toilet percentage",
        "Good-condition classroom percentage",
        "Digital devices per reporting school"
    ]

    result = {}

    for indicator in required_indicators:

        match = params[
            params["indicator"] == indicator
        ]

        if len(match) != 1:
            raise ValueError(
                f"Expected exactly one normalization row "
                f"for: {indicator}"
            )

        row = match.iloc[0]

        if (
            pd.isna(row["p05"])
            or pd.isna(row["p95"])
            or row["p95"] <= row["p05"]
        ):
            raise ValueError(
                f"Invalid P5/P95 parameters for {indicator}"
            )

        result[indicator] = {
            "p05": float(row["p05"]),
            "p95": float(row["p95"]),
            "direction": str(row["direction"])
        }

    return result


# ============================================================
# 8. NORMALIZE FORECASTED INDICATORS
# ============================================================

def calculate_normalized_score(
    values,
    parameters
):

    values = pd.to_numeric(
        values,
        errors="coerce"
    )

    low = parameters["p05"]
    high = parameters["p95"]
    direction = parameters["direction"]

    clipped = values.clip(
        lower=low,
        upper=high
    )

    score = (
        (clipped - low)
        / (high - low)
        * 100
    )

    if direction == "LOWER_IS_BETTER":
        score = 100 - score

    elif direction != "HIGHER_IS_BETTER":
        raise ValueError(
            f"Unknown direction in normalization: {direction}"
        )

    return score.clip(
        lower=0,
        upper=100
    )


# ============================================================
# 9. HISTORICAL RISK REFERENCE THRESHOLDS
# ============================================================

def get_historical_thresholds(historical_scores):

    values = pd.to_numeric(
        historical_scores,
        errors="coerce"
    ).dropna()

    if len(values) != 288:
        raise ValueError(
            f"Expected 288 historical Shala Scores; got {len(values)}"
        )

    return {
        "q25": float(values.quantile(0.25)),
        "q50": float(values.quantile(0.50)),
        "q75": float(values.quantile(0.75))
    }


def classify_relative_band(score, thresholds):

    if pd.isna(score):
        return "NOT SCORED"

    if score <= thresholds["q25"]:
        return "CRITICAL"

    if score <= thresholds["q50"]:
        return "HIGH"

    if score <= thresholds["q75"]:
        return "MODERATE"

    return "LOW"


# ============================================================
# 10. APPLY HISTORICAL ERROR RANGE TO FORECAST
# ============================================================

def add_error_range(
    output,
    task,
    config,
    error_info
):

    prediction = pd.to_numeric(
        output[config["output_column"]],
        errors="coerce"
    )

    info = error_info[task]

    lower = prediction + info["q10"]
    upper = prediction + info["q90"]

    lower = apply_bounds(
        lower,
        config["lower_bound"],
        config["upper_bound"]
    )

    upper = apply_bounds(
        upper,
        config["lower_bound"],
        config["upper_bound"]
    )

    output[config["lower_column"]] = lower
    output[config["upper_column"]] = upper

    return output


# ============================================================
# 11. MAIN FORECAST ENGINE
# ============================================================

def main():

    print("=" * 70)
    print("SHALASCOPE - 2026-27 FORECAST ENGINE")
    print("=" * 70)

    # --------------------------------------------------------
    # A. LOAD INPUT FILES
    # --------------------------------------------------------

    historical = load_csv(
        SCORE_INPUT
    )

    model_summary = load_csv(
        MODEL_SUMMARY_INPUT
    )

    oof = load_csv(
        OOF_INPUT
    )

    digital_pairs = load_csv(
        DIGITAL_PAIRS_INPUT
    )

    normalization = load_normalization_parameters()

    # --------------------------------------------------------
    # B. VALIDATE HISTORICAL DATA
    # --------------------------------------------------------

    required_columns = [
        "academic_year",
        "district",
        "school_count",
        "enrollment_reported_student_total",
        "score_teacher_total_derived",
        "functional_toilet_pct_raw",
        "good_classroom_pct_raw",
        "digital_devices_per_school_raw",
        "shala_score_v1"
    ]

    missing = [
        c for c in required_columns
        if c not in historical.columns
    ]

    if missing:
        raise ValueError(
            f"Historical dataset missing columns: {missing}"
        )

    historical = historical.copy()

    historical["academic_year"] = (
        historical["academic_year"].astype(str)
    )

    historical["year_start"] = pd.to_numeric(
        historical["academic_year"].str.extract(
            r"^(\d{4})"
        )[0],
        errors="coerce"
    )

    if historical["year_start"].isna().any():
        raise ValueError("Invalid academic year format")

    if len(historical) != 288:
        raise ValueError(
            f"Expected 288 historical rows; found {len(historical)}"
        )

    if historical["district"].nunique() != 36:
        raise ValueError("Expected 36 unique districts")

    if historical.duplicated(
        ["district", "year_start"]
    ).any():
        raise ValueError("Duplicate district-year records detected")

    latest_start = int(
        historical["year_start"].max()
    )

    if latest_start != 2025:
        raise ValueError(
            f"Expected latest historical year 2025-26; "
            f"found start year {latest_start}"
        )

    source_year = "2025-26"
    forecast_start = latest_start + 1

    forecast_year = (
        f"{forecast_start}-{str(forecast_start + 1)[-2:]}"
    )

    latest = historical[
        historical["year_start"] == latest_start
    ].copy()

    if len(latest) != 36:
        raise ValueError(
            f"Expected 36 latest-year districts; found {len(latest)}"
        )

    if latest["district"].nunique() != 36:
        raise ValueError(
            "Latest-year district count is not 36"
        )

    print("\nINPUT VALIDATION: PASS")
    print("Historical rows:", len(historical))
    print("Latest source year:", source_year)
    print("Forecast year:", forecast_year)
    print("Districts:", len(latest))

    # Convert forecast source fields to numeric.
    numeric_source_columns = [
        "school_count",
        "enrollment_reported_student_total",
        "score_teacher_total_derived",
        "functional_toilet_pct_raw",
        "good_classroom_pct_raw",
        "digital_devices_per_school_raw"
    ]

    for column in numeric_source_columns:
        latest[column] = pd.to_numeric(
            latest[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # C. SELECT MODELS
    # --------------------------------------------------------

    selected_models, selection_report = select_models(
        model_summary
    )

    print("\nSELECTED MODELS:")
    print(
        selection_report[
            [
                "prediction",
                "selected_model",
                "selected_mae",
                "skill_vs_persistence",
                "validation_folds_won"
            ]
        ].to_string(index=False)
    )

    # --------------------------------------------------------
    # D. HISTORICAL OOF ERROR RANGES
    # --------------------------------------------------------

    error_info = build_error_ranges(
        oof,
        selected_models
    )

    # --------------------------------------------------------
    # E. INITIALIZE DISTRICT OUTPUT
    # --------------------------------------------------------

    output = latest[
        [
            "district",
            "school_count",
            "enrollment_reported_student_total",
            "score_teacher_total_derived",
            "functional_toilet_pct_raw",
            "good_classroom_pct_raw",
            "digital_devices_per_school_raw"
        ]
    ].copy()

    output = output.rename(columns={
        "school_count": "source_school_count_2025_26",
        "enrollment_reported_student_total": "source_enrollment_2025_26",
        "score_teacher_total_derived": "source_teachers_2025_26",
        "functional_toilet_pct_raw": "source_functional_toilet_pct_2025_26",
        "good_classroom_pct_raw": "source_good_classroom_pct_2025_26",
        "digital_devices_per_school_raw": "source_digital_devices_per_school_2025_26"
    })

    output.insert(
        0,
        "forecast_academic_year",
        forecast_year
    )

    output.insert(
        1,
        "source_academic_year",
        source_year
    )

    # --------------------------------------------------------
    # F. PERSISTENCE FORECASTS
    # --------------------------------------------------------

    source_mapping = {
        "student_enrollment":
            "source_enrollment_2025_26",

        "teacher_forecast":
            "source_teachers_2025_26",

        "infrastructure_toilet":
            "source_functional_toilet_pct_2025_26",

        "infrastructure_classroom":
            "source_good_classroom_pct_2025_26"
    }

    for task, source_column in source_mapping.items():

        config = TASKS[task]

        if selected_models[task] != "persistence":
            raise ValueError(
                f"{task}: selected model is "
                f"{selected_models[task]}, but this engine "
                f"currently implements Persistence for this task."
            )

        output[config["output_column"]] = (
            pd.to_numeric(
                output[source_column],
                errors="coerce"
            )
        )

        print(
            f"Forecast created: {task} -> Persistence"
        )

    # --------------------------------------------------------
    # G. DIGITAL READINESS DISTRICT TREND FORECAST
    # --------------------------------------------------------

    digital_task = "digital_readiness"

    digital_model = selected_models[digital_task]

    if digital_model == "district_linear_trend":

        digital_forecast = forecast_digital_trend(
            pairs=digital_pairs,
            forecast_year=forecast_start,
            district_list=output["district"].tolist()
        )

        output = output.merge(
            digital_forecast,
            on="district",
            how="left",
            validate="one_to_one"
        )

        if output[
            "forecast_digital_devices_per_school"
        ].isna().any():
            raise ValueError(
                "Missing digital forecast values"
            )

    elif digital_model == "persistence":

        output["forecast_digital_devices_per_school"] = (
            output["source_digital_devices_per_school_2025_26"]
        )

    else:
        raise ValueError(
            f"Unsupported selected digital model: {digital_model}"
        )

    print(
        "Forecast created: digital_readiness ->",
        digital_model
    )

    # --------------------------------------------------------
    # H. CHECK FORECAST VALUES
    # --------------------------------------------------------

    forecast_checks = [
        ("forecast_enrollment", 0, None),
        ("forecast_teachers", 0, None),
        ("forecast_functional_toilet_pct", 0, 100),
        ("forecast_good_classroom_pct", 0, 100),
        ("forecast_digital_devices_per_school", 0, None)
    ]

    for column, low, high in forecast_checks:

        values = pd.to_numeric(
            output[column],
            errors="coerce"
        )

        if values.isna().any():
            raise ValueError(
                f"Missing forecasts in {column}"
            )

        if (values < low).any():
            raise ValueError(
                f"Invalid negative forecast in {column}"
            )

        if high is not None and (values > high).any():
            raise ValueError(
                f"Invalid percentage forecast in {column}"
            )

    # --------------------------------------------------------
    # I. ADD HISTORICAL EMPIRICAL ERROR RANGES
    # --------------------------------------------------------

    task_order = [
        "student_enrollment",
        "teacher_forecast",
        "infrastructure_toilet",
        "infrastructure_classroom",
        "digital_readiness"
    ]

    for task in task_order:

        output = add_error_range(
            output,
            task,
            TASKS[task],
            error_info
        )

    print("\nEMPIRICAL ERROR RANGES: CREATED")

    # --------------------------------------------------------
    # J. FORECAST PUPIL-TEACHER RATIO
    # --------------------------------------------------------

    output["forecast_students_per_teacher"] = (
        output["forecast_enrollment"]
        / output["forecast_teachers"].where(
            output["forecast_teachers"] > 0
        )
    )

    if output[
        "forecast_students_per_teacher"
    ].isna().any():
        raise ValueError(
            "Invalid forecast student-teacher ratio"
        )

    # --------------------------------------------------------
    # K. CALCULATE FUTURE SHALA SCORE
    # --------------------------------------------------------

    output[
        "forecast_teacher_strength_score"
    ] = calculate_normalized_score(
        output["forecast_students_per_teacher"],
        normalization["Students per teacher"]
    )

    output[
        "forecast_functional_toilet_score"
    ] = calculate_normalized_score(
        output["forecast_functional_toilet_pct"],
        normalization["Functional toilet percentage"]
    )

    output[
        "forecast_good_classrooms_score"
    ] = calculate_normalized_score(
        output["forecast_good_classroom_pct"],
        normalization["Good-condition classroom percentage"]
    )

    output[
        "forecast_infrastructure_score"
    ] = output[
        [
            "forecast_functional_toilet_score",
            "forecast_good_classrooms_score"
        ]
    ].mean(axis=1)

    output[
        "forecast_digital_readiness_score"
    ] = calculate_normalized_score(
        output["forecast_digital_devices_per_school"],
        normalization[
            "Digital devices per reporting school"
        ]
    )

    output["forecast_shala_score_v1"] = output[
        [
            "forecast_teacher_strength_score",
            "forecast_infrastructure_score",
            "forecast_digital_readiness_score"
        ]
    ].mean(axis=1)

    # --------------------------------------------------------
    # L. HISTORICAL RELATIVE PERFORMANCE BANDS
    # --------------------------------------------------------

    thresholds = get_historical_thresholds(
        historical["shala_score_v1"]
    )

    output["forecast_relative_performance_band"] = (
        output["forecast_shala_score_v1"].apply(
            lambda value: classify_relative_band(
                value,
                thresholds
            )
        )
    )

    output = output.sort_values(
        "forecast_shala_score_v1",
        ascending=False
    ).reset_index(drop=True)

    output.insert(
        0,
        "forecast_rank",
        range(1, len(output) + 1)
    )

    # --------------------------------------------------------
    # M. MODEL AND METHODOLOGY COLUMNS
    # --------------------------------------------------------

    model_column_mapping = {
        "forecast_enrollment_model":
            "student_enrollment",

        "forecast_teacher_model":
            "teacher_forecast",

        "forecast_toilet_model":
            "infrastructure_toilet",

        "forecast_classroom_model":
            "infrastructure_classroom",

        "forecast_digital_model":
            "digital_readiness"
    }

    for column, task in model_column_mapping.items():
        output[column] = selected_models[task]

    output["forecast_error_range_type"] = (
        "Historical OOF residual P10-P90; empirical range only"
    )

    output["forecast_score_method"] = (
        "V1 frozen P5-P95 normalization and equal pillar weights"
    )

    output["forecast_risk_interpretation"] = (
        "Historical relative performance band; not risk probability"
    )

    # --------------------------------------------------------
    # N. SAVE MAIN FORECAST DATASET
    # --------------------------------------------------------

    output.to_csv(
        MAIN_OUTPUT,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nMAIN FORECAST DATASET SAVED:")
    print(MAIN_OUTPUT)

    # --------------------------------------------------------
    # O. SAVE RANKED FORECAST REPORT
    # --------------------------------------------------------

    ranked_columns = [
        "forecast_rank",
        "district",
        "forecast_academic_year",
        "forecast_shala_score_v1",
        "forecast_relative_performance_band",
        "forecast_teacher_strength_score",
        "forecast_infrastructure_score",
        "forecast_digital_readiness_score",
        "forecast_enrollment",
        "forecast_teachers",
        "forecast_students_per_teacher",
        "forecast_functional_toilet_pct",
        "forecast_good_classroom_pct",
        "forecast_digital_devices_per_school"
    ]

    ranked = output[ranked_columns].copy()

    ranked.to_csv(
        OUT / "forecast_ranked_districts_2026_27.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # P. SAVE MODEL SELECTION
    # --------------------------------------------------------

    # selection_report is also saved by select_models().
    # Save a separate copy inside this forecast report folder.

    selection_report.to_csv(
        OUT / "forecast_model_selection_2026_27.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Q. SAVE SCORE NORMALIZATION PARAMETERS USED
    # --------------------------------------------------------

    normalization_report = pd.DataFrame([
        {
            "indicator": name,
            "p05": values["p05"],
            "p95": values["p95"],
            "direction": values["direction"],
            "source": "Historical Shala Score V1 parameters"
        }
        for name, values in normalization.items()
    ])

    normalization_report.to_csv(
        OUT / "forecast_score_normalization_parameters.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # R. SAVE HISTORICAL RISK THRESHOLDS
    # --------------------------------------------------------

    threshold_report = pd.DataFrame([
        {
            "threshold": "Q25",
            "value": thresholds["q25"]
        },
        {
            "threshold": "Q50",
            "value": thresholds["q50"]
        },
        {
            "threshold": "Q75",
            "value": thresholds["q75"]
        }
    ])

    threshold_report.to_csv(
        OUT / "forecast_historical_score_thresholds.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # S. SAVE VALIDATION BASIS
    # --------------------------------------------------------

    validation_rows = []

    for task in task_order:

        validation_rows.append({
            "prediction": task,
            "selected_model": selected_models[task],
            "validation_method": "Expanding-window chronological validation",
            "validation_target_years": "2021-22 to 2025-26",
            "districts_per_validation_year": 36,
            "historical_oof_records": error_info[task]["count"],
            "residual_p10": error_info[task]["q10"],
            "residual_p50": error_info[task]["q50"],
            "residual_p90": error_info[task]["q90"],
            "status": "EXPERIMENTAL FORECAST"
        })

    pd.DataFrame(validation_rows).to_csv(
        OUT / "forecast_validation_basis_2026_27.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # T. SAVE METHODOLOGY
    # --------------------------------------------------------

    methodology = [
        "SHALASCOPE MAHARASHTRA - 2026-27 FORECAST",
        "",
        "Source historical data: 2018-19 to 2025-26.",
        "Forecast period: 2026-27.",
        "Geographic coverage: 36 Maharashtra districts.",
        "",
        "Model selection rule:",
        "A complex model is eligible when its overall MAE skill",
        "against Persistence is positive and it wins at least",
        "four of the five chronological validation folds.",
        "Otherwise Persistence is selected.",
        "",
        "Selected model is based on the V2 baseline evaluation.",
        "Student enrollment: Persistence.",
        "Teacher forecast: Persistence.",
        "Functional toilets: Persistence.",
        "Good classrooms: Persistence.",
        "Digital readiness: District linear trend.",
        "",
        "Persistence uses the latest 2025-26 observed value.",
        "Digital trend uses historical target-year observations",
        "available through 2025-26 and extrapolates to 2026-27.",
        "",
        "Historical error ranges use pooled out-of-fold residual",
        "P10 and P90 quantiles from 2021-22 to 2025-26.",
        "These are empirical error ranges, not formal prediction",
        "intervals and do not guarantee 80 percent coverage.",
        "",
        "Future Shala Score is derived from forecast raw indicators.",
        "Historical V1 P5-P95 parameters are frozen and reused.",
        "Teacher score uses forecast students per teacher.",
        "Infrastructure score is the mean of toilet and classroom scores.",
        "Digital score uses forecast devices per reporting school.",
        "All three pillars have equal weights.",
        "",
        "Relative performance bands use historical V1 score quartiles.",
        "They are descriptive categories, not risk probabilities.",
        "",
        "Forecasts are experimental and not official government estimates.",
        "No student learning outcome or causal impact is inferred."
    ]

    (OUT / "forecast_methodology_2026_27.txt").write_text(
        "\n".join(methodology),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # U. FINAL VALIDATION
    # --------------------------------------------------------

    checks = {
        "districts": len(output) == 36,
        "unique_districts": output["district"].nunique() == 36,
        "unique_rank": output["forecast_rank"].nunique() == 36,
        "enrollment_complete": output[
            "forecast_enrollment"
        ].notna().all(),
        "teachers_complete": output[
            "forecast_teachers"
        ].notna().all(),
        "toilet_complete": output[
            "forecast_functional_toilet_pct"
        ].notna().all(),
        "classroom_complete": output[
            "forecast_good_classroom_pct"
        ].notna().all(),
        "digital_complete": output[
            "forecast_digital_devices_per_school"
        ].notna().all(),
        "score_complete": output[
            "forecast_shala_score_v1"
        ].notna().all(),
        "score_range_valid": output[
            "forecast_shala_score_v1"
        ].between(0, 100).all()
    }

    print("\n" + "=" * 70)
    print("2026-27 FORECAST VALIDATION")
    print("=" * 70)

    for name, passed in checks.items():
        print(
            f"{name:28s}: {'PASS' if passed else 'FAIL'}"
        )

    if not all(checks.values()):
        raise RuntimeError(
            "Forecast validation failed. Review output."
        )

    # --------------------------------------------------------
    # V. PRINT FINAL RESULT
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("SHALASCOPE - 2026-27 FORECAST RESULT")
    print("=" * 70)

    print("Districts:", len(output))
    print("Forecast year:", forecast_year)

    print(
        "Average Forecast Shala Score:",
        round(
            output["forecast_shala_score_v1"].mean(),
            2
        )
    )

    print(
        "Median Forecast Shala Score:",
        round(
            output["forecast_shala_score_v1"].median(),
            2
        )
    )

    print("\nRELATIVE PERFORMANCE BANDS:")
    print(
        output[
            "forecast_relative_performance_band"
        ].value_counts().to_string()
    )

    print("\nTOP 10 DISTRICTS:")

    print(
        ranked.head(10).to_string(index=False)
    )

    print("\nBOTTOM 5 DISTRICTS:")

    print(
        ranked.tail(5).to_string(index=False)
    )

    print("\nMAIN OUTPUT:")
    print(MAIN_OUTPUT)

    print("\nREPORT FOLDER:")
    print(OUT)

    print("\nSTATUS: PASS")
    print(
        "Forecast is experimental; not an official "
        "government projection."
    )


if __name__ == "__main__":
    main()

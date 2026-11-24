
from pathlib import Path
import warnings

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# ============================================================
# SHALASCOPE - BASELINE ML EXPERIMENTS V2
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

PAIR_DIR = (
    ROOT / "reports" / "ml_readiness" / "training_pairs"
)

OUT = ROOT / "reports" / "ml_modeling_baseline"

OUT.mkdir(parents=True, exist_ok=True)


# ============================================================
# 1. FEATURES
# ============================================================

BASE_FEATURES = [
    "school_count",
    "enrollment_reported_student_total",
    "score_teacher_total_derived",
    "functional_toilet_pct_raw",
    "good_classroom_pct_raw",
    "digital_devices_per_school_raw"
]

NUMERIC_FEATURES = [
    "feature_year_start",
    *BASE_FEATURES
]

CATEGORICAL_FEATURES = [
    "district"
]

FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


# ============================================================
# 2. PREDICTION TASKS
# ============================================================

TASKS = {
    "student_enrollment": {
        "current_value": "enrollment_reported_student_total",
        "target": "target_next_year",
        "file": "student_enrollment_pairs_complete.csv",
        "bounds": (0, None),
        "unit": "students"
    },

    "teacher_forecast": {
        "current_value": "score_teacher_total_derived",
        "target": "target_next_year",
        "file": "teacher_forecast_pairs_complete.csv",
        "bounds": (0, None),
        "unit": "teachers"
    },

    "infrastructure_toilet": {
        "current_value": "functional_toilet_pct_raw",
        "target": "target_next_year",
        "file": "infrastructure_toilet_pairs_complete.csv",
        "bounds": (0, 100),
        "unit": "percentage points"
    },

    "infrastructure_classroom": {
        "current_value": "good_classroom_pct_raw",
        "target": "target_next_year",
        "file": "infrastructure_classroom_pairs_complete.csv",
        "bounds": (0, 100),
        "unit": "percentage points"
    },

    "digital_readiness": {
        "current_value": "digital_devices_per_school_raw",
        "target": "target_next_year",
        "file": "digital_readiness_pairs_complete.csv",
        "bounds": (0, None),
        "unit": "devices per school"
    }
}


# ============================================================
# 3. PREDICTION CONSTRAINTS
# ============================================================

def constrain_prediction(values, bounds):
    """
    Apply valid output limits to predictions.
    """

    values = np.asarray(values, dtype=float)

    low, high = bounds

    values = np.where(
        np.isfinite(values),
        values,
        low
    )

    if high is None:
        return np.maximum(values, low)

    return np.clip(values, low, high)


# ============================================================
# 4. MODEL PIPELINE
# ============================================================

def build_pipeline(model_type):
    """
    Build leakage-safe preprocessing + ML pipeline.

    Imputation, scaling and encoding are fitted
    separately inside each training fold.
    """

    numeric_pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(strategy="median")
        ),
        (
            "scaler",
            StandardScaler()
        )
    ])

    categorical_pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(strategy="most_frequent")
        ),
        (
            "onehot",
            OneHotEncoder(handle_unknown="ignore")
        )
    ])

    preprocessor = ColumnTransformer([
        (
            "numeric",
            numeric_pipeline,
            NUMERIC_FEATURES
        ),
        (
            "categorical",
            categorical_pipeline,
            CATEGORICAL_FEATURES
        )
    ])

    if model_type == "ridge":

        estimator = Ridge(
            alpha=10.0
        )

    elif model_type == "random_forest":

        estimator = RandomForestRegressor(
            n_estimators=300,
            max_depth=4,
            min_samples_leaf=4,
            max_features=0.8,
            random_state=42,
            n_jobs=-1
        )

    else:
        raise ValueError(
            f"Unknown model type: {model_type}"
        )

    return Pipeline([
        (
            "preprocessor",
            preprocessor
        ),
        (
            "model",
            estimator
        )
    ])


# ============================================================
# 5. DISTRICT LINEAR TREND MODEL
# ============================================================

def district_linear_trend(
    train,
    test,
    target_column,
    target_year_column,
    bounds
):
    """
    Forecast each district using its historical target trend.

    Only training-period target observations are used.
    The validation target year is used only as the
    future time coordinate for extrapolation.
    """

    predictions = []

    global_mean = float(
        train[target_column].mean()
    )

    for _, test_row in test.iterrows():

        district = test_row["district"]

        future_year = float(
            test_row[target_year_column]
        )

        history = train[
            train["district"] == district
        ][
            [
                target_year_column,
                target_column
            ]
        ].dropna().copy()

        history = (
            history.groupby(
                target_year_column,
                as_index=False
            )[target_column]
            .mean()
            .sort_values(target_year_column)
        )

        if (
            len(history) >= 2
            and history[target_year_column].nunique() >= 2
        ):

            x = history[target_year_column].to_numpy(
                dtype=float
            )

            y = history[target_column].to_numpy(
                dtype=float
            )

            slope, intercept = np.polyfit(
                x,
                y,
                deg=1
            )

            prediction = (
                slope * future_year + intercept
            )

        elif len(history) == 1:

            prediction = float(
                history[target_column].iloc[-1]
            )

        else:

            prediction = global_mean

        predictions.append(prediction)

    return constrain_prediction(
        predictions,
        bounds
    )


# ============================================================
# 6. METRICS
# ============================================================

def calculate_metrics(actual, predicted):

    actual = np.asarray(
        actual,
        dtype=float
    )

    predicted = np.asarray(
        predicted,
        dtype=float
    )

    return {
        "mae": float(
            mean_absolute_error(
                actual,
                predicted
            )
        ),

        "rmse": float(
            np.sqrt(
                mean_squared_error(
                    actual,
                    predicted
                )
            )
        ),

        "r2": float(
            r2_score(
                actual,
                predicted
            )
        )
    }


# ============================================================
# 7. LOAD AND VALIDATE TASK DATA
# ============================================================

def load_task_data(task, config):

    path = PAIR_DIR / config["file"]

    if not path.exists():
        raise FileNotFoundError(
            f"Training-pair file not found: {path}"
        )

    data = pd.read_csv(
        path,
        low_memory=False
    )

    required = [
        "district",
        "feature_year_start",
        "target_year_start",
        *FEATURES,
        config["target"],
        config["current_value"]
    ]

    missing = [
        c for c in set(required)
        if c not in data.columns
    ]

    if missing:
        raise ValueError(
            f"{task}: missing columns: {missing}"
        )

    data["district"] = (
        data["district"]
        .astype("string")
        .str.strip()
    )

    numeric_columns = (
        NUMERIC_FEATURES
        + [
            "target_year_start",
            config["target"],
            config["current_value"]
        ]
    )

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    data = data.dropna(
        subset=[
            "district",
            "feature_year_start",
            "target_year_start",
            config["target"],
            config["current_value"]
        ]
    ).copy()

    data["feature_year_start"] = (
        data["feature_year_start"].astype(int)
    )

    data["target_year_start"] = (
        data["target_year_start"].astype(int)
    )

    # Ensure that the target is exactly one academic year ahead.
    valid_transition = (
        data["target_year_start"]
        == data["feature_year_start"] + 1
    )

    data = data[valid_transition].copy()

    if data.empty:
        raise ValueError(
            f"{task}: no valid consecutive-year pairs"
        )

    if data.duplicated(
        ["district", "target_year_start"]
    ).any():

        raise ValueError(
            f"{task}: duplicate district-target-year records"
        )

    return data.sort_values(
        ["target_year_start", "district"]
    ).reset_index(drop=True)


# ============================================================
# 8. MAIN EXPERIMENT
# ============================================================

def main():

    print("=" * 70)
    print("SHALASCOPE - BASELINE ML EXPERIMENTS V2")
    print("=" * 70)

    fold_records = []
    prediction_records = []

    for task, config in TASKS.items():

        print("\n" + "-" * 65)
        print("TASK:", task)
        print("-" * 65)

        data = load_task_data(
            task,
            config
        )

        years = sorted(
            data["target_year_start"].unique()
        )

        # First two target years are initial training history.
        validation_years = years[2:]

        if len(validation_years) != 5:
            raise ValueError(
                f"{task}: expected five validation periods, "
                f"found {validation_years}"
            )

        print("Available pairs:", len(data))
        print("Validation target years:", validation_years)

        # ====================================================
        # EXPANDING WINDOW VALIDATION
        # ====================================================

        for validation_year in validation_years:

            train = data[
                data["target_year_start"]
                < validation_year
            ].copy()

            test = data[
                data["target_year_start"]
                == validation_year
            ].copy()

            if len(train) == 0 or len(test) != 36:

                raise ValueError(
                    f"{task}: invalid validation fold "
                    f"for {validation_year}. "
                    f"Train={len(train)}, Test={len(test)}"
                )

            X_train = train[FEATURES]
            y_train = train[
                config["target"]
            ].astype(float)

            X_test = test[FEATURES]
            y_test = test[
                config["target"]
            ].astype(float)

            models = {}

            # ------------------------------------------------
            # MODEL 1: PERSISTENCE
            # ------------------------------------------------

            persistence_raw = test[
                config["current_value"]
            ].to_numpy(dtype=float)

            models["persistence"] = (
                constrain_prediction(
                    persistence_raw,
                    config["bounds"]
                )
            )

            # ------------------------------------------------
            # MODEL 2: DISTRICT HISTORICAL MEAN
            # ------------------------------------------------

            district_mean = (
                train.groupby("district")[
                    config["target"]
                ].mean()
            )

            global_mean = float(
                y_train.mean()
            )

            mean_raw = (
                test["district"]
                .map(district_mean)
                .fillna(global_mean)
                .to_numpy(dtype=float)
            )

            models["district_historical_mean"] = (
                constrain_prediction(
                    mean_raw,
                    config["bounds"]
                )
            )

            # ------------------------------------------------
            # MODEL 3: DISTRICT LINEAR TREND
            # ------------------------------------------------

            trend_predictions = district_linear_trend(
                train=train,
                test=test,
                target_column=config["target"],
                target_year_column="target_year_start",
                bounds=config["bounds"]
            )

            models["district_linear_trend"] = (
                trend_predictions
            )

            # ------------------------------------------------
            # MODEL 4: RIDGE REGRESSION
            # ------------------------------------------------

            ridge = build_pipeline(
                "ridge"
            )

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ridge.fit(
                    X_train,
                    y_train
                )

            ridge_raw = ridge.predict(
                X_test
            )

            models["ridge_regression"] = (
                constrain_prediction(
                    ridge_raw,
                    config["bounds"]
                )
            )

            # ------------------------------------------------
            # MODEL 5: RANDOM FOREST
            # ------------------------------------------------

            forest = build_pipeline(
                "random_forest"
            )

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                forest.fit(
                    X_train,
                    y_train
                )

            forest_raw = forest.predict(
                X_test
            )

            models["random_forest"] = (
                constrain_prediction(
                    forest_raw,
                    config["bounds"]
                )
            )

            # ------------------------------------------------
            # EVALUATE EACH MODEL
            # ------------------------------------------------

            print(
                f"\nValidation target year: {validation_year}"
            )

            print(
                f"Training rows: {len(train)} | "
                f"Validation rows: {len(test)}"
            )

            for model_name, predictions in models.items():

                metrics = calculate_metrics(
                    y_test,
                    predictions
                )

                fold_records.append({
                    "prediction": task,
                    "validation_target_year": validation_year,
                    "model": model_name,
                    "training_rows": len(train),
                    "validation_rows": len(test),
                    "mae": metrics["mae"],
                    "rmse": metrics["rmse"],
                    "r2": metrics["r2"]
                })

                for index, (_, row) in enumerate(
                    test.iterrows()
                ):

                    actual = float(
                        y_test.iloc[index]
                    )

                    predicted = float(
                        predictions[index]
                    )

                    prediction_records.append({
                        "prediction": task,
                        "validation_target_year": validation_year,
                        "district": row["district"],
                        "model": model_name,
                        "actual": actual,
                        "predicted": predicted,
                        "residual": actual - predicted,
                        "absolute_error": abs(
                            actual - predicted
                        ),
                        "unit": config["unit"]
                    })

                print(
                    f"  {model_name:28s}"
                    f" MAE={metrics['mae']:.4f}"
                    f" RMSE={metrics['rmse']:.4f}"
                    f" R2={metrics['r2']:.4f}"
                )

    # ========================================================
    # 9. CREATE OUTPUT DATAFRAMES
    # ========================================================

    folds = pd.DataFrame(
        fold_records
    )

    predictions = pd.DataFrame(
        prediction_records
    )

    if folds.empty or predictions.empty:
        raise RuntimeError(
            "No validation results were generated"
        )

    # ========================================================
    # 10. SAVE FOLD METRICS
    # ========================================================

    folds.to_csv(
        OUT / "baseline_fold_metrics.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # 11. SAVE OUT-OF-FOLD PREDICTIONS
    # ========================================================

    predictions.to_csv(
        OUT / "baseline_oof_predictions.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # 12. MODEL COMPARISON SUMMARY
    # ========================================================

    summary_rows = []

    for task, task_predictions in predictions.groupby(
        "prediction"
    ):

        persistence = task_predictions[
            task_predictions["model"]
            == "persistence"
        ]

        persistence_mae = float(
            persistence["absolute_error"].mean()
        )

        persistence_by_fold = (
            folds[
                (folds["prediction"] == task)
                & (folds["model"] == "persistence")
            ][
                [
                    "validation_target_year",
                    "mae"
                ]
            ].rename(
                columns={
                    "mae": "persistence_fold_mae"
                }
            )
        )

        for model_name, model_predictions in (
            task_predictions.groupby("model")
        ):

            actual = model_predictions[
                "actual"
            ]

            predicted = model_predictions[
                "predicted"
            ]

            metrics = calculate_metrics(
                actual,
                predicted
            )

            model_by_fold = folds[
                (folds["prediction"] == task)
                & (folds["model"] == model_name)
            ]

            comparison = model_by_fold.merge(
                persistence_by_fold,
                on="validation_target_year",
                how="left"
            )

            wins = int(
                (
                    comparison["mae"]
                    < comparison["persistence_fold_mae"]
                ).sum()
            )

            skill = (
                1 - metrics["mae"] / persistence_mae
                if persistence_mae > 0
                else np.nan
            )

            summary_rows.append({
                "prediction": task,
                "model": model_name,
                "oof_predictions": len(model_predictions),
                "mae": metrics["mae"],
                "rmse": metrics["rmse"],
                "r2": metrics["r2"],
                "persistence_mae": persistence_mae,
                "skill_vs_persistence": skill,
                "validation_folds_won_vs_persistence": wins,
                "total_validation_folds": len(
                    comparison
                )
            })

    summary = pd.DataFrame(
        summary_rows
    )

    summary = summary.sort_values(
        ["prediction", "mae"]
    )

    summary.to_csv(
        OUT / "baseline_model_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # 13. BEST MODEL PER TASK
    # ========================================================

    best_models = (
        summary.sort_values(
            ["prediction", "mae"]
        )
        .groupby("prediction", as_index=False)
        .first()
    )

    best_models.to_csv(
        OUT / "baseline_best_model_by_task.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # 14. METHODOLOGY REPORT
    # ========================================================

    methodology = [
        "SHALASCOPE - BASELINE ML EXPERIMENTS V2",
        "",
        "Validation: Expanding-window chronological validation.",
        "Validation target years: 2021-22 through 2025-26.",
        "Each validation year contains 36 districts.",
        "No random train-test split was used.",
        "",
        "Five model approaches:",
        "1. Persistence baseline.",
        "2. District historical mean.",
        "3. District linear trend.",
        "4. Ridge regression.",
        "5. Random Forest.",
        "",
        "Forecast features come from the preceding academic year.",
        "Forecast target is from the next consecutive academic year.",
        "Historical mean uses training target values only.",
        "District trend uses past training target observations only.",
        "Trend extrapolation uses the known validation year coordinate.",
        "ML preprocessing is fitted separately inside each training fold.",
        "",
        "Primary metric: MAE.",
        "Secondary metrics: RMSE and R2.",
        "Skill = 1 - model MAE / persistence MAE.",
        "Positive skill means improvement over persistence.",
        "Negative skill means worse MAE than persistence.",
        "Fold wins count validation periods with lower MAE than persistence.",
        "",
        "There are only five temporal validation folds.",
        "Repeated observations from each district are not independent.",
        "Model selection considers overall MAE and fold stability.",
        "No model is automatically production-ready.",
        "",
        "Future Shala Score must be derived from forecast raw indicators.",
        "It must not be trained directly using full-period normalized scores.",
        "Normalization for future scoring must use training-period parameters."
    ]

    (
        OUT / "baseline_experiment_methodology.txt"
    ).write_text(
        "\n".join(methodology),
        encoding="utf-8"
    )

    # ========================================================
    # 15. FINAL SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("SHALASCOPE - BASELINE ML EXPERIMENT SUMMARY")
    print("=" * 70)

    print(
        summary.to_string(index=False)
    )

    print("\nBEST MODEL BY PREDICTION:")

    print(
        best_models[
            [
                "prediction",
                "model",
                "mae",
                "skill_vs_persistence",
                "validation_folds_won_vs_persistence"
            ]
        ].to_string(index=False)
    )

    print("\nOUTPUT FILES:")
    print(OUT / "baseline_fold_metrics.csv")
    print(OUT / "baseline_oof_predictions.csv")
    print(OUT / "baseline_model_summary.csv")
    print(OUT / "baseline_best_model_by_task.csv")
    print(OUT / "baseline_experiment_methodology.txt")

    print("\nSTATUS: EXPERIMENT COMPLETED")
    print("No model has been declared production-ready.")


if __name__ == "__main__":
    main()

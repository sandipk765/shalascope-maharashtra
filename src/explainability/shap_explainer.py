# -*- coding: utf-8 -*-
"""
src/explainability/shap_explainer.py
======================================
SHAP explainability wrapper for ShalaScope Maharashtra.

Covers:
  M4 -- Teacher Shortage Risk       (RandomForestClassifier, TreeExplainer)
  M5 -- District Risk Classification (RandomForestClassifier, TreeExplainer)

Design rules:
  - Graceful fallback: if shap is unavailable or explainer construction fails,
    return a status dict instead of raising.
  - All SHAP values saved to reports/explainability/ as CSV.
  - Per-district mean |SHAP| ranking also saved (used by dashboard).
  - No synthetic data: explainers run on the real 2024-25 test slice.

Fallback return schema:
  {"status": "SHAP_UNAVAILABLE", "reason": "<message>"}
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
import joblib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

V2_CSV    = ROOT / "data/processed/district_year/maharashtra_district_year_shala_score_v2.csv"
MODEL_DIR = ROOT / "models"
RPT_DIR   = ROOT / "reports/explainability"
RPT_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_YEARS = ["2018-19","2019-20","2020-21","2021-22","2022-23","2023-24"]
TEST_YEAR   = "2024-25"

# Feature sets must match run_prediction_modules.py exactly
M4_FEATS = [
    "year_num", "school_count",
    "enrollment_reported_student_total",
    "pillar2_infrastructure", "pillar2_digital",
    "pillar2_participation",
]
M5_FEATS = [
    "year_num",
    "pillar2_teacher_ptr",
    "pillar2_infrastructure",
    "pillar2_participation",
    "pillar2_digital",
    "ptr_students_per_teacher_raw",
    "school_count",
    "enrollment_reported_student_total",
]

StatusDict = dict[str, str]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _load_test_slice() -> pd.DataFrame:
    df = pd.read_csv(V2_CSV, low_memory=False)
    df["year_num"] = df["academic_year"].str[:4].astype(int)
    return df[df["academic_year"] == TEST_YEAR].copy()


def _safe_X(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    present = [c for c in feature_cols if c in df.columns]
    X = df[present].copy()
    for c in X.columns:
        X[c] = pd.to_numeric(X[c], errors="coerce")
        if X[c].isna().any():
            X[c] = X[c].fillna(X[c].median())
    return X


def _save_shap_outputs(
    shap_values: np.ndarray,
    X: pd.DataFrame,
    districts: pd.Series,
    module_id: str,
    class_names: list[str] | None = None,
) -> None:
    """
    Save two CSVs per module:
      1. Full SHAP matrix  (districts x features, one row per district-year)
      2. Mean |SHAP| ranking per feature  (global importance)
    For multi-class RF, shap_values shape is (n_samples, n_features, n_classes);
    we aggregate across classes by mean absolute value.
    """
    # Normalise to 2-D: (n_samples, n_features)
    if shap_values.ndim == 3:
        # mean |SHAP| across all classes
        sv2d = np.mean(np.abs(shap_values), axis=2)
    else:
        sv2d = shap_values

    # Full matrix
    shap_df = pd.DataFrame(sv2d, columns=X.columns)
    shap_df.insert(0, "district", districts.values)
    shap_df.to_csv(RPT_DIR / ("%s_shap_values.csv" % module_id),
                   index=False, encoding="utf-8-sig")

    # Mean |SHAP| ranking
    ranking = pd.DataFrame({
        "feature":       X.columns,
        "mean_abs_shap": np.mean(np.abs(sv2d), axis=0),
    }).sort_values("mean_abs_shap", ascending=False)
    ranking.to_csv(RPT_DIR / ("%s_shap_feature_ranking.csv" % module_id),
                   index=False, encoding="utf-8-sig")

    # Per-district top driver (feature with highest |SHAP| for each row)
    top_idx = np.argmax(np.abs(sv2d), axis=1)
    top_df  = pd.DataFrame({
        "district":      districts.values,
        "top_driver":    X.columns[top_idx],
        "top_shap_abs":  np.abs(sv2d)[np.arange(len(sv2d)), top_idx].round(4),
    })
    top_df.to_csv(RPT_DIR / ("%s_shap_top_driver.csv" % module_id),
                  index=False, encoding="utf-8-sig")

    print("    Saved: %s_shap_values.csv, %s_shap_feature_ranking.csv, "
          "%s_shap_top_driver.csv" % (module_id, module_id, module_id))


# ---------------------------------------------------------------------------
# M4 explainer
# ---------------------------------------------------------------------------

def explain_m4() -> Union[dict, StatusDict]:
    """
    TreeExplainer for M4 (Teacher Shortage Risk, RandomForestClassifier).
    Returns feature-level SHAP values for the 2024-25 test slice.
    Falls back gracefully if shap is unavailable or model load fails.
    """
    print("\n[SHAP] M4 Teacher Shortage Risk")
    try:
        import shap
    except ImportError as exc:
        reason = "shap package not installed: %s" % exc
        print("    FALLBACK: %s" % reason)
        return {"status": "SHAP_UNAVAILABLE", "reason": reason}

    model_path = MODEL_DIR / "m4_teacher_shortage_rf.joblib"
    if not model_path.exists():
        reason = "model artifact not found: %s" % model_path
        print("    FALLBACK: %s" % reason)
        return {"status": "SHAP_UNAVAILABLE", "reason": reason}

    try:
        model = joblib.load(model_path)
        test  = _load_test_slice()
        X_te  = _safe_X(test, M4_FEATS)

        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_te)

        # shap_values from RF binary classifier is a list [class0, class1]
        # We want class-1 (shortage risk)
        if isinstance(shap_values, list):
            sv = np.array(shap_values[1])   # shape (n_samples, n_features)
        else:
            sv = shap_values

        _save_shap_outputs(sv, X_te, test["district"], "m4")

        # summary dict for dashboard consumption
        ranking = pd.read_csv(RPT_DIR / "m4_shap_feature_ranking.csv")
        top3    = ranking.head(3)["feature"].tolist()
        print("    Top-3 global drivers: %s" % top3)
        return {"status": "OK", "module": "M4", "top_drivers": top3}

    except Exception as exc:
        reason = "TreeExplainer failed: %s" % exc
        print("    FALLBACK: %s" % reason)
        return {"status": "SHAP_UNAVAILABLE", "reason": reason}


# ---------------------------------------------------------------------------
# M5 explainer
# ---------------------------------------------------------------------------

def explain_m5() -> Union[dict, StatusDict]:
    """
    TreeExplainer for M5 (District Risk Classification, RandomForestClassifier).
    shap_values shape: (n_classes, n_samples, n_features) from some versions,
    or (n_samples, n_features, n_classes) from others -- handled below.
    """
    print("\n[SHAP] M5 District Risk Classification")
    try:
        import shap
    except ImportError as exc:
        reason = "shap package not installed: %s" % exc
        print("    FALLBACK: %s" % reason)
        return {"status": "SHAP_UNAVAILABLE", "reason": reason}

    model_path = MODEL_DIR / "m5_risk_class_rf.joblib"
    if not model_path.exists():
        reason = "model artifact not found: %s" % model_path
        print("    FALLBACK: %s" % reason)
        return {"status": "SHAP_UNAVAILABLE", "reason": reason}

    try:
        artifact = joblib.load(model_path)
        model    = artifact["model"]
        le       = artifact["label_encoder"]
        test     = _load_test_slice()
        X_te     = _safe_X(test, M5_FEATS)

        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_te)

        # Normalise shape to (n_samples, n_features, n_classes)
        if isinstance(shap_values, list):
            # list of arrays each (n_samples, n_features) -> stack on axis 2
            sv3d = np.stack(shap_values, axis=2)
        elif shap_values.ndim == 3:
            # could be (n_classes, n_samples, n_features) -> transpose
            if shap_values.shape[0] == len(le.classes_):
                sv3d = np.transpose(shap_values, (1, 2, 0))
            else:
                sv3d = shap_values   # already (n_samples, n_features, n_classes)
        else:
            sv3d = shap_values[:, :, np.newaxis]

        _save_shap_outputs(sv3d, X_te, test["district"], "m5",
                           class_names=list(le.classes_))

        ranking = pd.read_csv(RPT_DIR / "m5_shap_feature_ranking.csv")
        top3    = ranking.head(3)["feature"].tolist()
        print("    Top-3 global drivers: %s" % top3)
        return {"status": "OK", "module": "M5", "top_drivers": top3,
                "classes": list(le.classes_)}

    except Exception as exc:
        reason = "TreeExplainer failed: %s" % exc
        print("    FALLBACK: %s" % reason)
        return {"status": "SHAP_UNAVAILABLE", "reason": reason}


# ---------------------------------------------------------------------------
# combined runner
# ---------------------------------------------------------------------------

def run_all() -> dict:
    print("=" * 60)
    print("SHALASCOPE -- SHAP EXPLAINABILITY")
    print("Test slice: %s  |  Output: %s" % (TEST_YEAR, RPT_DIR))
    print("=" * 60)

    results = {
        "m4": explain_m4(),
        "m5": explain_m5(),
    }

    print("\n-- SUMMARY -----------------------------------------")
    for mid, res in results.items():
        status = res.get("status","?")
        if status == "OK":
            print("  %s: OK  top_drivers=%s" % (mid.upper(), res.get("top_drivers",[])))
        else:
            print("  %s: %s  reason=%s" % (mid.upper(), status, res.get("reason","")))

    # Persist combined status for dashboard to read
    rows = []
    for mid, res in results.items():
        rows.append({
            "module":      mid.upper(),
            "status":      res.get("status","?"),
            "top_drivers": str(res.get("top_drivers",[])),
            "reason":      res.get("reason",""),
        })
    pd.DataFrame(rows).to_csv(RPT_DIR / "shap_status.csv",
                               index=False, encoding="utf-8-sig")
    print("\nSaved: reports/explainability/shap_status.csv")
    return results


if __name__ == "__main__":
    run_all()

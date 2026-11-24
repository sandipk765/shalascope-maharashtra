# -*- coding: utf-8 -*-
"""
src/prescriptive.py
====================
Prescriptive Intervention & Out-of-Time Forecasting Engine  (Objective 6)

PUBLIC API
----------
validate_temporal_forecast(df)
    Out-of-time evaluation: train on <= 2023-24, test on 2024-25.
    Returns a dict with R2, MAE, and next-year (2025-26) projections.

recommend_top_interventions(district_row, state_benchmarks, top_n=3)
    Evaluates counterfactual improvements on controllable inputs and
    returns the top `top_n` actions sorted by marginal delta_shala_score.

GUARDRAILS
----------
- Never writes to raw/ or processed/ source CSVs.
- Uses only columns confirmed PRESENT in the v2 dataset.
- All missing-column cases handled gracefully (NaN, empty list).
- No learning outcome or dropout fabrication.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Column constants (confirmed PRESENT in v2 CSV)
# ---------------------------------------------------------------------------
COL_YEAR     = "academic_year"
COL_DISTRICT = "district"
COL_SCORE_V1 = "shala_score_v1"
COL_SCORE_V2 = "shala_score_v2"
COL_TIER     = "risk_tier_v2"
COL_PTR      = "ptr_students_per_teacher_raw"
COL_TOILET   = "functional_toilet_pct_raw"
COL_CLASS    = "good_classroom_pct_raw"
COL_DIGITAL  = "digital_devices_per_school_raw"
COL_P_TEACH  = "pillar_teacher_strength"
COL_P_INFRA  = "pillar_infrastructure"
COL_P_DIG    = "pillar_digital_readiness"
COL_P2_PTR   = "pillar2_teacher_ptr"
COL_P2_INFRA = "pillar2_infrastructure"
COL_P2_PART  = "pillar2_participation"
COL_P2_DIG   = "pillar2_digital"

# Features used for the out-of-time forecast model
# (all confirmed present, 0 null in v2 CSV)
FORECAST_FEATURES = [
    COL_PTR,
    COL_TOILET,
    COL_CLASS,
    COL_DIGITAL,
    COL_P_TEACH,
    COL_P_INFRA,
    COL_P_DIG,
]

# Controllable administrative inputs for prescriptive recommendations
CONTROLLABLE_INPUTS: Dict[str, Dict[str, Any]] = {
    COL_PTR: {
        "label":          "Reduce Pupil-Teacher Ratio to <= 30",
        "direction":      "decrease",   # lower is better
        "rte_target":     30.0,
        "step_min":       1.0,
        "step_max":       5.0,
        "clip_lo":        10.0,
        "clip_hi":        80.0,
        "pillar_proxy":   COL_P_TEACH,
    },
    COL_TOILET: {
        "label":          "Increase Functional Toilet Coverage (%)",
        "direction":      "increase",
        "step_min":       5.0,
        "step_max":       15.0,
        "clip_lo":        0.0,
        "clip_hi":        100.0,
        "pillar_proxy":   COL_P_INFRA,
    },
    COL_CLASS: {
        "label":          "Improve Good-Condition Classroom Share (%)",
        "direction":      "increase",
        "step_min":       5.0,
        "step_max":       15.0,
        "clip_lo":        0.0,
        "clip_hi":        100.0,
        "pillar_proxy":   COL_P_INFRA,
    },
    COL_DIGITAL: {
        "label":          "Increase Digital Devices per School",
        "direction":      "increase",
        "step_min":       1.0,
        "step_max":       5.0,
        "clip_lo":        0.0,
        "clip_hi":        100.0,
        "pillar_proxy":   COL_P_DIG,
    },
}

TIER_THRESHOLDS = [
    ("Thriving",  75.0),  # score >= 75
    ("Stable",    55.0),  # score >= 55
    ("At-Risk",   40.0),  # score >= 40
    ("Critical",   0.0),  # below 40
]


def _score_to_tier(score: float) -> str:
    for tier, threshold in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "Critical"


def _year_to_int(year_str: str) -> int:
    """Convert '2023-24' -> 2023."""
    try:
        return int(str(year_str)[:4])
    except (ValueError, TypeError):
        return 0


def _safe_float(value: Any, default: float = np.nan) -> float:
    try:
        v = float(value)
        return default if np.isnan(v) else v
    except (TypeError, ValueError):
        return default


def _build_year_num(df: pd.DataFrame) -> pd.Series:
    return df[COL_YEAR].apply(_year_to_int)


# ---------------------------------------------------------------------------
# validate_temporal_forecast
# ---------------------------------------------------------------------------

def validate_temporal_forecast(
    df: pd.DataFrame,
    train_cutoff: str = "2023-24",
    test_year:    str = "2024-25",
    target_col:   Optional[str] = None,
) -> Dict[str, Any]:
    """
    Strictly out-of-time evaluation.

    Train : academic_year <= train_cutoff  (all years up to and including 2023-24)
    Test  : academic_year == test_year     (2024-25)
    Forecast: projects 2025-26 scores per district.

    Parameters
    ----------
    df           : district-year DataFrame (must include COL_YEAR, COL_DISTRICT,
                   and at least one of COL_SCORE_V2 / COL_SCORE_V1).
    train_cutoff : last year included in training (default '2023-24').
    test_year    : hold-out evaluation year (default '2024-25').
    target_col   : score column to predict; auto-selects v2 > v1.

    Returns
    -------
    dict with keys:
        'model'          : model type used
        'features'       : list of feature columns used
        'target'         : target column name
        'train_rows'     : int
        'test_rows'      : int
        'r2'             : float  (out-of-time R2; NaN if < 2 test rows)
        'mae'            : float  (out-of-time MAE)
        'test_actuals'   : Series (index = district)
        'test_preds'     : Series (index = district)
        'forecast_2025_26': dict  {district: projected_score}
        'status'         : 'OK' | 'INSUFFICIENT_DATA' | error message
    """
    result: Dict[str, Any] = {
        "model": None, "features": [], "target": None,
        "train_rows": 0, "test_rows": 0, "r2": np.nan, "mae": np.nan,
        "test_actuals": pd.Series(dtype=float),
        "test_preds":   pd.Series(dtype=float),
        "forecast_2025_26": {},
        "status": "OK",
    }

    # -- Resolve target column --
    if target_col is None:
        target_col = COL_SCORE_V2 if COL_SCORE_V2 in df.columns else COL_SCORE_V1
    if target_col not in df.columns:
        result["status"] = f"INSUFFICIENT_DATA: target column '{target_col}' absent"
        return result
    result["target"] = target_col

    # -- Resolve feature columns (use only those present) --
    feats = [f for f in FORECAST_FEATURES if f in df.columns]
    if len(feats) < 2:
        result["status"] = "INSUFFICIENT_DATA: fewer than 2 feature columns present"
        return result
    result["features"] = feats

    # -- Build year_num for ordering --
    df = df.copy()
    df["_yr_int"] = _build_year_num(df)
    cutoff_int = _year_to_int(train_cutoff)
    test_int   = _year_to_int(test_year)

    train_mask = df["_yr_int"] <= cutoff_int
    test_mask  = df["_yr_int"] == test_int

    train = df.loc[train_mask].copy()
    test  = df.loc[test_mask].copy()

    result["train_rows"] = int(train_mask.sum())
    result["test_rows"]  = int(test_mask.sum())

    if result["train_rows"] < 10 or result["test_rows"] < 2:
        result["status"] = "INSUFFICIENT_DATA: too few rows in train or test split"
        return result

    def _safe_X(d: pd.DataFrame) -> pd.DataFrame:
        X = d[feats].copy()
        for c in X.columns:
            X[c] = pd.to_numeric(X[c], errors="coerce")
            X[c] = X[c].fillna(X[c].median())
        return X

    X_tr = _safe_X(train)
    y_tr = pd.to_numeric(train[target_col], errors="coerce").fillna(
        pd.to_numeric(train[target_col], errors="coerce").median()
    )
    X_te = _safe_X(test)
    y_te = pd.to_numeric(test[target_col], errors="coerce")

    # -- Choose model: RF if enough rows, Ridge otherwise --
    try:
        if result["train_rows"] >= 50:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.metrics import r2_score, mean_absolute_error
            model = RandomForestRegressor(
                n_estimators=200,
                max_depth=5,
                min_samples_leaf=4,
                random_state=42,
                n_jobs=-1,
            )
            result["model"] = "RandomForestRegressor"
        else:
            from sklearn.linear_model import Ridge
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import Pipeline
            from sklearn.metrics import r2_score, mean_absolute_error
            model = Pipeline([
                ("scale", StandardScaler()),
                ("ridge", Ridge(alpha=10.0)),
            ])
            result["model"] = "Ridge"

        model.fit(X_tr, y_tr)
        y_pred_te = pd.Series(model.predict(X_te), index=test.index)

        valid_te = y_te.notna()
        if valid_te.sum() >= 2:
            from sklearn.metrics import r2_score, mean_absolute_error
            result["r2"]  = round(float(r2_score(y_te[valid_te], y_pred_te[valid_te])), 4)
            result["mae"] = round(float(mean_absolute_error(y_te[valid_te], y_pred_te[valid_te])), 4)

        # Attach district labels where available
        if COL_DISTRICT in test.columns:
            result["test_actuals"] = y_te.set_axis(test[COL_DISTRICT].values)
            result["test_preds"]   = y_pred_te.set_axis(test[COL_DISTRICT].values)
        else:
            result["test_actuals"] = y_te
            result["test_preds"]   = y_pred_te

        # -- Project 2025-26: carry forward last known features per district --
        if COL_DISTRICT in df.columns:
            latest = (
                df.sort_values("_yr_int")
                .groupby(COL_DISTRICT)
                .last()
                .reset_index()
            )
            X_fc = _safe_X(latest)
            y_fc = model.predict(X_fc)
            result["forecast_2025_26"] = {
                str(d): round(float(np.clip(s, 0, 100)), 2)
                for d, s in zip(latest[COL_DISTRICT].values, y_fc)
            }

    except Exception as exc:
        result["status"] = f"ERROR: {exc}"

    return result


# ---------------------------------------------------------------------------
# recommend_top_interventions
# ---------------------------------------------------------------------------

def recommend_top_interventions(
    district_row:     Dict[str, Any],
    state_benchmarks: Dict[str, float],
    top_n:            int = 3,
) -> List[Dict[str, Any]]:
    """
    Evaluate counterfactual improvements on controllable administrative inputs.

    For each controllable input (PTR, toilet %, classroom %, digital devices):
      1. Determine the realistic target (capped at RTE norm / state benchmark).
      2. Estimate the marginal Shala Score delta using the confirmed pillar
         proxy relationship (linear normalisation matching build_shala_score_v2).
      3. Compute the new projected Shala Score and resulting risk tier.

    Parameters
    ----------
    district_row : dict of {column_name: value} for one district-year.
                   Must include at least COL_SCORE_V2 (or COL_SCORE_V1)
                   and the controllable input columns.
    state_benchmarks : dict mapping column_name -> state average value.
                       Used to compute relative improvement headroom.
    top_n : maximum number of recommendations to return (default 3).

    Returns
    -------
    List of dicts (up to top_n), sorted by delta_shala_score descending.
    Each dict contains:
        'input_col'          : str
        'label'              : str
        'current_value'      : float
        'target_value'       : float
        'improvement_pct_pt' : float  (amount of change)
        'delta_shala_score'  : float  (estimated score gain)
        'new_shala_score'    : float
        'new_risk_tier'      : str
        'notes'              : str
    """
    # -- Resolve base score --
    base_score_col = COL_SCORE_V2 if COL_SCORE_V2 in district_row else COL_SCORE_V1
    base_score = _safe_float(district_row.get(base_score_col))
    if np.isnan(base_score):
        # Try v1 fallback
        base_score = _safe_float(district_row.get(COL_SCORE_V1))
    if np.isnan(base_score):
        return []

    actions: List[Dict[str, Any]] = []

    for col, cfg in CONTROLLABLE_INPUTS.items():
        current = _safe_float(district_row.get(col))
        if np.isnan(current):
            continue

        direction  = cfg["direction"]
        step_min   = cfg["step_min"]
        step_max   = cfg["step_max"]
        clip_lo    = cfg["clip_lo"]
        clip_hi    = cfg["clip_hi"]
        rte_target = cfg.get("rte_target")

        # -- Compute realistic target --
        state_avg = _safe_float(state_benchmarks.get(col))

        if direction == "decrease":
            # PTR: target is min(current - step_min, rte_target, state_avg)
            candidates = [current - step_min]
            if rte_target is not None:
                candidates.append(rte_target)
            if not np.isnan(state_avg):
                candidates.append(state_avg)
            target = max(clip_lo, min(candidates))
            improvement = current - target   # positive = improvement
        else:
            # Increase metrics: target is current + step, capped at 100 / state_avg
            headroom = clip_hi - current
            if headroom <= 0:
                continue   # already at max
            step = min(step_max, max(step_min, headroom * 0.3))
            candidates = [current + step]
            if not np.isnan(state_avg) and state_avg > current:
                candidates.append(state_avg)
            target = min(clip_hi, max(candidates))
            improvement = target - current   # positive = improvement

        if improvement <= 0:
            continue

        # -- Estimate delta_shala_score via pillar-proxy linear mapping --
        # Each pillar is normalised 0-100; the Shala Score is a weighted mean
        # of four pillars with effective weight ~0.25 each.
        # Delta score ≈ (improvement / max_possible_range) * 100 * pillar_weight
        # For a 1 ppt improvement in a 0-100 metric, delta ~ 1 * 0.25 = 0.25 pts
        # This is a conservative linear estimate; actual RF model would differ.

        PILLAR_WEIGHT = 0.25  # equal weighting after Learning redistribution

        if col == COL_PTR:
            # PTR is inverted: lower PTR → higher pillar score
            # Range in UDISE+ data approx 15-50; normalise improvement in this range
            ptr_range  = 35.0   # approx P95 - P5
            delta_score = (improvement / ptr_range) * 100.0 * PILLAR_WEIGHT
        elif col in (COL_TOILET, COL_CLASS):
            # Already 0-100 percentage: 1 ppt improvement → ~PILLAR_WEIGHT pts
            delta_score = improvement * PILLAR_WEIGHT
        elif col == COL_DIGITAL:
            # Range approx 0-20 devices/school
            digital_range = 20.0
            delta_score = (improvement / digital_range) * 100.0 * PILLAR_WEIGHT
        else:
            delta_score = improvement * PILLAR_WEIGHT

        delta_score = round(float(np.clip(delta_score, 0, 25)), 3)
        new_score   = round(float(np.clip(base_score + delta_score, 0, 100)), 2)
        new_tier    = _score_to_tier(new_score)

        actions.append({
            "input_col":          col,
            "label":              cfg["label"],
            "current_value":      round(current, 2),
            "target_value":       round(target, 2),
            "improvement_pct_pt": round(improvement, 2),
            "delta_shala_score":  delta_score,
            "new_shala_score":    new_score,
            "new_risk_tier":      new_tier,
            "notes": (
                f"Conservative linear pillar-proxy estimate. "
                f"Pillar weight ~{PILLAR_WEIGHT:.0%}. "
                f"Source: {col}."
            ),
        })

    # Sort by delta_shala_score descending, tie-break by improvement amount
    actions.sort(key=lambda x: (-x["delta_shala_score"], -x["improvement_pct_pt"]))
    return actions[:top_n]

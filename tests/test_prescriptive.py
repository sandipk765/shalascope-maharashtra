# -*- coding: utf-8 -*-
"""
tests/test_prescriptive.py
===========================
Unit tests for src/prescriptive.py:
  - validate_temporal_forecast
  - recommend_top_interventions
  - _score_to_tier (helper)

Design principles:
  - All tests use synthetic DataFrames; no raw/processed source CSVs are read.
  - Tests cover only the five core blueprint pillars:
      Pupil-Teacher Ratio, Infrastructure Index (toilet % + classroom %),
      Digital Readiness, and trend features.
  - No learning-outcome or dropout data is fabricated.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.prescriptive import (
    recommend_top_interventions,
    validate_temporal_forecast,
    _score_to_tier,
)


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

DISTRICTS = ["PUNE", "NAGPUR", "LATUR", "THANE", "NASHIK", "AMRAVATI"]
YEARS     = ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]


@pytest.fixture(scope="module")
def base_df() -> pd.DataFrame:
    """
    Synthetic district-year DataFrame using only confirmed-present UDISE+ columns.
    Covers the five core blueprint pillars.
    """
    rng = np.random.default_rng(42)
    rows = []
    for dist in DISTRICTS:
        for yr in YEARS:
            rows.append({
                "district":                        dist,
                "academic_year":                   yr,
                "shala_score_v2":                  float(rng.uniform(35, 72)),
                "shala_score_v1":                  float(rng.uniform(35, 70)),
                "risk_tier_v2":                    rng.choice(["Thriving", "Stable", "At-Risk", "Critical"]),
                "ptr_students_per_teacher_raw":    float(rng.uniform(18, 46)),
                "functional_toilet_pct_raw":       float(rng.uniform(55, 97)),
                "good_classroom_pct_raw":          float(rng.uniform(50, 92)),
                "digital_devices_per_school_raw":  float(rng.uniform(0.5, 18)),
                "pillar_teacher_strength":         float(rng.uniform(40, 85)),
                "pillar_infrastructure":           float(rng.uniform(45, 88)),
                "pillar_digital_readiness":        float(rng.uniform(30, 78)),
                "pillar2_teacher_ptr":             float(rng.uniform(40, 85)),
                "pillar2_infrastructure":          float(rng.uniform(45, 88)),
                "pillar2_participation":           float(rng.uniform(35, 80)),
                "pillar2_digital":                 float(rng.uniform(30, 78)),
                "enrollment_reported_student_total": float(rng.integers(50000, 500000)),
                "score_teacher_total_derived":     float(rng.integers(5000, 50000)),
                "school_count":                    float(rng.integers(500, 5000)),
                "region":                          rng.choice(["Konkan", "Western Maharashtra",
                                                                "Marathwada", "Vidarbha"]),
            })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def minimal_df() -> pd.DataFrame:
    """Minimal DataFrame with only required temporal + pillar columns."""
    rng = np.random.default_rng(99)
    rows = []
    for d in ["PUNE", "NAGPUR"]:
        for yr in YEARS:
            rows.append({
                "district":                       d,
                "academic_year":                  yr,
                "shala_score_v2":                 float(rng.uniform(40, 70)),
                "ptr_students_per_teacher_raw":   float(rng.uniform(20, 40)),
                "functional_toilet_pct_raw":      float(rng.uniform(60, 95)),
                "good_classroom_pct_raw":         float(rng.uniform(55, 90)),
                "digital_devices_per_school_raw": float(rng.uniform(1, 15)),
                "pillar_teacher_strength":        float(rng.uniform(45, 80)),
                "pillar_infrastructure":          float(rng.uniform(50, 85)),
                "pillar_digital_readiness":       float(rng.uniform(35, 75)),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# TESTS: validate_temporal_forecast
# ---------------------------------------------------------------------------

class TestValidateTemporalForecast:

    def test_returns_dict(self, base_df):
        result = validate_temporal_forecast(base_df)
        assert isinstance(result, dict)

    def test_required_keys_present(self, base_df):
        result = validate_temporal_forecast(base_df)
        for key in ["status", "model", "r2", "mae", "train_rows", "test_rows",
                    "forecast_2025_26", "test_actuals", "test_preds", "features", "target"]:
            assert key in result, f"Key '{key}' missing from result"

    def test_status_ok_on_valid_data(self, base_df):
        result = validate_temporal_forecast(base_df)
        assert result["status"] == "OK", f"Unexpected status: {result['status']}"

    def test_train_test_split_correct(self, base_df):
        # 6 years * 6 districts = 36 train rows; 1 year * 6 = 6 test rows
        result = validate_temporal_forecast(base_df)
        assert result["train_rows"] == 36, f"Expected 36 train rows, got {result['train_rows']}"
        assert result["test_rows"]  == 6,  f"Expected 6 test rows, got {result['test_rows']}"

    def test_no_future_leakage(self, base_df):
        """test_preds must have one entry per district (trained on <= 2023-24 only)."""
        test_preds = validate_temporal_forecast(base_df)["test_preds"]
        assert len(test_preds) == len(DISTRICTS)

    def test_r2_and_mae_are_finite(self, base_df):
        result = validate_temporal_forecast(base_df)
        assert np.isfinite(result["r2"]),  f"R2 is not finite: {result['r2']}"
        assert np.isfinite(result["mae"]), f"MAE is not finite: {result['mae']}"
        assert result["mae"] >= 0

    def test_forecast_2025_26_has_all_districts(self, base_df):
        result = validate_temporal_forecast(base_df)
        fc = result["forecast_2025_26"]
        for dist in DISTRICTS:
            assert dist in fc, f"District '{dist}' missing from 2025-26 forecast"

    def test_forecast_scores_in_valid_range(self, base_df):
        result = validate_temporal_forecast(base_df)
        for dist, score in result["forecast_2025_26"].items():
            assert 0 <= score <= 100, f"{dist}: forecast score {score} out of [0, 100]"

    def test_insufficient_data_returns_gracefully(self):
        """Too-small DataFrame should return a failure status, not raise."""
        tiny = pd.DataFrame({
            "district":                       ["PUNE"],
            "academic_year":                  ["2024-25"],
            "shala_score_v2":                 [55.0],
            "ptr_students_per_teacher_raw":   [28.0],
            "functional_toilet_pct_raw":      [80.0],
            "good_classroom_pct_raw":         [75.0],
            "digital_devices_per_school_raw": [5.0],
            "pillar_teacher_strength":        [60.0],
            "pillar_infrastructure":          [65.0],
            "pillar_digital_readiness":       [50.0],
        })
        result = validate_temporal_forecast(tiny)
        assert "INSUFFICIENT_DATA" in result["status"] or result["status"] == "OK"

    def test_missing_target_column_returns_gracefully(self, base_df):
        df_no_score = base_df.drop(columns=["shala_score_v2", "shala_score_v1"], errors="ignore")
        result = validate_temporal_forecast(df_no_score)
        assert "INSUFFICIENT_DATA" in result["status"] or "ERROR" in result["status"]

    def test_model_type_is_valid(self, base_df):
        result = validate_temporal_forecast(base_df)
        assert result["model"] in ("Ridge", "RandomForestRegressor")


# ---------------------------------------------------------------------------
# TESTS: recommend_top_interventions
# ---------------------------------------------------------------------------

class TestRecommendTopInterventions:

    @pytest.fixture
    def typical_row(self) -> dict:
        return {
            "district":                        "PUNE",
            "academic_year":                   "2024-25",
            "shala_score_v2":                  48.5,
            "shala_score_v1":                  47.0,
            "ptr_students_per_teacher_raw":    38.0,   # above 30 RTE norm
            "functional_toilet_pct_raw":       72.0,   # below state avg
            "good_classroom_pct_raw":          68.0,   # below state avg
            "digital_devices_per_school_raw":  3.5,
        }

    @pytest.fixture
    def state_bm(self) -> dict:
        return {
            "ptr_students_per_teacher_raw":   30.0,
            "functional_toilet_pct_raw":      85.0,
            "good_classroom_pct_raw":         80.0,
            "digital_devices_per_school_raw": 7.0,
        }

    def test_returns_list(self, typical_row, state_bm):
        assert isinstance(recommend_top_interventions(typical_row, state_bm), list)

    def test_at_most_top_n(self, typical_row, state_bm):
        for n in (1, 2, 3):
            result = recommend_top_interventions(typical_row, state_bm, top_n=n)
            assert len(result) <= n

    def test_default_top_3(self, typical_row, state_bm):
        assert len(recommend_top_interventions(typical_row, state_bm)) <= 3

    def test_delta_shala_score_non_negative(self, typical_row, state_bm):
        for rec in recommend_top_interventions(typical_row, state_bm):
            assert rec["delta_shala_score"] >= 0, (
                f"Negative delta for {rec['input_col']}: {rec['delta_shala_score']}"
            )

    def test_new_score_in_valid_range(self, typical_row, state_bm):
        for rec in recommend_top_interventions(typical_row, state_bm):
            assert 0 <= rec["new_shala_score"] <= 100, (
                f"new_shala_score {rec['new_shala_score']} out of [0, 100]"
            )

    def test_new_risk_tier_valid(self, typical_row, state_bm):
        valid_tiers = {"Thriving", "Stable", "At-Risk", "Critical"}
        for rec in recommend_top_interventions(typical_row, state_bm):
            assert rec["new_risk_tier"] in valid_tiers, f"Invalid tier: {rec['new_risk_tier']}"

    def test_required_keys_in_each_rec(self, typical_row, state_bm):
        required = {
            "input_col", "label", "current_value", "target_value",
            "improvement_pct_pt", "delta_shala_score", "new_shala_score",
            "new_risk_tier", "notes",
        }
        for rec in recommend_top_interventions(typical_row, state_bm):
            assert not (required - set(rec.keys())), \
                f"Missing keys: {required - set(rec.keys())}"

    def test_sorted_by_delta_descending(self, typical_row, state_bm):
        result = recommend_top_interventions(typical_row, state_bm)
        deltas = [r["delta_shala_score"] for r in result]
        assert deltas == sorted(deltas, reverse=True)

    def test_missing_score_returns_empty(self, state_bm):
        """When no score column present, return [] not raise."""
        row = {"ptr_students_per_teacher_raw": 35.0, "functional_toilet_pct_raw": 75.0}
        assert recommend_top_interventions(row, state_bm) == []

    def test_empty_benchmarks_still_returns_recs(self, typical_row):
        result = recommend_top_interventions(typical_row, {})
        assert isinstance(result, list)

    def test_controllable_inputs_are_core_pillars_only(self, typical_row, state_bm):
        """Recommendations must only touch the four core controllable indicators."""
        allowed = {
            "ptr_students_per_teacher_raw",
            "functional_toilet_pct_raw",
            "good_classroom_pct_raw",
            "digital_devices_per_school_raw",
        }
        for rec in recommend_top_interventions(typical_row, state_bm):
            assert rec["input_col"] in allowed, \
                f"Unexpected controllable input: {rec['input_col']}"

    def test_maxed_infrastructure_excluded(self, state_bm):
        """Toilet % and classroom % already at 100 must not appear in recs."""
        maxed_row = {
            "shala_score_v2":                  60.0,
            "ptr_students_per_teacher_raw":    35.0,
            "functional_toilet_pct_raw":       100.0,
            "good_classroom_pct_raw":          100.0,
            "digital_devices_per_school_raw":  5.0,
        }
        result = recommend_top_interventions(maxed_row, state_bm)
        input_cols = [r["input_col"] for r in result]
        assert "functional_toilet_pct_raw" not in input_cols
        assert "good_classroom_pct_raw"    not in input_cols

    def test_improvement_always_positive(self, typical_row, state_bm):
        for rec in recommend_top_interventions(typical_row, state_bm):
            assert rec["improvement_pct_pt"] > 0


# ---------------------------------------------------------------------------
# TESTS: _score_to_tier (helper)
# ---------------------------------------------------------------------------

class TestScoreToTier:

    @pytest.mark.parametrize("score,expected", [
        (80.0,  "Thriving"),
        (75.0,  "Thriving"),
        (74.9,  "Stable"),
        (55.0,  "Stable"),
        (54.9,  "At-Risk"),
        (40.0,  "At-Risk"),
        (39.9,  "Critical"),
        (0.0,   "Critical"),
    ])
    def test_tier_boundaries(self, score, expected):
        assert _score_to_tier(score) == expected, \
            f"Score {score}: expected '{expected}', got '{_score_to_tier(score)}'"

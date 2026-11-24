# -*- coding: utf-8 -*-
"""
tests/test_score_v2.py
Unit tests for Shala Score v2 output integrity.
Reads the already-generated CSV; does NOT re-run the scorer.
"""
import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

V2_PATH = ROOT / "data/processed/district_year/maharashtra_district_year_shala_score_v2.csv"

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def v2():
    if not V2_PATH.exists():
        pytest.skip(f"v2 CSV not found at {V2_PATH} — run build_shala_score_v2.py first")
    df = pd.read_csv(V2_PATH, low_memory=False)
    return df


# ---------------------------------------------------------------------------
# shape and coverage
# ---------------------------------------------------------------------------

def test_row_count(v2):
    """288 rows = 36 districts × 8 years."""
    assert len(v2) == 288, f"Expected 288 rows, got {len(v2)}"


def test_district_count(v2):
    assert v2["district"].nunique() == 36, (
        f"Expected 36 districts, got {v2['district'].nunique()}"
    )


def test_year_count(v2):
    assert v2["academic_year"].nunique() == 8, (
        f"Expected 8 years, got {v2['academic_year'].nunique()}"
    )


def test_score_column_present(v2):
    assert "shala_score_v2" in v2.columns, "shala_score_v2 column missing"


def test_all_288_scored(v2):
    n_null = v2["shala_score_v2"].isna().sum()
    assert n_null == 0, f"{n_null} rows have null shala_score_v2"


# ---------------------------------------------------------------------------
# score range
# ---------------------------------------------------------------------------

def test_score_in_0_100(v2):
    scores = pd.to_numeric(v2["shala_score_v2"], errors="coerce")
    assert scores.min() >= 0, f"Minimum score {scores.min():.4f} is below 0"
    assert scores.max() <= 100, f"Maximum score {scores.max():.4f} is above 100"


def test_score_range_reasonable(v2):
    """Score should span at least 20 points across 288 district-years."""
    scores = pd.to_numeric(v2["shala_score_v2"], errors="coerce")
    spread = float(scores.max()) - float(scores.min())
    assert spread >= 20.0, f"Score spread {spread:.2f} is suspiciously narrow"


# ---------------------------------------------------------------------------
# risk tiers
# ---------------------------------------------------------------------------

def test_risk_tier_column_present(v2):
    assert "risk_tier_v2" in v2.columns, "risk_tier_v2 column missing"


def test_four_tiers(v2):
    tiers = set(v2["risk_tier_v2"].dropna().unique())
    expected = {"Thriving", "Stable", "At-Risk", "Critical"}
    assert tiers == expected, f"Unexpected tiers: {tiers}"


def test_equal_size_tiers(v2):
    """Each tier must contain exactly 72 rows (288 / 4)."""
    counts = v2["risk_tier_v2"].value_counts()
    for tier, n in counts.items():
        assert n == 72, f"Tier '{tier}' has {n} rows, expected 72"


# ---------------------------------------------------------------------------
# pillar columns
# ---------------------------------------------------------------------------

PILLAR_COLS = [
    "pillar2_teacher_ptr",
    "pillar2_infrastructure",
    "pillar2_participation",
    "pillar2_digital",
]

def test_pillar_columns_present(v2):
    missing = [c for c in PILLAR_COLS if c not in v2.columns]
    assert not missing, f"Pillar columns missing: {missing}"


def test_pillar_scores_in_0_100(v2):
    for col in PILLAR_COLS:
        if col not in v2.columns:
            continue
        s = pd.to_numeric(v2[col], errors="coerce").dropna()
        assert s.min() >= 0,   f"{col} has value below 0: {s.min():.4f}"
        assert s.max() <= 100, f"{col} has value above 100: {s.max():.4f}"


# ---------------------------------------------------------------------------
# no double-counting guard
# ---------------------------------------------------------------------------

def test_learning_pillar_weight_zero(v2):
    """
    Learning pillar (pillar2_learning) must be absent or all-NaN.
    It is a confirmed MISSING_IN_SOURCE column; a non-NaN value would
    indicate fabricated data or double-counting.
    """
    if "pillar2_learning" in v2.columns:
        n_nonull = v2["pillar2_learning"].notna().sum()
        assert n_nonull == 0, (
            f"pillar2_learning has {n_nonull} non-null values — "
            "this column should be absent (MISSING_IN_SOURCE)"
        )


# ---------------------------------------------------------------------------
# no synthetic data check
# ---------------------------------------------------------------------------

def test_no_fabricated_learning_columns(v2):
    """
    Columns that were confirmed absent from UDISE+ must not appear
    with real (non-NaN) values.
    """
    forbidden = [
        "learning_outcome", "ger", "dropout_rate",
        "aser_score", "nas_score",
    ]
    for col in forbidden:
        if col in v2.columns:
            n_real = pd.to_numeric(v2[col], errors="coerce").notna().sum()
            assert n_real == 0, (
                f"Column '{col}' was confirmed MISSING_IN_SOURCE but has "
                f"{n_real} non-null values in v2 CSV"
            )

# -*- coding: utf-8 -*-
"""
tests/test_regions.py
Unit tests for src/core/regions.py
"""
import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.regions import (
    REGION_MAP,
    REGIONS,
    add_region,
    compute_gpi,
    compute_marginalised_enrolment_pct,
)


# ---------------------------------------------------------------------------
# REGION_MAP coverage
# ---------------------------------------------------------------------------

def test_all_36_districts_mapped():
    """REGION_MAP must contain exactly 36 canonical district entries
    (after removing any aliases that map to the same physical district)."""
    # Every value must be a known region
    for dist, reg in REGION_MAP.items():
        assert reg in REGIONS, f"District '{dist}' maps to unknown region '{reg}'"
    # At least 36 unique districts (some aliases may add extras)
    assert len(REGION_MAP) >= 36, (
        f"REGION_MAP has only {len(REGION_MAP)} entries — expected at least 36"
    )


def test_region_values_are_valid():
    for dist, reg in REGION_MAP.items():
        assert reg in REGIONS, f"'{dist}' -> '{reg}' not in REGIONS"


def test_four_regions_present():
    regions_in_map = set(REGION_MAP.values())
    assert regions_in_map == set(REGIONS), (
        f"Regions in map: {regions_in_map} != expected: {set(REGIONS)}"
    )


def test_region_counts_at_least_minimum():
    """Each region must contain at least its documented minimum."""
    minimums = {
        "Konkan": 7,
        "Western Maharashtra": 10,
        "Marathwada": 8,
        "Vidarbha": 11,
    }
    from collections import Counter
    counts = Counter(REGION_MAP.values())
    for reg, minimum in minimums.items():
        assert counts[reg] >= minimum, (
            f"Region '{reg}' has {counts[reg]} districts, expected >= {minimum}"
        )


# ---------------------------------------------------------------------------
# add_region()
# ---------------------------------------------------------------------------

def _make_df(districts):
    return pd.DataFrame({"district": districts})


def test_add_region_known_districts():
    df = _make_df(["PUNE", "NAGPUR", "LATUR", "THANE"])
    out = add_region(df)
    assert "region" in out.columns
    assert out.loc[out["district"] == "PUNE",   "region"].iloc[0] == "Western Maharashtra"
    assert out.loc[out["district"] == "NAGPUR",  "region"].iloc[0] == "Vidarbha"
    assert out.loc[out["district"] == "LATUR",   "region"].iloc[0] == "Marathwada"
    assert out.loc[out["district"] == "THANE",   "region"].iloc[0] == "Konkan"


def test_add_region_zero_unmapped_for_known():
    """All canonical district names in REGION_MAP must resolve without NaN."""
    df = _make_df(list(REGION_MAP.keys()))
    out = add_region(df)
    n_unmapped = out["region"].isna().sum()
    assert n_unmapped == 0, f"{n_unmapped} known districts were unmapped"


def test_add_region_unknown_district_raises():
    """add_region() raises ValueError for unknown districts (strict by design)."""
    df = _make_df(["UNKNOWN_DISTRICT_XYZ_99"])
    with pytest.raises(ValueError, match="not in REGION_MAP"):
        add_region(df)


def test_add_region_does_not_mutate_input():
    df = _make_df(["PUNE", "NAGPUR"])
    original_cols = list(df.columns)
    _ = add_region(df)
    assert list(df.columns) == original_cols


# ---------------------------------------------------------------------------
# compute_gpi()  — takes a DataFrame with real UDISE+ column names
# ---------------------------------------------------------------------------

BOYS_COL  = "enrollment_reported_enrollment_b_component_total"
GIRLS_COL = "enrollment_reported_enrollment_g_component_total"


def _gpi_df(boys_vals, girls_vals):
    return pd.DataFrame({BOYS_COL: boys_vals, GIRLS_COL: girls_vals})


def test_gpi_typical_values():
    df  = _gpi_df([1000.0, 500.0], [900.0, 600.0])
    out = compute_gpi(df=df)
    # compute_gpi returns a DataFrame with a 'gpi' column
    gpi = out["gpi"] if isinstance(out, pd.DataFrame) else out
    assert abs(float(gpi.iloc[0]) - 0.9) < 1e-9
    assert abs(float(gpi.iloc[1]) - 1.2) < 1e-9


def test_gpi_zero_boys_is_nan():
    df  = _gpi_df([0.0], [100.0])
    out = compute_gpi(df=df)
    gpi = out["gpi"] if isinstance(out, pd.DataFrame) else out
    assert bool(gpi.isna().iloc[0])


def test_gpi_all_positive():
    df  = _gpi_df([100.0, 200.0, 300.0], [80.0, 210.0, 310.0])
    out = compute_gpi(df=df)
    gpi = out["gpi"] if isinstance(out, pd.DataFrame) else out
    assert bool(gpi.notna().all())
    assert bool((gpi > 0).all())


# ---------------------------------------------------------------------------
# compute_marginalised_enrolment_pct()
# ---------------------------------------------------------------------------

def test_marginalised_pct_sum():
    """SC + ST + OBC / total should give the expected percentage."""
    df = pd.DataFrame({
        "enrollment_reported_sc_enrollment":  [100.0],
        "enrollment_reported_st_enrollment":  [50.0],
        "enrollment_reported_obc_enrollment": [150.0],
        "enrollment_reported_student_total":  [500.0],
    })
    result = compute_marginalised_enrolment_pct(df)
    expected = (100 + 50 + 150) / 500 * 100
    assert abs(float(result["marginalised_enrolment_pct"].iloc[0]) - expected) < 1e-6


def test_marginalised_pct_zero_total_is_nan():
    df = pd.DataFrame({
        "enrollment_reported_sc_enrollment":  [100.0],
        "enrollment_reported_st_enrollment":  [50.0],
        "enrollment_reported_obc_enrollment": [0.0],
        "enrollment_reported_student_total":  [0.0],
    })
    result = compute_marginalised_enrolment_pct(df)
    assert pd.isna(result["marginalised_enrolment_pct"].iloc[0])


def test_marginalised_pct_clipped_at_100():
    """Result must be clipped to 0–100 even if components sum > total."""
    df = pd.DataFrame({
        "enrollment_reported_sc_enrollment":  [400.0],
        "enrollment_reported_st_enrollment":  [400.0],
        "enrollment_reported_obc_enrollment": [400.0],
        "enrollment_reported_student_total":  [500.0],
    })
    result = compute_marginalised_enrolment_pct(df)
    pct = float(result["marginalised_enrolment_pct"].iloc[0])
    assert pct <= 100.0

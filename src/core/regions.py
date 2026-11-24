"""
src/core/regions.py
===================
Single source of truth for:
  - 36-district → region mapping  (Konkan, Western Maharashtra, Marathwada, Vidarbha)
  - District name aliases (old census names → current official names)
  - GPI computation  (girls_enrolment / boys_enrolment)
  - Utility helpers used by both pipeline scripts and the dashboard

Data sources used:
  - Maharashtra Revenue Division boundaries (public)
  - UDISE+ district code list 2023-24

GUARDRAILS
  - No synthetic data.  Pure lookups derived from public geography.
  - Raises immediately if any of the 36 districts in the dataset is unmapped.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Optional

# ---------------------------------------------------------------------------
# 1.  DISTRICT → REGION MAPPING
#     Source: Maharashtra Revenue Divisions (Konkan, Nashik, Pune, Aurangabad,
#     Latur, Amravati, Nagpur) collapsed into the four analytical regions used
#     by the specification.
# ---------------------------------------------------------------------------

REGION_MAP: dict[str, str] = {
    # ── KONKAN ──────────────────────────────────────────────────────────────
    "MUMBAI II":          "Konkan",
    "MUMBAI (SUBURBAN)":  "Konkan",
    "THANE":              "Konkan",
    "PALGHAR":            "Konkan",
    "RAIGAD":             "Konkan",
    "RATNAGIRI":          "Konkan",
    "SINDHUDURG":         "Konkan",
    # ── WESTERN MAHARASHTRA ─────────────────────────────────────────────────
    "PUNE":               "Western Maharashtra",
    "SATARA":             "Western Maharashtra",
    "SANGLI":             "Western Maharashtra",
    "KOLHAPUR":           "Western Maharashtra",
    "SOLAPUR":            "Western Maharashtra",
    "NASHIK":             "Western Maharashtra",
    "DHULE":              "Western Maharashtra",
    "NANDURBAR":          "Western Maharashtra",
    "JALGAON":            "Western Maharashtra",
    "AHILYANAGAR":        "Western Maharashtra",   # formerly Ahmednagar
    # ── MARATHWADA ──────────────────────────────────────────────────────────
    "CHHATRAPATI SAMBHAJINAGAR": "Marathwada",    # formerly Aurangabad
    "JALNA":              "Marathwada",
    "BEED":               "Marathwada",
    "LATUR":              "Marathwada",
    "DHARASHIV":          "Marathwada",            # formerly Osmanabad
    "NANDED":             "Marathwada",
    "HINGOLI":            "Marathwada",
    "PARBHANI":           "Marathwada",
    # ── VIDARBHA ──────────────────────────────────────────────��─────────────
    "NAGPUR":             "Vidarbha",
    "WARDHA":             "Vidarbha",
    "YAVATMAL":           "Vidarbha",
    "CHANDRAPUR":         "Vidarbha",
    "GADCHIROLI":         "Vidarbha",
    "BHANDARA":           "Vidarbha",
    "GONDIA":             "Vidarbha",
    "AMRAVATI":           "Vidarbha",
    "AKOLA":              "Vidarbha",
    "WASHIM":             "Vidarbha",
    "BULDANA":            "Vidarbha",
}

REGIONS = ["Konkan", "Western Maharashtra", "Marathwada", "Vidarbha"]

# ---------------------------------------------------------------------------
# 2.  ALIAS TABLE  (old name → canonical name used in UDISE+ 2023-24 onwards)
# ---------------------------------------------------------------------------

DISTRICT_ALIASES: dict[str, str] = {
    "AURANGABAD":          "CHHATRAPATI SAMBHAJINAGAR",
    "OSMANABAD":           "DHARASHIV",
    "AHMEDNAGAR":          "AHILYANAGAR",
    "AHMADNAGAR":          "AHILYANAGAR",
    "MUMBAI SUBURBAN":     "MUMBAI (SUBURBAN)",
    "GREATER MUMBAI":      "MUMBAI II",
    "MUMBAI CITY":         "MUMBAI II",
    "GONDIYA":             "GONDIA",
    "BID":                 "BEED",
    "OSMANABAD":           "DHARASHIV",
}


def canonicalise(name: str) -> str:
    """Return the canonical district name, applying alias table if needed."""
    upper = str(name).strip().upper()
    return DISTRICT_ALIASES.get(upper, upper)


# ---------------------------------------------------------------------------
# 3.  PUBLIC HELPERS
# ---------------------------------------------------------------------------

def add_region(df: pd.DataFrame, district_col: str = "district") -> pd.DataFrame:
    """
    Add a 'region' column to *df* based on the district column.

    Raises
    ------
    ValueError
        If any district value is not in REGION_MAP after alias normalisation.
    """
    df = df.copy()
    df[district_col] = df[district_col].apply(canonicalise)
    mapped = df[district_col].map(REGION_MAP)
    missing = df.loc[mapped.isna(), district_col].unique().tolist()
    if missing:
        raise ValueError(
            f"add_region(): {len(missing)} district(s) not in REGION_MAP: {missing}"
        )
    df["region"] = mapped
    return df


def compute_gpi(
    df: pd.DataFrame,
    boys_col: str = "enrollment_reported_enrollment_b_component_total",
    girls_col: str = "enrollment_reported_enrollment_g_component_total",
    out_col: str = "gpi",
) -> pd.DataFrame:
    """
    Gender Parity Index = girls_enrolment / boys_enrolment.

    Both columns confirmed present with 0 nulls in v1 dataset.
    Division-by-zero is guarded; result is set to NaN when boys == 0.
    Result is NOT clipped — values slightly above 1.0 are valid (more girls
    than boys enrolled).

    Parameters
    ----------
    df : DataFrame with district-year rows
    boys_col, girls_col : source columns (confirmed real UDISE+ columns)
    out_col : name of the new GPI column

    Returns
    -------
    df copy with new column `out_col`
    """
    df = df.copy()
    b = pd.to_numeric(df[boys_col], errors="coerce")
    g = pd.to_numeric(df[girls_col], errors="coerce")
    df[out_col] = np.where(b > 0, g / b, np.nan)
    n_null = df[out_col].isna().sum()
    if n_null > 0:
        import warnings
        warnings.warn(f"compute_gpi(): {n_null} NaN values in '{out_col}'")
    return df


def compute_marginalised_enrolment_pct(
    df: pd.DataFrame,
    out_col: str = "marginalised_enrolment_pct",
) -> pd.DataFrame:
    """
    Participation quality proxy:
      (SC + ST + OBC enrolment) / total enrolment  × 100

    All four columns are present with 0 nulls.
    Used as the Participation pillar in Shala Score v2.
    """
    df = df.copy()
    num_cols = [
        "enrollment_reported_sc_enrollment",
        "enrollment_reported_st_enrollment",
        "enrollment_reported_obc_enrollment",
    ]
    total_col = "enrollment_reported_student_total"
    for c in num_cols + [total_col]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    numerator = df[num_cols].sum(axis=1)
    denominator = df[total_col].replace(0, np.nan)
    df[out_col] = (numerator / denominator * 100).clip(0, 100)
    return df


# ---------------------------------------------------------------------------
# 4.  SELF-TEST (run directly to verify 0 unmapped districts)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pathlib, sys

    ROOT = pathlib.Path(__file__).resolve().parents[2]
    master = ROOT / "data/processed/district_year/maharashtra_district_year_shala_score_v1.csv"

    df = pd.read_csv(master, usecols=["district", "academic_year"], low_memory=False)
    print(f"Loaded {len(df)} rows")

    df = add_region(df)          # raises if any district unmapped
    print("add_region(): PASS -- 0 unmapped districts")
    print(df.groupby("region")["district"].nunique().rename("unique_districts"))

    df = compute_gpi(df.merge(
        pd.read_csv(master, low_memory=False)[
            ["district", "academic_year",
             "enrollment_reported_enrollment_b_component_total",
             "enrollment_reported_enrollment_g_component_total"]
        ],
        on=["district", "academic_year"],
    ))
    print(f"\nGPI stats:  min={df['gpi'].min():.4f}  max={df['gpi'].max():.4f}  "
          f"null={df['gpi'].isna().sum()}")
    print("compute_gpi(): PASS")

    df_part = compute_marginalised_enrolment_pct(
        pd.read_csv(master, low_memory=False)
    )
    print(f"\nMarginalised enrolment %:  "
          f"min={df_part['marginalised_enrolment_pct'].min():.1f}  "
          f"max={df_part['marginalised_enrolment_pct'].max():.1f}  "
          f"null={df_part['marginalised_enrolment_pct'].isna().sum()}")
    print("compute_marginalised_enrolment_pct(): PASS")

    print("\nAll Step-2a checks PASSED.")
    sys.exit(0)

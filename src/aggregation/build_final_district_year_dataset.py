
from pathlib import Path
import pandas as pd
import re

# ============================================================
# SHALASCOPE MAHARASHTRA
# FINAL DISTRICT-YEAR DATASET INTEGRATION
#
# Inputs:
# 1. Core District-Year Master
# 2. Enrollment District-Year Features
#
# Expected:
# 36 districts x 8 academic years = 288 records
#
# Original datasets remain unchanged.
# ============================================================


# ------------------------------------------------------------
# 1. PATHS
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

CORE_FILE = (
    ROOT
    / "data"
    / "processed"
    / "district_year"
    / "maharashtra_district_year_core_master.csv"
)

ENROLLMENT_FILE = (
    ROOT
    / "data"
    / "processed"
    / "district_year"
    / "maharashtra_district_year_enrollment_features.csv"
)

OUTPUT_DIR = (
    ROOT
    / "data"
    / "processed"
    / "district_year"
)

REPORT_DIR = (
    ROOT
    / "reports"
    / "data_audit"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ------------------------------------------------------------
# 2. EXPECTED CONFIGURATION
# ------------------------------------------------------------

YEARS = [
    "2018-19",
    "2019-20",
    "2020-21",
    "2021-22",
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
]

EXPECTED_DISTRICTS = 36
EXPECTED_ROWS = len(YEARS) * EXPECTED_DISTRICTS


# ------------------------------------------------------------
# 3. HELPER FUNCTIONS
# ------------------------------------------------------------

def find_column(columns, candidates):

    lookup = {
        str(col).strip().lower(): col
        for col in columns
    }

    for candidate in candidates:

        key = candidate.strip().lower()

        if key in lookup:
            return lookup[key]

    return None


def normalize_district(series):

    return (
        series.astype("string")
        .str.strip()
        .str.upper()
        .str.replace(
            r"\s+",
            " ",
            regex=True,
        )
    )


def prepare_keys(df, label):

    year_col = find_column(
        df.columns,
        [
            "academic_year",
            "year",
        ],
    )

    district_col = find_column(
        df.columns,
        [
            "district",
            "district_std",
            "district_name",
            "district_standardized",
        ],
    )

    if year_col is None:

        raise ValueError(
            f"{label}: Academic year column missing."
        )

    if district_col is None:

        raise ValueError(
            f"{label}: District column missing."
        )

    result = df.copy()

    result["_join_year"] = (
        result[year_col]
        .astype("string")
        .str.strip()
    )

    result["_join_district"] = normalize_district(
        result[district_col]
    )

    keys = [
        "_join_year",
        "_join_district",
    ]

    if result[keys].isna().any().any():

        raise ValueError(
            f"{label}: Missing district/year join keys."
        )

    if result[keys].eq("").any().any():

        raise ValueError(
            f"{label}: Blank district/year join keys."
        )

    return result, year_col, district_col


def validate_source(df, label):

    key_cols = [
        "_join_year",
        "_join_district",
    ]

    duplicate_count = df.duplicated(
        subset=key_cols
    ).sum()

    if duplicate_count:

        raise ValueError(
            f"{label}: Duplicate district-year keys: "
            f"{duplicate_count}"
        )

    found_years = sorted(
        df["_join_year"].unique().tolist()
    )

    if found_years != sorted(YEARS):

        raise ValueError(
            f"{label}: Academic year mismatch: "
            f"{found_years}"
        )

    district_counts = (
        df.groupby("_join_year")["_join_district"]
        .nunique()
    )

    invalid = district_counts[
        district_counts != EXPECTED_DISTRICTS
    ]

    if not invalid.empty:

        raise ValueError(
            f"{label}: District count validation failed:\n"
            f"{invalid}"
        )

    print(f"{label}: PASS")


def numeric_series(series):

    return pd.to_numeric(
        series,
        errors="coerce",
    )


# ============================================================
# 4. MAIN PIPELINE
# ============================================================

print("\n" + "=" * 70)
print("SHALASCOPE - FINAL DISTRICT-YEAR DATASET INTEGRATION")
print("=" * 70)


# ------------------------------------------------------------
# STEP 1: INPUT FILE CHECK
# ------------------------------------------------------------

print("\nSTEP 1: CHECKING INPUT FILES")

if not CORE_FILE.exists():

    raise FileNotFoundError(
        f"Core dataset not found:\n{CORE_FILE}"
    )

if not ENROLLMENT_FILE.exists():

    raise FileNotFoundError(
        f"Enrollment dataset not found:\n{ENROLLMENT_FILE}"
    )


# ------------------------------------------------------------
# STEP 2: LOAD DATASETS
# ------------------------------------------------------------

print("\nSTEP 2: LOADING DATASETS")

core = pd.read_csv(
    CORE_FILE,
    low_memory=False,
    encoding="utf-8-sig",
)

enrollment = pd.read_csv(
    ENROLLMENT_FILE,
    low_memory=False,
    encoding="utf-8-sig",
)

core_original_columns = len(core.columns)
enrollment_original_columns = len(enrollment.columns)

print(f"Core rows: {len(core):,}")
print(f"Enrollment rows: {len(enrollment):,}")
print(f"Core columns: {core_original_columns:,}")
print(f"Enrollment columns: {enrollment_original_columns:,}")


# ------------------------------------------------------------
# STEP 3: PREPARE JOIN KEYS
# ------------------------------------------------------------

print("\nSTEP 3: PREPARING JOIN KEYS")

core, core_year_col, core_district_col = prepare_keys(
    core,
    "Core dataset",
)

enrollment, enrollment_year_col, enrollment_district_col = (
    prepare_keys(
        enrollment,
        "Enrollment dataset",
    )
)

validate_source(
    core,
    "Core dataset validation",
)

validate_source(
    enrollment,
    "Enrollment dataset validation",
)


# ------------------------------------------------------------
# STEP 4: CHECK DISTRICT-YEAR KEY MATCH
# ------------------------------------------------------------

print("\nSTEP 4: MATCHING DISTRICT-YEAR KEYS")

JOIN_KEYS = [
    "_join_year",
    "_join_district",
]

core_keys = core[JOIN_KEYS].drop_duplicates()
enrollment_keys = enrollment[JOIN_KEYS].drop_duplicates()

key_check = core_keys.merge(
    enrollment_keys,
    on=JOIN_KEYS,
    how="outer",
    indicator=True,
    validate="one_to_one",
)

mismatches = key_check[
    key_check["_merge"] != "both"
].copy()

mismatch_file = (
    REPORT_DIR
    / "final_dataset_integration_key_mismatches.csv"
)

mismatches.to_csv(
    mismatch_file,
    index=False,
    encoding="utf-8-sig",
)

if not mismatches.empty:

    print(mismatches.to_string(index=False))

    raise ValueError(
        "Core and Enrollment district-year keys do not match. "
        f"Check: {mismatch_file}"
    )

matched_keys = len(key_check)

if matched_keys != EXPECTED_ROWS:

    raise ValueError(
        f"Expected {EXPECTED_ROWS} matched keys, "
        f"found {matched_keys}."
    )

print(f"Matched district-year keys: {matched_keys}")
print("District-Year key matching: PASS")


# ------------------------------------------------------------
# STEP 5: PREPARE ENROLLMENT COLUMNS
# ------------------------------------------------------------

print("\nSTEP 5: PREPARING ENROLLMENT FEATURES")

# Remove the original display key columns.
# Keep temporary join keys.
enrollment_features = enrollment.drop(
    columns=[
        enrollment_year_col,
        enrollment_district_col,
    ],
    errors="ignore",
).copy()


# Prefix Enrollment fields consistently.
rename_map = {}

for col in enrollment_features.columns:

    if col in JOIN_KEYS:
        continue

    if str(col).startswith("enrollment_"):

        new_name = str(col)

    else:

        new_name = f"enrollment_{col}"

    # Avoid collisions with existing Core columns.
    if new_name in core.columns:

        new_name = (
            f"enrollment_feature_{col}"
        )

    rename_map[col] = new_name


enrollment_features = enrollment_features.rename(
    columns=rename_map
)


# Check join keys are retained.
missing_keys = [
    col
    for col in JOIN_KEYS
    if col not in enrollment_features.columns
]

if missing_keys:

    raise ValueError(
        f"Enrollment join keys missing: {missing_keys}"
    )


# Check duplicate Enrollment feature keys.
if enrollment_features.duplicated(
    subset=JOIN_KEYS
).any():

    raise ValueError(
        "Duplicate Enrollment district-year keys found."
    )


# Check name collisions after prefixing.
core_non_key = (
    set(core.columns)
    - set(JOIN_KEYS)
)

enrollment_non_key = (
    set(enrollment_features.columns)
    - set(JOIN_KEYS)
)

collisions = (
    core_non_key
    & enrollment_non_key
)

if collisions:

    raise ValueError(
        f"Column collisions found: {sorted(collisions)}"
    )

print("Enrollment columns prepared: PASS")
print("Enrollment column prefix validation: PASS")


# ------------------------------------------------------------
# STEP 6: MERGE CORE + ENROLLMENT
# ------------------------------------------------------------

print("\nSTEP 6: MERGING DATASETS")

final_df = core.merge(
    enrollment_features,
    on=JOIN_KEYS,
    how="left",
    validate="one_to_one",
    indicator="_enrollment_merge",
)

final_df["enrollment_dataset_merge_status"] = (
    final_df["_enrollment_merge"].map({
        "both": "MATCHED",
        "left_only": "ENROLLMENT_NOT_FOUND",
        "right_only": "UNEXPECTED_ENROLLMENT_RECORD",
    })
)

unmatched_count = int(
    final_df[
        "enrollment_dataset_merge_status"
    ].ne("MATCHED").sum()
)

final_df = final_df.drop(
    columns=[
        "_enrollment_merge",
        "_join_year",
        "_join_district",
    ]
)

if unmatched_count:

    raise ValueError(
        f"Enrollment unmatched rows: {unmatched_count}"
    )

print(f"Merged rows: {len(final_df):,}")
print(f"Matched Enrollment rows: {len(final_df):,}")
print(f"Unmatched rows: {unmatched_count}")


# ------------------------------------------------------------
# STEP 7: VALIDATE SCHOOL COUNTS
# ------------------------------------------------------------

print("\nSTEP 7: SCHOOL COUNT RECONCILIATION")

enrollment_count_col = (
    "enrollment_total_schools"
)

count_comparison_results = []

if enrollment_count_col in final_df.columns:

    enrollment_counts = numeric_series(
        final_df[enrollment_count_col]
    )

    for candidate in [
        "total_schools",
        "school_count",
        "facility_total_schools",
    ]:

        if candidate not in final_df.columns:
            continue

        reference_counts = numeric_series(
            final_df[candidate]
        )

        comparable = (
            enrollment_counts.notna()
            & reference_counts.notna()
        )

        mismatch_count = int(
            (
                enrollment_counts[comparable]
                != reference_counts[comparable]
            ).sum()
        )

        comparison_record = {
            "reference_column": candidate,
            "enrollment_count_column": enrollment_count_col,
            "comparable_records": int(
                comparable.sum()
            ),
            "mismatch_records": mismatch_count,
            "status": (
                "PASS"
                if mismatch_count == 0
                else "REVIEW"
            ),
        }

        count_comparison_results.append(
            comparison_record
        )

        print(
            f"{candidate} vs {enrollment_count_col}: "
            f"{mismatch_count} mismatches"
        )

else:

    print(
        "Enrollment school count column not found; "
        "comparison skipped."
    )


count_comparison_file = (
    REPORT_DIR
    / "final_dataset_school_count_comparison.csv"
)

pd.DataFrame(
    count_comparison_results
).to_csv(
    count_comparison_file,
    index=False,
    encoding="utf-8-sig",
)


# ------------------------------------------------------------
# STEP 8: FINAL RECORD VALIDATION
# ------------------------------------------------------------

print("\nSTEP 8: FINAL DATASET VALIDATION")

if len(final_df) != EXPECTED_ROWS:

    raise ValueError(
        f"Expected {EXPECTED_ROWS} final records, "
        f"found {len(final_df)}."
    )


if final_df.duplicated(
    subset=[
        core_year_col,
        core_district_col,
    ]
).any():

    raise ValueError(
        "Duplicate final district-year records found."
    )


year_counts = (
    final_df.groupby(core_year_col)
    .size()
)

if len(year_counts) != len(YEARS):

    raise ValueError(
        "Expected 8 academic years."
    )

invalid_years = year_counts[
    year_counts != EXPECTED_DISTRICTS
]

if not invalid_years.empty:

    raise ValueError(
        f"District count mismatch:\n{invalid_years}"
    )


unique_districts = final_df[
    core_district_col
].nunique()

if unique_districts != EXPECTED_DISTRICTS:

    raise ValueError(
        f"Expected 36 districts, "
        f"found {unique_districts}."
    )


if not final_df[
    "enrollment_dataset_merge_status"
].eq("MATCHED").all():

    raise ValueError(
        "Some Enrollment dataset rows were not matched."
    )


print("Final rows validation: PASS")
print("Academic year validation: PASS")
print("36-district validation: PASS")
print("Duplicate validation: PASS")
print("Enrollment merge validation: PASS")


# ------------------------------------------------------------
# STEP 9: SAVE FINAL MASTER DATASET
# ------------------------------------------------------------

print("\nSTEP 9: SAVING FINAL MASTER DATASET")

FINAL_FILE = (
    OUTPUT_DIR
    / "maharashtra_district_year_final_master.csv"
)

final_df.to_csv(
    FINAL_FILE,
    index=False,
    encoding="utf-8-sig",
)

print(f"Saved: {FINAL_FILE}")


# ------------------------------------------------------------
# STEP 10: COLUMN INVENTORY
# ------------------------------------------------------------

print("\nSTEP 10: CREATING COLUMN INVENTORY")

inventory_rows = []

for col in final_df.columns:

    inventory_rows.append({
        "column_name": col,
        "data_type": str(final_df[col].dtype),
        "non_null_count": int(
            final_df[col].notna().sum()
        ),
        "missing_count": int(
            final_df[col].isna().sum()
        ),
        "missing_percentage": round(
            final_df[col].isna().mean() * 100,
            2,
        ),
    })


column_inventory = pd.DataFrame(
    inventory_rows
)

column_inventory_file = (
    REPORT_DIR
    / "final_dataset_column_inventory.csv"
)

column_inventory.to_csv(
    column_inventory_file,
    index=False,
    encoding="utf-8-sig",
)


# ------------------------------------------------------------
# STEP 11: YEAR-WISE SUMMARY
# ------------------------------------------------------------

print("\nSTEP 11: CREATING YEAR-WISE SUMMARY")

yearly_rows = []

for year in YEARS:

    group = final_df[
        final_df[core_year_col].astype(str) == year
    ]

    available_col = (
        "enrollment_reporting_schools"
    )

    if available_col not in group.columns:

        available_col = None

    reporting_schools = (
        int(
            pd.to_numeric(
                group[available_col],
                errors="coerce",
            ).fillna(0).sum()
        )
        if available_col
        else None
    )

    yearly_rows.append({
        "academic_year": year,
        "districts": group[core_district_col].nunique(),
        "records": len(group),
        "total_columns": len(final_df.columns),
        "enrollment_reporting_schools": reporting_schools,
        "enrollment_matched_districts": int(
            group[
                "enrollment_dataset_merge_status"
            ].eq("MATCHED").sum()
        ),
    })


yearly_summary = pd.DataFrame(
    yearly_rows
)

yearly_summary_file = (
    REPORT_DIR
    / "final_dataset_yearwise_summary.csv"
)

yearly_summary.to_csv(
    yearly_summary_file,
    index=False,
    encoding="utf-8-sig",
)


# ------------------------------------------------------------
# STEP 12: OVERALL SUMMARY
# ------------------------------------------------------------

summary = pd.DataFrame([{
    "core_source_rows": len(core),
    "enrollment_source_rows": len(enrollment),
    "final_rows": len(final_df),
    "expected_rows": EXPECTED_ROWS,
    "unique_districts": unique_districts,
    "academic_years": final_df[core_year_col].nunique(),
    "core_source_columns": core_original_columns,
    "enrollment_source_columns": enrollment_original_columns,
    "final_columns": len(final_df.columns),
    "matched_enrollment_rows": len(final_df) - unmatched_count,
    "unmatched_enrollment_rows": unmatched_count,
    "duplicate_district_year_records": int(
        final_df.duplicated(
            [
                core_year_col,
                core_district_col,
            ]
        ).sum()
    ),
    "status": "PASS",
}])

summary_file = (
    REPORT_DIR
    / "final_dataset_integration_summary.csv"
)

summary.to_csv(
    summary_file,
    index=False,
    encoding="utf-8-sig",
)


# ------------------------------------------------------------
# STEP 13: FINAL RESULT
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("SHALASCOPE FINAL DATASET - RESULT")
print("=" * 70)

print(f"Core rows: {len(core):,}")
print(f"Enrollment rows: {len(enrollment):,}")
print(f"Final rows: {len(final_df):,}")
print(f"Final columns: {len(final_df.columns):,}")

print(f"Academic years: {len(YEARS)}")
print(f"Unique districts: {unique_districts}")

print(f"Matched Enrollment rows: {len(final_df) - unmatched_count}")
print(f"Unmatched Enrollment rows: {unmatched_count}")

print(
    "Duplicate District-Year records:",
    final_df.duplicated(
        [
            core_year_col,
            core_district_col,
        ]
    ).sum()
)

print("\nYEAR-WISE SUMMARY:")

print(
    yearly_summary.to_string(index=False)
)

print("\nOUTPUT FILES:")

print(FINAL_FILE)
print(summary_file)
print(yearly_summary_file)
print(column_inventory_file)
print(count_comparison_file)
print(mismatch_file)

print("\n" + "=" * 70)
print("FINAL DISTRICT-YEAR DATASET INTEGRATION COMPLETED")
print("STATUS: PASS")
print("=" * 70)

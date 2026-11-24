
from pathlib import Path
import pandas as pd


# ============================================================
# SHALASCOPE MAHARASHTRA
# CORE DISTRICT-YEAR DATASET INTEGRATION
#
# Integrates:
# 1. Existing District-Year Master
# 2. District-Year Facility Features
#
# Expected:
# 36 districts x 8 academic years = 288 records
# ============================================================


# ------------------------------------------------------------
# 1. PROJECT PATHS
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

BASE_FILE = (
    ROOT
    / "data"
    / "processed"
    / "district_year"
    / "maharashtra_district_year_master.csv"
)

FACILITY_FILE = (
    ROOT
    / "data"
    / "processed"
    / "district_year"
    / "maharashtra_district_year_facility_features.csv"
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

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 2. EXPECTED DATASET CONFIGURATION
# ------------------------------------------------------------

EXPECTED_YEARS = [
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

EXPECTED_ROWS = (
    len(EXPECTED_YEARS)
    * EXPECTED_DISTRICTS
)


# ------------------------------------------------------------
# 3. HELPER FUNCTIONS
# ------------------------------------------------------------

def find_column(columns, candidates):
    """
    Find a column using case-insensitive exact matching.
    """

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
    """
    Normalize district labels for safe joining.
    """

    return (
        series.astype("string")
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
    )


def prepare_keys(df, label):
    """
    Create temporary academic-year and district join keys.
    Original source columns are preserved.
    """

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
        ],
    )

    if year_col is None:
        raise ValueError(
            f"{label}: Academic year column not found."
        )

    if district_col is None:
        raise ValueError(
            f"{label}: District column not found."
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

    join_keys = [
        "_join_year",
        "_join_district",
    ]

    if result[join_keys].isna().any().any():
        raise ValueError(
            f"{label}: Missing year or district join keys."
        )

    blank_keys = (
        result[join_keys]
        .eq("")
        .any()
        .any()
    )

    if blank_keys:
        raise ValueError(
            f"{label}: Blank year or district join keys."
        )

    return result, year_col, district_col


def validate_source_keys(df, label):
    """
    Validate uniqueness, year coverage and district coverage.
    """

    join_keys = [
        "_join_year",
        "_join_district",
    ]

    duplicates = df.duplicated(
        subset=join_keys
    ).sum()

    if duplicates > 0:
        raise ValueError(
            f"{label}: {duplicates} duplicate District-Year keys."
        )

    years_found = sorted(
        df["_join_year"].dropna().unique().tolist()
    )

    if years_found != sorted(EXPECTED_YEARS):
        raise ValueError(
            f"{label}: Unexpected academic years: {years_found}"
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
            f"{label}: Expected 36 districts in every year.\n"
            f"{invalid}"
        )

    print(f"{label} source validation: PASS")


# ============================================================
# 4. MAIN INTEGRATION PIPELINE
# ============================================================

print("\n" + "=" * 70)
print("SHALASCOPE - CORE DISTRICT-YEAR DATASET INTEGRATION")
print("=" * 70)


# ------------------------------------------------------------
# STEP 1: CHECK INPUT FILES
# ------------------------------------------------------------

if not BASE_FILE.exists():
    raise FileNotFoundError(
        f"Base dataset not found:\n{BASE_FILE}"
    )

if not FACILITY_FILE.exists():
    raise FileNotFoundError(
        f"Facility dataset not found:\n{FACILITY_FILE}"
    )


# ------------------------------------------------------------
# STEP 2: LOAD DATASETS
# ------------------------------------------------------------

print("\nSTEP 1: LOADING DATASETS")

base = pd.read_csv(
    BASE_FILE,
    low_memory=False,
    encoding="utf-8-sig",
)

facility = pd.read_csv(
    FACILITY_FILE,
    low_memory=False,
    encoding="utf-8-sig",
)

base_column_count = len(base.columns)
facility_column_count = len(facility.columns)

print(f"Base dataset rows: {len(base):,}")
print(f"Facility dataset rows: {len(facility):,}")
print(f"Base columns: {base_column_count:,}")
print(f"Facility columns: {facility_column_count:,}")


# ------------------------------------------------------------
# STEP 3: PREPARE DISTRICT-YEAR KEYS
# ------------------------------------------------------------

print("\nSTEP 2: PREPARING JOIN KEYS")

base, base_year_col, base_district_col = prepare_keys(
    base,
    "Base dataset",
)

facility, facility_year_col, facility_district_col = prepare_keys(
    facility,
    "Facility dataset",
)

validate_source_keys(
    base,
    "Base dataset",
)

validate_source_keys(
    facility,
    "Facility dataset",
)


# ------------------------------------------------------------
# STEP 4: MATCH DISTRICT-YEAR KEYS
# ------------------------------------------------------------

print("\nSTEP 3: CHECKING DISTRICT-YEAR MATCHES")

base_keys = base[
    [
        "_join_year",
        "_join_district",
    ]
].drop_duplicates()

facility_keys = facility[
    [
        "_join_year",
        "_join_district",
    ]
].drop_duplicates()

key_check = base_keys.merge(
    facility_keys,
    on=[
        "_join_year",
        "_join_district",
    ],
    how="outer",
    indicator=True,
    validate="one_to_one",
)

mismatch = key_check[
    key_check["_merge"] != "both"
].copy()

mismatch_file = (
    REPORT_DIR
    / "core_dataset_integration_key_mismatches.csv"
)

mismatch.to_csv(
    mismatch_file,
    index=False,
    encoding="utf-8-sig",
)

if not mismatch.empty:

    print("\nDISTRICT-YEAR KEY MISMATCHES:")

    print(
        mismatch.to_string(index=False)
    )

    raise ValueError(
        "Base and Facility keys do not fully match. "
        f"Check report: {mismatch_file}"
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
# STEP 5: PREFIX FACILITY COLUMNS - CORRECTED
# ------------------------------------------------------------

print("\nSTEP 4: PREPARING FACILITY FEATURES")

# Keep temporary join keys.
# Remove only the original year and district display columns.

facility_features = facility.drop(
    columns=[
        facility_year_col,
        facility_district_col,
    ],
    errors="ignore",
).copy()


# Prefix all Facility feature columns.
# Preserve temporary join keys WITHOUT prefix.

rename_map = {}

for col in facility_features.columns:

    if col not in [
        "_join_year",
        "_join_district",
    ]:

        rename_map[col] = f"facility_{col}"


facility_features = facility_features.rename(
    columns=rename_map
)


# Check required join keys.

required_join_keys = [
    "_join_year",
    "_join_district",
]

missing_join_keys = [
    col
    for col in required_join_keys
    if col not in facility_features.columns
]

if missing_join_keys:
    raise ValueError(
        f"Facility merge keys missing: {missing_join_keys}"
    )


# Check duplicate keys.

facility_duplicate_keys = facility_features.duplicated(
    subset=required_join_keys
).sum()

if facility_duplicate_keys > 0:
    raise ValueError(
        f"Duplicate Facility keys: {facility_duplicate_keys}"
    )


# Check column collisions.

base_non_key_columns = set(base.columns) - set(required_join_keys)

facility_non_key_columns = (
    set(facility_features.columns)
    - set(required_join_keys)
)

column_collisions = (
    base_non_key_columns
    & facility_non_key_columns
)

if column_collisions:
    raise ValueError(
        "Column name collisions detected:\n"
        f"{sorted(column_collisions)}"
    )

print("Facility join keys preserved: PASS")
print("Facility columns prefixed: PASS")
print("Column collision validation: PASS")


# ------------------------------------------------------------
# STEP 6: MERGE BASE AND FACILITY DATASETS
# ------------------------------------------------------------

print("\nSTEP 5: MERGING DATASETS")

merged = base.merge(
    facility_features,
    on=[
        "_join_year",
        "_join_district",
    ],
    how="left",
    validate="one_to_one",
    indicator="_facility_merge",
)


# Add merge status.

merged["facility_merge_status"] = (
    merged["_facility_merge"]
    .map({
        "both": "MATCHED",
        "left_only": "FACILITY_NOT_FOUND",
        "right_only": "UNEXPECTED_FACILITY_RECORD",
    })
)


unmatched_rows = int(
    merged["facility_merge_status"]
    .ne("MATCHED")
    .sum()
)


# Remove temporary columns.

merged = merged.drop(
    columns=[
        "_facility_merge",
        "_join_year",
        "_join_district",
    ],
)


if unmatched_rows > 0:
    raise ValueError(
        f"Facility merge incomplete. "
        f"Unmatched records: {unmatched_rows}"
    )


print(f"Merged records: {len(merged):,}")
print(f"Matched records: {len(merged):,}")
print(f"Unmatched records: {unmatched_rows}")
print("Facility merge validation: PASS")


# ------------------------------------------------------------
# STEP 7: COMPARE SCHOOL COUNTS
# ------------------------------------------------------------

print("\nSTEP 6: SCHOOL COUNT VALIDATION")

base_school_col = find_column(
    base.columns,
    [
        "total_schools",
        "school_count",
    ],
)

facility_school_col = "facility_total_schools"

school_count_mismatches = "NOT_COMPARABLE"
school_count_comparable = 0

if (
    base_school_col is not None
    and facility_school_col in merged.columns
):

    base_counts = pd.to_numeric(
        merged[base_school_col],
        errors="coerce",
    )

    facility_counts = pd.to_numeric(
        merged[facility_school_col],
        errors="coerce",
    )

    comparable = (
        base_counts.notna()
        & facility_counts.notna()
    )

    school_count_comparable = int(
        comparable.sum()
    )

    comparison = (
        base_counts.eq(facility_counts)
        & comparable
    )

    school_count_mismatches = int(
        (
            ~comparison
            & comparable
        ).sum()
    )

    merged["facility_school_count_match"] = (
        comparison.where(comparable)
    )

    print(
        f"Comparable school-count records: "
        f"{school_count_comparable}"
    )

    print(
        f"School-count mismatches: "
        f"{school_count_mismatches}"
    )

else:

    print(
        "School count comparison: NOT COMPARABLE "
        "(required fields not found)"
    )


# ------------------------------------------------------------
# STEP 8: FINAL DATASET VALIDATION
# ------------------------------------------------------------

print("\nSTEP 7: FINAL DATASET VALIDATION")

if len(merged) != EXPECTED_ROWS:
    raise ValueError(
        f"Expected {EXPECTED_ROWS} records, "
        f"found {len(merged)}."
    )


# Year-wise validation.

year_counts = (
    merged.groupby(base_year_col)
    .size()
)

if len(year_counts) != len(EXPECTED_YEARS):
    raise ValueError(
        "Academic year count is not 8."
    )

invalid_year_counts = year_counts[
    year_counts != EXPECTED_DISTRICTS
]

if not invalid_year_counts.empty:
    raise ValueError(
        "Invalid district counts by year:\n"
        f"{invalid_year_counts}"
    )


# District validation.

unique_districts = merged[
    base_district_col
].nunique()

if unique_districts != EXPECTED_DISTRICTS:
    raise ValueError(
        f"Expected 36 unique districts, "
        f"found {unique_districts}."
    )


# Duplicate district-year validation.

duplicate_records = merged.duplicated(
    subset=[
        base_year_col,
        base_district_col,
    ]
).sum()

if duplicate_records > 0:
    raise ValueError(
        f"Duplicate district-year records: {duplicate_records}"
    )


# Facility merge status validation.

matched_status_count = int(
    merged["facility_merge_status"]
    .eq("MATCHED")
    .sum()
)

if matched_status_count != EXPECTED_ROWS:
    raise ValueError(
        "Not all Facility records have matched."
    )


print("Merged row count validation: PASS")
print("Academic year validation: PASS")
print("36 district validation: PASS")
print("Duplicate District-Year validation: PASS")
print("Facility match validation: PASS")


# ------------------------------------------------------------
# STEP 9: SAVE CORE MASTER DATASET
# ------------------------------------------------------------

print("\nSTEP 8: SAVING CORE MASTER DATASET")

output_file = (
    OUTPUT_DIR
    / "maharashtra_district_year_core_master.csv"
)

merged.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig",
)

print(f"Saved: {output_file}")


# ------------------------------------------------------------
# STEP 10: SAVE COLUMN INVENTORY
# ------------------------------------------------------------

print("\nSTEP 9: CREATING COLUMN INVENTORY")

inventory_rows = []

for col in merged.columns:

    inventory_rows.append({
        "column_name": col,
        "data_type": str(merged[col].dtype),
        "non_null_count": int(
            merged[col].notna().sum()
        ),
        "missing_count": int(
            merged[col].isna().sum()
        ),
        "missing_percentage": round(
            merged[col].isna().mean() * 100,
            2,
        ),
    })


inventory = pd.DataFrame(
    inventory_rows
)

inventory_file = (
    REPORT_DIR
    / "core_dataset_column_inventory.csv"
)

inventory.to_csv(
    inventory_file,
    index=False,
    encoding="utf-8-sig",
)


# ------------------------------------------------------------
# STEP 11: SAVE YEAR-WISE INTEGRATION SUMMARY
# ------------------------------------------------------------

yearly_rows = []

for year in EXPECTED_YEARS:

    year_data = merged[
        merged[base_year_col].astype(str) == year
    ]

    yearly_rows.append({
        "academic_year": year,
        "districts": year_data[base_district_col].nunique(),
        "merged_records": len(year_data),
        "facility_matched_records": int(
            year_data["facility_merge_status"]
            .eq("MATCHED")
            .sum()
        ),
        "facility_unmatched_records": int(
            year_data["facility_merge_status"]
            .ne("MATCHED")
            .sum()
        ),
        "duplicate_records": int(
            year_data.duplicated(
                subset=[
                    base_year_col,
                    base_district_col,
                ]
            ).sum()
        ),
    })


yearly_summary = pd.DataFrame(
    yearly_rows
)

yearly_summary_file = (
    REPORT_DIR
    / "core_dataset_yearwise_integration_summary.csv"
)

yearly_summary.to_csv(
    yearly_summary_file,
    index=False,
    encoding="utf-8-sig",
)


# ------------------------------------------------------------
# STEP 12: SAVE OVERALL INTEGRATION SUMMARY
# ------------------------------------------------------------

summary = pd.DataFrame([{
    "base_rows": len(base),
    "facility_rows": len(facility),
    "merged_rows": len(merged),
    "expected_rows": EXPECTED_ROWS,
    "unique_districts": unique_districts,
    "academic_years": merged[base_year_col].nunique(),
    "base_columns": base_column_count,
    "facility_source_columns": facility_column_count,
    "merged_columns": len(merged.columns),
    "matched_facility_rows": matched_status_count,
    "unmatched_facility_rows": unmatched_rows,
    "school_count_comparable_records": school_count_comparable,
    "school_count_mismatches": school_count_mismatches,
    "duplicate_district_year_records": int(
        duplicate_records
    ),
    "status": "PASS",
}])


summary_file = (
    REPORT_DIR
    / "core_dataset_integration_summary.csv"
)

summary.to_csv(
    summary_file,
    index=False,
    encoding="utf-8-sig",
)


# ------------------------------------------------------------
# STEP 13: FINAL REPORT
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("CORE DISTRICT-YEAR INTEGRATION - FINAL RESULT")
print("=" * 70)

print(f"Base dataset rows: {len(base):,}")
print(f"Facility dataset rows: {len(facility):,}")
print(f"Merged dataset rows: {len(merged):,}")
print(f"Merged dataset columns: {len(merged.columns):,}")

print(f"Expected rows: {EXPECTED_ROWS}")
print(f"Unique districts: {unique_districts}")
print(f"Academic years: {merged[base_year_col].nunique()}")

print(f"Matched Facility records: {matched_status_count}")
print(f"Unmatched Facility records: {unmatched_rows}")

print(f"Duplicate District-Year records: {duplicate_records}")

print("\nYEAR-WISE SUMMARY:")

print(
    yearly_summary.to_string(index=False)
)


print("\nOUTPUT FILES:")

print("\nCORE MASTER DATASET:")
print(output_file)

print("\nAUDIT REPORTS:")
print(summary_file)
print(yearly_summary_file)
print(inventory_file)
print(mismatch_file)


print("\n" + "=" * 70)
print("CORE DISTRICT-YEAR DATASET INTEGRATION COMPLETED")
print("STATUS: PASS")
print("=" * 70)

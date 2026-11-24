
from pathlib import Path
import re
import numpy as np
import pandas as pd


# ============================================================
# SHALASCOPE MAHARASHTRA
# FACILITY FEATURE ENGINEERING - PHASE 1
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = ROOT / "data" / "processed" / "school_year_integrated"
OUTPUT_DIR = ROOT / "data" / "processed" / "school_year_features" / "facility"
REPORT_DIR = ROOT / "reports" / "data_audit"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

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


# ------------------------------------------------------------
# 1. SOURCE FIELD ALIASES
# ------------------------------------------------------------

FIELD_ALIASES = {
    "total_boys_toilet": [
        "total_boys_toilet",
    ],
    "total_girls_toilet": [
        "total_girls_toilet",
    ],
    "total_boys_func_toilet": [
        "total_boys_func_toilet",
        "total_boys_functional_toilet",
    ],
    "total_girls_func_toilet": [
        "total_girls_func_toilet",
        "total_girls_functional_toilet",
    ],
    "no_building_blocks": [
        "no_building_blocks",
    ],
    "pucca_building_blocks": [
        "pucca_building_blocks",
    ],
    "total_class_rooms": [
        "total_class_rooms",
        "total_classrooms",
    ],
    "classrooms_in_good_condition": [
        "classrooms_in_good_condition",
    ],
    "classrooms_needs_minor_repair": [
        "classrooms_needs_minor_repair",
        "classrooms_need_minor_repair",
    ],
    "classrooms_needs_major_repair": [
        "classrooms_needs_major_repair",
        "classrooms_need_major_repair",
    ],
    "desktop": [
        "desktop",
    ],
    "laptop": [
        "laptop",
    ],
    "tablet": [
        "tablet",
    ],
    "printer": [
        "printer",
    ],
    "projector": [
        "projector",
    ],
}


# ------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ------------------------------------------------------------

def normalize_name(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def find_column(columns, candidates):
    normalized = {
        col: normalize_name(col)
        for col in columns
    }

    # First preference: exact match
    for candidate in candidates:
        target = normalize_name(candidate)

        for col, name in normalized.items():
            if name == target:
                return col

    # Second preference: prefixed column match
    for candidate in candidates:
        target = normalize_name(candidate)

        for col, name in normalized.items():
            if name.endswith(target):
                return col

    return None


def find_facility_column(columns, aliases):
    targets = {
        normalize_name(alias)
        for alias in aliases
    }

    preferred = []
    fallback = []

    for col in columns:
        name = normalize_name(col)
        stripped = name

        # Integrated dataset uses facility__ prefix.
        if stripped.startswith("facility"):
            stripped = stripped[len("facility"):]

        elif stripped.startswith("fac"):
            stripped = stripped[len("fac"):]

        if stripped in targets:
            preferred.append(col)

        elif name in targets:
            fallback.append(col)

    if preferred:
        return preferred[0]

    if fallback:
        return fallback[0]

    return None


def numeric_count(series):
    values = pd.to_numeric(series, errors="coerce")
    negative_count = int((values < 0).sum())

    # Negative counts are not valid quantities.
    values = values.mask(values < 0)

    return values, negative_count


def sum_required(numeric_data, field_names, column_map, index):
    """
    Calculate a sum only when all required source columns exist.
    Missing values in a row are not silently treated as zero.
    """

    if not all(column_map.get(name) for name in field_names):
        return pd.Series(np.nan, index=index, dtype="float64")

    selected = [
        numeric_data[name]
        for name in field_names
    ]

    combined = pd.concat(selected, axis=1)

    return combined.sum(
        axis=1,
        min_count=len(field_names)
    )


def safe_percentage(numerator, denominator):
    valid = (
        numerator.notna()
        & denominator.notna()
        & (denominator > 0)
        & (numerator >= 0)
        & (numerator <= denominator)
    )

    result = (numerator / denominator) * 100

    return result.where(valid)


def parse_availability(series):
    values = series.astype("string").str.strip().str.lower()

    return values.isin([
        "1",
        "1.0",
        "true",
        "yes",
        "y",
    ])


# ------------------------------------------------------------
# 3. PROCESS EACH ACADEMIC YEAR
# ------------------------------------------------------------

all_year_outputs = []
summary_rows = []
manifest_rows = []

for year in YEARS:

    print("\n" + "=" * 65)
    print(f"FACILITY FEATURE ENGINEERING: {year}")
    print("=" * 65)

    input_file = (
        INPUT_DIR
        / f"maharashtra_school_year_integrated_{year}.csv"
    )

    if not input_file.exists():
        raise FileNotFoundError(
            f"Integrated input file not found: {input_file}"
        )

    df = pd.read_csv(
        input_file,
        dtype=str,
        low_memory=False,
        encoding="utf-8-sig",
    )

    print(f"Input rows: {len(df):,}")

    # --------------------------------------------------------
    # 3A. IDENTIFY SCHOOL ID AND DISTRICT
    # --------------------------------------------------------

    school_id_col = find_column(
        df.columns,
        [
            "school_id",
            "schoolid",
            "udise_code",
            "udisecode",
            "pseudocode",
            "psuedocode",
            "school_code",
            "schoolcode",
        ],
    )

    district_col = find_column(
        df.columns,
        [
            "district_std",
            "district_standardized",
            "district",
            "district_name",
            "districtname",
            "district_clean",
        ],
    )

    if school_id_col is None:
        raise ValueError(
            f"School ID column not found for {year}. "
            f"Available columns: {list(df.columns)}"
        )

    if district_col is None:
        raise ValueError(
            f"District column not found for {year}. "
            f"Available columns: {list(df.columns)}"
        )

    school_ids = (
        df[school_id_col]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

    districts = (
        df[district_col]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

    missing_ids = int(school_ids.isna().sum())
    duplicate_ids = int(school_ids.duplicated().sum())
    missing_districts = int(districts.isna().sum())
    unique_districts = int(districts.nunique())

    if missing_ids > 0:
        raise ValueError(
            f"{year}: {missing_ids} missing School IDs."
        )

    if duplicate_ids > 0:
        raise ValueError(
            f"{year}: {duplicate_ids} duplicate School IDs."
        )

    if missing_districts > 0:
        raise ValueError(
            f"{year}: {missing_districts} missing districts."
        )

    # --------------------------------------------------------
    # 3B. FIND FACILITY SOURCE COLUMNS
    # --------------------------------------------------------

    column_map = {}

    for feature_name, aliases in FIELD_ALIASES.items():
        column_map[feature_name] = find_facility_column(
            df.columns,
            aliases,
        )

    numeric_data = {}
    total_negative_values = 0

    for feature_name, source_col in column_map.items():

        if source_col is not None:
            values, negative_count = numeric_count(
                df[source_col]
            )

            numeric_data[feature_name] = values
            total_negative_values += negative_count

        else:
            numeric_data[feature_name] = pd.Series(
                np.nan,
                index=df.index,
                dtype="float64",
            )

    found_fields = [
        name
        for name, source_col in column_map.items()
        if source_col is not None
    ]

    missing_fields = [
        name
        for name, source_col in column_map.items()
        if source_col is None
    ]

    print(f"Numeric source fields found: {len(found_fields)}")
    print(f"Numeric source fields missing: {len(missing_fields)}")

    # --------------------------------------------------------
    # 3C. OUTPUT BASE INFORMATION
    # --------------------------------------------------------

    out = pd.DataFrame(index=df.index)

    out["school_id"] = school_ids
    out["district"] = districts
    out["academic_year"] = year

    availability_col = find_column(
        df.columns,
        [
            "facility_record_available",
            "facilityrecordavailable",
        ],
    )

    if availability_col is not None:
        out["facility_record_available"] = (
            parse_availability(df[availability_col])
        )
    else:
        # Every row is from the successfully integrated master.
        out["facility_record_available"] = True

    # Preserve selected numeric source values in this feature
    # output for traceability. Original integrated CSV is untouched.
    for name in FIELD_ALIASES:
        out[f"source_{name}"] = numeric_data[name]

    # --------------------------------------------------------
    # 4. TOILET FEATURES
    # --------------------------------------------------------

    total_toilets = sum_required(
        numeric_data,
        [
            "total_boys_toilet",
            "total_girls_toilet",
        ],
        column_map,
        df.index,
    )

    functional_toilets = sum_required(
        numeric_data,
        [
            "total_boys_func_toilet",
            "total_girls_func_toilet",
        ],
        column_map,
        df.index,
    )

    out["total_toilet_count"] = total_toilets
    out["functional_toilet_count"] = functional_toilets

    toilet_mismatch = (
        total_toilets.notna()
        & functional_toilets.notna()
        & (functional_toilets > total_toilets)
    )

    out["functional_toilet_pct"] = safe_percentage(
        functional_toilets,
        total_toilets,
    ).mask(toilet_mismatch)

    out["toilet_feature_status"] = "PASS"
    out.loc[
        toilet_mismatch,
        "toilet_feature_status"
    ] = "REVIEW_FUNCTIONAL_GREATER_THAN_TOTAL"

    # --------------------------------------------------------
    # 5. BUILDING BLOCK FEATURES
    # --------------------------------------------------------

    reported_blocks = numeric_data["no_building_blocks"]
    pucca_blocks = numeric_data["pucca_building_blocks"]

    usable_blocks = reported_blocks.copy()

    block_issue = (
        reported_blocks.notna()
        & pucca_blocks.notna()
        & (reported_blocks < pucca_blocks)
    )

    block_source_year_excluded = year == "2024-25"

    if block_source_year_excluded:
        # The source audit found 100% zero reported blocks
        # in this academic year. Do not use this denominator.
        usable_blocks[:] = np.nan

        block_status = pd.Series(
            "EXCLUDED_2024_25_SOURCE_ANOMALY",
            index=df.index,
        )

    else:
        usable_blocks = usable_blocks.mask(block_issue)

        if column_map["no_building_blocks"] is None or (
            column_map["pucca_building_blocks"] is None
        ):
            block_status = pd.Series(
                "NOT_AVAILABLE",
                index=df.index,
            )
        else:
            block_status = pd.Series(
                "PASS",
                index=df.index,
            )

            block_status.loc[
                reported_blocks.isna() | pucca_blocks.isna()
            ] = "MISSING_SOURCE_VALUE"

            block_status.loc[
                block_issue
            ] = "REVIEW_TOTAL_LT_PUCCA"

    out["usable_total_building_blocks"] = usable_blocks

    out["pucca_building_blocks_count"] = pucca_blocks

    out["pucca_building_block_pct"] = safe_percentage(
        pucca_blocks,
        usable_blocks,
    )

    out["building_block_feature_status"] = block_status

    # --------------------------------------------------------
    # 6. CLASSROOM FEATURES
    # --------------------------------------------------------

    reported_classrooms = numeric_data["total_class_rooms"]

    good_classrooms = numeric_data[
        "classrooms_in_good_condition"
    ]

    minor_repair = numeric_data[
        "classrooms_needs_minor_repair"
    ]

    major_repair = numeric_data[
        "classrooms_needs_major_repair"
    ]

    condition_sum = sum_required(
        numeric_data,
        [
            "classrooms_in_good_condition",
            "classrooms_needs_minor_repair",
            "classrooms_needs_major_repair",
        ],
        column_map,
        df.index,
    )

    usable_classrooms = reported_classrooms.copy()

    # Based on the source audit, 2021-22 has 452 records
    # with zero total classrooms but positive condition counts.
    classroom_issue = pd.Series(
        False,
        index=df.index,
    )

    if year == "2021-22":
        classroom_issue = (
            reported_classrooms.eq(0)
            & condition_sum.gt(0)
        )

        usable_classrooms = usable_classrooms.mask(
            classroom_issue
        )

    classroom_source_year_excluded = year == "2024-25"

    if classroom_source_year_excluded:
        # All 108,250 source records have zero total classrooms.
        usable_classrooms[:] = np.nan

        classroom_status = pd.Series(
            "EXCLUDED_2024_25_SOURCE_ANOMALY",
            index=df.index,
        )

    else:
        if column_map["total_class_rooms"] is None:
            classroom_status = pd.Series(
                "NOT_AVAILABLE",
                index=df.index,
            )
        else:
            classroom_status = pd.Series(
                "PASS",
                index=df.index,
            )

            classroom_status.loc[
                reported_classrooms.isna()
            ] = "MISSING_SOURCE_VALUE"

            classroom_status.loc[
                classroom_issue
            ] = "REVIEW_ZERO_TOTAL_WITH_POSITIVE_CONDITION"

    out["usable_total_classrooms"] = usable_classrooms

    out["classrooms_condition_reported_count"] = condition_sum

    out["classrooms_needing_repair_count"] = (
        minor_repair + major_repair
    ).where(
        minor_repair.notna() & major_repair.notna()
    )

    out["classrooms_good_condition_pct"] = safe_percentage(
        good_classrooms,
        condition_sum,
    )

    out["classrooms_minor_repair_pct"] = safe_percentage(
        minor_repair,
        condition_sum,
    )

    out["classrooms_major_repair_pct"] = safe_percentage(
        major_repair,
        condition_sum,
    )

    out["classrooms_needing_repair_pct"] = safe_percentage(
        minor_repair + major_repair,
        condition_sum,
    )

    out["classroom_feature_status"] = classroom_status

    # --------------------------------------------------------
    # 7. DIGITAL DEVICE FEATURES
    # --------------------------------------------------------

    digital_fields = [
        "desktop",
        "laptop",
        "tablet",
    ]

    digital_component_count = sum(
        numeric_data[name].notna().astype(int)
        for name in digital_fields
    )

    out["digital_device_components_available"] = (
        digital_component_count
    )

    out["digital_device_components_coverage_pct"] = (
        digital_component_count / len(digital_fields)
    ) * 100

    out["total_digital_devices"] = sum_required(
        numeric_data,
        digital_fields,
        column_map,
        df.index,
    )

    # Individual resources remain separately visible.
    out["desktop_count"] = numeric_data["desktop"]
    out["laptop_count"] = numeric_data["laptop"]
    out["tablet_count"] = numeric_data["tablet"]
    out["printer_count"] = numeric_data["printer"]
    out["projector_count"] = numeric_data["projector"]

    # --------------------------------------------------------
    # 8. DATA QUALITY STATUS
    # --------------------------------------------------------

    review_mask = (
        toilet_mismatch
        | block_issue
        | classroom_issue
        | block_source_year_excluded
        | classroom_source_year_excluded
    )

    out["facility_feature_quality_status"] = np.where(
        review_mask,
        "REVIEW",
        "PASS",
    )

    out["numeric_source_fields_found"] = len(found_fields)

    # --------------------------------------------------------
    # 9. SAVE YEAR OUTPUT
    # --------------------------------------------------------

    output_file = (
        OUTPUT_DIR
        / f"maharashtra_facility_features_{year}.csv"
    )

    out.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig",
    )

    all_year_outputs.append(out)

    # --------------------------------------------------------
    # 10. YEAR SUMMARY
    # --------------------------------------------------------

    summary_rows.append({
        "academic_year": year,
        "input_rows": len(df),
        "output_rows": len(out),
        "unique_school_ids": school_ids.nunique(),
        "unique_districts": unique_districts,
        "duplicate_school_ids": duplicate_ids,
        "missing_school_ids": missing_ids,
        "missing_districts": missing_districts,
        "facility_records_available": int(
            out["facility_record_available"].sum()
        ),
        "numeric_source_fields_found": len(found_fields),
        "numeric_source_fields_missing": len(missing_fields),
        "negative_source_values_cleaned": total_negative_values,
        "toilet_mismatch_rows": int(toilet_mismatch.sum()),
        "block_consistency_exception_rows": int(block_issue.sum()),
        "block_year_excluded_rows": (
            len(df) if block_source_year_excluded else 0
        ),
        "classroom_consistency_exception_rows": int(
            classroom_issue.sum()
        ),
        "classroom_year_excluded_rows": (
            len(df) if classroom_source_year_excluded else 0
        ),
        "usable_total_building_blocks_rows": int(
            out["usable_total_building_blocks"].notna().sum()
        ),
        "usable_total_classrooms_rows": int(
            out["usable_total_classrooms"].notna().sum()
        ),
        "output_file": str(output_file),
    })

    print(f"Output rows: {len(out):,}")
    print(f"Districts: {unique_districts}")
    print(f"Block exception rows: {int(block_issue.sum()):,}")
    print(f"Classroom exception rows: {int(classroom_issue.sum()):,}")
    print(f"Saved: {output_file}")


# ------------------------------------------------------------
# 11. BUILD ALL-YEAR MASTER
# ------------------------------------------------------------

print("\n" + "=" * 65)
print("BUILDING FACILITY FEATURES MASTER")
print("=" * 65)

facility_master = pd.concat(
    all_year_outputs,
    ignore_index=True,
)

facility_master_file = (
    OUTPUT_DIR
    / "maharashtra_facility_features_master.csv"
)

facility_master.to_csv(
    facility_master_file,
    index=False,
    encoding="utf-8-sig",
)

# ------------------------------------------------------------
# 12. SAVE AUDIT SUMMARY
# ------------------------------------------------------------

summary_df = pd.DataFrame(summary_rows)

summary_file = (
    REPORT_DIR
    / "facility_feature_engineering_summary.csv"
)

summary_df.to_csv(
    summary_file,
    index=False,
    encoding="utf-8-sig",
)

# ------------------------------------------------------------
# 13. SAVE FEATURE DICTIONARY
# ------------------------------------------------------------

manifest = [
    {
        "feature": "total_toilet_count",
        "source_fields": "total_boys_toilet + total_girls_toilet",
        "method": "Sum of boys and girls toilet counts",
        "note": "Numeric count feature",
    },
    {
        "feature": "functional_toilet_count",
        "source_fields": "total_boys_func_toilet + total_girls_func_toilet",
        "method": "Sum of functional toilet counts",
        "note": "Numeric count feature",
    },
    {
        "feature": "functional_toilet_pct",
        "source_fields": "functional_toilet_count / total_toilet_count",
        "method": "Percentage; invalid numerator greater than denominator excluded",
        "note": "Missing values are not converted to zero",
    },
    {
        "feature": "usable_total_building_blocks",
        "source_fields": "no_building_blocks",
        "method": "Source total after structural quality exclusions",
        "note": "Entire 2024-25 field excluded; inconsistent 2021-22 rows excluded",
    },
    {
        "feature": "pucca_building_block_pct",
        "source_fields": "pucca_building_blocks / usable_total_building_blocks",
        "method": "Percentage",
        "note": "Only calculated when numerator does not exceed denominator",
    },
    {
        "feature": "usable_total_classrooms",
        "source_fields": "total_class_rooms",
        "method": "Source total after structural quality exclusions",
        "note": "Entire 2024-25 field excluded; 2021-22 zero-total exceptions excluded",
    },
    {
        "feature": "classrooms_condition_reported_count",
        "source_fields": "classrooms_in_good_condition + classrooms_needs_minor_repair + classrooms_needs_major_repair",
        "method": "Sum of reported condition categories",
        "note": "Independent of the suspect total_class_rooms field",
    },
    {
        "feature": "classrooms_needing_repair_pct",
        "source_fields": "minor repair + major repair / condition reported count",
        "method": "Percentage among reported condition counts",
        "note": "Not a percentage of total classrooms",
    },
    {
        "feature": "total_digital_devices",
        "source_fields": "desktop + laptop + tablet",
        "method": "Sum when all three source components are available",
        "note": "Missing components are not treated as zero",
    },
    {
        "feature": "printer_count",
        "source_fields": "printer",
        "method": "Numeric count",
        "note": "Raw count retained separately",
    },
    {
        "feature": "projector_count",
        "source_fields": "projector",
        "method": "Numeric count",
        "note": "Raw count retained separately",
    },
]

manifest_df = pd.DataFrame(manifest)

manifest_file = (
    REPORT_DIR
    / "facility_feature_dictionary.csv"
)

manifest_df.to_csv(
    manifest_file,
    index=False,
    encoding="utf-8-sig",
)

# ------------------------------------------------------------
# 14. FINAL VALIDATION
# ------------------------------------------------------------

duplicate_master = facility_master.duplicated(
    subset=["academic_year", "school_id"]
).sum()

print("\n" + "=" * 65)
print("FACILITY FEATURE ENGINEERING - FINAL RESULT")
print("=" * 65)

print(f"Years processed: {len(all_year_outputs)}")
print(f"Total school-year records: {len(facility_master):,}")
print(f"Unique school-year keys: {facility_master[['academic_year', 'school_id']].drop_duplicates().shape[0]:,}")
print(f"Duplicate school-year records: {duplicate_master:,}")

print("\nYEAR-WISE SUMMARY:")
print(
    summary_df[
        [
            "academic_year",
            "output_rows",
            "unique_districts",
            "numeric_source_fields_found",
            "block_consistency_exception_rows",
            "block_year_excluded_rows",
            "classroom_consistency_exception_rows",
            "classroom_year_excluded_rows",
        ]
    ].to_string(index=False)
)

print("\nOUTPUT FILES:")
print(f"Feature folder: {OUTPUT_DIR}")
print(f"Master file: {facility_master_file}")
print(f"Summary report: {summary_file}")
print(f"Feature dictionary: {manifest_file}")

if duplicate_master == 0:
    print("\nFACILITY FEATURE ENGINEERING COMPLETED")
else:
    raise ValueError(
        f"Duplicate school-year records found: {duplicate_master}"
    )

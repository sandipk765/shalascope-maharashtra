
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT / "data" / "processed" / "school_year_features"
    / "facility" / "maharashtra_facility_features_master.csv"
)

OUTPUT_DIR = ROOT / "data" / "processed" / "district_year"
REPORT_DIR = ROOT / "reports" / "data_audit"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_YEARS = [
    "2018-19", "2019-20", "2020-21", "2021-22",
    "2022-23", "2023-24", "2024-25", "2025-26"
]

def numeric(df, col):
    return pd.to_numeric(df[col], errors="coerce")

def safe_pct(numerator, denominator):
    if pd.isna(denominator) or denominator <= 0:
        return np.nan
    return numerator / denominator * 100

def sum_valid(series):
    return series.sum(min_count=1)

print("=" * 65)
print("SHALASCOPE - DISTRICT YEAR FACILITY AGGREGATION")
print("=" * 65)

if not INPUT_FILE.exists():
    raise FileNotFoundError(INPUT_FILE)

df = pd.read_csv(INPUT_FILE, low_memory=False)

required_columns = [
    "school_id",
    "district",
    "academic_year",
    "facility_record_available",
    "total_toilet_count",
    "functional_toilet_count",
    "usable_total_building_blocks",
    "pucca_building_blocks_count",
    "usable_total_classrooms",
    "source_classrooms_in_good_condition",
    "source_classrooms_needs_minor_repair",
    "source_classrooms_needs_major_repair",
    "classrooms_condition_reported_count",
    "classrooms_needing_repair_count",
    "total_digital_devices",
    "desktop_count",
    "laptop_count",
    "tablet_count",
    "printer_count",
    "projector_count",
    "facility_feature_quality_status",
]

missing = [c for c in required_columns if c not in df.columns]

if missing:
    raise ValueError(f"Missing required columns: {missing}")

# ------------------------------------------------------------
# 1. SCHOOL-LEVEL VALIDATION
# ------------------------------------------------------------

df["school_id"] = df["school_id"].astype("string").str.strip()
df["district"] = df["district"].astype("string").str.strip()
df["academic_year"] = df["academic_year"].astype("string").str.strip()

if df[["school_id", "district", "academic_year"]].isna().any().any():
    raise ValueError("Missing school ID, district or academic year.")

if df["school_id"].eq("").any() or df["district"].eq("").any():
    raise ValueError("Blank school ID or district found.")

duplicate_keys = df.duplicated(
    subset=["academic_year", "school_id"]
).sum()

if duplicate_keys:
    raise ValueError(f"Duplicate school-year keys: {duplicate_keys}")

actual_years = sorted(df["academic_year"].unique().tolist())

if sorted(EXPECTED_YEARS) != actual_years:
    raise ValueError(f"Unexpected year coverage: {actual_years}")

for year in EXPECTED_YEARS:
    year_data = df[df["academic_year"] == year]
    district_count = year_data["district"].nunique()

    if district_count != 36:
        raise ValueError(
            f"{year}: Expected 36 districts, found {district_count}"
        )

print(f"School-year records: {len(df):,}")
print(f"Duplicate keys: {duplicate_keys}")
print("Year-wise district validation: PASS")

# ------------------------------------------------------------
# 2. NUMERIC CONVERSION
# ------------------------------------------------------------

numeric_columns = [
    "total_toilet_count",
    "functional_toilet_count",
    "usable_total_building_blocks",
    "pucca_building_blocks_count",
    "usable_total_classrooms",
    "source_classrooms_in_good_condition",
    "source_classrooms_needs_minor_repair",
    "source_classrooms_needs_major_repair",
    "classrooms_condition_reported_count",
    "classrooms_needing_repair_count",
    "total_digital_devices",
    "desktop_count",
    "laptop_count",
    "tablet_count",
    "printer_count",
    "projector_count",
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ------------------------------------------------------------
# 3. DISTRICT-YEAR AGGREGATION
# ------------------------------------------------------------

results = []
coverage_results = []

grouped = df.groupby(
    ["academic_year", "district"],
    sort=True,
    dropna=False
)

for (year, district), g in grouped:

    n = len(g)

    record = {
        "academic_year": year,
        "district": district,
        "total_schools": n,
        "facility_records_available": int(
            g["facility_record_available"].fillna(False).astype(bool).sum()
        ),
        "facility_review_schools": int(
            g["facility_feature_quality_status"].eq("REVIEW").sum()
        ),
    }

    # --------------------------------------------------------
    # A. TOILET METRICS
    # --------------------------------------------------------

    total = g["total_toilet_count"]
    functional = g["functional_toilet_count"]

    valid = (
        total.notna()
        & functional.notna()
        & total.ge(0)
        & functional.ge(0)
        & functional.le(total)
    )

    total_sum = sum_valid(total[valid])
    functional_sum = sum_valid(functional[valid])

    record["toilet_data_schools"] = int(valid.sum())
    record["toilet_data_coverage_pct"] = safe_pct(
        valid.sum(), n
    )

    record["total_toilets"] = total_sum
    record["functional_toilets"] = functional_sum

    record["functional_toilet_pct"] = safe_pct(
        functional_sum, total_sum
    )

    # --------------------------------------------------------
    # B. BUILDING BLOCK METRICS
    # --------------------------------------------------------

    blocks = g["usable_total_building_blocks"]
    pucca = g["pucca_building_blocks_count"]

    valid = (
        blocks.notna()
        & pucca.notna()
        & blocks.ge(0)
        & pucca.ge(0)
        & pucca.le(blocks)
    )

    blocks_sum = sum_valid(blocks[valid])
    pucca_sum = sum_valid(pucca[valid])

    record["building_block_data_schools"] = int(valid.sum())
    record["building_block_coverage_pct"] = safe_pct(
        valid.sum(), n
    )

    record["usable_total_building_blocks"] = blocks_sum
    record["pucca_building_blocks"] = pucca_sum

    record["pucca_building_block_pct"] = safe_pct(
        pucca_sum, blocks_sum
    )

    # --------------------------------------------------------
    # C. CLASSROOM CONDITION METRICS
    # --------------------------------------------------------

    good = g["source_classrooms_in_good_condition"]
    minor = g["source_classrooms_needs_minor_repair"]
    major = g["source_classrooms_needs_major_repair"]

    valid = (
        good.notna()
        & minor.notna()
        & major.notna()
        & good.ge(0)
        & minor.ge(0)
        & major.ge(0)
    )

    good_sum = sum_valid(good[valid])
    minor_sum = sum_valid(minor[valid])
    major_sum = sum_valid(major[valid])

    condition_total = (
        good_sum + minor_sum + major_sum
        if pd.notna(good_sum)
        and pd.notna(minor_sum)
        and pd.notna(major_sum)
        else np.nan
    )

    repair_total = (
        minor_sum + major_sum
        if pd.notna(minor_sum) and pd.notna(major_sum)
        else np.nan
    )

    record["classroom_condition_data_schools"] = int(valid.sum())
    record["classroom_condition_coverage_pct"] = safe_pct(
        valid.sum(), n
    )

    record["classrooms_good_condition_count"] = good_sum
    record["classrooms_minor_repair_count"] = minor_sum
    record["classrooms_major_repair_count"] = major_sum
    record["classrooms_condition_reported_count"] = condition_total

    record["classrooms_good_condition_pct"] = safe_pct(
        good_sum, condition_total
    )

    record["classrooms_minor_repair_pct"] = safe_pct(
        minor_sum, condition_total
    )

    record["classrooms_major_repair_pct"] = safe_pct(
        major_sum, condition_total
    )

    record["classrooms_needing_repair_count"] = repair_total

    record["classrooms_needing_repair_pct"] = safe_pct(
        repair_total, condition_total
    )

    # Reported total classrooms are separate from condition counts.
    usable_classrooms = g["usable_total_classrooms"].dropna()

    record["usable_total_classrooms"] = sum_valid(
        usable_classrooms
    )

    record["classroom_total_data_schools"] = int(
        g["usable_total_classrooms"].notna().sum()
    )

    record["classroom_total_coverage_pct"] = safe_pct(
        record["classroom_total_data_schools"], n
    )

    # --------------------------------------------------------
    # D. DIGITAL DEVICE METRICS
    # --------------------------------------------------------

    device_fields = [
        "desktop_count",
        "laptop_count",
        "tablet_count",
    ]

    devices = g["total_digital_devices"]
    valid_devices = devices.notna() & devices.ge(0)

    record["digital_device_data_schools"] = int(
        valid_devices.sum()
    )

    record["digital_device_coverage_pct"] = safe_pct(
        valid_devices.sum(), n
    )

    record["total_digital_devices"] = sum_valid(
        devices[valid_devices]
    )

    record["avg_digital_devices_per_reporting_school"] = (
        record["total_digital_devices"]
        / valid_devices.sum()
        if valid_devices.sum() > 0
        else np.nan
    )

    for field in device_fields:
        values = g[field]
        valid_values = values.notna() & values.ge(0)

        record[f"total_{field}"] = sum_valid(
            values[valid_values]
        )

        record[f"{field}_data_schools"] = int(
            valid_values.sum()
        )

        record[f"{field}_coverage_pct"] = safe_pct(
            valid_values.sum(), n
        )

    # --------------------------------------------------------
    # E. OTHER EQUIPMENT
    # --------------------------------------------------------

    for field in ["printer_count", "projector_count"]:

        values = g[field]
        valid_values = values.notna() & values.ge(0)

        record[f"total_{field}"] = sum_valid(
            values[valid_values]
        )

        record[f"{field}_data_schools"] = int(
            valid_values.sum()
        )

        record[f"{field}_coverage_pct"] = safe_pct(
            valid_values.sum(), n
        )

    results.append(record)

    coverage_results.append({
        "academic_year": year,
        "district": district,
        "total_schools": n,
        "toilet_coverage_pct": record["toilet_data_coverage_pct"],
        "building_block_coverage_pct": record["building_block_coverage_pct"],
        "classroom_condition_coverage_pct": record[
            "classroom_condition_coverage_pct"
        ],
        "classroom_total_coverage_pct": record[
            "classroom_total_coverage_pct"
        ],
        "digital_device_coverage_pct": record[
            "digital_device_coverage_pct"
        ],
        "facility_review_schools": record["facility_review_schools"],
    })

# ------------------------------------------------------------
# 4. SAVE DISTRICT-YEAR DATASETS
# ------------------------------------------------------------

district_df = pd.DataFrame(results).sort_values(
    ["academic_year", "district"]
).reset_index(drop=True)

coverage_df = pd.DataFrame(coverage_results).sort_values(
    ["academic_year", "district"]
).reset_index(drop=True)

expected_rows = len(EXPECTED_YEARS) * 36

if len(district_df) != expected_rows:
    raise ValueError(
        f"Expected {expected_rows} district-year records, "
        f"found {len(district_df)}"
    )

if district_df.duplicated(
    ["academic_year", "district"]
).any():
    raise ValueError("Duplicate district-year records found.")

master_file = (
    OUTPUT_DIR / "maharashtra_district_year_facility_features.csv"
)

coverage_file = (
    REPORT_DIR / "district_year_facility_feature_coverage.csv"
)

summary_file = (
    REPORT_DIR / "district_year_facility_aggregation_summary.csv"
)

district_df.to_csv(
    master_file, index=False, encoding="utf-8-sig"
)

coverage_df.to_csv(
    coverage_file, index=False, encoding="utf-8-sig"
)

# Also save individual year datasets.
for year in EXPECTED_YEARS:

    year_df = district_df[
        district_df["academic_year"] == year
    ]

    year_file = (
        OUTPUT_DIR
        / f"maharashtra_district_year_facility_{year}.csv"
    )

    year_df.to_csv(
        year_file,
        index=False,
        encoding="utf-8-sig"
    )

# ------------------------------------------------------------
# 5. YEAR-WISE SUMMARY
# ------------------------------------------------------------

summary = (
    district_df.groupby("academic_year")
    .agg(
        districts=("district", "nunique"),
        total_schools=("total_schools", "sum"),
        toilet_reporting_schools=("toilet_data_schools", "sum"),
        building_reporting_schools=("building_block_data_schools", "sum"),
        classroom_condition_reporting_schools=(
            "classroom_condition_data_schools", "sum"
        ),
        digital_reporting_schools=("digital_device_data_schools", "sum"),
        facility_review_schools=("facility_review_schools", "sum"),
    )
    .reset_index()
)

summary.to_csv(
    summary_file,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 6. FINAL VALIDATION
# ------------------------------------------------------------

print("\n" + "=" * 65)
print("DISTRICT-YEAR FACILITY AGGREGATION RESULT")
print("=" * 65)

print(f"District-year records: {len(district_df)}")
print(f"Expected records: {expected_rows}")
print(f"Unique districts: {district_df['district'].nunique()}")
print(f"Academic years: {district_df['academic_year'].nunique()}")
print(
    "Duplicate district-year records:",
    district_df.duplicated(
        ["academic_year", "district"]
    ).sum()
)

print("\nYEAR-WISE SUMMARY:")
print(summary.to_string(index=False))

print("\nOUTPUT FILES:")
print(master_file)
print(coverage_file)
print(summary_file)

print("\nDISTRICT-YEAR FACILITY AGGREGATION COMPLETED")

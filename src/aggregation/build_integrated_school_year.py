
from pathlib import Path
import re
import pandas as pd

# ============================================================
# SHALASCOPE MAHARASHTRA
# SCHOOL + FACILITY + ENROLLMENT INTEGRATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

EXTRACTED = ROOT / "data" / "extracted"
MASTER_DIR = ROOT / "data" / "processed" / "school_year"

INTEGRATED_DIR = (
    ROOT / "data" / "processed" / "school_year_integrated"
)

ENROLLMENT_DIR = (
    ROOT / "data" / "processed" / "enrollment_long"
)

ENROLLMENT_DISTRICT_DIR = (
    ROOT / "data" / "processed" / "enrollment_district"
)

REPORT_DIR = ROOT / "reports" / "data_audit"

for directory in [
    INTEGRATED_DIR,
    ENROLLMENT_DIR,
    ENROLLMENT_DISTRICT_DIR,
    REPORT_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

YEARS = [
    "2018-19", "2019-20", "2020-21", "2021-22",
    "2022-23", "2023-24", "2024-25", "2025-26"
]

EXPECTED_ENROLLMENT_GAPS = {
    "2018-19": 0,
    "2019-20": 0,
    "2020-21": 0,
    "2021-22": 0,
    "2022-23": 129,
    "2023-24": 18,
    "2024-25": 0,
    "2025-26": 0,
}

SUMMARY = []
ENROLLMENT_SUMMARIES = []
ENROLLMENT_FIELD_AUDITS = []


# ============================================================
# 1. FIND SOURCE FILE
# ============================================================

def find_one(year, suffix):

    folder = EXTRACTED / year

    matches = [
        p for p in folder.rglob("*.csv")
        if p.name.lower().endswith(suffix.lower())
    ]

    if len(matches) != 1:
        raise FileNotFoundError(
            f"{year}: Expected one {suffix}, found {len(matches)}"
        )

    return matches[0]


def detect_id_column(path):

    headers = pd.read_csv(
        path,
        nrows=0,
        encoding="utf-8-sig"
    ).columns.tolist()

    for name in [
        "psuedocode",
        "pseudocode",
        "school_id",
    ]:
        if name in headers:
            return name

    raise ValueError(
        f"School ID column not found: {path.name}"
    )


# ============================================================
# 2. NORMALIZE SOURCE IDS
# ============================================================

def normalize_ids(series):
    return series.astype("string").str.strip()


# ============================================================
# 3. FACILITY ONE-TO-ONE JOIN
# ============================================================

def load_and_join_facility(
    master,
    facility_path,
    year,
):

    id_col = detect_id_column(facility_path)

    facility = pd.read_csv(
        facility_path,
        dtype={id_col: "string"},
        low_memory=False,
        encoding="utf-8-sig",
    )

    facility["school_id"] = normalize_ids(
        facility[id_col]
    )

    missing_ids = int(
        facility["school_id"].isna().sum()
        + facility["school_id"].eq("").fillna(False).sum()
    )

    duplicate_ids = int(
        facility["school_id"].duplicated().sum()
    )

    if missing_ids or duplicate_ids:
        raise ValueError(
            f"{year}: Facility ID integrity failed."
        )

    master_ids = set(master["school_id"].tolist())
    facility_ids = set(facility["school_id"].tolist())

    unmatched = facility_ids - master_ids
    missing_facility = master_ids - facility_ids

    if unmatched:
        raise ValueError(
            f"{year}: {len(unmatched)} Facility IDs not in Master."
        )

    # Preserve source ID separately.
    if id_col != "school_id":
        facility["facility_source_school_id"] = (
            facility[id_col]
        )

    facility = facility.drop(
        columns=[id_col],
        errors="ignore",
    )

    # Prefix raw facility fields to avoid column collisions.
    rename_map = {
        col: f"facility__{col}"
        for col in facility.columns
        if col != "school_id"
    }

    facility = facility.rename(columns=rename_map)

    facility["facility_record_available"] = True

    merged = master.merge(
        facility,
        on="school_id",
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    merged["facility_record_available"] = (
        merged["_merge"].eq("both")
    )

    merged = merged.drop(columns=["_merge"])

    if len(merged) != len(master):
        raise ValueError(
            f"{year}: Facility join changed Master row count."
        )

    return merged, {
        "facility_source_rows": len(facility),
        "facility_matched_schools": len(facility_ids & master_ids),
        "facility_missing_schools": len(missing_facility),
        "facility_unmatched_source_ids": len(unmatched),
        "facility_duplicate_ids": duplicate_ids,
    }


# ============================================================
# 4. PROCESS ENROLLMENT FILE
# ============================================================

def process_enrollment_file(
    path,
    year,
    source_type,
    master,
):

    id_col = detect_id_column(path)

    df = pd.read_csv(
        path,
        dtype={id_col: "string"},
        low_memory=False,
        encoding="utf-8-sig",
    )

    df["school_id"] = normalize_ids(df[id_col])

    missing_ids = int(
        df["school_id"].isna().sum()
        + df["school_id"].eq("").fillna(False).sum()
    )

    if missing_ids:
        raise ValueError(
            f"{year} {source_type}: Missing School IDs."
        )

    district_map = dict(
        zip(master["school_id"], master["district"])
    )

    df["district"] = df["school_id"].map(district_map)

    unmatched_ids = int(df["district"].isna().sum())

    if unmatched_ids:
        raise ValueError(
            f"{year} {source_type}: "
            f"{unmatched_ids} records have unmatched IDs."
        )

    # --------------------------------------------------------
    # DUPLICATE ITEM-KEY VALIDATION
    # --------------------------------------------------------

    if "item_desc" in df.columns:
        item_key_cols = ["item_desc"]

    elif {"item_group", "item_id"}.issubset(df.columns):
        item_key_cols = ["item_group", "item_id"]

    else:
        raise ValueError(
            f"{year} {source_type}: Item key missing."
        )

    duplicate_key_rows = int(
        df.duplicated(
            subset=["school_id"] + item_key_cols
        ).sum()
    )

    if duplicate_key_rows:
        raise ValueError(
            f"{year} {source_type}: "
            f"{duplicate_key_rows} duplicate item keys."
        )

    # --------------------------------------------------------
    # PRESERVE ORIGINAL ITEM DATA
    # --------------------------------------------------------

    raw_output = df.copy()

    raw_output["academic_year"] = year
    raw_output["source_type"] = source_type

    year_output_dir = ENROLLMENT_DIR / year
    year_output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = (
        year_output_dir
        / f"maharashtra_{source_type.lower()}_items_{year}.csv.gz"
    )

    raw_output.to_csv(
        raw_path,
        index=False,
        encoding="utf-8",
        compression="gzip",
    )

    # Each school has multiple item records.
    # This is a record count, NOT a student count.
    per_school_records = (
        df.groupby("school_id")
        .size()
        .rename(f"{source_type.lower()}_item_rows")
    )

    # --------------------------------------------------------
    # SAFE DISTRICT ITEM AGGREGATION
    # --------------------------------------------------------

    work = df.copy()

    for col in ["item_desc", "item_group", "item_id"]:

        if col not in work.columns:
            work[col] = ""

        work[col] = (
            work[col]
            .fillna("[BLANK]")
            .astype("string")
            .str.strip()
        )

    grade_cols = [
        col for col in work.columns
        if re.fullmatch(r"(?:cpp|c\d+)_(?:b|g|t)", col)
    ]

    # Convert grade-wise values for arithmetic only.
    # Raw original values are already saved above.
    for col in grade_cols:

        raw = work[col].astype("string").str.strip()

        blank = (
            raw.isna()
            | raw.eq("").fillna(False)
        )

        numeric = pd.to_numeric(
            raw.str.replace(",", "", regex=False),
            errors="coerce",
        )

        invalid = int(
            ((~blank) & numeric.isna()).sum()
        )

        negative = int(
            numeric.lt(0).sum()
        )

        ENROLLMENT_FIELD_AUDITS.append({
            "academic_year": year,
            "source_type": source_type,
            "source_file": path.name,
            "field": col,
            "records": len(work),
            "missing_values": int(blank.sum()),
            "invalid_numeric_values": invalid,
            "negative_values": negative,
            "status": (
                "PASS"
                if invalid == 0 and negative == 0
                else "PASS_WITH_VALUE_REVIEW"
            ),
        })

        work[col] = numeric

    group_keys = [
        "district",
        "item_desc",
        "item_group",
        "item_id",
    ]

    grouped = work.groupby(
        group_keys,
        dropna=False,
        sort=False,
    )

    district_summary = (
        grouped.size()
        .rename("item_record_rows")
        .reset_index()
    )

    district_summary["schools_reporting"] = (
        grouped["school_id"].nunique().values
    )

    if grade_cols:

        sums = (
            grouped[grade_cols]
            .sum(min_count=1)
            .reset_index()
        )

        sums = sums.rename(columns={
            col: f"{col}_sum"
            for col in grade_cols
        })

        counts = (
            grouped[grade_cols]
            .count()
            .reset_index()
        )

        counts = counts.rename(columns={
            col: f"{col}_reporting_rows"
            for col in grade_cols
        })

        district_summary = (
            district_summary
            .merge(sums, on=group_keys, validate="one_to_one")
            .merge(counts, on=group_keys, validate="one_to_one")
        )

    district_summary["academic_year"] = year
    district_summary["source_type"] = source_type
    district_summary["source_file"] = path.name

    ENROLLMENT_SUMMARIES.append(district_summary)

    return {
        "school_record_counts": per_school_records,
        "source_rows": len(df),
        "unique_school_ids": int(df["school_id"].nunique()),
        "unmatched_school_ids": unmatched_ids,
        "missing_school_id_rows": missing_ids,
        "duplicate_item_keys": duplicate_key_rows,
        "grade_columns": len(grade_cols),
        "compressed_output": str(raw_path),
    }


# ============================================================
# 5. PROCESS ONE ACADEMIC YEAR
# ============================================================

def process_year(year):

    print("\n" + "=" * 70)
    print(f"INTEGRATING ACADEMIC YEAR: {year}")
    print("=" * 70)

    master_path = (
        MASTER_DIR
        / f"maharashtra_school_year_master_{year}.csv"
    )

    if not master_path.exists():
        raise FileNotFoundError(master_path)

    master = pd.read_csv(
        master_path,
        dtype={"school_id": "string"},
        low_memory=False,
        encoding="utf-8-sig",
    )

    master["school_id"] = normalize_ids(
        master["school_id"]
    )

    master["district"] = (
        master["district"]
        .astype("string")
        .str.strip()
    )

    master_rows = len(master)

    if master["school_id"].isna().any():
        raise ValueError(f"{year}: Missing Master School IDs.")

    if master["school_id"].duplicated().any():
        raise ValueError(f"{year}: Duplicate Master School IDs.")

    # --------------------------------------------------------
    # FACILITY
    # --------------------------------------------------------

    facility_path = find_one(year, "_fac.csv")

    merged, facility_audit = load_and_join_facility(
        master,
        facility_path,
        year,
    )

    # --------------------------------------------------------
    # ENROLLMENT FILES
    # --------------------------------------------------------

    enrollment_audits = {}

    for source_type, suffix in [
        ("ENR1", "_enr1.csv"),
        ("ENR2", "_enr2.csv"),
    ]:

        source_path = find_one(year, suffix)

        enrollment_audits[source_type] = process_enrollment_file(
            source_path,
            year,
            source_type,
            master,
        )

    # --------------------------------------------------------
    # ADD ITEM-ROW COUNTS TO SCHOOL MASTER
    # --------------------------------------------------------

    for source_type in ["ENR1", "ENR2"]:

        count_series = enrollment_audits[source_type][
            "school_record_counts"
        ]

        count_column = f"{source_type.lower()}_item_rows"

        merged[count_column] = (
            merged["school_id"]
            .map(count_series)
            .fillna(0)
            .astype("int32")
        )

        merged[f"{source_type.lower()}_data_available"] = (
            merged[count_column] > 0
        )

    merged["enrollment_sources_present"] = (
        merged["enr1_data_available"]
        & merged["enr2_data_available"]
    )

    merged["enrollment_source_status"] = "PRESENT_IN_BOTH_FILES"

    merged.loc[
        ~merged["enr1_data_available"]
        & ~merged["enr2_data_available"],
        "enrollment_source_status"
    ] = "MISSING_FROM_BOTH_FILES"

    merged.loc[
        ~merged["enr1_data_available"]
        & merged["enr2_data_available"],
        "enrollment_source_status"
    ] = "MISSING_FROM_ENR1_ONLY"

    merged.loc[
        merged["enr1_data_available"]
        & ~merged["enr2_data_available"],
        "enrollment_source_status"
    ] = "MISSING_FROM_ENR2_ONLY"

    # --------------------------------------------------------
    # FINAL SCHOOL-YEAR VALIDATION
    # --------------------------------------------------------

    facility_missing = int(
        (~merged["facility_record_available"]).sum()
    )

    enrollment_missing_both = int(
        (
            ~merged["enr1_data_available"]
            & ~merged["enr2_data_available"]
        ).sum()
    )

    enrollment_missing_any = int(
        (~merged["enrollment_sources_present"]).sum()
    )

    expected_gap = EXPECTED_ENROLLMENT_GAPS[year]

    if enrollment_missing_both != expected_gap:
        raise ValueError(
            f"{year}: Expected {expected_gap} known enrollment gaps, "
            f"found {enrollment_missing_both}."
        )

    if (
        facility_missing != 0
        or len(merged) != master_rows
        or merged["school_id"].duplicated().any()
    ):
        raise ValueError(
            f"{year}: Integrated dataset validation failed."
        )

    output_path = (
        INTEGRATED_DIR
        / f"maharashtra_school_year_integrated_{year}.csv"
    )

    merged.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    status = (
        "PASS_WITH_DOCUMENTED_ENROLLMENT_GAPS"
        if enrollment_missing_any > 0
        else "PASS"
    )

    record = {
        "academic_year": year,
        "master_schools": master_rows,
        "integrated_schools": len(merged),
        "facility_source_rows": facility_audit["facility_source_rows"],
        "facility_missing_schools": facility_missing,
        "enr1_unique_ids": enrollment_audits["ENR1"]["unique_school_ids"],
        "enr2_unique_ids": enrollment_audits["ENR2"]["unique_school_ids"],
        "enrollment_missing_from_both": enrollment_missing_both,
        "enrollment_missing_from_any": enrollment_missing_any,
        "enr1_item_rows": enrollment_audits["ENR1"]["source_rows"],
        "enr2_item_rows": enrollment_audits["ENR2"]["source_rows"],
        "integrated_columns": len(merged.columns),
        "status": status,
        "output_file": output_path.name,
    }

    SUMMARY.append(record)

    print(f"Master Schools          : {master_rows:,}")
    print(f"Facility Missing        : {facility_missing}")
    print(f"ENR1 Unique IDs         : {record['enr1_unique_ids']:,}")
    print(f"ENR2 Unique IDs         : {record['enr2_unique_ids']:,}")
    print(f"Enrollment Gaps         : {enrollment_missing_any}")
    print(f"Integrated Columns      : {len(merged.columns)}")
    print(f"STATUS                  : {status}")
    print(f"OUTPUT                  : {output_path}")


# ============================================================
# 6. MAIN
# ============================================================

def main():

    print("\n" + "=" * 75)
    print("SHALASCOPE MAHARASHTRA")
    print("INTEGRATED SCHOOL-YEAR DATA PIPELINE")
    print("=" * 75)

    failures = []

    for year in YEARS:

        try:
            process_year(year)

        except Exception as exc:

            failures.append({
                "academic_year": year,
                "error": str(exc),
            })

            print(
                f"\nFAILED: {year} | {exc}"
            )

    # --------------------------------------------------------
    # SAVE ENROLLMENT ITEM SUMMARIES
    # --------------------------------------------------------

    if ENROLLMENT_SUMMARIES:

        combined_enrollment = pd.concat(
            ENROLLMENT_SUMMARIES,
            ignore_index=True,
            sort=False,
        )

        enrollment_summary_path = (
            ENROLLMENT_DISTRICT_DIR
            / "maharashtra_enrollment_district_item_summary.csv"
        )

        combined_enrollment.to_csv(
            enrollment_summary_path,
            index=False,
            encoding="utf-8-sig",
        )

        print("\nEnrollment District Item Summary:")
        print(enrollment_summary_path)

    # --------------------------------------------------------
    # SAVE AUDIT REPORTS
    # --------------------------------------------------------

    summary_path = (
        REPORT_DIR / "integrated_school_year_summary.csv"
    )

    pd.DataFrame(SUMMARY).to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    field_audit_path = (
        REPORT_DIR / "enrollment_numeric_value_audit.csv"
    )

    pd.DataFrame(ENROLLMENT_FIELD_AUDITS).to_csv(
        field_audit_path,
        index=False,
        encoding="utf-8-sig",
    )

    if failures:

        failure_path = (
            REPORT_DIR / "integrated_school_year_failures.csv"
        )

        pd.DataFrame(failures).to_csv(
            failure_path,
            index=False,
            encoding="utf-8-sig",
        )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    print("\n" + "=" * 75)
    print("INTEGRATION SUMMARY")
    print("=" * 75)

    if SUMMARY:
        summary_df = pd.DataFrame(SUMMARY)
        print(summary_df.to_string(index=False))

    print(f"\nYears Processed: {len(SUMMARY)}")
    print(f"Years Failed   : {len(failures)}")

    print("\nReports:")
    print(summary_path)
    print(field_audit_path)

    if ENROLLMENT_SUMMARIES:
        print(enrollment_summary_path)

    if failures:
        print("\nFINAL STATUS: REVIEW REQUIRED")
    elif len(SUMMARY) == len(YEARS):
        print("\nFINAL STATUS: INTEGRATION PASS")
    else:
        print("\nFINAL STATUS: INCOMPLETE")

    print("\nINTEGRATION COMPLETED")


if __name__ == "__main__":
    main()

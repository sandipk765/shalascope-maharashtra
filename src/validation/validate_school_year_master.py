
"""
ShalaScope Maharashtra
School-Year Master Dataset Integrity Audit

Validates:
1. All 8 master CSV files.
2. Record count against Profile 1 reference.
3. Unique and non-missing School IDs.
4. 36 standardized districts.
5. District and district_raw mapping.
6. Academic year consistency.
7. CSV row width and column uniqueness.

Original files are never modified.
Python standard library only.
"""

from pathlib import Path
import csv
import re


# ==================================================
# 1. PATHS
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

MASTER_DIR = ROOT / "data" / "processed" / "school_year"

PROFILE1_DIR = (
    ROOT / "data" / "interim" / "standardized" / "profile1"
)

REPORT_DIR = ROOT / "reports" / "data_audit"

SUMMARY_REPORT = (
    REPORT_DIR / "master_dataset_integrity_audit.csv"
)

ISSUES_REPORT = (
    REPORT_DIR / "master_dataset_integrity_issues.csv"
)

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

ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "latin-1",
)

MISSING_VALUES = {
    "",
    "na",
    "n/a",
    "null",
    "none",
    "nan",
}

ID_ALIASES = {
    "pseudocode",
    "psuedocode",
    "schoolid",
    "udiseid",
}

MAX_ISSUES = 500


# ==================================================
# 2. HELPERS
# ==================================================

def norm(value):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


def clean(value):

    return str(value or "").strip()


def is_missing(value):

    return clean(value).lower() in MISSING_VALUES


def normalized_value(value):

    return clean(value).upper()


def open_csv(path):

    last_error = None

    for encoding in ENCODINGS:

        handle = None

        try:

            handle = path.open(
                "r",
                encoding=encoding,
                newline=""
            )

            sample = handle.read(65536)
            handle.seek(0)

            try:

                dialect = csv.Sniffer().sniff(
                    sample,
                    delimiters=",;\t|"
                )

            except csv.Error:

                dialect = csv.excel

            return handle, dialect

        except UnicodeDecodeError as error:

            last_error = error

            if handle is not None:
                handle.close()

    raise UnicodeError(
        f"Cannot decode {path}: {last_error}"
    )


def add_issue(
    issues,
    year,
    issue,
    school_id="",
    record_number="",
    expected="",
    actual=""
):

    if len(issues) >= MAX_ISSUES:
        return

    issues.append({

        "academic_year": year,
        "issue": issue,
        "school_id": school_id,
        "record_number": record_number,
        "expected_value": expected,
        "actual_value": actual,

    })


# ==================================================
# 3. LOAD PROFILE 1 REFERENCE
# ==================================================

def load_profile1_reference(year, issues):

    path = (
        PROFILE1_DIR
        / f"maharashtra_profile1_{year}_standardized.csv"
    )

    if not path.exists():
        raise FileNotFoundError(path)

    handle, dialect = open_csv(path)

    reference = {}

    malformed = 0
    missing_ids = 0
    duplicate_ids = 0

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        normalized_headers = {
            norm(name): index
            for index, name in enumerate(headers)
        }

        id_index = next(
            (
                normalized_headers[a]
                for a in ID_ALIASES
                if a in normalized_headers
            ),
            None
        )

        district_index = normalized_headers.get("district")
        raw_index = normalized_headers.get("districtraw")

        if (
            id_index is None
            or district_index is None
            or raw_index is None
        ):
            raise ValueError(
                f"Required reference columns missing in {path.name}"
            )

        for record_number, row in enumerate(reader, start=2):

            if not row or all(not clean(v) for v in row):
                continue

            if len(row) != len(headers):

                malformed += 1

                add_issue(
                    issues,
                    year,
                    "REFERENCE_MALFORMED_ROW",
                    record_number=record_number
                )

                continue

            school_id = clean(row[id_index])

            district = normalized_value(
                row[district_index]
            )

            raw_district = normalized_value(
                row[raw_index]
            )

            if is_missing(school_id):

                missing_ids += 1
                continue

            if school_id in reference:

                duplicate_ids += 1
                continue

            reference[school_id] = (
                district,
                raw_district
            )

    finally:
        handle.close()

    return {
        "reference": reference,
        "malformed": malformed,
        "missing_ids": missing_ids,
        "duplicate_ids": duplicate_ids,
    }


# ==================================================
# 4. VALIDATE MASTER FILE
# ==================================================

def validate_master(year, reference_info):

    path = (
        MASTER_DIR
        / f"maharashtra_school_year_master_{year}.csv"
    )

    if not path.exists():
        raise FileNotFoundError(path)

    issues = []

    reference = reference_info["reference"]

    expected_ids = set(reference)

    handle, dialect = open_csv(path)

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        if not headers:
            raise ValueError("Master CSV header is empty.")

        normalized_headers = [
            norm(name)
            for name in headers
        ]

        duplicate_columns = (
            len(normalized_headers)
            - len(set(normalized_headers))
        )

        field_positions = {
            name: index
            for index, name in enumerate(normalized_headers)
        }

        required = [
            "academicyear",
            "schoolid",
            "district",
            "districtraw",
        ]

        missing_columns = [
            field
            for field in required
            if field not in field_positions
        ]

        if missing_columns:

            raise ValueError(
                f"Required master columns missing: {missing_columns}"
            )

        year_index = field_positions["academicyear"]
        id_index = field_positions["schoolid"]
        district_index = field_positions["district"]
        raw_index = field_positions["districtraw"]

        records = 0
        malformed = 0
        missing_ids = 0
        duplicate_ids = 0
        missing_districts = 0
        missing_raw = 0
        mapping_mismatches = 0
        wrong_year = 0
        extra_ids = 0

        seen_ids = set()
        districts = set()

        for record_number, row in enumerate(reader, start=2):

            if not row or all(not clean(v) for v in row):
                continue

            records += 1

            if len(row) != len(headers):

                malformed += 1

                add_issue(
                    issues,
                    year,
                    "MASTER_MALFORMED_ROW",
                    record_number=record_number
                )

                continue

            actual_year = clean(row[year_index])

            school_id = clean(row[id_index])

            district = normalized_value(
                row[district_index]
            )

            raw_district = normalized_value(
                row[raw_index]
            )

            if actual_year != year:

                wrong_year += 1

                add_issue(
                    issues,
                    year,
                    "WRONG_ACADEMIC_YEAR",
                    school_id,
                    record_number,
                    year,
                    actual_year
                )

            if is_missing(school_id):

                missing_ids += 1

                add_issue(
                    issues,
                    year,
                    "MISSING_SCHOOL_ID",
                    record_number=record_number
                )

                continue

            if school_id in seen_ids:

                duplicate_ids += 1

                add_issue(
                    issues,
                    year,
                    "DUPLICATE_SCHOOL_ID",
                    school_id,
                    record_number
                )

            seen_ids.add(school_id)

            if is_missing(district):

                missing_districts += 1

                add_issue(
                    issues,
                    year,
                    "MISSING_DISTRICT",
                    school_id,
                    record_number
                )

            else:

                districts.add(district)

            if is_missing(raw_district):

                missing_raw += 1

                add_issue(
                    issues,
                    year,
                    "MISSING_DISTRICT_RAW",
                    school_id,
                    record_number
                )

            if school_id not in reference:

                extra_ids += 1

                add_issue(
                    issues,
                    year,
                    "SCHOOL_ID_NOT_IN_PROFILE1",
                    school_id,
                    record_number
                )

                continue

            expected_district, expected_raw = (
                reference[school_id]
            )

            if district != expected_district:

                mapping_mismatches += 1

                add_issue(
                    issues,
                    year,
                    "DISTRICT_MISMATCH",
                    school_id,
                    record_number,
                    expected_district,
                    district
                )

            if raw_district != expected_raw:

                mapping_mismatches += 1

                add_issue(
                    issues,
                    year,
                    "DISTRICT_RAW_MISMATCH",
                    school_id,
                    record_number,
                    expected_raw,
                    raw_district
                )

    finally:
        handle.close()

    missing_from_master = len(
        expected_ids - seen_ids
    )

    if missing_from_master > 0:

        add_issue(
            issues,
            year,
            "PROFILE1_IDS_MISSING_FROM_MASTER",
            expected=str(missing_from_master)
        )

    # ------------------------------------------
    # DETERMINE STATUS
    # ------------------------------------------

    status = "PASS"

    checks = [

        records == len(expected_ids),

        len(seen_ids) == len(expected_ids),

        missing_from_master == 0,
        missing_ids == 0,
        duplicate_ids == 0,
        malformed == 0,
        missing_districts == 0,
        missing_raw == 0,
        extra_ids == 0,
        mapping_mismatches == 0,
        wrong_year == 0,
        duplicate_columns == 0,
        len(districts) == 36,

    ]

    if not all(checks):
        status = "REVIEW_REQUIRED"

    result = {

        "academic_year": year,
        "master_records": records,
        "master_columns": len(headers),
        "expected_profile1_records": len(expected_ids),
        "unique_school_ids": len(seen_ids),
        "unique_districts": len(districts),

        "missing_ids": missing_ids,
        "duplicate_ids": duplicate_ids,
        "missing_from_master": missing_from_master,
        "extra_ids": extra_ids,

        "missing_districts": missing_districts,
        "missing_district_raw": missing_raw,
        "mapping_mismatches": mapping_mismatches,

        "wrong_academic_year": wrong_year,
        "malformed_rows": malformed,
        "duplicate_columns": duplicate_columns,

        "status": status,

    }

    return result, issues


# ==================================================
# 5. SAVE REPORTS
# ==================================================

def save_report(path, rows, fields):

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(rows)


# ==================================================
# 6. MAIN
# ==================================================

def main():

    print("\nSHALASCOPE - MASTER DATASET INTEGRITY AUDIT")
    print("=" * 75)

    if not MASTER_DIR.exists():
        raise FileNotFoundError(MASTER_DIR)

    summaries = []
    all_issues = []

    for index, year in enumerate(YEARS, 1):

        print(
            f"\n[{index}/{len(YEARS)}] {year}"
        )

        try:

            reference_info = load_profile1_reference(
                year,
                all_issues
            )

            reference_checks_pass = (
                reference_info["malformed"] == 0
                and reference_info["missing_ids"] == 0
                and reference_info["duplicate_ids"] == 0
            )

            if not reference_checks_pass:

                raise ValueError(
                    "Profile 1 reference integrity failed."
                )

            result, issues = validate_master(
                year,
                reference_info
            )

            summaries.append(result)
            all_issues.extend(issues)

            print(
                f"Master Records: {result['master_records']:,}"
            )

            print(
                f"Master Columns: {result['master_columns']}"
            )

            print(
                f"Unique School IDs: {result['unique_school_ids']:,}"
            )

            print(
                f"Unique Districts: {result['unique_districts']}"
            )

            print(
                f"Missing IDs: {result['missing_ids']}"
            )

            print(
                f"Duplicate IDs: {result['duplicate_ids']}"
            )

            print(
                f"District Mapping Mismatches: "
                f"{result['mapping_mismatches']}"
            )

            print(
                f"Malformed Rows: {result['malformed_rows']}"
            )

            print(
                f"STATUS: {result['status']}"
            )

        except Exception as error:

            print(f"ERROR: {error}")

            summaries.append({

                "academic_year": year,
                "master_records": 0,
                "master_columns": 0,
                "expected_profile1_records": 0,
                "unique_school_ids": 0,
                "unique_districts": 0,
                "missing_ids": 0,
                "duplicate_ids": 0,
                "missing_from_master": 0,
                "extra_ids": 0,
                "missing_districts": 0,
                "missing_district_raw": 0,
                "mapping_mismatches": 0,
                "wrong_academic_year": 0,
                "malformed_rows": 0,
                "duplicate_columns": 0,
                "status": "FAILED",

            })

            add_issue(
                all_issues,
                year,
                "VALIDATION_FAILED",
                actual=str(error)
            )

    # ------------------------------------------
    # SAVE SUMMARY
    # ------------------------------------------

    summary_fields = list(summaries[0].keys())

    save_report(
        SUMMARY_REPORT,
        summaries,
        summary_fields
    )

    # ------------------------------------------
    # SAVE ISSUES
    # ------------------------------------------

    issue_fields = [
        "academic_year",
        "issue",
        "school_id",
        "record_number",
        "expected_value",
        "actual_value",
    ]

    save_report(
        ISSUES_REPORT,
        all_issues,
        issue_fields
    )

    # ------------------------------------------
    # FINAL SUMMARY
    # ------------------------------------------

    passed = sum(
        row["status"] == "PASS"
        for row in summaries
    )

    review = sum(
        row["status"] == "REVIEW_REQUIRED"
        for row in summaries
    )

    failed = sum(
        row["status"] == "FAILED"
        for row in summaries
    )

    total_records = sum(
        row["master_records"]
        for row in summaries
    )

    print("\n" + "=" * 75)
    print("FINAL MASTER INTEGRITY SUMMARY")
    print("=" * 75)

    print(f"Academic Years: {len(summaries)}")
    print(f"Total Master Records: {total_records:,}")
    print(f"PASS: {passed}")
    print(f"Review Required: {review}")
    print(f"Failed: {failed}")

    print("\nREPORTS CREATED")
    print(SUMMARY_REPORT)
    print(ISSUES_REPORT)

    print("\nMASTER DATASET INTEGRITY AUDIT COMPLETED")


if __name__ == "__main__":
    main()

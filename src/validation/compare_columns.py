
"""
ShalaScope Maharashtra
Year-wise Column Comparison

Purpose:
1. Compare columns across all academic years.
2. Identify schema changes.
3. Identify missing or newly introduced columns.
4. Compare file categories and row counts.
5. Generate two CSV audit reports.

This script does not modify original datasets.
"""

from pathlib import Path
import csv


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

AUDIT_DIR = ROOT / "reports" / "data_audit"

COLUMN_INPUT = AUDIT_DIR / "csv_column_inventory.csv"
FILE_INPUT = AUDIT_DIR / "csv_file_audit.csv"

OUTPUT_MATRIX = AUDIT_DIR / "column_presence_matrix.csv"
OUTPUT_SUMMARY = AUDIT_DIR / "year_category_summary.csv"
OUTPUT_UNKNOWN = AUDIT_DIR / "unclassified_files.csv"

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

CATEGORIES = [
    "profile_1",
    "profile_2",
    "enrolment_1",
    "enrolment_2",
    "facility",
    "teacher",
    "safety",
]


# --------------------------------------------------
# CATEGORY DETECTION
# --------------------------------------------------

def identify_category(record):
    """
    Identifies dataset category using archive and CSV names.
    """

    archive = str(record.get("archive_name", "")).lower()
    filename = str(record.get("file_name", "")).lower()

    combined = archive + " " + filename

    if "safety" in combined:
        return "safety"

    if "profile_data_1" in combined or "prof1" in combined:
        return "profile_1"

    if "profile_data_2" in combined or "prof2" in combined:
        return "profile_2"

    if (
        "enrolment_data_1" in combined
        or "enrollment_data_1" in combined
        or "enr1" in combined
    ):
        return "enrolment_1"

    if (
        "enrolment_data_2" in combined
        or "enrollment_data_2" in combined
        or "enr2" in combined
    ):
        return "enrolment_2"

    if "facility_data" in combined or "127_fac" in combined or "27_fac" in combined:
        return "facility"

    if "teacher_data" in combined or "127_tch" in combined or "27_tch" in combined:
        return "teacher"

    return "unclassified"


# --------------------------------------------------
# READ CSV REPORT
# --------------------------------------------------

def read_report(path):

    if not path.exists():
        raise FileNotFoundError(
            f"Required audit report not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        return list(csv.DictReader(file))


# --------------------------------------------------
# BUILD COLUMN PRESENCE MATRIX
# --------------------------------------------------

def build_column_matrix(records):

    presence = {}
    positions = {}
    unknown = []

    for record in records:

        year = record.get("academic_year", "")
        category = identify_category(record)

        if year not in YEARS:
            unknown.append(record)
            continue

        if category == "unclassified":
            unknown.append(record)
            continue

        column = str(
            record.get("column_name", "")
        ).strip()

        if not column:
            continue

        key = (category, column)

        if key not in presence:
            presence[key] = set()
            positions[key] = {}

        presence[key].add(year)

        position = record.get("position", "")

        positions[key][year] = position

    rows = []

    for category, column in sorted(
        presence.keys()
    ):

        key = (category, column)

        row = {
            "category": category,
            "column_name": column,
            "years_available": len(presence[key]),
        }

        for year in YEARS:

            row[year] = (
                "YES" if year in presence[key]
                else "NO"
            )

            row[f"{year}_position"] = (
                positions[key].get(year, "")
            )

        rows.append(row)

    return rows, unknown


# --------------------------------------------------
# BUILD YEAR-WISE CATEGORY SUMMARY
# --------------------------------------------------

def build_category_summary(records):

    summary = {}

    unknown = []

    for record in records:

        year = record.get("academic_year", "")
        category = identify_category(record)

        if year not in YEARS:
            unknown.append(record)
            continue

        if category == "unclassified":
            unknown.append(record)
            continue

        key = (year, category)

        if key not in summary:

            summary[key] = {
                "academic_year": year,
                "category": category,
                "file_count": 0,
                "total_rows": 0,
                "column_counts": [],
                "files": [],
                "failed_files": 0,
                "warning_files": 0,
            }

        item = summary[key]

        item["file_count"] += 1
        item["total_rows"] += int(
            record.get("rows", 0) or 0
        )

        item["column_counts"].append(
            record.get("columns", "")
        )

        item["files"].append(
            record.get("file_name", "")
        )

        status = record.get("status", "").upper()

        if status == "FAILED":
            item["failed_files"] += 1

        if status == "WARNING":
            item["warning_files"] += 1

    rows = []

    for year in YEARS:

        for category in CATEGORIES:

            item = summary.get((year, category))

            if item is None:
                rows.append({
                    "academic_year": year,
                    "category": category,
                    "file_count": 0,
                    "total_rows": 0,
                    "column_counts": "",
                    "files": "",
                    "failed_files": 0,
                    "warning_files": 0,
                })
                continue

            rows.append({
                "academic_year": year,
                "category": category,
                "file_count": item["file_count"],
                "total_rows": item["total_rows"],
                "column_counts": ";".join(
                    map(str, item["column_counts"])
                ),
                "files": ";".join(item["files"]),
                "failed_files": item["failed_files"],
                "warning_files": item["warning_files"],
            })

    return rows, unknown


# --------------------------------------------------
# SAVE REPORT
# --------------------------------------------------

def save_csv(path, rows, fields):

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


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("\nSHALASCOPE - COLUMN COMPARISON")
    print("=" * 60)

    column_records = read_report(COLUMN_INPUT)
    file_records = read_report(FILE_INPUT)

    matrix, unknown_columns = build_column_matrix(
        column_records
    )

    summary, unknown_files = build_category_summary(
        file_records
    )

    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Save column matrix.
    matrix_fields = [
        "category",
        "column_name",
        "years_available"
    ]

    for year in YEARS:
        matrix_fields.extend([
            year,
            f"{year}_position"
        ])

    save_csv(
        OUTPUT_MATRIX,
        matrix,
        matrix_fields
    )

    # Save year/category summary.
    summary_fields = [
        "academic_year",
        "category",
        "file_count",
        "total_rows",
        "column_counts",
        "files",
        "failed_files",
        "warning_files"
    ]

    save_csv(
        OUTPUT_SUMMARY,
        summary,
        summary_fields
    )

    # Save unclassified files, if any.
    unknown_records = (
        unknown_columns + unknown_files
    )

    if unknown_records:

        unknown_fields = list(
            dict.fromkeys(
                key
                for record in unknown_records
                for key in record.keys()
            )
        )

        save_csv(
            OUTPUT_UNKNOWN,
            unknown_records,
            unknown_fields
        )

    print(f"Column records: {len(column_records)}")
    print(f"File records: {len(file_records)}")
    print(f"Unique column mappings: {len(matrix)}")

    print("\nYEAR-WISE CATEGORY COVERAGE")
    print("-" * 60)

    for year in YEARS:

        available = sum(
            item["file_count"] > 0
            for item in summary
            if item["academic_year"] == year
        )

        print(
            f"{year}: {available}/"
            f"{len(CATEGORIES)} categories"
        )

    print("\nUNCLASSIFIED RECORDS:", len(unknown_records))

    print("\nREPORTS CREATED")
    print(OUTPUT_MATRIX)
    print(OUTPUT_SUMMARY)

    if unknown_records:
        print(OUTPUT_UNKNOWN)

    print("\nCOLUMN COMPARISON COMPLETED")


if __name__ == "__main__":
    main()


"""
ShalaScope Maharashtra
Teacher School ID Audit

Checks:
1. Missing School IDs
2. Duplicate School IDs
3. Unique School IDs
4. Duplicate occurrence counts
5. Year-wise audit summary

Original CSV files are never modified.
Python standard library only.
"""

from pathlib import Path
from collections import defaultdict
import csv
import re


# ==================================================
# 1. PROJECT PATHS
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

EXTRACT_ROOT = ROOT / "data" / "extracted"
REPORT_DIR = ROOT / "reports" / "data_audit"

SUMMARY_REPORT = REPORT_DIR / "teacher_school_id_audit_summary.csv"
DUPLICATE_REPORT = REPORT_DIR / "teacher_duplicate_school_ids.csv"
MISSING_REPORT = REPORT_DIR / "teacher_missing_school_ids.csv"

YEARS = {
    "2018-19",
    "2019-20",
    "2020-21",
    "2021-22",
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
}

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

ID_ALIASES = [
    "pseudocode",
    "psuedocode",
    "schoolid",
    "udiseid",
]


# ==================================================
# 2. NORMALIZE COLUMN NAMES
# ==================================================

def norm(value):
    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


# ==================================================
# 3. IDENTIFY TEACHER FILES
# ==================================================

def is_teacher_csv(path):

    name = path.name.lower()

    archive_parts = [
        part.lower()
        for part in path.parts
    ]

    return (
        any("teacher_data" in part for part in archive_parts)
        or re.search(r"(^|[_-])tch([_.-]|$)", name) is not None
    )


def get_year(path):

    for part in path.parts:
        if part in YEARS:
            return part

    return "UNKNOWN"


# ==================================================
# 4. OPEN CSV
# ==================================================

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

            return handle, dialect, encoding

        except UnicodeDecodeError as error:

            last_error = error

            if handle is not None:
                handle.close()

    raise UnicodeError(
        f"Could not decode {path}: {last_error}"
    )


# ==================================================
# 5. FIND SCHOOL ID COLUMN
# ==================================================

def find_school_id_column(headers):

    normalized = {
        norm(header): index
        for index, header in enumerate(headers)
        if header is not None
    }

    for alias in ID_ALIASES:

        if alias in normalized:
            return normalized[alias], headers[normalized[alias]]

    return None, None


# ==================================================
# 6. AUDIT ONE TEACHER FILE
# ==================================================

def audit_file(path):

    year = get_year(path)

    handle, dialect, encoding = open_csv(path)

    total_records = 0
    blank_rows = 0

    missing_records = []

    id_records = defaultdict(list)

    malformed_rows = 0

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        if not headers:
            raise ValueError("CSV header is empty.")

        id_index, id_column = find_school_id_column(headers)

        if id_index is None:

            return {
                "summary": {
                    "academic_year": year,
                    "source_file": path.name,
                    "school_id_column": "",
                    "total_records": 0,
                    "unique_school_ids": 0,
                    "missing_school_ids": 0,
                    "missing_percentage": 0,
                    "duplicate_id_count": 0,
                    "duplicate_rows": 0,
                    "duplicate_excess_rows": 0,
                    "malformed_rows": 0,
                    "status": "SCHOOL_ID_COLUMN_MISSING",
                },
                "duplicates": [],
                "missing": [],
            }

        # CSV record number starts at 2 because row 1 is header.
        for record_number, row in enumerate(reader, start=2):

            if not row or all(
                not str(value).strip()
                for value in row
            ):
                blank_rows += 1
                continue

            total_records += 1

            if len(row) != len(headers):
                malformed_rows += 1

            raw_id = (
                row[id_index]
                if id_index < len(row)
                else ""
            )

            school_id = str(raw_id).strip()

            if school_id.lower() in MISSING_VALUES:

                missing_records.append({
                    "academic_year": year,
                    "source_file": path.name,
                    "record_number": record_number,
                    "school_id": school_id,
                })

            else:

                # Keep ID as text to preserve leading zeros.
                id_records[school_id].append(record_number)

    finally:
        handle.close()

    # ------------------------------------------
    # FIND DUPLICATE IDS
    # ------------------------------------------

    duplicate_records = []

    for school_id, record_numbers in sorted(id_records.items()):

        if len(record_numbers) > 1:

            duplicate_records.append({

                "academic_year": year,
                "source_file": path.name,
                "school_id": school_id,
                "occurrences": len(record_numbers),
                "record_numbers": ";".join(
                    str(number)
                    for number in record_numbers
                ),

            })

    duplicate_id_count = len(duplicate_records)

    duplicate_rows = sum(
        item["occurrences"]
        for item in duplicate_records
    )

    duplicate_excess_rows = sum(
        item["occurrences"] - 1
        for item in duplicate_records
    )

    missing_count = len(missing_records)

    missing_percentage = (
        round(100 * missing_count / total_records, 2)
        if total_records > 0
        else 0
    )

    # ------------------------------------------
    # DETERMINE STATUS
    # ------------------------------------------

    if total_records == 0:

        status = "NO_DATA_ROWS"

    elif duplicate_id_count > 0 and missing_count > 0:

        status = "DUPLICATES_AND_MISSING"

    elif duplicate_id_count > 0:

        status = "DUPLICATES_FOUND"

    elif missing_count > 0:

        status = "MISSING_IDS_FOUND"

    else:

        status = "PASS"

    summary = {

        "academic_year": year,
        "source_file": path.name,
        "school_id_column": id_column,
        "total_records": total_records,
        "unique_school_ids": len(id_records),
        "missing_school_ids": missing_count,
        "missing_percentage": missing_percentage,
        "duplicate_id_count": duplicate_id_count,
        "duplicate_rows": duplicate_rows,
        "duplicate_excess_rows": duplicate_excess_rows,
        "malformed_rows": malformed_rows,
        "status": status,

    }

    return {
        "summary": summary,
        "duplicates": duplicate_records,
        "missing": missing_records,
    }


# ==================================================
# 7. SAVE REPORT
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
# 8. MAIN PROGRAM
# ==================================================

def main():

    print("\nSHALASCOPE - TEACHER SCHOOL ID AUDIT")
    print("=" * 70)

    if not EXTRACT_ROOT.exists():

        raise FileNotFoundError(
            f"Extracted folder not found: {EXTRACT_ROOT}"
        )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    teacher_files = sorted(
        path
        for path in EXTRACT_ROOT.rglob("*.csv")
        if is_teacher_csv(path)
    )

    if not teacher_files:

        raise FileNotFoundError(
            "No Teacher CSV files found."
        )

    summaries = []
    all_duplicates = []
    all_missing = []

    for index, path in enumerate(teacher_files, 1):

        year = get_year(path)

        print(
            f"\n[{index}/{len(teacher_files)}] "
            f"{year} | {path.name}"
        )

        try:

            result = audit_file(path)

            summary = result["summary"]

            summaries.append(summary)

            all_duplicates.extend(
                result["duplicates"]
            )

            all_missing.extend(
                result["missing"]
            )

            print(
                f"Records: {summary['total_records']:,} | "
                f"Unique IDs: {summary['unique_school_ids']:,}"
            )

            print(
                f"Missing IDs: {summary['missing_school_ids']:,} | "
                f"Duplicate IDs: {summary['duplicate_id_count']:,}"
            )

            print(
                f"Status: {summary['status']}"
            )

        except Exception as error:

            print(f"ERROR: {error}")

            summaries.append({

                "academic_year": year,
                "source_file": path.name,
                "school_id_column": "",
                "total_records": 0,
                "unique_school_ids": 0,
                "missing_school_ids": 0,
                "missing_percentage": 0,
                "duplicate_id_count": 0,
                "duplicate_rows": 0,
                "duplicate_excess_rows": 0,
                "malformed_rows": 0,
                "status": "FAILED",

            })

    # ------------------------------------------
    # SAVE SUMMARY
    # ------------------------------------------

    summary_fields = [
        "academic_year",
        "source_file",
        "school_id_column",
        "total_records",
        "unique_school_ids",
        "missing_school_ids",
        "missing_percentage",
        "duplicate_id_count",
        "duplicate_rows",
        "duplicate_excess_rows",
        "malformed_rows",
        "status",
    ]

    save_report(
        SUMMARY_REPORT,
        summaries,
        summary_fields
    )

    # ------------------------------------------
    # SAVE DUPLICATE IDS
    # ------------------------------------------

    duplicate_fields = [
        "academic_year",
        "source_file",
        "school_id",
        "occurrences",
        "record_numbers",
    ]

    save_report(
        DUPLICATE_REPORT,
        all_duplicates,
        duplicate_fields
    )

    # ------------------------------------------
    # SAVE MISSING IDS
    # ------------------------------------------

    missing_fields = [
        "academic_year",
        "source_file",
        "record_number",
        "school_id",
    ]

    save_report(
        MISSING_REPORT,
        all_missing,
        missing_fields
    )

    # ------------------------------------------
    # FINAL SUMMARY
    # ------------------------------------------

    passed = sum(
        row["status"] == "PASS"
        for row in summaries
    )

    failed = sum(
        row["status"] == "FAILED"
        for row in summaries
    )

    total_missing = sum(
        row["missing_school_ids"]
        for row in summaries
    )

    total_duplicate_ids = sum(
        row["duplicate_id_count"]
        for row in summaries
    )

    print("\n" + "=" * 70)
    print("FINAL SCHOOL ID AUDIT SUMMARY")
    print("=" * 70)

    print(f"Teacher CSV Files : {len(teacher_files)}")
    print(f"PASS              : {passed}")
    print(f"Failed            : {failed}")
    print(f"Missing IDs       : {total_missing:,}")
    print(f"Duplicate IDs     : {total_duplicate_ids:,}")

    print("\nREPORTS CREATED")

    print(SUMMARY_REPORT)
    print(DUPLICATE_REPORT)
    print(MISSING_REPORT)

    print("\nTEACHER SCHOOL ID AUDIT COMPLETED")


if __name__ == "__main__":
    main()

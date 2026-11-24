
"""
ShalaScope Maharashtra
CSV Structure and Quality Audit

Checks:
1. Extracted CSV files
2. Academic year and archive source
3. Row count and column count
4. Column names and duplicate headers
5. Encoding and delimiter
6. Rows with unexpected column counts
7. Empty rows

Does not modify the original CSV files.
Uses only Python built-in libraries.
"""

from pathlib import Path
import csv
from collections import defaultdict


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

EXTRACT_ROOT = ROOT / "data" / "extracted"

REPORT_DIR = ROOT / "reports" / "data_audit"

FILE_REPORT = REPORT_DIR / "csv_file_audit.csv"
COLUMN_REPORT = REPORT_DIR / "csv_column_inventory.csv"

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

ENCODINGS = [
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "latin-1",
]


# --------------------------------------------------
# DETECT CSV ENCODING AND DELIMITER
# --------------------------------------------------

def detect_csv_format(file_path):
    """
    Detects a usable text encoding and CSV delimiter.
    """

    for encoding in ENCODINGS:

        try:
            with file_path.open(
                "r",
                encoding=encoding,
                newline=""
            ) as file:

                sample = file.read(65536)

                if not sample:
                    return encoding, csv.excel

                try:
                    dialect = csv.Sniffer().sniff(
                        sample,
                        delimiters=",;\t|"
                    )
                except csv.Error:
                    dialect = csv.excel

                return encoding, dialect

        except UnicodeDecodeError:
            continue

    raise ValueError("Unsupported CSV encoding")


# --------------------------------------------------
# AUDIT ONE CSV FILE
# --------------------------------------------------

def audit_csv(file_path):

    result = {
        "status": "PENDING",
        "rows": 0,
        "columns": 0,
        "encoding": "",
        "delimiter": "",
        "blank_rows": 0,
        "column_mismatch_rows": 0,
        "duplicate_headers": 0,
        "error": ""
    }

    column_records = []

    try:

        encoding, dialect = detect_csv_format(file_path)

        with file_path.open(
            "r",
            encoding=encoding,
            newline=""
        ) as file:

            reader = csv.reader(file, dialect)

            header = next(reader, [])

            if not header:
                raise ValueError("Empty CSV or missing header")

            clean_headers = [
                str(name).strip()
                for name in header
            ]

            duplicate_count = (
                len(clean_headers)
                - len(set(clean_headers))
            )

            result["columns"] = len(clean_headers)
            result["encoding"] = encoding
            result["delimiter"] = repr(dialect.delimiter)
            result["duplicate_headers"] = duplicate_count

            for position, name in enumerate(
                clean_headers, start=1
            ):

                column_records.append({
                    "position": position,
                    "column_name": name,
                    "is_duplicate": (
                        clean_headers.count(name) > 1
                    )
                })

            expected_width = len(header)

            for row in reader:

                if not row or all(
                    not str(value).strip()
                    for value in row
                ):
                    result["blank_rows"] += 1
                    continue

                result["rows"] += 1

                if len(row) != expected_width:
                    result["column_mismatch_rows"] += 1

        result["status"] = (
            "WARNING"
            if (
                duplicate_count > 0
                or result["column_mismatch_rows"] > 0
            )
            else "PASS"
        )

    except Exception as error:

        result["status"] = "FAILED"
        result["error"] = str(error)

    return result, column_records


# --------------------------------------------------
# MAIN AUDIT
# --------------------------------------------------

def main():

    if not EXTRACT_ROOT.exists():
        raise FileNotFoundError(
            f"Extracted folder not found: {EXTRACT_ROOT}"
        )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    csv_files = sorted(
        EXTRACT_ROOT.rglob("*.csv")
    )

    if not csv_files:
        raise FileNotFoundError(
            "No CSV files found. Check ZIP extraction."
        )

    file_results = []
    column_results = []

    year_summary = defaultdict(
        lambda: {
            "files": 0,
            "rows": 0,
            "failed": 0,
            "warnings": 0
        }
    )

    print("\nSHALASCOPE - CSV DATA AUDIT")
    print("=" * 65)

    for index, file_path in enumerate(csv_files, 1):

        relative = file_path.relative_to(EXTRACT_ROOT)

        year = relative.parts[0]

        archive_name = (
            relative.parts[1]
            if len(relative.parts) > 1
            else "Unknown"
        )

        print(
            f"\n[{index}/{len(csv_files)}] "
            f"{year} | {file_path.name}"
        )

        audit, columns = audit_csv(file_path)

        row = {
            "academic_year": year,
            "archive_name": archive_name,
            "file_name": file_path.name,
            "relative_path": str(
                file_path.relative_to(ROOT)
            ),
            "file_size_mb": round(
                file_path.stat().st_size / (1024 * 1024),
                3
            ),
            **audit
        }

        file_results.append(row)

        for column in columns:

            column_results.append({
                "academic_year": year,
                "archive_name": archive_name,
                "file_name": file_path.name,
                **column
            })

        summary = year_summary[year]

        summary["files"] += 1
        summary["rows"] += audit["rows"]

        if audit["status"] == "FAILED":
            summary["failed"] += 1

        if audit["status"] == "WARNING":
            summary["warnings"] += 1

        print(
            f"Status: {audit['status']} | "
            f"Rows: {audit['rows']:,} | "
            f"Columns: {audit['columns']}"
        )

        if audit["error"]:
            print(f"Error: {audit['error']}")

    # --------------------------------------------------
    # SAVE FILE AUDIT
    # --------------------------------------------------

    file_fields = list(file_results[0].keys())

    with FILE_REPORT.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=file_fields
        )

        writer.writeheader()
        writer.writerows(file_results)

    # --------------------------------------------------
    # SAVE COLUMN INVENTORY
    # --------------------------------------------------

    column_fields = [
        "academic_year",
        "archive_name",
        "file_name",
        "position",
        "column_name",
        "is_duplicate"
    ]

    with COLUMN_REPORT.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=column_fields
        )

        writer.writeheader()
        writer.writerows(column_results)

    # --------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------

    passed = sum(
        item["status"] == "PASS"
        for item in file_results
    )

    warnings = sum(
        item["status"] == "WARNING"
        for item in file_results
    )

    failed = sum(
        item["status"] == "FAILED"
        for item in file_results
    )

    print("\n" + "=" * 65)
    print("YEAR-WISE CSV SUMMARY")
    print("=" * 65)

    for year in EXPECTED_YEARS:

        data = year_summary[year]

        print(
            f"{year}: "
            f"{data['files']} CSV files | "
            f"{data['rows']:,} data rows | "
            f"{data['failed']} failed | "
            f"{data['warnings']} warnings"
        )

    print("\n" + "=" * 65)
    print("FINAL AUDIT")
    print(f"Total CSV files : {len(file_results)}")
    print(f"Passed          : {passed}")
    print(f"Warnings        : {warnings}")
    print(f"Failed          : {failed}")

    print(f"\nFile Audit: {FILE_REPORT}")
    print(f"Column Audit: {COLUMN_REPORT}")

    print("\nCSV AUDIT COMPLETED")


if __name__ == "__main__":
    main()

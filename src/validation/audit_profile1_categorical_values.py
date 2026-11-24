
"""
ShalaScope Maharashtra
Profile 1 Categorical Value Audit

Audits categorical fields across 8 academic years.

Checks:
1. Unique values and their frequencies.
2. Missing values.
3. Value percentages by year.
4. Column availability.
5. Preserves numeric codes as text.

Original master CSV files are never modified.
Python standard library only.
"""

from pathlib import Path
from collections import Counter
import csv
import re


# ==================================================
# 1. PATHS AND SETTINGS
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

MASTER_DIR = ROOT / "data" / "processed" / "school_year"

REPORT_DIR = ROOT / "reports" / "data_audit"

OUTPUT_REPORT = (
    REPORT_DIR / "profile1_categorical_value_audit.csv"
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

TARGET_COLUMNS = [
    "rural_urban",
    "school_category",
    "school_type",
    "managment",
    "special_school_for_cwsn",
    "shift_school",
    "resi_school",
    "minority_school",
    "pre_primary",
    "medium_instr1",
]

ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "latin-1",
)

MISSING_VALUES = {
    "", "na", "n/a", "null", "none", "nan"
}


# ==================================================
# 2. HELPERS
# ==================================================

def norm(value):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


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
        f"Could not decode {path}: {last_error}"
    )


# ==================================================
# 3. PROFILE ONE YEAR
# ==================================================

def audit_year(year):

    path = (
        MASTER_DIR
        / f"maharashtra_school_year_master_{year}.csv"
    )

    if not path.exists():
        raise FileNotFoundError(path)

    handle, dialect = open_csv(path)

    counters = {
        column: Counter()
        for column in TARGET_COLUMNS
    }

    total_records = 0
    malformed_rows = 0

    try:

        reader = csv.DictReader(
            handle,
            dialect=dialect
        )

        headers = reader.fieldnames or []

        normalized_headers = {
            norm(header): header
            for header in headers
        }

        missing_columns = [
            column
            for column in TARGET_COLUMNS
            if norm(column) not in normalized_headers
        ]

        if missing_columns:

            raise ValueError(
                f"{year}: Missing columns: {missing_columns}"
            )

        actual_columns = {
            column: normalized_headers[norm(column)]
            for column in TARGET_COLUMNS
        }

        for row in reader:

            if row is None:
                continue

            if None in row:

                malformed_rows += 1

                raise ValueError(
                    f"{year}: Malformed CSV row detected."
                )

            total_records += 1

            for column, actual_name in actual_columns.items():

                value = str(
                    row.get(actual_name) or ""
                ).strip()

                if value.lower() in MISSING_VALUES:
                    value = "[MISSING]"

                counters[column][value] += 1

    finally:

        handle.close()

    results = []

    for column in TARGET_COLUMNS:

        for value, count in sorted(
            counters[column].items(),
            key=lambda item: (-item[1], item[0])
        ):

            percentage = (
                round(100 * count / total_records, 2)
                if total_records
                else 0
            )

            results.append({

                "academic_year": year,
                "source_column": column,
                "observed_value": value,
                "school_count": count,
                "percentage": percentage,
                "total_records": total_records,
                "unique_values_in_column": len(
                    counters[column]
                ),
                "missing_count": counters[column].get(
                    "[MISSING]", 0
                ),
                "status": "PASS",

            })

    summary = {

        "academic_year": year,
        "total_records": total_records,
        "malformed_rows": malformed_rows,
        "columns_audited": len(counters),
        "status": "PASS",

    }

    return results, summary


# ==================================================
# 4. SAVE REPORT
# ==================================================

def save_report(path, rows):

    fields = [

        "academic_year",
        "source_column",
        "observed_value",
        "school_count",
        "percentage",
        "total_records",
        "unique_values_in_column",
        "missing_count",
        "status",

    ]

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
# 5. MAIN
# ==================================================

def main():

    print("\nSHALASCOPE - PROFILE 1 CATEGORICAL VALUE AUDIT")
    print("=" * 75)

    if not MASTER_DIR.exists():
        raise FileNotFoundError(MASTER_DIR)

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    all_results = []
    summaries = []

    for index, year in enumerate(YEARS, 1):

        print(
            f"\n[{index}/{len(YEARS)}] {year}"
        )

        results, summary = audit_year(year)

        all_results.extend(results)
        summaries.append(summary)

        print(
            f"Records: {summary['total_records']:,}"
        )

        print(
            f"Columns audited: {summary['columns_audited']}"
        )

        print(
            f"Malformed rows: {summary['malformed_rows']}"
        )

        print(
            f"Status: {summary['status']}"
        )

    # ------------------------------------------
    # SAVE REPORT
    # ------------------------------------------

    save_report(
        OUTPUT_REPORT,
        all_results
    )

    # ------------------------------------------
    # FINAL SUMMARY
    # ------------------------------------------

    passed = sum(
        row["status"] == "PASS"
        for row in summaries
    )

    print("\n" + "=" * 75)
    print("FINAL CATEGORICAL AUDIT SUMMARY")
    print("=" * 75)

    print(f"Academic Years: {len(summaries)}")
    print(f"Columns per Year: {len(TARGET_COLUMNS)}")
    print(f"Total Column-Year Checks: {len(summaries) * len(TARGET_COLUMNS)}")
    print(f"PASS: {passed}")

    print("\nREPORT CREATED")
    print(OUTPUT_REPORT)

    print("\nPROFILE 1 CATEGORICAL AUDIT COMPLETED")


if __name__ == "__main__":
    main()

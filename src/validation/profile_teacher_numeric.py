
"""
ShalaScope Maharashtra
Teacher Data Numeric Profiling and Gender Consistency Audit

Features:
1. Finds Teacher CSV files for all eight academic years.
2. Profiles every column except the School ID column.
3. Calculates missing, numeric, non-numeric, zero and negative values.
4. Calculates minimum and maximum values.
5. Validates Male + Female + Transgender = Total Teachers.
6. Supports older total_teacher and newer total_tch columns.
7. Saves two audit reports.
8. Never modifies original CSV files.

Python standard library only.

Run:
python .\src\validation\profile_teacher_numeric.py
"""

from pathlib import Path
import csv
import re


# ==================================================
# 1. PROJECT PATHS
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

EXTRACT_ROOT = ROOT / "data" / "extracted"
REPORT_DIR = ROOT / "reports" / "data_audit"

NUMERIC_REPORT = REPORT_DIR / "teacher_numeric_profile.csv"
GENDER_REPORT = REPORT_DIR / "teacher_gender_consistency.csv"

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


# ==================================================
# 2. NORMALIZE COLUMN NAMES
# ==================================================

def norm(value):
    """Normalize column names by removing spaces and punctuation."""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


# ==================================================
# 3. IDENTIFY TEACHER CSV FILES
# ==================================================

def is_teacher_csv(path):
    """Identify Teacher CSV files."""

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
    """Find academic year from extracted folder path."""

    for part in path.parts:
        if part in YEARS:
            return part

    return "UNKNOWN"


# ==================================================
# 4. OPEN CSV WITH ENCODING DETECTION
# ==================================================

def open_csv(path):
    """Open CSV and detect its delimiter."""

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
        f"Could not decode CSV: {path}. {last_error}"
    )


# ==================================================
# 5. CONVERT VALUES TO NUMBERS
# ==================================================

def to_number(value):
    """
    Returns:
        (number, status)

    Status:
        numeric
        missing
        non_numeric
    """

    text = str(value).strip()

    if text.lower() in MISSING_VALUES:
        return None, "missing"

    try:
        number = float(text.replace(",", ""))
        return number, "numeric"

    except (ValueError, OverflowError):
        return None, "non_numeric"


# ==================================================
# 6. IDENTIFY GENDER COLUMNS
# ==================================================

GENDER_ALIASES = {

    # Older schema: total_teacher
    # Newer schema: total_tch

    "total": {
        "totalteacher",
        "totalteachers",
        "teachertotal",
        "totaltch",
    },

    "male": {
        "male",
        "maleteacher",
        "maleteachers",
    },

    "female": {
        "female",
        "femaleteacher",
        "femaleteachers",
    },

    "transgender": {
        "transgender",
        "transgenderteacher",
        "transgenderteachers",
    },
}


def find_gender_columns(headers):
    """Find gender-related column positions."""

    normalized = {
        norm(name): index
        for index, name in enumerate(headers)
        if name is not None
    }

    result = {}

    for field, aliases in GENDER_ALIASES.items():

        result[field] = next(
            (
                normalized[alias]
                for alias in aliases
                if alias in normalized
            ),
            None
        )

    return result


# ==================================================
# 7. PROFILE ONE TEACHER FILE
# ==================================================

def profile_file(path):

    year = get_year(path)

    handle, dialect, encoding = open_csv(path)

    numeric_stats = {}

    rows_scanned = 0
    blank_rows = 0
    malformed_rows = 0

    gender_checked = 0
    gender_matched = 0
    gender_mismatched = 0
    gender_incomplete = 0

    mismatch_examples = []

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        if not headers:
            raise ValueError("CSV header is empty.")

        normalized_headers = [
            norm(header)
            for header in headers
        ]

        # ------------------------------------------
        # FIND SCHOOL ID COLUMN
        # ------------------------------------------

        school_id_index = next(
            (
                index
                for index, header in enumerate(normalized_headers)
                if header in {
                    "psuedocode",
                    "pseudocode",
                    "schoolid",
                    "udiseid",
                }
            ),
            None
        )

        # ------------------------------------------
        # INITIALIZE NUMERIC PROFILING
        # ------------------------------------------

        for index, header in enumerate(headers):

            if index == school_id_index:
                continue

            numeric_stats[index] = {
                "column_name": header,
                "numeric_count": 0,
                "missing_count": 0,
                "non_numeric_count": 0,
                "zero_count": 0,
                "negative_count": 0,
                "minimum": None,
                "maximum": None,
                "non_numeric_examples": [],
            }

        # ------------------------------------------
        # IDENTIFY GENDER COLUMNS
        # ------------------------------------------

        gender_columns = find_gender_columns(headers)

        required_gender_fields = {
            "total",
            "male",
            "female",
            "transgender",
        }

        gender_missing_columns = [
            field
            for field, index in gender_columns.items()
            if index is None
        ]

        gender_available = not gender_missing_columns

        # ------------------------------------------
        # PROCESS CSV ROWS
        # ------------------------------------------

        for row in reader:

            if not row or all(
                not str(value).strip()
                for value in row
            ):
                blank_rows += 1
                continue

            rows_scanned += 1

            if len(row) != len(headers):
                malformed_rows += 1

            # --------------------------------------
            # NUMERIC COLUMN PROFILING
            # --------------------------------------

            for index, stats in numeric_stats.items():

                raw_value = (
                    row[index]
                    if index < len(row)
                    else ""
                )

                number, status = to_number(raw_value)

                if status == "missing":

                    stats["missing_count"] += 1

                elif status == "non_numeric":

                    stats["non_numeric_count"] += 1

                    if len(stats["non_numeric_examples"]) < 5:

                        stats["non_numeric_examples"].append(
                            str(raw_value)[:50]
                        )

                else:

                    stats["numeric_count"] += 1

                    if number == 0:
                        stats["zero_count"] += 1

                    if number < 0:
                        stats["negative_count"] += 1

                    if (
                        stats["minimum"] is None
                        or number < stats["minimum"]
                    ):
                        stats["minimum"] = number

                    if (
                        stats["maximum"] is None
                        or number > stats["maximum"]
                    ):
                        stats["maximum"] = number

            # --------------------------------------
            # GENDER TOTAL CONSISTENCY
            # --------------------------------------

            if not gender_available:
                continue

            parsed = {}

            for field, index in gender_columns.items():

                raw_value = (
                    row[index]
                    if index < len(row)
                    else ""
                )

                number, status = to_number(raw_value)

                if status != "numeric":
                    parsed[field] = None
                else:
                    parsed[field] = number

            if any(
                parsed[field] is None
                for field in required_gender_fields
            ):

                gender_incomplete += 1
                continue

            gender_checked += 1

            expected_total = (
                parsed["male"]
                + parsed["female"]
                + parsed["transgender"]
            )

            actual_total = parsed["total"]

            if abs(expected_total - actual_total) < 0.000001:

                gender_matched += 1

            else:

                gender_mismatched += 1

                if len(mismatch_examples) < 10:

                    school_id = (
                        row[school_id_index]
                        if (
                            school_id_index is not None
                            and school_id_index < len(row)
                        )
                        else "UNKNOWN"
                    )

                    mismatch_examples.append(
                        f"SchoolID={school_id}; "
                        f"Total={actual_total}; "
                        f"GenderSum={expected_total}"
                    )

    finally:
        handle.close()

    # ==================================================
    # 8. BUILD NUMERIC REPORT
    # ==================================================

    numeric_results = []

    for stats in numeric_stats.values():

        if (
            stats["numeric_count"] > 0
            and stats["non_numeric_count"] == 0
        ):

            classification = "NUMERIC"

        elif stats["numeric_count"] > 0:

            classification = "MIXED"

        elif stats["non_numeric_count"] > 0:

            classification = "NON_NUMERIC"

        else:

            classification = "ALL_MISSING"

        numeric_results.append({

            "academic_year": year,
            "source_file": path.name,
            "column_name": stats["column_name"],
            "rows_scanned": rows_scanned,
            "numeric_values": stats["numeric_count"],
            "missing_values": stats["missing_count"],
            "non_numeric_values": stats["non_numeric_count"],
            "zero_values": stats["zero_count"],
            "negative_values": stats["negative_count"],
            "minimum": stats["minimum"],
            "maximum": stats["maximum"],
            "classification": classification,
            "non_numeric_examples": " | ".join(
                stats["non_numeric_examples"]
            )

        })

    # ==================================================
    # 9. BUILD GENDER REPORT
    # ==================================================

    if not gender_available:

        gender_status = "REQUIRED_COLUMNS_MISSING"

    elif gender_checked == 0:

        gender_status = "NO_VALID_ROWS"

    elif gender_mismatched > 0:

        gender_status = "MISMATCH_FOUND"

    else:

        gender_status = "PASS"

    gender_result = {

        "academic_year": year,
        "source_file": path.name,
        "rows_scanned": rows_scanned,

        "school_id_available": (
            school_id_index is not None
        ),

        "gender_columns_found": ";".join(
            field
            for field, index in gender_columns.items()
            if index is not None
        ),

        "missing_gender_columns": ";".join(
            gender_missing_columns
        ),

        "gender_rows_checked": gender_checked,
        "matched_rows": gender_matched,
        "mismatched_rows": gender_mismatched,
        "incomplete_rows": gender_incomplete,
        "blank_rows": blank_rows,
        "malformed_rows": malformed_rows,
        "status": gender_status,

        "mismatch_examples": " | ".join(
            mismatch_examples
        )

    }

    return numeric_results, gender_result


# ==================================================
# 10. SAVE CSV REPORT
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
# 11. MAIN PROGRAM
# ==================================================

def main():

    print("\nSHALASCOPE - TEACHER DATA AUDIT")
    print("=" * 65)

    if not EXTRACT_ROOT.exists():

        raise FileNotFoundError(
            f"Extracted data folder not found: {EXTRACT_ROOT}"
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

    numeric_results = []
    gender_results = []

    # ------------------------------------------
    # PROCESS ALL TEACHER FILES
    # ------------------------------------------

    for index, path in enumerate(teacher_files, 1):

        year = get_year(path)

        print(
            f"\n[{index}/{len(teacher_files)}] "
            f"{year} | {path.name}"
        )

        try:

            numeric, gender = profile_file(path)

            numeric_results.extend(numeric)
            gender_results.append(gender)

            print(
                f"Rows: {gender['rows_scanned']:,} | "
                f"Gender Checked: "
                f"{gender['gender_rows_checked']:,} | "
                f"Mismatch: "
                f"{gender['mismatched_rows']:,}"
            )

            print(
                f"Status: {gender['status']}"
            )

        except Exception as error:

            print(f"ERROR: {error}")

            gender_results.append({

                "academic_year": year,
                "source_file": path.name,
                "rows_scanned": 0,
                "school_id_available": False,
                "gender_columns_found": "",
                "missing_gender_columns": "",
                "gender_rows_checked": 0,
                "matched_rows": 0,
                "mismatched_rows": 0,
                "incomplete_rows": 0,
                "blank_rows": 0,
                "malformed_rows": 0,
                "status": "FAILED",
                "mismatch_examples": str(error),

            })

    # ==================================================
    # 12. SAVE NUMERIC REPORT
    # ==================================================

    numeric_fields = [

        "academic_year",
        "source_file",
        "column_name",
        "rows_scanned",
        "numeric_values",
        "missing_values",
        "non_numeric_values",
        "zero_values",
        "negative_values",
        "minimum",
        "maximum",
        "classification",
        "non_numeric_examples",

    ]

    save_report(
        NUMERIC_REPORT,
        numeric_results,
        numeric_fields
    )

    # ==================================================
    # 13. SAVE GENDER REPORT
    # ==================================================

    gender_fields = [

        "academic_year",
        "source_file",
        "rows_scanned",
        "school_id_available",
        "gender_columns_found",
        "missing_gender_columns",
        "gender_rows_checked",
        "matched_rows",
        "mismatched_rows",
        "incomplete_rows",
        "blank_rows",
        "malformed_rows",
        "status",
        "mismatch_examples",

    ]

    save_report(
        GENDER_REPORT,
        gender_results,
        gender_fields
    )

    # ==================================================
    # 14. FINAL SUMMARY
    # ==================================================

    passed = sum(
        row["status"] == "PASS"
        for row in gender_results
    )

    mismatched = sum(
        row["status"] == "MISMATCH_FOUND"
        for row in gender_results
    )

    missing_columns = sum(
        row["status"] == "REQUIRED_COLUMNS_MISSING"
        for row in gender_results
    )

    no_valid_rows = sum(
        row["status"] == "NO_VALID_ROWS"
        for row in gender_results
    )

    failed = sum(
        row["status"] == "FAILED"
        for row in gender_results
    )

    print("\n" + "=" * 65)
    print("FINAL TEACHER AUDIT SUMMARY")
    print("=" * 65)

    print(f"Teacher CSV files : {len(teacher_files)}")
    print(f"PASS              : {passed}")
    print(f"Mismatches        : {mismatched}")
    print(f"Missing columns   : {missing_columns}")
    print(f"No valid rows     : {no_valid_rows}")
    print(f"Failed files      : {failed}")

    print("\nREPORTS CREATED")

    print(NUMERIC_REPORT)
    print(GENDER_REPORT)

    print("\nTEACHER DATA AUDIT COMPLETED")


# ==================================================
# 15. RUN PROGRAM
# ==================================================

if __name__ == "__main__":
    main()

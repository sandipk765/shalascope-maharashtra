
"""
ShalaScope Maharashtra
Teacher Semantic Consistency Audit

Years: 2018-19 to 2025-26

Checks:
1. Old and new total teacher column aliases.
2. Gender sum consistency.
3. Computer-trained teacher count <= total teachers.
4. Negative and fractional teacher counts.
5. Missing and non-numeric values.
6. Year-wise teacher totals and computer-training totals.

Original files are never modified.
Python standard library only.
"""

from pathlib import Path
from decimal import Decimal, InvalidOperation
import csv
import re


# ==================================================
# 1. PATHS
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

TEACHER_DIR = (
    ROOT / "data" / "interim" / "standardized" / "teacher"
)

REPORT_DIR = ROOT / "reports" / "data_audit"

SUMMARY_REPORT = (
    REPORT_DIR / "teacher_semantic_consistency_audit.csv"
)

DETAIL_REPORT = (
    REPORT_DIR / "teacher_semantic_consistency_issues.csv"
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
    "", "na", "n/a", "null", "none", "nan"
}

MAX_ISSUE_EXAMPLES = 500


# ==================================================
# 2. HELPERS
# ==================================================

def norm(value):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


def parse_number(value):

    text = str(value or "").strip()

    if text.lower() in MISSING_VALUES:
        return None, "MISSING"

    try:

        number = Decimal(text.replace(",", ""))

        if not number.is_finite():
            return None, "NON_NUMERIC"

        return number, "NUMERIC"

    except (InvalidOperation, ValueError):

        return None, "NON_NUMERIC"


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


def find_field(headers, aliases):

    lookup = {
        norm(header): header
        for header in headers
    }

    for alias in aliases:

        if norm(alias) in lookup:
            return lookup[norm(alias)]

    return None


def add_issue(
    issues,
    year,
    issue,
    school_id,
    details
):

    if len(issues) >= MAX_ISSUE_EXAMPLES:
        return

    issues.append({

        "academic_year": year,
        "issue": issue,
        "school_id": school_id,
        "details": details,

    })


def decimal_text(value):

    if value is None:
        return ""

    return str(value)


# ==================================================
# 3. PROCESS ONE YEAR
# ==================================================

def audit_year(year):

    path = (
        TEACHER_DIR
        / f"maharashtra_teacher_{year}_standardized.csv"
    )

    if not path.exists():
        raise FileNotFoundError(path)

    handle, dialect = open_csv(path)

    issues = []

    rows_scanned = 0

    missing_values = 0
    non_numeric_values = 0
    negative_values = 0
    fractional_values = 0

    gender_mismatches = 0
    computer_over_total = 0

    complete_rows = 0

    total_teacher_sum = Decimal("0")
    male_sum = Decimal("0")
    female_sum = Decimal("0")
    transgender_sum = Decimal("0")
    computer_trained_sum = Decimal("0")

    total_teacher_max = Decimal("0")
    computer_trained_max = Decimal("0")

    try:

        reader = csv.DictReader(
            handle,
            dialect=dialect
        )

        headers = reader.fieldnames or []

        if not headers:
            raise ValueError("Teacher CSV header is empty.")

        # Old and new schema aliases.
        fields = {

            "total": find_field(
                headers,
                ["total_teacher", "total_tch"]
            ),

            "male": find_field(
                headers,
                ["male"]
            ),

            "female": find_field(
                headers,
                ["female"]
            ),

            "transgender": find_field(
                headers,
                ["transgender"]
            ),

            "computer_trained": find_field(
                headers,
                [
                    "total_teacher_trained_computer",
                    "trained_comp"
                ]
            ),

            "school_id": find_field(
                headers,
                [
                    "pseudocode",
                    "psuedocode",
                    "schoolid",
                    "udiseid"
                ]
            ),

        }

        missing_columns = [
            name
            for name, field in fields.items()
            if field is None
        ]

        if missing_columns:

            raise ValueError(
                f"Required columns missing: {missing_columns}"
            )

        field_types = [
            "total",
            "male",
            "female",
            "transgender",
            "computer_trained",
        ]

        # ------------------------------------------
        # PROCESS ROWS
        # ------------------------------------------

        for record_number, row in enumerate(reader, start=2):

            if not row or all(
                not str(value or "").strip()
                for value in row.values()
            ):
                continue

            rows_scanned += 1

            school_id = str(
                row.get(fields["school_id"], "")
            ).strip()

            parsed = {}
            row_valid = True

            for field_name in field_types:

                source_column = fields[field_name]

                number, status = parse_number(
                    row.get(source_column)
                )

                parsed[field_name] = number

                if status == "MISSING":

                    missing_values += 1
                    row_valid = False

                    add_issue(
                        issues,
                        year,
                        "MISSING_VALUE",
                        school_id,
                        f"{source_column} at record {record_number}"
                    )

                elif status == "NON_NUMERIC":

                    non_numeric_values += 1
                    row_valid = False

                    add_issue(
                        issues,
                        year,
                        "NON_NUMERIC_VALUE",
                        school_id,
                        f"{source_column} at record {record_number}"
                    )

                else:

                    if number < 0:

                        negative_values += 1
                        row_valid = False

                        add_issue(
                            issues,
                            year,
                            "NEGATIVE_VALUE",
                            school_id,
                            f"{source_column}={number}"
                        )

                    if number != number.to_integral_value():

                        fractional_values += 1
                        row_valid = False

                        add_issue(
                            issues,
                            year,
                            "FRACTIONAL_TEACHER_COUNT",
                            school_id,
                            f"{source_column}={number}"
                        )

            if not row_valid:
                continue

            complete_rows += 1

            total = parsed["total"]
            male = parsed["male"]
            female = parsed["female"]
            transgender = parsed["transgender"]
            computer = parsed["computer_trained"]

            # ------------------------------------------
            # GENDER CONSISTENCY
            # ------------------------------------------

            gender_sum = male + female + transgender

            if gender_sum != total:

                gender_mismatches += 1

                add_issue(
                    issues,
                    year,
                    "GENDER_TOTAL_MISMATCH",
                    school_id,
                    f"Total={total}; GenderSum={gender_sum}"
                )

            # ------------------------------------------
            # COMPUTER TRAINING RANGE
            # ------------------------------------------

            if computer > total:

                computer_over_total += 1

                add_issue(
                    issues,
                    year,
                    "COMPUTER_TRAINED_EXCEEDS_TOTAL",
                    school_id,
                    f"ComputerTrained={computer}; TotalTeachers={total}"
                )

            # ------------------------------------------
            # AGGREGATES
            # ------------------------------------------

            total_teacher_sum += total
            male_sum += male
            female_sum += female
            transgender_sum += transgender
            computer_trained_sum += computer

            if total > total_teacher_max:
                total_teacher_max = total

            if computer > computer_trained_max:
                computer_trained_max = computer

    finally:

        handle.close()

    # ------------------------------------------
    # COMPLETENESS
    # ------------------------------------------

    expected_values = rows_scanned * len(field_types)

    valid_values = (
        expected_values
        - missing_values
        - non_numeric_values
    )

    completeness_percentage = (
        round(100 * valid_values / expected_values, 2)
        if expected_values
        else 0
    )

    training_percentage = (
        round(
            float(
                computer_trained_sum
                / total_teacher_sum
                * Decimal("100")
            ),
            2
        )
        if total_teacher_sum > 0
        else 0
    )

    # ------------------------------------------
    # STATUS
    # ------------------------------------------

    status = "PASS"

    if (
        missing_values > 0
        or non_numeric_values > 0
        or negative_values > 0
        or fractional_values > 0
        or gender_mismatches > 0
        or computer_over_total > 0
        or complete_rows != rows_scanned
    ):

        status = "REVIEW_REQUIRED"

    result = {

        "academic_year": year,
        "source_file": path.name,

        "total_column_used": fields["total"],
        "computer_column_used": fields["computer_trained"],

        "rows_scanned": rows_scanned,
        "complete_rows": complete_rows,

        "missing_values": missing_values,
        "non_numeric_values": non_numeric_values,
        "negative_values": negative_values,
        "fractional_values": fractional_values,

        "gender_mismatches": gender_mismatches,
        "computer_over_total": computer_over_total,

        "total_teachers_statewide": decimal_text(
            total_teacher_sum
        ),

        "male_teachers_statewide": decimal_text(
            male_sum
        ),

        "female_teachers_statewide": decimal_text(
            female_sum
        ),

        "transgender_teachers_statewide": decimal_text(
            transgender_sum
        ),

        "computer_trained_teachers_statewide": decimal_text(
            computer_trained_sum
        ),

        "computer_training_percentage": training_percentage,

        "maximum_teachers_in_one_school": decimal_text(
            total_teacher_max
        ),

        "maximum_computer_trained_in_one_school": decimal_text(
            computer_trained_max
        ),

        "completeness_percentage": completeness_percentage,

        "status": status,

    }

    return result, issues


# ==================================================
# 4. SAVE REPORTS
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
# 5. MAIN PROGRAM
# ==================================================

def main():

    print("\nSHALASCOPE - TEACHER SEMANTIC CONSISTENCY AUDIT")
    print("=" * 75)

    if not TEACHER_DIR.exists():
        raise FileNotFoundError(TEACHER_DIR)

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    summaries = []
    all_issues = []

    for index, year in enumerate(YEARS, 1):

        print(
            f"\n[{index}/{len(YEARS)}] Academic Year: {year}"
        )

        try:

            result, issues = audit_year(year)

            summaries.append(result)
            all_issues.extend(issues)

            print(
                f"Total Column: {result['total_column_used']}"
            )

            print(
                f"Computer Column: "
                f"{result['computer_column_used']}"
            )

            print(
                f"Rows Scanned: {result['rows_scanned']:,}"
            )

            print(
                f"Completeness: "
                f"{result['completeness_percentage']}%"
            )

            print(
                f"Gender Mismatches: "
                f"{result['gender_mismatches']}"
            )

            print(
                f"Computer Trained > Total: "
                f"{result['computer_over_total']}"
            )

            print(
                f"Statewide Total Teachers: "
                f"{result['total_teachers_statewide']}"
            )

            print(
                f"Statewide Computer-Trained Teachers: "
                f"{result['computer_trained_teachers_statewide']}"
            )

            print(
                f"Computer Training Ratio: "
                f"{result['computer_training_percentage']}%"
            )

            print(
                f"STATUS: {result['status']}"
            )

        except Exception as error:

            print(f"ERROR: {error}")

            summaries.append({

                "academic_year": year,
                "source_file": "",
                "total_column_used": "",
                "computer_column_used": "",
                "rows_scanned": 0,
                "complete_rows": 0,
                "missing_values": 0,
                "non_numeric_values": 0,
                "negative_values": 0,
                "fractional_values": 0,
                "gender_mismatches": 0,
                "computer_over_total": 0,
                "total_teachers_statewide": "",
                "male_teachers_statewide": "",
                "female_teachers_statewide": "",
                "transgender_teachers_statewide": "",
                "computer_trained_teachers_statewide": "",
                "computer_training_percentage": 0,
                "maximum_teachers_in_one_school": "",
                "maximum_computer_trained_in_one_school": "",
                "completeness_percentage": 0,
                "status": "FAILED",

            })

            add_issue(
                all_issues,
                year,
                "FILE_PROCESSING_FAILED",
                "",
                str(error)
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
    # SAVE DETAILS
    # ------------------------------------------

    detail_fields = [
        "academic_year",
        "issue",
        "school_id",
        "details",
    ]

    save_report(
        DETAIL_REPORT,
        all_issues,
        detail_fields
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

    print("\n" + "=" * 75)
    print("FINAL TEACHER SEMANTIC AUDIT SUMMARY")
    print("=" * 75)

    print(f"Academic Years: {len(summaries)}")
    print(f"PASS: {passed}")
    print(f"Review Required: {review}")
    print(f"Failed: {failed}")

    print("\nREPORTS CREATED")
    print(SUMMARY_REPORT)
    print(DETAIL_REPORT)

    print("\nTEACHER SEMANTIC AUDIT COMPLETED")


if __name__ == "__main__":
    main()

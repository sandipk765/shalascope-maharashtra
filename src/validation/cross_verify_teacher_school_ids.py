
"""
ShalaScope Maharashtra
Teacher and School Profile ID Cross-Verification

Checks all 8 academic years:
1. Teacher vs Profile 1
2. Teacher vs Profile 2
3. Profile 1 vs Profile 2
4. Missing School IDs
5. Duplicate School IDs
6. Malformed CSV rows

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

SUMMARY_REPORT = REPORT_DIR / "teacher_school_cross_verification.csv"
DETAIL_REPORT = REPORT_DIR / "teacher_school_cross_verification_details.csv"

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
# 3. IDENTIFY CSV FILES
# ==================================================

FILE_PATTERNS = {
    "teacher": re.compile(r"(^|[_-])tch\.csv$", re.I),
    "profile1": re.compile(r"(^|[_-])prof1\.csv$", re.I),
    "profile2": re.compile(r"(^|[_-])prof2\.csv$", re.I),
}


def find_year_file(year, file_type, all_files):

    pattern = FILE_PATTERNS[file_type]

    matches = [
        path
        for path in all_files
        if year in path.parts and pattern.search(path.name)
    ]

    if len(matches) != 1:

        raise RuntimeError(
            f"{year}: Expected exactly one {file_type} CSV, "
            f"but found {len(matches)}: {matches}"
        )

    return matches[0]


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

            return handle, dialect

        except UnicodeDecodeError as error:

            last_error = error

            if handle is not None:
                handle.close()

    raise UnicodeError(
        f"Cannot decode {path}: {last_error}"
    )


# ==================================================
# 5. FIND SCHOOL ID COLUMN
# ==================================================

def find_id_column(headers):

    normalized = {
        norm(header): index
        for index, header in enumerate(headers)
        if header is not None
    }

    for alias in ID_ALIASES:

        if alias in normalized:

            index = normalized[alias]

            return index, headers[index]

    return None, None


# ==================================================
# 6. READ AND PROFILE ONE CSV
# ==================================================

def read_school_ids(path, year, dataset_type):

    handle, dialect = open_csv(path)

    total_records = 0
    blank_rows = 0
    malformed_rows = 0
    missing_ids = 0

    id_rows = defaultdict(list)

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        if not headers:
            raise ValueError("Empty CSV header.")

        id_index, id_column = find_id_column(headers)

        if id_index is None:

            raise ValueError(
                f"School ID column not found in {path.name}. "
                f"Available columns: {headers}"
            )

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

                missing_ids += 1
                continue

            # Keep School ID as text.
            # This preserves leading zeros.
            id_rows[school_id].append(record_number)

    finally:

        handle.close()

    duplicate_ids = {
        school_id: rows
        for school_id, rows in id_rows.items()
        if len(rows) > 1
    }

    duplicate_excess_rows = sum(
        len(rows) - 1
        for rows in duplicate_ids.values()
    )

    return {

        "year": year,
        "dataset_type": dataset_type,
        "source_file": path.name,
        "id_column": id_column,

        "total_records": total_records,
        "blank_rows": blank_rows,
        "malformed_rows": malformed_rows,
        "missing_ids": missing_ids,

        "unique_ids": set(id_rows.keys()),
        "id_rows": dict(id_rows),

        "duplicate_ids": duplicate_ids,
        "duplicate_id_count": len(duplicate_ids),
        "duplicate_excess_rows": duplicate_excess_rows,

    }


# ==================================================
# 7. CREATE ISSUE DETAILS
# ==================================================

def add_detail(
    details,
    year,
    comparison,
    issue,
    dataset,
    school_id="",
    occurrences=0,
    record_numbers=""
):

    details.append({

        "academic_year": year,
        "comparison": comparison,
        "issue": issue,
        "dataset": dataset,
        "school_id": school_id,
        "occurrences": occurrences,
        "record_numbers": record_numbers,

    })


# ==================================================
# 8. ADD MISSING AND DUPLICATE DETAILS
# ==================================================

def add_dataset_issues(data, details):

    year = data["year"]
    dataset_type = data["dataset_type"]

    # Missing ID records are identified by count.
    # School ID values are not available for these rows.

    if data["missing_ids"] > 0:

        add_detail(
            details,
            year,
            "INDIVIDUAL_DATASET_AUDIT",
            "MISSING_SCHOOL_ID",
            dataset_type,
            occurrences=data["missing_ids"]
        )

    # Duplicate School IDs

    for school_id, rows in data["duplicate_ids"].items():

        add_detail(
            details,
            year,
            "INDIVIDUAL_DATASET_AUDIT",
            "DUPLICATE_SCHOOL_ID",
            dataset_type,
            school_id,
            len(rows),
            ";".join(str(number) for number in rows)
        )

    # Malformed rows

    if data["malformed_rows"] > 0:

        add_detail(
            details,
            year,
            "INDIVIDUAL_DATASET_AUDIT",
            "MALFORMED_ROWS",
            dataset_type,
            occurrences=data["malformed_rows"]
        )


# ==================================================
# 9. COMPARE TWO DATASETS
# ==================================================

def compare_datasets(
    year,
    left,
    right,
    comparison_name,
    details
):

    left_only = left["unique_ids"] - right["unique_ids"]

    right_only = right["unique_ids"] - left["unique_ids"]

    matched = left["unique_ids"] & right["unique_ids"]

    # IDs found in left but not right.

    for school_id in sorted(left_only):

        add_detail(
            details,
            year,
            comparison_name,
            "ID_NOT_FOUND_IN_RIGHT_DATASET",
            left["dataset_type"],
            school_id
        )

    # IDs found in right but not left.

    for school_id in sorted(right_only):

        add_detail(
            details,
            year,
            comparison_name,
            "ID_NOT_FOUND_IN_LEFT_DATASET",
            right["dataset_type"],
            school_id
        )

    return {

        "matched_unique_ids": len(matched),
        "left_only_unique_ids": len(left_only),
        "right_only_unique_ids": len(right_only),

    }


# ==================================================
# 10. SAVE REPORT
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

    print("\nSHALASCOPE - SCHOOL ID CROSS VERIFICATION")
    print("=" * 75)

    if not EXTRACT_ROOT.exists():

        raise FileNotFoundError(
            f"Extracted folder not found: {EXTRACT_ROOT}"
        )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    all_files = list(
        EXTRACT_ROOT.rglob("*.csv")
    )

    summaries = []
    all_details = []

    # --------------------------------------------------
    # PROCESS EACH ACADEMIC YEAR
    # --------------------------------------------------

    for index, year in enumerate(YEARS, start=1):

        print(f"\n[{index}/{len(YEARS)}] Academic Year: {year}")

        teacher_path = find_year_file(
            year, "teacher", all_files
        )

        profile1_path = find_year_file(
            year, "profile1", all_files
        )

        profile2_path = find_year_file(
            year, "profile2", all_files
        )

        print(f"Teacher : {teacher_path.name}")
        print(f"Profile1: {profile1_path.name}")
        print(f"Profile2: {profile2_path.name}")

        # Read all three datasets.

        teacher = read_school_ids(
            teacher_path,
            year,
            "TEACHER"
        )

        profile1 = read_school_ids(
            profile1_path,
            year,
            "PROFILE1"
        )

        profile2 = read_school_ids(
            profile2_path,
            year,
            "PROFILE2"
        )

        # Individual dataset audits.

        for dataset in (
            teacher,
            profile1,
            profile2
        ):

            add_dataset_issues(
                dataset,
                all_details
            )

        # --------------------------------------------------
        # COMPARE TEACHER WITH PROFILE 1
        # --------------------------------------------------

        t_p1 = compare_datasets(
            year,
            teacher,
            profile1,
            "TEACHER_VS_PROFILE1",
            all_details
        )

        # --------------------------------------------------
        # COMPARE TEACHER WITH PROFILE 2
        # --------------------------------------------------

        t_p2 = compare_datasets(
            year,
            teacher,
            profile2,
            "TEACHER_VS_PROFILE2",
            all_details
        )

        # --------------------------------------------------
        # COMPARE PROFILE 1 WITH PROFILE 2
        # --------------------------------------------------

        p1_p2 = compare_datasets(
            year,
            profile1,
            profile2,
            "PROFILE1_VS_PROFILE2",
            all_details
        )

        # --------------------------------------------------
        # DETERMINE YEAR STATUS
        # --------------------------------------------------

        datasets = (
            teacher,
            profile1,
            profile2
        )

        has_missing = any(
            item["missing_ids"] > 0
            for item in datasets
        )

        has_duplicates = any(
            item["duplicate_id_count"] > 0
            for item in datasets
        )

        has_malformed = any(
            item["malformed_rows"] > 0
            for item in datasets
        )

        has_teacher_mismatch = (
            t_p1["left_only_unique_ids"] > 0
            or t_p2["left_only_unique_ids"] > 0
        )

        has_profile_mismatch = (
            p1_p2["left_only_unique_ids"] > 0
            or p1_p2["right_only_unique_ids"] > 0
        )

        if (
            has_missing
            or has_duplicates
            or has_malformed
            or has_teacher_mismatch
            or has_profile_mismatch
        ):

            status = "REVIEW_REQUIRED"

        else:

            status = "PASS"

        # --------------------------------------------------
        # SUMMARY RECORD
        # --------------------------------------------------

        summary = {

            "academic_year": year,

            "teacher_records": teacher["total_records"],
            "teacher_unique_ids": len(teacher["unique_ids"]),
            "teacher_missing_ids": teacher["missing_ids"],
            "teacher_duplicate_ids": teacher["duplicate_id_count"],

            "profile1_records": profile1["total_records"],
            "profile1_unique_ids": len(profile1["unique_ids"]),
            "profile1_missing_ids": profile1["missing_ids"],
            "profile1_duplicate_ids": profile1["duplicate_id_count"],

            "profile2_records": profile2["total_records"],
            "profile2_unique_ids": len(profile2["unique_ids"]),
            "profile2_missing_ids": profile2["missing_ids"],
            "profile2_duplicate_ids": profile2["duplicate_id_count"],

            "teacher_profile1_matched": t_p1["matched_unique_ids"],
            "teacher_ids_not_in_profile1": t_p1["left_only_unique_ids"],
            "profile1_ids_not_in_teacher": t_p1["right_only_unique_ids"],

            "teacher_profile2_matched": t_p2["matched_unique_ids"],
            "teacher_ids_not_in_profile2": t_p2["left_only_unique_ids"],
            "profile2_ids_not_in_teacher": t_p2["right_only_unique_ids"],

            "profile1_profile2_matched": p1_p2["matched_unique_ids"],
            "profile1_ids_not_in_profile2": p1_p2["left_only_unique_ids"],
            "profile2_ids_not_in_profile1": p1_p2["right_only_unique_ids"],

            "teacher_malformed_rows": teacher["malformed_rows"],
            "profile1_malformed_rows": profile1["malformed_rows"],
            "profile2_malformed_rows": profile2["malformed_rows"],

            "status": status,

        }

        summaries.append(summary)

        # --------------------------------------------------
        # PRINT YEAR RESULTS
        # --------------------------------------------------

        print(
            f"Teacher IDs: {len(teacher['unique_ids']):,}"
        )

        print(
            f"Profile 1 IDs: {len(profile1['unique_ids']):,}"
        )

        print(
            f"Profile 2 IDs: {len(profile2['unique_ids']):,}"
        )

        print(
            f"Teacher IDs not in Profile 1: "
            f"{t_p1['left_only_unique_ids']:,}"
        )

        print(
            f"Teacher IDs not in Profile 2: "
            f"{t_p2['left_only_unique_ids']:,}"
        )

        print(
            f"Profile 1 IDs not in Profile 2: "
            f"{p1_p2['left_only_unique_ids']:,}"
        )

        print(f"YEAR STATUS: {status}")

    # ==================================================
    # 12. SAVE SUMMARY REPORT
    # ==================================================

    summary_fields = list(summaries[0].keys())

    save_report(
        SUMMARY_REPORT,
        summaries,
        summary_fields
    )

    # ==================================================
    # 13. SAVE DETAIL REPORT
    # ==================================================

    detail_fields = [
        "academic_year",
        "comparison",
        "issue",
        "dataset",
        "school_id",
        "occurrences",
        "record_numbers",
    ]

    save_report(
        DETAIL_REPORT,
        all_details,
        detail_fields
    )

    # ==================================================
    # 14. FINAL SUMMARY
    # ==================================================

    passed = sum(
        row["status"] == "PASS"
        for row in summaries
    )

    review = sum(
        row["status"] == "REVIEW_REQUIRED"
        for row in summaries
    )

    print("\n" + "=" * 75)
    print("FINAL CROSS-VERIFICATION SUMMARY")
    print("=" * 75)

    print(f"Academic Years : {len(summaries)}")
    print(f"PASS           : {passed}")
    print(f"Review Required: {review}")

    print("\nREPORTS CREATED")

    print(SUMMARY_REPORT)
    print(DETAIL_REPORT)

    print("\nSCHOOL ID CROSS-VERIFICATION COMPLETED")


if __name__ == "__main__":
    main()

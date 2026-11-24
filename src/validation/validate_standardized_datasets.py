
"""
ShalaScope Maharashtra
Final Standardized Dataset Validation

Validates:
1. Profile 1, Profile 2 and Teacher datasets.
2. School ID uniqueness and completeness.
3. Exact School ID set matching.
4. District and district_raw consistency.
5. 36 standardized districts per year.

Does not modify any source or standardized data.
Python standard library only.
"""

from pathlib import Path
import csv
import re


# ==================================================
# 1. PATHS AND SETTINGS
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

BASE_DIR = ROOT / "data" / "interim" / "standardized"

PROFILE1_DIR = BASE_DIR / "profile1"
PROFILE2_DIR = BASE_DIR / "profile2"
TEACHER_DIR = BASE_DIR / "teacher"

REPORT_DIR = ROOT / "reports" / "data_audit"

SUMMARY_REPORT = (
    REPORT_DIR / "standardized_dataset_final_validation.csv"
)

DETAIL_REPORT = (
    REPORT_DIR / "standardized_dataset_validation_issues.csv"
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

ID_ALIASES = [
    "pseudocode",
    "psuedocode",
    "schoolid",
    "udiseid",
]

MAX_DETAIL_EXAMPLES = 500


# ==================================================
# 2. HELPERS
# ==================================================

def norm(value):
    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


def is_missing(value):
    return str(value or "").strip().lower() in MISSING_VALUES


def normalized_value(value):
    return str(value or "").strip().upper()


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


def find_id_field(fieldnames):

    normalized = {
        norm(name): name
        for name in fieldnames
        if name
    }

    for alias in ID_ALIASES:
        if alias in normalized:
            return normalized[alias]

    return None


def add_detail(
    details,
    year,
    dataset,
    issue,
    school_id="",
    record_number="",
    expected="",
    actual=""
):

    if len(details) >= MAX_DETAIL_EXAMPLES:
        return

    details.append({

        "academic_year": year,
        "dataset": dataset,
        "issue": issue,
        "school_id": school_id,
        "record_number": record_number,
        "expected_value": expected,
        "actual_value": actual,

    })


# ==================================================
# 3. GET FILE PATHS
# ==================================================

def get_dataset_paths(year):

    return {

        "PROFILE1": (
            PROFILE1_DIR
            / f"maharashtra_profile1_{year}_standardized.csv"
        ),

        "PROFILE2": (
            PROFILE2_DIR
            / f"maharashtra_profile2_{year}_standardized.csv"
        ),

        "TEACHER": (
            TEACHER_DIR
            / f"maharashtra_teacher_{year}_standardized.csv"
        ),

    }


# ==================================================
# 4. AUDIT ONE DATASET
# ==================================================

def audit_dataset(path, year, dataset_name, p1_mapping=None):

    if not path.exists():
        raise FileNotFoundError(path)

    handle, dialect = open_csv(path)

    ids = set()
    district_values = set()

    records = 0
    missing_ids = 0
    duplicate_ids = 0
    missing_districts = 0
    missing_raw_districts = 0
    malformed_rows = 0
    mapping_mismatches = 0
    unmatched_ids = 0

    local_mapping = {}
    details = []

    try:

        reader = csv.DictReader(
            handle,
            dialect=dialect
        )

        fieldnames = reader.fieldnames or []

        if not fieldnames:
            raise ValueError(
                f"Empty CSV header: {path}"
            )

        id_field = find_id_field(fieldnames)

        normalized_fields = {
            norm(name): name
            for name in fieldnames
            if name
        }

        district_field = normalized_fields.get("district")
        raw_field = normalized_fields.get("districtraw")

        if not id_field:
            raise ValueError(
                f"School ID column missing: {path.name}"
            )

        if not district_field or not raw_field:
            raise ValueError(
                f"District columns missing: {path.name}"
            )

        for record_number, row in enumerate(reader, start=2):

            if row is None:
                continue

            if None in row:
                malformed_rows += 1

                add_detail(
                    details,
                    year,
                    dataset_name,
                    "MALFORMED_ROW",
                    record_number=record_number
                )

            records += 1

            school_id = str(
                row.get(id_field) or ""
            ).strip()

            district = normalized_value(
                row.get(district_field)
            )

            raw_district = normalized_value(
                row.get(raw_field)
            )

            # Missing ID
            if is_missing(school_id):

                missing_ids += 1

                add_detail(
                    details,
                    year,
                    dataset_name,
                    "MISSING_SCHOOL_ID",
                    record_number=record_number
                )

                continue

            # Duplicate ID
            if school_id in ids:

                duplicate_ids += 1

                add_detail(
                    details,
                    year,
                    dataset_name,
                    "DUPLICATE_SCHOOL_ID",
                    school_id,
                    record_number
                )

            else:

                ids.add(school_id)

            # Missing district
            if is_missing(district):

                missing_districts += 1

                add_detail(
                    details,
                    year,
                    dataset_name,
                    "MISSING_DISTRICT",
                    school_id,
                    record_number
                )

            else:

                district_values.add(district)

            if is_missing(raw_district):

                missing_raw_districts += 1

                add_detail(
                    details,
                    year,
                    dataset_name,
                    "MISSING_DISTRICT_RAW",
                    school_id,
                    record_number
                )

            # Build Profile 1 lookup
            if dataset_name == "PROFILE1":

                if (
                    not is_missing(district)
                    and not is_missing(raw_district)
                    and school_id not in local_mapping
                ):

                    local_mapping[school_id] = (
                        district,
                        raw_district
                    )

            # Compare Profile 2 and Teacher with Profile 1
            elif p1_mapping is not None:

                if school_id not in p1_mapping:

                    unmatched_ids += 1

                    add_detail(
                        details,
                        year,
                        dataset_name,
                        "ID_NOT_FOUND_IN_PROFILE1",
                        school_id,
                        record_number
                    )

                    continue

                expected_district, expected_raw = (
                    p1_mapping[school_id]
                )

                if district != expected_district:

                    mapping_mismatches += 1

                    add_detail(
                        details,
                        year,
                        dataset_name,
                        "DISTRICT_MISMATCH",
                        school_id,
                        record_number,
                        expected_district,
                        district
                    )

                if raw_district != expected_raw:

                    mapping_mismatches += 1

                    add_detail(
                        details,
                        year,
                        dataset_name,
                        "DISTRICT_RAW_MISMATCH",
                        school_id,
                        record_number,
                        expected_raw,
                        raw_district
                    )

    finally:
        handle.close()

    result = {

        "dataset": dataset_name,
        "records": records,
        "unique_ids": len(ids),
        "missing_ids": missing_ids,
        "duplicate_ids": duplicate_ids,
        "unique_districts": len(district_values),
        "missing_districts": missing_districts,
        "missing_raw_districts": missing_raw_districts,
        "malformed_rows": malformed_rows,
        "unmatched_ids": unmatched_ids,
        "mapping_mismatches": mapping_mismatches,

    }

    return result, ids, local_mapping, details


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

    print("\nSHALASCOPE - FINAL STANDARDIZED DATASET VALIDATION")
    print("=" * 78)

    for folder in (
        PROFILE1_DIR,
        PROFILE2_DIR,
        TEACHER_DIR,
    ):

        if not folder.exists():
            raise FileNotFoundError(folder)

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    summaries = []
    all_details = []

    total_all_records = 0

    for index, year in enumerate(YEARS, 1):

        print(
            f"\n[{index}/{len(YEARS)}] Academic Year: {year}"
        )

        paths = get_dataset_paths(year)

        # ------------------------------------------
        # PROFILE 1
        # ------------------------------------------

        p1, p1_ids, p1_mapping, p1_details = audit_dataset(
            paths["PROFILE1"],
            year,
            "PROFILE1"
        )

        all_details.extend(p1_details)

        # ------------------------------------------
        # PROFILE 2
        # ------------------------------------------

        p2, p2_ids, _, p2_details = audit_dataset(
            paths["PROFILE2"],
            year,
            "PROFILE2",
            p1_mapping
        )

        all_details.extend(p2_details)

        # ------------------------------------------
        # TEACHER
        # ------------------------------------------

        teacher, teacher_ids, _, teacher_details = audit_dataset(
            paths["TEACHER"],
            year,
            "TEACHER",
            p1_mapping
        )

        all_details.extend(teacher_details)

        # ------------------------------------------
        # CROSS DATASET ID MATCHING
        # ------------------------------------------

        p2_not_in_p1 = len(p2_ids - p1_ids)
        p1_not_in_p2 = len(p1_ids - p2_ids)

        teacher_not_in_p1 = len(teacher_ids - p1_ids)
        p1_not_in_teacher = len(p1_ids - teacher_ids)

        p2_not_in_teacher = len(p2_ids - teacher_ids)
        teacher_not_in_p2 = len(teacher_ids - p2_ids)

        id_sets_match = (
            p1_ids == p2_ids == teacher_ids
        )

        if not id_sets_match:

            for label, values in [
                ("PROFILE2_ID_NOT_IN_PROFILE1", p2_ids - p1_ids),
                ("PROFILE1_ID_NOT_IN_PROFILE2", p1_ids - p2_ids),
                ("TEACHER_ID_NOT_IN_PROFILE1", teacher_ids - p1_ids),
                ("PROFILE1_ID_NOT_IN_TEACHER", p1_ids - teacher_ids),
            ]:

                for school_id in sorted(values)[:100]:

                    add_detail(
                        all_details,
                        year,
                        "CROSS_DATASET",
                        label,
                        school_id
                    )

        datasets = [p1, p2, teacher]

        dataset_checks_pass = all(

            item["missing_ids"] == 0
            and item["duplicate_ids"] == 0
            and item["unique_districts"] == 36
            and item["missing_districts"] == 0
            and item["missing_raw_districts"] == 0
            and item["malformed_rows"] == 0
            and item["unmatched_ids"] == 0
            and item["mapping_mismatches"] == 0
            and item["records"] == item["unique_ids"]

            for item in datasets

        )

        record_counts_match = (
            p1["records"] == p2["records"] == teacher["records"]
        )

        status = (
            "PASS"
            if (
                dataset_checks_pass
                and id_sets_match
                and record_counts_match
            )
            else "REVIEW_REQUIRED"
        )

        summary = {

            "academic_year": year,

            "profile1_records": p1["records"],
            "profile2_records": p2["records"],
            "teacher_records": teacher["records"],

            "profile1_unique_ids": p1["unique_ids"],
            "profile2_unique_ids": p2["unique_ids"],
            "teacher_unique_ids": teacher["unique_ids"],

            "profile1_districts": p1["unique_districts"],
            "profile2_districts": p2["unique_districts"],
            "teacher_districts": teacher["unique_districts"],

            "profile2_ids_not_in_profile1": p2_not_in_p1,
            "profile1_ids_not_in_profile2": p1_not_in_p2,

            "teacher_ids_not_in_profile1": teacher_not_in_p1,
            "profile1_ids_not_in_teacher": p1_not_in_teacher,

            "profile2_ids_not_in_teacher": p2_not_in_teacher,
            "teacher_ids_not_in_profile2": teacher_not_in_p2,

            "missing_ids": (
                p1["missing_ids"]
                + p2["missing_ids"]
                + teacher["missing_ids"]
            ),

            "duplicate_ids": (
                p1["duplicate_ids"]
                + p2["duplicate_ids"]
                + teacher["duplicate_ids"]
            ),

            "missing_districts": (
                p1["missing_districts"]
                + p2["missing_districts"]
                + teacher["missing_districts"]
            ),

            "missing_raw_districts": (
                p1["missing_raw_districts"]
                + p2["missing_raw_districts"]
                + teacher["missing_raw_districts"]
            ),

            "mapping_mismatches": (
                p2["mapping_mismatches"]
                + teacher["mapping_mismatches"]
            ),

            "malformed_rows": (
                p1["malformed_rows"]
                + p2["malformed_rows"]
                + teacher["malformed_rows"]
            ),

            "id_sets_match": id_sets_match,
            "record_counts_match": record_counts_match,
            "status": status,

        }

        summaries.append(summary)

        total_all_records += (
            p1["records"]
            + p2["records"]
            + teacher["records"]
        )

        print(
            f"Profile 1: {p1['records']:,} records | "
            f"{p1['unique_districts']} districts"
        )

        print(
            f"Profile 2: {p2['records']:,} records | "
            f"{p2['unique_districts']} districts"
        )

        print(
            f"Teacher: {teacher['records']:,} records | "
            f"{teacher['unique_districts']} districts"
        )

        print(f"ID Sets Match: {id_sets_match}")
        print(f"Record Counts Match: {record_counts_match}")

        print(
            f"Missing IDs: {summary['missing_ids']}"
        )

        print(
            f"Duplicate IDs: {summary['duplicate_ids']}"
        )

        print(
            f"District Mapping Mismatches: "
            f"{summary['mapping_mismatches']}"
        )

        print(f"STATUS: {status}")

    # ==================================================
    # 7. SAVE FINAL REPORTS
    # ==================================================

    summary_fields = list(summaries[0].keys())

    save_report(
        SUMMARY_REPORT,
        summaries,
        summary_fields
    )

    detail_fields = [
        "academic_year",
        "dataset",
        "issue",
        "school_id",
        "record_number",
        "expected_value",
        "actual_value",
    ]

    save_report(
        DETAIL_REPORT,
        all_details,
        detail_fields
    )

    # ==================================================
    # 8. FINAL SUMMARY
    # ==================================================

    passed = sum(
        row["status"] == "PASS"
        for row in summaries
    )

    review = sum(
        row["status"] == "REVIEW_REQUIRED"
        for row in summaries
    )

    print("\n" + "=" * 78)
    print("FINAL STANDARDIZED DATASET VALIDATION")
    print("=" * 78)

    print(f"Academic Years: {len(summaries)}")
    print(f"Total Records Across 3 Datasets: {total_all_records:,}")
    print(f"PASS: {passed}")
    print(f"Review Required: {review}")

    print("\nREPORTS CREATED")
    print(SUMMARY_REPORT)
    print(DETAIL_REPORT)

    print("\nFINAL DATASET VALIDATION COMPLETED")


if __name__ == "__main__":
    main()

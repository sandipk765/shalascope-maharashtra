
"""
ShalaScope Maharashtra
Teacher District Standardization

Academic years: 2018-19 to 2025-26

Features:
1. Reads standardized Profile 1 data.
2. Creates School ID -> District mapping.
3. Matches every Teacher School ID.
4. Adds district and district_raw columns.
5. Preserves all original Teacher columns.
6. Validates missing and duplicate IDs.
7. Validates exact ID set matching.
8. Saves output only when all checks pass.
9. Never modifies original CSV files.

Python standard library only.
"""

from pathlib import Path
import csv
import re


# ==================================================
# 1. PROJECT PATHS
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

EXTRACT_ROOT = ROOT / "data" / "extracted"

PROFILE1_DIR = (
    ROOT
    / "data"
    / "interim"
    / "standardized"
    / "profile1"
)

OUTPUT_DIR = (
    ROOT
    / "data"
    / "interim"
    / "standardized"
    / "teacher"
)

REPORT_DIR = ROOT / "reports" / "data_audit"

AUDIT_REPORT = (
    REPORT_DIR
    / "teacher_district_standardization_audit.csv"
)

DETAIL_REPORT = (
    REPORT_DIR
    / "teacher_district_standardization_details.csv"
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
# 3. FIND SCHOOL ID COLUMN
# ==================================================

def find_id_column(headers):

    normalized = {
        norm(header): index
        for index, header in enumerate(headers)
    }

    for alias in ID_ALIASES:

        if alias in normalized:

            index = normalized[alias]

            return index, headers[index]

    return None, None


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
        f"Could not decode CSV: {path}. {last_error}"
    )


# ==================================================
# 5. FIND SOURCE TEACHER FILE
# ==================================================

def find_teacher_file(year):

    pattern = re.compile(
        r"(^|[_-])tch\.csv$",
        re.IGNORECASE
    )

    matches = [

        path
        for path in EXTRACT_ROOT.rglob("*.csv")
        if year in path.parts and pattern.search(path.name)

    ]

    if len(matches) != 1:

        raise RuntimeError(
            f"{year}: Expected exactly one Teacher CSV, "
            f"found {len(matches)}."
        )

    return matches[0]


# ==================================================
# 6. FIND STANDARDIZED PROFILE 1 FILE
# ==================================================

def find_profile1_file(year):

    path = (
        PROFILE1_DIR
        / f"maharashtra_profile1_{year}_standardized.csv"
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Standardized Profile 1 not found: {path}"
        )

    return path


# ==================================================
# 7. LOAD PROFILE 1 SCHOOL ID MAPPING
# ==================================================

def load_profile1_mapping(path):

    handle, dialect = open_csv(path)

    school_mapping = {}

    total_records = 0
    missing_ids = 0
    duplicate_ids = 0
    missing_districts = 0
    malformed_rows = 0

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        if not headers:
            raise ValueError("Profile 1 header is empty.")

        id_index, id_column = find_id_column(headers)

        normalized_headers = [
            norm(header)
            for header in headers
        ]

        district_index = next(
            (
                i
                for i, name in enumerate(normalized_headers)
                if name == "district"
            ),
            None
        )

        raw_index = next(
            (
                i
                for i, name in enumerate(normalized_headers)
                if name == "districtraw"
            ),
            None
        )

        if id_index is None:
            raise ValueError("Profile 1 School ID column missing.")

        if district_index is None:
            raise ValueError("Profile 1 district column missing.")

        if raw_index is None:
            raise ValueError("Profile 1 district_raw column missing.")

        for record_number, row in enumerate(reader, start=2):

            if not row or all(
                not str(value).strip()
                for value in row
            ):
                continue

            total_records += 1

            if len(row) != len(headers):

                malformed_rows += 1
                continue

            school_id = str(row[id_index]).strip()

            district = str(
                row[district_index]
            ).strip()

            district_raw = str(
                row[raw_index]
            ).strip()

            if school_id.lower() in MISSING_VALUES:

                missing_ids += 1
                continue

            if not district:

                missing_districts += 1
                continue

            if school_id in school_mapping:

                duplicate_ids += 1
                continue

            school_mapping[school_id] = {

                "district": district,
                "district_raw": district_raw,

            }

    finally:

        handle.close()

    if (
        missing_ids > 0
        or duplicate_ids > 0
        or missing_districts > 0
        or malformed_rows > 0
    ):

        raise ValueError(
            "Profile 1 integrity check failed: "
            f"Missing IDs={missing_ids}, "
            f"Duplicate IDs={duplicate_ids}, "
            f"Missing Districts={missing_districts}, "
            f"Malformed Rows={malformed_rows}"
        )

    return school_mapping, total_records


# ==================================================
# 8. STANDARD OUTPUT CSV WRITER
# ==================================================

def create_output_writer(file):

    return csv.writer(
        file,
        delimiter=",",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        doublequote=True,
        lineterminator="\n"
    )


# ==================================================
# 9. STANDARDIZE TEACHER DATA
# ==================================================

def standardize_teacher_file(
    year,
    teacher_path,
    profile1_path
):

    # ------------------------------------------
    # LOAD PROFILE 1 MAPPING
    # ------------------------------------------

    school_mapping, profile1_records = (
        load_profile1_mapping(profile1_path)
    )

    profile1_ids = set(school_mapping.keys())

    # ------------------------------------------
    # OUTPUT PATH
    # ------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        OUTPUT_DIR
        / f"maharashtra_teacher_{year}_standardized.csv"
    )

    temp_path = output_path.with_suffix(".tmp")

    if temp_path.exists():
        temp_path.unlink()

    # ------------------------------------------
    # AUDIT COUNTERS
    # ------------------------------------------

    teacher_records = 0

    teacher_ids = set()

    missing_ids = 0
    duplicate_ids = 0
    unmatched_ids = 0
    malformed_rows = 0

    missing_district_matches = 0

    details = []

    handle, dialect = open_csv(teacher_path)

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        if not headers:

            raise ValueError(
                "Teacher CSV header is empty."
            )

        id_index, id_column = find_id_column(headers)

        if id_index is None:

            raise ValueError(
                "Teacher School ID column not found."
            )

        normalized_headers = [
            norm(header)
            for header in headers
        ]

        if (
            "district" in normalized_headers
            or "districtraw" in normalized_headers
        ):

            raise ValueError(
                "Teacher source already contains district columns. "
                "Review its schema before proceeding."
            )

        output_headers = (
            headers
            + ["district", "district_raw"]
        )

        with temp_path.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as output_file:

            writer = create_output_writer(output_file)

            writer.writerow(output_headers)

            for record_number, row in enumerate(reader, start=2):

                if not row or all(
                    not str(value).strip()
                    for value in row
                ):
                    continue

                teacher_records += 1

                if len(row) != len(headers):

                    malformed_rows += 1

                    details.append({

                        "academic_year": year,
                        "issue": "MALFORMED_ROW",
                        "school_id": "",
                        "record_number": record_number,

                    })

                    continue

                school_id = str(
                    row[id_index]
                ).strip()

                # ----------------------------------
                # MISSING SCHOOL ID
                # ----------------------------------

                if school_id.lower() in MISSING_VALUES:

                    missing_ids += 1

                    details.append({

                        "academic_year": year,
                        "issue": "MISSING_SCHOOL_ID",
                        "school_id": "",
                        "record_number": record_number,

                    })

                    continue

                # ----------------------------------
                # DUPLICATE SCHOOL ID
                # ----------------------------------

                if school_id in teacher_ids:

                    duplicate_ids += 1

                    details.append({

                        "academic_year": year,
                        "issue": "DUPLICATE_SCHOOL_ID",
                        "school_id": school_id,
                        "record_number": record_number,

                    })

                teacher_ids.add(school_id)

                # ----------------------------------
                # MATCH WITH PROFILE 1
                # ----------------------------------

                if school_id not in school_mapping:

                    unmatched_ids += 1

                    details.append({

                        "academic_year": year,
                        "issue": "ID_NOT_FOUND_IN_PROFILE1",
                        "school_id": school_id,
                        "record_number": record_number,

                    })

                    row.extend(["", ""])

                else:

                    district_data = school_mapping[school_id]

                    district = district_data["district"]

                    district_raw = district_data["district_raw"]

                    if not district:

                        missing_district_matches += 1

                    row.extend([
                        district,
                        district_raw,
                    ])

                writer.writerow(row)

        # ------------------------------------------
        # FIND PROFILE 1 IDS NOT IN TEACHER
        # ------------------------------------------

        profile1_missing_in_teacher = (
            profile1_ids - teacher_ids
        )

        for school_id in sorted(profile1_missing_in_teacher):

            details.append({

                "academic_year": year,
                "issue": "PROFILE1_ID_NOT_FOUND_IN_TEACHER",
                "school_id": school_id,
                "record_number": "",

            })

    except Exception:

        if temp_path.exists():
            temp_path.unlink()

        raise

    finally:

        handle.close()

    # ==================================================
    # 10. VALIDATE SCHOOL ID SETS
    # ==================================================

    teacher_unique_ids = len(teacher_ids)

    id_sets_match = (
        profile1_ids == teacher_ids
    )

    profile1_ids_not_in_teacher = len(
        profile1_ids - teacher_ids
    )

    if (
        id_sets_match
        and missing_ids == 0
        and duplicate_ids == 0
        and unmatched_ids == 0
        and malformed_rows == 0
        and missing_district_matches == 0
        and teacher_records == teacher_unique_ids
    ):

        status = "PASS"

        temp_path.replace(output_path)

        output_name = str(
            output_path.relative_to(ROOT)
        )

    else:

        status = "REVIEW_REQUIRED"

        if temp_path.exists():
            temp_path.unlink()

        output_name = ""

    result = {

        "academic_year": year,

        "profile1_records": profile1_records,
        "profile1_unique_ids": len(profile1_ids),

        "teacher_records": teacher_records,
        "teacher_unique_ids": teacher_unique_ids,

        "missing_teacher_ids": missing_ids,
        "duplicate_teacher_ids": duplicate_ids,

        "teacher_ids_not_in_profile1": unmatched_ids,

        "profile1_ids_not_in_teacher": (
            profile1_ids_not_in_teacher
        ),

        "missing_district_matches": (
            missing_district_matches
        ),

        "malformed_rows": malformed_rows,

        "id_sets_match": id_sets_match,

        "output_file": output_name,
        "status": status,

    }

    return result, details


# ==================================================
# 11. SAVE REPORT
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
# 12. MAIN PROGRAM
# ==================================================

def main():

    print("\nSHALASCOPE - TEACHER DISTRICT STANDARDIZATION")
    print("=" * 75)

    if not EXTRACT_ROOT.exists():

        raise FileNotFoundError(
            f"Extracted folder not found: {EXTRACT_ROOT}"
        )

    if not PROFILE1_DIR.exists():

        raise FileNotFoundError(
            f"Standardized Profile 1 folder not found: {PROFILE1_DIR}"
        )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    summaries = []
    all_details = []

    # ------------------------------------------
    # PROCESS ALL EIGHT YEARS
    # ------------------------------------------

    for index, year in enumerate(YEARS, 1):

        print(
            f"\n[{index}/{len(YEARS)}] Academic Year: {year}"
        )

        try:

            profile1_path = find_profile1_file(year)

            teacher_path = find_teacher_file(year)

            print(
                f"Profile 1: {profile1_path.name}"
            )

            print(
                f"Teacher: {teacher_path.name}"
            )

            result, details = standardize_teacher_file(
                year,
                teacher_path,
                profile1_path
            )

            summaries.append(result)

            all_details.extend(details)

            print(
                f"Profile 1 Records: "
                f"{result['profile1_records']:,}"
            )

            print(
                f"Teacher Records: "
                f"{result['teacher_records']:,}"
            )

            print(
                f"Unique Teacher IDs: "
                f"{result['teacher_unique_ids']:,}"
            )

            print(
                f"Missing IDs: "
                f"{result['missing_teacher_ids']}"
            )

            print(
                f"Duplicate IDs: "
                f"{result['duplicate_teacher_ids']}"
            )

            print(
                f"Teacher IDs not in Profile 1: "
                f"{result['teacher_ids_not_in_profile1']}"
            )

            print(
                f"Profile 1 IDs not in Teacher: "
                f"{result['profile1_ids_not_in_teacher']}"
            )

            print(
                f"Missing District Matches: "
                f"{result['missing_district_matches']}"
            )

            print(
                f"ID Sets Match: "
                f"{result['id_sets_match']}"
            )

            print(
                f"STATUS: {result['status']}"
            )

            if result["output_file"]:

                print(
                    f"Output: {result['output_file']}"
                )

        except Exception as error:

            print(f"ERROR: {error}")

            summaries.append({

                "academic_year": year,

                "profile1_records": 0,
                "profile1_unique_ids": 0,

                "teacher_records": 0,
                "teacher_unique_ids": 0,

                "missing_teacher_ids": 0,
                "duplicate_teacher_ids": 0,

                "teacher_ids_not_in_profile1": 0,
                "profile1_ids_not_in_teacher": 0,

                "missing_district_matches": 0,
                "malformed_rows": 0,

                "id_sets_match": False,

                "output_file": "",
                "status": "FAILED",

            })

            all_details.append({

                "academic_year": year,
                "issue": "FILE_PROCESSING_FAILED",
                "school_id": "",
                "record_number": str(error),

            })

    # ==================================================
    # 13. SAVE SUMMARY REPORT
    # ==================================================

    summary_fields = [

        "academic_year",

        "profile1_records",
        "profile1_unique_ids",

        "teacher_records",
        "teacher_unique_ids",

        "missing_teacher_ids",
        "duplicate_teacher_ids",

        "teacher_ids_not_in_profile1",
        "profile1_ids_not_in_teacher",

        "missing_district_matches",
        "malformed_rows",

        "id_sets_match",

        "output_file",
        "status",

    ]

    save_report(
        AUDIT_REPORT,
        summaries,
        summary_fields
    )

    # ==================================================
    # 14. SAVE DETAIL REPORT
    # ==================================================

    detail_fields = [

        "academic_year",
        "issue",
        "school_id",
        "record_number",

    ]

    save_report(
        DETAIL_REPORT,
        all_details,
        detail_fields
    )

    # ==================================================
    # 15. FINAL SUMMARY
    # ==================================================

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
        row["teacher_records"]
        for row in summaries
    )

    print("\n" + "=" * 75)
    print("FINAL TEACHER DISTRICT STANDARDIZATION SUMMARY")
    print("=" * 75)

    print(f"Academic Years: {len(summaries)}")

    print(
        f"Total Teacher Records: {total_records:,}"
    )

    print(f"PASS: {passed}")
    print(f"Review Required: {review}")
    print(f"Failed: {failed}")

    print("\nREPORTS CREATED")

    print(AUDIT_REPORT)
    print(DETAIL_REPORT)

    print("\nSTANDARDIZED OUTPUT FOLDER")
    print(OUTPUT_DIR)

    print("\nTEACHER DISTRICT STANDARDIZATION COMPLETED")


if __name__ == "__main__":
    main()

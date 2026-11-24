
"""
ShalaScope Maharashtra
Profile 2 District Standardization

Academic years: 2018-19 to 2025-26

Method:
1. Read standardized Profile 1 data.
2. Build School ID -> District mapping.
3. Read original Profile 2 data.
4. Match using pseudocode / psuedocode.
5. Append district and district_raw.
6. Validate exact School ID matching.
7. Save standardized Profile 2 only when validation passes.

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
    / "profile2"
)

REPORT_DIR = ROOT / "reports" / "data_audit"

AUDIT_REPORT = (
    REPORT_DIR
    / "profile2_district_standardization_audit.csv"
)

DETAIL_REPORT = (
    REPORT_DIR
    / "profile2_district_standardization_details.csv"
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
# 4. OPEN SOURCE CSV
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
# 5. FIND SOURCE PROFILE 2 FILE
# ==================================================

def find_profile2_file(year):

    matches = [

        path
        for path in EXTRACT_ROOT.rglob("*prof2.csv")
        if year in path.parts

    ]

    if len(matches) != 1:

        raise RuntimeError(
            f"{year}: Expected one Profile 2 CSV, "
            f"found {len(matches)}."
        )

    return matches[0]


# ==================================================
# 6. FIND STANDARDIZED PROFILE 1 FILE
# ==================================================

def find_standardized_profile1(year):

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
# 7. LOAD SCHOOL ID TO DISTRICT MAPPING
# ==================================================

def load_profile1_mapping(path):

    handle, dialect = open_csv(path)

    school_mapping = {}

    total_records = 0
    duplicate_ids = 0
    missing_ids = 0
    missing_districts = 0
    malformed_rows = 0

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        if not headers:

            raise ValueError(
                f"Empty Profile 1 file: {path}"
            )

        id_index, id_column = find_id_column(headers)

        normalized_headers = [
            norm(header)
            for header in headers
        ]

        district_index = next(
            (
                i for i, name in enumerate(normalized_headers)
                if name == "district"
            ),
            None
        )

        raw_district_index = next(
            (
                i for i, name in enumerate(normalized_headers)
                if name == "districtraw"
            ),
            None
        )

        if id_index is None:

            raise ValueError(
                "School ID column not found in Profile 1."
            )

        if district_index is None:

            raise ValueError(
                "Standardized district column not found."
            )

        if raw_district_index is None:

            raise ValueError(
                "district_raw column not found."
            )

        for row in reader:

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
                row[raw_district_index]
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
        duplicate_ids > 0
        or missing_ids > 0
        or missing_districts > 0
        or malformed_rows > 0
    ):

        raise ValueError(
            "Profile 1 integrity check failed. "
            f"Duplicate IDs={duplicate_ids}, "
            f"Missing IDs={missing_ids}, "
            f"Missing Districts={missing_districts}, "
            f"Malformed Rows={malformed_rows}"
        )

    return school_mapping, total_records, id_column


# ==================================================
# 8. CREATE STANDARD OUTPUT WRITER
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
# 9. STANDARDIZE ONE PROFILE 2 FILE
# ==================================================

def standardize_file(year, profile1_path, profile2_path):

    # ------------------------------------------
    # LOAD PROFILE 1 DISTRICT MAPPING
    # ------------------------------------------

    school_mapping, p1_records, p1_id_column = (
        load_profile1_mapping(profile1_path)
    )

    p1_ids = set(school_mapping.keys())

    # ------------------------------------------
    # OUTPUT PATHS
    # ------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        OUTPUT_DIR
        / f"maharashtra_profile2_{year}_standardized.csv"
    )

    temp_path = output_path.with_suffix(".tmp")

    # ------------------------------------------
    # AUDIT COUNTERS
    # ------------------------------------------

    p2_records = 0

    p2_ids = set()

    missing_ids = 0
    duplicate_ids = 0
    unmatched_ids = 0
    malformed_rows = 0

    missing_district_matches = 0

    details = []

    handle, dialect = open_csv(profile2_path)

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        if not headers:

            raise ValueError(
                f"Empty Profile 2 file: {profile2_path}"
            )

        id_index, id_column = find_id_column(headers)

        if id_index is None:

            raise ValueError(
                "School ID column not found in Profile 2."
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
                "Source Profile 2 already contains district fields. "
                "Review schema before proceeding."
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

                p2_records += 1

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

                if school_id.lower() in MISSING_VALUES:

                    missing_ids += 1

                    details.append({
                        "academic_year": year,
                        "issue": "MISSING_SCHOOL_ID",
                        "school_id": "",
                        "record_number": record_number,
                    })

                    row.extend(["", ""])
                    writer.writerow(row)
                    continue

                if school_id in p2_ids:

                    duplicate_ids += 1

                    details.append({
                        "academic_year": year,
                        "issue": "DUPLICATE_SCHOOL_ID",
                        "school_id": school_id,
                        "record_number": record_number,
                    })

                p2_ids.add(school_id)

                # ----------------------------------
                # MATCH SCHOOL ID WITH PROFILE 1
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
        # IDENTIFY PROFILE 1 IDS MISSING IN PROFILE 2
        # ------------------------------------------

        p1_ids_not_in_p2 = p1_ids - p2_ids

        for school_id in sorted(p1_ids_not_in_p2):

            details.append({
                "academic_year": year,
                "issue": "PROFILE1_ID_NOT_FOUND_IN_PROFILE2",
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
    # 10. FINAL SET VALIDATION
    # ==================================================

    p2_unique_ids = len(p2_ids)

    id_set_match = p1_ids == p2_ids

    if (
        id_set_match
        and missing_ids == 0
        and duplicate_ids == 0
        and unmatched_ids == 0
        and malformed_rows == 0
        and missing_district_matches == 0
        and p2_records == p2_unique_ids
    ):

        status = "PASS"

        # Save only successfully validated output.
        temp_path.replace(output_path)

        output_name = str(
            output_path.relative_to(ROOT)
        )

    else:

        status = "REVIEW_REQUIRED"

        # Never keep an incomplete output as final.
        if temp_path.exists():
            temp_path.unlink()

        output_name = ""

    result = {

        "academic_year": year,

        "profile1_file": profile1_path.name,
        "profile2_file": profile2_path.name,

        "profile1_records": p1_records,
        "profile1_unique_ids": len(p1_ids),

        "profile2_records": p2_records,
        "profile2_unique_ids": p2_unique_ids,

        "missing_profile2_ids": missing_ids,
        "duplicate_profile2_ids": duplicate_ids,

        "profile2_ids_not_in_profile1": unmatched_ids,

        "profile1_ids_not_in_profile2": len(
            p1_ids_not_in_p2
        ),

        "missing_district_matches": missing_district_matches,
        "malformed_rows": malformed_rows,

        "id_sets_match": id_set_match,
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

    print("\nSHALASCOPE - PROFILE 2 DISTRICT STANDARDIZATION")
    print("=" * 75)

    if not EXTRACT_ROOT.exists():

        raise FileNotFoundError(
            f"Extracted data folder not found: {EXTRACT_ROOT}"
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

    # --------------------------------------------------
    # PROCESS ALL EIGHT YEARS
    # --------------------------------------------------

    for index, year in enumerate(YEARS, 1):

        print(
            f"\n[{index}/{len(YEARS)}] Academic Year: {year}"
        )

        try:

            profile1_path = find_standardized_profile1(year)

            profile2_path = find_profile2_file(year)

            print(
                f"Profile 1: {profile1_path.name}"
            )

            print(
                f"Profile 2: {profile2_path.name}"
            )

            result, details = standardize_file(
                year,
                profile1_path,
                profile2_path
            )

            summaries.append(result)

            all_details.extend(details)

            print(
                f"Profile 1 Records: "
                f"{result['profile1_records']:,}"
            )

            print(
                f"Profile 2 Records: "
                f"{result['profile2_records']:,}"
            )

            print(
                f"Unique Profile 2 IDs: "
                f"{result['profile2_unique_ids']:,}"
            )

            print(
                f"Missing IDs: "
                f"{result['missing_profile2_ids']}"
            )

            print(
                f"Duplicate IDs: "
                f"{result['duplicate_profile2_ids']}"
            )

            print(
                f"IDs not in Profile 1: "
                f"{result['profile2_ids_not_in_profile1']}"
            )

            print(
                f"Profile 1 IDs not in Profile 2: "
                f"{result['profile1_ids_not_in_profile2']}"
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
                "profile1_file": "",
                "profile2_file": "",
                "profile1_records": 0,
                "profile1_unique_ids": 0,
                "profile2_records": 0,
                "profile2_unique_ids": 0,
                "missing_profile2_ids": 0,
                "duplicate_profile2_ids": 0,
                "profile2_ids_not_in_profile1": 0,
                "profile1_ids_not_in_profile2": 0,
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
    # 13. SAVE AUDIT SUMMARY
    # ==================================================

    summary_fields = [

        "academic_year",
        "profile1_file",
        "profile2_file",
        "profile1_records",
        "profile1_unique_ids",
        "profile2_records",
        "profile2_unique_ids",
        "missing_profile2_ids",
        "duplicate_profile2_ids",
        "profile2_ids_not_in_profile1",
        "profile1_ids_not_in_profile2",
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
        row["profile2_records"]
        for row in summaries
    )

    print("\n" + "=" * 75)
    print("FINAL PROFILE 2 STANDARDIZATION SUMMARY")
    print("=" * 75)

    print(f"Academic Years: {len(summaries)}")
    print(f"Total Profile 2 Records: {total_records:,}")
    print(f"PASS: {passed}")
    print(f"Review Required: {review}")
    print(f"Failed: {failed}")

    print("\nREPORTS CREATED")

    print(AUDIT_REPORT)
    print(DETAIL_REPORT)

    print("\nSTANDARDIZED OUTPUT FOLDER")
    print(OUTPUT_DIR)

    print("\nPROFILE 2 STANDARDIZATION COMPLETED")


if __name__ == "__main__":
    main()


"""
ShalaScope Maharashtra
Profile 1 District Standardization

Academic years: 2018-19 to 2025-26

Features:
1. Reads the reviewed district mapping report.
2. Standardizes district names in Profile 1 CSV files.
3. Preserves original district values in district_raw.
4. Keeps all original Profile 1 columns.
5. Creates new standardized copies.
6. Validates 36 districts per year.
7. Never modifies original CSV files.

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

MAPPING_FILE = (
    ROOT
    / "reports"
    / "data_audit"
    / "district_name_mapping_review.csv"
)

OUTPUT_DIR = (
    ROOT
    / "data"
    / "interim"
    / "standardized"
    / "profile1"
)

REPORT_DIR = ROOT / "reports" / "data_audit"

AUDIT_REPORT = (
    REPORT_DIR
    / "profile1_district_standardization_audit.csv"
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
# 3. LOAD REVIEWED DISTRICT MAPPING
# ==================================================

def load_district_mapping():

    if not MAPPING_FILE.exists():

        raise FileNotFoundError(
            f"Mapping report not found: {MAPPING_FILE}"
        )

    mapping = {}

    with MAPPING_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "raw_district_name",
            "proposed_standard_district",
        }

        if not required_columns.issubset(
            set(reader.fieldnames or [])
        ):

            raise ValueError(
                "Required columns missing in district mapping report."
            )

        for row in reader:

            raw_name = (
                row["raw_district_name"] or ""
            ).strip().upper()

            standard_name = (
                row["proposed_standard_district"] or ""
            ).strip().upper()

            if not raw_name or not standard_name:

                raise ValueError(
                    f"Invalid mapping row: {row}"
                )

            if raw_name in mapping:

                raise ValueError(
                    f"Duplicate mapping found: {raw_name}"
                )

            mapping[raw_name] = standard_name

    print(
        f"District mapping records loaded: {len(mapping)}"
    )

    return mapping


# ==================================================
# 4. FIND PROFILE 1 FILE
# ==================================================

def find_profile1_file(year):

    matches = [

        path
        for path in EXTRACT_ROOT.rglob("*prof1.csv")
        if year in path.parts

    ]

    if len(matches) != 1:

        raise RuntimeError(
            f"{year}: Expected 1 Profile 1 CSV, "
            f"found {len(matches)}."
        )

    return matches[0]


# ==================================================
# 5. OPEN SOURCE CSV
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
        f"Cannot decode CSV: {path}. {last_error}"
    )


# ==================================================
# 6. CREATE STANDARD OUTPUT CSV WRITER
# ==================================================

def create_output_writer(output_file):

    """
    Always write output using a standard CSV format.

    Do not reuse the source dialect here.
    This avoids:
    _csv.Error: need to escape, but no escapechar set
    """

    return csv.writer(
        output_file,
        delimiter=",",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        doublequote=True,
        lineterminator="\n"
    )


# ==================================================
# 7. STANDARDIZE ONE PROFILE 1 FILE
# ==================================================

def standardize_file(path, year, mapping):

    handle, dialect = open_csv(path)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        OUTPUT_DIR
        / f"maharashtra_profile1_{year}_standardized.csv"
    )

    temp_path = output_path.with_suffix(".tmp")

    total_records = 0
    missing_districts = 0
    changed_rows = 0
    malformed_rows = 0

    raw_districts = set()
    standard_districts = set()

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        if not headers:

            raise ValueError(
                f"Empty CSV header: {path}"
            )

        normalized_headers = [
            norm(header)
            for header in headers
        ]

        district_index = next(
            (
                index
                for index, name in enumerate(normalized_headers)
                if name == "district"
            ),
            None
        )

        if district_index is None:

            raise ValueError(
                f"District column not found: {path.name}"
            )

        if "districtraw" in normalized_headers:

            raise ValueError(
                "Source already contains district_raw column. "
                "Review the input schema before proceeding."
            )

        # Preserve original district as district_raw.
        output_headers = headers + ["district_raw"]

        with temp_path.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as output_file:

            # FIX: Use standard writer, not source dialect.
            writer = create_output_writer(output_file)

            writer.writerow(output_headers)

            for row in reader:

                if not row or all(
                    not str(value).strip()
                    for value in row
                ):
                    continue

                if len(row) != len(headers):

                    malformed_rows += 1

                    raise ValueError(
                        f"Malformed row in {path.name}: "
                        f"record {total_records + 2}; "
                        f"expected {len(headers)} columns, "
                        f"found {len(row)}."
                    )

                total_records += 1

                # ------------------------------------------
                # ORIGINAL DISTRICT VALUE
                # ------------------------------------------

                original_district = (
                    str(row[district_index]).strip()
                )

                raw_key = original_district.upper()

                # ------------------------------------------
                # HANDLE MISSING DISTRICT
                # ------------------------------------------

                if raw_key.lower() in MISSING_VALUES:

                    missing_districts += 1

                    standardized_name = ""

                else:

                    raw_districts.add(raw_key)

                    # --------------------------------------
                    # CHECK MAPPING
                    # --------------------------------------

                    if raw_key not in mapping:

                        raise ValueError(
                            f"Unmapped district '{raw_key}' "
                            f"in {year}. "
                            f"Add it to the mapping review first."
                        )

                    standardized_name = mapping[raw_key]

                    standard_districts.add(
                        standardized_name
                    )

                    # Count rows whose district name changed.
                    if raw_key != standardized_name:

                        changed_rows += 1

                # ------------------------------------------
                # REPLACE STANDARD DISTRICT
                # ------------------------------------------

                row[district_index] = standardized_name

                # Preserve original district.
                row.append(original_district)

                writer.writerow(row)

        # Replace generated output only after successful completion.
        temp_path.replace(output_path)

    except Exception:

        if temp_path.exists():
            temp_path.unlink()

        raise

    finally:

        handle.close()

    # ==================================================
    # 8. YEAR VALIDATION
    # ==================================================

    if (
        len(standard_districts) == 36
        and missing_districts == 0
        and malformed_rows == 0
    ):

        status = "PASS"

    else:

        status = "REVIEW_REQUIRED"

    result = {

        "academic_year": year,
        "source_file": path.name,

        "output_file": str(
            output_path.relative_to(ROOT)
        ),

        "total_records": total_records,
        "raw_unique_districts": len(raw_districts),

        "standardized_unique_districts": len(
            standard_districts
        ),

        "rows_with_renamed_district": changed_rows,
        "missing_districts": missing_districts,
        "malformed_rows": malformed_rows,
        "status": status,

    }

    return result, standard_districts


# ==================================================
# 9. SAVE AUDIT REPORT
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
# 10. MAIN PROGRAM
# ==================================================

def main():

    print("\nSHALASCOPE - PROFILE 1 DISTRICT STANDARDIZATION")
    print("=" * 75)

    if not EXTRACT_ROOT.exists():

        raise FileNotFoundError(
            f"Extracted data folder not found: {EXTRACT_ROOT}"
        )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    mapping = load_district_mapping()

    audit_results = []

    all_standard_districts = set()

    # --------------------------------------------------
    # PROCESS ALL EIGHT YEARS
    # --------------------------------------------------

    for index, year in enumerate(YEARS, 1):

        print(
            f"\n[{index}/{len(YEARS)}] Academic Year: {year}"
        )

        source_path = find_profile1_file(year)

        print(f"Source: {source_path.name}")

        result, district_names = standardize_file(
            source_path,
            year,
            mapping
        )

        audit_results.append(result)

        all_standard_districts.update(
            district_names
        )

        print(
            f"School Records: "
            f"{result['total_records']:,}"
        )

        print(
            f"Raw Districts: "
            f"{result['raw_unique_districts']}"
        )

        print(
            f"Standardized Districts: "
            f"{result['standardized_unique_districts']}"
        )

        print(
            f"Rows with renamed district: "
            f"{result['rows_with_renamed_district']:,}"
        )

        print(
            f"Missing Districts: "
            f"{result['missing_districts']}"
        )

        print(
            f"Status: {result['status']}"
        )

        print(
            f"Output: {result['output_file']}"
        )

    # ==================================================
    # 11. SAVE AUDIT REPORT
    # ==================================================

    audit_fields = [

        "academic_year",
        "source_file",
        "output_file",
        "total_records",
        "raw_unique_districts",
        "standardized_unique_districts",
        "rows_with_renamed_district",
        "missing_districts",
        "malformed_rows",
        "status",

    ]

    save_report(
        AUDIT_REPORT,
        audit_results,
        audit_fields
    )

    # ==================================================
    # 12. FINAL SUMMARY
    # ==================================================

    passed = sum(
        row["status"] == "PASS"
        for row in audit_results
    )

    review = sum(
        row["status"] == "REVIEW_REQUIRED"
        for row in audit_results
    )

    total_records = sum(
        row["total_records"]
        for row in audit_results
    )

    print("\n" + "=" * 75)
    print("FINAL PROFILE 1 STANDARDIZATION SUMMARY")
    print("=" * 75)

    print(f"Academic Years: {len(audit_results)}")

    print(
        f"Total School Records: {total_records:,}"
    )

    print(
        "Unique Standardized Districts Across Years: "
        f"{len(all_standard_districts)}"
    )

    print(f"PASS: {passed}")
    print(f"Review Required: {review}")

    print("\nAUDIT REPORT")
    print(AUDIT_REPORT)

    print("\nSTANDARDIZED DATA FOLDER")
    print(OUTPUT_DIR)

    print("\nPROFILE 1 DISTRICT STANDARDIZATION COMPLETED")


# ==================================================
# 13. RUN PROGRAM
# ==================================================

if __name__ == "__main__":
    main()

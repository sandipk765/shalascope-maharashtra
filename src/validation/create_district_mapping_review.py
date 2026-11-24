
"""
ShalaScope Maharashtra
District Name Mapping Review

Purpose:
1. Read Profile 1 CSV for all 8 academic years.
2. Collect original district names and school counts.
3. Propose standardized district names.
4. Validate 36 standardized districts per year.
5. Preserve all original source files.
6. Generate two audit reports.

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

MAPPING_REPORT = (
    REPORT_DIR / "district_name_mapping_review.csv"
)

SUMMARY_REPORT = (
    REPORT_DIR / "district_mapping_validation_summary.csv"
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
# 2. DISTRICT ALIAS MAPPING
# ==================================================

DISTRICT_ALIASES = {

    # Ahmednagar -> Ahilyanagar

    "AHMADNAGAR": (
        "AHILYANAGAR",
        "OFFICIAL_RENAME",
        "Ahmednagar district renamed to Ahilyanagar."
    ),

    "AHILYANAGAR": (
        "AHILYANAGAR",
        "CURRENT_OFFICIAL_NAME",
        "Current district name."
    ),

    # Aurangabad -> Chhatrapati Sambhajinagar

    "AURANGABAD (MAHARASHTRA)": (
        "CHHATRAPATI SAMBHAJINAGAR",
        "OFFICIAL_RENAME",
        "Aurangabad district renamed to Chhatrapati Sambhajinagar."
    ),

    "CHHATRAPATI SAMBHAJINAGAR": (
        "CHHATRAPATI SAMBHAJINAGAR",
        "CURRENT_OFFICIAL_NAME",
        "Current district name."
    ),

    # Osmanabad -> Dharashiv

    "OSMANABAD": (
        "DHARASHIV",
        "OFFICIAL_RENAME",
        "Osmanabad district renamed to Dharashiv."
    ),

    "DHARASHIV": (
        "DHARASHIV",
        "CURRENT_OFFICIAL_NAME",
        "Current district name."
    ),

    # Spelling standardization

    "BID": (
        "BEED",
        "SPELLING_STANDARDIZATION",
        "Proposed standard spelling: Beed."
    ),

    "BEED": (
        "BEED",
        "CURRENT_OFFICIAL_NAME",
        "Current standard spelling."
    ),

    "GONDIYA": (
        "GONDIA",
        "SPELLING_STANDARDIZATION",
        "Proposed standard spelling: Gondia."
    ),

    "GONDIA": (
        "GONDIA",
        "CURRENT_OFFICIAL_NAME",
        "Current standard spelling."
    ),

    "RAIGARH (MAHARASHTRA)": (
        "RAIGAD",
        "SPELLING_STANDARDIZATION",
        "Proposed standard spelling: Raigad."
    ),

    "RAIGAD": (
        "RAIGAD",
        "CURRENT_OFFICIAL_NAME",
        "Current standard spelling."
    ),

    # Preserve separate UDISE label

    "MUMBAI II": (
        "MUMBAI II",
        "RETAIN_UDISE_LABEL",
        "Keep separate from MUMBAI (SUBURBAN)."
    ),
}


# ==================================================
# 3. NORMALIZE TEXT
# ==================================================

def norm(value):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


def standardize_district(raw_name):

    if raw_name == "[BLANK]":

        return (
            "[BLANK]",
            "MISSING",
            "District value is missing."
        )

    if raw_name in DISTRICT_ALIASES:

        return DISTRICT_ALIASES[raw_name]

    return (
        raw_name,
        "UNCHANGED",
        "No mapping rule applied. Original label retained."
    )


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
# 5. OPEN CSV
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
# 6. SAVE CSV REPORT
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
# 7. MAIN PROGRAM
# ==================================================

def main():

    print("\nSHALASCOPE - DISTRICT MAPPING REVIEW")
    print("=" * 70)

    if not EXTRACT_ROOT.exists():

        raise FileNotFoundError(
            f"Extracted folder not found: {EXTRACT_ROOT}"
        )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Raw district aggregation.

    district_stats = {}

    # Year-wise validation.

    yearly_results = []

    all_raw_names = set()
    all_standard_names = set()

    # --------------------------------------------------
    # PROCESS EACH YEAR
    # --------------------------------------------------

    for index, year in enumerate(YEARS, 1):

        path = find_profile1_file(year)

        print(
            f"\n[{index}/{len(YEARS)}] "
            f"{year} | {path.name}"
        )

        handle, dialect = open_csv(path)

        raw_names_this_year = set()
        standard_names_this_year = set()

        total_records = 0
        missing_districts = 0

        try:

            reader = csv.reader(
                handle,
                dialect=dialect
            )

            headers = next(reader, [])

            if not headers:
                raise ValueError("Empty CSV header.")

            normalized_headers = {
                norm(header): position
                for position, header in enumerate(headers)
            }

            district_index = normalized_headers.get("district")

            if district_index is None:

                raise ValueError(
                    "District column not found."
                )

            # ------------------------------------------
            # PROCESS ROWS
            # ------------------------------------------

            for row in reader:

                if not row or all(
                    not str(value).strip()
                    for value in row
                ):
                    continue

                total_records += 1

                raw_value = (
                    row[district_index]
                    if district_index < len(row)
                    else ""
                )

                raw_value = str(raw_value).strip()

                if raw_value.lower() in MISSING_VALUES:

                    raw_name = "[BLANK]"
                    missing_districts += 1

                else:

                    raw_name = raw_value.upper()

                standard_name, mapping_type, reason = (
                    standardize_district(raw_name)
                )

                raw_names_this_year.add(raw_name)
                standard_names_this_year.add(standard_name)

                all_raw_names.add(raw_name)
                all_standard_names.add(standard_name)

                # Initialize district record.

                if raw_name not in district_stats:

                    district_stats[raw_name] = {

                        "raw_name": raw_name,
                        "standard_name": standard_name,
                        "mapping_type": mapping_type,
                        "mapping_reason": reason,
                        "years": set(),
                        "total_records": 0,
                        "year_counts": defaultdict(int),

                    }

                stats = district_stats[raw_name]

                stats["total_records"] += 1
                stats["year_counts"][year] += 1
                stats["years"].add(year)

        finally:

            handle.close()

        # ------------------------------------------
        # YEAR-WISE SUMMARY
        # ------------------------------------------

        if (
            len(raw_names_this_year) == 36
            and len(standard_names_this_year) == 36
            and missing_districts == 0
        ):

            status = "PASS"

        else:

            status = "REVIEW_REQUIRED"

        yearly_results.append({

            "academic_year": year,
            "total_records": total_records,
            "raw_unique_districts": len(raw_names_this_year),
            "standardized_unique_districts": len(
                standard_names_this_year
            ),
            "missing_districts": missing_districts,
            "status": status,

        })

        print(f"School Records: {total_records:,}")
        print(f"Raw Districts: {len(raw_names_this_year)}")
        print(
            "Standardized Districts: "
            f"{len(standard_names_this_year)}"
        )
        print(f"Missing Districts: {missing_districts}")
        print(f"Status: {status}")

    # ==================================================
    # 8. BUILD MAPPING REVIEW REPORT
    # ==================================================

    mapping_results = []

    for raw_name in sorted(district_stats):

        stats = district_stats[raw_name]

        record = {

            "raw_district_name": stats["raw_name"],

            "proposed_standard_district": (
                stats["standard_name"]
            ),

            "mapping_type": stats["mapping_type"],

            "mapping_reason": stats["mapping_reason"],

            "academic_years_present": ";".join(
                sorted(stats["years"])
            ),

            "total_school_records": (
                stats["total_records"]
            ),

        }

        for year in YEARS:

            record[f"schools_{year}"] = (
                stats["year_counts"].get(year, 0)
            )

        mapping_results.append(record)

    mapping_fields = [

        "raw_district_name",
        "proposed_standard_district",
        "mapping_type",
        "mapping_reason",
        "academic_years_present",
        "total_school_records",

    ] + [
        f"schools_{year}"
        for year in YEARS
    ]

    save_report(
        MAPPING_REPORT,
        mapping_results,
        mapping_fields
    )

    # ==================================================
    # 9. BUILD YEAR VALIDATION REPORT
    # ==================================================

    summary_fields = [

        "academic_year",
        "total_records",
        "raw_unique_districts",
        "standardized_unique_districts",
        "missing_districts",
        "status",

    ]

    save_report(
        SUMMARY_REPORT,
        yearly_results,
        summary_fields
    )

    # ==================================================
    # 10. FINAL SUMMARY
    # ==================================================

    passed = sum(
        row["status"] == "PASS"
        for row in yearly_results
    )

    review = sum(
        row["status"] == "REVIEW_REQUIRED"
        for row in yearly_results
    )

    print("\n" + "=" * 70)
    print("FINAL DISTRICT MAPPING SUMMARY")
    print("=" * 70)

    print(f"Academic Years: {len(yearly_results)}")
    print(f"Raw District Labels Across Years: {len(all_raw_names)}")
    print(f"Standardized District Names: {len(all_standard_names)}")
    print(f"PASS: {passed}")
    print(f"Review Required: {review}")

    print("\nREPORTS CREATED")

    print(MAPPING_REPORT)
    print(SUMMARY_REPORT)

    print("\nDISTRICT MAPPING REVIEW COMPLETED")


if __name__ == "__main__":
    main()

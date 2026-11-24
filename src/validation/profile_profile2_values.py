"""
ShalaScope Maharashtra
Profile 2 Value Audit and Integrity Validation

Years: 2018-19 to 2025-26

Checks:
1. Column-wise missing values.
2. Numeric and non-numeric values.
3. Negative numeric values.
4. Numeric minimum and maximum.
5. Distinct values and category frequencies.
6. Pseudocode / School ID uniqueness.
7. Profile 2 vs Master School ID comparison.
8. District count and missing district values.
9. Year-wise schema differences.

Original datasets are never modified.
Python standard library only.
"""

from pathlib import Path
from collections import Counter
import csv


# ==================================================
# 1. PATHS
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

PROFILE2_DIR = (
    ROOT / "data" / "interim" / "standardized" / "profile2"
)

MASTER_DIR = (
    ROOT / "data" / "processed" / "school_year"
)

REPORT_DIR = ROOT / "reports" / "data_audit"

COLUMN_REPORT = (
    REPORT_DIR / "profile2_column_value_audit.csv"
)

FREQUENCY_REPORT = (
    REPORT_DIR / "profile2_low_cardinality_values.csv"
)

SUMMARY_REPORT = (
    REPORT_DIR / "profile2_year_integrity_audit.csv"
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

MISSING_VALUES = {
    "", "na", "n/a", "null", "none", "nan"
}

MAX_CATEGORY_VALUES = 100


# ==================================================
# 2. HELPERS
# ==================================================

def normalize_header(value):

    return "".join(
        ch.lower()
        for ch in str(value)
        if ch.isalnum()
    )


def open_csv(path):

    handle = path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    )

    sample = handle.read(8192)
    handle.seek(0)

    try:

        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=",;\t|"
        )

    except csv.Error:

        dialect = csv.excel

    return handle, dialect


def find_column(headers, candidates):

    lookup = {
        normalize_header(header): header
        for header in headers
    }

    for candidate in candidates:

        key = normalize_header(candidate)

        if key in lookup:
            return lookup[key]

    return None


def parse_number(value):

    text = str(value).strip().replace(",", "")

    try:
        return float(text)

    except (ValueError, TypeError):
        return None


def save_csv(path, rows, fields):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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
# 3. MASTER SCHOOL ID AUDIT
# ==================================================

def read_master_ids(path):

    handle, dialect = open_csv(path)

    try:

        reader = csv.DictReader(
            handle,
            dialect=dialect
        )

        headers = reader.fieldnames or []

        id_column = find_column(
            headers,
            ["school_id", "udise_code", "school_code"]
        )

        if not id_column:

            raise ValueError(
                "Master School ID column not found."
            )

        ids = set()
        total_rows = 0
        missing_ids = 0

        for row in reader:

            total_rows += 1

            value = str(
                row.get(id_column, "") or ""
            ).strip()

            if not value:

                missing_ids += 1

            else:

                ids.add(value)

        duplicate_ids = total_rows - missing_ids - len(ids)

        return {
            "id_column": id_column,
            "total_rows": total_rows,
            "ids": ids,
            "missing_ids": missing_ids,
            "duplicate_ids": duplicate_ids,
        }

    finally:

        handle.close()


# ==================================================
# 4. PROFILE 2 VALUE AUDIT
# ==================================================

def audit_profile2_file(year):

    profile2_path = (
        PROFILE2_DIR
        / f"maharashtra_profile2_{year}_standardized.csv"
    )

    master_path = (
        MASTER_DIR
        / f"maharashtra_school_year_master_{year}.csv"
    )

    if not profile2_path.exists():
        raise FileNotFoundError(profile2_path)

    if not master_path.exists():
        raise FileNotFoundError(master_path)

    print("\n" + "=" * 70)
    print(f"STARTING PROFILE 2 AUDIT: {year}")
    print("=" * 70)

    # ----------------------------------------------
    # Master ID reference
    # ----------------------------------------------

    master = read_master_ids(master_path)

    master_ids = master["ids"]

    print(
        f"Master Records: {master['total_rows']:,}"
    )

    # ----------------------------------------------
    # Profile 2 CSV
    # ----------------------------------------------

    handle, dialect = open_csv(profile2_path)

    column_results = []
    frequency_results = []

    profile2_ids = set()

    district_values = set()

    total_rows = 0
    missing_key = 0
    missing_district = 0

    try:

        reader = csv.DictReader(
            handle,
            dialect=dialect
        )

        headers = reader.fieldnames or []

        if not headers:
            raise ValueError("Profile 2 header is empty.")

        key_column = find_column(
            headers,
            [
                "psuedocode",
                "pseudocode",
                "school_id",
                "udise_code",
                "school_code",
            ]
        )

        district_column = find_column(
            headers,
            ["district"]
        )

        if not key_column:

            raise ValueError(
                "Profile 2 identifier column not found."
            )

        if not district_column:

            raise ValueError(
                "District column not found."
            )

        print(f"Profile 2 Key Column: {key_column}")
        print(f"Total Columns: {len(headers)}")

        # ------------------------------------------
        # Per-column statistics
        # ------------------------------------------

        stats = {}

        for column in headers:

            stats[column] = {
                "non_missing": 0,
                "missing": 0,
                "numeric": 0,
                "non_numeric": 0,
                "negative": 0,
                "minimum": None,
                "maximum": None,
                "frequency": Counter(),
                "sample": [],
                "sample_seen": set(),
                "high_cardinality": False,
            }

        # ------------------------------------------
        # Read records
        # ------------------------------------------

        for row in reader:

            if None in row:

                raise ValueError(
                    f"Malformed row near record {total_rows + 2}"
                )

            total_rows += 1

            # School identifier
            key_value = str(
                row.get(key_column, "") or ""
            ).strip()

            if not key_value:

                missing_key += 1

            else:

                profile2_ids.add(key_value)

            # District
            district_value = str(
                row.get(district_column, "") or ""
            ).strip()

            if not district_value:

                missing_district += 1

            else:

                district_values.add(district_value)

            # Column values
            for column in headers:

                value = str(
                    row.get(column, "") or ""
                ).strip()

                item = stats[column]

                if value.lower() in MISSING_VALUES:

                    item["missing"] += 1
                    continue

                item["non_missing"] += 1

                number = parse_number(value)

                if number is None:

                    item["non_numeric"] += 1

                else:

                    item["numeric"] += 1

                    if number < 0:
                        item["negative"] += 1

                    if item["minimum"] is None:

                        item["minimum"] = number
                        item["maximum"] = number

                    else:

                        item["minimum"] = min(
                            item["minimum"],
                            number
                        )

                        item["maximum"] = max(
                            item["maximum"],
                            number
                        )

                # Keep a small sample of unique values.
                if (
                    len(item["sample"]) < 8
                    and value not in item["sample_seen"]
                ):

                    item["sample_seen"].add(value)
                    item["sample"].append(value)

                # Keep frequency counts only up to 100
                # distinct values to avoid excessive memory use.
                if not item["high_cardinality"]:

                    item["frequency"][value] += 1

                    if len(item["frequency"]) > MAX_CATEGORY_VALUES:

                        item["high_cardinality"] = True
                        item["frequency"].clear()

        # ------------------------------------------
        # Build column report
        # ------------------------------------------

        for column, item in stats.items():

            if column in {
                key_column,
                district_column,
                "district_raw",
            }:

                profile_type = "IDENTIFIER_OR_LOCATION"

            elif item["non_missing"] == 0:

                profile_type = "ALL_MISSING"

            elif item["numeric"] == item["non_missing"]:

                profile_type = "NUMERIC"

            elif item["numeric"] == 0:

                profile_type = "TEXT_OR_CATEGORICAL"

            else:

                profile_type = "MIXED"

            distinct_count = (
                "MORE_THAN_100"
                if item["high_cardinality"]
                else len(item["frequency"])
            )

            column_results.append({

                "academic_year": year,
                "column_name": column,
                "total_rows": total_rows,
                "non_missing_values": item["non_missing"],
                "missing_values": item["missing"],
                "numeric_values": item["numeric"],
                "non_numeric_values": item["non_numeric"],
                "negative_numeric_values": item["negative"],
                "minimum_numeric_value": item["minimum"],
                "maximum_numeric_value": item["maximum"],
                "distinct_values": distinct_count,
                "sample_values": " | ".join(item["sample"]),
                "data_profile": profile_type,

            })

            # --------------------------------------
            # Frequency audit for low-cardinality
            # fields only
            # --------------------------------------

            if not item["high_cardinality"]:

                for value, count in sorted(
                    item["frequency"].items()
                ):

                    frequency_results.append({

                        "academic_year": year,
                        "column_name": column,
                        "value": value,
                        "frequency": count,

                    })

        # ------------------------------------------
        # Compare Profile 2 IDs with Master IDs
        # ------------------------------------------

        unmatched_profile2 = (
            profile2_ids - master_ids
        )

        missing_master = (
            master_ids - profile2_ids
        )

        duplicate_profile2_ids = (
            total_rows - missing_key - len(profile2_ids)
        )

        # ------------------------------------------
        # Year result
        # ------------------------------------------

        district_count = len(district_values)

        is_pass = (

            total_rows == master["total_rows"]

            and missing_key == 0

            and duplicate_profile2_ids == 0

            and len(unmatched_profile2) == 0

            and len(missing_master) == 0

            and district_count == 36

            and missing_district == 0

            and master["missing_ids"] == 0

            and master["duplicate_ids"] == 0

        )

        status = "PASS" if is_pass else "REVIEW_REQUIRED"

        summary = {

            "academic_year": year,
            "master_records": master["total_rows"],
            "profile2_records": total_rows,
            "profile2_columns": len(headers),
            "key_column": key_column,
            "missing_key": missing_key,
            "duplicate_profile2_ids": duplicate_profile2_ids,
            "unmatched_profile2_ids": len(unmatched_profile2),
            "missing_master_ids": len(missing_master),
            "district_count": district_count,
            "missing_district": missing_district,
            "status": status,

        }

        print(f"Profile 2 Records: {total_rows:,}")
        print(f"Missing Key: {missing_key}")
        print(f"Duplicate IDs: {duplicate_profile2_ids}")
        print(f"Unmatched Profile 2 IDs: {len(unmatched_profile2)}")
        print(f"Missing Master IDs: {len(missing_master)}")
        print(f"Districts: {district_count}")
        print(f"Missing District: {missing_district}")
        print(f"STATUS: {status}")

        return summary, column_results, frequency_results

    finally:

        handle.close()


# ==================================================
# 5. MAIN
# ==================================================

def main():

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    all_summaries = []
    all_columns = []
    all_frequencies = []

    for index, year in enumerate(YEARS, 1):

        print(
            f"\nPROCESSING YEAR {index}/{len(YEARS)}"
        )

        try:

            summary, columns, frequencies = (
                audit_profile2_file(year)
            )

            all_summaries.append(summary)
            all_columns.extend(columns)
            all_frequencies.extend(frequencies)

        except Exception as error:

            print(
                f"ERROR IN {year}: {error}"
            )

            all_summaries.append({

                "academic_year": year,
                "master_records": 0,
                "profile2_records": 0,
                "profile2_columns": 0,
                "key_column": "",
                "missing_key": 0,
                "duplicate_profile2_ids": 0,
                "unmatched_profile2_ids": 0,
                "missing_master_ids": 0,
                "district_count": 0,
                "missing_district": 0,
                "status": "FAILED",

            })

    # ----------------------------------------------
    # Save column report
    # ----------------------------------------------

    save_csv(

        COLUMN_REPORT,
        all_columns,

        [
            "academic_year",
            "column_name",
            "total_rows",
            "non_missing_values",
            "missing_values",
            "numeric_values",
            "non_numeric_values",
            "negative_numeric_values",
            "minimum_numeric_value",
            "maximum_numeric_value",
            "distinct_values",
            "sample_values",
            "data_profile",
        ]

    )

    # ----------------------------------------------
    # Save frequency report
    # ----------------------------------------------

    save_csv(

        FREQUENCY_REPORT,
        all_frequencies,

        [
            "academic_year",
            "column_name",
            "value",
            "frequency",
        ]

    )

    # ----------------------------------------------
    # Save year summary
    # ----------------------------------------------

    save_csv(

        SUMMARY_REPORT,
        all_summaries,

        [
            "academic_year",
            "master_records",
            "profile2_records",
            "profile2_columns",
            "key_column",
            "missing_key",
            "duplicate_profile2_ids",
            "unmatched_profile2_ids",
            "missing_master_ids",
            "district_count",
            "missing_district",
            "status",
        ]

    )

    # ----------------------------------------------
    # Final result
    # ----------------------------------------------

    passed = sum(
        row["status"] == "PASS"
        for row in all_summaries
    )

    failed = sum(
        row["status"] == "FAILED"
        for row in all_summaries
    )

    review = sum(
        row["status"] == "REVIEW_REQUIRED"
        for row in all_summaries
    )

    print("\n" + "=" * 70)
    print("PROFILE 2 - FINAL AUDIT SUMMARY")
    print("=" * 70)

    for row in all_summaries:

        print(
            f"{row['academic_year']} : {row['status']}"
        )

    print(f"\nTotal Years: {len(all_summaries)}")
    print(f"PASS: {passed}")
    print(f"REVIEW REQUIRED: {review}")
    print(f"FAILED: {failed}")

    print("\nREPORTS CREATED:")

    print(COLUMN_REPORT)
    print(FREQUENCY_REPORT)
    print(SUMMARY_REPORT)

    print("\nPROFILE 2 VALUE AUDIT COMPLETED")


if __name__ == "__main__":
    main()
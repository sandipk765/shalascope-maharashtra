"""
ShalaScope Maharashtra
Profile 1 Categorical Feature Decoder

Years: 2018-19 to 2025-26

Features:
1. Decodes Profile 1 categorical columns.
2. Preserves all original columns and raw codes.
3. Adds human-readable label columns.
4. Adds mapping-status columns.
5. Handles medium codes with leading zeros.
6. Uses year-aware management code mapping.
7. Flags uncertain code meanings for review.
8. Creates year-wise decoding audit reports.
9. Never modifies original Master CSV files.

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

OUTPUT_DIR = (
    ROOT
    / "data"
    / "processed"
    / "school_year_features"
    / "profile1"
)

REPORT_DIR = ROOT / "reports" / "data_audit"

VALUE_REPORT = REPORT_DIR / "profile1_categorical_decoding_audit.csv"

SUMMARY_REPORT = REPORT_DIR / "profile1_categorical_decoding_summary.csv"

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
# 2. CATEGORICAL CODEBOOK
# ==================================================

CODEBOOK = {

    "rural_urban": {
        "1": "Rural",
        "2": "Urban",
    },

    "school_category": {
        "1": "Primary Only (Grades 1-5)",
        "2": "Primary with Upper Primary (Grades 1-8)",
        "3": (
            "Primary, Upper Primary, Secondary "
            "and Higher Secondary (Grades 1-12)"
        ),
        "4": "Upper Primary Only (Grades 6-8)",
        "5": (
            "Upper Primary, Secondary "
            "and Higher Secondary (Grades 6-12)"
        ),
        "6": (
            "Primary, Upper Primary "
            "and Secondary (Grades 1-10)"
        ),
        "7": "Upper Primary and Secondary (Grades 6-10)",
        "8": "Secondary Only (Grades 9-10)",
        "10": "Secondary with Higher Secondary (Grades 9-12)",
        "11": "Higher Secondary / Junior College Only (Grades 11-12)",
        "12": "Pre-Primary Only",
    },

    "school_type": {
        "1": "Boys",
        "2": "Girls",
        "3": "Co-educational",
    },

    # Codes 97 and 99 are handled separately
    # in decode_management_code().

    "managment": {
        "1": "Department of Education",
        "2": "Tribal Welfare Department",
        "3": "Local Body",
        "4": "Government Aided",
        "5": "Private Unaided (Recognized)",
        "6": "Other State Government Managed Schools",
        "7": "Partially Government Aided",
        "8": "Unrecognized",
        "89": "Minority Affairs Department",
        "90": "Social Welfare Department",
        "91": "Ministry of Labour",
        "92": "Kendriya Vidyalaya / Central School",
        "93": "Jawahar Navodaya Vidyalaya",
        "94": "Sainik School",
        "95": "Railway School",
        "96": "Central Tibetan School",
        "97": "Recognized Madrasa (Subtype Not Specified)",
        "98": "Madrasa Unrecognized",
        "99": "Madrasa Aided (Recognized)",
        "101": "Other Central Government / PSU Schools",
        "102": "Veda Schools / Gurukuls / Pathashalas",
    },

    "special_school_for_cwsn": {
        "1": "Yes",
        "2": "No",
        "9": "Not Applicable",
    },

    "shift_school": {
        "1": "Yes",
        "2": "No",
        "9": "Not Applicable",
    },

    "resi_school": {
        "1": "Completely Residential",
        "2": "Partially Residential",
        "3": "Non-Residential",
    },

    "minority_school": {
        "1": "Yes",
        "2": "No",
        "9": "Not Applicable",
    },

    "pre_primary": {
        "1": "Yes",
        "2": "No",
        "9": "Not Applicable",
    },

    "medium_instr1": {
        "01": "Assamese",
        "02": "Bengali",
        "03": "Gujarati",
        "04": "Hindi",
        "05": "Kannada",
        "06": "Kashmiri",
        "07": "Konkani",
        "08": "Malayalam",
        "09": "Manipuri",
        "10": "Marathi",
        "11": "Nepali",
        "12": "Odia",
        "13": "Punjabi",
        "14": "Sanskrit",
        "15": "Sindhi",
        "16": "Tamil",
        "17": "Telugu",
        "18": "Urdu",
        "19": "English",
        "20": "Bodo",
        "22": "Dogri",
        "23": "Khasi",
        "24": "Garo",
        "25": "Mizo",
        "26": "Bhutia",
        "27": "Lepcha",
        "28": "Limbu",
        "29": "French",
        "30": "Hmar",
        "31": "Bishnupriya Manipuri",
        "32": "Karbi",
        "39": "Santhali",
        "49": "Bhoti (Ladakhi)",
        "51": "Maithili",
        "71": "Balti",
        "72": "Purgi",
        "73": "Tibetan",
        "97": "Foreign Medium",
        "99": "Other Medium of Instruction (Legacy / Variant Code)",
    },
}


# ==================================================
# 3. OUTPUT COLUMNS
# ==================================================

LABEL_COLUMNS = {
    column: f"{column}_label"
    for column in CODEBOOK
}

STATUS_COLUMNS = {
    column: f"{column}_label_status"
    for column in CODEBOOK
}


# ==================================================
# 4. HELPERS
# ==================================================

def norm_column(value):

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
        f"Cannot decode CSV file: {path}\n"
        f"Last error: {last_error}"
    )


def normalize_code(column, value):

    code = str(value or "").strip()

    if code.lower() in MISSING_VALUES:
        return ""

    # Convert single-digit medium codes into 01-09.
    if (
        column == "medium_instr1"
        and code.isdigit()
        and len(code) == 1
    ):
        code = code.zfill(2)

    return code


# ==================================================
# 5. YEAR-WISE MANAGEMENT CODE MAPPING
# ==================================================

def decode_management_code(code, year):

    # ----------------------------------------------
    # Management Code 97
    # ----------------------------------------------

    if code == "97":

        if year in {
            "2018-19",
            "2019-20",
            "2020-21",
            "2021-22",
        }:

            return (
                "Recognized Madrasa "
                "(Legacy Classification - Subtype Not Specified)",
                "MAPPED_WITH_CAVEAT"
            )

        if year == "2022-23":

            return (
                "Recognized Madrasa "
                "(2022-23 Reference Variant - Subtype Requires Review)",
                "MAPPED_WITH_CAVEAT"
            )

        if year in {
            "2023-24",
            "2024-25",
        }:

            return (
                "Recognized Madrasa "
                "(Subtype Not Specified - Reference Variation)",
                "MAPPED_WITH_CAVEAT"
            )

        if year == "2025-26":

            return (
                "Recognized Madrasa "
                "(Subtype Not Confirmed for 2025-26)",
                "MAPPED_WITH_CAVEAT"
            )

    # ----------------------------------------------
    # Management Code 99
    # ----------------------------------------------

    if code == "99":

        if year == "2022-23":

            return (
                "Madrasa Aided (Recognized) "
                "(2022-23 Reference Variant - Verify DCF Edition)",
                "MAPPED_WITH_CAVEAT"
            )

        if year in {
            "2023-24",
            "2024-25",
        }:

            return (
                "Madrasa Aided (Recognized)",
                "MAPPED"
            )

        if year == "2025-26":

            return (
                "Madrasa Aided (Recognized) "
                "(Current-year Reference Requires Verification)",
                "MAPPED_WITH_CAVEAT"
            )

        return (
            f"UNMAPPED_CODE:{code}",
            "REVIEW_REQUIRED"
        )

    return None


# ==================================================
# 6. MAIN DECODING FUNCTION
# ==================================================

def decode_value(column, raw_value, year):

    code = normalize_code(
        column,
        raw_value
    )

    if not code:

        return "MISSING", "MISSING"

    # Special year-wise Management mapping.
    if column == "managment":

        result = decode_management_code(
            code,
            year
        )

        if result is not None:
            return result

    # Medium code 99 requires a caveat.
    if (
        column == "medium_instr1"
        and code == "99"
    ):

        return (
            "Other Medium of Instruction "
            "(Legacy / Variant Code)",
            "MAPPED_WITH_CAVEAT"
        )

    label = CODEBOOK[column].get(code)

    if label is None:

        return (
            f"UNMAPPED_CODE:{code}",
            "REVIEW_REQUIRED"
        )

    return label, "MAPPED"


# ==================================================
# 7. SAVE REPORT
# ==================================================

def save_report(path, rows, fields):

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
            fieldnames=fields,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
            doublequote=True,
            lineterminator="\n"
        )

        writer.writeheader()
        writer.writerows(rows)


# ==================================================
# 8. PROCESS ONE YEAR
# ==================================================

def process_year(year):

    input_path = (
        MASTER_DIR
        / f"maharashtra_school_year_master_{year}.csv"
    )

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        OUTPUT_DIR
        / f"maharashtra_profile1_features_{year}.csv"
    )

    temp_path = output_path.with_suffix(".tmp")

    value_counts = {
        column: Counter()
        for column in CODEBOOK
    }

    total_records = 0
    unmapped_count = 0
    missing_count = 0
    caveat_count = 0

    handle, dialect = open_csv(input_path)

    try:

        reader = csv.DictReader(
            handle,
            dialect=dialect
        )

        headers = reader.fieldnames or []

        if not headers:
            raise ValueError("Master CSV header is empty.")

        # Normalize column names.
        lookup = {}

        for header in headers:

            normalized_header = norm_column(header)

            if normalized_header in lookup:

                raise ValueError(
                    f"Duplicate normalized column name: {header}"
                )

            lookup[normalized_header] = header

        # Validate required categorical columns.
        missing_columns = [
            column
            for column in CODEBOOK
            if norm_column(column) not in lookup
        ]

        if missing_columns:

            raise ValueError(
                f"{year}: Required columns missing: "
                f"{missing_columns}"
            )

        # Check that output columns are not already present.
        new_columns = (
            list(LABEL_COLUMNS.values())
            + list(STATUS_COLUMNS.values())
        )

        existing_normalized = set(lookup)

        duplicate_outputs = [
            name
            for name in new_columns
            if norm_column(name) in existing_normalized
        ]

        if duplicate_outputs:

            raise ValueError(
                "Output label/status columns already exist: "
                f"{duplicate_outputs}"
            )

        output_fields = headers + new_columns

        # Write temporary output first.
        with temp_path.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as output_file:

            writer = csv.DictWriter(
                output_file,
                fieldnames=output_fields,
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
                doublequote=True,
                lineterminator="\n",
                extrasaction="raise"
            )

            writer.writeheader()

            for record_number, row in enumerate(
                reader,
                start=2
            ):

                if row is None or None in row:

                    raise ValueError(
                        f"Malformed CSV row: {record_number}"
                    )

                if not any(
                    str(value or "").strip()
                    for value in row.values()
                ):
                    continue

                total_records += 1

                output_row = dict(row)

                for column in CODEBOOK:

                    source_column = lookup[
                        norm_column(column)
                    ]

                    raw_value = str(
                        row.get(source_column, "") or ""
                    ).strip()

                    normalized_code = normalize_code(
                        column,
                        raw_value
                    )

                    label, mapping_status = decode_value(
                        column,
                        raw_value,
                        year
                    )

                    label_column = LABEL_COLUMNS[column]
                    status_column = STATUS_COLUMNS[column]

                    output_row[label_column] = label
                    output_row[status_column] = mapping_status

                    value_counts[column][
                        (
                            raw_value,
                            normalized_code,
                            label,
                            mapping_status
                        )
                    ] += 1

                    if mapping_status == "REVIEW_REQUIRED":

                        unmapped_count += 1

                    elif mapping_status == "MISSING":

                        missing_count += 1

                    elif mapping_status == "MAPPED_WITH_CAVEAT":

                        caveat_count += 1

                writer.writerow(output_row)

        # Replace output only after successful processing.
        temp_path.replace(output_path)

    except Exception:

        if temp_path.exists():
            temp_path.unlink()

        raise

    finally:

        handle.close()

    # ==================================================
    # 9. BUILD VALUE AUDIT
    # ==================================================

    value_results = []

    for column, counter in value_counts.items():

        for key, count in counter.items():

            (
                raw_code,
                normalized_code,
                label,
                mapping_status
            ) = key

            value_results.append({

                "academic_year": year,
                "source_column": column,
                "raw_code": raw_code,
                "normalized_code": normalized_code,
                "decoded_label": label,
                "school_count": count,
                "status": mapping_status,

            })

    # ==================================================
    # 10. YEAR STATUS
    # ==================================================

    if unmapped_count > 0:

        year_status = "REVIEW_REQUIRED"

    elif caveat_count > 0:

        year_status = "PASS_WITH_CAVEATS"

    else:

        year_status = "PASS"

    summary = {

        "academic_year": year,
        "total_records": total_records,
        "categorical_columns_decoded": len(CODEBOOK),
        "missing_values": missing_count,
        "unmapped_values": unmapped_count,
        "values_with_semantic_caveat": caveat_count,

        "output_file": str(
            output_path.relative_to(ROOT)
        ),

        "status": year_status,

    }

    return summary, value_results


# ==================================================
# 11. MAIN FUNCTION
# ==================================================

def main():

    print(
        "\nSHALASCOPE - PROFILE 1 CATEGORICAL FEATURE BUILDER"
    )

    print("=" * 75)

    if not MASTER_DIR.exists():
        raise FileNotFoundError(MASTER_DIR)

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    summaries = []
    all_values = []

    for index, year in enumerate(YEARS, 1):

        print(
            f"\n[{index}/{len(YEARS)}] {year}"
        )

        try:

            summary, values = process_year(year)

            summaries.append(summary)
            all_values.extend(values)

            print(
                f"Records: {summary['total_records']:,}"
            )

            print(
                f"Categorical Columns: "
                f"{summary['categorical_columns_decoded']}"
            )

            print(
                f"Missing Values: "
                f"{summary['missing_values']}"
            )

            print(
                f"Unmapped Values: "
                f"{summary['unmapped_values']}"
            )

            print(
                f"Values with Semantic Caveat: "
                f"{summary['values_with_semantic_caveat']}"
            )

            print(
                f"STATUS: {summary['status']}"
            )

            print(
                f"Output: {summary['output_file']}"
            )

        except Exception as error:

            print(
                f"ERROR: {error}"
            )

            summaries.append({

                "academic_year": year,
                "total_records": 0,
                "categorical_columns_decoded": 0,
                "missing_values": 0,
                "unmapped_values": 0,
                "values_with_semantic_caveat": 0,
                "output_file": "",
                "status": "FAILED",

            })

    # ==================================================
    # 12. SAVE VALUE AUDIT
    # ==================================================

    value_fields = [

        "academic_year",
        "source_column",
        "raw_code",
        "normalized_code",
        "decoded_label",
        "school_count",
        "status",

    ]

    save_report(
        VALUE_REPORT,
        all_values,
        value_fields
    )

    # ==================================================
    # 13. SAVE SUMMARY AUDIT
    # ==================================================

    summary_fields = [

        "academic_year",
        "total_records",
        "categorical_columns_decoded",
        "missing_values",
        "unmapped_values",
        "values_with_semantic_caveat",
        "output_file",
        "status",

    ]

    save_report(
        SUMMARY_REPORT,
        summaries,
        summary_fields
    )

    # ==================================================
    # 14. FINAL SUMMARY
    # ==================================================

    passed = sum(
        row["status"] in {
            "PASS",
            "PASS_WITH_CAVEATS"
        }
        for row in summaries
    )

    caveat_years = sum(
        row["status"] == "PASS_WITH_CAVEATS"
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
        row["total_records"]
        for row in summaries
    )

    total_unmapped = sum(
        row["unmapped_values"]
        for row in summaries
    )

    total_caveats = sum(
        row["values_with_semantic_caveat"]
        for row in summaries
    )

    print("\n" + "=" * 75)

    print(
        "FINAL PROFILE 1 CATEGORICAL FEATURE SUMMARY"
    )

    print("=" * 75)

    print(
        f"Academic Years: {len(summaries)}"
    )

    print(
        f"Total Records: {total_records:,}"
    )

    print(
        f"PASS / PASS WITH CAVEATS: {passed}"
    )

    print(
        f"Years with Caveats: {caveat_years}"
    )

    print(
        f"Review Required: {review}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        f"Unmapped Values: {total_unmapped}"
    )

    print(
        f"Values with Semantic Caveat: {total_caveats}"
    )

    print("\nOUTPUT FOLDER")
    print(OUTPUT_DIR)

    print("\nREPORTS CREATED")
    print(VALUE_REPORT)
    print(SUMMARY_REPORT)

    print(
        "\nPROFILE 1 CATEGORICAL FEATURE BUILD COMPLETED"
    )


# ==================================================
# 15. ENTRY POINT
# ==================================================

if __name__ == "__main__":

    main()
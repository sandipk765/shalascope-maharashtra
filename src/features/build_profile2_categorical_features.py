"""
===========================================================
SHALASCOPE MAHARASHTRA
PROFILE 2 CATEGORICAL FEATURE DECODER - V3
===========================================================

Academic Years:
2018-19 to 2025-26

OLD SCHEMA:
2018-19 to 2021-22

NEW SCHEMA:
2022-23 to 2025-26

Features:
1. Year-wise categorical decoding.
2. Old and new schema separation.
3. Officially documented code mapping.
4. Code 9 = Not Applicable for old schema.
5. 2021-22 SMDC code 3 mapping.
6. Unknown codes preserved for review.
7. Original columns and raw values preserved.
8. Versioned output files.
9. Detailed decoding audit reports.

Original input CSV files are never modified.

Python standard library only.
===========================================================
"""

from pathlib import Path
from collections import Counter
import csv
import re


# ===========================================================
# 1. PROJECT PATHS
# ===========================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    ROOT
    / "data"
    / "interim"
    / "standardized"
    / "profile2"
)

OUTPUT_DIR = (
    ROOT
    / "data"
    / "processed"
    / "school_year_features"
    / "profile2"
)

REPORT_DIR = (
    ROOT
    / "reports"
    / "data_audit"
)


# ===========================================================
# 2. VERSION 3 OUTPUT FILES
# ===========================================================

VALUE_REPORT = (
    REPORT_DIR
    / "profile2_categorical_decoding_audit_v3.csv"
)

SUMMARY_REPORT = (
    REPORT_DIR
    / "profile2_categorical_decoding_summary_v3.csv"
)


# ===========================================================
# 3. ACADEMIC YEARS
# ===========================================================

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

OLD_YEARS = {
    "2018-19",
    "2019-20",
    "2020-21",
    "2021-22",
}

NEW_YEARS = {
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
}


# ===========================================================
# 4. CSV SETTINGS
# ===========================================================

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


# ===========================================================
# 5. OLD SCHEMA NUMERIC FIELDS
# ===========================================================
# These fields are preserved without categorical decoding.
#
# Their exact semantic interpretation should be validated
# separately against the relevant historical DCF.
# ===========================================================

OLD_NUMERIC_FIELDS = {

    "free_text_books_pr",

    "transport_pr",

    "free_uniform_pr",

    "free_text_books_up",

    "transport_up",

    "free_uniform_up",

}


# ===========================================================
# 6. YES / NO CODEBOOK
# ===========================================================

YES_NO = {

    "1": "Yes",

    "2": "No",

}


# ===========================================================
# 7. YEAR-WISE CODEBOOK
# ===========================================================

def get_year_codebook(year):

    codebook = {}


    # -------------------------------------------------------
    # OLD SCHEMA: 2018-19 TO 2021-22
    # -------------------------------------------------------

    if year in OLD_YEARS:

        # According to the old DSP Schema:
        # 9 = Not Applicable.

        old_not_applicable = {

            "1": "Yes",

            "2": "No",

            "9": "Not Applicable",

        }

        codebook["special_training"] = (
            old_not_applicable.copy()
        )

        codebook["material_training"] = (
            old_not_applicable.copy()
        )

        codebook["text_books_received"] = (
            old_not_applicable.copy()
        )

        codebook["smc_exists"] = (
            old_not_applicable.copy()
        )

        codebook["smdc_constituted"] = (
            old_not_applicable.copy()
        )

        codebook["smc_smdc_same"] = {

            "1": "SMC and SMDC are Same",

            "2": "SMC and SMDC are Different",

            "9": "Not Applicable",

        }

        # Special 2021-22 mapping:
        # The official 2021-22 Help Module describes
        # Code 3 as Same as SMC for SMDC constitution.

        if year == "2021-22":

            codebook["smdc_constituted"] = {

                "1": "SMDC Separately Constituted",

                "2": "SMDC Not Constituted",

                "3": "Same as SMC",

                "9": "Not Applicable",

            }


    # -------------------------------------------------------
    # NEW SCHEMA: 2022-23 TO 2025-26
    # -------------------------------------------------------

    elif year in NEW_YEARS:

        codebook["balavatika_located_yn"] = (
            YES_NO.copy()
        )

        codebook["special_training"] = (
            YES_NO.copy()
        )

        codebook["material_training"] = (
            YES_NO.copy()
        )

        codebook["free_text_books_pr"] = (
            YES_NO.copy()
        )

        codebook["free_uniform_pr"] = (
            YES_NO.copy()
        )

        codebook["free_text_books_up"] = (
            YES_NO.copy()
        )

        codebook["free_uniform_up"] = (
            YES_NO.copy()
        )

        codebook["smc_exists"] = (
            YES_NO.copy()
        )

        codebook["smc_smdc_same"] = {

            "1": "SDMC Constituted",

            "2": "SDMC Not Constituted",

            "3": "Same as SMC",

        }

    else:

        raise ValueError(
            f"Unsupported academic year: {year}"
        )

    return codebook


# ===========================================================
# 8. NORMALIZE RAW CODES
# ===========================================================

def normalize_code(value):

    code = str(value or "").strip()

    if code.lower() in MISSING_VALUES:

        return ""

    # Convert integer-like codes:
    # 1.0 -> 1
    # 2.0 -> 2

    if re.fullmatch(r"\d+\.0+", code):

        code = code.split(".")[0]

    return code


# ===========================================================
# 9. READ CSV SAFELY
# ===========================================================

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
        f"Cannot decode CSV: {path}\n"
        f"Last error: {last_error}"
    )


# ===========================================================
# 10. DECODE FUNCTION
# ===========================================================

def decode_value(column, raw_value, codebook):

    code = normalize_code(raw_value)

    if not code:

        return (
            "MISSING",
            "MISSING"
        )

    mapping = codebook.get(column)

    if mapping is None:

        return (
            f"UNMAPPED_FIELD:{column}",
            "REVIEW_REQUIRED"
        )

    label = mapping.get(code)

    if label is None:

        return (
            f"UNMAPPED_CODE:{code}",
            "REVIEW_REQUIRED"
        )

    return (
        label,
        "MAPPED"
    )


# ===========================================================
# 11. SAVE REPORT FUNCTION
# ===========================================================

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
            lineterminator="\n"
        )

        writer.writeheader()

        writer.writerows(rows)


# ===========================================================
# 12. PROCESS ONE ACADEMIC YEAR
# ===========================================================

def process_year(year):

    # -------------------------------------------------------
    # INPUT FILE
    # -------------------------------------------------------

    input_path = (
        INPUT_DIR
        / f"maharashtra_profile2_{year}_standardized.csv"
    )

    if not input_path.exists():

        raise FileNotFoundError(input_path)


    # -------------------------------------------------------
    # VERSION 3 OUTPUT
    # -------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        OUTPUT_DIR
        / f"maharashtra_profile2_features_v3_{year}.csv"
    )

    temp_path = output_path.with_suffix(".tmp")


    # -------------------------------------------------------
    # YEAR-WISE CODEBOOK
    # -------------------------------------------------------

    codebook = get_year_codebook(year)

    decoded_columns = list(codebook)


    # -------------------------------------------------------
    # COUNTERS
    # -------------------------------------------------------

    value_counts = Counter()

    total_records = 0

    missing_count = 0

    review_count = 0


    # -------------------------------------------------------
    # READ INPUT CSV
    # -------------------------------------------------------

    handle, dialect = open_csv(input_path)

    try:

        reader = csv.DictReader(
            handle,
            dialect=dialect
        )

        headers = reader.fieldnames or []

        if not headers:

            raise ValueError(
                "Profile 2 CSV header is empty."
            )


        # ---------------------------------------------------
        # VALIDATE EXPECTED CATEGORICAL FIELDS
        # ---------------------------------------------------

        missing_fields = [

            column

            for column in decoded_columns

            if column not in headers

        ]

        if missing_fields:

            raise ValueError(
                f"{year}: Missing expected columns: "
                f"{missing_fields}"
            )


        # ---------------------------------------------------
        # CHECK EXISTING OUTPUT COLUMNS
        # ---------------------------------------------------

        new_columns = []

        for column in decoded_columns:

            new_columns.extend([

                f"{column}_label",

                f"{column}_label_status",

            ])

        duplicate_columns = [

            column

            for column in new_columns

            if column in headers

        ]

        if duplicate_columns:

            raise ValueError(
                f"Output columns already exist: "
                f"{duplicate_columns}"
            )


        # ---------------------------------------------------
        # FIND NUMERIC-LIKE OLD FIELDS PRESERVED
        # ---------------------------------------------------

        preserved_fields = [

            column

            for column in OLD_NUMERIC_FIELDS

            if year in OLD_YEARS
            and column in headers

        ]


        # ---------------------------------------------------
        # OUTPUT HEADER
        # ---------------------------------------------------

        output_fields = (
            headers + new_columns
        )


        # ---------------------------------------------------
        # PROCESS ROWS
        # ---------------------------------------------------

        with temp_path.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as output_file:

            writer = csv.DictWriter(
                output_file,
                fieldnames=output_fields,
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
                        f"Malformed CSV row: "
                        f"{record_number}"
                    )

                # Ignore completely blank rows.
                if not any(
                    str(value or "").strip()
                    for value in row.values()
                ):

                    continue

                total_records += 1

                # Preserve all original values.
                output_row = dict(row)


                # -------------------------------------------
                # DECODE CATEGORICAL FIELDS
                # -------------------------------------------

                for column in decoded_columns:

                    raw_value = str(
                        row.get(column, "") or ""
                    ).strip()

                    normalized = normalize_code(
                        raw_value
                    )

                    label, status = decode_value(
                        column,
                        raw_value,
                        codebook
                    )


                    # Add label and mapping status.
                    output_row[
                        f"{column}_label"
                    ] = label

                    output_row[
                        f"{column}_label_status"
                    ] = status


                    # Maintain value-level audit counts.
                    value_counts[

                        (
                            column,
                            raw_value,
                            normalized,
                            label,
                            status
                        )

                    ] += 1


                    if status == "MISSING":

                        missing_count += 1

                    elif status == "REVIEW_REQUIRED":

                        review_count += 1


                writer.writerow(output_row)


        # ---------------------------------------------------
        # REPLACE TEMP FILE AFTER SUCCESSFUL PROCESSING
        # ---------------------------------------------------

        temp_path.replace(output_path)

    except Exception:

        if temp_path.exists():

            temp_path.unlink()

        raise

    finally:

        handle.close()


    # =======================================================
    # 13. BUILD VALUE AUDIT REPORT
    # =======================================================

    value_results = []

    for key, count in value_counts.items():

        (
            column,
            raw_code,
            normalized_code,
            label,
            status
        ) = key

        value_results.append({

            "academic_year": year,

            "source_column": column,

            "raw_code": raw_code,

            "normalized_code": normalized_code,

            "decoded_label": label,

            "school_count": count,

            "status": status,

        })


    # =======================================================
    # 14. YEAR-WISE STATUS
    # =======================================================

    if review_count > 0:

        year_status = "PASS_WITH_REVIEW"

    else:

        year_status = "PASS"


    summary = {

        "academic_year": year,

        "total_records": total_records,

        "categorical_columns_decoded": len(
            decoded_columns
        ),

        "numeric_like_fields_preserved": len(
            preserved_fields
        ),

        "missing_values": missing_count,

        "review_required_values": review_count,

        "output_file": str(
            output_path.relative_to(ROOT)
        ),

        "status": year_status,

    }

    return (
        summary,
        value_results
    )


# ===========================================================
# 15. MAIN FUNCTION
# ===========================================================

def main():

    print(
        "\nSHALASCOPE - PROFILE 2 CATEGORICAL DECODER V3"
    )

    print("=" * 75)

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    summaries = []

    all_values = []


    # -------------------------------------------------------
    # PROCESS ALL YEARS
    # -------------------------------------------------------

    for index, year in enumerate(YEARS, 1):

        print(
            f"\n[{index}/8] {year}"
        )

        if year in OLD_YEARS:

            print(
                "Schema: OLD"
            )

            print(
                "Code 9: Not Applicable "
                "(documented in old DSP Schema)"
            )

        else:

            print(
                "Schema: NEW"
            )

            print(
                "Codes 0 and 9: Review unless verified"
            )

        try:

            summary, values = process_year(year)

            summaries.append(summary)

            all_values.extend(values)


            print(
                f"Records: "
                f"{summary['total_records']:,}"
            )

            print(
                f"Categorical Columns: "
                f"{summary['categorical_columns_decoded']}"
            )

            print(
                f"Numeric-like Fields Preserved: "
                f"{summary['numeric_like_fields_preserved']}"
            )

            print(
                f"Missing Values: "
                f"{summary['missing_values']}"
            )

            print(
                f"Review Required: "
                f"{summary['review_required_values']}"
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

                "numeric_like_fields_preserved": 0,

                "missing_values": 0,

                "review_required_values": 0,

                "output_file": "",

                "status": "FAILED",

            })


    # =======================================================
    # 16. SAVE VALUE AUDIT REPORT
    # =======================================================

    save_report(

        VALUE_REPORT,

        all_values,

        [

            "academic_year",

            "source_column",

            "raw_code",

            "normalized_code",

            "decoded_label",

            "school_count",

            "status",

        ]

    )


    # =======================================================
    # 17. SAVE SUMMARY REPORT
    # =======================================================

    save_report(

        SUMMARY_REPORT,

        summaries,

        [

            "academic_year",

            "total_records",

            "categorical_columns_decoded",

            "numeric_like_fields_preserved",

            "missing_values",

            "review_required_values",

            "output_file",

            "status",

        ]

    )


    # =======================================================
    # 18. FINAL SUMMARY
    # =======================================================

    passed = sum(

        row["status"] == "PASS"

        for row in summaries

    )

    review = sum(

        row["status"] == "PASS_WITH_REVIEW"

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

    total_review = sum(

        row["review_required_values"]

        for row in summaries

    )


    print("\n" + "=" * 75)

    print(
        "PROFILE 2 DECODER V3 FINAL SUMMARY"
    )

    print("=" * 75)

    print(
        f"Academic Years: {len(summaries)}"
    )

    print(
        f"Total Records: {total_records:,}"
    )

    print(
        f"PASS: {passed}"
    )

    print(
        f"PASS WITH REVIEW: {review}"
    )

    print(
        f"FAILED: {failed}"
    )

    print(
        f"Review Required Values: {total_review:,}"
    )


    print("\nOUTPUT FOLDER")

    print(OUTPUT_DIR)


    print("\nREPORTS CREATED")

    print(VALUE_REPORT)

    print(SUMMARY_REPORT)


    print(
        "\nPROFILE 2 CATEGORICAL DECODER V3 COMPLETED"
    )


# ===========================================================
# 19. ENTRY POINT
# ===========================================================

if __name__ == "__main__":

    main()
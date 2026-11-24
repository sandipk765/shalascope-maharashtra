
"""
ShalaScope Maharashtra
Common Teacher Feature Builder

Years: 2018-19 to 2025-26

Creates one standardized teacher feature dataset
for each school and academic year.

Original master CSV files are never modified.
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

MASTER_DIR = ROOT / "data" / "processed" / "school_year"

OUTPUT_DIR = (
    ROOT
    / "data"
    / "processed"
    / "school_year_features"
    / "teacher"
)

REPORT_DIR = ROOT / "reports" / "data_audit"

SUMMARY_REPORT = (
    REPORT_DIR / "teacher_common_features_audit.csv"
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


# ==================================================
# 2. COMMON TEACHER FEATURE MAPPING
# ==================================================

FEATURE_MAP = {

    "total_teachers": [
        "total_teacher",
        "total_tch",
    ],

    "male_teachers": [
        "male",
    ],

    "female_teachers": [
        "female",
    ],

    "transgender_teachers": [
        "transgender",
    ],

    "regular_teachers": [
        "regular",
    ],

    "contract_teachers": [
        "contract",
    ],

    "part_time_teachers": [
        "part_time",
    ],

    "below_graduate_teachers": [
        "below_graduate",
    ],

    "graduate_teachers": [
        "graduate",
    ],

    "postgraduate_and_above_teachers": [
        "post_graduate_and_above",
    ],

    "computer_trained_teachers": [
        "total_teacher_trained_computer",
        "trained_comp",
    ],

    "primary_teachers": [
        "class_taught_pr",
    ],

    "upper_primary_teachers": [
        "class_taught_upr",
    ],

    "primary_upper_primary_teachers": [
        "class_taught_pr_upr",
    ],

    "secondary_only_teachers": [
        "class_taught_sec_only",
    ],

    "higher_secondary_only_teachers": [
        "class_taught_hsec_only",
    ],

    "upper_primary_secondary_teachers": [
        "class_taught_upr_sec",
    ],

    "secondary_higher_secondary_teachers": [
        "class_taught_sec_hsec",
    ],

    "pre_primary_only_teachers": [
        "class_taugt_pre_primary_only",
    ],

    "pre_primary_primary_teachers": [
        "class_taught_pr_and_pre_pri",
    ],

    "teachers_non_training_assignment": [
        "teacher_involve_non_training_assignment",
    ],

    "diploma_certificate_teachers": [
        "diploma_certificate",
    ],

    "bachelor_elementary_education_teachers": [
        "bachelor_of_ee",
    ],

    "bed_equivalent_teachers": [
        "bed_equivalent",
    ],

    "med_equivalent_teachers": [
        "med_equivalent",
    ],

    "other_professional_qualification_teachers": [
        "other",
    ],

    "no_professional_qualification_teachers": [
        "none",
    ],

    "special_education_diploma_teachers": [
        "diploma_special_edu",
    ],

    "teachers_pursuing_professional_course": [
        "pursuing_rpc",
    ],

}


# ==================================================
# 3. HELPERS
# ==================================================

def norm(value):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


def parse_count(value, column, school_id):

    text = str(value or "").strip()

    if text.lower() in MISSING_VALUES:

        raise ValueError(
            f"Missing value in {column}; School ID={school_id}"
        )

    try:

        number = Decimal(
            text.replace(",", "")
        )

        if not number.is_finite():

            raise ValueError(
                f"Invalid numeric value in {column}: {text}"
            )

        if number < 0:

            raise ValueError(
                f"Negative value in {column}: {text}"
            )

        if number != number.to_integral_value():

            raise ValueError(
                f"Fractional teacher count in {column}: {text}"
            )

        return number

    except InvalidOperation:

        raise ValueError(
            f"Non-numeric value in {column}: {text}"
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
        f"Cannot decode {path}: {last_error}"
    )


def resolve_feature_columns(headers):

    lookup = {
        norm(header): header
        for header in headers
    }

    resolved = {}

    for feature, aliases in FEATURE_MAP.items():

        found = next(
            (
                lookup[norm(alias)]
                for alias in aliases
                if norm(alias) in lookup
            ),
            None
        )

        if found is None:

            raise ValueError(
                f"Feature '{feature}' not found. "
                f"Expected one of: {aliases}"
            )

        resolved[feature] = found

    return resolved


def csv_writer(file, fields):

    writer = csv.DictWriter(
        file,
        fieldnames=fields,
        delimiter=",",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        doublequote=True,
        lineterminator="\n"
    )

    return writer


# ==================================================
# 4. PROCESS ONE MASTER FILE
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
        / f"maharashtra_teacher_features_{year}.csv"
    )

    temp_path = output_path.with_suffix(".tmp")

    handle, dialect = open_csv(input_path)

    total_records = 0
    unique_ids = set()

    total_teachers_sum = Decimal("0")
    computer_trained_sum = Decimal("0")

    gender_mismatches = 0
    computer_over_total = 0

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        if not headers:

            raise ValueError(
                f"Empty master file: {input_path}"
            )

        normalized_headers = [
            norm(header)
            for header in headers
        ]

        id_index = normalized_headers.index("schoolid")
        district_index = normalized_headers.index("district")
        raw_index = normalized_headers.index("districtraw")

        year_index = normalized_headers.index("academicyear")

        feature_columns = resolve_feature_columns(headers)

        output_fields = [

            "academic_year",
            "school_id",
            "district",
            "district_raw",

            *FEATURE_MAP.keys(),

            "female_teacher_share_pct",
            "computer_trained_teacher_share_pct",
            "regular_teacher_share_pct",

            "gender_consistency_flag",
            "computer_training_count_valid_flag",

        ]

        with temp_path.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as output_file:

            writer = csv_writer(
                output_file,
                output_fields
            )

            writer.writeheader()

            for record_number, row in enumerate(reader, start=2):

                if not row or all(
                    not str(value).strip()
                    for value in row
                ):
                    continue

                if len(row) != len(headers):

                    raise ValueError(
                        f"Malformed master row {record_number} "
                        f"in {year}."
                    )

                total_records += 1

                school_id = str(
                    row[id_index]
                ).strip()

                district = str(
                    row[district_index]
                ).strip().upper()

                district_raw = str(
                    row[raw_index]
                ).strip().upper()

                actual_year = str(
                    row[year_index]
                ).strip()

                if not school_id:

                    raise ValueError(
                        f"Missing School ID in {year}."
                    )

                if school_id in unique_ids:

                    raise ValueError(
                        f"Duplicate School ID: {school_id}"
                    )

                unique_ids.add(school_id)

                if actual_year != year:

                    raise ValueError(
                        f"Wrong academic year at record "
                        f"{record_number}."
                    )

                if not district or not district_raw:

                    raise ValueError(
                        f"Missing district for {school_id}."
                    )

                # --------------------------------------
                # EXTRACT COMMON FEATURES
                # --------------------------------------

                features = {}

                for feature, source_column in (
                    feature_columns.items()
                ):

                    source_index = headers.index(
                        source_column
                    )

                    features[feature] = parse_count(
                        row[source_index],
                        source_column,
                        school_id
                    )

                total = features["total_teachers"]

                male = features["male_teachers"]
                female = features["female_teachers"]
                transgender = features["transgender_teachers"]

                computer = features["computer_trained_teachers"]

                regular = features["regular_teachers"]

                # --------------------------------------
                # QUALITY FLAGS
                # --------------------------------------

                gender_valid = (
                    male + female + transgender == total
                )

                computer_valid = (
                    computer <= total
                )

                if not gender_valid:
                    gender_mismatches += 1

                if not computer_valid:
                    computer_over_total += 1

                if total > 0:

                    female_share = round(
                        float(female / total * Decimal("100")),
                        2
                    )

                    computer_share = round(
                        float(computer / total * Decimal("100")),
                        2
                    )

                    regular_share = round(
                        float(regular / total * Decimal("100")),
                        2
                    )

                else:

                    female_share = ""
                    computer_share = ""
                    regular_share = ""

                output_row = {

                    "academic_year": year,
                    "school_id": school_id,
                    "district": district,
                    "district_raw": district_raw,

                }

                for feature, value in features.items():

                    output_row[feature] = str(value)

                output_row.update({

                    "female_teacher_share_pct": female_share,

                    "computer_trained_teacher_share_pct": (
                        computer_share
                    ),

                    "regular_teacher_share_pct": regular_share,

                    "gender_consistency_flag": (
                        "PASS" if gender_valid else "REVIEW"
                    ),

                    "computer_training_count_valid_flag": (
                        "PASS" if computer_valid else "REVIEW"
                    ),

                })

                writer.writerow(output_row)

                total_teachers_sum += total
                computer_trained_sum += computer

        if total_records != len(unique_ids):

            raise ValueError(
                f"Record count and unique ID count differ for {year}."
            )

        # --------------------------------------
        # YEAR SUMMARY
        # --------------------------------------

        computer_ratio = (

            round(
                float(
                    computer_trained_sum
                    / total_teachers_sum
                    * Decimal("100")
                ),
                2
            )

            if total_teachers_sum > 0
            else 0

        )

        status = (
            "PASS"
            if gender_mismatches == 0
            and computer_over_total == 0
            else "REVIEW_REQUIRED"
        )

        if status != "PASS":

            raise ValueError(
                f"Semantic validation failed for {year}."
            )

        # Save final output after validation.
        temp_path.replace(output_path)

        return {

            "academic_year": year,
            "records": total_records,
            "unique_school_ids": len(unique_ids),

            "total_teachers": str(total_teachers_sum),

            "computer_trained_teachers": str(
                computer_trained_sum
            ),

            "computer_training_share_pct": computer_ratio,

            "gender_mismatches": gender_mismatches,
            "computer_over_total": computer_over_total,

            "output_file": str(
                output_path.relative_to(ROOT)
            ),

            "status": status,

        }

    except Exception:

        if temp_path.exists():
            temp_path.unlink()

        raise

    finally:

        handle.close()


# ==================================================
# 5. SAVE SUMMARY
# ==================================================

def save_report(path, rows):

    if not rows:
        return

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys())
        )

        writer.writeheader()
        writer.writerows(rows)


# ==================================================
# 6. MAIN
# ==================================================

def main():

    print("\nSHALASCOPE - COMMON TEACHER FEATURE BUILDER")
    print("=" * 75)

    if not MASTER_DIR.exists():
        raise FileNotFoundError(MASTER_DIR)

    summaries = []

    for index, year in enumerate(YEARS, 1):

        print(
            f"\n[{index}/{len(YEARS)}] {year}"
        )

        try:

            result = process_year(year)

            summaries.append(result)

            print(
                f"Records: {result['records']:,}"
            )

            print(
                f"Unique School IDs: "
                f"{result['unique_school_ids']:,}"
            )

            print(
                f"Total Teachers: "
                f"{result['total_teachers']}"
            )

            print(
                f"Computer-Trained Teachers: "
                f"{result['computer_trained_teachers']}"
            )

            print(
                f"Computer Training Share: "
                f"{result['computer_training_share_pct']}%"
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
                f"STATUS: {result['status']}"
            )

            print(
                f"Output: {result['output_file']}"
            )

        except Exception as error:

            print(f"ERROR: {error}")

            summaries.append({

                "academic_year": year,
                "records": 0,
                "unique_school_ids": 0,
                "total_teachers": "",
                "computer_trained_teachers": "",
                "computer_training_share_pct": 0,
                "gender_mismatches": 0,
                "computer_over_total": 0,
                "output_file": "",
                "status": "FAILED",

            })

    # ------------------------------------------
    # SAVE AUDIT
    # ------------------------------------------

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    save_report(
        SUMMARY_REPORT,
        summaries
    )

    # ------------------------------------------
    # FINAL SUMMARY
    # ------------------------------------------

    passed = sum(
        row["status"] == "PASS"
        for row in summaries
    )

    failed = sum(
        row["status"] == "FAILED"
        for row in summaries
    )

    total_records = sum(
        row["records"]
        for row in summaries
    )

    print("\n" + "=" * 75)
    print("FINAL COMMON TEACHER FEATURE SUMMARY")
    print("=" * 75)

    print(f"Academic Years: {len(summaries)}")
    print(f"Total Records: {total_records:,}")
    print(f"PASS: {passed}")
    print(f"Failed: {failed}")

    print("\nOUTPUT FOLDER")
    print(OUTPUT_DIR)

    print("\nAUDIT REPORT")
    print(SUMMARY_REPORT)

    print("\nCOMMON TEACHER FEATURE BUILD COMPLETED")


if __name__ == "__main__":
    main()

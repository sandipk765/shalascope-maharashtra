
from pathlib import Path
import re
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=RuntimeWarning)

# =========================================================
# 1. PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = PROJECT_ROOT / "data" / "processed" / "school_year"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "school_year_features"
    / "numeric"
)

REPORT_DIR = PROJECT_ROOT / "reports" / "data_audit"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

INPUT_PATTERN = "maharashtra_school_year_master_*.csv"

# =========================================================
# 2. AUDIT STORAGE
# =========================================================

field_audits = []
year_summaries = []
feature_manifests = []


def log_field_audit(
    year,
    source,
    feature,
    status,
    row_count=0,
    nonblank=0,
    missing=0,
    invalid=0,
    negative=0,
    minimum=None,
    maximum=None,
):
    field_audits.append({
        "academic_year": year,
        "source_column": source,
        "output_feature": feature,
        "status": status,
        "rows": row_count,
        "nonblank_values": nonblank,
        "missing_values": missing,
        "invalid_numeric_values": invalid,
        "negative_values": negative,
        "minimum": minimum,
        "maximum": maximum,
    })


# =========================================================
# 3. NUMERIC CONVERSION
# =========================================================

def add_numeric_feature(
    df,
    output,
    year,
    source,
    target,
    nonnegative=False,
):
    if source not in df.columns:

        log_field_audit(
            year,
            source,
            target,
            "NOT_AVAILABLE_IN_SOURCE_SCHEMA",
            row_count=len(df),
        )

        return None

    raw = df[source]

    text_values = raw.astype("string").str.strip()

    cleaned_values = text_values.str.replace(
        ",", "", regex=False
    )

    numeric = pd.to_numeric(
        cleaned_values,
        errors="coerce",
    )

    blank = (
        text_values.isna()
        | text_values.eq("").fillna(False)
    )

    invalid_mask = (~blank) & numeric.isna()

    negative_mask = numeric.lt(0).fillna(False)

    invalid_count = int(invalid_mask.sum())
    negative_count = int(negative_mask.sum())

    if nonnegative:
        numeric = numeric.mask(negative_mask)

    output[target] = numeric

    valid_values = numeric.dropna()

    minimum = (
        float(valid_values.min())
        if len(valid_values) else None
    )

    maximum = (
        float(valid_values.max())
        if len(valid_values) else None
    )

    status = "PASS"

    if invalid_count > 0 or (
        nonnegative and negative_count > 0
    ):
        status = "PASS_WITH_VALUE_REVIEW"

    log_field_audit(
        year=year,
        source=source,
        feature=target,
        status=status,
        row_count=len(df),
        nonblank=int((~blank).sum()),
        missing=int(blank.sum()),
        invalid=invalid_count,
        negative=negative_count,
        minimum=minimum,
        maximum=maximum,
    )

    return numeric


# =========================================================
# 4. STRICT SUM
# =========================================================

def strict_sum(series_list):
    """
    A total is generated only when every included
    source value is available for that row.
    No missing-value imputation is performed.
    """

    if not series_list:
        return None

    if len(series_list) == 1:
        return series_list[0]

    combined = pd.concat(series_list, axis=1)

    return combined.sum(
        axis=1,
        min_count=len(series_list),
    )


# =========================================================
# 5. SAFE PERCENTAGE
# =========================================================

def safe_percentage(numerator, denominator):

    if numerator is None or denominator is None:
        return None

    valid_denominator = denominator.where(
        denominator > 0
    )

    result = (
        numerator / valid_denominator
    ) * 100

    return result.round(3)


# =========================================================
# 6. YEAR DETECTION
# =========================================================

def detect_year(file_path, df):

    if "academic_year" in df.columns:

        values = (
            df["academic_year"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        if not values.empty:
            return values.iloc[0]

    match = re.search(
        r"(20\d{2})[-_](\d{2})",
        file_path.stem,
    )

    if match:
        return f"{match.group(1)}-{match.group(2)}"

    raise ValueError(
        f"Cannot determine academic year: {file_path.name}"
    )


# =========================================================
# 7. PROCESS ONE YEAR
# =========================================================

def process_year(file_path):

    print("\n" + "=" * 65)
    print(f"PROCESSING: {file_path.name}")
    print("=" * 65)

    df = pd.read_csv(
        file_path,
        dtype={"school_id": "string"},
        low_memory=False,
    )

    year = detect_year(file_path, df)

    if "school_id" not in df.columns:
        raise ValueError(
            f"{year}: school_id column missing"
        )

    if "district" not in df.columns:
        raise ValueError(
            f"{year}: district column missing"
        )

    original_rows = len(df)

    school_ids = df["school_id"].astype("string").str.strip()

    districts = df["district"].astype("string").str.strip()

    duplicate_ids = int(school_ids.duplicated().sum())

    missing_ids = int(
        school_ids.isna().sum()
        + school_ids.eq("").fillna(False).sum()
    )

    missing_districts = int(
        districts.isna().sum()
        + districts.eq("").fillna(False).sum()
    )

    output = pd.DataFrame({
        "academic_year": year,
        "school_id": school_ids,
        "district": districts,
    })

    # -----------------------------------------------------
    # SCHOOL PROFILE NUMERIC FEATURES
    # -----------------------------------------------------

    profile_fields = [
        ("school_establishment_year",
         "year_of_establishment", False),

        ("anganwadi_boys_count",
         "anganwadi_boys", True),

        ("anganwadi_girls_count",
         "anganwadi_girls", True),

        ("instruction_days_primary",
         "instr_days_pr", True),

        ("instruction_days_upper_primary",
         "instr_days_up", True),

        ("instruction_days_secondary",
         "instr_days_sec", True),

        ("instruction_days_higher_secondary",
         "instr_days_hsec", True),

        ("avg_student_hours_primary",
         "avg_school_hrs_student_pr", True),

        ("avg_student_hours_upper_primary",
         "avg_school_hrs_student_up", True),

        ("avg_student_hours_secondary",
         "avg_school_hrs_student_sec", True),

        ("avg_student_hours_higher_secondary",
         "avg_school_hrs_student_hsec", True),

        ("avg_teacher_hours_primary",
         "avg_school_hrs_teacher_pr", True),

        ("avg_teacher_hours_upper_primary",
         "avg_school_hrs_teacher_up", True),

        ("avg_teacher_hours_secondary",
         "avg_school_hrs_teacher_sec", True),

        ("avg_teacher_hours_higher_secondary",
         "avg_school_hrs_teacher_hsec", True),
    ]

    profile_cache = {}

    for target, source, nonnegative in profile_fields:

        values = add_numeric_feature(
            df, output, year,
            source, target, nonnegative
        )

        profile_cache[source] = values

    # School age: only valid establishment years are used.
    establishment = profile_cache.get(
        "year_of_establishment"
    )

    start_year = int(year[:4])

    if establishment is not None:

        valid_establishment = establishment.between(
            1800, start_year
        )

        school_age = (
            start_year - establishment
        ).where(valid_establishment)

        output["school_age_years"] = school_age

        invalid_establishment = int(
            (establishment.notna()
             & ~valid_establishment).sum()
        )

        log_field_audit(
            year,
            "year_of_establishment",
            "school_age_years",
            (
                "PASS"
                if invalid_establishment == 0
                else "PASS_WITH_VALUE_REVIEW"
            ),
            row_count=len(df),
            nonblank=int(establishment.notna().sum()),
            missing=int(school_age.isna().sum()),
            invalid=invalid_establishment,
            minimum=(
                float(school_age.min())
                if school_age.notna().any()
                else None
            ),
            maximum=(
                float(school_age.max())
                if school_age.notna().any()
                else None
            ),
        )

    anganwadi_boys = profile_cache.get("anganwadi_boys")
    anganwadi_girls = profile_cache.get("anganwadi_girls")

    if anganwadi_boys is not None and anganwadi_girls is not None:

        output["anganwadi_children_total"] = strict_sum([
            anganwadi_boys,
            anganwadi_girls,
        ])

    # -----------------------------------------------------
    # PROFILE 2 NUMERIC COUNTS AND GRANTS
    # -----------------------------------------------------

    profile2_fields = [
        ("academic_inspections_count",
         "acad_inspections", True),

        ("crc_coordinator_visits_count",
         "crc_coordinator", True),

        ("block_officer_visits_count",
         "block_level_officers", True),

        ("district_officer_visits_count",
         "district_officers", True),

        ("grant_receipt_amount",
         "grants_receipt", False),

        ("grant_expenditure_amount",
         "grants_expenditure", False),

        ("free_textbooks_primary_count",
         "free_text_books_pr", True),

        ("transport_primary_count",
         "transport_pr", True),

        ("free_uniform_primary_count",
         "free_uniform_pr", True),

        ("free_textbooks_upper_primary_count",
         "free_text_books_up", True),

        ("transport_upper_primary_count",
         "transport_up", True),

        ("free_uniform_upper_primary_count",
         "free_uniform_up", True),
    ]

    profile2_cache = {}

    for target, source, nonnegative in profile2_fields:

        values = add_numeric_feature(
            df, output, year,
            source, target, nonnegative
        )

        profile2_cache[source] = values

    # Financial difference. Both source values must exist.
    grant_receipt = profile2_cache.get("grants_receipt")
    grant_expenditure = profile2_cache.get("grants_expenditure")

    if (
        grant_receipt is not None
        and grant_expenditure is not None
    ):

        output["grant_net_amount"] = (
            grant_receipt - grant_expenditure
        )

    # Stage-wise beneficiary totals.
    benefit_groups = [
        (
            "free_textbooks_beneficiaries_total",
            "free_text_books_pr",
            "free_text_books_up",
        ),
        (
            "transport_beneficiaries_total",
            "transport_pr",
            "transport_up",
        ),
        (
            "free_uniform_beneficiaries_total",
            "free_uniform_pr",
            "free_uniform_up",
        ),
    ]

    for target, first_source, second_source in benefit_groups:

        first = profile2_cache.get(first_source)
        second = profile2_cache.get(second_source)

        if first is not None and second is not None:

            output[target] = strict_sum([
                first,
                second,
            ])

    # -----------------------------------------------------
    # RTE STUDENT COUNTS
    # -----------------------------------------------------

    rte_groups = {
        "rte_private": re.compile(r"^rte_pvt_c\d+_[bg]$"),
        "rte_ews": re.compile(r"^rte_ews_c\d+_[bg]$"),
    }

    rte_totals = {}

    for group_name, pattern in rte_groups.items():

        columns = sorted([
            col for col in df.columns
            if pattern.fullmatch(str(col))
        ])

        series_list = []

        for source in columns:

            target = f"{source}_count"

            values = add_numeric_feature(
                df,
                output,
                year,
                source,
                target,
                nonnegative=True,
            )

            if values is not None:
                series_list.append(values)

        if series_list:

            total_name = f"{group_name}_total_students"

            output[total_name] = strict_sum(
                series_list
            )

            rte_totals[group_name] = output[total_name]

            feature_manifests.append({
                "academic_year": year,
                "feature": total_name,
                "source_columns_used": len(series_list),
                "status": "CREATED",
            })

        else:

            log_field_audit(
                year,
                f"{group_name}_column_pattern",
                f"{group_name}_total_students",
                "NOT_AVAILABLE_IN_SOURCE_SCHEMA",
                row_count=len(df),
            )

    if (
        "rte_private" in rte_totals
        and "rte_ews" in rte_totals
    ):

        output["rte_total_admissions_students"] = strict_sum([
            rte_totals["rte_private"],
            rte_totals["rte_ews"],
        ])

    # -----------------------------------------------------
    # TEACHER NUMERIC FEATURES
    # -----------------------------------------------------

    teacher_fields = [
        ("teacher_total", "total_teacher"),

        ("male_teachers", "male"),

        ("female_teachers", "female"),

        ("transgender_teachers", "transgender"),

        ("regular_teachers", "regular"),

        ("contract_teachers", "contract"),

        ("part_time_teachers", "part_time"),

        ("below_graduate_teachers", "below_graduate"),

        ("graduate_teachers", "graduate"),

        ("postgraduate_teachers",
         "post_graduate_and_above"),

        ("computer_trained_teachers",
         "total_teacher_trained_computer"),

        ("teachers_aged_above_55",
         "teachers_aged_above_55"),

        ("teachers_received_service_training",
         "teacher_received_service_training"),

        ("teachers_non_training_assignment",
         "teacher_involve_non_training_assignment"),

        ("diploma_certificate_teachers",
         "diploma_certificate"),

        ("bachelor_of_education_teachers",
         "bachelor_of_ee"),

        ("b_ed_equivalent_teachers",
         "bed_equivalent"),

        ("m_ed_equivalent_teachers",
         "med_equivalent"),

        ("other_qualification_teachers",
         "other"),

        ("no_qualification_teachers",
         "none"),

        ("special_education_diploma_teachers",
         "diploma_special_edu"),

        ("teachers_pursuing_rpc",
         "pursuing_rpc"),
    ]

    teacher_cache = {}

    for target, source in teacher_fields:

        values = add_numeric_feature(
            df,
            output,
            year,
            source,
            target,
            nonnegative=True,
        )

        teacher_cache[source] = values

    # Class allocation counts.
    class_fields = [
        "class_taught_pr",
        "class_taught_upr",
        "class_taught_pr_upr",
        "class_taught_sec_only",
        "class_taught_hsec_only",
        "class_taught_upr_sec",
        "class_taught_sec_hsec",
        "class_taugt_pre_primary_only",
        "class_taught_pr_and_pre_pri",
    ]

    for source in class_fields:

        add_numeric_feature(
            df,
            output,
            year,
            source,
            f"{source}_count",
            nonnegative=True,
        )

    # -----------------------------------------------------
    # TEACHER PERCENTAGES
    # -----------------------------------------------------

    total_teachers = teacher_cache.get("total_teacher")

    percentage_pairs = [
        ("male_teacher_pct", "male"),
        ("female_teacher_pct", "female"),
        ("transgender_teacher_pct", "transgender"),
        ("regular_teacher_pct", "regular"),
        ("contract_teacher_pct", "contract"),
        ("part_time_teacher_pct", "part_time"),
        ("computer_trained_teacher_pct",
         "total_teacher_trained_computer"),
        ("teachers_above_55_pct",
         "teachers_aged_above_55"),
        ("below_graduate_teacher_pct",
         "below_graduate"),
        ("graduate_teacher_pct", "graduate"),
        ("postgraduate_teacher_pct",
         "post_graduate_and_above"),
    ]

    if total_teachers is not None:

        for target, source in percentage_pairs:

            numerator = teacher_cache.get(source)

            if numerator is not None:

                output[target] = safe_percentage(
                    numerator,
                    total_teachers,
                )

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    percentage_columns = [
        col for col in output.columns
        if col.endswith("_pct")
    ]

    percentage_errors = 0

    for col in percentage_columns:

        invalid_share = (
            output[col].notna()
            & ~output[col].between(0, 100)
        )

        percentage_errors += int(
            invalid_share.sum()
        )

    output_path = (
        OUTPUT_DIR
        / f"maharashtra_numeric_features_{year}.csv"
    )

    output.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    unique_ids = int(school_ids.nunique(dropna=True))

    if (
        missing_ids > 0
        or missing_districts > 0
        or duplicate_ids > 0
        or percentage_errors > 0
    ):
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    year_summaries.append({
        "academic_year": year,
        "input_file": file_path.name,
        "output_file": output_path.name,
        "rows": original_rows,
        "unique_school_ids": unique_ids,
        "district_count": int(districts.nunique(dropna=True)),
        "feature_columns": len(output.columns) - 3,
        "missing_school_ids": missing_ids,
        "duplicate_school_ids": duplicate_ids,
        "missing_districts": missing_districts,
        "invalid_percentage_values": percentage_errors,
        "status": status,
    })

    print(f"Academic Year       : {year}")
    print(f"Input Rows          : {original_rows:,}")
    print(f"Unique School IDs   : {unique_ids:,}")
    print(f"Districts           : {districts.nunique():,}")
    print(f"Output Features     : {len(output.columns) - 3}")
    print(f"Duplicate IDs       : {duplicate_ids}")
    print(f"Missing IDs         : {missing_ids}")
    print(f"Missing Districts   : {missing_districts}")
    print(f"Percentage Errors   : {percentage_errors}")
    print(f"Output              : {output_path}")
    print(f"STATUS              : {status}")

    return output_path


# =========================================================
# 8. MAIN
# =========================================================

def main():

    print("\n" + "=" * 70)
    print("SHALASCOPE MAHARASHTRA")
    print("NUMERIC FEATURE ENGINEERING")
    print("=" * 70)

    files = sorted(
        INPUT_DIR.glob(INPUT_PATTERN)
    )

    if not files:

        raise FileNotFoundError(
            f"No master CSV files found in: {INPUT_DIR}"
        )

    print(f"\nMaster CSV files found: {len(files)}")

    processed = 0
    failed = []

    for file_path in files:

        try:
            process_year(file_path)
            processed += 1

        except Exception as exc:

            failed.append({
                "file": file_path.name,
                "error": str(exc),
            })

            print(
                f"\nPROCESSING FAILED: {file_path.name}",
                file=sys.stderr,
            )

            print(str(exc), file=sys.stderr)

    # -----------------------------------------------------
    # SAVE AUDIT REPORTS
    # -----------------------------------------------------

    field_audit_df = pd.DataFrame(field_audits)
    summary_df = pd.DataFrame(year_summaries)
    manifest_df = pd.DataFrame(feature_manifests)

    field_audit_path = (
        REPORT_DIR
        / "numeric_feature_field_audit.csv"
    )

    summary_path = (
        REPORT_DIR
        / "numeric_feature_engineering_summary.csv"
    )

    manifest_path = (
        REPORT_DIR
        / "numeric_feature_manifest.csv"
    )

    field_audit_df.to_csv(
        field_audit_path,
        index=False,
        encoding="utf-8-sig",
    )

    summary_df.to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    manifest_df.to_csv(
        manifest_path,
        index=False,
        encoding="utf-8-sig",
    )

    # -----------------------------------------------------
    # FINAL SUMMARY
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("FINAL NUMERIC FEATURE ENGINEERING SUMMARY")
    print("=" * 70)

    print(f"Files Found       : {len(files)}")
    print(f"Files Processed   : {processed}")
    print(f"Files Failed      : {len(failed)}")

    if not summary_df.empty:

        print(
            "\n"
            + summary_df.to_string(index=False)
        )

        total_rows = int(summary_df["rows"].sum())

        total_unique = int(
            summary_df["unique_school_ids"].sum()
        )

        print(f"\nTotal School-Year Rows: {total_rows:,}")
        print(f"Total Unique IDs Across Years: {total_unique:,}")

    print("\nAudit Reports:")
    print(field_audit_path)
    print(summary_path)
    print(manifest_path)

    if failed:

        failure_path = (
            REPORT_DIR
            / "numeric_feature_engineering_failures.csv"
        )

        pd.DataFrame(failed).to_csv(
            failure_path,
            index=False,
            encoding="utf-8-sig",
        )

        print("\nFAILED FILES:")
        for item in failed:
            print(item["file"], ":", item["error"])

        print("\nFINAL STATUS: REVIEW REQUIRED")

    elif processed == len(files):

        print("\nFINAL STATUS: PROCESSING PASS")

    print("\nNUMERIC FEATURE ENGINEERING COMPLETED")


if __name__ == "__main__":
    main()

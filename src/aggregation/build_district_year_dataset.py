
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

# ============================================================
# SHALASCOPE MAHARASHTRA - DISTRICT YEAR DATASET
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    ROOT / "data" / "processed"
    / "school_year_features" / "numeric"
)

OUTPUT_DIR = ROOT / "data" / "processed" / "district_year"
REPORT_DIR = ROOT / "reports" / "data_audit"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_YEARS = 8
EXPECTED_DISTRICTS = 36

SUMMARIES = []
COVERAGE = []
ALL_DISTRICT_DATA = []


# ============================================================
# 1. AGGREGATION METHOD
# ============================================================

def get_method(column):

    # Percentages are school-level ratios.
    if column.endswith("_pct"):
        return "MEAN_SCHOOL_PERCENTAGE"

    # These are average or time-related measurements.
    if (
        column in {
            "school_age_years",
            "school_establishment_year",
        }
        or column.startswith("avg_student_hours_")
        or column.startswith("avg_teacher_hours_")
        or column.startswith("instruction_days_")
    ):
        return "MEAN"

    # Counts, teacher numbers, beneficiaries and money amounts.
    return "SUM_AND_MEAN"


# ============================================================
# 2. YEAR DETECTION
# ============================================================

def get_year(df, path):

    if "academic_year" in df.columns:

        years = (
            df["academic_year"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

        if len(years) == 1:
            return years[0]

        raise ValueError(
            f"Unexpected academic_year values in {path.name}: {years}"
        )

    match = re.search(
        r"(20\d{2}-\d{2})",
        path.name,
    )

    if match:
        return match.group(1)

    raise ValueError(
        f"Academic year not found: {path.name}"
    )


# ============================================================
# 3. PROCESS ONE YEAR
# ============================================================

def process_file(path):

    print("\n" + "=" * 65)
    print(f"PROCESSING: {path.name}")
    print("=" * 65)

    df = pd.read_csv(
        path,
        dtype={"school_id": "string"},
        low_memory=False,
    )

    year = get_year(df, path)

    required = [
        "academic_year",
        "school_id",
        "district",
    ]

    missing_columns = [
        col for col in required
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    df["academic_year"] = year
    df["school_id"] = df["school_id"].str.strip()
    df["district"] = df["district"].astype("string").str.strip()

    rows = len(df)

    missing_ids = int(
        df["school_id"].isna().sum()
        + df["school_id"].eq("").fillna(False).sum()
    )

    duplicate_ids = int(
        df["school_id"].duplicated().sum()
    )

    missing_districts = int(
        df["district"].isna().sum()
        + df["district"].eq("").fillna(False).sum()
    )

    if missing_ids or duplicate_ids or missing_districts:
        raise ValueError(
            f"{year}: ID/district integrity failed. "
            f"Missing IDs={missing_ids}, "
            f"Duplicate IDs={duplicate_ids}, "
            f"Missing districts={missing_districts}"
        )

    numeric_columns = list(
        df.select_dtypes(include=[np.number]).columns
    )

    # Do not aggregate identifier or year columns.
    numeric_columns = [
        c for c in numeric_columns
        if c not in {
            "school_id",
            "academic_year",
        }
    ]

    if not numeric_columns:
        raise ValueError(
            f"{year}: No numeric feature columns found."
        )

    grouped = df.groupby(
        ["academic_year", "district"],
        dropna=False,
        sort=True,
    )

    result = grouped.size().rename("school_count").to_frame()

    result["unique_school_ids"] = (
        grouped["school_id"].nunique()
    )

    # --------------------------------------------------------
    # AGGREGATE NUMERIC FEATURES
    # --------------------------------------------------------

    for col in numeric_columns:

        method = get_method(col)

        reporting = grouped[col].count()

        result[f"{col}_schools_reporting"] = reporting

        result[f"{col}_coverage_pct"] = (
            reporting / result["school_count"] * 100
        ).round(2)

        if method == "MEAN_SCHOOL_PERCENTAGE":

            result[f"{col}_mean_school_pct"] = (
                grouped[col].mean()
            ).round(3)

        elif method == "MEAN":

            result[f"{col}_mean"] = (
                grouped[col].mean()
            ).round(3)

        else:

            # min_count=1 prevents all-missing groups becoming zero.
            result[f"{col}_sum"] = (
                grouped[col].sum(min_count=1)
            )

            result[f"{col}_mean_per_school"] = (
                grouped[col].mean()
            ).round(3)

        COVERAGE.append({
            "academic_year": year,
            "feature": col,
            "aggregation_method": method,
            "schools_in_source": rows,
            "schools_reporting": int(df[col].count()),
            "overall_coverage_pct": round(
                100 * df[col].count() / rows, 2
            ) if rows else 0,
        })

    result = result.reset_index()

    # --------------------------------------------------------
    # DISTRICT-WEIGHTED TEACHER PERCENTAGES
    # --------------------------------------------------------

    teacher_ratios = {
        "male_teacher": "male_teachers",
        "female_teacher": "female_teachers",
        "transgender_teacher": "transgender_teachers",
        "regular_teacher": "regular_teachers",
        "contract_teacher": "contract_teachers",
        "part_time_teacher": "part_time_teachers",
        "computer_trained_teacher": "computer_trained_teachers",
        "teachers_above_55": "teachers_aged_above_55",
        "below_graduate_teacher": "below_graduate_teachers",
        "graduate_teacher": "graduate_teachers",
        "postgraduate_teacher": "postgraduate_teachers",
        "service_training_teacher": "teachers_received_service_training",
        "non_training_assignment_teacher": "teachers_non_training_assignment",
    }

    for output_name, numerator_name in teacher_ratios.items():

        numerator_col = f"{numerator_name}_sum"
        denominator_col = "teacher_total_sum"

        if (
            numerator_col in result.columns
            and denominator_col in result.columns
        ):

            denominator = result[denominator_col].where(
                result[denominator_col] > 0
            )

            result[f"district_{output_name}_pct"] = (
                result[numerator_col] / denominator * 100
            ).round(3)

    result["academic_year"] = result["academic_year"].astype(str)

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    district_count = int(result["district"].nunique())

    district_groups = len(result)

    aggregated_schools = int(result["school_count"].sum())

    duplicate_district_years = int(
        result.duplicated(
            subset=["academic_year", "district"]
        ).sum()
    )

    if aggregated_schools != rows:
        raise ValueError(
            f"{year}: Aggregated school count does not match source rows."
        )

    if duplicate_district_years != 0:
        raise ValueError(
            f"{year}: Duplicate district-year records found."
        )

    if district_count != EXPECTED_DISTRICTS:
        raise ValueError(
            f"{year}: Expected 36 districts, found {district_count}."
        )

    status = "PASS"

    output_path = (
        OUTPUT_DIR
        / f"maharashtra_district_year_{year}.csv"
    )

    result.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    ALL_DISTRICT_DATA.append(result)

    SUMMARIES.append({
        "academic_year": year,
        "source_rows": rows,
        "district_count": district_count,
        "district_year_records": district_groups,
        "aggregated_school_count": aggregated_schools,
        "numeric_source_features": len(numeric_columns),
        "output_columns": len(result.columns),
        "duplicate_district_years": duplicate_district_years,
        "status": status,
    })

    print(f"Academic Year       : {year}")
    print(f"Source Schools      : {rows:,}")
    print(f"Districts           : {district_count}")
    print(f"District-Year Rows  : {district_groups}")
    print(f"Numeric Features    : {len(numeric_columns)}")
    print(f"Output Columns      : {len(result.columns)}")
    print(f"Aggregated Schools  : {aggregated_schools:,}")
    print(f"STATUS              : {status}")
    print(f"OUTPUT              : {output_path}")

    return result


# ============================================================
# 4. MAIN
# ============================================================

def main():

    print("\n" + "=" * 70)
    print("SHALASCOPE MAHARASHTRA")
    print("DISTRICT-YEAR DATASET BUILDER")
    print("=" * 70)

    files = sorted(
        INPUT_DIR.glob("maharashtra_numeric_features_*.csv")
    )

    if len(files) != EXPECTED_YEARS:
        raise ValueError(
            f"Expected {EXPECTED_YEARS} year files, found {len(files)}."
        )

    failed = []

    for path in files:

        try:
            process_file(path)

        except Exception as exc:

            failed.append({
                "file": path.name,
                "error": str(exc),
            })

            print(
                f"\nFAILED: {path.name} - {exc}",
                file=sys.stderr,
            )

    if failed:

        pd.DataFrame(failed).to_csv(
            REPORT_DIR / "district_year_failures.csv",
            index=False,
            encoding="utf-8-sig",
        )

        print("\nFINAL STATUS: REVIEW REQUIRED")
        return

    combined = pd.concat(
        ALL_DISTRICT_DATA,
        ignore_index=True,
        sort=False,
    )

    combined_path = (
        OUTPUT_DIR
        / "maharashtra_district_year_master.csv"
    )

    combined.to_csv(
        combined_path,
        index=False,
        encoding="utf-8-sig",
    )

    summary = pd.DataFrame(SUMMARIES)
    coverage = pd.DataFrame(COVERAGE)

    summary_path = (
        REPORT_DIR
        / "district_year_aggregation_summary.csv"
    )

    coverage_path = (
        REPORT_DIR
        / "district_year_feature_coverage.csv"
    )

    validation_path = (
        REPORT_DIR
        / "district_year_validation.csv"
    )

    summary.to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    coverage.to_csv(
        coverage_path,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # FINAL COMBINED VALIDATION
    # --------------------------------------------------------

    total_source_rows = int(summary["source_rows"].sum())

    total_aggregated_schools = int(
        combined["school_count"].sum()
    )

    unique_years = int(
        combined["academic_year"].nunique()
    )

    unique_districts = int(
        combined["district"].nunique()
    )

    unique_groups = len(combined)

    duplicate_groups = int(
        combined.duplicated(
            subset=["academic_year", "district"]
        ).sum()
    )

    validation = pd.DataFrame([{
        "years": unique_years,
        "districts": unique_districts,
        "district_year_records": unique_groups,
        "expected_records": EXPECTED_YEARS * EXPECTED_DISTRICTS,
        "source_school_year_rows": total_source_rows,
        "aggregated_school_year_rows": total_aggregated_schools,
        "duplicate_district_years": duplicate_groups,
        "status": (
            "PASS"
            if (
                unique_years == EXPECTED_YEARS
                and unique_districts == EXPECTED_DISTRICTS
                and unique_groups == EXPECTED_YEARS * EXPECTED_DISTRICTS
                and total_source_rows == total_aggregated_schools
                and duplicate_groups == 0
            )
            else "REVIEW_REQUIRED"
        ),
    }])

    validation.to_csv(
        validation_path,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n" + "=" * 70)
    print("DISTRICT-YEAR FINAL SUMMARY")
    print("=" * 70)

    print(summary.to_string(index=False))

    print("\nFINAL VALIDATION")
    print(validation.to_string(index=False))

    print("\nCOMBINED OUTPUT:")
    print(combined_path)

    print("\nAUDIT REPORTS:")
    print(summary_path)
    print(coverage_path)
    print(validation_path)

    print(
        "\nFINAL STATUS:",
        validation.iloc[0]["status"],
    )


if __name__ == "__main__":
    main()

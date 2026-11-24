
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "data" / "processed" / "district_year"
    / "maharashtra_district_year_final_master.csv"
)

OUT = ROOT / "reports" / "score_design"


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Dataset not found: {INPUT}")

    OUT.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT, low_memory=False)

    required = ["academic_year", "district", "school_count"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    def col(name):
        if name not in df.columns:
            return None
        return pd.to_numeric(df[name], errors="coerce")

    metrics = []

    def add_metric(name, pillar, values, source,
                   direction, status, expected_range=None, note=""):

        if values is None:
            print(f"SKIPPED: {name}")
            return

        values = pd.to_numeric(values, errors="coerce")
        valid = values.dropna()

        out_of_range = 0
        if expected_range is not None:
            low, high = expected_range
            out_of_range = int(
                ((valid < low) | (valid > high)).sum()
            )

        metrics.append({
            "indicator": name,
            "pillar": pillar,
            "source_or_formula": source,
            "direction": direction,
            "status": status,
            "available_records": int(valid.count()),
            "missing_records": int(values.isna().sum()),
            "coverage_pct": round(values.notna().mean() * 100, 2),
            "minimum": valid.min() if len(valid) else None,
            "median": valid.median() if len(valid) else None,
            "mean": valid.mean() if len(valid) else None,
            "maximum": valid.max() if len(valid) else None,
            "zero_records": int((valid == 0).sum()),
            "negative_records": int((valid < 0).sum()),
            "out_of_range_records": out_of_range,
            "notes": note
        })

    def ratio(numerator, denominator, multiplier=1):
        n = col(numerator)
        d = col(denominator)

        if n is None or d is None:
            return None

        return n / d.where(d > 0) * multiplier

    # --------------------------------------------------
    # 1. STUDENT ACCESS & SUPPORT
    # --------------------------------------------------

    add_metric(
        "Textbook beneficiaries per 100 students",
        "Student Access & Support",
        ratio(
            "free_textbooks_beneficiaries_total_sum",
            "enrollment_reported_student_total",
            100
        ),
        "Textbook beneficiaries / reported students * 100",
        "Higher may indicate broader support",
        "CANDIDATE - VERIFY",
        (0, 100),
        "Check source definitions and values above 100."
    )

    add_metric(
        "Uniform beneficiaries per 100 students",
        "Student Access & Support",
        ratio(
            "free_uniform_beneficiaries_total_sum",
            "enrollment_reported_student_total",
            100
        ),
        "Uniform beneficiaries / reported students * 100",
        "Higher may indicate broader support",
        "CANDIDATE - VERIFY",
        (0, 100),
        "Check source definitions and values above 100."
    )

    add_metric(
        "Enrollment reporting coverage",
        "Data Quality",
        col("enrollment_coverage_pct"),
        "enrollment_coverage_pct",
        "Higher means more complete reporting",
        "DATA CONFIDENCE ONLY",
        (0, 100),
        "Not a real-world enrollment/access rate."
    )

    add_metric(
        "Enrollment validation rate",
        "Data Quality",
        ratio(
            "enrollment_validated_schools",
            "enrollment_reporting_schools",
            100
        ),
        "Validated schools / reporting schools * 100",
        "Higher means better reconciliation",
        "DATA CONFIDENCE ONLY",
        (0, 100),
        "Review-required records must not be treated as zero."
    )

    # --------------------------------------------------
    # 2. TEACHER TOTAL RECONCILIATION
    # --------------------------------------------------

    gender_cols = [
        "male_teachers_sum",
        "female_teachers_sum",
        "transgender_teachers_sum"
    ]

    gender_total = None

    if all(c in df.columns for c in gender_cols):
        gender_data = pd.concat(
            [col(c) for c in gender_cols],
            axis=1
        )

        gender_total = gender_data.sum(
            axis=1,
            min_count=3
        )

        add_metric(
            "Teacher total from gender components",
            "Teacher Strength",
            gender_total,
            "Male + Female + Transgender teachers",
            "Denominator candidate",
            "DIAGNOSTIC ONLY",
            None,
            "Use only after reconciliation with official teacher total."
        )

    official_total = col("teacher_total_sum")

    if gender_total is not None and official_total is not None:
        comparison = pd.DataFrame({
            "derived": gender_total,
            "official": official_total
        }).dropna()

        if len(comparison):
            difference = (
                comparison["derived"] -
                comparison["official"]
            ).abs()

            pct_difference = (
                difference /
                comparison["official"].abs().replace(0, float("nan"))
                * 100
            )

            print("\nTEACHER TOTAL RECONCILIATION")
            print("Compared records:", len(comparison))
            print("Exact matches:", int((difference == 0).sum()))
            print(
                "Within 1%:",
                int((pct_difference <= 1).sum())
            )
            print("Median difference:", difference.median())
            print("Maximum difference:", difference.max())

    if gender_total is not None:
        student_total = col("enrollment_reported_student_total")

        if student_total is not None:
            add_metric(
                "District aggregate students per teacher",
                "Teacher Strength",
                student_total /
                gender_total.where(gender_total > 0),
                "Student total / gender-component teacher total",
                "Lower is generally better",
                "CANDIDATE - PENDING RECONCILIATION",
                None,
                "District aggregate ratio, not average school PTR."
            )

        teacher_share_fields = [
            ("Regular teacher share", "regular_teachers_sum"),
            ("Contract teacher share", "contract_teachers_sum"),
            ("Part-time teacher share", "part_time_teachers_sum"),
            ("Below-graduate teacher share", "below_graduate_teachers_sum"),
            ("No-qualification teacher share", "no_qualification_teachers_sum"),
            ("Graduate teacher share", "graduate_teachers_sum"),
            ("Postgraduate teacher share", "postgraduate_teachers_sum"),
            ("B.Ed teacher share", "bachelor_of_education_teachers_sum")
        ]

        for name, numerator in teacher_share_fields:
            n = col(numerator)

            if n is not None:
                add_metric(
                    name,
                    "Teacher Strength",
                    n / gender_total.where(gender_total > 0) * 100,
                    f"{numerator} / gender teacher total * 100",
                    "REVIEW SOURCE DEFINITIONS",
                    "CANDIDATE - VERIFY",
                    (0, 100),
                    "Check category overlap and official definitions."
                )

    # --------------------------------------------------
    # 3. INFRASTRUCTURE
    # --------------------------------------------------

    infrastructure_fields = [
        (
            "Functional toilet percentage",
            "facility_functional_toilet_pct",
            "Higher is better",
            "Share of reported toilet units that are functional."
        ),
        (
            "Good condition classroom percentage",
            "facility_classrooms_good_condition_pct",
            "Higher is better",
            "Based on reported classroom condition."
        ),
        (
            "Classrooms needing repair percentage",
            "facility_classrooms_needing_repair_pct",
            "Lower is better",
            "Based on reported classroom condition."
        ),
        (
            "Pucca building block percentage",
            "facility_pucca_building_block_pct",
            "Higher is better",
            "Supplementary only: 12.5% missing."
        )
    ]

    for name, field, direction, note in infrastructure_fields:
        status = (
            "SUPPLEMENTARY ONLY"
            if field == "facility_pucca_building_block_pct"
            else "CANDIDATE"
        )

        add_metric(
            name,
            "Infrastructure",
            col(field),
            field,
            direction,
            status,
            (0, 100),
            note
        )

    # --------------------------------------------------
    # 4. DIGITAL READINESS
    # --------------------------------------------------

    add_metric(
        "Average digital devices per reporting school",
        "Digital Readiness",
        col("facility_avg_digital_devices_per_reporting_school"),
        "facility_avg_digital_devices_per_reporting_school",
        "Higher may indicate better device availability",
        "CORE CANDIDATE",
        None,
        "Does not measure actual student access or usage."
    )

    add_metric(
        "Computer-trained teachers per 100 teachers",
        "Digital Readiness",
        ratio(
            "computer_trained_teachers_sum",
            "teacher_total_sum",
            100
        ),
        "Computer-trained teachers / official teacher total * 100",
        "Higher is better",
        "SUPPLEMENTARY - 4 YEARS",
        (0, 100),
        "Not available for the full 8-year period."
    )

    # --------------------------------------------------
    # 5. FINANCIAL & GOVERNANCE
    # --------------------------------------------------

    add_metric(
        "Grant expenditure as percentage of receipts",
        "Financial & Governance",
        ratio(
            "grant_expenditure_amount_sum",
            "grant_receipt_amount_sum",
            100
        ),
        "Grant expenditure / grant receipts * 100",
        "Context-dependent",
        "CANDIDATE - VERIFY",
        None,
        "Check grant accounting and previous-balance definitions."
    )

    governance_fields = [
        ("Academic inspections", "academic_inspections_count_sum"),
        ("Block officer visits", "block_officer_visits_count_sum"),
        ("CRC coordinator visits", "crc_coordinator_visits_count_sum"),
        ("District officer visits", "district_officer_visits_count_sum")
    ]

    for name, field in governance_fields:
        add_metric(
            name + " per 100 schools",
            "Financial & Governance",
            ratio(field, "school_count", 100),
            field + " / school_count * 100",
            "Higher means more recorded monitoring",
            "CANDIDATE - INTERPRET CAREFULLY",
            None,
            "More visits do not automatically mean better outcomes."
        )

    # --------------------------------------------------
    # SAVE REPORTS
    # --------------------------------------------------

    audit = pd.DataFrame(metrics)

    audit_file = OUT / "shala_score_indicator_diagnostics.csv"
    audit.to_csv(
        audit_file,
        index=False,
        encoding="utf-8-sig"
    )

    years = df.groupby("academic_year")["district"].nunique()
    duplicate_keys = df.duplicated(
        ["academic_year", "district"]
    ).sum()

    print("\n" + "=" * 65)
    print("SHALASCOPE - SHALA SCORE INDICATOR AUDIT")
    print("=" * 65)

    print("Rows:", len(df))
    print("Columns:", len(df.columns))
    print("Academic years:", df["academic_year"].nunique())
    print("Districts:", df["district"].nunique())
    print("Duplicate district-year keys:", int(duplicate_keys))

    print("\nDISTRICTS PER YEAR")
    print(years.to_string())

    print("\nINDICATOR DIAGNOSTICS")
    print(
        audit[
            [
                "indicator",
                "coverage_pct",
                "minimum",
                "median",
                "maximum",
                "out_of_range_records"
            ]
        ].to_string(index=False)
    )

    print("\nREPORT SAVED:")
    print(audit_file)

    print("\nSTATUS: DIAGNOSTICS COMPLETED")
    print("No Shala Score has been calculated in this script.")


if __name__ == "__main__":
    main()

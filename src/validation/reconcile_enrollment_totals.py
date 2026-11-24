
from pathlib import Path
import pandas as pd
import numpy as np
import re
import gc

# ============================================================
# SHALASCOPE MAHARASHTRA
# ENROLLMENT CROSS-SOURCE RECONCILIATION
#
# 1. ENR1: General + SC + ST + OBC
# 2. ENR2: All reported Age-wise items
# 3. ENR1: Group 4 CWSN types vs Group 5 Item 0
#
# Diagnostic only. Does not create final student totals.
# Raw and processed inputs remain unchanged.
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = ROOT / "data" / "processed" / "enrollment_long"
REPORT_DIR = ROOT / "reports" / "data_audit"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

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

# Grade-wise and sex-wise enrollment columns.
VALUE_PATTERN = re.compile(
    r"^(cpp|c(?:[1-9]|1[0-2]))_(b|g|t)$",
    re.IGNORECASE,
)

SOCIAL_LABELS = {
    "general",
    "sc",
    "st",
    "obc",
}


# ------------------------------------------------------------
# 1. HELPERS
# ------------------------------------------------------------

def find_column(columns, candidates):

    lookup = {
        str(c).strip().lower(): c
        for c in columns
    }

    for candidate in candidates:

        key = candidate.lower()

        if key in lookup:
            return lookup[key]

    return None


def clean_series(series):

    return (
        series.astype("string")
        .str.strip()
        .replace("", pd.NA)
    )


def normalize_label(value):

    if pd.isna(value):
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower(),
    )


def identify_value_columns(columns):

    return [
        col
        for col in columns
        if VALUE_PATTERN.fullmatch(str(col).strip())
    ]


def get_file_path(year, part):

    return (
        INPUT_DIR
        / year
        / f"maharashtra_{part}_items_{year}.csv.gz"
    )


def read_enrollment_file(year, part):

    path = get_file_path(year, part)

    if not path.exists():
        raise FileNotFoundError(path)

    # Read only the required columns.
    header = pd.read_csv(
        path,
        compression="gzip",
        nrows=0,
        encoding="utf-8-sig",
    )

    school_col = find_column(
        header.columns,
        [
            "pseudocode",
            "psuedocode",
            "school_id",
            "school_code",
            "udise_code",
        ],
    )

    group_col = find_column(
        header.columns,
        ["item_group"],
    )

    item_col = find_column(
        header.columns,
        ["item_id"],
    )

    description_col = find_column(
        header.columns,
        [
            "item_desc",
            "item_description",
        ],
    )

    if school_col is None:
        raise ValueError(
            f"{year} {part}: School ID column missing."
        )

    value_cols = identify_value_columns(
        header.columns
    )

    if not value_cols:
        raise ValueError(
            f"{year} {part}: No enrollment value columns."
        )

    usecols = [school_col] + value_cols

    for col in [
        group_col,
        item_col,
        description_col,
    ]:
        if col is not None and col not in usecols:
            usecols.append(col)

    df = pd.read_csv(
        path,
        compression="gzip",
        usecols=usecols,
        dtype=str,
        low_memory=False,
        encoding="utf-8-sig",
    )

    df = df.rename(
        columns={school_col: "school_id"}
    )

    df["school_id"] = clean_series(
        df["school_id"]
    )

    if df["school_id"].isna().any():
        raise ValueError(
            f"{year} {part}: Missing School IDs."
        )

    # Convert all value fields to numeric.
    for col in value_cols:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

        if df[col].lt(0).any():
            raise ValueError(
                f"{year} {part}: Negative values in {col}"
            )

    # Normalized item fields.
    if group_col is not None:

        df["_group"] = (
            df[group_col]
            .astype("string")
            .str.strip()
            .fillna("")
        )

    else:
        df["_group"] = ""

    if item_col is not None:

        df["_item"] = (
            df[item_col]
            .astype("string")
            .str.strip()
            .fillna("")
        )

    else:
        df["_item"] = ""

    if description_col is not None:

        df["_description"] = (
            df[description_col]
            .astype("string")
            .str.strip()
            .fillna("")
        )

    else:
        df["_description"] = ""

    df["_description_norm"] = (
        df["_description"]
        .apply(normalize_label)
    )

    return (
        df,
        value_cols,
        group_col is not None,
        description_col is not None,
    )


def aggregate_items(df, value_cols, mask, token):

    """
    Aggregate selected item rows by school.

    Missing item rows are NOT automatically interpreted
    as zero. Item counts are retained for coverage analysis.
    """

    sub = df.loc[
        mask,
        ["school_id"] + value_cols
    ].copy()

    if sub.empty:
        return pd.DataFrame(
            columns=value_cols + ["item_count"]
        ).rename_axis("school_id")

    sub["_item_token"] = token.loc[sub.index]

    # Prevent duplicate item rows from silently inflating totals.
    duplicate_count = sub.duplicated(
        ["school_id", "_item_token"]
    ).sum()

    if duplicate_count > 0:
        raise ValueError(
            f"Duplicate school-item rows: {duplicate_count}"
        )

    sums = (
        sub.groupby("school_id")[value_cols]
        .sum(min_count=1)
    )

    counts = (
        sub.groupby("school_id")["_item_token"]
        .nunique()
        .rename("item_count")
    )

    return sums.join(counts)


def compare_aggregates(left, right, value_cols, year, label):

    """
    Compare two independent enrollment aggregations.
    Only comparable non-missing cells are evaluated.
    """

    common_schools = left.index.intersection(
        right.index
    )

    left = left.loc[common_schools]
    right = right.loc[common_schools]

    common_cols = [
        col
        for col in value_cols
        if col in left.columns and col in right.columns
    ]

    if not common_cols or len(common_schools) == 0:
        return None, [], None

    a = left[common_cols]
    b = right[common_cols]

    valid = a.notna() & b.notna()
    equal = a.eq(b)

    comparable_cells = int(valid.sum().sum())
    exact_cells = int((equal & valid).sum().sum())
    mismatch_cells = comparable_cells - exact_cells

    match_pct = (
        exact_cells / comparable_cells * 100
        if comparable_cells else np.nan
    )

    school_has_comparison = valid.any(axis=1)

    school_exact = (
        (equal | ~valid).all(axis=1)
        & school_has_comparison
    )

    school_exact_count = int(school_exact.sum())

    # Dimension-wise comparison.
    dimension_rows = []

    for col in common_cols:

        col_valid = valid[col]
        col_exact = equal[col] & col_valid

        n_valid = int(col_valid.sum())
        n_equal = int(col_exact.sum())

        dimension_rows.append({
            "academic_year": year,
            "comparison": label,
            "grade_sex_column": col,
            "comparable_schools": n_valid,
            "exact_match_schools": n_equal,
            "mismatch_schools": n_valid - n_equal,
            "match_percentage": (
                round(n_equal / n_valid * 100, 2)
                if n_valid else np.nan
            ),
        })

    # Mismatch sample.
    sample_ids = school_exact[
        ~school_exact
    ].index[:100]

    mismatch_samples = []

    for school_id in sample_ids:

        row = {
            "academic_year": year,
            "comparison": label,
            "school_id": school_id,
        }

        for col in common_cols:

            av = a.at[school_id, col]
            bv = b.at[school_id, col]

            row[f"left_{col}"] = av
            row[f"right_{col}"] = bv

            row[f"difference_{col}"] = (
                av - bv
                if pd.notna(av) and pd.notna(bv)
                else np.nan
            )

        mismatch_samples.append(row)

    summary = {
        "academic_year": year,
        "comparison": label,
        "schools_left": len(left),
        "schools_right": len(right),
        "common_schools": len(common_schools),
        "compared_columns": len(common_cols),
        "comparable_cells": comparable_cells,
        "exact_match_cells": exact_cells,
        "mismatch_cells": mismatch_cells,
        "cell_match_percentage": (
            round(match_pct, 2)
            if pd.notna(match_pct) else np.nan
        ),
        "schools_matching_all_comparable_cells": school_exact_count,
        "schools_with_comparison": int(
            school_has_comparison.sum()
        ),
    }

    return (
        summary,
        dimension_rows,
        mismatch_samples,
    )


# ============================================================
# 2. MAIN AUDIT
# ============================================================

print("=" * 70)
print("SHALASCOPE - ENROLLMENT TOTAL RECONCILIATION")
print("=" * 70)

yearly_results = []
dimension_results = []
mismatch_results = []
cwsn_results = []
cwsn_mismatch_results = []
coverage_results = []
blank_results = []


for year in YEARS:

    print("\n" + "=" * 70)
    print(f"ACADEMIC YEAR: {year}")
    print("=" * 70)

    # --------------------------------------------------------
    # 2A. READ ENR1
    # --------------------------------------------------------

    enr1, enr1_cols, enr1_has_groups, enr1_has_desc = (
        read_enrollment_file(year, "enr1")
    )

    # --------------------------------------------------------
    # 2B. READ ENR2
    # --------------------------------------------------------

    enr2, enr2_cols, enr2_has_groups, enr2_has_desc = (
        read_enrollment_file(year, "enr2")
    )

    common_value_cols = [
        col
        for col in enr1_cols
        if col in enr2_cols
    ]

    if not common_value_cols:
        raise ValueError(
            f"{year}: No common grade/sex columns."
        )

    # --------------------------------------------------------
    # 2C. CREATE SOCIAL CATEGORY MASK
    # --------------------------------------------------------

    if enr1_has_groups:

        social_mask = (
            enr1["_group"].eq("1")
            & enr1["_item"].isin(["1", "2", "3", "4"])
        )

        social_token = (
            enr1["_group"]
            + "_"
            + enr1["_item"]
        )

    else:

        social_mask = (
            enr1["_description_norm"].isin(
                SOCIAL_LABELS
            )
        )

        social_token = (
            enr1["_description_norm"]
        )

    social = aggregate_items(
        enr1,
        enr1_cols,
        social_mask,
        social_token,
    )

    # --------------------------------------------------------
    # 2D. CREATE AGE-WISE MASK
    # --------------------------------------------------------

    if enr2_has_groups:

        age_numeric_id = pd.to_numeric(
            enr2["_item"],
            errors="coerce",
        )

        age_mask = (
            enr2["_group"].eq("8")
            & age_numeric_id.between(2, 22)
        )

        age_token = (
            enr2["_group"]
            + "_"
            + enr2["_item"]
        )

    else:

        # Accept source labels like Age<5, Age5, Age6...
        age_mask = (
            enr2["_description"]
            .str.replace(" ", "", regex=False)
            .str.match(
                r"^Age(?:<5|\d+)$",
                case=False,
                na=False,
            )
        )

        age_token = enr2["_description"]

    age = aggregate_items(
        enr2,
        enr2_cols,
        age_mask,
        age_token,
    )

    # --------------------------------------------------------
    # 2E. RECONCILE SOCIAL CATEGORY vs AGE-WISE TOTAL
    # --------------------------------------------------------

    comparison, dimensions, samples = compare_aggregates(
        social,
        age,
        common_value_cols,
        year,
        "SOCIAL_CATEGORY_VS_AGE_WISE",
    )

    if comparison is None:

        print("No comparable schools found.")

    else:

        comparison["social_schools"] = len(social)
        comparison["age_wise_schools"] = len(age)

        comparison["social_complete_4_item_schools"] = int(
            social["item_count"].eq(4).sum()
        )

        comparison["social_partial_item_schools"] = int(
            social["item_count"].lt(4).sum()
        )

        comparison["age_item_count_min"] = (
            int(age["item_count"].min())
            if len(age) else 0
        )

        comparison["age_item_count_median"] = (
            float(age["item_count"].median())
            if len(age) else np.nan
        )

        comparison["age_item_count_max"] = (
            int(age["item_count"].max())
            if len(age) else 0
        )

        yearly_results.append(comparison)

        dimension_results.extend(dimensions)
        mismatch_results.extend(samples)

        print(
            "Common schools:",
            comparison["common_schools"],
        )

        print(
            "Comparable grade/sex cells:",
            comparison["comparable_cells"],
        )

        print(
            "Exact cell match %:",
            comparison["cell_match_percentage"],
        )

        print(
            "Schools matching every comparable cell:",
            comparison[
                "schools_matching_all_comparable_cells"
            ],
        )

    # --------------------------------------------------------
    # 2F. CWSN GROUP 4 vs GROUP 5 ITEM 0
    # --------------------------------------------------------

    if (
        enr1_has_groups
        and year in [
            "2022-23",
            "2023-24",
            "2024-25",
            "2025-26",
        ]
    ):

        group4_mask = (
            enr1["_group"].eq("4")
            & pd.to_numeric(
                enr1["_item"],
                errors="coerce",
            ).between(1, 21)
        )

        group5_mask = (
            enr1["_group"].eq("5")
            & enr1["_item"].eq("0")
        )

        group4_token = (
            enr1["_group"]
            + "_"
            + enr1["_item"]
        )

        group5_token = (
            enr1["_group"]
            + "_"
            + enr1["_item"]
        )

        group4 = aggregate_items(
            enr1,
            enr1_cols,
            group4_mask,
            group4_token,
        )

        group5 = aggregate_items(
            enr1,
            enr1_cols,
            group5_mask,
            group5_token,
        )

        cwsn_comparison, cwsn_dimensions, cwsn_samples = (
            compare_aggregates(
                group4,
                group5,
                enr1_cols,
                year,
                "GROUP4_SUM_VS_GROUP5_ITEM0",
            )
        )

        if cwsn_comparison is not None:

            cwsn_comparison["group4_schools"] = len(group4)
            cwsn_comparison["group5_schools"] = len(group5)

            cwsn_comparison["group4_item_rows_complete"] = int(
                group4["item_count"].eq(21).sum()
            )

            cwsn_results.append(cwsn_comparison)
            cwsn_mismatch_results.extend(cwsn_samples)

            print(
                "Group 4 vs Group 5 cell match %:",
                cwsn_comparison["cell_match_percentage"],
            )

    # --------------------------------------------------------
    # 2G. AUDIT BLANK ENR2 ITEM (2021-22)
    # --------------------------------------------------------

    if (
        year == "2021-22"
        and not enr2_has_groups
        and "_description" in enr2.columns
    ):

        blank_mask = (
            enr2["_description"]
            .str.strip()
            .eq("")
        )

        blank = enr2.loc[
            blank_mask,
            enr2_cols,
        ]

        blank_numeric = blank.apply(
            pd.to_numeric,
            errors="coerce",
        )

        blank_results.append({
            "academic_year": year,
            "blank_item_rows": len(blank),
            "unique_schools": int(
                enr2.loc[blank_mask, "school_id"].nunique()
            ),
            "non_null_cells": int(
                blank_numeric.notna().sum().sum()
            ),
            "non_zero_cells": int(
                blank_numeric.fillna(0).ne(0).sum().sum()
            ),
            "sum_diagnostic_only": float(
                blank_numeric.sum().sum()
            ),
        })

    # --------------------------------------------------------
    # 2H. COVERAGE REPORT
    # --------------------------------------------------------

    coverage_results.append({
        "academic_year": year,
        "enr1_rows": len(enr1),
        "enr1_unique_schools": enr1["school_id"].nunique(),
        "enr1_social_item_rows": int(social_mask.sum()),
        "enr1_social_schools": len(social),
        "enr1_social_complete_four_items": (
            int(social["item_count"].eq(4).sum())
        ),
        "enr2_rows": len(enr2),
        "enr2_unique_schools": enr2["school_id"].nunique(),
        "enr2_age_item_rows": int(age_mask.sum()),
        "enr2_age_schools": len(age),
        "common_value_columns": len(common_value_cols),
    })

    print(
        "Social category schools:",
        len(social),
    )

    print(
        "Age-wise schools:",
        len(age),
    )

    del enr1, enr2, social, age
    gc.collect()


# ============================================================
# 3. SAVE REPORTS
# ============================================================

def save_report(rows, filename):

    df = pd.DataFrame(rows)

    path = REPORT_DIR / filename

    df.to_csv(
        path,
        index=False,
        encoding="utf-8-sig",
    )

    return path


yearly_file = save_report(
    yearly_results,
    "enrollment_social_vs_age_reconciliation_yearly.csv",
)

dimension_file = save_report(
    dimension_results,
    "enrollment_social_vs_age_reconciliation_by_grade_sex.csv",
)

mismatch_file = save_report(
    mismatch_results,
    "enrollment_social_vs_age_mismatch_samples.csv",
)

coverage_file = save_report(
    coverage_results,
    "enrollment_reconciliation_source_coverage.csv",
)

cwsn_file = save_report(
    cwsn_results,
    "enrollment_group5_vs_cwsn_validation.csv",
)

cwsn_mismatch_file = save_report(
    cwsn_mismatch_results,
    "enrollment_group5_vs_cwsn_mismatch_samples.csv",
)

blank_file = save_report(
    blank_results,
    "enrollment_blank_item_2021_22_audit.csv",
)


# ============================================================
# 4. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("ENROLLMENT RECONCILIATION - FINAL RESULT")
print("=" * 70)

print("\nSOCIAL CATEGORY vs AGE-WISE:")

if yearly_results:

    yearly_df = pd.DataFrame(yearly_results)

    display_cols = [
        "academic_year",
        "common_schools",
        "social_complete_4_item_schools",
        "age_item_count_min",
        "age_item_count_median",
        "age_item_count_max",
        "comparable_cells",
        "exact_match_cells",
        "mismatch_cells",
        "cell_match_percentage",
        "schools_matching_all_comparable_cells",
    ]

    print(
        yearly_df[display_cols].to_string(
            index=False
        )
    )

else:
    print("No comparable results.")

print("\nGROUP 4 vs GROUP 5:")

if cwsn_results:

    cwsn_df = pd.DataFrame(cwsn_results)

    print(
        cwsn_df[
            [
                "academic_year",
                "common_schools",
                "group4_item_rows_complete",
                "cell_match_percentage",
                "schools_matching_all_comparable_cells",
            ]
        ].to_string(index=False)
    )

else:
    print("No comparable Group 4 / Group 5 results.")

print("\nSOURCE COVERAGE:")

print(
    pd.DataFrame(coverage_results).to_string(
        index=False
    )
)

print("\nREPORTS SAVED:")

for path in [
    yearly_file,
    dimension_file,
    mismatch_file,
    coverage_file,
    cwsn_file,
    cwsn_mismatch_file,
    blank_file,
]:
    print(path)

print("\nIMPORTANT:")
print("- No missing item rows were converted into zero.")
print("- No Group 5 meaning was assumed.")
print("- Age IDs were not converted to actual age labels.")
print("- Reconciliation results are diagnostic only.")
print("- No final Student Total has been created.")

print("\nENROLLMENT RECONCILIATION COMPLETED")

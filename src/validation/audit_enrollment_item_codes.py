
from pathlib import Path
import re
import pandas as pd
import numpy as np

# ============================================================
# SHALASCOPE MAHARASHTRA
# ENROLLMENT ITEM CODE AUDIT
# Read-only audit. Original files remain unchanged.
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = ROOT / "data" / "processed" / "enrollment_long"
REPORT_DIR = ROOT / "reports" / "data_audit"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [
    "2018-19", "2019-20", "2020-21", "2021-22",
    "2022-23", "2023-24", "2024-25", "2025-26"
]

PARTS = ["enr1", "enr2"]


def find_school_column(columns):
    preferred = [
        "pseudocode",
        "psuedocode",
        "school_id",
        "school_code",
        "udise_code",
    ]

    lookup = {
        str(c).strip().lower(): c
        for c in columns
    }

    for name in preferred:
        if name in lookup:
            return lookup[name]

    return None


def find_value_columns(columns):
    """
    Find grade-wise numeric fields.
    Examples: cpp_b, cpp_g, c1_b, c1_g, c1_t.
    """

    pattern = re.compile(
        r"^(cpp|c\d+)(_|$)",
        flags=re.IGNORECASE
    )

    return [
        col for col in columns
        if pattern.match(str(col).strip())
    ]


def clean_text(series):
    return (
        series.astype("string")
        .fillna("")
        .str.strip()
    )


profile_rows = []
sample_rows = []
structure_rows = []
missing_files = []

print("=" * 70)
print("SHALASCOPE - ENROLLMENT ITEM CODE AUDIT")
print("=" * 70)

for year in YEARS:

    for part in PARTS:

        file_path = (
            INPUT_DIR
            / year
            / f"maharashtra_{part}_items_{year}.csv.gz"
        )

        if not file_path.exists():
            missing_files.append(str(file_path))
            print(f"MISSING: {year} {part}")
            continue

        print(f"\nProcessing: {year} | {part.upper()}")

        df = pd.read_csv(
            file_path,
            compression="gzip",
            dtype=str,
            low_memory=False,
            encoding="utf-8-sig",
        )

        school_col = find_school_column(df.columns)

        value_cols = find_value_columns(df.columns)

        group_col = (
            "item_group"
            if "item_group" in df.columns
            else None
        )

        item_col = (
            "item_id"
            if "item_id" in df.columns
            else None
        )

        desc_col = (
            "item_desc"
            if "item_desc" in df.columns
            else None
        )

        print(f"Rows: {len(df):,}")
        print(f"Columns: {len(df.columns)}")
        print(f"Value fields: {len(value_cols)}")

        structure_rows.append({
            "academic_year": year,
            "file_name": file_path.name,
            "rows": len(df),
            "columns": len(df.columns),
            "school_id_column": school_col,
            "item_group_column": group_col,
            "item_id_column": item_col,
            "item_desc_column": desc_col,
            "value_columns": "|".join(value_cols),
            "value_column_count": len(value_cols),
        })

        if school_col is None:
            raise ValueError(
                f"School ID column not found: {file_path}"
            )

        if not value_cols:
            raise ValueError(
                f"No grade-wise value columns found: {file_path}"
            )

        # Convert grade fields to numeric for audit only.
        numeric_values = pd.DataFrame(index=df.index)

        for col in value_cols:
            numeric_values[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        school_ids = clean_text(df[school_col])

        # ----------------------------------------------------
        # CREATE ITEM KEYS
        # ----------------------------------------------------

        if group_col and item_col:

            groups = clean_text(df[group_col])
            items = clean_text(df[item_col])

            descriptions = (
                clean_text(df[desc_col])
                if desc_col
                else pd.Series("", index=df.index)
            )

            df["_audit_group"] = groups
            df["_audit_item"] = items
            df["_audit_description"] = descriptions

            df["_audit_key"] = (
                "GROUP_" + groups
                + "_ITEM_" + items
            )

        elif desc_col:

            df["_audit_group"] = ""
            df["_audit_item"] = ""
            df["_audit_description"] = clean_text(
                df[desc_col]
            )

            df["_audit_key"] = (
                "DESC_" + df["_audit_description"]
            )

        else:
            raise ValueError(
                f"No item mapping columns found: {file_path}"
            )

        # ----------------------------------------------------
        # DUPLICATE SCHOOL-ITEM KEY AUDIT
        # ----------------------------------------------------

        duplicate_key_columns = [
            school_col,
            "_audit_key",
        ]

        duplicate_count = int(
            df.duplicated(
                subset=duplicate_key_columns
            ).sum()
        )

        # ----------------------------------------------------
        # GROUP-WISE VALUE PROFILES
        # ----------------------------------------------------

        grouped = df.groupby(
            [
                "_audit_key",
                "_audit_group",
                "_audit_item",
                "_audit_description",
            ],
            dropna=False,
            sort=True,
        )

        for (
            audit_key,
            audit_group,
            audit_item,
            audit_description,
        ), indexes in grouped.groups.items():

            idx = list(indexes)

            values = numeric_values.loc[
                idx, value_cols
            ]

            non_null_cells = int(
                values.notna().sum().sum()
            )

            non_zero_cells = int(
                values.fillna(0).ne(0).sum().sum()
            )

            negative_cells = int(
                values.lt(0).sum().sum()
            )

            numeric_sum = float(
                values.sum().sum()
            )

            row = {
                "academic_year": year,
                "file_name": file_path.name,
                "item_key": audit_key,
                "item_group": audit_group,
                "item_id": audit_item,
                "item_description": audit_description,
                "source_rows": len(idx),
                "unique_schools": school_ids.iloc[idx].nunique(),
                "grade_value_columns": len(value_cols),
                "non_null_value_cells": non_null_cells,
                "non_zero_value_cells": non_zero_cells,
                "negative_value_cells": negative_cells,
                "sum_all_grade_cells_DIAGNOSTIC_ONLY": numeric_sum,
                "duplicate_school_item_keys": duplicate_count,
            }

            # Column-wise totals for inspection.
            for col in value_cols:

                col_values = values[col]

                row[f"sum_{col}"] = col_values.sum(
                    min_count=1
                )

                row[f"non_null_{col}"] = int(
                    col_values.notna().sum()
                )

            profile_rows.append(row)

            # Save one non-empty sample row per item key.
            sample = df.loc[idx].copy()

            non_empty_mask = (
                numeric_values.loc[idx]
                .fillna(0)
                .ne(0)
                .any(axis=1)
            )

            sample_indexes = sample.index[
                non_empty_mask
            ]

            if len(sample_indexes) == 0:
                sample_indexes = sample.index[:1]

            for sample_index in sample_indexes[:1]:

                sample_row = {
                    "academic_year": year,
                    "file_name": file_path.name,
                    "item_key": audit_key,
                    "item_group": audit_group,
                    "item_id": audit_item,
                    "item_description": audit_description,
                }

                for col in value_cols:
                    sample_row[col] = df.at[
                        sample_index, col
                    ]

                sample_rows.append(sample_row)

        print(
            f"Item keys processed: "
            f"{grouped.ngroups}"
        )

        print(
            f"Duplicate school-item keys: "
            f"{duplicate_count:,}"
        )


# ============================================================
# SAVE AUDIT REPORTS
# ============================================================

profile_df = pd.DataFrame(profile_rows)
sample_df = pd.DataFrame(sample_rows)
structure_df = pd.DataFrame(structure_rows)

profile_file = (
    REPORT_DIR
    / "enrollment_code_numeric_profiles.csv"
)

sample_file = (
    REPORT_DIR
    / "enrollment_code_sample_rows.csv"
)

structure_file = (
    REPORT_DIR
    / "enrollment_file_structure.csv"
)

profile_df.to_csv(
    profile_file,
    index=False,
    encoding="utf-8-sig",
)

sample_df.to_csv(
    sample_file,
    index=False,
    encoding="utf-8-sig",
)

structure_df.to_csv(
    structure_file,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("ENROLLMENT ITEM CODE AUDIT - FINAL RESULT")
print("=" * 70)

print(f"Files processed: {len(structure_df)}")
print(f"Item profiles: {len(profile_df)}")
print(f"Sample rows: {len(sample_df)}")

if missing_files:
    print(f"Missing files: {len(missing_files)}")

    for missing in missing_files:
        print(missing)
else:
    print("Missing files: 0")

if not profile_df.empty:

    print("\nYEAR-WISE ITEM PROFILE COUNTS:")

    print(
        profile_df.groupby("academic_year")
        .size()
        .to_string()
    )

    print("\nCODED ITEM KEYS (2022-23 ONWARDS):")

    coded = profile_df[
        profile_df["academic_year"].isin(
            ["2022-23", "2023-24", "2024-25", "2025-26"]
        )
    ]

    print(
        coded[
            [
                "academic_year",
                "file_name",
                "item_group",
                "item_id",
                "source_rows",
                "unique_schools",
                "non_zero_value_cells",
                "sum_all_grade_cells_DIAGNOSTIC_ONLY",
            ]
        ].to_string(index=False)
    )

print("\nOUTPUT REPORTS:")
print(profile_file)
print(sample_file)
print(structure_file)

print("\nIMPORTANT:")
print("Numeric sums are diagnostic only.")
print("Do not interpret them as total enrollment.")
print("No item codes have been decoded in this audit.")

print("\nENROLLMENT ITEM CODE AUDIT COMPLETED")

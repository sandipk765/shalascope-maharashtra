
from pathlib import Path
import re
import gc
import pandas as pd
import numpy as np


# ============================================================
# SHALASCOPE MAHARASHTRA
# ENROLLMENT FEATURE ENGINEERING
#
# Primary source: ENR1 Social Category
# Validation source: ENR2 Age-wise Enrollment
#
# Outputs:
# 1. School-level Enrollment Features
# 2. District-Year Enrollment Features
# 3. Enrollment Validation Reports
#
# Important:
# - Age<5 and Age5 remain separate.
# - Group 5 Item 0 is excluded.
# - Age IDs are NOT translated into actual ages.
# - Missing school records remain NA, not zero.
# - Old years use ENR1 as primary source with review flags.
# - New years require exact ENR1/ENR2 reconciliation.
# - Raw files are never modified.
# ============================================================


# ------------------------------------------------------------
# 1. PROJECT PATHS AND CONFIGURATION
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

LONG_DIR = (
    ROOT
    / "data"
    / "processed"
    / "enrollment_long"
)

SCHOOL_MASTER_DIR = (
    ROOT
    / "data"
    / "processed"
    / "school_year_integrated"
)

SCHOOL_OUTPUT_DIR = (
    ROOT
    / "data"
    / "processed"
    / "school_year_features"
    / "enrollment"
)

DISTRICT_OUTPUT_DIR = (
    ROOT
    / "data"
    / "processed"
    / "district_year"
)

REPORT_DIR = (
    ROOT
    / "reports"
    / "data_audit"
)

for folder in [
    SCHOOL_OUTPUT_DIR,
    DISTRICT_OUTPUT_DIR,
    REPORT_DIR,
]:
    folder.mkdir(
        parents=True,
        exist_ok=True,
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

OLD_FORMAT_YEARS = [
    "2018-19",
    "2019-20",
    "2020-21",
    "2021-22",
]

NEW_FORMAT_YEARS = [
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
]

EXPECTED_DISTRICTS = 36

SOCIAL_CATEGORIES = {
    "general": "General",
    "sc": "SC",
    "st": "ST",
    "obc": "OBC",
}

SOCIAL_ITEM_IDS = {
    "general": "1",
    "sc": "2",
    "st": "3",
    "obc": "4",
}

VALUE_PATTERN = re.compile(
    r"^(cpp|c(?:[1-9]|1[0-2]))_(b|g|t)$",
    re.IGNORECASE,
)


# ------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ------------------------------------------------------------

def find_column(columns, candidates):
    """
    Case-insensitive exact column matching.
    """

    lookup = {
        str(col).strip().lower(): col
        for col in columns
    }

    for candidate in candidates:

        key = candidate.strip().lower()

        if key in lookup:
            return lookup[key]

    return None


def clean_ids(series):
    """
    Preserve School IDs as strings.
    """

    return (
        series.astype("string")
        .str.strip()
        .replace("", pd.NA)
    )


def normalize_label(value):
    """
    Normalize source labels for category matching.
    Used for General, SC, ST and OBC.
    """

    if pd.isna(value):
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower(),
    )


def normalize_code(value):
    """
    Normalize item_group and item_id.
    Handles numeric strings such as 1, 1.0.
    """

    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text == "":
        return ""

    try:
        number = float(text)

        if number.is_integer():
            return str(int(number))

    except ValueError:
        pass

    return text


def normalize_item_token(value):
    """
    Create distinct item tokens.

    Critical correction:
    Age<5 must never become the same token as Age5.
    """

    if pd.isna(value):
        return "blank"

    raw = re.sub(
        r"\s+",
        "",
        str(value).strip().lower(),
    )

    if raw in {
        "age<5",
        "age<05",
    }:
        return "age_less_than_5"

    if raw == "age5":
        return "age_5"

    if re.fullmatch(r"age\d+", raw):

        age_number = re.search(
            r"\d+",
            raw,
        ).group()

        return f"age_{age_number}"

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        raw,
    ).strip("_")


def make_safe_name(value):

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value).strip().lower(),
    ).strip("_")


# Confirm the Age<5 / Age5 correction.
assert (
    normalize_item_token("Age<5")
    != normalize_item_token("Age5")
), "Age<5 and Age5 token collision detected."


def value_column_sort_key(column):
    """
    Sort columns in academic order:
    CPP, Class 1 ... Class 12,
    followed by B, G, T.
    """

    grade, gender = column.lower().rsplit("_", 1)

    if grade == "cpp":
        grade_order = 0
    else:
        grade_order = int(grade[1:])

    gender_order = {
        "b": 0,
        "g": 1,
        "t": 2,
    }.get(gender, 9)

    return grade_order, gender_order


def get_grade_columns(value_cols):

    grades = {}

    for col in value_cols:

        match = VALUE_PATTERN.fullmatch(
            str(col)
        )

        if match:

            grade = match.group(1).lower()

            grades.setdefault(
                grade,
                [],
            ).append(col)

    return grades


def row_sum_complete(matrix, columns):
    """
    Sum only when every required component is available.
    """

    if matrix.empty:

        return pd.Series(
            index=matrix.index,
            dtype="float64",
        )

    if not columns:

        return pd.Series(
            index=matrix.index,
            dtype="float64",
        )

    return matrix[columns].sum(
        axis=1,
        min_count=len(columns),
    )


def make_empty_aggregate(value_cols):

    empty = pd.DataFrame(
        index=pd.Index(
            [],
            name="school_id",
        ),
        columns=value_cols,
        dtype="float64",
    )

    empty["item_rows"] = pd.Series(
        dtype="int64",
        index=empty.index,
    )

    return empty


def age_feature_name(token, code_mode):
    """
    Output naming:

    Old format:
      Age<5 -> age_less_than_5_reported_total
      Age5  -> age_5_reported_total

    New format:
      Group 8 / Item 5 -> age_id_5_reported_total

    The new IDs are NOT decoded into actual ages.
    """

    if code_mode:

        match = re.fullmatch(
            r"G8_I(\d+)",
            str(token),
        )

        if match:

            return (
                f"age_id_{match.group(1)}"
                "_reported_total"
            )

    token = str(token)

    if token.startswith("DESC_"):
        token = token[5:]

    return (
        make_safe_name(token)
        + "_reported_total"
    )


# ------------------------------------------------------------
# 3. READ LONG ENROLLMENT SOURCE
# ------------------------------------------------------------

def read_source(year, part):

    source_file = (
        LONG_DIR
        / year
        / f"maharashtra_{part}_items_{year}.csv.gz"
    )

    if not source_file.exists():

        raise FileNotFoundError(
            f"Enrollment source file not found:\n"
            f"{source_file}"
        )

    # Read header only.
    header = pd.read_csv(
        source_file,
        compression="gzip",
        nrows=0,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # IDENTIFY SOURCE COLUMNS
    # --------------------------------------------------------

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

    candidate_value_cols = [
        col
        for col in header.columns
        if VALUE_PATTERN.fullmatch(
            str(col).strip()
        )
    ]

    if not candidate_value_cols:

        raise ValueError(
            f"{year} {part}: No grade/sex value columns."
        )

    usecols = [
        school_col,
        *candidate_value_cols,
    ]

    for col in [
        group_col,
        item_col,
        description_col,
    ]:

        if col is not None and col not in usecols:
            usecols.append(col)

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    df = pd.read_csv(
        source_file,
        compression="gzip",
        usecols=usecols,
        dtype=str,
        low_memory=False,
        encoding="utf-8-sig",
    )

    df = df.rename(
        columns={
            school_col: "school_id",
        }
    )

    df["school_id"] = clean_ids(
        df["school_id"]
    )

    if df["school_id"].isna().any():

        raise ValueError(
            f"{year} {part}: Missing School IDs."
        )

    # --------------------------------------------------------
    # NORMALIZE ITEM GROUP
    # --------------------------------------------------------

    if group_col is not None:

        df["_group"] = (
            df[group_col].apply(normalize_code)
        )

    else:

        df["_group"] = ""

    # --------------------------------------------------------
    # NORMALIZE ITEM ID
    # --------------------------------------------------------

    if item_col is not None:

        df["_item"] = (
            df[item_col].apply(normalize_code)
        )

    else:

        df["_item"] = ""

    # --------------------------------------------------------
    # PRESERVE SOURCE DESCRIPTION
    # --------------------------------------------------------

    if description_col is not None:

        df["_description"] = (
            df[description_col]
            .astype("string")
            .fillna("")
            .str.strip()
        )

    else:

        df["_description"] = ""

    df["_description_norm"] = (
        df["_description"].apply(
            normalize_label
        )
    )

    # --------------------------------------------------------
    # NUMERIC VALUE CONVERSION
    # --------------------------------------------------------

    value_cols = []

    for col in candidate_value_cols:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

        if df[col].lt(0).any():

            raise ValueError(
                f"{year} {part}: Negative values in {col}."
            )

        if df[col].notna().any():

            value_cols.append(col)

    if not value_cols:

        raise ValueError(
            f"{year} {part}: No usable numeric fields."
        )

    value_cols = sorted(
        value_cols,
        key=value_column_sort_key,
    )

    # --------------------------------------------------------
    # DETERMINE OLD / NEW ITEM FORMAT
    # --------------------------------------------------------

    code_mode = df["_group"].ne("").any()

    if code_mode:

        df["_item_token"] = (
            "G"
            + df["_group"]
            + "_I"
            + df["_item"]
        )

    else:

        # IMPORTANT:
        # Use normalize_item_token, NOT normalize_label.
        # This prevents Age<5 / Age5 collisions.

        df["_item_token"] = (
            "DESC_"
            + df["_description"].apply(
                normalize_item_token
            )
        )

    # --------------------------------------------------------
    # SOURCE DUPLICATE VALIDATION
    # --------------------------------------------------------

    duplicate_rows = df.duplicated(
        subset=[
            "school_id",
            "_item_token",
        ]
    ).sum()

    if duplicate_rows:

        raise ValueError(
            f"{year} {part}: "
            f"{duplicate_rows} duplicate school-item rows."
        )

    # Verify the legacy Age labels remain distinct.
    if not code_mode:

        description_tokens = {}

        for description in df["_description"].unique():

            description_tokens[
                str(description)
            ] = normalize_item_token(description)

        if (
            "Age<5" in description_tokens
            and "Age5" in description_tokens
        ):

            if (
                description_tokens["Age<5"]
                == description_tokens["Age5"]
            ):

                raise ValueError(
                    f"{year}: Age<5 / Age5 normalization collision."
                )

    return (
        df,
        value_cols,
        code_mode,
    )


# ------------------------------------------------------------
# 4. AGGREGATE SELECTED ITEMS BY SCHOOL
# ------------------------------------------------------------

def aggregate_items(
    selected,
    value_cols,
    label,
):

    if selected.empty:

        return make_empty_aggregate(
            value_cols
        )

    duplicate_count = selected.duplicated(
        subset=[
            "school_id",
            "_item_token",
        ]
    ).sum()

    if duplicate_count:

        raise ValueError(
            f"{label}: Duplicate school-item rows: "
            f"{duplicate_count}"
        )

    grouped = selected.groupby(
        "school_id",
        sort=False,
    )

    values = grouped[value_cols].sum(
        min_count=1
    )

    item_counts = grouped.size().rename(
        "item_rows"
    )

    # Do not silently fill missing values with zero.
    for col in value_cols:

        non_null_counts = grouped[col].count()

        incomplete_ids = non_null_counts[
            non_null_counts < item_counts
        ].index

        if len(incomplete_ids):

            values.loc[
                incomplete_ids,
                col,
            ] = np.nan

    result = values.join(
        item_counts
    )

    return result


# ------------------------------------------------------------
# 5. ITEM MASKS
# ------------------------------------------------------------

def create_social_masks(
    enr1,
    code_mode,
):

    masks = {}

    if code_mode:

        for category, item_id in SOCIAL_ITEM_IDS.items():

            masks[category] = (
                enr1["_group"].eq("1")
                & enr1["_item"].eq(item_id)
            )

    else:

        for category, source_label in SOCIAL_CATEGORIES.items():

            masks[category] = (
                enr1["_description_norm"]
                == normalize_label(source_label)
            )

    return masks


def create_age_mask(
    enr2,
    code_mode,
):

    if code_mode:

        item_numbers = pd.to_numeric(
            enr2["_item"],
            errors="coerce",
        )

        return (
            enr2["_group"].eq("8")
            & item_numbers.between(2, 22)
        )

    descriptions = (
        enr2["_description"]
        .str.replace(
            " ",
            "",
            regex=False,
        )
    )

    return descriptions.str.match(
        r"^Age(?:<5|\d+)$",
        case=False,
        na=False,
    )


# ------------------------------------------------------------
# 6. RECONCILE ENR1 AND ENR2
# ------------------------------------------------------------

def reconcile_sources(
    social,
    age,
    value_cols,
    year,
):

    common_ids = social.index.intersection(
        age.index
    )

    left = social.loc[
        common_ids,
        value_cols,
    ]

    right = age.loc[
        common_ids,
        value_cols,
    ]

    comparable = (
        left.notna()
        & right.notna()
    )

    equal = left.eq(right)

    mismatch_mask = (
        comparable
        & ~equal
    )

    compared_by_school = comparable.sum(
        axis=1
    )

    mismatch_by_school = mismatch_mask.sum(
        axis=1
    )

    exact_by_school = (
        compared_by_school.eq(len(value_cols))
        & mismatch_by_school.eq(0)
    )

    comparable_cells = int(
        comparable.sum().sum()
    )

    exact_cells = int(
        (equal & comparable).sum().sum()
    )

    mismatch_cells = (
        comparable_cells
        - exact_cells
    )

    expected_cells = (
        len(common_ids)
        * len(value_cols)
    )

    cell_match_pct = (
        exact_cells / comparable_cells * 100
        if comparable_cells > 0
        else np.nan
    )

    full_comparison_exact = (
        len(common_ids) > 0
        and comparable_cells == expected_cells
        and mismatch_cells == 0
    )

    # New-format years were previously verified at 100%.
    # Stop if this condition changes.
    if year in NEW_FORMAT_YEARS:

        if not full_comparison_exact:

            raise ValueError(
                f"{year}: New-format ENR1/ENR2 "
                "reconciliation is not completely exact. "
                "Student totals will not be accepted."
            )

    return {
        "common_ids": common_ids,
        "compared_by_school": compared_by_school,
        "mismatch_by_school": mismatch_by_school,
        "exact_by_school": exact_by_school,
        "comparable_cells": comparable_cells,
        "exact_cells": exact_cells,
        "mismatch_cells": mismatch_cells,
        "cell_match_percentage": cell_match_pct,
        "full_comparison_exact": full_comparison_exact,
    }


# ------------------------------------------------------------
# 7. BUILD ONE YEAR'S SCHOOL FEATURES
# ------------------------------------------------------------

def build_year_features(year):

    print("\n" + "=" * 70)
    print(
        f"ENROLLMENT FEATURE ENGINEERING: {year}"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # A. LOAD SOURCES
    # --------------------------------------------------------

    enr1, enr1_cols, enr1_code_mode = read_source(
        year,
        "enr1",
    )

    enr2, enr2_cols, enr2_code_mode = read_source(
        year,
        "enr2",
    )

    if set(enr1_cols) != set(enr2_cols):

        raise ValueError(
            f"{year}: ENR1 and ENR2 grade/sex "
            "columns do not match."
        )

    if enr1_code_mode != enr2_code_mode:

        raise ValueError(
            f"{year}: ENR1/ENR2 item format mismatch."
        )

    value_cols = sorted(
        enr1_cols,
        key=value_column_sort_key,
    )

    grade_columns = get_grade_columns(
        value_cols
    )

    # --------------------------------------------------------
    # B. SOCIAL CATEGORY AGGREGATION
    # --------------------------------------------------------

    social_masks = create_social_masks(
        enr1,
        enr1_code_mode,
    )

    social_selected_mask = pd.Series(
        False,
        index=enr1.index,
    )

    for mask in social_masks.values():

        social_selected_mask |= mask

    social_rows = enr1.loc[
        social_selected_mask
    ].copy()

    social = aggregate_items(
        social_rows,
        value_cols,
        f"{year} ENR1 Social Categories",
    )

    social_total = row_sum_complete(
        social,
        value_cols,
    )

    # --------------------------------------------------------
    # C. AGE-WISE AGGREGATION
    # --------------------------------------------------------

    age_mask = create_age_mask(
        enr2,
        enr2_code_mode,
    )

    age_rows = enr2.loc[
        age_mask
    ].copy()

    age = aggregate_items(
        age_rows,
        value_cols,
        f"{year} ENR2 Age Wise",
    )

    age_total = row_sum_complete(
        age,
        value_cols,
    )

    # --------------------------------------------------------
    # D. RECONCILIATION
    # --------------------------------------------------------

    check = reconcile_sources(
        social,
        age,
        value_cols,
        year,
    )

    common_ids = check["common_ids"]

    compared_by_school = (
        check["compared_by_school"]
    )

    mismatch_by_school = (
        check["mismatch_by_school"]
    )

    exact_by_school = (
        check["exact_by_school"]
    )

    exact_for_school = (
        exact_by_school
        .reindex(social.index)
        .fillna(False)
        .astype(bool)
    )

    # --------------------------------------------------------
    # E. SOURCE COMPLETENESS
    # --------------------------------------------------------

    social_total_source_complete = (
        social_total.notna()
    )

    if year in OLD_FORMAT_YEARS:

        # Four legacy Social Category items.
        social_source_complete = (
            social["item_rows"].eq(4)
            & social_total_source_complete
        )

        # ENR1 remains primary in old years.
        # ENR2 discrepancies are explicitly reviewed.
        student_total_eligible = (
            social_source_complete
        )

    else:

        # New-format sparse category rows are accepted
        # only for schools with exact cross-source matches.
        student_total_eligible = (
            social_total_source_complete
            & exact_for_school
        )

        social_source_complete = (
            student_total_eligible
        )

    student_total = social_total.where(
        student_total_eligible
    )

    age_total_aligned = age_total.reindex(
        social.index
    )

    # --------------------------------------------------------
    # F. CROSS-CHECK STATUS
    # --------------------------------------------------------

    crosscheck_status = pd.Series(
        "NO_COMPARABLE_RECORD",
        index=social.index,
        dtype="string",
    )

    crosscheck_status.loc[
        exact_for_school
    ] = "EXACT_MATCH"

    if year in OLD_FORMAT_YEARS:

        source_difference = (
            student_total_eligible
            & ~exact_for_school
        )

        crosscheck_status.loc[
            source_difference
        ] = "ENR1_PRIMARY_SOURCE_DIFFERENCE"

    else:

        incomplete_comparison = (
            student_total_eligible
            == False
        )

        crosscheck_status.loc[
            incomplete_comparison
            & social_total.notna()
        ] = "REVIEW_OR_NO_COMPLETE_MATCH"

    # --------------------------------------------------------
    # G. SCHOOL-LEVEL OUTPUT
    # --------------------------------------------------------

    features = pd.DataFrame(
        index=social.index
    )

    features.index.name = "school_id"

    features["student_total"] = (
        student_total
    )

    features["student_total_enr1"] = (
        social_total
    )

    features["student_total_enr2"] = (
        age_total_aligned
    )

    features["student_total_source_complete"] = (
        student_total_eligible
    )

    # True only when ENR1 and ENR2 match exactly.
    features["student_total_validated"] = (
        student_total.notna()
        & exact_for_school
    )

    features["enrollment_source_primary"] = (
        "ENR1_SOCIAL_CATEGORY"
    )

    features["enrollment_crosscheck_status"] = (
        crosscheck_status
    )

    features["social_category_item_rows"] = (
        social["item_rows"]
    )

    features["age_item_rows"] = (
        age["item_rows"].reindex(
            social.index
        )
    )

    features["enr1_enr2_compared_cells"] = (
        compared_by_school.reindex(
            social.index
        )
    )

    features["enr1_enr2_mismatch_cells"] = (
        mismatch_by_school.reindex(
            social.index
        )
    )

    school_match_percentage = (
        (
            compared_by_school
            - mismatch_by_school
        )
        / compared_by_school.replace(
            0,
            np.nan,
        )
        * 100
    )

    features["enr1_enr2_match_percentage"] = (
        school_match_percentage.reindex(
            social.index
        )
    )

    features["enrollment_record_available"] = True

    # --------------------------------------------------------
    # H. GRADE-WISE ENROLLMENT
    # --------------------------------------------------------

    for grade, columns in grade_columns.items():

        features[
            f"enrollment_{grade}_total"
        ] = row_sum_complete(
            social,
            columns,
        )

    # --------------------------------------------------------
    # I. B/G/T COMPONENT TOTALS
    # --------------------------------------------------------

    for suffix in [
        "b",
        "g",
        "t",
    ]:

        columns = [
            col
            for col in value_cols
            if col.lower().endswith(
                "_" + suffix
            )
        ]

        feature_name = (
            f"enrollment_{suffix}_component_total"
        )

        if columns:

            features[feature_name] = (
                row_sum_complete(
                    social,
                    columns,
                )
            )

        else:

            features[feature_name] = np.nan

    if any(
        col.lower().endswith("_t")
        for col in value_cols
    ):

        features["gender_field_schema"] = (
            "B_G_T_SEPARATE"
        )

    else:

        features["gender_field_schema"] = (
            "LEGACY_B_G_FIELDS"
        )

    # --------------------------------------------------------
    # J. ENR1 / ENR2 GRADE-SEX DETAILS
    # --------------------------------------------------------

    for col in value_cols:

        features[f"enr1_{col}"] = (
            social[col]
        )

        if col in age.columns:

            features[f"enr2_{col}"] = (
                age[col].reindex(
                    social.index
                )
            )

    # --------------------------------------------------------
    # K. SOCIAL CATEGORY TOTALS
    # --------------------------------------------------------

    sparse_new_format = (
        year in NEW_FORMAT_YEARS
    )

    for category, mask in social_masks.items():

        category_rows = enr1.loc[
            mask
        ].copy()

        category_matrix = aggregate_items(
            category_rows,
            value_cols,
            f"{year} {category}",
        )

        category_total = row_sum_complete(
            category_matrix,
            value_cols,
        ).reindex(
            social.index
        )

        category_item_count = (
            category_matrix["item_rows"]
            .reindex(
                social.index
            )
        )

        # Missing category records are treated as zero
        # ONLY for individual schools where ENR1/ENR2
        # reconciliation has been exact.
        if sparse_new_format:

            absent_and_exact = (
                category_item_count.isna()
                & exact_for_school
            )

            category_total = category_total.mask(
                absent_and_exact,
                0,
            )

        features[
            f"enrollment_{category}_total"
        ] = category_total

        features[
            f"enrollment_{category}_item_present"
        ] = category_item_count.notna()

    # --------------------------------------------------------
    # L. AGE-WISE FEATURES
    # --------------------------------------------------------

    age_tokens = sorted(
        age_rows["_item_token"].dropna().unique()
    )

    for token in age_tokens:

        token_rows = age_rows[
            age_rows["_item_token"].eq(token)
        ].copy()

        token_matrix = aggregate_items(
            token_rows,
            value_cols,
            f"{year} Age Item {token}",
        )

        token_total = row_sum_complete(
            token_matrix,
            value_cols,
        ).reindex(
            social.index
        )

        token_item_count = (
            token_matrix["item_rows"]
            .reindex(
                social.index
            )
        )

        # Sparse Age ID row absence is zero only for schools
        # whose full ENR1/ENR2 reconciliation is exact.
        if sparse_new_format:

            absent_and_exact = (
                token_item_count.isna()
                & exact_for_school
            )

            token_total = token_total.mask(
                absent_and_exact,
                0,
            )

        feature_name = age_feature_name(
            token,
            enr2_code_mode,
        )

        if feature_name in features.columns:

            raise ValueError(
                f"{year}: Duplicate age feature name: "
                f"{feature_name}"
            )

        features[feature_name] = token_total

    # --------------------------------------------------------
    # M. QUALITY STATUS
    # --------------------------------------------------------

    quality_status = pd.Series(
        "SOURCE_INCOMPLETE",
        index=social.index,
        dtype="string",
    )

    quality_status.loc[
        student_total.notna()
        & exact_for_school
    ] = "VALIDATED_ENR1_ENR2_EXACT"

    quality_status.loc[
        student_total.notna()
        & ~exact_for_school
    ] = "REVIEW_SOURCE_DIFFERENCE"

    features["enrollment_quality_status"] = (
        quality_status
    )

    features = features.reset_index()

    # --------------------------------------------------------
    # N. YEAR SUMMARY
    # --------------------------------------------------------

    year_summary = {
        "academic_year": year,
        "enr1_rows": len(enr1),
        "enr2_rows": len(enr2),
        "enr1_unique_schools": (
            enr1["school_id"].nunique()
        ),
        "enr2_unique_schools": (
            enr2["school_id"].nunique()
        ),
        "social_category_schools": len(social),
        "age_wise_schools": len(age),
        "social_four_item_schools": int(
            social["item_rows"].eq(4).sum()
        ),
        "common_schools": len(common_ids),
        "compared_cells": check["comparable_cells"],
        "exact_cells": check["exact_cells"],
        "mismatch_cells": check["mismatch_cells"],
        "cell_match_percentage": (
            round(
                check["cell_match_percentage"],
                4,
            )
            if pd.notna(
                check["cell_match_percentage"]
            )
            else np.nan
        ),
        "student_total_source_complete_schools": int(
            student_total_eligible.sum()
        ),
        "student_total_validated_schools": int(
            (
                student_total.notna()
                & exact_for_school
            ).sum()
        ),
        "student_total_review_schools": int(
            (
                student_total.notna()
                & ~exact_for_school
            ).sum()
        ),
        "student_total_unavailable_in_source": int(
            social_total.isna().sum()
        ),
        "value_columns": len(value_cols),
        "gender_field_schema": (
            "B_G_T_SEPARATE"
            if any(
                c.lower().endswith("_t")
                for c in value_cols
            )
            else "LEGACY_B_G_FIELDS"
        ),
    }

    print(
        f"Source format: "
        f"{'NEW CODED' if enr1_code_mode else 'LEGACY LABELLED'}"
    )

    print(
        f"Social category schools: {len(social):,}"
    )

    print(
        f"Age-wise schools: {len(age):,}"
    )

    print(
        "ENR1/ENR2 exact match:",
        f"{year_summary['cell_match_percentage']}%",
    )

    print(
        "Student total source-complete schools:",
        year_summary[
            "student_total_source_complete_schools"
        ],
    )

    print(
        "Student total cross-source validated schools:",
        year_summary[
            "student_total_validated_schools"
        ],
    )

    print(
        "Student total review schools:",
        year_summary[
            "student_total_review_schools"
        ],
    )

    return (
        features,
        year_summary,
    )


# ============================================================
# 8. PROCESS ALL ACADEMIC YEARS
# ============================================================

school_year_outputs = []
year_summaries = []
district_year_outputs = []

print("\n" + "=" * 70)
print("STARTING ALL-YEAR ENROLLMENT ENGINEERING")
print("=" * 70)


for year in YEARS:

    # --------------------------------------------------------
    # A. BUILD ENROLLMENT FEATURES
    # --------------------------------------------------------

    feature_df, year_summary = (
        build_year_features(year)
    )

    # --------------------------------------------------------
    # B. LOAD INTEGRATED SCHOOL MASTER
    # --------------------------------------------------------

    master_file = (
        SCHOOL_MASTER_DIR
        / f"maharashtra_school_year_integrated_{year}.csv"
    )

    if not master_file.exists():

        raise FileNotFoundError(
            f"School master not found:\n{master_file}"
        )

    master_raw = pd.read_csv(
        master_file,
        dtype=str,
        low_memory=False,
        encoding="utf-8-sig",
    )

    master_id_col = find_column(
        master_raw.columns,
        [
            "school_id",
            "schoolid",
            "udise_code",
            "udisecode",
            "pseudocode",
            "psuedocode",
            "school_code",
            "schoolcode",
        ],
    )

    district_col = find_column(
        master_raw.columns,
        [
            "district",
            "district_std",
            "district_standardized",
            "district_name",
            "district_clean",
        ],
    )

    if master_id_col is None:

        raise ValueError(
            f"{year}: School ID column not found "
            "in integrated master."
        )

    if district_col is None:

        raise ValueError(
            f"{year}: District column not found "
            "in integrated master."
        )

    master = pd.DataFrame({
        "school_id": clean_ids(
            master_raw[master_id_col]
        ),
        "district": (
            master_raw[district_col]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        ),
    })

    if master[
        ["school_id", "district"]
    ].isna().any().any():

        raise ValueError(
            f"{year}: Missing School ID or district "
            "in integrated master."
        )

    if master["school_id"].duplicated().any():

        raise ValueError(
            f"{year}: Duplicate School IDs "
            "in integrated master."
        )

    district_count = master["district"].nunique()

    if district_count != EXPECTED_DISTRICTS:

        raise ValueError(
            f"{year}: Expected 36 districts, "
            f"found {district_count}."
        )

    # --------------------------------------------------------
    # C. VALIDATE ENROLLMENT SCHOOL IDS
    # --------------------------------------------------------

    feature_df["school_id"] = clean_ids(
        feature_df["school_id"]
    )

    if feature_df["school_id"].isna().any():

        raise ValueError(
            f"{year}: Missing School IDs in features."
        )

    if feature_df["school_id"].duplicated().any():

        raise ValueError(
            f"{year}: Duplicate School IDs "
            "in Enrollment features."
        )

    master_ids = set(
        master["school_id"].dropna()
    )

    feature_ids = set(
        feature_df["school_id"].dropna()
    )

    extra_ids = feature_ids - master_ids

    if extra_ids:

        raise ValueError(
            f"{year}: {len(extra_ids)} Enrollment IDs "
            "not found in Integrated School Master."
        )

    # --------------------------------------------------------
    # D. MERGE WITH ALL MASTER SCHOOLS
    # --------------------------------------------------------

    school_df = master.merge(
        feature_df,
        on="school_id",
        how="left",
        validate="one_to_one",
        indicator="_enrollment_merge",
    )

    school_df["academic_year"] = year

    school_df["enrollment_record_available"] = (
        school_df["_enrollment_merge"].eq("both")
    )

    school_df["enrollment_merge_status"] = (
        school_df["_enrollment_merge"].map({
            "both": "MATCHED",
            "left_only": "NO_ENROLLMENT_RECORD",
            "right_only": "UNEXPECTED_RECORD",
        })
    )

    school_df["enrollment_total_available"] = (
        school_df["student_total"].notna()
    )

    school_df = school_df.drop(
        columns=["_enrollment_merge"]
    )

    if len(school_df) != len(master):

        raise ValueError(
            f"{year}: School count changed after merge."
        )

    if school_df["school_id"].duplicated().any():

        raise ValueError(
            f"{year}: Duplicate School IDs after merge."
        )

    # --------------------------------------------------------
    # E. SAVE YEAR-WISE SCHOOL FEATURES
    # --------------------------------------------------------

    school_output_file = (
        SCHOOL_OUTPUT_DIR
        / f"maharashtra_enrollment_features_{year}.csv"
    )

    school_df.to_csv(
        school_output_file,
        index=False,
        encoding="utf-8-sig",
    )

    school_year_outputs.append(
        school_df
    )

    year_summaries.append(
        year_summary
    )

    # --------------------------------------------------------
    # F. DISTRICT-YEAR AGGREGATION
    # --------------------------------------------------------

    for district, group in school_df.groupby(
        "district",
        sort=True,
    ):

        valid_total = (
            group["student_total"].notna()
        )

        reporting_count = int(
            valid_total.sum()
        )

        reported_total = (
            group.loc[
                valid_total,
                "student_total",
            ].sum(min_count=1)
        )

        district_record = {
            "academic_year": year,
            "district": district,
            "total_schools": len(group),

            "enrollment_reporting_schools": (
                reporting_count
            ),

            "enrollment_missing_schools": (
                len(group) - reporting_count
            ),

            "enrollment_coverage_pct": (
                round(
                    reporting_count / len(group) * 100,
                    2,
                )
                if len(group)
                else np.nan
            ),

            "reported_student_total": (
                reported_total
            ),

            "enrollment_validated_schools": int(
                group[
                    "student_total_validated"
                ].fillna(False).astype(bool).sum()
            ),

            "enrollment_review_schools": int(
                group[
                    "enrollment_quality_status"
                ].eq(
                    "REVIEW_SOURCE_DIFFERENCE"
                ).sum()
            ),

            "enrollment_record_available_schools": int(
                group[
                    "enrollment_record_available"
                ].fillna(False).sum()
            ),
        }

        # ----------------------------------------------------
        # SOCIAL CATEGORY DISTRICT TOTALS
        # ----------------------------------------------------

        for category in SOCIAL_CATEGORIES:

            col = (
                f"enrollment_{category}_total"
            )

            if col not in group.columns:
                continue

            valid_category = (
                group[col].notna()
            )

            district_record[
                f"reported_{category}_enrollment"
            ] = group.loc[
                valid_category,
                col,
            ].sum(min_count=1)

            district_record[
                f"{category}_reporting_schools"
            ] = int(
                valid_category.sum()
            )

        # ----------------------------------------------------
        # GRADE-WISE DISTRICT TOTALS
        # ----------------------------------------------------

        grade_cols = [
            col
            for col in group.columns
            if re.fullmatch(
                r"enrollment_(cpp|c(?:[1-9]|1[0-2]))_total",
                col,
            )
        ]

        for col in grade_cols:

            valid_grade = group[col].notna()

            district_record[
                f"reported_{col}"
            ] = group.loc[
                valid_grade,
                col,
            ].sum(min_count=1)

            district_record[
                f"{col}_reporting_schools"
            ] = int(
                valid_grade.sum()
            )

        # ----------------------------------------------------
        # REPORTED B/G/T COMPONENT TOTALS
        # ----------------------------------------------------

        for suffix in [
            "b",
            "g",
            "t",
        ]:

            col = (
                f"enrollment_{suffix}_component_total"
            )

            if col not in group.columns:
                continue

            valid_gender = group[col].notna()

            district_record[
                f"reported_{col}"
            ] = group.loc[
                valid_gender,
                col,
            ].sum(min_count=1)

            district_record[
                f"{col}_reporting_schools"
            ] = int(
                valid_gender.sum()
            )

        # ----------------------------------------------------
        # AGE / AGE-ID DISTRICT TOTALS
        # ----------------------------------------------------

        age_cols = [
            col
            for col in group.columns
            if col.startswith("age_")
            and col.endswith("_reported_total")
        ]

        for col in age_cols:

            valid_age = group[col].notna()

            district_record[
                f"reported_{col}"
            ] = group.loc[
                valid_age,
                col,
            ].sum(min_count=1)

            district_record[
                f"{col}_reporting_schools"
            ] = int(
                valid_age.sum()
            )

        district_year_outputs.append(
            district_record
        )

    # --------------------------------------------------------
    # G. YEAR RESULT
    # --------------------------------------------------------

    print("\nYEAR RESULT:")
    print(f"Academic Year: {year}")
    print(f"School records: {len(school_df):,}")

    print(
        "Enrollment records available:",
        int(
            school_df[
                "enrollment_record_available"
            ].sum()
        ),
    )

    print(
        "Student total available:",
        int(
            school_df[
                "student_total"
            ].notna().sum()
        ),
    )

    print(
        "Student total unavailable:",
        int(
            school_df[
                "student_total"
            ].isna().sum()
        ),
    )

    print(
        "Saved:",
        school_output_file,
    )

    del master_raw
    del master
    del feature_df
    del school_df

    gc.collect()


# ============================================================
# 9. BUILD ALL-YEAR SCHOOL MASTER
# ============================================================

print("\n" + "=" * 70)
print("BUILDING ENROLLMENT SCHOOL MASTER")
print("=" * 70)

school_master = pd.concat(
    school_year_outputs,
    ignore_index=True,
)

school_master_file = (
    SCHOOL_OUTPUT_DIR
    / "maharashtra_enrollment_features_master.csv"
)

school_master.to_csv(
    school_master_file,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# 10. BUILD DISTRICT-YEAR MASTER
# ============================================================

print("\n" + "=" * 70)
print("BUILDING DISTRICT-YEAR ENROLLMENT MASTER")
print("=" * 70)

district_master = pd.DataFrame(
    district_year_outputs
)

district_master = district_master.sort_values(
    [
        "academic_year",
        "district",
    ]
).reset_index(drop=True)

expected_district_rows = (
    len(YEARS)
    * EXPECTED_DISTRICTS
)

if len(district_master) != expected_district_rows:

    raise ValueError(
        f"Expected {expected_district_rows} "
        f"district-year rows, found {len(district_master)}."
    )

district_duplicates = district_master.duplicated(
    subset=[
        "academic_year",
        "district",
    ]
).sum()

if district_duplicates:

    raise ValueError(
        f"Duplicate district-year records: "
        f"{district_duplicates}"
    )

district_master_file = (
    DISTRICT_OUTPUT_DIR
    / "maharashtra_district_year_enrollment_features.csv"
)

district_master.to_csv(
    district_master_file,
    index=False,
    encoding="utf-8-sig",
)

# Save individual academic years.
for year in YEARS:

    year_df = district_master[
        district_master["academic_year"] == year
    ]

    year_file = (
        DISTRICT_OUTPUT_DIR
        / f"maharashtra_district_year_enrollment_{year}.csv"
    )

    year_df.to_csv(
        year_file,
        index=False,
        encoding="utf-8-sig",
    )


# ============================================================
# 11. SAVE AUDIT REPORTS
# ============================================================

print("\n" + "=" * 70)
print("SAVING ENROLLMENT AUDIT REPORTS")
print("=" * 70)

year_summary_df = pd.DataFrame(
    year_summaries
)

year_summary_file = (
    REPORT_DIR
    / "enrollment_feature_engineering_summary.csv"
)

year_summary_df.to_csv(
    year_summary_file,
    index=False,
    encoding="utf-8-sig",
)

district_coverage_file = (
    REPORT_DIR
    / "district_year_enrollment_feature_coverage.csv"
)

coverage_columns = [
    "academic_year",
    "district",
    "total_schools",
    "enrollment_record_available_schools",
    "enrollment_reporting_schools",
    "enrollment_missing_schools",
    "enrollment_coverage_pct",
    "reported_student_total",
    "enrollment_validated_schools",
    "enrollment_review_schools",
]

district_master[
    coverage_columns
].to_csv(
    district_coverage_file,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# 12. FINAL VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("ENROLLMENT FEATURE ENGINEERING - FINAL VALIDATION")
print("=" * 70)

school_duplicates = school_master.duplicated(
    subset=[
        "academic_year",
        "school_id",
    ]
).sum()

district_duplicates = district_master.duplicated(
    subset=[
        "academic_year",
        "district",
    ]
).sum()

if school_duplicates:

    raise ValueError(
        f"Duplicate school-year records: "
        f"{school_duplicates}"
    )

if district_duplicates:

    raise ValueError(
        f"Duplicate district-year records: "
        f"{district_duplicates}"
    )

# Year-wise validation.
for year in YEARS:

    year_data = district_master[
        district_master["academic_year"] == year
    ]

    if len(year_data) != EXPECTED_DISTRICTS:

        raise ValueError(
            f"{year}: Expected 36 district records, "
            f"found {len(year_data)}."
        )

    if year_data["district"].nunique() != EXPECTED_DISTRICTS:

        raise ValueError(
            f"{year}: Unique district validation failed."
        )


# ------------------------------------------------------------
# FINAL OUTPUT
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("ENROLLMENT FEATURE ENGINEERING - FINAL RESULT")
print("=" * 70)

print(f"Academic years: {len(YEARS)}")

print(
    f"School-year records: "
    f"{len(school_master):,}"
)

print(
    "Unique school-year keys:",
    school_master[
        [
            "academic_year",
            "school_id",
        ]
    ].drop_duplicates().shape[0],
)

print(
    f"District-year records: "
    f"{len(district_master):,}"
)

print(
    f"Expected district-year records: "
    f"{expected_district_rows}"
)

print(
    f"School-year duplicate records: "
    f"{school_duplicates}"
)

print(
    f"District-year duplicate records: "
    f"{district_duplicates}"
)

print("\nYEAR-WISE ENROLLMENT RECONCILIATION:")

summary_columns = [
    "academic_year",
    "common_schools",
    "cell_match_percentage",
    "mismatch_cells",
    "student_total_source_complete_schools",
    "student_total_validated_schools",
    "student_total_review_schools",
    "value_columns",
]

print(
    year_summary_df[
        summary_columns
    ].to_string(index=False)
)

print("\nOUTPUT FILES:")

print("\nSCHOOL-LEVEL MASTER:")
print(school_master_file)

print("\nDISTRICT-YEAR MASTER:")
print(district_master_file)

print("\nAUDIT REPORTS:")
print(year_summary_file)
print(district_coverage_file)

print("\nIMPORTANT:")
print("- ENR1 Social Category is the primary source.")
print("- ENR2 Age-wise data is used for cross-validation.")
print("- Age<5 and Age5 are separate categories.")
print("- Group 5 Item 0 is excluded.")
print("- Age IDs are not decoded into actual ages.")
print("- Missing schools remain NA, not zero.")
print("- Old-year source differences are marked REVIEW.")
print("- New-year totals require exact cross-source matches.")
print("- Raw source files remain unchanged.")

print("\n" + "=" * 70)
print("ENROLLMENT FEATURE ENGINEERING COMPLETED")
print("STATUS: PASS")
print("=" * 70)

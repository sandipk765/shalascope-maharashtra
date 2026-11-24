
from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

EXTRACTED = ROOT / "data" / "extracted"
MASTER_DIR = ROOT / "data" / "processed" / "school_year"
REPORT_DIR = ROOT / "reports" / "data_audit"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [
    "2018-19", "2019-20", "2020-21", "2021-22",
    "2022-23", "2023-24", "2024-25", "2025-26"
]

VALIDATION = []
ITEMS = []
FIELD_PROFILES = []


def find_source_files(year_dir):
    found = {
        "ENROLLMENT": [],
        "FACILITY": []
    }

    for path in year_dir.rglob("*.csv"):
        stem = path.stem.lower()

        if stem.endswith("_enr1") or stem.endswith("_enr2"):
            found["ENROLLMENT"].append(path)

        elif stem.endswith("_fac"):
            found["FACILITY"].append(path)

    return found


def find_id_column(df):
    for col in ["psuedocode", "pseudocode", "school_id"]:
        if col in df.columns:
            return col
    return None


def clean_ids(series):
    return series.astype("string").str.strip()


def get_duplicate_key_count(df, id_col, source_type):

    if source_type == "FACILITY":
        keys = [id_col]

    elif "item_desc" in df.columns:
        keys = [id_col, "item_desc"]

    elif {"item_group", "item_id"}.issubset(df.columns):
        keys = [id_col, "item_group", "item_id"]

    else:
        return None

    return int(df.duplicated(subset=keys).sum())


def profile_fields(df, year, filename, source_type, id_col):

    descriptor_cols = {
        id_col,
        "item_desc",
        "item_group",
        "item_id"
    }

    for col in df.columns:

        if col in descriptor_cols:
            continue

        raw = df[col].astype("string").str.strip()

        blank = raw.isna() | raw.eq("").fillna(False)

        cleaned = raw.str.replace(",", "", regex=False)

        numeric = pd.to_numeric(
            cleaned,
            errors="coerce"
        )

        nonblank = int((~blank).sum())
        numeric_count = int(numeric.notna().sum())

        nonnumeric = int(
            ((~blank) & numeric.isna()).sum()
        )

        unique_count = int(raw.nunique(dropna=True))

        zero_count = int(
            numeric.eq(0).sum()
        )

        negative_count = int(
            numeric.lt(0).sum()
        )

        valid_numeric = numeric.dropna()

        min_value = (
            float(valid_numeric.min())
            if len(valid_numeric) else None
        )

        max_value = (
            float(valid_numeric.max())
            if len(valid_numeric) else None
        )

        top_values = (
            raw.value_counts(dropna=False)
            .head(12)
            .to_dict()
        )

        top_text = " | ".join(
            f"{k}:{v}" for k, v in top_values.items()
        )

        FIELD_PROFILES.append({
            "academic_year": year,
            "source_type": source_type,
            "file_name": filename,
            "field": col,
            "rows": len(df),
            "blank_values": int(blank.sum()),
            "nonblank_values": nonblank,
            "distinct_values": unique_count,
            "numeric_values": numeric_count,
            "nonnumeric_values": nonnumeric,
            "zero_values": zero_count,
            "negative_values": negative_count,
            "minimum": min_value,
            "maximum": max_value,
            "raw_top_values": top_text,
        })


def audit_enrollment_descriptors(df, year, filename):

    if "item_desc" in df.columns:

        grouped = (
            df.assign(
                item_desc=df["item_desc"].fillna("[BLANK]")
            )
            .groupby("item_desc", dropna=False)
            .agg(
                records=("item_desc", "size")
            )
            .reset_index()
        )

        for _, row in grouped.iterrows():
            ITEMS.append({
                "academic_year": year,
                "file_name": filename,
                "item_group": "",
                "item_id": "",
                "item_desc": row["item_desc"],
                "record_count": int(row["records"])
            })

    elif {"item_group", "item_id"}.issubset(df.columns):

        grouped = (
            df.assign(
                item_group=df["item_group"].fillna("[BLANK]"),
                item_id=df["item_id"].fillna("[BLANK]")
            )
            .groupby(
                ["item_group", "item_id"],
                dropna=False
            )
            .size()
            .reset_index(name="record_count")
        )

        for _, row in grouped.iterrows():
            ITEMS.append({
                "academic_year": year,
                "file_name": filename,
                "item_group": row["item_group"],
                "item_id": row["item_id"],
                "item_desc": "",
                "record_count": int(row["record_count"])
            })


def audit_file(path, year, source_type, master_ids):

    print(f"\nChecking: {year} | {path.name}")

    df = pd.read_csv(
        path,
        dtype="string",
        encoding="utf-8-sig",
        low_memory=False
    )

    id_col = find_id_column(df)

    if id_col is None:
        raise ValueError("School ID column not found")

    ids = clean_ids(df[id_col])

    missing_ids = int(
        ids.isna().sum() + ids.eq("").fillna(False).sum()
    )

    valid_ids = set(
        ids.dropna().loc[lambda x: x.ne("")].tolist()
    )

    matched_ids = valid_ids.intersection(master_ids)

    unmatched_ids = valid_ids.difference(master_ids)

    duplicate_keys = get_duplicate_key_count(
        df, id_col, source_type
    )

    audit_enrollment_descriptors(
        df, year, path.name
    ) if source_type == "ENROLLMENT" else None

    profile_fields(
        df, year, path.name, source_type, id_col
    )

    status = "PASS"

    if (
        missing_ids > 0
        or len(unmatched_ids) > 0
        or duplicate_keys is None
        or duplicate_keys > 0
    ):
        status = "REVIEW_REQUIRED"

    record = {
        "academic_year": year,
        "source_type": source_type,
        "file_name": path.name,
        "records": len(df),
        "columns": len(df.columns),
        "id_column": id_col,
        "unique_school_ids": len(valid_ids),
        "matched_master_ids": len(matched_ids),
        "unmatched_school_ids": len(unmatched_ids),
        "missing_id_rows": missing_ids,
        "duplicate_key_rows": duplicate_keys,
        "status": status
    }

    VALIDATION.append(record)

    print(
        f"Rows={len(df):,} | "
        f"Unique IDs={len(valid_ids):,} | "
        f"Matched={len(matched_ids):,} | "
        f"Unmatched={len(unmatched_ids)} | "
        f"Duplicate keys={duplicate_keys} | "
        f"Status={status}"
    )


def main():

    print("\n" + "=" * 75)
    print("SHALASCOPE MAHARASHTRA")
    print("ENROLLMENT + FACILITY VALUE AND JOIN AUDIT")
    print("=" * 75)

    for year in YEARS:

        year_dir = EXTRACTED / year

        master_path = (
            MASTER_DIR
            / f"maharashtra_school_year_master_{year}.csv"
        )

        if not year_dir.exists():
            print(f"\nMISSING YEAR DIRECTORY: {year}")
            continue

        if not master_path.exists():
            print(f"\nMISSING MASTER FILE: {year}")
            continue

        master = pd.read_csv(
            master_path,
            usecols=["school_id"],
            dtype={"school_id": "string"}
        )

        master_ids = set(
            clean_ids(master["school_id"])
            .dropna()
            .loc[lambda x: x.ne("")]
            .tolist()
        )

        sources = find_source_files(year_dir)

        print(f"\n{'=' * 60}")
        print(f"ACADEMIC YEAR: {year}")
        print(f"Master School IDs: {len(master_ids):,}")

        for source_type, paths in sources.items():

            expected = 2 if source_type == "ENROLLMENT" else 1

            print(
                f"\n{source_type}: "
                f"{len(paths)} file(s), expected {expected}"
            )

            if len(paths) != expected:
                VALIDATION.append({
                    "academic_year": year,
                    "source_type": source_type,
                    "file_name": "",
                    "records": 0,
                    "columns": 0,
                    "id_column": "",
                    "unique_school_ids": 0,
                    "matched_master_ids": 0,
                    "unmatched_school_ids": 0,
                    "missing_id_rows": 0,
                    "duplicate_key_rows": None,
                    "status": "FILE_COUNT_REVIEW"
                })

            for path in sorted(paths):

                try:
                    audit_file(
                        path,
                        year,
                        source_type,
                        master_ids
                    )

                except Exception as exc:

                    print(
                        f"ERROR: {path.name}: {exc}"
                    )

                    VALIDATION.append({
                        "academic_year": year,
                        "source_type": source_type,
                        "file_name": path.name,
                        "records": 0,
                        "columns": 0,
                        "id_column": "",
                        "unique_school_ids": 0,
                        "matched_master_ids": 0,
                        "unmatched_school_ids": 0,
                        "missing_id_rows": 0,
                        "duplicate_key_rows": None,
                        "status": "FAILED"
                    })

    # Save reports
    validation_df = pd.DataFrame(VALIDATION)
    items_df = pd.DataFrame(ITEMS)
    profile_df = pd.DataFrame(FIELD_PROFILES)

    validation_path = (
        REPORT_DIR
        / "enrollment_facility_source_validation.csv"
    )

    items_path = (
        REPORT_DIR
        / "enrollment_item_inventory.csv"
    )

    profile_path = (
        REPORT_DIR
        / "enrollment_facility_value_profile.csv"
    )

    validation_df.to_csv(
        validation_path,
        index=False,
        encoding="utf-8-sig"
    )

    items_df.to_csv(
        items_path,
        index=False,
        encoding="utf-8-sig"
    )

    profile_df.to_csv(
        profile_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 75)
    print("SOURCE VALIDATION SUMMARY")
    print("=" * 75)

    if not validation_df.empty:
        print(
            validation_df.to_string(index=False)
        )

    print("\n" + "=" * 75)
    print("ENROLLMENT ITEM DESCRIPTORS / IDS")
    print("=" * 75)

    if not items_df.empty:
        print(items_df.to_string(index=False))

    print("\n" + "=" * 75)
    print("FINAL COUNTS")
    print("=" * 75)

    print(f"Files audited: {len(validation_df)}")
    print(f"Enrollment item rows: {len(items_df)}")
    print(f"Field profiles: {len(profile_df)}")

    print("\nReports saved:")
    print(validation_path)
    print(items_path)
    print(profile_path)

    failed = (
        validation_df["status"]
        .isin(["FAILED", "REVIEW_REQUIRED", "FILE_COUNT_REVIEW"])
        .any()
    ) if not validation_df.empty else True

    if failed:
        print("\nFINAL STATUS: REVIEW REQUIRED")
    else:
        print("\nFINAL STATUS: SOURCE AUDIT PASS")

    print("\nAUDIT COMPLETED")


if __name__ == "__main__":
    main()

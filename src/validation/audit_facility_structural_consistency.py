
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

SOURCE_DIR = ROOT / "data" / "extracted"
MASTER_DIR = ROOT / "data" / "processed" / "school_year"
REPORT_DIR = ROOT / "reports" / "data_audit"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [
    "2018-19", "2019-20", "2020-21", "2021-22",
    "2022-23", "2023-24", "2024-25", "2025-26"
]

SUMMARY = []
EXCEPTIONS = []


def find_facility_file(year):

    matches = [
        p for p in (SOURCE_DIR / year).rglob("*.csv")
        if p.name.lower().endswith("_fac.csv")
    ]

    if len(matches) != 1:
        raise FileNotFoundError(
            f"{year}: Expected one Facility CSV, found {len(matches)}"
        )

    return matches[0]


def numeric_column(df, col):

    if col not in df.columns:
        return pd.Series(
            float("nan"),
            index=df.index,
            dtype="float64"
        )

    return pd.to_numeric(
        df[col]
        .astype("string")
        .str.strip()
        .str.replace(",", "", regex=False),
        errors="coerce"
    )


def main():

    print("\n" + "=" * 70)
    print("SHALASCOPE MAHARASHTRA")
    print("FACILITY STRUCTURAL CONSISTENCY AUDIT")
    print("=" * 70)

    for year in YEARS:

        print(f"\nProcessing: {year}")

        path = find_facility_file(year)

        master_path = (
            MASTER_DIR
            / f"maharashtra_school_year_master_{year}.csv"
        )

        master = pd.read_csv(
            master_path,
            usecols=["school_id", "district"],
            dtype={"school_id": "string"}
        )

        master["school_id"] = (
            master["school_id"].str.strip()
        )

        district_map = dict(
            zip(master["school_id"], master["district"])
        )

        df = pd.read_csv(
            path,
            dtype="string",
            low_memory=False,
            encoding="utf-8-sig"
        )

        id_col = next(
            (
                c for c in [
                    "psuedocode",
                    "pseudocode",
                    "school_id"
                ]
                if c in df.columns
            ),
            None
        )

        if id_col is None:
            raise ValueError(
                f"{year}: Facility School ID column missing"
            )

        df["school_id"] = df[id_col].str.strip()

        df["district"] = df["school_id"].map(
            district_map
        )

        # ------------------------------------------------
        # BUILDING BLOCK COUNTS
        # ------------------------------------------------

        building_total = numeric_column(
            df, "no_building_blocks"
        )

        pucca = numeric_column(
            df, "pucca_building_blocks"
        )

        block_zero = building_total.eq(0)

        pucca_positive = pucca.gt(0)

        block_zero_with_pucca = (
            block_zero & pucca_positive
        )

        block_less_than_pucca = (
            building_total.notna()
            & pucca.notna()
            & (building_total < pucca)
        )

        # ------------------------------------------------
        # CLASSROOM COUNTS
        # ------------------------------------------------

        total_rooms = numeric_column(
            df, "total_class_rooms"
        )

        good = numeric_column(
            df, "classrooms_in_good_condition"
        )

        minor = numeric_column(
            df, "classrooms_needs_minor_repair"
        )

        major = numeric_column(
            df, "classrooms_needs_major_repair"
        )

        condition_df = pd.concat(
            [good, minor, major],
            axis=1
        )

        any_condition_positive = (
            condition_df.gt(0).any(axis=1)
        )

        rooms_zero = total_rooms.eq(0)

        room_zero_with_condition = (
            rooms_zero & any_condition_positive
        )

        # ------------------------------------------------
        # RECORD-LEVEL EXCEPTIONS
        # ------------------------------------------------

        exception_mask = (
            block_zero_with_pucca
            | block_less_than_pucca
            | room_zero_with_condition
        )

        for idx in df.index[exception_mask]:

            EXCEPTIONS.append({
                "academic_year": year,
                "school_id": df.at[idx, "school_id"],
                "district": df.at[idx, "district"],
                "no_building_blocks": building_total.at[idx],
                "pucca_building_blocks": pucca.at[idx],
                "total_class_rooms": total_rooms.at[idx],
                "classrooms_in_good_condition": good.at[idx],
                "classrooms_needs_minor_repair": minor.at[idx],
                "classrooms_needs_major_repair": major.at[idx],
                "block_zero_with_pucca": bool(
                    block_zero_with_pucca.at[idx]
                ),
                "block_less_than_pucca": bool(
                    block_less_than_pucca.at[idx]
                ),
                "room_zero_with_positive_condition": bool(
                    room_zero_with_condition.at[idx]
                ),
            })

        # ------------------------------------------------
        # SUMMARY
        # ------------------------------------------------

        missing_ids = int(
            df["school_id"].isna().sum()
        )

        duplicate_ids = int(
            df["school_id"].duplicated().sum()
        )

        record = {
            "academic_year": year,
            "source_rows": len(df),
            "unique_school_ids": df["school_id"].nunique(),
            "missing_school_ids": missing_ids,
            "duplicate_school_ids": duplicate_ids,
            "zero_building_block_records": int(
                block_zero.sum()
            ),
            "zero_blocks_with_positive_pucca": int(
                block_zero_with_pucca.sum()
            ),
            "building_total_less_than_pucca": int(
                block_less_than_pucca.sum()
            ),
            "zero_total_classroom_records": int(
                rooms_zero.sum()
            ),
            "zero_classrooms_with_positive_condition": int(
                room_zero_with_condition.sum()
            ),
            "structural_exception_records": int(
                exception_mask.sum()
            ),
        }

        record["status"] = (
            "REVIEW_REQUIRED"
            if (
                missing_ids
                or duplicate_ids
                or exception_mask.any()
            )
            else "PASS"
        )

        SUMMARY.append(record)

        print(
            f"Schools: {len(df):,} | "
            f"Block anomalies: {int(block_zero_with_pucca.sum())} | "
            f"Classroom anomalies: {int(room_zero_with_condition.sum())} | "
            f"Status: {record['status']}"
        )

    # ----------------------------------------------------
    # SAVE REPORTS
    # ----------------------------------------------------

    summary_df = pd.DataFrame(SUMMARY)
    exception_df = pd.DataFrame(EXCEPTIONS)

    summary_path = (
        REPORT_DIR
        / "facility_structural_consistency_summary.csv"
    )

    exception_path = (
        REPORT_DIR
        / "facility_structural_exceptions.csv"
    )

    summary_df.to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig"
    )

    exception_df.to_csv(
        exception_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 70)
    print("FINAL STRUCTURAL AUDIT SUMMARY")
    print("=" * 70)

    print(summary_df.to_string(index=False))

    print(f"\nYears Audited: {len(summary_df)}")
    print(f"Exception Records: {len(exception_df):,}")

    print("\nReports:")
    print(summary_path)
    print(exception_path)

    print("\nSTRUCTURAL CONSISTENCY AUDIT COMPLETED")


if __name__ == "__main__":
    main()

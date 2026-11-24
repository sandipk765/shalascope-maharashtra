
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "extracted"
MASTER = ROOT / "data" / "processed" / "school_year"
REPORT = ROOT / "reports" / "data_audit"

REPORT.mkdir(parents=True, exist_ok=True)

CHECK_YEARS = ["2021-22", "2023-24", "2024-25", "2025-26"]

FIELDS = [
    "no_building_blocks",
    "pucca_building_blocks",
    "total_class_rooms",
    "classrooms_in_good_condition",
    "classrooms_needs_minor_repair",
    "classrooms_needs_major_repair",
]

def find_facility(year):
    matches = [
        p for p in (SOURCE / year).rglob("*.csv")
        if p.name.lower().endswith("_fac.csv")
    ]
    if len(matches) != 1:
        raise FileNotFoundError(
            f"{year}: Expected one facility file, found {len(matches)}"
        )
    return matches[0]


def read_facility(year):

    path = find_facility(year)
    headers = pd.read_csv(path, nrows=0).columns.tolist()

    id_col = next(
        (c for c in ["psuedocode", "pseudocode", "school_id"]
         if c in headers),
        None
    )

    if id_col is None:
        raise ValueError(f"{year}: School ID column missing")

    selected = [id_col] + [
        c for c in FIELDS if c in headers
    ]

    df = pd.read_csv(
        path,
        usecols=selected,
        dtype="string",
        low_memory=False,
        encoding="utf-8-sig"
    )

    df = df.rename(columns={id_col: "school_id"})
    df["school_id"] = df["school_id"].str.strip()

    for col in FIELDS:
        if col not in df.columns:
            df[col] = pd.NA

        df[col + "_numeric"] = pd.to_numeric(
            df[col].str.strip().str.replace(",", "", regex=False),
            errors="coerce"
        )

    master_path = (
        MASTER / f"maharashtra_school_year_master_{year}.csv"
    )

    master = pd.read_csv(
        master_path,
        usecols=["school_id", "district"],
        dtype={"school_id": "string"}
    )

    master["school_id"] = master["school_id"].str.strip()

    district_map = dict(
        zip(master["school_id"], master["district"])
    )

    df["district"] = df["school_id"].map(district_map)

    return df


def main():

    datasets = {}
    frequency_rows = []
    district_rows = []

    print("\n========== RAW SOURCE YEAR COMPARISON ==========")

    for year in CHECK_YEARS:

        df = read_facility(year)
        datasets[year] = df

        print(f"\n{year}: {len(df):,} source records")

        for field in FIELDS:

            numeric = df[field + "_numeric"]
            counts = numeric.value_counts(dropna=False)

            for value, count in counts.items():
                frequency_rows.append({
                    "academic_year": year,
                    "field": field,
                    "raw_numeric_value": (
                        "[MISSING]" if pd.isna(value) else value
                    ),
                    "records": int(count)
                })

        block = df["no_building_blocks_numeric"]
        pucca = df["pucca_building_blocks_numeric"]

        rooms = df["total_class_rooms_numeric"]

        conditions = df[
            [
                "classrooms_in_good_condition_numeric",
                "classrooms_needs_minor_repair_numeric",
                "classrooms_needs_major_repair_numeric",
            ]
        ]

        block_flag = block.eq(0) & pucca.gt(0)
        rooms_flag = rooms.eq(0) & conditions.gt(0).any(axis=1)

        flagged = block_flag | rooms_flag

        print("Block zero with positive Pucca:", int(block_flag.sum()))
        print("Classroom zero with positive condition:", int(rooms_flag.sum()))

        district_check = df.assign(
            block_anomaly=block_flag,
            classroom_anomaly=rooms_flag
        ).groupby("district", dropna=False).agg(
            schools=("school_id", "nunique"),
            block_anomalies=("block_anomaly", "sum"),
            classroom_anomalies=("classroom_anomaly", "sum")
        ).reset_index()

        district_check["academic_year"] = year
        district_rows.append(district_check)

    # ------------------------------------------------
    # SELECT 2024-25 ANOMALOUS SCHOOLS
    # ------------------------------------------------

    target = datasets["2024-25"].copy()

    block_flag = (
        target["no_building_blocks_numeric"].eq(0)
        & target["pucca_building_blocks_numeric"].gt(0)
    )

    room_flag = (
        target["total_class_rooms_numeric"].eq(0)
        & target[
            [
                "classrooms_in_good_condition_numeric",
                "classrooms_needs_minor_repair_numeric",
                "classrooms_needs_major_repair_numeric",
            ]
        ].gt(0).any(axis=1)
    )

    sample_ids = set(
        target.loc[block_flag, "school_id"].dropna().head(30)
    )

    sample_ids.update(
        target.loc[room_flag, "school_id"].dropna().head(30)
    )

    # Include Government-wide representative anomalies
    # and compare exactly the same School IDs across years.

    comparison_rows = []

    for year, df in datasets.items():

        subset = df[df["school_id"].isin(sample_ids)].copy()

        for _, row in subset.iterrows():

            comparison_rows.append({
                "academic_year": year,
                "school_id": row["school_id"],
                "district": row["district"],
                "no_building_blocks": row["no_building_blocks"],
                "pucca_building_blocks": row["pucca_building_blocks"],
                "total_class_rooms": row["total_class_rooms"],
                "classrooms_in_good_condition":
                    row["classrooms_in_good_condition"],
                "classrooms_needs_minor_repair":
                    row["classrooms_needs_minor_repair"],
                "classrooms_needs_major_repair":
                    row["classrooms_needs_major_repair"],
            })

    comparison = pd.DataFrame(comparison_rows)

    frequency_path = (
        REPORT / "facility_anomaly_cross_year_frequencies.csv"
    )

    comparison_path = (
        REPORT / "facility_anomaly_cross_year_school_samples.csv"
    )

    district_path = (
        REPORT / "facility_anomaly_cross_year_district_summary.csv"
    )

    pd.DataFrame(frequency_rows).to_csv(
        frequency_path,
        index=False,
        encoding="utf-8-sig"
    )

    comparison.to_csv(
        comparison_path,
        index=False,
        encoding="utf-8-sig"
    )

    pd.concat(district_rows, ignore_index=True).to_csv(
        district_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n========== FINAL COMPARISON ==========")
    print("2024-25 Anomalous Sample School IDs:", len(sample_ids))
    print("Cross-year Comparison Rows:", len(comparison))

    print("\nReports:")
    print(frequency_path)
    print(comparison_path)
    print(district_path)

    print("\nSOURCE COMPARISON COMPLETED")


if __name__ == "__main__":
    main()

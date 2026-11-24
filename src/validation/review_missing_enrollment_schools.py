
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

MASTER_DIR = ROOT / "data" / "processed" / "school_year"
EXTRACTED_DIR = ROOT / "data" / "extracted"
REPORT_DIR = ROOT / "reports" / "data_audit"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = ["2022-23", "2023-24"]


def locate_file(year, filename):
    matches = list(
        (EXTRACTED_DIR / year).rglob(filename)
    )

    if len(matches) != 1:
        raise FileNotFoundError(
            f"{year}: Expected one {filename}, found {len(matches)}"
        )

    return matches[0]


def load_ids(path):
    headers = pd.read_csv(path, nrows=0).columns.tolist()

    id_col = next(
        (c for c in ["psuedocode", "pseudocode", "school_id"]
         if c in headers),
        None
    )

    if id_col is None:
        raise ValueError(f"School ID column missing: {path}")

    df = pd.read_csv(
        path,
        usecols=[id_col],
        dtype={id_col: "string"}
    )

    return set(
        df[id_col].str.strip()
        .dropna()
        .loc[lambda x: x.ne("")]
        .tolist()
    )


all_gaps = []
summaries = []

print("\n========== ENROLLMENT MASTER ID GAP REVIEW ==========")

for year in YEARS:

    print(f"\nProcessing {year}...")

    master_path = (
        MASTER_DIR
        / f"maharashtra_school_year_master_{year}.csv"
    )

    master = pd.read_csv(
        master_path,
        usecols=["school_id", "district"],
        dtype={"school_id": "string"}
    )

    master["school_id"] = master["school_id"].str.strip()

    master = master.dropna(subset=["school_id"])
    master = master.drop_duplicates("school_id")

    master_ids = set(master["school_id"].tolist())

    district_map = dict(
        zip(master["school_id"], master["district"])
    )

    enr1_path = locate_file(year, "27_enr1.csv")
    enr2_path = locate_file(year, "27_enr2.csv")

    enr1_ids = load_ids(enr1_path)
    enr2_ids = load_ids(enr2_path)

    missing_enr1 = master_ids - enr1_ids
    missing_enr2 = master_ids - enr2_ids

    common_missing = missing_enr1 & missing_enr2
    only_enr1 = missing_enr1 - missing_enr2
    only_enr2 = missing_enr2 - missing_enr1

    for school_id in sorted(missing_enr1 | missing_enr2):

        all_gaps.append({
            "academic_year": year,
            "school_id": school_id,
            "district": district_map.get(school_id, "UNKNOWN"),
            "missing_from_enr1": school_id in missing_enr1,
            "missing_from_enr2": school_id in missing_enr2,
            "missing_from_both": school_id in common_missing,
        })

    summaries.append({
        "academic_year": year,
        "master_schools": len(master_ids),
        "enr1_unique_ids": len(enr1_ids),
        "enr2_unique_ids": len(enr2_ids),
        "missing_from_enr1": len(missing_enr1),
        "missing_from_enr2": len(missing_enr2),
        "missing_from_both": len(common_missing),
        "missing_only_enr1": len(only_enr1),
        "missing_only_enr2": len(only_enr2),
    })

    print(f"Master Schools       : {len(master_ids):,}")
    print(f"Missing from ENR1    : {len(missing_enr1)}")
    print(f"Missing from ENR2    : {len(missing_enr2)}")
    print(f"Missing from Both    : {len(common_missing)}")
    print(f"Missing only ENR1    : {len(only_enr1)}")
    print(f"Missing only ENR2    : {len(only_enr2)}")

gap_df = pd.DataFrame(all_gaps)
summary_df = pd.DataFrame(summaries)

gap_path = (
    REPORT_DIR / "enrollment_master_id_gaps_2022_2024.csv"
)

summary_path = (
    REPORT_DIR / "enrollment_master_id_gap_summary.csv"
)

gap_df.to_csv(gap_path, index=False, encoding="utf-8-sig")
summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

print("\n========== DISTRICT-WISE GAPS ==========")

if not gap_df.empty:
    district_summary = (
        gap_df.groupby(["academic_year", "district"])
        .agg(missing_school_ids=("school_id", "nunique"))
        .reset_index()
        .sort_values(
            ["academic_year", "missing_school_ids"],
            ascending=[True, False]
        )
    )

    print(district_summary.to_string(index=False))

    district_summary.to_csv(
        REPORT_DIR / "enrollment_missing_ids_by_district.csv",
        index=False,
        encoding="utf-8-sig"
    )
else:
    print("No missing enrollment school IDs.")

print("\n========== FINAL SUMMARY ==========")
print(summary_df.to_string(index=False))

print("\nDetailed Report:", gap_path)
print("Summary Report :", summary_path)
print("\nGAP REVIEW COMPLETED")

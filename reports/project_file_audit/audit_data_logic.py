from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
REPORT = ROOT / "reports" / "project_file_audit"

YEARS = [
    "2018-19", "2019-20", "2020-21", "2021-22",
    "2022-23", "2023-24", "2024-25", "2025-26"
]

SCHOOL_DIR = ROOT / "data" / "processed" / "school_year"
DISTRICT_DIR = ROOT / "data" / "processed" / "district_year"

results = []

def add(file, test, observed, expected, status):
    results.append({
        "File": str(file),
        "Test": test,
        "Observed": str(observed),
        "Expected": str(expected),
        "Status": status
    })

def find_col(columns, candidates):
    lookup = {str(c).strip().lower(): c for c in columns}

    for candidate in candidates:
        if candidate in lookup:
            return lookup[candidate]

    return None

def inspect_school_year(year):
    filename = f"maharashtra_school_year_master_{year}.csv"
    path = SCHOOL_DIR / filename

    if not path.exists():
        add(filename, "File exists", False, True, "FAIL")
        return

    header = pd.read_csv(path, nrows=0).columns.tolist()

    id_col = find_col(header, [
        "school_id", "school_code", "udise_code",
        "udise_school_code", "schoolid"
    ])

    if id_col is None:
        candidates = [
            c for c in header
            if ("school" in c.lower() and
                ("id" in c.lower() or "code" in c.lower()))
            or "udise" in c.lower()
        ]

        if len(candidates) == 1:
            id_col = candidates[0]

    district_col = find_col(header, [
        "district", "district_name"
    ])

    if id_col is None:
        add(filename, "School ID column", "Not identified",
            "One verified ID column", "REVIEW")
        return

    usecols = [id_col]
    if district_col:
        usecols.append(district_col)

    df = pd.read_csv(path, usecols=usecols, dtype=str)
    ids = df[id_col].fillna("").str.strip()

    missing = int((ids == "").sum())
    duplicate = int(ids[ids != ""].duplicated().sum())

    add(filename, "School ID missing", missing, 0,
        "PASS" if missing == 0 else "REVIEW")

    add(filename, "Duplicate School IDs", duplicate, 0,
        "PASS" if duplicate == 0 else "REVIEW")

    expected_rows = {
        "2018-19": 109942,
        "2019-20": 110229,
        "2020-21": 110114,
        "2021-22": 109605,
        "2022-23": 108451,
        "2023-24": 108237,
        "2024-25": 108250,
        "2025-26": 108139
    }[year]

    add(filename, "School-year row count", len(df), expected_rows,
        "PASS" if len(df) == expected_rows else "REVIEW")

    if district_col:
        districts = df[district_col].dropna().str.strip().nunique()
        add(filename, "Unique districts", districts, 36,
            "PASS" if districts == 36 else "REVIEW")
    else:
        add(filename, "District column", "Not found",
            "district or district_name", "REVIEW")


for year in YEARS:
    inspect_school_year(year)


def inspect_district_file(filename, year_col, score_col=None,
                          expected_rows=288, forecast=False):

    path = DISTRICT_DIR / filename

    if not path.exists():
        add(filename, "File exists", False, True, "FAIL")
        return None

    header = pd.read_csv(path, nrows=0).columns.tolist()

    district_col = find_col(header, ["district", "district_name"])
    actual_year_col = find_col(header, [year_col])

    required = [district_col, actual_year_col]

    if score_col:
        actual_score_col = find_col(header, [score_col])
        required.append(actual_score_col)
    else:
        actual_score_col = None

    if any(c is None for c in required):
        add(filename, "Required columns", header,
            "District, year and optional score column", "REVIEW")
        return None

    df = pd.read_csv(
        path,
        usecols=list(dict.fromkeys(required)),
        dtype=str
    )

    df[district_col] = df[district_col].fillna("").str.strip()
    df[actual_year_col] = df[actual_year_col].fillna("").str.strip()

    unique_districts = df[district_col].nunique()
    duplicate_keys = int(
        df.duplicated([district_col, actual_year_col]).sum()
    )

    add(filename, "Row count", len(df), expected_rows,
        "PASS" if len(df) == expected_rows else "REVIEW")

    add(filename, "Unique districts", unique_districts, 36,
        "PASS" if unique_districts == 36 else "REVIEW")

    add(filename, "Duplicate district-year keys", duplicate_keys, 0,
        "PASS" if duplicate_keys == 0 else "REVIEW")

    if not forecast:
        years_found = sorted(
            x for x in df[actual_year_col].unique() if x
        )
        add(filename, "Academic years", years_found,
            "2018-19 through 2025-26",
            "PASS" if len(years_found) == 8 else "REVIEW")
    else:
        years_found = sorted(
            x for x in df[actual_year_col].unique() if x
        )
        add(filename, "Forecast academic year", years_found,
            ["2026-27"],
            "PASS" if years_found == ["2026-27"] else "REVIEW")

    if actual_score_col:
        score = pd.to_numeric(
            df[actual_score_col], errors="coerce"
        )

        missing = int(score.isna().sum())

        add(filename, "Score missing", missing, 0,
            "PASS" if missing == 0 else "REVIEW")

        if missing == 0:
            minimum = float(score.min())
            maximum = float(score.max())

            add(filename, "Score range",
                f"{minimum:.3f} to {maximum:.3f}",
                "0 to 100",
                "PASS" if minimum >= 0 and maximum <= 100
                else "REVIEW")

    return df


final_df = inspect_district_file(
    "maharashtra_district_year_final_master.csv",
    "academic_year",
    expected_rows=288
)

score_df = inspect_district_file(
    "maharashtra_district_year_shala_score_v1.csv",
    "academic_year",
    "shala_score_v1",
    288
)

forecast_df = inspect_district_file(
    "maharashtra_district_year_forecast_2026_27.csv",
    "forecast_academic_year",
    "forecast_shala_score_v1",
    36,
    True
)

if final_df is not None and score_df is not None:
    final_key = set(zip(
        final_df["district"].str.upper(),
        final_df["academic_year"]
    ))

    score_key = set(zip(
        score_df["district"].str.upper(),
        score_df["academic_year"]
    ))

    same = final_key == score_key

    add("Final Master vs Shala Score",
        "District-Year key match",
        len(final_key.intersection(score_key)),
        len(final_key),
        "PASS" if same else "REVIEW")

if final_df is not None and forecast_df is not None:
    historical = set(
        final_df.loc[
            final_df["academic_year"] == "2025-26",
            "district"
        ].str.upper()
    )

    future = set(forecast_df["district"].str.upper())

    same = historical == future

    add("2025-26 vs 2026-27 Forecast",
        "District match",
        len(historical.intersection(future)),
        36,
        "PASS" if same and len(future) == 36 else "REVIEW")

REPORT.mkdir(parents=True, exist_ok=True)

result_df = pd.DataFrame(results)

result_df.to_csv(
    REPORT / "data_logic_validation.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n========== DATA LOGIC VALIDATION ==========")

if not result_df.empty:
    print(result_df.to_string(index=False))

print("\n========== SUMMARY ==========")

print("Total checks:", len(result_df))
print("PASS:", (result_df["Status"] == "PASS").sum())
print("REVIEW:", (result_df["Status"] == "REVIEW").sum())
print("FAIL:", (result_df["Status"] == "FAIL").sum())

print("\nReport saved:")
print(REPORT / "data_logic_validation.csv")

print("\nNo source data was modified.")

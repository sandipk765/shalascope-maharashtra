
from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "extracted"
REPORT = ROOT / "reports" / "data_audit"

REPORT.mkdir(parents=True, exist_ok=True)

PATTERN = re.compile(
    r"enrol|enrollment|enrolment|facility|facilities|infrastructure",
    re.IGNORECASE
)

YEAR_PATTERN = re.compile(r"20\d{2}-\d{2}")

records = []

print("\n" + "=" * 75)
print("SHALASCOPE MAHARASHTRA")
print("ENROLLMENT AND FACILITY SOURCE SCHEMA AUDIT")
print("=" * 75)

files = sorted(BASE.rglob("*.csv"))

for path in files:

    relative = path.relative_to(BASE)
    relative_text = str(relative)

    if not PATTERN.search(relative_text):
        continue

    year_match = YEAR_PATTERN.search(relative_text)
    year = year_match.group(0) if year_match else "YEAR_NOT_FOUND"

    try:
        headers = pd.read_csv(
            path,
            nrows=0,
            encoding="utf-8-sig"
        ).columns.tolist()

        status = "READABLE"

    except Exception as exc:
        headers = []
        status = f"READ_ERROR: {exc}"

    records.append({
        "academic_year": year,
        "source_type": (
            "ENROLLMENT"
            if re.search(r"enrol", relative_text, re.I)
            else "FACILITY"
        ),
        "file_name": path.name,
        "relative_path": relative_text,
        "column_count": len(headers),
        "columns": " | ".join(headers),
        "status": status,
    })

    print("\n" + "-" * 75)
    print(f"YEAR       : {year}")
    print(f"FILE       : {path.name}")
    print(f"SOURCE     : {records[-1]['source_type']}")
    print(f"COLUMNS    : {len(headers)}")
    print(f"STATUS     : {status}")

    if headers:
        for i, col in enumerate(headers, 1):
            print(f"{i:03d}. {col}")

if records:

    report_path = (
        REPORT / "enrollment_facility_schema_inventory.csv"
    )

    pd.DataFrame(records).to_csv(
        report_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 75)
    print("SOURCE TYPE SUMMARY")
    print("=" * 75)

    summary = (
        pd.DataFrame(records)
        .groupby(["academic_year", "source_type"])
        .agg(
            files=("file_name", "count"),
            readable_files=(
                "status",
                lambda x: sum(v == "READABLE" for v in x)
            ),
            total_columns=("column_count", "sum")
        )
        .reset_index()
    )

    print(summary.to_string(index=False))
    print(f"\nREPORT: {report_path}")

else:

    print("\nNo matching Enrollment or Facility CSV files found.")
    print("Review the extracted archive folder names.")

print("\nSCHEMA AUDIT COMPLETED")

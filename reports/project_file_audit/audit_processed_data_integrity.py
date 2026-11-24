import csv
import gzip
from pathlib import Path

ROOT = Path.cwd()
REPORT_DIR = ROOT / "reports" / "project_file_audit"

SCAN_DIRS = [
    ROOT / "data" / "processed",
    ROOT / "reports" / "ml_readiness" / "training_pairs",
    ROOT / "reports" / "ml_modeling_baseline",
    ROOT / "reports" / "forecast_2026_27",
]

EXPECTED_ROWS = {
    "maharashtra_district_year_core_master.csv": 288,
    "maharashtra_district_year_final_master.csv": 288,
    "maharashtra_district_year_enrollment_features.csv": 288,
    "maharashtra_district_year_facility_features.csv": 288,
    "maharashtra_district_year_shala_score_v1.csv": 288,
    "maharashtra_district_year_forecast_2026_27.csv": 36,

    "maharashtra_school_year_master_2018-19.csv": 109942,
    "maharashtra_school_year_master_2019-20.csv": 110229,
    "maharashtra_school_year_master_2020-21.csv": 110114,
    "maharashtra_school_year_master_2021-22.csv": 109605,
    "maharashtra_school_year_master_2022-23.csv": 108451,
    "maharashtra_school_year_master_2023-24.csv": 108237,
    "maharashtra_school_year_master_2024-25.csv": 108250,
    "maharashtra_school_year_master_2025-26.csv": 108139,
}

TRAINING_PAIRS_DIR = ROOT / "reports" / "ml_readiness" / "training_pairs"


def is_csv_file(path):
    name = path.name.lower()
    return name.endswith(".csv") or name.endswith(".csv.gz")


def scan_csv(path):
    is_gzip = path.name.lower().endswith(".gz")
    open_func = gzip.open if is_gzip else open

    last_error = None

    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open_func(
                path,
                "rt",
                encoding=encoding,
                newline=""
            ) as handle:

                reader = csv.reader(handle)

                header = next(reader, None)

                if header is None:
                    return {
                        "encoding": encoding,
                        "rows": 0,
                        "columns": 0,
                        "duplicate_headers": 0,
                        "blank_headers": 0,
                        "blank_rows": 0,
                        "bad_width_rows": 0,
                        "first_bad_row": "",
                        "error": "EMPTY FILE - NO HEADER",
                    }

                normalized = [str(x).strip() for x in header]
                duplicate_headers = (
                    len(normalized) - len(set(normalized))
                )
                blank_headers = sum(
                    1 for x in normalized if not x
                )

                row_count = 0
                blank_rows = 0
                bad_width_rows = 0
                first_bad_row = ""

                for line_number, row in enumerate(reader, start=2):

                    if not row or all(not str(x).strip() for x in row):
                        blank_rows += 1
                        continue

                    row_count += 1

                    if len(row) != len(header):
                        bad_width_rows += 1

                        if not first_bad_row:
                            first_bad_row = line_number

                return {
                    "encoding": encoding,
                    "rows": row_count,
                    "columns": len(header),
                    "duplicate_headers": duplicate_headers,
                    "blank_headers": blank_headers,
                    "blank_rows": blank_rows,
                    "bad_width_rows": bad_width_rows,
                    "first_bad_row": first_bad_row,
                    "error": "",
                }

        except UnicodeDecodeError as exc:
            last_error = str(exc)
            continue

        except Exception as exc:
            return {
                "encoding": encoding,
                "rows": "",
                "columns": "",
                "duplicate_headers": "",
                "blank_headers": "",
                "blank_rows": "",
                "bad_width_rows": "",
                "first_bad_row": "",
                "error": f"{type(exc).__name__}: {exc}",
            }

    return {
        "encoding": "",
        "rows": "",
        "columns": "",
        "duplicate_headers": "",
        "blank_headers": "",
        "blank_rows": "",
        "bad_width_rows": "",
        "first_bad_row": "",
        "error": f"ENCODING ERROR: {last_error}",
    }


files = []
missing_dirs = []

for directory in SCAN_DIRS:
    if not directory.exists():
        missing_dirs.append(str(directory.relative_to(ROOT)))
        continue

    files.extend(
        p for p in directory.rglob("*")
        if p.is_file() and is_csv_file(p)
    )

files = sorted(set(files))

results = []

for path in files:
    info = scan_csv(path)

    relative = str(path.relative_to(ROOT))
    expected = EXPECTED_ROWS.get(path.name)

    if (
        expected is None
        and path.is_relative_to(TRAINING_PAIRS_DIR)
        and path.name.lower().endswith(".csv")
    ):
        expected = 252

    if info["error"]:
        row_check = "NOT_CHECKED"
        status = "READ_ERROR"

    elif expected is not None:
        row_check = (
            "PASS" if info["rows"] == expected else "MISMATCH"
        )
        status = "PASS" if row_check == "PASS" else "REVIEW_REQUIRED"

    else:
        row_check = "NOT_SPECIFIED"
        status = "PASS"

    if not info["error"]:
        if (
            info["duplicate_headers"]
            or info["blank_headers"]
            or info["bad_width_rows"]
            or info["rows"] == 0
        ):
            status = "REVIEW_REQUIRED"

    results.append({
        "File": relative,
        "Encoding": info["encoding"],
        "Rows": info["rows"],
        "Columns": info["columns"],
        "ExpectedRows": expected if expected is not None else "",
        "RowCheck": row_check,
        "DuplicateHeaders": info["duplicate_headers"],
        "BlankHeaders": info["blank_headers"],
        "BlankRows": info["blank_rows"],
        "BadWidthRows": info["bad_width_rows"],
        "FirstBadRow": info["first_bad_row"],
        "Status": status,
        "Error": info["error"],
    })


REPORT_DIR.mkdir(parents=True, exist_ok=True)

report_path = REPORT_DIR / "processed_data_integrity.csv"

fieldnames = list(results[0].keys()) if results else [
    "File", "Status", "Error"
]

with report_path.open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

passed = sum(r["Status"] == "PASS" for r in results)
review = sum(r["Status"] == "REVIEW_REQUIRED" for r in results)
errors = sum(r["Status"] == "READ_ERROR" for r in results)
mismatches = sum(r["RowCheck"] == "MISMATCH" for r in results)

summary = [
    "SHALASCOPE - PROCESSED DATA INTEGRITY AUDIT",
    "",
    f"Audit date: 2026-11-17",
    f"CSV files scanned: {len(results)}",
    f"PASS: {passed}",
    f"Review required: {review}",
    f"Read errors: {errors}",
    f"Expected row-count mismatches: {mismatches}",
    "",
    "Missing audit directories:",
]

summary.extend(missing_dirs if missing_dirs else ["None"])
summary.extend([
    "",
    f"Detailed report: {report_path.relative_to(ROOT)}",
    "",
    "Note: PASS means file was readable and passed the checks above.",
    "It does not independently prove data accuracy or source authenticity.",
])

summary_path = REPORT_DIR / "processed_data_summary.txt"
summary_path.write_text("\n".join(summary), encoding="utf-8")

print("\n========== PROCESSED DATA AUDIT ==========")
print("\n".join(summary))

print("\n========== FILE STATUS ==========")

for item in results:
    print(
        f'{item["Status"]:16} '
        f'{str(item["Rows"]):>10} rows  '
        f'{item["File"]}'
    )

print("\nAudit completed. No data files were changed.")

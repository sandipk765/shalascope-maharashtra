
"""
ShalaScope Maharashtra
Inspect actual Teacher CSV column names for all years.
Does not modify source files.
"""

from pathlib import Path
import csv
import re

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "extracted"
REPORT_DIR = ROOT / "reports" / "data_audit"

OUTPUT = REPORT_DIR / "teacher_header_inventory.csv"

ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]


def open_csv(path):
    for encoding in ENCODINGS:
        try:
            f = path.open("r", encoding=encoding, newline="")
            sample = f.read(65536)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(
                    sample, delimiters=",;\t|"
                )
            except csv.Error:
                dialect = csv.excel

            return f, dialect

        except UnicodeDecodeError:
            try:
                f.close()
            except Exception:
                pass

    raise ValueError(f"Cannot decode: {path}")


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    records = []

    files = sorted(
        p for p in DATA_ROOT.rglob("*.csv")
        if (
            "teacher_data" in str(p.parent).lower()
            or re.search(r"(^|[_-])tch([_.-]|$)", p.name.lower())
        )
    )

    if not files:
        raise FileNotFoundError("No Teacher CSV files found.")

    print("\nSHALASCOPE - TEACHER COLUMN INSPECTION")
    print("=" * 65)

    for path in files:
        year = next(
            (part for part in path.parts
             if re.fullmatch(r"20\d{2}-\d{2}", part)),
            "UNKNOWN"
        )

        handle, dialect = open_csv(path)

        try:
            reader = csv.reader(handle, dialect)
            headers = next(reader, [])

            print(f"\n{year} | {path.name}")
            print("-" * 50)

            for position, name in enumerate(headers, start=1):
                print(f"{position:02d}. {name}")

                records.append({
                    "academic_year": year,
                    "file_name": path.name,
                    "column_position": position,
                    "original_column": name
                })

        finally:
            handle.close()

    with OUTPUT.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "academic_year",
                "file_name",
                "column_position",
                "original_column"
            ]
        )
        writer.writeheader()
        writer.writerows(records)

    print("\n" + "=" * 65)
    print(f"Teacher CSV files: {len(files)}")
    print(f"Total headers: {len(records)}")
    print(f"Report created: {OUTPUT}")


if __name__ == "__main__":
    main()

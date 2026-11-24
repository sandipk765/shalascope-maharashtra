"""
ShalaScope Maharashtra - Phase 3 ZIP Integrity Audit
Checks all ZIP files in data/raw/udise_zip for readability and corruption.
"""
import zipfile
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ZIP_ROOT = ROOT / "data" / "raw" / "udise_zip"
OUT = ROOT / "reports" / "project_file_audit"

results = []
for z in sorted(ZIP_ROOT.rglob("*.zip")):
    row = {
        "year": z.parent.name,
        "file": z.name,
        "size_mb": round(z.stat().st_size / 1024 / 1024, 3),
        "status": "",
        "entries": 0,
        "inner_files": "",
        "error": ""
    }
    try:
        with zipfile.ZipFile(z) as zf:
            bad = zf.testzip()
            names = zf.namelist()
            row["status"] = f"CORRUPT:{bad}" if bad else "OK"
            row["entries"] = len(names)
            row["inner_files"] = "; ".join(names[:5])
    except Exception as e:
        row["status"] = "ERROR"
        row["error"] = str(e)
    results.append(row)

# Write CSV
out_file = OUT / "zip_integrity_report.csv"
with open(out_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    writer.writeheader()
    writer.writerows(results)

# Print summary
ok = sum(1 for r in results if r["status"] == "OK")
corrupt = sum(1 for r in results if "CORRUPT" in r["status"])
error = sum(1 for r in results if r["status"] == "ERROR")

print(f"Total ZIPs : {len(results)}")
print(f"OK         : {ok}")
print(f"Corrupt    : {corrupt}")
print(f"Error      : {error}")
print()
for r in results:
    flag = "  OK" if r["status"] == "OK" else "FAIL"
    print(f"[{flag}] {r['year']} | {r['file'][:55]:55s} | {r['size_mb']} MB | entries={r['entries']}")

print(f"\nReport: {out_file}")

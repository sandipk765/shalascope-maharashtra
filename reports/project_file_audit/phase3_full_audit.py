"""
ShalaScope Maharashtra - Phase 3 Complete Raw Data Audit
Checks all 49 ZIPs and 49 extracted CSVs.
Outputs 7 audit report CSVs.
Never modifies source data.
"""
import zipfile
import csv
import io
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra")
ZIP_ROOT    = ROOT / "data" / "raw" / "udise_zip"
EXTRACT_ROOT = ROOT / "data" / "extracted"
OUT         = ROOT / "reports" / "data_audit"
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_YEARS = ["2018-19","2019-20","2020-21","2021-22","2022-23","2023-24","2024-25","2025-26"]
EXPECTED_TYPES = ["enr1","enr2","fac","prof1","prof2","tch"]

ENCODINGS = ["utf-8-sig","utf-8","cp1252","latin-1"]


# ── helpers ─────────────────────────────────────────────────────────────────

def detect_encoding(path):
    for enc in ENCODINGS:
        try:
            with open(path, encoding=enc, errors="strict") as f:
                f.read(32768)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    return None


def read_csv_safe(path):
    """Return (header_list, rows_list, encoding, error_msg)."""
    enc = detect_encoding(path)
    if enc is None:
        return None, None, None, "Cannot detect encoding"
    try:
        with open(path, encoding=enc, newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None:
                return None, None, enc, "Empty file / no header"
            rows = list(reader)
        return header, rows, enc, ""
    except Exception as e:
        return None, None, enc, str(e)


def clean(val):
    return str(val).strip() if val is not None else ""


def try_float(val):
    try:
        return float(clean(val))
    except (ValueError, TypeError):
        return None


# ── 1. ZIP INTEGRITY ─────────────────────────────────────────────────────────

print("\n[1/7] ZIP integrity audit ...")
zip_rows = []
for z in sorted(ZIP_ROOT.rglob("*.zip")):
    row = {
        "year": z.parent.name, "file": z.name,
        "size_mb": round(z.stat().st_size / 1048576, 3),
        "status": "", "entries": 0, "inner_files": "", "error": ""
    }
    try:
        with zipfile.ZipFile(z) as zf:
            bad = zf.testzip()
            names = zf.namelist()
            row["status"] = f"CORRUPT:{bad}" if bad else "OK"
            row["entries"] = len(names)
            row["inner_files"] = "; ".join(names[:4])
    except Exception as e:
        row["status"] = "ERROR"
        row["error"] = str(e)
    zip_rows.append(row)
    flag = "OK" if row["status"] == "OK" else "!!"
    print(f"  [{flag}] {row['year']} | {row['file'][:52]:52s} | {row['size_mb']:6.2f} MB | entries={row['entries']}")

with open(OUT / "zip_integrity_report.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(zip_rows[0].keys()))
    w.writeheader(); w.writerows(zip_rows)

ok_zips  = sum(1 for r in zip_rows if r["status"] == "OK")
bad_zips = len(zip_rows) - ok_zips
print(f"\n  ZIP summary: {ok_zips} OK | {bad_zips} FAIL out of {len(zip_rows)}")


# ── 2. EXTRACTED CSV FILE AUDIT ───────────────────────────────────────────────

print("\n[2/7] Extracted CSV schema audit ...")
csv_files = sorted(EXTRACT_ROOT.rglob("*.csv"))
print(f"  Found {len(csv_files)} extracted CSV files")

schema_rows   = []
raw_audit_rows = []
missing_val_rows = []
dup_rows      = []
invalid_rows  = []

# Map to track district-year keys across files for the processed master (done in Phase 5).
# Here we focus on raw file-level checks only.

for csv_path in csv_files:
    year = csv_path.parts[csv_path.parts.index("extracted") + 1] if "extracted" in csv_path.parts else "unknown"
    fname = csv_path.name
    rel   = str(csv_path.relative_to(ROOT))

    header, rows, enc, err = read_csv_safe(csv_path)

    base_row = {
        "year": year, "file": fname, "relative_path": rel,
        "size_mb": round(csv_path.stat().st_size / 1048576, 3),
        "encoding": enc or "unknown",
        "data_rows": len(rows) if rows else 0,
        "columns": len(header) if header else 0,
        "status": "", "error": err
    }

    if err or header is None:
        base_row["status"] = "READ_ERROR"
        raw_audit_rows.append(base_row)
        continue

    # Duplicate headers
    dup_headers = len(header) - len(set(h.strip() for h in header))
    base_row["duplicate_headers"] = dup_headers
    base_row["status"] = "WARNING" if dup_headers > 0 else "PASS"
    raw_audit_rows.append(base_row)

    # Schema: record column names
    for i, col in enumerate(header):
        schema_rows.append({
            "year": year, "file": fname, "position": i+1, "column_name": col.strip()
        })

    # Missing values scan – count per column
    missing_by_col = defaultdict(int)
    blank_rows = 0
    total_data_rows = 0
    for row in rows:
        if not any(clean(v) for v in row):
            blank_rows += 1
            continue
        total_data_rows += 1
        for i, val in enumerate(row):
            if not clean(val):
                col_name = header[i].strip() if i < len(header) else f"col_{i}"
                missing_by_col[col_name] += 1

    for col, cnt in missing_by_col.items():
        if cnt > 0:
            missing_val_rows.append({
                "year": year, "file": fname, "column": col,
                "missing_count": cnt,
                "total_rows": total_data_rows,
                "missing_pct": round(cnt / total_data_rows * 100, 2) if total_data_rows > 0 else 0
            })

    # Duplicate rows (by full row content, first 100k rows)
    seen = set()
    dup_count = 0
    for row in rows[:100000]:
        key = tuple(clean(v) for v in row)
        if key in seen:
            dup_count += 1
        seen.add(key)
    if dup_count > 0:
        dup_rows.append({
            "year": year, "file": fname, "duplicate_rows": dup_count,
            "total_rows": total_data_rows
        })

    # Numeric range checks on key columns
    h_lower = [c.strip().lower() for c in header]

    # Find state/district column
    dist_col = next((i for i, c in enumerate(h_lower)
                     if c in ("state_cd","statecode","state_code","district_cd","distcode")), None)

    # Look for numeric columns that shouldn't be negative
    neg_cols_keywords = ["enrol","enrolment","enrollment","teacher","total"]
    pct_cols_keywords = ["pct","percent","ratio","prop"]

    for row in rows[:50000]:
        for i, col_name in enumerate(h_lower):
            if i >= len(row):
                continue
            val = try_float(row[i])
            if val is None:
                continue
            # Negative count check
            if any(k in col_name for k in neg_cols_keywords):
                if val < 0:
                    invalid_rows.append({
                        "year": year, "file": fname, "column": header[i].strip(),
                        "value": row[i], "issue": "NEGATIVE_COUNT",
                        "row_sample": str(row[:5])
                    })
            # Percentage out of range
            if any(k in col_name for k in pct_cols_keywords):
                if val < 0 or val > 100:
                    invalid_rows.append({
                        "year": year, "file": fname, "column": header[i].strip(),
                        "value": row[i], "issue": "PCT_OUT_OF_RANGE",
                        "row_sample": str(row[:5])
                    })

    print(f"  [{'PASS' if base_row['status']=='PASS' else 'WARN'}] {year} | {fname[:45]:45s} | rows={total_data_rows:,} | cols={len(header)} | missing_cols={len(missing_by_col)} | dups={dup_count}")


# ── 3. DISTRICT-YEAR COVERAGE CHECK ──────────────────────────────────────────

print("\n[3/7] District-year coverage from processed master ...")
master_path = ROOT / "data" / "processed" / "district_year" / "maharashtra_district_year_shala_score_v1.csv"
coverage_rows = []
if master_path.exists():
    header_m, rows_m, enc_m, err_m = read_csv_safe(master_path)
    if header_m and rows_m:
        h_lower_m = [c.strip().lower() for c in header_m]
        ay_idx = next((i for i, c in enumerate(h_lower_m) if c == "academic_year"), None)
        dist_idx = next((i for i, c in enumerate(h_lower_m) if c == "district"), None)
        if ay_idx is not None and dist_idx is not None:
            year_dist = defaultdict(set)
            for row in rows_m:
                if len(row) > max(ay_idx, dist_idx):
                    year_dist[clean(row[ay_idx])].add(clean(row[dist_idx]))
            for yr in sorted(year_dist.keys()):
                districts = sorted(year_dist[yr])
                coverage_rows.append({
                    "academic_year": yr,
                    "district_count": len(districts),
                    "expected_count": 36,
                    "status": "PASS" if len(districts) == 36 else "FAIL",
                    "districts": "; ".join(districts)
                })
                print(f"  {yr}: {len(districts)} districts | {'PASS' if len(districts)==36 else 'FAIL'}")
else:
    print("  Master CSV not found - skipping coverage check")


# ── 4. WRITE ALL REPORTS ──────────────────────────────────────────────────────

print("\n[4/7] Writing audit reports ...")

def write_csv(path, rows):
    if not rows:
        rows = [{"note": "No issues found"}]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

write_csv(OUT / "raw_data_audit_summary.csv", raw_audit_rows)
write_csv(OUT / "csv_schema_audit.csv", schema_rows)
write_csv(OUT / "missing_values_report.csv", missing_val_rows)
write_csv(OUT / "duplicate_records_report.csv", dup_rows)
write_csv(OUT / "district_year_coverage.csv", coverage_rows)
write_csv(OUT / "invalid_values_report.csv", invalid_rows)

print("  Reports written.")

# ── 5. FINAL SUMMARY ─────────────────────────────────────────────────────────

print("\n" + "="*65)
print("PHASE 3 RAW DATA AUDIT - FINAL SUMMARY")
print("="*65)
print(f"ZIP files checked         : {len(zip_rows)}")
print(f"ZIP OK                    : {ok_zips}")
print(f"ZIP FAIL/CORRUPT          : {bad_zips}")
print(f"Extracted CSVs checked    : {len(csv_files)}")
read_errors = sum(1 for r in raw_audit_rows if r["status"] == "READ_ERROR")
warnings    = sum(1 for r in raw_audit_rows if r["status"] == "WARNING")
passes      = sum(1 for r in raw_audit_rows if r["status"] == "PASS")
print(f"CSV READ ERRORS           : {read_errors}")
print(f"CSV WARNINGS              : {warnings}")
print(f"CSV PASS                  : {passes}")
print(f"Total missing-value cols  : {len(missing_val_rows)}")
print(f"Files with duplicate rows : {len(dup_rows)}")
print(f"Invalid value records     : {len(invalid_rows)}")
print(f"Coverage years checked    : {len(coverage_rows)}")
print(f"\nReport folder: {OUT}")
print("STATUS: PHASE 3 COMPLETE")

"""
ShalaScope Maharashtra - Key Value Profiler

Purpose:
- Inspect distinct values/frequencies for coded fields.
- Inspect district names and enrolment row dimensions.
- Do not modify any source CSV files.
- Read large CSV files in chunks to keep memory usage controlled.

Run from project root:
    python src/validation/profile_key_values.py

Outputs:
    reports/data_audit/key_value_frequency.csv
    reports/data_audit/key_field_summary.csv
"""

from pathlib import Path
from collections import Counter
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXTRACT_ROOT = ROOT / "data" / "extracted"
REPORT_DIR = ROOT / "reports" / "data_audit"
FREQUENCY_OUT = REPORT_DIR / "key_value_frequency.csv"
SUMMARY_OUT = REPORT_DIR / "key_field_summary.csv"
CHUNK_SIZE = 150_000

PROFILE1_FIELDS = {
    "state", "district", "rural_urban", "school_category", "school_type",
    "managment", "aff_board_sec", "aff_board_hsec", "special_school_for_cwsn",
    "shift_school", "resi_school", "resi_type", "minority_school",
    "medium_instr1", "medium_of_instr2", "medium_of_instr3", "medium_of_instr4",
    "approachable_road", "pre_primary", "anganwadi_premises", "anganwadi_yn",
    "cce_pr", "cce_up", "cce_sec", "cce_hsec", "cce_yn", "is_nsqf",
    "prevoc_yn", "stc_yn", "certified_fit_india_yn", "cwsn_sch_type"
}

PROFILE2_FIELDS = {
    "balavatika_located_yn", "special_training", "text_books_received",
    "material_training", "smc_exists", "smc_smdc_same", "smdc_constituted",
    "smc_smdc_meetings"
}

FACILITY_FIELDS = {
    "building_status", "boundary_wall", "drinking_water_available",
    "drinking_water_functional", "rain_water_harvesting",
    "handwash_facility_for_meal", "handwash_near_toilet",
    "electricity_availability", "solar_panel", "library_availability",
    "playground_available", "medical_checkups", "availability_ramps",
    "availability_of_handrails", "ict_lab", "ict_lab_yn", "comp_ict_lab_yn",
    "book_bank", "reading_corner", "playground_alt_yn", "cyber_safety",
    "psycho_social", "enrichment_activities"
}

SAFETY_FIELDS = {
    "safe_sec_audit", "teacher_displaying_photo", "vidya_pravesh",
    "tch_first_level_counsellor"
}

ENROLMENT_DIMENSIONS = {"item_desc", "item_group", "item_id"}


def identify_category(path: Path) -> str:
    folder = path.parent.name.lower()
    stem = path.stem.lower()
    label = folder + " " + stem

    if "safety" in label or "safety" in stem:
        return "safety"
    if "profile_data_1" in label or "prof1" in stem:
        return "profile_1"
    if "profile_data_2" in label or "prof2" in stem:
        return "profile_2"
    if "enrolment_data_1" in label or "enrollment_data_1" in label or "enr1" in stem:
        return "enrolment_1"
    if "enrolment_data_2" in label or "enrollment_data_2" in label or "enr2" in stem:
        return "enrolment_2"
    if "facility_data" in label or stem.endswith("_fac"):
        return "facility"
    if "teacher_data" in label or stem.endswith("_tch"):
        return "teacher"
    return "unclassified"


def select_fields(category: str, columns: list[str]) -> list[str]:
    present = set(columns)

    if category == "profile_1":
        wanted = PROFILE1_FIELDS | {c for c in columns if c.endswith("_yn")}
    elif category == "profile_2":
        wanted = PROFILE2_FIELDS | {c for c in columns if c.endswith("_yn")}
    elif category == "facility":
        wanted = FACILITY_FIELDS | {c for c in columns if c.endswith("_yn")}
    elif category == "safety":
        wanted = SAFETY_FIELDS | {c for c in columns if c.endswith("_yn")}
    elif category in {"enrolment_1", "enrolment_2"}:
        wanted = ENROLMENT_DIMENSIONS
    else:
        wanted = set()

    # District names and common school classifications are especially useful for joins.
    return sorted(present & wanted)


def profile_file(path: Path, year: str):
    category = identify_category(path)
    result_counts = {}
    total_rows = 0
    selected = []

    try:
        header = pd.read_csv(path, nrows=0, encoding="utf-8-sig")
        columns = [str(c).strip() for c in header.columns]
        selected = select_fields(category, columns)

        if not selected:
            return [], [{
                "academic_year": year,
                "category": category,
                "file_name": path.name,
                "source_column": "",
                "rows_scanned": 0,
                "non_missing": 0,
                "missing": 0,
                "unique_values": 0,
                "status": "NO_TARGET_FIELDS_FOUND"
            }]

        for col in selected:
            result_counts[col] = Counter()

        for chunk in pd.read_csv(
            path,
            usecols=selected,
            dtype="string",
            encoding="utf-8-sig",
            chunksize=CHUNK_SIZE,
            low_memory=False
        ):
            total_rows += len(chunk)
            for col in selected:
                values = chunk[col].fillna("<MISSING>").astype(str).str.strip()
                values = values.replace({"": "<EMPTY>"})
                result_counts[col].update(values.value_counts(dropna=False).to_dict())

        frequencies = []
        summaries = []
        for col, counter in result_counts.items():
            missing = counter.get("<MISSING>", 0) + counter.get("<EMPTY>", 0)
            non_missing = total_rows - missing
            summaries.append({
                "academic_year": year,
                "category": category,
                "file_name": path.name,
                "source_column": col,
                "rows_scanned": total_rows,
                "non_missing": non_missing,
                "missing": missing,
                "unique_values": len(counter),
                "status": "PROFILED"
            })
            for value, count in sorted(counter.items(), key=lambda x: (-x[1], x[0])):
                frequencies.append({
                    "academic_year": year,
                    "category": category,
                    "file_name": path.name,
                    "source_column": col,
                    "observed_value": value,
                    "frequency": count
                })
        return frequencies, summaries

    except Exception as exc:
        return [], [{
            "academic_year": year,
            "category": category,
            "file_name": path.name,
            "source_column": "",
            "rows_scanned": total_rows,
            "non_missing": 0,
            "missing": 0,
            "unique_values": 0,
            "status": f"FAILED: {exc}"
        }]


def main():
    if not EXTRACT_ROOT.exists():
        raise FileNotFoundError(f"Extracted data folder not found: {EXTRACT_ROOT}")

    files = sorted(EXTRACT_ROOT.rglob("*.csv"))
    if not files:
        raise FileNotFoundError("No extracted CSV files were found.")

    all_frequencies = []
    all_summaries = []

    print("\nSHALASCOPE - KEY VALUE PROFILING")
    print("=" * 65)
    print(f"CSV files found: {len(files)}")

    for index, path in enumerate(files, start=1):
        rel = path.relative_to(EXTRACT_ROOT)
        year = rel.parts[0]
        category = identify_category(path)
        print(f"[{index}/{len(files)}] {year} | {category} | {path.name}")

        frequencies, summaries = profile_file(path, year)
        all_frequencies.extend(frequencies)
        all_summaries.extend(summaries)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(all_frequencies).to_csv(
        FREQUENCY_OUT, index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(all_summaries).to_csv(
        SUMMARY_OUT, index=False, encoding="utf-8-sig"
    )

    print("\n" + "=" * 65)
    print("KEY VALUE PROFILING COMPLETED")
    print(f"Frequency report: {FREQUENCY_OUT}")
    print(f"Summary report:   {SUMMARY_OUT}")
    print("Original CSV files were not modified.")


if __name__ == "__main__":
    main()

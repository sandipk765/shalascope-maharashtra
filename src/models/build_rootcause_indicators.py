"""
ShikshanDarpan AI  –  Educational Root-Cause Indicator Analysis
===============================================================
Generates a district-level diagnostic dataset with:
  - Observed indicator values
  - Benchmark comparisons (state average, RTE norms, project thresholds)
  - Status flags (ADEQUATE / CONCERN / CRITICAL)
  - Plain-English explanations

These are POTENTIAL educational risk factors, not confirmed
dropout causes. No causal claim is made.

Output:
  - reports/rootcause/educational_rootcause_indicators.csv
  - reports/rootcause/rootcause_state_benchmarks.csv
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "data" / "processed" / "district_year"
    / "maharashtra_district_year_shala_score_v1.csv"
)

OUT = ROOT / "reports" / "rootcause"
OUT.mkdir(parents=True, exist_ok=True)

# ── Thresholds ──────────────────────────────────────────────
THRESHOLDS = {
    "ptr_students_per_teacher_raw": {
        "label": "Pupil-Teacher Ratio",
        "direction": "lower_is_better",
        "rte_norm": 30,
        "critical_above": 35,
        "unit": "students / teacher",
        "explanation_good":  "PTR is within RTE norm (<= 30:1). Adequate teacher availability.",
        "explanation_concern": "PTR exceeds RTE norm of 30:1. Teacher availability may need attention.",
        "explanation_critical": "PTR is critically high (> 35:1). Significant teacher shortage indicated.",
    },
    "functional_toilet_pct_raw": {
        "label": "Functional Toilet Coverage",
        "direction": "higher_is_better",
        "threshold_adequate": 90,
        "threshold_concern": 85,
        "unit": "%",
        "explanation_good":  "Functional toilet coverage is good (>= 90%). Adequate sanitation.",
        "explanation_concern": "Toilet coverage is below 90%. Sanitation infrastructure may need improvement.",
        "explanation_critical": "Toilet coverage is critically low (< 85%). Serious sanitation gap.",
    },
    "good_classroom_pct_raw": {
        "label": "Good-Condition Classrooms",
        "direction": "higher_is_better",
        "threshold_adequate": 90,
        "threshold_concern": 75,
        "unit": "%",
        "explanation_good":  "Good-condition classroom share is adequate (>= 90%).",
        "explanation_concern": "Classroom quality needs attention. Less than 90% are in good condition.",
        "explanation_critical": "Classroom quality is critically low (< 75%). Significant repair backlog.",
    },
    "facility_classrooms_needing_repair_pct": {
        "label": "Classrooms Needing Repair",
        "direction": "lower_is_better",
        "threshold_adequate": 10,
        "threshold_concern": 20,
        "unit": "%",
        "explanation_good":  "Repair backlog is low (< 10% of classrooms). Infrastructure is well maintained.",
        "explanation_concern": "Moderate repair backlog (10-20% of classrooms). Infrastructure attention needed.",
        "explanation_critical": "High repair backlog (> 20% of classrooms). Priority infrastructure investment needed.",
    },
    "digital_devices_per_school_raw": {
        "label": "Digital Devices per School",
        "direction": "higher_is_better",
        "threshold_adequate": 5,
        "threshold_concern": 2,
        "unit": "devices / school",
        "explanation_good":  "Digital access is adequate (>= 5 devices per reporting school).",
        "explanation_concern": "Digital device availability is limited (2-5 per school). Digital access improvement needed.",
        "explanation_critical": "Digital access is critically low (< 2 devices per reporting school). Significant digital gap.",
    },
}


# ── Status assignment ────────────────────────────────────────
def assign_status(col, value):
    t = THRESHOLDS[col]
    direction = t["direction"]
    if pd.isna(value):
        return "DATA MISSING"

    if direction == "lower_is_better":
        # Supports PTR-style keys (rte_norm, critical_above)
        # AND Repair-style keys (threshold_adequate, threshold_concern).
        crit_threshold = t.get("critical_above") or t.get("threshold_concern")
        warn_threshold = t.get("rte_norm") or t.get("threshold_adequate")
        if crit_threshold is not None and value > crit_threshold:
            return "CRITICAL"
        if warn_threshold is not None and value > warn_threshold:
            return "CONCERN"
        return "ADEQUATE"
    else:
        tq = t.get("threshold_adequate", 90)
        tc = t.get("threshold_concern", 75)
        if value >= tq:
            return "ADEQUATE"
        if value >= tc:
            return "CONCERN"
        return "CRITICAL"


def assign_explanation(col, status):
    t = THRESHOLDS[col]
    if status == "ADEQUATE":
        return t["explanation_good"]
    if status == "CONCERN":
        return t["explanation_concern"]
    if status == "CRITICAL":
        return t["explanation_critical"]
    return "Data not available for this indicator."


# ── Main ─────────────────────────────────────────────────────
def main():
    df = pd.read_csv(INPUT, low_memory=False)

    for col in THRESHOLDS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # State benchmarks (computed once across all 288 rows)
    benchmarks = {}
    for col, t in THRESHOLDS.items():
        benchmarks[col] = {
            "indicator": t["label"],
            "unit": t["unit"],
            "state_mean": float(df[col].mean()),
            "state_median": float(df[col].median()),
            "state_p10": float(df[col].quantile(0.10)),
            "state_p90": float(df[col].quantile(0.90)),
        }

    bench_df = pd.DataFrame.from_dict(benchmarks, orient="index").reset_index()
    bench_df.rename(columns={"index": "column"}, inplace=True)
    bench_df.to_csv(OUT / "rootcause_state_benchmarks.csv",
                    index=False, encoding="utf-8-sig")

    # Per-district, per-year diagnostic rows
    rows = []
    for _, record in df.iterrows():
        district = str(record["district"])
        year = str(record["academic_year"])
        for col, t in THRESHOLDS.items():
            value = record[col]
            status = assign_status(col, value)
            state_mean = benchmarks[col]["state_mean"]
            rows.append({
                "district": district,
                "academic_year": year,
                "indicator": t["label"],
                "column": col,
                "value": float(value) if pd.notna(value) else None,
                "unit": t["unit"],
                "state_mean": round(state_mean, 4),
                "delta_vs_state": (
                    round(float(value) - state_mean, 4)
                    if pd.notna(value) else None
                ),
                "status": status,
                "explanation": assign_explanation(col, status),
            })

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT / "educational_rootcause_indicators.csv",
                  index=False, encoding="utf-8-sig")

    # Summary count per year
    summary = (
        out_df[out_df["status"].isin(["CONCERN", "CRITICAL"])]
        .groupby(["academic_year", "indicator"])["district"]
        .count()
        .reset_index()
        .rename(columns={"district": "districts_with_concern_or_critical"})
    )
    summary.to_csv(OUT / "rootcause_concern_summary.csv",
                   index=False, encoding="utf-8-sig")

    print("Root-cause indicator analysis complete.")
    print(f"  Records: {len(out_df)}")
    print(f"  Output : {OUT}")
    print("\nState benchmarks:")
    print(bench_df.to_string(index=False))

    # Print latest year concern counts
    latest = df["academic_year"].max()
    print(f"\nConcern/Critical districts in {latest}:")
    latest_summary = summary[summary["academic_year"] == str(latest)]
    print(latest_summary.to_string(index=False))


if __name__ == "__main__":
    main()

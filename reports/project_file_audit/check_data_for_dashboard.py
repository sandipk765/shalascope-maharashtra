import pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra")
hist = pd.read_csv(ROOT / "data/processed/district_year/maharashtra_district_year_shala_score_v1.csv", low_memory=False)
fore = pd.read_csv(ROOT / "data/processed/district_year/maharashtra_district_year_forecast_2026_27.csv", low_memory=False)

print("=== HISTORICAL: score-related columns ===")
score_cols = [c for c in hist.columns if any(k in c.lower() for k in
    ["school","enroll","teacher","toilet","classroom","digital","score","pillar","ptr","shala"])]
print(score_cols)

print("\n=== FORECAST COLUMNS ===")
print(list(fore.columns))

print("\n=== SCORE RANGE ACROSS YEARS ===")
print(hist.groupby("academic_year")["shala_score_v1"].agg(["min","max","mean"]).round(2).to_string())

print("\n=== FORECAST SAMPLE (sorted by score) ===")
print(fore[["district","forecast_shala_score_v1","forecast_relative_performance_band",
            "forecast_enrollment","forecast_teachers",
            "forecast_functional_toilet_pct","forecast_good_classroom_pct",
            "forecast_digital_devices_per_school"]].to_string(index=False))

print("\n=== PILLAR AVERAGES 2025-26 ===")
latest = hist[hist["academic_year"] == "2025-26"]
for col in ["pillar_teacher_strength","pillar_infrastructure","pillar_digital_readiness","shala_score_v1"]:
    if col in latest.columns:
        print(f"  {col}: mean={latest[col].mean():.2f}  min={latest[col].min():.2f}  max={latest[col].max():.2f}")

print("\n=== MISSING COLUMNS THAT COULD BE ADDED ===")
extra = [c for c in hist.columns if c not in score_cols and "academic_year" not in c and "district" not in c]
print(f"Total other columns: {len(extra)}")
print("Sample:", extra[:20])

print("\n=== FORECAST: error range columns ===")
err_cols = [c for c in fore.columns if "lower" in c or "upper" in c or "p10" in c or "p90" in c]
print(err_cols)

print("\n=== FORECAST: slope/trend columns for digital ===")
trend_cols = [c for c in fore.columns if "trend" in c or "slope" in c or "digital_trend" in c]
print(trend_cols)

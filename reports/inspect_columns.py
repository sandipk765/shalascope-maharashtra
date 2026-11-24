import pandas as pd

df = pd.read_csv(
    r"c:\Users\userp\Desktop\ShalaScope_Maharashtra\data\processed\district_year\maharashtra_district_year_shala_score_v1.csv",
    low_memory=False, nrows=2
)
cols = df.columns.tolist()

groups = {
    "enrolment_gender_b_g": [c for c in cols if "_b_" in c or "_g_" in c or "boys" in c.lower() or "girls" in c.lower() or "b_component" in c or "g_component" in c],
    "teacher_pct": [c for c in cols if "teacher_pct" in c or "female_teacher" in c or "male_teacher" in c],
    "ptr": [c for c in cols if "ptr" in c.lower()],
    "region": [c for c in cols if "region" in c.lower()],
    "literacy": [c for c in cols if "literacy" in c.lower()],
    "dropout": [c for c in cols if "dropout" in c.lower()],
    "ger": [c for c in cols if "ger" in c.lower()],
    "electricity": [c for c in cols if "electric" in c.lower()],
    "water": [c for c in cols if "water" in c.lower() or "drink" in c.lower()],
    "library": [c for c in cols if "library" in c.lower()],
    "ramp": [c for c in cols if "ramp" in c.lower()],
    "internet": [c for c in cols if "internet" in c.lower()],
    "computer": [c for c in cols if "computer" in c.lower()],
    "shala_pillars": [c for c in cols if "shala" in c.lower() or "pillar" in c.lower()],
    "facility_pct": [c for c in cols if "facility" in c.lower() and "pct" in c.lower()],
}

for grp, matched in groups.items():
    print(f"\n{grp} ({len(matched)} cols):")
    for c in matched[:8]:
        print(f"  {c}")
    if len(matched) > 8:
        print(f"  ... +{len(matched)-8} more")

print(f"\nTotal columns: {len(cols)}")

# Check actual year range
df2 = pd.read_csv(
    r"c:\Users\userp\Desktop\ShalaScope_Maharashtra\data\processed\district_year\maharashtra_district_year_shala_score_v1.csv",
    low_memory=False, usecols=["district", "academic_year"]
)
print(f"\nYears: {sorted(df2['academic_year'].unique())}")
print(f"Districts: {sorted(df2['district'].unique())}")
print(f"Rows: {len(df2)}")

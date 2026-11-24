import pandas as pd

df = pd.read_csv(
    r"c:\Users\userp\Desktop\ShalaScope_Maharashtra\data\processed\district_year\maharashtra_district_year_shala_score_v1.csv",
    low_memory=False, nrows=2
)
cols = df.columns.tolist()

# Check infrastructure sub-indicators in detail
infra_related = [c for c in cols if any(k in c.lower() for k in [
    "toilet", "electric", "water", "drink", "library", "ramp",
    "building", "classroom", "facility", "pucca", "repair",
    "computer", "laptop", "internet", "projector", "tablet",
    "digital", "device"
])]
print("INFRASTRUCTURE/DIGITAL COLUMNS:")
for c in infra_related:
    print(f"  {c}")

# Check enrolment gender components
print("\nGENDER ENROLMENT KEY COLUMNS:")
gender_key = [c for c in cols if any(k in c for k in [
    "enrollment_reported_enrollment_b_component",
    "enrollment_reported_enrollment_g_component",
    "enrollment_reported_enrollment_t_component",
    "enrollment_reported_sc_enrollment",
    "enrollment_reported_st_enrollment",
    "enrollment_reported_general_enrollment",
    "enrollment_reported_student_total"
])]
for c in gender_key:
    print(f"  {c}")

# Check missing data for key columns
print("\nMISSING VALUE CHECK:")
df2 = pd.read_csv(
    r"c:\Users\userp\Desktop\ShalaScope_Maharashtra\data\processed\district_year\maharashtra_district_year_shala_score_v1.csv",
    low_memory=False
)
key_cols = [
    "facility_functional_toilet_pct",
    "facility_classrooms_good_condition_pct",
    "facility_avg_digital_devices_per_reporting_school",
    "enrollment_reported_enrollment_b_component_total",
    "enrollment_reported_enrollment_g_component_total",
    "ptr_students_per_teacher_raw",
    "pillar_teacher_strength",
    "pillar_infrastructure",
    "pillar_digital_readiness",
    "shala_score_v1",
    "district_female_teacher_pct",
]
for c in key_cols:
    if c in df2.columns:
        n_null = df2[c].isnull().sum()
        print(f"  {c}: {n_null}/288 null")
    else:
        print(f"  {c}: COLUMN NOT FOUND")

# Check if facility has internet/electricity columns
print("\nFACILITY COLUMNS (all):")
fac_cols = [c for c in cols if c.startswith("facility")]
for c in sorted(fac_cols):
    print(f"  {c}")

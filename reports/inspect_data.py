import pandas as pd

assign = pd.read_csv(r"reports/kmeans_grouping/kmeans_cluster_assignments.csv")
print("Current clusters:")
print(assign["cluster_label"].value_counts().to_string())

hist = pd.read_csv(r"data/processed/district_year/maharashtra_district_year_shala_score_v1.csv", low_memory=False)
districts = sorted(hist["district"].dropna().astype(str).unique().tolist())
pune_idx = districts.index("PUNE") if "PUNE" in districts else -1
print(f"\nPUNE index in sorted districts: {pune_idx}")
print(f"Total districts: {len(districts)}")

latest_year = hist["academic_year"].max()
print(f"Latest year: {latest_year}")
latest = hist[hist["academic_year"] == latest_year].copy()

print(f"Total schools: {latest['school_count'].sum():.0f}")
print(f"Total enrollment: {latest['enrollment_reported_student_total'].sum():.0f}")
print(f"Total teachers: {latest['score_teacher_total_derived'].sum():.0f}")
print(f"State avg PTR: {latest['ptr_students_per_teacher_raw'].mean():.2f}")
print(f"State avg Shala Score: {latest['shala_score_v1'].mean():.2f}")

# Pune profile
pune = latest[latest["district"] == "PUNE"].iloc[0]
print(f"\nPUNE shala_score: {pune['shala_score_v1']:.2f}")
print(f"PUNE PTR: {pune['ptr_students_per_teacher_raw']:.2f}")
print(f"PUNE toilet%: {pune['functional_toilet_pct_raw']:.2f}")
print(f"PUNE classroom%: {pune['good_classroom_pct_raw']:.2f}")
print(f"PUNE digital: {pune['digital_devices_per_school_raw']:.2f}")
print(f"PUNE repair%: {pune['facility_classrooms_needing_repair_pct']:.2f}")

# Rank of Pune
ranked = latest.sort_values("shala_score_v1", ascending=False).reset_index(drop=True)
pune_rank = ranked[ranked["district"]=="PUNE"].index[0] + 1
print(f"PUNE rank: {pune_rank} of {len(ranked)}")

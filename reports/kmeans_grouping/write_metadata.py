"""Write kmeans_metadata.json from already-saved CSV outputs."""
import json
import pandas as pd
from pathlib import Path

OUT = Path(__file__).resolve().parent

elbow = pd.read_csv(OUT / "kmeans_elbow_silhouette.csv")
summary = pd.read_csv(OUT / "kmeans_cluster_summary.csv")
assignments = pd.read_csv(OUT / "kmeans_cluster_assignments.csv")

CLUSTER_FEATURES = [
    "ptr_students_per_teacher_raw",
    "functional_toilet_pct_raw",
    "good_classroom_pct_raw",
    "digital_devices_per_school_raw",
    "facility_classrooms_needing_repair_pct",
]
FEATURE_LABELS = {
    "ptr_students_per_teacher_raw": "Students per Teacher",
    "functional_toilet_pct_raw": "Functional Toilet %",
    "good_classroom_pct_raw": "Good Classroom %",
    "digital_devices_per_school_raw": "Digital Devices / School",
    "facility_classrooms_needing_repair_pct": "Classrooms Needing Repair %",
}

optimal_k = int(elbow.loc[elbow["silhouette"].idxmax(), "k"])
best_sil = float(elbow["silhouette"].max())

eval_records = [
    {"k": int(r.k), "inertia": float(r.inertia), "silhouette": float(r.silhouette)}
    for r in elbow.itertuples()
]

cluster_labels = {}
summary_records = []
for _, row in summary.iterrows():
    c = int(row["cluster"])
    lbl = str(row["descriptive_label"])
    cluster_labels[str(c)] = lbl
    rec = {"cluster": c, "descriptive_label": lbl,
           "district_count": int(row["district_count"]),
           "mean_shala_score": float(row["mean_shala_score"])}
    for f in CLUSTER_FEATURES:
        rec[f] = float(row[f])
    summary_records.append(rec)

meta = {
    "optimal_k": optimal_k,
    "best_silhouette": best_sil,
    "random_state": 42,
    "features": CLUSTER_FEATURES,
    "feature_labels": FEATURE_LABELS,
    "evaluation": eval_records,
    "cluster_labels": cluster_labels,
    "cluster_summary": summary_records,
}

(OUT / "kmeans_metadata.json").write_text(
    json.dumps(meta, indent=2), encoding="utf-8"
)
print("Written: kmeans_metadata.json")
print(f"optimal_k={optimal_k}, best_silhouette={best_sil:.4f}")
print(f"Cluster labels: {cluster_labels}")

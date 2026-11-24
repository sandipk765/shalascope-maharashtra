"""
ShikshanDarpan AI  –  K-Means District Risk Grouping
====================================================
Groups districts with similar educational conditions using
K-Means clustering on standardized educational indicators.

Input features (all 100% populated across 288 rows):
  - Pupil-Teacher Ratio (students per teacher)
  - Functional toilet percentage
  - Good-condition classroom percentage
  - Digital devices per reporting school
  - Classroom repair percentage (needing repair)

Process:
  1. Aggregate to district-level means across all 8 years
     (one row per district = 36 rows for clustering)
  2. Impute any remaining missing values with median
  3. Standardize features (StandardScaler)
  4. Evaluate k = 2..8 using Elbow Method (inertia) and
     Silhouette Score
  5. Select optimal k using silhouette score
  6. Fit final K-Means, assign cluster labels
  7. Calculate cluster-level indicator summaries
  8. Assign descriptive labels based on actual cluster profiles
  9. Save all outputs

Outputs:
  - reports/kmeans_grouping/kmeans_cluster_assignments.csv
  - reports/kmeans_grouping/kmeans_cluster_summary.csv
  - reports/kmeans_grouping/kmeans_elbow_silhouette.csv
  - reports/kmeans_grouping/kmeans_model_artifact.joblib
  - reports/kmeans_grouping/kmeans_parameters.txt
  - reports/kmeans_grouping/kmeans_metadata.json
"""

from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import joblib

warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "data" / "processed" / "district_year"
    / "maharashtra_district_year_shala_score_v1.csv"
)

OUT = ROOT / "reports" / "kmeans_grouping"
OUT.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
K_RANGE = range(2, 9)  # test k = 2..8


# ============================================================
# 1. FEATURE SET (for clustering)
# ============================================================
CLUSTER_FEATURES = [
    "ptr_students_per_teacher_raw",
    "functional_toilet_pct_raw",
    "good_classroom_pct_raw",
    "digital_devices_per_school_raw",
    "facility_classrooms_needing_repair_pct",
]

# Human-readable labels for output tables
FEATURE_LABELS = {
    "ptr_students_per_teacher_raw": "Students per Teacher",
    "functional_toilet_pct_raw": "Functional Toilet %",
    "good_classroom_pct_raw": "Good Classroom %",
    "digital_devices_per_school_raw": "Digital Devices / School",
    "facility_classrooms_needing_repair_pct": "Classrooms Needing Repair %",
}


# ============================================================
# 2. LOAD AND AGGREGATE TO DISTRICT LEVEL
# ============================================================
def load_and_aggregate():
    if not INPUT.exists():
        raise FileNotFoundError(f"Input not found: {INPUT}")

    df = pd.read_csv(INPUT, low_memory=False)

    if len(df) != 288 or df["district"].nunique() != 36:
        raise ValueError(
            f"Unexpected shape: rows={len(df)}, "
            f"districts={df['district'].nunique()}"
        )

    # Convert features to numeric
    for c in CLUSTER_FEATURES:
        if c not in df.columns:
            raise ValueError(f"Feature column missing: {c}")
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Aggregate to district level: mean across all 8 years
    district_df = (
        df.groupby("district", as_index=False)[CLUSTER_FEATURES]
        .mean()
    )

    # Report and handle missing values
    imputation_values = {}
    for c in CLUSTER_FEATURES:
        n_missing = int(district_df[c].isna().sum())
        if n_missing > 0:
            med = float(district_df[c].median())
            district_df[c] = district_df[c].fillna(med)
            imputation_values[c] = med
            print(f"  Imputed {c}: {n_missing} missing -> median {med:.4f}")

    print(f"\nDistrict-level data: {len(district_df)} rows, "
          f"{len(CLUSTER_FEATURES)} features")

    return district_df, imputation_values


# ============================================================
# 3. EVALUATE CLUSTER COUNTS
# ============================================================
def evaluate_k_values(X_scaled):
    """Test k = 2..8 and compute inertia + silhouette."""
    results = []
    for k in K_RANGE:
        km = KMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            n_init=10,
        )
        labels = km.fit_predict(X_scaled)
        inertia = km.inertia_
        sil = silhouette_score(X_scaled, labels)

        results.append({
            "k": k,
            "inertia": float(inertia),
            "silhouette": float(sil),
        })
        print(f"  k={k}: inertia={inertia:.2f}, "
              f"silhouette={sil:.4f}")

    return pd.DataFrame(results)


# ============================================================
# 4. FIT FINAL MODEL AND ASSIGN CLUSTERS
# ============================================================
def fit_final_kmeans(X_scaled, optimal_k):
    km = KMeans(
        n_clusters=optimal_k,
        random_state=RANDOM_STATE,
        n_init=10,
    )
    labels = km.fit_predict(X_scaled)
    centers = km.cluster_centers_

    return km, labels, centers


# ============================================================
# 5. INTERPRET CLUSTERS
# ============================================================
def interpret_clusters(district_df, labels, centers, scaler, optimal_k):
    """Assign descriptive labels based on actual cluster profiles."""
    district_df = district_df.copy()
    district_df["cluster"] = labels

    # Compute cluster means in original (unscaled) space
    cluster_summary = (
        district_df.groupby("cluster")[CLUSTER_FEATURES]
        .mean()
        .round(2)
    )

    # Add cluster size
    cluster_sizes = district_df["cluster"].value_counts().sort_index()
    cluster_summary["district_count"] = cluster_sizes

    # Compute mean Shala Score per cluster for label assignment
    # (Load full dataset to get scores)
    full_df = pd.read_csv(INPUT, low_memory=False)
    full_df["shala_score_v1"] = pd.to_numeric(
        full_df["shala_score_v1"], errors="coerce"
    )
    score_by_district = full_df.groupby("district")["shala_score_v1"].mean()
    district_df["mean_shala_score"] = (
        district_df["district"].map(score_by_district)
    )
    cluster_scores = (
        district_df.groupby("cluster")["mean_shala_score"].mean().round(2)
    )
    cluster_summary["mean_shala_score"] = cluster_scores

    # Assign descriptive labels: rank clusters by mean Shala Score
    # Highest score = "Strong Educational Conditions"
    # Middle = "Moderate Educational Conditions"
    # Lowest = "Priority Support Required"
    sorted_clusters = cluster_scores.sort_values(ascending=False)
    cluster_labels = {}

    if optimal_k == 2:
        label_map = {sorted_clusters.index[0]: "Strong Educational Conditions",
                     sorted_clusters.index[1]: "Priority Support Required"}
    elif optimal_k == 3:
        label_map = {sorted_clusters.index[0]: "Strong Educational Conditions",
                     sorted_clusters.index[1]: "Moderate Educational Conditions",
                     sorted_clusters.index[2]: "Priority Support Required"}
    else:
        # For k>3, use more granular labels
        labels_list = [
            "Strong Educational Conditions",
            "Above Average Conditions",
            "Moderate Educational Conditions",
            "Below Average Conditions",
            "Priority Support Required",
            "Critical Support Required",
            "Most Critical",
            "Lowest Ranked",
        ]
        label_map = {}
        for i, c_idx in enumerate(sorted_clusters.index):
            if i < len(labels_list):
                label_map[c_idx] = labels_list[i]
            else:
                label_map[c_idx] = f"Cluster {c_idx}"

    cluster_summary["descriptive_label"] = [
        label_map.get(c, f"Cluster {c}") for c in cluster_summary.index
    ]

    # Add descriptive labels to district assignments
    district_df["cluster_label"] = district_df["cluster"].map(label_map)

    return district_df, cluster_summary, label_map


# ============================================================
# 6. SAVE OUTPUTS
# ============================================================
def save_outputs(district_df, cluster_summary, eval_df, km, scaler,
                  optimal_k, imputation_values, label_map):
    # Cluster assignments
    assign_path = OUT / "kmeans_cluster_assignments.csv"
    output_cols = ["district"] + CLUSTER_FEATURES + ["cluster", "cluster_label"]
    district_df[output_cols].to_csv(
        assign_path, index=False, encoding="utf-8-sig"
    )

    # Cluster summary
    summary_path = OUT / "kmeans_cluster_summary.csv"
    cluster_summary.to_csv(summary_path, encoding="utf-8-sig")

    # Elbow + silhouette
    eval_path = OUT / "kmeans_elbow_silhouette.csv"
    eval_df.to_csv(eval_path, index=False, encoding="utf-8-sig")

    # Model artifact (kmeans + scaler together)
    model_path = OUT / "kmeans_model_artifact.joblib"
    joblib.dump({"kmeans": km, "scaler": scaler}, model_path)

    # Parameters
    params_path = OUT / "kmeans_parameters.txt"
    params_lines = [
        "SHIKSHANDARPAN AI - K-MEANS DISTRICT RISK GROUPING",
        "=" * 60,
        "",
        f"Optimal k: {optimal_k}",
        f"Random state: {RANDOM_STATE}",
        f"n_init: 10",
        "",
        "Clustering Features:",
    ]
    for c in CLUSTER_FEATURES:
        params_lines.append(f"  - {c} ({FEATURE_LABELS.get(c, c)})")
    params_lines.extend([
        "",
        "Preprocessing:",
        "  - Aggregated to district-level means across 8 years",
        "  - StandardScaler (zero mean, unit variance)",
        "  - Median imputation for missing values",
        "",
        "Cluster Evaluation:",
    ])
    for _, row in eval_df.iterrows():
        params_lines.append(
            f"  k={row['k']}: inertia={row['inertia']:.2f}, "
            f"silhouette={row['silhouette']:.4f}"
        )
    params_lines.extend([
        "",
        "Cluster Profiles (unscaled means):",
    ])
    for c_idx, row in cluster_summary.iterrows():
        params_lines.append(
            f"\n  Cluster {c_idx}: {row['descriptive_label']}"
            f" ({row['district_count']} districts, "
            f"mean score {row['mean_shala_score']:.2f})"
        )
        for feat in CLUSTER_FEATURES:
            params_lines.append(
                f"    {FEATURE_LABELS.get(feat, feat)}: "
                f"{row[feat]:.2f}"
            )

    params_lines.extend([
        "",
        "Imputation:",
    ])
    for c, val in imputation_values.items():
        params_lines.append(f"  {c}: median {val:.4f}")
    if not imputation_values:
        params_lines.append("  No imputation needed.")
    params_lines.extend([
        "",
        "=" * 60,
        "Cluster labels are assigned based on actual cluster profiles",
        "(ranked by mean Shala Score), not assumed cluster numbers.",
        "=" * 60,
    ])
    params_path.write_text("\n".join(params_lines), encoding="utf-8")

    # JSON metadata — write from clean Python dicts
    eval_records = [
        {"k": int(r["k"]), "inertia": float(r["inertia"]),
         "silhouette": float(r["silhouette"])}
        for r in eval_df.to_dict(orient="records")
    ]
    summary_records = []
    for c_idx, row in cluster_summary.iterrows():
        rec = {"cluster": int(c_idx),
               "descriptive_label": str(row["descriptive_label"]),
               "district_count": int(row["district_count"]),
               "mean_shala_score": float(row["mean_shala_score"])}
        for feat in CLUSTER_FEATURES:
            rec[feat] = float(row[feat])
        summary_records.append(rec)
    meta = {
        "optimal_k": int(optimal_k),
        "best_silhouette": float(eval_df["silhouette"].max()),
        "random_state": int(RANDOM_STATE),
        "features": CLUSTER_FEATURES,
        "feature_labels": FEATURE_LABELS,
        "evaluation": eval_records,
        "cluster_labels": {str(k): str(v) for k, v in label_map.items()},
        "cluster_summary": summary_records,
        "imputation_values": {k: float(v) for k, v in imputation_values.items()},
    }
    meta_path = OUT / "kmeans_metadata.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, default=str), encoding="utf-8"
    )

    print(f"\nOutputs saved to {OUT}")
    print(f"  Assignments: {assign_path}")
    print(f"  Summary: {summary_path}")
    print(f"  Evaluation: {eval_path}")
    print(f"  Model: {model_path}")
    print(f"  Parameters: {params_path}")
    print(f"  Metadata: {meta_path}")


# ============================================================
# 7. MAIN
# ============================================================
def main():
    print("=" * 65)
    print("SHIKSHANDARPAN AI - K-MEANS DISTRICT GROUPING")
    print("=" * 65)

    # Load and aggregate
    district_df, imputation_values = load_and_aggregate()

    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(district_df[CLUSTER_FEATURES])

    # Evaluate k values
    print("\nEvaluating k = 2..8:")
    eval_df = evaluate_k_values(X_scaled)

    # Select optimal k (highest silhouette)
    optimal_k = int(eval_df.loc[eval_df["silhouette"].idxmax(), "k"])
    print(f"\nOptimal k (by silhouette): {optimal_k}")

    # Fit final model
    km, labels, centers = fit_final_kmeans(X_scaled, optimal_k)

    # Interpret clusters
    district_df, cluster_summary, label_map = interpret_clusters(
        district_df, labels, centers, scaler, optimal_k
    )

    # Save
    save_outputs(
        district_df, cluster_summary, eval_df, km, scaler,
        optimal_k, imputation_values, label_map
    )

    # Print summary
    print("\n" + "=" * 65)
    print("CLUSTER PROFILES")
    print("=" * 65)
    print(cluster_summary.to_string())
    print("\n" + "=" * 65)
    print("DISTRICT ASSIGNMENTS")
    print("=" * 65)
    print(district_df[["district", "cluster", "cluster_label"]]
          .sort_values("cluster").to_string(index=False))
    print(f"\nOptimal k: {optimal_k}")
    print(f"Best silhouette: {eval_df['silhouette'].max():.4f}")
    print("\nSTATUS: COMPLETE")


if __name__ == "__main__":
    main()

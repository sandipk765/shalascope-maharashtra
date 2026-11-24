# ShikshanDarpan AI
## District-Wise Educational Audit & Dropout Risk Factor Analysis in Maharashtra
### Complete Project Documentation

---

## 1. Project Overview

**ShikshanDarpan AI** is an upgrade of ShalaScope Maharashtra. It retains the existing Shala Score pipeline and 2026-27 forecasting, and adds three new analytical modules:

1. **Random Forest Educational Risk Factor Analysis** — identifies which educational indicators are most strongly associated with educational conditions
2. **K-Means District Risk Grouping** — groups districts with similar educational profiles using unsupervised clustering
3. **Educational Audit** — district-level diagnostic report against state benchmarks and project thresholds

**Important limitation:** No dropout or retention data exists in the UDISE+ district-year dataset. The platform does NOT predict student dropout. The "Dropout Risk Factor" label in the project title refers to educational infrastructure and staffing risk factors that may be associated with poor educational conditions — it does not refer to actual observed dropout rates, which are not in the dataset.

---

## 2. Dataset and Available Indicators

**Source:** UDISE+ school education records, Maharashtra
**Coverage:** 36 districts × 8 academic years (2018-19 to 2025-26) = 288 district-year records

### Core Score Indicators (100% populated, 288/288 rows)

| Column | Description | Type | ML-Ready |
|---|---|---|---|
| `ptr_students_per_teacher_raw` | Students per teacher | Float | Yes |
| `functional_toilet_pct_raw` | Functional toilet % | Float | Yes |
| `good_classroom_pct_raw` | Good-condition classroom % | Float | Yes |
| `digital_devices_per_school_raw` | Digital devices per reporting school | Float | Yes |
| `facility_classrooms_needing_repair_pct` | Classrooms needing repair % | Float | Yes |
| `school_count` | Number of schools per district | Integer | Yes |
| `enrollment_reported_student_total` | Total reported student enrollment | Integer | Yes |
| `score_teacher_total_derived` | M+F+Transgender teacher total | Integer | Yes |
| `shala_score_v1` | Composite educational condition index (0-100) | Float | Yes (target) |

### Partially Populated Indicators (144/288 rows — 50%)

| Column | Description |
|---|---|
| `district_female_teacher_pct` | Female teacher share % |
| `district_regular_teacher_pct` | Regular teacher share % |
| `district_contract_teacher_pct` | Contract teacher share % |
| `district_computer_trained_teacher_pct` | Computer-trained teacher % |

These are imputed with median values in ML models.

### Not Available

| Indicator | Status |
|---|---|
| Student dropout rate | NOT IN DATASET |
| Student retention rate | NOT IN DATASET |
| Learning outcome scores | NOT IN DATASET |

---

## 3. Data Cleaning Process

1. Raw UDISE+ ZIP archives extracted to `data/extracted/`
2. School-level CSVs aggregated to district-year level via SQLite in-memory joins
3. 659-column final master produced by `build_final_district_year_dataset.py`
4. All 4 Shala Score input indicators have 0 missing values in the 288-row master
5. Teacher-percentage columns (50% missing) imputed with median in ML models

No original source files were modified.

---

## 4. Feature Engineering Formulas

### Pupil-Teacher Ratio (PTR)
```
PTR = Enrollment Total / (Male Teachers + Female Teachers + Transgender Teachers)
     (where teacher total > 0; NaN if zero or missing)
```

### Infrastructure Indicators (direct from UDISE+ facility data)
```
Functional Toilet % = (Functional Toilets / Total Toilets) × 100
Good Classroom % = (Classrooms in Good Condition / Total Classrooms Reported) × 100
Classrooms Needing Repair % = (Minor + Major Repair Classrooms) / Total × 100
```

### Shala Score (unchanged from V1)
```
S = (Teacher Strength + Infrastructure + Digital Readiness) / 3
Infrastructure = (Functional Toilet Score + Good Classroom Score) / 2
Scores normalized using P5-P95 winsorized min-max (pooled across 288 rows)
```

---

## 5. Random Forest Methodology

**Script:** `src/models/run_rf_risk_factor_analysis.py`

**Objective:** Identify which educational indicators are most statistically associated with the Shala Score (educational condition index). No dropout data exists in this dataset; the model identifies indicators of poor educational conditions, not actual dropout causes.

**Target:** `shala_score_v1` — the validated composite educational condition index

**Features (12 total):**
- school_count
- enrollment_reported_student_total
- score_teacher_total_derived
- ptr_students_per_teacher_raw
- functional_toilet_pct_raw
- good_classroom_pct_raw
- digital_devices_per_school_raw
- facility_classrooms_needing_repair_pct
- district_female_teacher_pct (imputed)
- district_regular_teacher_pct (imputed)
- district_contract_teacher_pct (imputed)
- district_computer_trained_teacher_pct (imputed)

**Model parameters:**
- n_estimators=300, max_depth=8, min_samples_leaf=3, max_features=0.7, random_state=42

**Validation:** 5-fold KFold (shuffle=True, random_state=42)

**Note:** KFold (not chronological) is used because the purpose is cross-sectional risk factor identification, not time-series forecasting.

---

## 6. Random Forest Evaluation Results

| Metric | Value |
|---|---|
| Cross-validated MAE | 2.08 Shala Score points |
| Cross-validated R² | 0.949 |
| Validation method | 5-fold KFold |
| Training samples | 288 |
| Features | 12 |

### Feature Importance Ranking

| Rank | Feature | Importance |
|---|---|---|
| 1 | Good-Condition Classrooms % | 0.3301 |
| 2 | Classrooms Needing Repair % | 0.2536 |
| 3 | Functional Toilet Coverage % | 0.1338 |
| 4 | Pupil-Teacher Ratio | 0.1176 |
| 5 | Digital Devices per School | 0.0879 |
| 6 | Female Teacher Share % | 0.0363 |
| 7-12 | (School count, computer %, contract %, enrollment, teachers, regular %) | <0.01 each |

---

## 7. K-Means Methodology

**Script:** `src/models/run_kmeans_district_grouping.py`

**Objective:** Group districts with similar educational conditions.

**Input:** District-level means across 8 years (36 district × 5 feature matrix)

**Features:** PTR, Functional Toilet %, Good Classroom %, Digital Devices/School, Classrooms Needing Repair %

**Preprocessing:** StandardScaler (zero mean, unit variance)

**Cluster evaluation:** k=2..8, inertia + silhouette score

---

## 8. K-Means Evaluation Results

| k | Inertia | Silhouette |
|---|---|---|
| 2 | 106.45 | **0.4287** (optimal) |
| 3 | 76.95 | 0.2625 |
| 4 | 55.16 | 0.2918 |
| 5 | 42.14 | 0.2948 |
| 6 | 34.96 | 0.3626 |
| 7 | 29.20 | 0.2454 |
| 8 | 22.75 | 0.2807 |

**Optimal k=2** (highest silhouette = 0.4287, indicating moderate-to-strong cluster separation)

### Cluster Profiles

| Cluster | Label | Districts | Mean Shala Score | PTR | Toilet % | Classroom % | Repair % | Devices |
|---|---|---|---|---|---|---|---|---|
| 0 | Strong Educational Conditions | 9 | 48.44 | 32.59 | 97.91 | 93.86 | 6.14 | 13.42 |
| 1 | Priority Support Required | 27 | 34.98 | 26.75 | 95.24 | 86.90 | 13.10 | 4.38 |

Cluster 0 (Strong): Pune, Mumbai II, Mumbai Suburban, Nagpur, Nashik, Thane, Dhule, Jalgaon, Palghar
Cluster 1 (Priority): Remaining 27 districts

Labels are assigned based on ranked mean Shala Scores after clustering. Cluster 0 is not automatically "best" — it was confirmed to have the higher mean score.

---

## 9. Educational Root-Cause Indicator Analysis

**Script:** `src/models/build_rootcause_indicators.py`

**Thresholds used:**

| Indicator | Adequate | Concern | Critical |
|---|---|---|---|
| PTR | ≤ 30:1 (RTE norm) | 30-35:1 | > 35:1 |
| Functional Toilet % | ≥ 90% | 85-90% | < 85% |
| Good Classroom % | ≥ 90% | 75-90% | < 75% |
| Classrooms Needing Repair % | < 10% | 10-20% | > 20% |
| Digital Devices/School | ≥ 5 | 2-5 | < 2 |

---

## 10. Dashboard Functionality

| Tab | Content |
|---|---|
| 01 Overview | Maharashtra KPIs, top/bottom 10, trend, priority matrix, choropleth map |
| 02 District Explorer | District profile, diagnostic card, comparison, forecast |
| 03 Education Analytics | 10 indicators, bar charts, RTE norm line, correlation |
| 04 Predictive Intelligence | 6 what-if workspaces (2026-27 forecast) |
| 05 Data Quality & Methodology | Coverage heatmap, Shala Score formula, limitations |
| **06 Risk Factor Analysis** | **RF feature importance, CV results, interpretation** |
| **07 District Grouping** | **K-Means clusters, radar chart, district membership** |
| **08 Educational Audit** | **Overview KPIs, concern heatmap, diagnostic report card** |

---

## 11. Known Limitations

1. **No dropout data exists** — the platform cannot predict student dropout. It identifies educational infrastructure and staffing risk factors associated with low Shala Scores.
2. **Pooled normalization** — Shala Scores are relative to the 8-year pooled distribution. Year-to-year changes reflect both real change and shifts in relative standing.
3. **Ceiling effect** — Mumbai II and Mumbai (Suburban) score 100 on digital readiness due to the P95 ceiling. They cannot be further distinguished on this dimension.
4. **Persistence forecast** — 4 of 5 forecast targets use the Persistence baseline (last year's value carried forward). These are not predictive models.
5. **50% missing teacher-percentage columns** — `district_*_teacher_pct` columns are only available for 144 of 288 rows. Imputed with median in RF model.
6. **K-Means sensitivity** — With only 36 districts, cluster assignments can change with initialization. `random_state=42` and `n_init=10` ensure reproducibility.

---

## 12. Distinction Between Model Types

| Output | Type | What It Is |
|---|---|---|
| Shala Score | Formula-derived index | Composite indicator, not a prediction |
| 2026-27 Forecast | Statistical extrapolation | Persistence or linear trend, not an ML prediction |
| RF Feature Importance | Associative ML | Which indicators statistically associate with conditions |
| K-Means Clusters | Unsupervised grouping | Districts with similar profiles, not risk predictions |
| Diagnostic Flags | Rule-based threshold check | Indicators below project benchmarks, not risk predictions |

Do not present correlations or feature importance as proof of causation. No model in this project predicts dropout rates.

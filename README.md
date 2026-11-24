# ShalaScope Maharashtra

District-level school education intelligence and predictive analytics for
Maharashtra's 36 districts, built entirely on the UDISE+ public dataset
(2018-19 to 2025-26).

---

## What this project does

- Computes **Shala Score v2** (5-pillar weighted composite, 0-100) for every
  district-year, with proportional weight redistribution when a pillar's source
  data is absent.
- Maps all 36 districts to Maharashtra's four geographic regions
  (Konkan, Western Maharashtra, Marathwada, Vidarbha).
- Runs five prediction modules (M1-M5) with strict chronological splits and
  zero future leakage.
- Produces SHAP explanations for the two Random Forest models (M4, M5).
- Serves an interactive 10-tab Streamlit dashboard (tabs 00 Home through
  09 Region Comparison).

---

## Data principles

| Rule | Detail |
|---|---|
| No synthetic data | Every number comes from the UDISE+ extract. Missing columns are documented as `MISSING_IN_SOURCE`, never imputed or fabricated. |
| No source file mutation | Raw CSVs in `data/extracted/` are never touched. All derived outputs land in `data/processed/` or `reports/`. |
| No double-counting | `facility_classrooms_good_condition_pct` is in the **Infrastructure pillar only** and is not reused in the Learning pillar. |
| Leakage guard | Temporal split: train 2018-19 to 2023-24 (216 rows), test 2024-25 (36 rows). Forecast horizon: 2025-26 / 2026-27. |
| M2 substitute | No NAS/ASER/GER/dropout data exists in UDISE+. M2 uses `pillar2_infrastructure` as a documented proxy, clearly labelled `SUBSTITUTE_PROXY` in every output. |
| M5 label | M5 is labelled "Classroom Infrastructure Quality Trend (Documented Proxy)" -- not a learning-outcome or dropout predictor. |

---

## Year scope

| Scope | Years | Rows | Notes |
|---|---|---|---|
| Full dataset | 2018-19 to 2025-26 | 288 | Complete UDISE+ extract available |
| Spec primary window | 2019-20 to 2024-25 | 216 | Core modelling and reporting window |
| Edge years | 2018-19 and 2025-26 | 72 | 2018-19 anchors trend models; 2025-26 is provisional |

Modelling split: **train** 2018-19 to 2023-24 (216 rows), **test** 2024-25 (36 rows),
**forecast** horizon 2025-26 and 2026-27 (never in train or test).

---

## 36 Districts and 4 regions

| Region | n | Districts |
|---|---|---|
| Konkan | 7 | Mumbai II, Thane, Palghar, Raigad, Ratnagiri, Sindhudurg, Mumbai (Suburban) |
| Western Maharashtra | 10 | Pune, Nashik, Ahilyanagar, Solapur, Satara, Sangli, Kolhapur, Dhule, Nandurbar, Jalgaon |
| Marathwada | 8 | Chhatrapati Sambhajinagar, Jalna, Beed, Latur, Dharashiv, Nanded, Hingoli, Parbhani |
| Vidarbha | 11 | Nagpur, Wardha, Yavatmal, Amravati, Akola, Washim, Buldhana, Chandrapur, Gadchiroli, Gondia, Bhandara |

District names use current official names (Ahilyanagar not Ahmednagar,
Chhatrapati Sambhajinagar not Aurangabad, Dharashiv not Osmanabad, etc.).
Verified 0 unmapped districts in `src/core/regions.py`.

GPI range: 0.80-0.98. Marginalised enrolment: 12.9-96.2%.

---

## Shala Score v2 -- pillar design

| Pillar | Nominal weight | Effective weight (this dataset) | Source columns |
|---|---|---|---|
| Teacher PTR | 25% | 29.4% (redistributed) | `ptr_students_per_teacher_raw` |
| Infrastructure | 25% | 29.4% (redistributed) | `facility_functional_toilet_pct`, `facility_classrooms_good_condition_pct` |
| Participation | 25% | 23.5% (redistributed) | Boys + Girls enrolment totals, SC/ST/OBC breakdown |
| Digital | 25% | 17.6% (redistributed) | `facility_avg_digital_devices_per_reporting_school` |
| Learning | 15% | **0% -- MISSING_IN_SOURCE** | No NAS/ASER/GER/dropout data in UDISE+ |

Redistribution formula: `eff_weight_i = nominal_i / sum(nominal_j for available j)`.
Weights sum to 1.0 per row after redistribution.

Score range: **24.90 to 72.16** across 288 district-years.
Four equal-size risk tiers (72 districts each):

| Tier | Meaning |
|---|---|
| Thriving | Top quartile Shala Score v2 |
| Stable | Second quartile |
| At-Risk | Third quartile |
| Critical | Bottom quartile |

---

## Five prediction modules

| ID | Model | Target | Metric | Notes |
|---|---|---|---|---|
| M1 | LinearRegression | Total student enrolment | R2=0.7784 | District-year trend |
| M2 | Ridge | `pillar2_infrastructure` | R2=0.5204 | **SUBSTITUTE_PROXY** -- Learning MISSING_IN_SOURCE |
| M3 | Holt-Winters per district | `enrollment_reported_student_total` | R2=0.9967 | 36/36 districts fitted; 2-year forecast |
| M4 | RandomForestClassifier | PTR > 30 (teacher shortage) | Acc=0.972 F1=0.973 | RTE norm; PTR not in feature set |
| M5 | RandomForestClassifier | `risk_tier_v2` | Acc=0.694 F1=0.671 | Classroom Infra Quality Trend proxy -- NOT learning outcome |

Temporal split: train 2018-19 to 2023-24 (216 rows), test 2024-25 (36 rows).
Forecast horizon: 2025-26 and 2026-27.

**Leakage guards:**
- M1: PTR not in feature set.
- M3: each district model fitted on its own train history only.
- M4: PTR used as target threshold, not as feature.
- M5: `shala_score_v2` (composite) excluded from features.

---

## SHAP explainability

TreeExplainer applied to M4 and M5 on the 2024-25 test slice (36 district-rows).

| Model | Top 3 global drivers (mean |SHAP|) |
|---|---|
| M4 Teacher Shortage Risk | enrollment_reported_student_total, pillar2_infrastructure, pillar2_participation |
| M5 Classroom Infra Proxy | pillar2_participation, pillar2_infrastructure, pillar2_digital |

Output files in `reports/explainability/`:

```
m4_shap_values.csv           m5_shap_values.csv
m4_shap_feature_ranking.csv  m5_shap_feature_ranking.csv
m4_shap_top_driver.csv       m5_shap_top_driver.csv
shap_status.csv
```

The dashboard (Tab 02 District Explorer) shows each district's M5 top SHAP driver.
Fallback: if SHAP is unavailable a status notice is shown instead of raising.

---

## 10-tab dashboard

`dashboard/app.py` (3395 lines, 10 tabs):

| Tab | Contents |
|---|---|
| 00 Home | Scope badges, live KPIs, v2 score strip, tab navigation cards, data-principle steps |
| 01 Overview | Maharashtra KPIs, priority matrix, state trend, choropleth map, v2 score strip |
| 02 District Explorer | v2 risk tier badge, M5 SHAP top driver, ratio bars, score history, forecast |
| 03 Education Analytics | Single-indicator bar/trend, relationship explorer (scatter + correlation) |
| 04 Predictive Intelligence | M1-M5 model output sub-tabs + non-destructive What-If simulator |
| 05 Data Quality & Methodology | AVAILABLE vs MISSING_IN_SOURCE audit, coverage heatmap, score methodology |
| 06 Risk Factor Analysis | Random Forest feature importance predicting Shala Score |
| 07 District Grouping | K-Means clusters, elbow/silhouette chart, cluster profiles and radar |
| 08 Educational Audit | District diagnostic report card vs state benchmarks |
| 09 Region Comparison | Konkan/W.Mah/Marathwada/Vidarbha KPIs, trends, risk tier stacked bar, pillar heatmap |

---

## Project structure

```
ShalaScope_Maharashtra/
├── data/
│   ├── extracted/              raw UDISE+ CSVs (never modified)
│   └── processed/
│       └── district_year/      scored CSVs (v1 288x677, v2 288x688, forecast)
├── src/
│   ├── core/
│   │   └── regions.py          36-district region map, GPI, marginalised %
│   ├── features/
│   │   ├── build_shala_score_v2.py   5-pillar Shala Score v2
│   │   └── build_data_log.py         column availability audit
│   ├── models/
│   │   └── run_prediction_modules.py M1-M5 prediction modules
│   └── explainability/
│       └── shap_explainer.py         SHAP for M4 and M5
├── models/                     saved joblib artifacts
│   ├── m1_enrolment_trend.joblib
│   ├── m2_learning_proxy.joblib
│   ├── m3_total_enrolment_hw.joblib
│   ├── m4_teacher_shortage_rf.joblib
│   └── m5_risk_class_rf.joblib
├── reports/
│   ├── models/                 per-module CSVs + all_modules_metrics_summary.csv
│   ├── explainability/         SHAP values, rankings, top drivers, shap_status.csv
│   └── score_design/           v2 weights, normalization params, PCA, ranking
├── dashboard/
│   └── app.py                  Streamlit dashboard (10 tabs)
├── notebooks/
│   ├── 01_audit_and_cleaning.ipynb
│   ├── 02_shala_score_v2.ipynb
│   ├── 03_region_analysis.ipynb
│   ├── 04_prediction_models.ipynb
│   └── 05_models_and_shap.ipynb
├── tests/
│   ├── test_regions.py         14 tests -- region map, GPI, marginalised %
│   └── test_score_v2.py        14 tests -- shape, range, tiers, no fabrication
├── docs/
│   ├── data_log.md             9-section column audit with year scope
│   └── data_log.xlsx           4-sheet machine-readable version
└── requirements.txt
```

---

## Running the pipeline

All commands run from the project root with the virtual environment active.

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Step 1 -- build column availability audit (docs/data_log.md + .xlsx)
python src/features/build_data_log.py

# Step 2 -- build Shala Score v2 (data/processed/district_year/..._v2.csv)
python src/features/build_shala_score_v2.py

# Step 3 -- run all 5 prediction modules (models/*.joblib + reports/models/*.csv)
$env:PYTHONIOENCODING="utf-8"
python src/models/run_prediction_modules.py

# Step 4 -- run SHAP explainability (reports/explainability/*.csv)
python src/explainability/shap_explainer.py

# Step 5 -- run unit tests (must be 28/28)
python -m pytest tests/ -v

# Step 6 -- launch dashboard
streamlit run dashboard/app.py
```

Expected test output: `28 passed, 1 warning` (the warning is expected: GPI
with zero boys enrollment triggers a UserWarning by design).

---

## Requirements

Key packages (see `requirements.txt` for full list):

```
streamlit
pandas
numpy
plotly
scikit-learn
statsmodels>=0.14
shap>=0.44
joblib
scipy
openpyxl
pytest
```

---

## Limitations and disclaimers

- Shala Score is an **analytical index**, not a government-certified ranking.
- **M2** uses a classroom-quality proxy (`pillar2_infrastructure`) because no
  learning outcome data (NAS/ASER/GER/dropout) exists in UDISE+. It is labelled
  `SUBSTITUTE_PROXY` in every output file.
- **M5** predicts `risk_tier_v2`, which is derived from pillar scores that
  include classroom quality. It is labelled "Classroom Infrastructure Quality
  Trend (Documented Proxy)" -- not a dropout or learning outcome predictor.
- M4 and M5 are trained on 36-district cross-sections across 6 years.
  Small N limits generalisation beyond Maharashtra.
- Forecast outputs are experimental estimates, not official government projections.
- SHAP values indicate statistical association, not causal direction.
- 2025-26 data is provisional/partial; treat values as indicative until
  officially confirmed by UDISE+.

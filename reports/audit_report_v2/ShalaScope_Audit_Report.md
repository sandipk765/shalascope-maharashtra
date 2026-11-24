# ShalaScope Maharashtra
## Complete Project Audit Report

**District-Level School Education Intelligence & Predictive Analytics Platform**

---

**Audit Date:** 19 November 2026  
**Auditor:** Independent External Review  
**Project Location:** ShalaScope_Maharashtra  
**Version:** V1 Scope  

---

## 1. Professional Cover

| | |
|---|---|
| **Project Title** | ShalaScope Maharashtra |
| **Subtitle** | District-Level School Education Intelligence & Predictive Analytics Platform |
| **Geographic Scope** | 36 districts of Maharashtra |
| **Temporal Scope** | 2018-19 to 2025-26 (8 academic years) |
| **Forecast Horizon** | 2026-27 |
| **Data Source** | UDISE+ school education records |
| **Data Storage** | Local CSV datasets |
| **Dashboard** | Python + Streamlit |
| **Audit Type** | Complete technical, methodological, and academic audit |

---

## 2. Executive Summary

ShalaScope Maharashtra is a complete, functional data science project with a verified end-to-end pipeline from raw UDISE+ ZIP archives through to a working Streamlit dashboard with six what-if workspaces.

**What was verified:**
- 288 district-year records across 36 districts and 8 academic years
- Shala Score formula mathematically correct
- ML validation framework methodologically sound with no data leakage
- All 10 principal numeric claims independently recalculated and confirmed
- 49 raw ZIP archives all passed integrity checks
- Zero duplicate records, zero invalid values in score inputs

**What was found needing correction:**
- 3 critical issues (missing `scikit-learn` in requirements, missing academic report, Teacher What-If workspace inconsistency)
- 7 major issues (dead variable, ceiling effect, empty directories, deprecated API parameter, missing README, pooled normalization documentation, schema documentation)
- 10 minor issues

**Verdict: Ready After Minor Corrections.** The 4 critical fixes can be completed in under 2 hours. None require retraining models, changing formulas, or regenerating data.

---

## 3. Project Overview

### 3.1 Project Statistics

| Metric | Value | Status |
|---|---|---|
| Districts | 36 | PASS |
| Academic years | 8 (2018-19 to 2025-26) | PASS |
| District-year records | 288 | PASS |
| Master dataset columns | 659 | PASS |
| Raw ZIP archives | 49 | PASS |
| Extracted CSV files | 49 | PASS |
| Forecast targets | 5 | PASS |
| Validation folds | 5 | PASS |
| What-if workspaces | 6 | PASS |
| Dashboard modules | 5 | PASS |

### 3.2 Composite Score Design

The Shala Score is a relative descriptive index combining three equally weighted pillars:

```
Shala Score = (Teacher Strength + Infrastructure + Digital Readiness) / 3
```

```
Infrastructure = (Functional Toilet Score + Good Classroom Score) / 2
```

**Effective indicator weights:**

| Indicator | Weight | Direction |
|---|---|---|
| Teacher Strength (PTR) | 33.33% | Lower is better |
| Functional Toilet % | 16.67% | Higher is better |
| Good Classroom % | 16.67% | Higher is better |
| Digital Devices / School | 33.33% | Higher is better |

### 3.3 Forecasting Scope

| Target | Selected Method | MAE |
|---|---|---|
| Student Enrollment | Persistence | 15,126 students |
| Teacher Count | Persistence | 370 teachers |
| Functional Toilet % | Persistence | 0.455 pp |
| Good Classroom % | Persistence | 0.508 pp |
| Digital Readiness | District Linear Trend | 0.641 devices |

---

## 4. Overall Project Health

| Domain | Score / 100 | Status |
|---|---|---|
| Data Quality | 82 | PASS |
| Data Processing | 80 | PASS |
| Shala Score Methodology | 85 | PASS |
| Machine Learning | 78 | NEEDS REVIEW |
| Forecasting | 84 | PASS |
| What-If Scenarios | 74 | NEEDS REVIEW |
| Dashboard | 76 | NEEDS REVIEW |
| Python Code Quality | 79 | PASS |
| Documentation | 70 | NEEDS REVIEW |
| Reproducibility | 72 | NEEDS REVIEW |

**Average: 78/100 — Ready After Minor Corrections**

---

## 5. Project Structure Audit

### 5.1 Directory Inventory

| Directory | Files | Status |
|---|---|---|
| `src/aggregation/` | 6 scripts | PASS |
| `src/features/` | 7 scripts | PASS |
| `src/models/` | 2 scripts | PASS |
| `src/validation/` | 26 scripts | PASS |
| `src/ingestion/` | 2 scripts | PASS |
| `src/cleaning/` | 0 files | MISSING |
| `dashboard/` | app.py | PASS |
| `dashboard/pages/` | 0 files | PARTIAL |
| `models/` | 0 files | PARTIAL |
| `notebooks/` | 0 files | PARTIAL |
| `reports/final/` | 0 files | MISSING |
| `.streamlit/` | config.toml | PASS |
| `data/raw/udise_zip/` | 49 ZIPs | PASS |
| `data/extracted/` | 49 CSVs | PASS |
| `data/processed/` | 106 CSV + 16 CSV.GZ | PASS |
| `data/interim/` | 24 CSVs | PASS |
| `docs/column_mapping/` | Mapping files | PASS |

### 5.2 Key Output Files

| File | Path | Status |
|---|---|---|
| Shala Score CSV | `data/processed/district_year/maharashtra_district_year_shala_score_v1.csv` | PASS |
| Forecast CSV | `data/processed/district_year/maharashtra_district_year_forecast_2026_27.csv` | PASS |
| Final Master CSV | `data/processed/district_year/maharashtra_district_year_final_master.csv` | PASS |
| OOF Predictions | `reports/ml_modeling_baseline/baseline_oof_predictions.csv` | PASS |
| Model Summary | `reports/ml_modeling_baseline/baseline_model_summary.csv` | PASS |
| Fold Metrics | `reports/ml_modeling_baseline/baseline_fold_metrics.csv` | PASS |
| Normalization Parameters | `reports/score_design/shala_score_normalization_parameters_v1.csv` | PASS |
| Academic Report | `reports/final/` | MISSING |
| README.md | Project root | MISSING |

---

## 6. Data Sources and Coverage

### 6.1 Raw Data Inventory

| Year | Data Types | Files | Status |
|---|---|---|---|
| 2018-19 | enr1, enr2, fac, prof1, prof2, tch | 6 | PASS |
| 2019-20 | enr1, enr2, fac, prof1, prof2, tch | 6 | PASS |
| 2020-21 | enr1, enr2, fac, prof1, prof2, tch | 6 | PASS |
| 2021-22 | enr1, enr2, fac, prof1, prof2, tch | 6 | PASS |
| 2022-23 | enr1, enr2, fac, prof1, prof2, tch | 6 | PASS |
| 2023-24 | enr1, enr2, fac, prof1, prof2, tch | 6 | PASS |
| 2024-25 | enr1, enr2, fac, prof1, prof2, tch | 6 | PASS |
| 2025-26 | enr1, enr2, fac, prof1, prof2, tch, safety | 7 | PASS |
| **Total** | | **49** | **PASS** |

### 6.2 ZIP Integrity

All 49 ZIP files passed `zipfile.testzip()` integrity verification. Zero corrupt archives.

### 6.3 Filename Naming Convention

| Period | Prefix | Example |
|---|---|---|
| 2018-19 to 2021-22 | `127_` | `127_enr1.csv` |
| 2022-23 to 2025-26 | `27_` | `27_enr1.csv` |

This reflects a UDISE+ source naming change. Processing scripts use `rglob("*.csv")` and are unaffected. Status: PASS with documentation note.

### 6.4 District-Year Coverage

| Year | Districts | Status |
|---|---|---|
| 2018-19 | 36 | PASS |
| 2019-20 | 36 | PASS |
| 2020-21 | 36 | PASS |
| 2021-22 | 36 | PASS |
| 2022-23 | 36 | PASS |
| 2023-24 | 36 | PASS |
| 2024-25 | 36 | PASS |
| 2025-26 | 36 | PASS |

All 8 years have exactly 36 districts. Total: 288 district-year records. Verified.

---

## 7. Data Ingestion and Processing

### 7.1 Pipeline Architecture

```
UDISE+ ZIPs (49 files)
    ↓ extract_archives.py
Extracted CSVs (49 files)
    ↓ build_school_year_master.py (SQLite in-memory)
School-Year Master (8 files)
    ↓ build_integrated_school_year.py
Integrated School-Year (8 files)
    ↓ Feature builders (7 scripts)
School-Year Features (per type)
    ↓ build_district_year_dataset.py + build_final_district_year_dataset.py
District-Year Final Master (288 rows × 659 cols)
    ↓ build_shala_score_v1.py
Shala Score V1 (288 rows with scores)
```

### 7.2 Schema Evolution

Column counts change across UDISE+ survey versions:

| File Type | 2018-21 | 2022-25 | 2025-26 | Change |
|---|---|---|---|---|
| enr1 / enr2 | 28 cols | 29 cols | 42 cols | +14 in 2025-26 |
| fac | 41 cols | 70 cols | 82 cols | +29 from 2022 |
| prof1 | 53-54 cols | 38 cols | 49 cols | Reduced then restored |
| prof2 | 63 cols | 17 cols | 17 cols | -46 from 2022 |
| tch | 32 cols | 38 cols | 38 cols | +6 from 2022 |

The pipeline handles these breaks via column-name mapping, not positional indexing. Status: PASS.

---

## 8. Data Quality Assessment

### 8.1 Structural Checks

| Check | Result | Status |
|---|---|---|
| ZIP integrity (49 files) | 49/49 OK | PASS |
| CSV readability (49 files) | 49/49 readable | PASS |
| Zero read errors | Confirmed | PASS |
| Zero duplicate rows in raw CSVs | Confirmed | PASS |
| Zero negative enrollment values | Confirmed | PASS |
| Zero negative teacher counts | Confirmed | PASS |
| Toilet % in [0, 100] | 0 violations | PASS |
| Classroom % in [0, 100] | 0 violations | PASS |
| Duplicate district-year keys | 0 | PASS |
| Score inputs missing values | 0 (all 288 complete) | PASS |

### 8.2 Missing Values in Non-Score Columns

All 56 missing-value findings are in `prof1.csv` administrative boundary fields (assembly, parliamentary, city, municipality). These are structurally absent for rural schools. None affect the Shala Score.

| Field | Years Affected | Missing % | Impact |
|---|---|---|---|
| `assembly`, `parliamentary` | 2018-19 | 100% | None — not used in any feature |
| `city`, `municipality` | 2018-20 | 52-68% | None — rural schools have no city |
| `lgd_urban_local_body_name` | 2021-26 | ~74% | None — absent for rural schools |
| `lgd_vill_name` | 2021-26 | ~26% | None — absent for urban schools |
| `year_of_recognition_*` | All years | 0.01-90% | None — not used in score |
| `enrichment_activities` | 2025-26 only | 16.7% | None — new field, not in pipeline |

### 8.3 The 142 CSV Claim

| Category | Count |
|---|---|
| Raw extracted CSVs | 49 |
| Processed plain CSVs | 106 |
| Processed CSV.GZ files | 16 |
| Interim CSVs | 24 |
| Training pair CSVs | 10 |
| **142-file audit covers** | **Processed + interim + training pair files** |

The claim "142 CSV files passed structural checks" is technically correct but refers to processed pipeline files, not raw source files. Status: PASS with documentation recommendation.

---

## 9. District-Year Master Dataset

| Check | Result | Status |
|---|---|---|
| Total rows | 288 | PASS |
| Unique districts | 36 | PASS |
| Academic years | 8 | PASS |
| Duplicate keys | 0 | PASS |
| Total columns | 659 | PASS |
| All 4 score inputs present | Yes (PTR, toilet %, classroom %, digital devices) | PASS |
| Teacher total derivation | `male + female + transgender` with `min_count=3` | PASS |
| Teacher reconciliation | Cross-checked against official total | PASS |

---

## 10. Feature Engineering

### 10.1 Feature Builder Scripts

| Script | Purpose | Status |
|---|---|---|
| `build_shala_score_v1.py` | Composite score calculation | PASS |
| `build_enrollment_features.py` | Enrollment from ENR1 + ENR2 | PASS |
| `build_facility_features.py` | Toilets, classrooms, digital devices | PASS |
| `build_teacher_common_features.py` | Teacher counts by gender, type, qualification | PASS |
| `build_numeric_features.py` | Instruction days, hours, grants, inspections | PASS |
| `build_profile1_categorical_features.py` | Management type, medium of instruction | PASS |
| `build_profile2_categorical_features.py` | SMDC, pre-primary, special education | PASS |

### 10.2 Available Indicators Not Displayed in Dashboard

| Category | Columns Available | In Dashboard? |
|---|---|---|
| Teacher gender breakdown | `district_female_teacher_pct`, `district_male_teacher_pct` | No |
| Teacher type breakdown | `district_regular_teacher_pct`, `district_contract_teacher_pct` | No |
| Teacher qualification | `district_graduate_teacher_pct`, `district_postgraduate_teacher_pct` | No |
| Computer-trained teachers | `district_computer_trained_teacher_pct` | No |
| Classroom repair detail | `facility_classrooms_minor_repair_pct`, `facility_classrooms_major_repair_pct` | No |
| Digital device types | `facility_total_desktop_count`, `facility_total_laptop_count`, `facility_total_tablet_count` | No |
| Enrollment by category | `enrollment_reported_sc_enrollment`, `enrollment_reported_st_enrollment`, `enrollment_reported_obc_enrollment` | No |
| Grant data | `grant_receipt_amount_mean_per_school`, `grant_expenditure_amount_mean_per_school` | No |
| Inspection counts | `academic_inspections_count_mean_per_school` | No |

These represent significant untapped analytical depth.

---

## 11. Shala Score Methodology

### 11.1 Normalization

**Method:** Pooled P5-P95 winsorized min-max across all 288 district-year rows.

**Process:**
1. Compute P5 and P95 from all 288 valid values
2. Clip values to [P5, P95]
3. Scale to [0, 100]: `(clipped - P5) / (P95 - P5) * 100`
4. If direction is LOWER_IS_BETTER: `score = 100 - score`
5. NaN values are preserved as NaN (no imputation)

### 11.2 Normalization Parameters

| Indicator | Direction | P5 | P95 | Min | Max | Clipped |
|---|---|---|---|---|---|---|
| Students per teacher | LOWER_IS_BETTER | 20.01 | 35.39 | 16.44 | 38.16 | 15 below, 15 above |
| Functional toilet % | HIGHER_IS_BETTER | 91.90 | 99.43 | 84.32 | 99.78 | 15 below, 15 above |
| Good classroom % | HIGHER_IS_BETTER | 82.92 | 95.81 | 72.52 | 99.58 | 15 below, 15 above |
| Digital devices / school | HIGHER_IS_BETTER | 2.50 | 22.31 | 1.79 | 43.10 | 15 below, 15 above |

### 11.3 Score Range Verification

| Check | Result | Status |
|---|---|---|
| All scores in [0, 100] | Min 13.88, Max 80.15 | PASS |
| 288 complete scores | All 288 non-null | PASS |
| Pillar scores in [0, 100] | Confirmed | PASS |
| Formula consistency (all 288 rows) | Recalculated, max error < 1e-14 | PASS |

### 11.4 Year-Wise Score Summary

| Year | Mean | Median | Min | Max | Teacher | Infra | Digital |
|---|---|---|---|---|---|---|---|
| 2018-19 | 33.80 | 30.62 | 13.88 | 72.05 | 42.07 | 47.15 | 12.18 |
| 2019-20 | 35.82 | 33.52 | 16.00 | 75.22 | 46.49 | 47.39 | 13.58 |
| 2020-21 | 37.18 | 35.06 | 19.21 | 73.64 | 46.52 | 50.92 | 14.10 |
| 2021-22 | 36.04 | 34.35 | 18.70 | 72.15 | 41.30 | 51.43 | 15.37 |
| 2022-23 | 39.88 | 37.14 | 19.85 | 77.17 | 49.89 | 50.69 | 19.05 |
| 2023-24 | 39.86 | 38.09 | 19.94 | 78.20 | 47.64 | 49.96 | 21.98 |
| 2024-25 | 41.33 | 39.08 | 20.50 | 80.15 | 50.40 | 49.63 | 23.97 |
| 2025-26 | 42.85 | 40.69 | 26.43 | 79.89 | 47.98 | 53.83 | 26.73 |

**Trend:** Statewide average rose from 33.8 to 42.9 over 8 years. Digital Readiness is the fastest-growing pillar (12.2 to 26.7).

### 11.5 Ceiling Effect

15 of 288 records exceed the Digital Readiness P95 ceiling (22.31 devices/school). Mumbai II and Mumbai (Suburban) are above the ceiling for all 8 years, scoring a fixed 100 on this pillar. They cannot be distinguished from each other on this dimension.

Status: NEEDS REVIEW — ceiling effect must be documented in the methodology.

### 11.6 Robustness Validation

| Normalization Method | Spearman Correlation vs P5-P95 | Status |
|---|---|---|
| P1-P99 | 0.9743 | PASS |
| P2.5-P97.5 | 0.9895 | PASS |

The score is robust to alternative clipping boundaries.

---

## 12. Teacher Strength Analysis

### 12.1 Formula

```
Teacher Total = Male Teachers + Female Teachers + Transgender Teachers
PTR = Enrollment Total / Teacher Total
Teacher Strength Score = normalize(PTR, LOWER_IS_BETTER)
```

### 12.2 Verification

| Check | Result | Status |
|---|---|---|
| Teacher total derived with `min_count=3` | All 3 columns required, no silent zeros | PASS |
| Reconciliation against official total | Cross-checked, near-zero differences | PASS |
| PTR direction correct | LOWER_IS_BETTER applied after normalization | PASS |
| PTR historical range | 16.44 to 38.16 students per teacher | PASS |
| PTR in forecast | `forecast_enrollment / forecast_teachers` | PASS |

---

## 13. Infrastructure Analysis

### 13.1 Formula

```
Infrastructure Score = (Functional Toilet Score + Good Classroom Score) / 2
```

Both sub-indicators normalized independently with HIGHER_IS_BETTER direction. Equal 50/50 weight. `skipna=False` means both must be present for a pillar score.

### 13.2 Verification

| Indicator | Range | P5 | P95 | Status |
|---|---|---|---|---|
| Functional toilet % | 84.32% - 99.78% | 91.90% | 99.43% | PASS |
| Good classroom % | 72.52% - 99.58% | 82.92% | 95.81% | PASS |
| Zero values outside [0, 100] | Confirmed | — | — | PASS |

### 13.3 Available but Not Displayed

| Column | Description |
|---|---|
| `facility_classrooms_minor_repair_pct` | % classrooms needing minor repair |
| `facility_classrooms_major_repair_pct` | % classrooms needing major repair |
| `facility_classrooms_needing_repair_pct` | Combined repair need |

---

## 14. Digital Readiness Analysis

### 14.1 Formula

```
Digital Readiness Score = normalize(devices_per_reporting_school, HIGHER_IS_BETTER)
```

### 14.2 Verification

| Check | Result | Status |
|---|---|---|
| Devices/school range | 1.79 to 43.10 | PASS |
| P5 = 2.50, P95 = 22.31 | 15 records clipped at each tail | PASS |
| Ceiling effect (Mumbai II) | All 8 years at 100.0 | NEEDS REVIEW |
| Ceiling effect (Mumbai Suburban) | 7 of 8 years at 100.0 | NEEDS REVIEW |
| Forecast for Mumbai II | 45.36 devices (>2x P95, scores 100) | NEEDS REVIEW |

### 14.3 Device Type Breakdown (Available)

| Column | Description |
|---|---|
| `facility_total_desktop_count` | Desktop computers |
| `facility_total_laptop_count` | Laptops |
| `facility_total_tablet_count` | Tablets |
| `facility_total_printer_count` | Printers |
| `facility_total_projector_count` | Projectors |

Not displayed in dashboard. Available for enhancement.

---

## 15. Student Enrollment and PTR

### 15.1 Enrollment

| Check | Result | Status |
|---|---|---|
| Total enrollment column | `enrollment_reported_student_total` | PASS |
| Zero negative values | Confirmed | PASS |
| Enrollment by social category | SC, ST, OBC, general available | PASS |
| Enrollment by gender | Boys, girls, transgender components available | PASS |
| Enrollment by grade | C0 through C12 available | PASS |
| Enrollment by age | Ages 5-23 available | PASS |

### 15.2 Pupil-Teacher Ratio

| Check | Result | Status |
|---|---|---|
| Formula | `enrollment / (male + female + transgender teachers)` | PASS |
| Division-by-zero handling | `.where(teacher_total > 0)` | PASS |
| Direction | LOWER_IS_BETTER — lower PTR = higher score | PASS |
| Normalization | P5=20.01, P95=35.39 | PASS |
| Forecast PTR | `forecast_enrollment / forecast_teachers` | PASS |

---

## 16. Forecasting Methodology

### 16.1 Forecast Model Selection

A complex model is eligible only if it shows **positive MAE skill** against Persistence AND wins **>=4 of 5** validation folds. Otherwise Persistence is selected.

### 16.2 Model Comparison Summary

| Target | Model | MAE | RMSE | R² | Skill vs Persistence | Folds Won | Selected |
|---|---|---|---|---|---|---|---|
| Student Enrollment | Persistence | 15,126 | 26,925 | 0.9960 | 0.0 | 0/5 | Yes |
| Student Enrollment | District Linear Trend | 21,417 | 34,313 | 0.9936 | -0.416 | 1/5 | No |
| Student Enrollment | Ridge | 31,603 | 43,498 | 0.9897 | -1.089 | 1/5 | No |
| Student Enrollment | Random Forest | 37,759 | 74,308 | 0.9698 | -1.496 | 0/5 | No |
| Teacher Count | Persistence | 370.4 | 603.8 | 0.9980 | 0.0 | 0/5 | Yes |
| Teacher Count | District Linear Trend | 478.5 | 861.3 | 0.9959 | -0.292 | 1/5 | No |
| Teacher Count | Ridge | 774.7 | 1337.2 | 0.9901 | -1.092 | 0/5 | No |
| Teacher Count | Random Forest | 1026.3 | 2469.4 | 0.9663 | -1.771 | 0/5 | No |
| Functional Toilet % | Persistence | 0.455 | 0.748 | 0.8626 | 0.0 | 0/5 | Yes |
| Functional Toilet % | Random Forest | 0.520 | 0.780 | 0.8505 | -0.142 | 1/5 | No |
| Functional Toilet % | Ridge | 0.603 | 0.840 | 0.8269 | -0.323 | 1/5 | No |
| Good Classroom % | Persistence | 0.508 | 0.727 | 0.9736 | 0.0 | 0/5 | Yes |
| Good Classroom % | Ridge | 0.746 | 1.058 | 0.9440 | -0.469 | 0/5 | No |
| Good Classroom % | Random Forest | 0.790 | 1.296 | 0.9161 | -0.556 | 0/5 | No |
| **Digital Readiness** | **District Linear Trend** | **0.641** | **1.163** | **0.9726** | **+0.1148** | **4/5** | **Yes** |
| Digital Readiness | Ridge | 0.651 | 1.167 | 0.9725 | +0.1013 | 4/5 | No (higher MAE) |
| Digital Readiness | Persistence | 0.724 | 1.106 | 0.9753 | 0.0 | 0/5 | No |

### 16.3 Digital Readiness Improvement

**Claim:** District Linear Trend improves MAE by 11.48% over Persistence.

**Verification:**

```
Persistence MAE = 0.7239
Linear Trend MAE = 0.6408
Skill = 1 - (0.6408 / 0.7239) = 0.1148
Percentage = 11.48%
```

Status: PASS — independently recalculated and confirmed.

### 16.4 Why Simpler Models Were Retained

Persistence outperforms complex models when year-to-year autocorrelation is high and the dataset is small (36 districts, 7 year-to-year transitions). Ridge and Random Forest overfit with limited training data. The conservative selection rule (positive skill AND >=4/5 folds) prevents selecting a model that looks good on one unusual fold.

---

## 17. Model Validation and Evaluation

### 17.1 Validation Framework

| Check | Result | Status |
|---|---|---|
| Validation type | Expanding-window chronological | PASS |
| Number of folds | 5 (target years 2021-2025) | PASS |
| Districts per fold | 36 (enforced with ValueError) | PASS |
| Training rows fold 1 (2021) | 72 (36 districts x 2 prior years) | PASS |
| Training rows fold 5 (2025) | 216 (36 districts x 6 prior years) | PASS |
| Random split used? | No — strictly chronological | PASS |
| Preprocessing fitted per fold? | Yes — imputation, scaling, encoding inside each fold | PASS |
| District encoding leakage? | No — OneHotEncoder with `handle_unknown="ignore"` fitted on train only | PASS |
| Target-derived features in features? | No — raw indicators only | PASS |
| Normalization leakage in ML? | No — ML uses raw indicators, not normalized scores | PASS |

### 17.2 Out-of-Fold Predictions

| Check | Result | Status |
|---|---|---|
| OOF predictions per task per model | 180 (5 folds x 36 districts) | PASS |
| Total OOF rows | 4,500 (5 tasks x 5 models x 180) | PASS |
| Fold-level MAE, RMSE, R2 computed | All in `baseline_fold_metrics.csv` | PASS |

### 17.3 Robustness Correlations

| Method | Spearman vs P5-P95 | Status |
|---|---|---|
| P1-P99 | 0.9743 | PASS |
| P2.5-P97.5 | 0.9895 | PASS |

---

## 18. What-If Scenario Audit

### 18.1 Workspace Summary

| # | Workspace | Calculation | Status |
|---|---|---|---|
| 1 | Shala Score | `(T + I + D) / 3` from user pillar inputs | PASS |
| 2 | Student Enrollment | `max(0, baseline x (1 + growth%))` | PASS |
| 3 | Teacher Strength | `max(0, baseline_teachers + change)` | PARTIAL |
| 4 | Functional Toilets | `clip(baseline + change_pp, 0, 100)` | PASS |
| 5 | Classroom Quality | `clip(baseline + change_pp, 0, 100)` | PASS |
| 6 | Digital Readiness | `baseline + add_devices` | PASS |

### 18.2 Workspace 3 Issue (PARTIAL)

The Teacher Strength workspace (idx==2) displays a raw teacher count after the user's adjustment. It does not compute the adjusted Pupil-Teacher Ratio or estimate the impact on the Teacher Strength pillar score. The other 5 workspaces return values directly comparable to their forecast baseline. This workspace does not.

**Impact:** A user who adds 500 teachers sees "15,500 teachers" but cannot tell what that means for the district's Shala Score or PTR.

**Recommended fix:** Also compute adjusted PTR = forecast_enrollment / adjusted_teachers, then apply frozen normalization to estimate the pillar score change.

### 18.3 What-If Disclaimer

The dashboard correctly labels all scenario outputs as what-if calculations, not new ML predictions. The disclaimer at the bottom of Tab 4 states: "It does not retrain an ML model or claim a new model prediction." Status: PASS.

---

## 19. Streamlit Dashboard Audit

### 19.1 Module Summary

| Module | Contents | Status |
|---|---|---|
| 01 Overview | KPIs, top/bottom 10, trend, pillar profile, priority matrix | PASS |
| 02 District Explorer | District scores, comparison, history, forecast, heatmap | PASS |
| 03 Education Analytics | 10 indicators, bar charts, trend, correlation scatter | PASS |
| 04 Predictive Intelligence | 6 what-if workspaces, forecast comparison | PASS (Workspace 3 PARTIAL) |
| 05 Data Quality & Methodology | Formulas, coverage heatmap, validation table | PASS |

### 19.2 Code Quality

| Check | Result | Status |
|---|---|---|
| Syntax errors | None | PASS |
| All imports present | `from html import escape` confirmed | PASS |
| File path detection | Robust `ROOT_CANDIDATES` logic | PASS |
| Missing file handling | `missing_file_help()` with informative error | PASS |
| Column validation | Required columns checked with `st.stop()` | PASS |
| `width="stretch"` parameter | Deprecated in newer Streamlit | NEEDS REVIEW |

---

## 20. Charts, Filters and District Analysis

### 20.1 Available Features

| Feature | Status |
|---|---|
| Sidebar district + year filters | PASS |
| Selected district highlighted across all tabs | PASS |
| Top 10 / Bottom 10 bar charts | PASS |
| State average reference line on charts | PASS |
| Priority matrix scatter (score vs YoY change) | PASS |
| District vs state comparison grouped bar | PASS |
| Score history line chart (district + state) | PASS |
| 10-indicator Education Analytics | PASS |
| Relationship scatter with Pearson r | PASS |
| 36-district heatmap (pillars) | PASS |
| Forecast display (score, teachers, band) | PASS |
| Error range P10-P90 context cards | PASS |
| 6 what-if workspaces with charts | PASS |

### 20.2 Not Available (Enhancement Opportunities)

| Feature | Data Available |
|---|---|
| District education profile (raw indicators) | Yes — in master CSV |
| Auto-generated district insights | Yes — computable from data |
| Teacher gender/type/qualification charts | Yes — in master CSV |
| Classroom repair breakdown | Yes — in master CSV |
| Digital device type breakdown | Yes — in master CSV |
| Enrollment by social category | Yes — in master CSV |
| District report generator | Yes — all data in CSVs |
| Marathi language support | Needs translation strings |
| Data science lifecycle visual | All stages verified |

---

## 21. Dependencies and Technical Risks

### 21.1 Requirements

| Package | In requirements.txt | Installed | Status |
|---|---|---|---|
| streamlit | >=1.50 | 1.56.0 | PASS |
| pandas | >=2.0 | 2.3.3 | PASS |
| numpy | >=1.24 | 2.2.6 | PASS |
| plotly | >=5.24 | 7.1.0 | PASS |
| **scikit-learn** | **MISSING** | 1.8.0 (installed) | **FAIL** |

**Critical:** `scikit-learn` is imported by `run_ml_baseline_experiments.py` but is absent from `requirements.txt`. Anyone installing from `requirements.txt` cannot run the ML pipeline.

### 21.2 Technical Issues

| Issue | File | Status |
|---|---|---|
| Dead variable `RISK_THRESHOLD_INPUT` | `build_forecast_2026_27.py` line 47 | NEEDS REVIEW |
| `width="stretch"` deprecated parameter | `dashboard/app.py` (multiple) | NEEDS REVIEW |
| No `__init__.py` in src/ | All src/ subdirectories | NEEDS REVIEW |
| No lockfile / pinned versions | Project root | NEEDS REVIEW |

---

## 22. Documentation and Submission Readiness

| Check | Status |
|---|---|
| Academic project report | MISSING — `reports/final/` is empty |
| README.md | MISSING — not found at project root |
| Methodology documentation | PASS — in reports/ |
| ML experiment methodology | PASS — in reports/ |
| Data audit reports | PASS — in reports/data_audit/ |
| Normalization parameters | PASS — in reports/score_design/ |
| Robustness audit | PASS — in reports/score_design/robustness_audit_v1/ |
| Column mapping docs | PASS — in docs/column_mapping/ |
| requirements.txt | PARTIAL — missing scikit-learn |

---

## 23. Missing Features and Improvement Opportunities

### 23.1 Critical Fixes Required

| # | Fix | File | Effort |
|---|---|---|---|
| 1 | Add `scikit-learn>=1.3` to requirements.txt | `requirements.txt` | 30 sec |
| 2 | Place academic report in `reports/final/` | External | External |
| 3 | Remove dead `RISK_THRESHOLD_INPUT` variable | `build_forecast_2026_27.py` | 1 min |
| 4 | Fix Teacher What-If to show PTR and pillar score impact | `app.py` | 30 min |

### 23.2 Recommended Improvements

| # | Improvement | Priority | Effort |
|---|---|---|---|
| 5 | District Education Profile panel (raw indicators) | High | 1 hour |
| 6 | Auto-generated district insights (5 templates) | High | 1 hour |
| 7 | Model selection table in Methodology tab | Medium | 30 min |
| 8 | Normalization parameter table in Methodology tab | Medium | 30 min |
| 9 | Teacher type/gender breakdown in Analytics tab | Medium | 45 min |
| 10 | Classroom repair breakdown in District Explorer | Medium | 30 min |
| 11 | Replace `width="stretch"` with `use_container_width=True` | Low | 15 min |
| 12 | Add README.md at project root | Medium | 30 min |
| 13 | Document ceiling effect in methodology | Low | 15 min |
| 14 | Document pooled normalization temporal note | Low | 15 min |

### 23.3 Optional Future Enhancements

| # | Enhancement | Effort |
|---|---|---|
| 15 | District Report Generator (structured text report) | 3 hours |
| 16 | Marathi/English language toggle | 4 hours |
| 17 | Data science lifecycle visual diagram | 2 hours |
| 18 | GeoJSON map visualization | 4 hours |

---

## 24. Premium Dashboard Improvement Proposal

### 24.1 District Education Profile

**Purpose:** Show the complete educational condition of a selected district, not just its score rank.

**Proposed indicators (all available in existing data):**

| Indicator | Column | Display |
|---|---|---|
| Total schools | `school_count` | Number + state avg comparison |
| Student enrollment | `enrollment_reported_student_total` | Number + state avg comparison |
| Total teachers | `score_teacher_total_derived` | Number + state avg comparison |
| Pupil-Teacher Ratio | `ptr_students_per_teacher_raw` | Number (lower = better) + state avg |
| Functional toilet % | `functional_toilet_pct_raw` | Percentage + state avg |
| Good classroom % | `good_classroom_pct_raw` | Percentage + state avg |
| Digital devices/school | `digital_devices_per_school_raw` | Number + state avg |

**Location:** Below existing pillar score cards in District Explorer tab.

### 24.2 Evidence-Based District Insights

**Purpose:** Auto-generate plain-language findings from the data.

**Templates (all computable from existing data):**

| Insight | Condition | Example |
|---|---|---|
| Teacher availability | District PTR > state PTR | "Teacher availability is weaker than the state average." |
| Toilet coverage | District toilet % < state avg | "Functional toilet coverage needs attention." |
| Digital access | District devices < state avg | "Digital device availability is below the state average." |
| Enrollment trend | Current < previous year | "Student enrollment has declined vs the previous year." |
| Classroom condition | District classroom % < state avg | "Good-condition classroom share is below the state average." |

**Constraint:** Enrollment decline must NOT be labeled as "dropout." The data shows reported enrollment, not dropout.

### 24.3 District Report Generator

**Purpose:** Structured report for a selected district and year.

**Inputs:** District, academic year, language (English/Marathi).

**Report structure:**
1. District name and year header
2. Key indicators table
3. Shala Score and pillar scores with state comparison
4. Strengths (indicators above state average)
5. Areas needing attention (indicators below state average)
6. Trend summary (score change vs previous year)
7. Forecast summary (2026-27 values)
8. Disclaimer

### 24.4 Marathi and English Support

**Scope:** Dashboard labels, insight text, district report content.

**Not in scope (V1):** Plotly chart labels in Marathi (font rendering issues), data column names (stay in English).

### 24.5 Data Science Lifecycle

| Stage | Script/Output | Status |
|---|---|---|
| Data Collection | 49 ZIPs in `data/raw/udise_zip/` | VERIFIED |
| Data Understanding | `audit_extracted_csvs.py` + `reports/data_audit/` | VERIFIED |
| Data Cleaning | Embedded in `build_school_year_master.py` | VERIFIED |
| EDA | 26 scripts in `src/validation/` | VERIFIED |
| Feature Engineering | 7 scripts in `src/features/` | VERIFIED |
| Model Development | `run_ml_baseline_experiments.py` | VERIFIED |
| Model Validation | 5-fold expanding window, fold metrics CSV | VERIFIED |
| Prediction | `build_forecast_2026_27.py` | VERIFIED |
| Dashboard Insights | `dashboard/app.py` | VERIFIED |

---

## 25. Prioritized Implementation Roadmap

### Tier 1 — Immediate (Before Demonstration)

| # | Task | Effort | Outcome |
|---|---|---|---|
| 1 | Add `scikit-learn>=1.3` to requirements.txt | 30 sec | ML pipeline reproducible |
| 2 | Remove dead `RISK_THRESHOLD_INPUT` variable | 1 min | Clean code |
| 3 | Fix Teacher What-If workspace (PTR + pillar score) | 30 min | Consistent workspaces |
| 4 | Add District Education Profile panel | 1 hour | Richer district view |
| 5 | Add auto-generated district insights | 1 hour | Evidence-based findings |

### Tier 2 — Important (Before Final Submission)

| # | Task | Effort | Outcome |
|---|---|---|---|
| 6 | Add model selection + normalization tables to Methodology | 45 min | Transparent methodology |
| 7 | Add teacher type/gender breakdown to Analytics | 45 min | Deeper analysis |
| 8 | Add classroom repair breakdown to District Explorer | 30 min | Infrastructure detail |
| 9 | Replace `width="stretch"` with `use_container_width=True` | 15 min | Future-proof API |
| 10 | Add README.md | 30 min | Project documentation |
| 11 | Place academic report in `reports/final/` | External | Submission complete |
| 12 | Document ceiling effect + pooled normalization | 30 min | Methodological clarity |

### Tier 3 — Optional Future Enhancements

| # | Task | Effort | Outcome |
|---|---|---|---|
| 13 | District Report Generator | 3 hours | Structured reports |
| 14 | Marathi/English language toggle | 4 hours | Bilingual support |
| 15 | Data science lifecycle visual | 2 hours | Process documentation |
| 16 | GeoJSON map visualization | 4 hours | Geographic view |

---

## 26. Final Project Readiness Assessment

| Criterion | Status |
|---|---|
| Data pipeline complete and verified | READY |
| Shala Score formula correct | READY |
| ML validation sound, no leakage | READY |
| Forecasts generated for all 36 districts | READY |
| Dashboard functional with 5 tabs + 6 workspaces | READY |
| requirements.txt complete | FIX NEEDED |
| Academic report present | MISSING |
| Teacher What-If workspace consistent | FIX NEEDED |
| Dead code removed | FIX NEEDED |
| README present | MISSING |

### Final Verdict

**READY AFTER MINOR CORRECTIONS**

The project is methodologically sound and functionally complete. The 4 critical fixes (Tier 1 items 1-4) can be completed in under 2 hours. None require retraining models, changing formulas, or regenerating data.

---

## Appendix A: Verified Claims

| Claim | Expected | Actual | Status |
|---|---|---|---|
| 36 districts | 36 | 36 | VERIFIED |
| 288 district-year records | 288 | 288 | VERIFIED |
| Zero duplicate keys | 0 | 0 | VERIFIED |
| 288 complete Shala Scores | 288 | 288 | VERIFIED |
| Scores in [0, 100] | Yes | Min 13.88, Max 80.15 | VERIFIED |
| P1-P99 correlation 0.9743 | 0.9743 | 0.9742921 | VERIFIED |
| P2.5-P97.5 correlation 0.9895 | 0.9895 | 0.9895109 | VERIFIED |
| 180 OOF predictions per target | 180 | 180 | VERIFIED |
| Digital Readiness MAE improvement 11.48% | 11.48% | 11.4833% | VERIFIED |
| 5 temporal folds | 5 | 5 | VERIFIED |
| 49 ZIP archives | 49 | 49 | VERIFIED |
| scikit-learn in requirements | Present | ABSENT | FAILED |
| Academic report present | Present | MISSING | FAILED |

---

*End of Audit Report*

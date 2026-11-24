# ShalaScope Maharashtra -- Data Log

**Generated:** 2026-11-23  
**Dataset:** `data/processed/district_year/maharashtra_district_year_shala_score_v1.csv`  
**Rows:** 288 (36 districts x 8 academic years)  

---

## 1. Year Scope

| Scope | Years | Rows | Purpose |
|-------|-------|------|---------|
| Full dataset | 2018-19 to 2025-26 | 288 | Complete UDISE+ extract |
| Spec primary window | 2019-20 to 2024-25 | 216 | Core modelling and reporting window |
| Edge years (documented) | 2018-19 and 2025-26 | 72 | Trend context; 2025-26 is provisional |

> **Modelling split:** Train = 2018-19 to 2023-24 (216 rows), Test = 2024-25 (36 rows).
> Forecast horizon = 2025-26 and 2026-27 (never in train or test).
> 2018-19 is the first available year and anchors trend models.
> 2025-26 is included for context; treat values as provisional until officially confirmed.

---

## 2. District Coverage

All **36 districts** present, using current official names:

- AHILYANAGAR
- AKOLA
- AMRAVATI
- BEED
- BHANDARA
- BULDANA
- CHANDRAPUR
- CHHATRAPATI SAMBHAJINAGAR
- DHARASHIV
- DHULE
- GADCHIROLI
- GONDIA
- HINGOLI
- JALGAON
- JALNA
- KOLHAPUR
- LATUR
- MUMBAI (SUBURBAN)
- MUMBAI II
- NAGPUR
- NANDED
- NANDURBAR
- NASHIK
- PALGHAR
- PARBHANI
- PUNE
- RAIGAD
- RATNAGIRI
- SANGLI
- SATARA
- SINDHUDURG
- SOLAPUR
- THANE
- WARDHA
- WASHIM
- YAVATMAL

---

## 3. Region Mapping

| Region | Districts |
|--------|-----------|
| Konkan | MUMBAI II, MUMBAI (SUBURBAN), THANE, PALGHAR, RAIGAD, RATNAGIRI, SINDHUDURG |
| Western Maharashtra | PUNE, SATARA, SANGLI, KOLHAPUR, SOLAPUR, NASHIK, DHULE, NANDURBAR, JALGAON, AHILYANAGAR |
| Marathwada | CHHATRAPATI SAMBHAJINAGAR, JALNA, BEED, LATUR, DHARASHIV, NANDED, HINGOLI, PARBHANI |
| Vidarbha | NAGPUR, WARDHA, YAVATMAL, CHANDRAPUR, GADCHIROLI, BHANDARA, GONDIA, AMRAVATI, AKOLA, WASHIM, BULDANA |

---

## 4. Available Indicators

| Category | Indicator | Column | Null % | Range |
|----------|-----------|--------|--------|-------|
| Teacher / PTR | Total teachers derived (M+F+T) | `score_teacher_total_derived` | 0.0% | 5497.00 - 78894.00 |
| Teacher / PTR | Pupil-Teacher Ratio | `ptr_students_per_teacher_raw` | 0.0% | 16.44 - 38.16 |
| Teacher / PTR | Female teacher share % | `district_female_teacher_pct` | 50.0% | 22.87 - 77.28 |
| Infrastructure | Functional toilet % | `facility_functional_toilet_pct` | 0.0% | 84.32 - 99.78 |
| Infrastructure | Good-condition classroom % | `facility_classrooms_good_condition_pct` | 0.0% | 72.52 - 99.58 |
| Infrastructure | Pucca building block % | `facility_pucca_building_block_pct` | 12.5% | 50.67 - 95.74 |
| Participation / GPI | Boys enrolment | `enrollment_reported_enrollment_b_component_total` | 0.0% | 48961.00 - 1203651.00 |
| Participation / GPI | Girls enrolment | `enrollment_reported_enrollment_g_component_total` | 0.0% | 46363.00 - 1091086.00 |
| Participation / GPI | SC enrolment | `enrollment_reported_sc_enrollment` | 0.0% | 6919.00 - 350424.00 |
| Participation / GPI | ST enrolment | `enrollment_reported_st_enrollment` | 0.0% | 1116.00 - 407176.00 |
| Participation / GPI | OBC enrolment | `enrollment_reported_obc_enrollment` | 0.0% | 36791.00 - 601939.00 |
| Digital Readiness | Avg digital devices / school | `facility_avg_digital_devices_per_reporting_school` | 0.0% | 1.79 - 43.10 |
| Digital Readiness | Computer-trained teacher % | `district_computer_trained_teacher_pct` | 50.0% | 31.42 - 79.46 |
| Shala Score v1 | Shala Score v1 (3-pillar baseline) | `shala_score_v1` | 0.0% | 13.88 - 80.15 |

---

## 5. Missing Indicators (MISSING_IN_SOURCE)

> These columns are **absent from the UDISE+ extract** used by this project.
> They are **never fabricated, imputed, or synthesised**.
> Pillar weights are redistributed proportionally when a full pillar is unavailable.

| Category | Indicator | Notes |
|----------|-----------|-------|
| Infrastructure | Electricity % | MISSING_IN_SOURCE -- not collected in this UDISE+ release |
| Infrastructure | Drinking water % | MISSING_IN_SOURCE |
| Infrastructure | Library % | MISSING_IN_SOURCE |
| Infrastructure | Ramp / barrier-free % | MISSING_IN_SOURCE |
| Participation / GPI | GPI (girls/boys ratio) | Computed; range 0.80-0.98 |
| Digital Readiness | Internet connectivity % | MISSING_IN_SOURCE |
| Learning Outcomes | Learning outcome score | MISSING_IN_SOURCE -- no NAS/ASER/learning data |
| Learning Outcomes | Gross Enrolment Ratio (GER) | MISSING_IN_SOURCE |
| Learning Outcomes | Dropout rate | MISSING_IN_SOURCE |
| Shala Score v2 | Shala Score v2 (4-pillar + redistribution) | New; range 24.90-72.16 |
| Risk Classification | Risk tier v2 (Thriving/Stable/At-Risk/Critical) | Quartile-based; 72 districts per tier |
| Geography | Region (Konkan / Western Mah. / Marathwada / Vidarbha) | 0 unmapped |

---

## 6. Shala Score v2 -- Weight Design

| Pillar | Nominal Weight | Actual Weight (this dataset) | Status |
|--------|---------------|------------------------------|--------|
| Teacher / PTR | 25% | **29.4%** (redistributed) | AVAILABLE |
| Infrastructure | 25% | **29.4%** (redistributed) | AVAILABLE |
| Participation / GPI | 20% | **23.5%** (redistributed) | AVAILABLE |
| Digital Readiness | 15% | **17.6%** (redistributed) | AVAILABLE |
| Learning Outcomes | 15% | **0%** | MISSING_IN_SOURCE |

> Redistribution formula: `eff_weight_i = nominal_i / sum(nominal_j for available j)`

---

## 7. No Double-Counting Guarantee

- `facility_classrooms_good_condition_pct` appears in **Infrastructure pillar only**.
- It is **not** used in Learning Outcomes to avoid double-counting.
- Learning Outcomes weight is redistributed to the four available pillars.

---

## 8. District Alias Standardisation

| Old Name | Current Official Name |
|----------|-----------------------|
| Aurangabad | Chhatrapati Sambhajinagar |
| Osmanabad | Dharashiv |
| Ahmednagar / Ahmadnagar | Ahilyanagar |
| Gondiya | Gondia |
| Bid | Beed |

All 36 districts in the dataset already use the current official names.

---

## 9. Files Created / Modified

| File | Purpose |
|------|---------|
| `src/core/regions.py` | Region map, GPI, marginalised enrolment % |
| `src/features/build_shala_score_v2.py` | Shala Score v2 pipeline |
| `data/processed/district_year/maharashtra_district_year_shala_score_v2.csv` | Scored dataset (288 x 688) |
| `reports/score_design/shala_score_v2_*.csv` | Normalization params, weights, PCA, ranking |
| `docs/data_log.md` | This file |
| `docs/data_log.xlsx` | Machine-readable version |

**Raw source files (`data/raw/`, `data/extracted/`) are never modified.**
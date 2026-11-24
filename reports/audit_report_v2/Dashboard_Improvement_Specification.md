# ShalaScope Maharashtra
## Premium Dashboard Improvement Specification

**Document Type:** Design Proposal  
**Status:** For Approval — No Code Changes Made  

---

## 1. Design Philosophy

**Approach:** Minimal premium editorial dashboard. Calm, clean, professional.

**Colour System (existing, retained):**

| Colour | Hex | Usage |
|---|---|---|
| Deep plum | #6F3853 | Primary brand, cards, buttons |
| Deep wine | #4A1525 | Headings, active states |
| Antique brass | #B8895B | Highlights, selected district |
| Muted teal | #4E8178 | Positive indicators, Teacher Strength |
| Sage green | #5D8A70 | PASS, strong performance |
| Slate blue | #6A8EA3 | Information, Digital Readiness |
| Soft violet | #7D7191 | Neutral information |
| Muted coral | #BC6C70 | Attention areas, FAIL |
| Warm amber | #C08A4B | Warnings, PARTIAL |
| Warm off-white | #F7F4F1 | Page background |
| Neutral grey | #786D73 | Secondary text |

**Design principles:**
- One idea per card
- Consistent card dimensions
- Thin borders, subtle shadows
- Whitespace between sections
- No excessive gradients or decorations

---

## 2. Proposed Improvements

### 2.1 District Education Profile (New Panel in District Explorer)

**Purpose:** Show the complete educational condition of a selected district with raw indicators, not just score ranks.

**Location:** Below existing pillar score cards in District Explorer tab.

**Layout:** 2 rows of 4 metric cards.

**Row 1 — Scale indicators:**

| Card | Data Column | Format | Comparison |
|---|---|---|---|
| Total schools | `school_count` | Integer | vs state average |
| Student enrollment | `enrollment_reported_student_total` | Integer | vs state average |
| Total teachers | `score_teacher_total_derived` | Integer | vs state average |
| Pupil-Teacher Ratio | `ptr_students_per_teacher_raw` | 1 decimal | vs state average (lower = better) |

**Row 2 — Quality indicators:**

| Card | Data Column | Format | Comparison |
|---|---|---|---|
| Shala Score | `shala_score_v1` | 2 decimals | vs state average |
| Functional toilet % | `functional_toilet_pct_raw` | 1 decimal | vs state average |
| Good classroom % | `good_classroom_pct_raw` | 1 decimal | vs state average |
| Digital devices/school | `digital_devices_per_school_raw` | 2 decimals | vs state average |

**Each card shows:**
- Label (uppercase, small)
- Value (large, accent colour)
- State average comparison caption
- Delta badge (green if above average, coral if below)

**All data already exists in the historical master CSV.** No new data collection needed.

---

### 2.2 Evidence-Based District Insights (New in District Explorer)

**Purpose:** Auto-generate plain-language findings from the data.

**Location:** Below the District Education Profile panel.

**Layout:** Vertical stack of insight cards (same style as existing `insight_card` component).

**Insight templates:**

| # | Condition | Text Template |
|---|---|---|
| 1 | District PTR > state PTR | "Teacher availability is relatively weaker than the state average ({district_ptr:.1f} vs {state_ptr:.1f} students per teacher)." |
| 2 | District toilet % < state avg | "Functional toilet coverage needs attention ({district:.1f}% vs state {state:.1f}%)." |
| 3 | District devices < state avg | "Digital device availability is below the state average ({district:.1f} vs {state:.1f} devices per reporting school)." |
| 4 | Current enrollment < previous year | "Student enrollment has declined compared with the previous year ({delta:+,} students)." |
| 5 | District classroom % < state avg | "Good-condition classroom share is below the state average ({district:.1f}% vs state {state:.1f}%)." |

**Critical constraint:** Enrollment decline must NOT be labeled as "dropout." The data shows reported enrollment, not dropout rates.

**All computations use existing data in the historical CSV.** No model retraining needed.

---

### 2.3 Maharashtra Average Comparison (Enhancement to existing comparison)

**Current state:** District Explorer shows a grouped bar chart comparing district vs state on 3 pillar scores.

**Proposed enhancement:** Add a second comparison chart showing all 7 raw indicators (schools, enrollment, teachers, PTR, toilet %, classroom %, devices) side by side with the state average.

**Layout:** Horizontal grouped bar chart, same style as existing pillar comparison.

---

### 2.4 Historical Trends (Enhancement to existing history chart)

**Current state:** Score history line chart shows Shala Score over 8 years.

**Proposed enhancement:** Add a toggle to switch between:
- Shala Score trend (existing)
- Individual pillar trends (Teacher, Infrastructure, Digital)
- Individual raw indicator trends (PTR, toilet %, classroom %, devices/school)

**Implementation:** `st.radio("Show", ["Shala Score", "Pillars", "Raw indicators"])` above the chart.

---

### 2.5 Teacher, Infrastructure and Digital Indicators (New in Education Analytics)

**Current state:** Education Analytics offers 10 indicators.

**Proposed additions:**

| Indicator | Column | Direction | Meaning |
|---|---|---|---|
| Female teachers (%) | `district_female_teacher_pct` | Higher = more gender diversity | Share of female teachers |
| Regular teachers (%) | `district_regular_teacher_pct` | Higher = more stable workforce | Permanent vs contract |
| Contract teachers (%) | `district_contract_teacher_pct` | Lower = more stable | Contract share |
| Computer-trained (%) | `district_computer_trained_teacher_pct` | Higher = better tech readiness | Teachers with computer training |
| Classrooms needing repair (%) | `facility_classrooms_needing_repair_pct` | Lower = better | Minor + major repair combined |

**All columns exist in the historical master CSV.** No new data needed.

---

### 2.6 District Report Generator (New Module)

**Purpose:** Structured text report for a selected district and year.

**Location:** New section at the bottom of District Explorer, or a new tab "06 District Report."

**Inputs:**
- District (from sidebar or local selector)
- Academic year (from sidebar)
- Language: English or Marathi (radio toggle)

**Report structure:**

```
SHALASCOPE DISTRICT EDUCATION REPORT
{District Name} — {Academic Year}

1. KEY INDICATORS
   Schools:          X (state avg: Y)
   Enrollment:       X (state avg: Y)
   Teachers:         X (state avg: Y)
   PTR:              X (state avg: Y)
   Toilet %:          X% (state avg: Y%)
   Classroom %:       X% (state avg: Y%)
   Devices/school:   X (state avg: Y)

2. SHALA SCORE
   Overall:          X.XX (state avg: Y.YY)
   Teacher Strength:  X.XX
   Infrastructure:    X.XX
   Digital Readiness: X.XX

3. STRENGTHS
   [Indicators above state average]

4. AREAS NEEDING ATTENTION
   [Indicators below state average]

5. TREND
   Score change vs previous year: +/- X.XX points

6. 2026-27 FORECAST
   Forecast score: X.XX
   Forecast enrollment: X
   Forecast teachers: X
   Performance band: [LOW/MODERATE/HIGH/CRITICAL]

7. DISCLAIMER
   This is an experimental estimate, not an official government assessment.
```

**All data for this report already exists in the historical and forecast CSVs.**

---

### 2.7 English and Marathi Support

**Approach:** Language toggle in sidebar.

```python
lang = st.sidebar.radio("Language / भाषा", ["English", "मराठी"])
```

**Translation scope:**

| Element | English | Marathi |
|---|---|---|
| Dashboard title | ShalaScope Maharashtra | शालास्कोप महाराष्ट्र |
| Teacher Strength | Teacher Strength | शिक्षक सामर्थ्य |
| Infrastructure | Infrastructure | पायाभूत सुविधा |
| Digital Readiness | Digital Readiness | डिजिटल सज्जता |
| Shala Score | Shala Score | शाळा गुण |
| Functional toilets | Functional Toilets | वापरता येण्याजोगी शौचालय |
| Good classrooms | Good Classrooms | चांगल्या स्थितीत वर्गखोली |
| Digital devices | Digital Devices | डिजिटल साधने |
| Students per teacher | Students per Teacher | प्रति शिक्षक विद्यार्थी |
| State average | State Average | राज्य सरासरी |
| Forecast | Forecast | अंदाज |
| What-if scenario | What-if Scenario | कल्पना परिदृश्य |

**Not in scope (V1):** Plotly chart axis labels in Marathi (font rendering complexity).

---

### 2.8 Data Science Lifecycle Section (New in Methodology Tab)

**Purpose:** Present the project's Data Science Lifecycle with actual evidence.

**Layout:** Horizontal step cards (using existing `step` CSS class).

```
[1] Data Collection → [2] Data Understanding → [3] Data Cleaning →
[4] EDA → [5] Feature Engineering → [6] Model Development →
[7] Model Validation → [8] Prediction → [9] Dashboard Insights
```

**Each step shows:**

| Step | Script/Output | Status |
|---|---|---|
| Data Collection | 49 ZIPs in `data/raw/udise_zip/` | VERIFIED |
| Data Understanding | `audit_extracted_csvs.py` + audit reports | VERIFIED |
| Data Cleaning | Embedded in `build_school_year_master.py` | VERIFIED |
| EDA | 26 scripts in `src/validation/` | VERIFIED |
| Feature Engineering | 7 scripts in `src/features/` | VERIFIED |
| Model Development | `run_ml_baseline_experiments.py` | VERIFIED |
| Model Validation | 5-fold expanding window, fold metrics CSV | VERIFIED |
| Prediction | `build_forecast_2026_27.py` | VERIFIED |
| Dashboard Insights | `dashboard/app.py` | VERIFIED |

---

## 3. Visual Hierarchy

```
HERO BANNER (existing, retained)
    ↓
SIDEBAR: Year + District + Language toggle
    ↓
TAB 01 — OVERVIEW (existing + enhancements)
    KPI cards → Insights → Top/Bottom 10 → Trend → Pillar Profile → Priority Matrix
    ↓
TAB 02 — DISTRICT EXPLORER (existing + major enhancement)
    Pillar Scores → [NEW] Education Profile → [NEW] District Insights →
    vs State Chart → History (with toggle) → Forecast → Comparison → Heatmap
    ↓
TAB 03 — EDUCATION ANALYTICS (existing + new indicators)
    15 indicators (existing 10 + 5 new) → Bar chart → Trend → Correlation
    ↓
TAB 04 — PREDICTIVE INTELLIGENCE (existing + Teacher fix)
    6 workspaces (Workspace 3 fixed to show PTR + pillar score)
    ↓
TAB 05 — DATA QUALITY & METHODOLOGY (existing + lifecycle)
    Formulas → [NEW] Model Selection Table → [NEW] Normalization Table →
    [NEW] Data Science Lifecycle → Coverage → Limitations
```

---

## 4. UI Refinements (Minor)

| Element | Current | Proposed |
|---|---|---|
| Metric card height | min-height: 119px | min-height: 100px (tighter) |
| Chart shadows | box-shadow on every chart | Remove shadow, keep border only |
| Hero banner | Decorative circle `:before` | Remove decorative circle |
| Priority matrix | 4 colors | 3 colors (simplify) |
| Data tables | Default st.dataframe | Add `column_config` progress bars for scores |
| Insight cards | Left-border accent only | Add subtle background tint |

---

## 5. Implementation Approach

**Rule:** No existing functionality will be removed. All enhancements are additive.

**Data:** All proposed indicators already exist in the 659-column master CSV. No new data collection, no model retraining, no formula changes.

**Code:** All enhancements are in `dashboard/app.py` only. No changes to `src/` scripts, CSV files, or model outputs.

**Risk:** Low. The existing 5-tab structure is preserved. New content is added within existing tabs or as new sections within tabs.

---

## 6. Proposed Changes Summary

| Change | Type | Data Available | Effort |
|---|---|---|---|
| District Education Profile panel | New panel | Yes | 1 hour |
| Auto-generated district insights | New panel | Yes | 1 hour |
| Enhanced comparison chart (7 indicators) | Enhancement | Yes | 45 min |
| Historical trend toggle | Enhancement | Yes | 30 min |
| 5 new Education Analytics indicators | Enhancement | Yes | 45 min |
| Teacher What-If workspace fix | Bug fix | Yes | 30 min |
| District Report Generator | New module | Yes | 3 hours |
| Marathi/English toggle | New feature | Needs strings | 4 hours |
| Data Science Lifecycle visual | New section | Yes | 2 hours |
| Model selection table | New table | Yes (CSV exists) | 30 min |
| Normalization parameter table | New table | Yes (CSV exists) | 30 min |
| UI refinements | Minor CSS | N/A | 30 min |

**Total estimated effort:** ~14 hours for all improvements. Tier 1 items only: ~3 hours.

---

*This specification is for approval. No code changes will be made until approved.*

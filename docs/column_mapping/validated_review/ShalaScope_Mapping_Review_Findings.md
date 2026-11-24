# ShalaScope Maharashtra – Mapping Review Findings

## Reviewed inputs
- `ShalaScope_Final_Mapping_Review_Pack.zip` (10 files)
- `DSP_Schema.pdf` (15 pages)
- 404 source-column/category mappings across 2018-19 to 2025-26.

## Key conclusion
The uploaded DSP schema supports many legacy field definitions, but it is not a complete codebook for the 2022-23 to 2025-26 redesigned extracts. The mapping draft is therefore not a final merge specification. Use the evidence review CSV and keep unresolved fields raw.

## Confirmed from the supplied DSP schema
- School Profile 1: school ID, state, district, rural/urban, assembly/parliamentary constituency, city/municipality/gram panchayat, school category/type, lowest/highest class, management, pincode, establishment/recognition years, medium, instructional days/hours, Anganwadi and CCE fields. (PDF pp. 1-3)
- School Profile 2: RTE enrolment fields, school inspections/visits, SMC/SMDC fields, free textbook/transport/uniform indicators and grants. (PDF pp. 4-8)
- Facility: building status, classrooms, toilet-seat counts, water/electricity/library/playground/ramp/handwashing and ICT/device fields. (PDF pp. 9-11)
- Teacher Profile: total and gender counts, employment type, academic/professional qualifications and teaching-level counts. (PDF pp. 12-14)
- Enrolment: Pre-primary and class 1-12 boys/girls fields. (PDF p. 15)

## Explicit code legends present in the PDF
- `rural_urban`: 1 Rural; 2 Urban.
- `school_type`: 1 Boys; 2 Girls; 3 Co-educational.
- `school_category`: 1,2,3,4,5,6,7,8,10,11 with labels in codebook CSV.
- `managment`: values 1,2,3,4,5,6,8,90-98 with labels in codebook CSV.
- `building_status`: 1,2,3,4,5,7,10 with labels in codebook CSV.
- PDF note: code 9 means Not Applicable where the coded field uses that note. Do not convert every numeric 9 in count fields to missing.

## Important cautions
1. `psuedocode` / `pseudocode` is the school pseudo-code key. Normalize the spelling to `school_id`, preserve original value and compare IDs across files within each year.
2. The PDF's Enrolment schema lists `item_desc` and class-wise boys/girls columns. The newer extracts contain `item_group` and `item_id`, which are not defined by this PDF. Inspect distinct values and obtain the matching newer schema before aggregation.
3. The two enrolment archives must not be added together blindly. Determine row/category grain first.
4. 2025-26 `*_t` total enrolment columns should be compared with boys + girls. Preserve source totals and validation flags.
5. Facility toilet columns are seat counts, not the percent of schools with toilets. Calculate school availability indicators from the right denominator only after checking value semantics.
6. The legacy schema describes `internet` as a number of internet (source wording). Do not interpret it as a percentage or binary availability indicator without a newer codebook.
7. Facility indicator code legends for drinking water, electricity, library, playground, ramps and similar yes/no fields are not fully supplied in this PDF. Keep raw codes; do not assume 1=yes, 2=no.
8. Safety fields are only in the 2025-26 extract and are not defined in the provided 15-page DSP schema. Keep as a separate extension until a 2025-26 Safety schema is obtained.
9. Latest-year fields such as ECCE, balvatika, laboratory condition, taps/wells, boarding, cyber-safety and new profile indicators need a matching current codebook.
10. The CSV audit PASS means files were readable and structurally consistent (header/row width); it does not prove data correctness, completeness, code validity or semantic equivalence.

## Recommended next data-engineering sequence
1. Preserve all raw ZIP and extracted CSVs unchanged.
2. Generate value-frequency profiles (distinct values, min/max, nulls) for every coded field and for `item_desc`, `item_group`, `item_id`.
3. Verify per-year school IDs and duplicate keys across Profile-1, Profile-2, Facility and Teacher.
4. Aggregate Enrolment separately by its documented row dimensions; validate 2025-26 totals.
5. Produce one clean school-year table per year; do not concatenate incompatible columns yet.
6. Aggregate school-year records to district-year (36 × six main years target = 216 rows) after checking district coverage and scope.
7. Treat 2018-19 as baseline and 2025-26 as extension, outside the main six-year modelling window unless the project scope is formally revised.

## What is not yet final
- 99 originally `REVIEW_REQUIRED` and 28 `Review meaning` fields need a current schema/value review. Some legacy fields can be clarified by the uploaded PDF; this is reflected in `ShalaScope_Mapping_Evidence_Review.csv`.
- Full 2022-23 onward codebook.
- Final School ID joins and all-year row-level cross-validation (the pack contains inventory and audit summaries, not the raw row values).
- Final Shala Score weights and prediction feasibility.

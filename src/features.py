# -*- coding: utf-8 -*-
"""
src/features.py
================
Core feature column constants for ShalaScope Maharashtra.

The five blueprint pillars are computed by build_shala_score_v2.py and
stored in the v2 CSV. This module exposes the confirmed-present column
names so other modules (prescriptive.py, dashboard) can import them from
a single authoritative source instead of repeating string literals.

Confirmed PRESENT in v2 CSV (688 columns):
  ptr_students_per_teacher_raw, shala_score_v1, shala_score_v2,
  risk_tier_v2, functional_toilet_pct_raw, good_classroom_pct_raw,
  digital_devices_per_school_raw, pillar_teacher_strength,
  pillar_infrastructure, pillar_digital_readiness,
  pillar2_teacher_ptr, pillar2_infrastructure, pillar2_participation,
  pillar2_digital, enrollment_reported_student_total,
  enrollment_reported_enrollment_b/g_component_total,
  score_teacher_total_derived, school_count, academic_year, district.

Confirmed MISSING_IN_SOURCE (never in UDISE+ extract):
  MPI, Literacy, Urban_Pct, girls_toilet_pct, drinking_water_pct,
  electricity_pct, digital_classroom_pct.
"""

# ---------------------------------------------------------------------------
# Core column name constants
# ---------------------------------------------------------------------------

# Identity
COL_DISTRICT  = "district"
COL_YEAR      = "academic_year"
COL_REGION    = "region"

# Score outputs
COL_SCORE_V1  = "shala_score_v1"
COL_SCORE_V2  = "shala_score_v2"
COL_TIER      = "risk_tier_v2"

# Five core blueprint pillars (all confirmed present, 0 null)
COL_PTR       = "ptr_students_per_teacher_raw"          # Pupil-Teacher Ratio
COL_TOILET    = "functional_toilet_pct_raw"             # Infrastructure Index (toilet %)
COL_CLASSROOM = "good_classroom_pct_raw"                # Infrastructure Index (classroom %)
COL_DIGITAL   = "digital_devices_per_school_raw"        # Digital Readiness

# Pillar scores (v1 and v2)
COL_P_TEACH   = "pillar_teacher_strength"
COL_P_INFRA   = "pillar_infrastructure"
COL_P_DIG     = "pillar_digital_readiness"
COL_P2_PTR    = "pillar2_teacher_ptr"
COL_P2_INFRA  = "pillar2_infrastructure"
COL_P2_PART   = "pillar2_participation"
COL_P2_DIG    = "pillar2_digital"

# Enrolment (Gender Parity Index source)
COL_ENROL_B   = "enrollment_reported_enrollment_b_component_total"
COL_ENROL_G   = "enrollment_reported_enrollment_g_component_total"
COL_ENROL_TOT = "enrollment_reported_student_total"

# Teacher / school counts
COL_TEACHERS  = "score_teacher_total_derived"
COL_SCHOOLS   = "school_count"

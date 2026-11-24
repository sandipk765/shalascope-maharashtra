
from pathlib import Path
import pandas as pd
import re

# ============================================================
# SHALASCOPE MAHARASHTRA
# ENROLLMENT ITEM CODEBOOK CROSSWALK
#
# Creates a documented mapping for observed Enrollment codes.
# Does not modify any raw or processed source files.
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT
    / "reports"
    / "data_audit"
    / "enrollment_item_inventory.csv"
)

OUTPUT_DIR = ROOT / "reports" / "data_audit"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 1. DOCUMENTED ITEM MAPPINGS
# ------------------------------------------------------------

ENR1_MAPPING = {

    # Social category
    ("1", "1"): (
        "SOCIAL_CATEGORY",
        "General",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("1", "2"): (
        "SOCIAL_CATEGORY",
        "SC",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("1", "3"): (
        "SOCIAL_CATEGORY",
        "ST",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("1", "4"): (
        "SOCIAL_CATEGORY",
        "OBC",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    # Minority group
    ("2", "5"): (
        "MINORITY_GROUP",
        "Muslim",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("2", "6"): (
        "MINORITY_GROUP",
        "Christian",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("2", "7"): (
        "MINORITY_GROUP",
        "Sikh",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("2", "8"): (
        "MINORITY_GROUP",
        "Buddhist",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("2", "9"): (
        "MINORITY_GROUP",
        "Parsi",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("2", "10"): (
        "MINORITY_GROUP",
        "Jain",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    # BPL
    ("3", "13"): (
        "BENEFICIARY_CATEGORY",
        "BPL",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    # CWSN disability types
    ("4", "1"): (
        "CWSN_DISABILITY",
        "Blindness",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "2"): (
        "CWSN_DISABILITY",
        "Low Vision",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "3"): (
        "CWSN_DISABILITY",
        "Hearing Impairment",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "4"): (
        "CWSN_DISABILITY",
        "Speech and Language Disability",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "5"): (
        "CWSN_DISABILITY",
        "Locomotor Disability",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "6"): (
        "CWSN_DISABILITY",
        "Mental Illness",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "7"): (
        "CWSN_DISABILITY",
        "Specific Learning Disabilities",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "8"): (
        "CWSN_DISABILITY",
        "Cerebral Palsy",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "9"): (
        "CWSN_DISABILITY",
        "Autism Spectrum Disorder",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "10"): (
        "CWSN_DISABILITY",
        "Multiple Disability Including Deaf-Blindness",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "11"): (
        "CWSN_DISABILITY",
        "Leprosy Cured",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "12"): (
        "CWSN_DISABILITY",
        "Dwarfism",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "13"): (
        "CWSN_DISABILITY",
        "Intellectual Disability",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "14"): (
        "CWSN_DISABILITY",
        "Muscular Dystrophy",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "15"): (
        "CWSN_DISABILITY",
        "Chronic Neurological Conditions",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "16"): (
        "CWSN_DISABILITY",
        "Multiple Sclerosis",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "17"): (
        "CWSN_DISABILITY",
        "Thalassemia",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "18"): (
        "CWSN_DISABILITY",
        "Hemophilia",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "19"): (
        "CWSN_DISABILITY",
        "Sickle Cell Disease",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "20"): (
        "CWSN_DISABILITY",
        "Acid Attack Victim",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),

    ("4", "21"): (
        "CWSN_DISABILITY",
        "Parkinson's Disease",
        "DCF_EXTENSION",
        "UDISE+ DCF 2025-26 Section 4.1.17(a)",
    ),

    # EWS
    ("10", "32"): (
        "BENEFICIARY_CATEGORY",
        "EWS",
        "SCHEMA_MAPPED",
        "UDISE+ Data Sharing Portal Schema - School Enrolment_1",
    ),
}


# ------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ------------------------------------------------------------

def clean_value(value):

    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.lower() in ["", "nan", "none", "null", "[blank]"]:
        return ""

    return text


def normalize_code(value):

    text = clean_value(value)

    if not text:
        return ""

    try:
        number = float(text)

        if number.is_integer():
            return str(int(number))

    except ValueError:
        pass

    return text


def identify_part(filename):

    name = str(filename).lower()

    if "enr1" in name:
        return "ENR1"

    if "enr2" in name:
        return "ENR2"

    return "UNKNOWN"


def resolve_mapping(row):

    part = row["file_part"]
    group = row["item_group"]
    item = row["item_id"]
    description = row["item_desc"]

    # Old format uses source-provided descriptions.
    if not group and not item:

        if description:
            return (
                "SOURCE_LABELLED_ITEM",
                description,
                "SOURCE_LABEL_ONLY",
                "Original UDISE Enrollment item description",
                "Retained from source label; no extra decoding",
            )

        return (
            "UNKNOWN",
            "UNMAPPED",
            "UNMAPPED",
            "No source description or code mapping found",
            "Blank source item",
        )

    # ENR1 documented mappings.
    if part == "ENR1":

        key = (group, item)

        if key in ENR1_MAPPING:

            category, label, status, source = ENR1_MAPPING[key]

            return (
                category,
                label,
                status,
                source,
                "Mapped using the documented item_group/item_id definition",
            )

    # ENR2 Age Wise Enrolment.
    if part == "ENR2" and group == "8":

        try:
            age_id = int(item)
        except ValueError:
            age_id = None

        if age_id is not None and 2 <= age_id <= 22:

            return (
                "AGE_WISE_ENROLMENT",
                f"Age_ID_{age_id}",
                "AGE_ID_ONLY",
                "UDISE+ Data Sharing Portal Schema - Age Wise Enrolment_2",
                "Age ID range is documented, but ID-to-actual-age labels are not specified",
            )

    # Explicitly unresolved codes.
    return (
        "UNKNOWN",
        "UNMAPPED",
        "UNMAPPED",
        "No confirmed mapping in the consulted schema",
        "Requires additional authoritative codebook",
    )


# ============================================================
# 3. LOAD SOURCE INVENTORY
# ============================================================

print("=" * 70)
print("SHALASCOPE - ENROLLMENT CODEBOOK CROSSWALK")
print("=" * 70)

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Inventory file not found:\n{INPUT_FILE}"
    )

inventory = pd.read_csv(
    INPUT_FILE,
    dtype=str,
    low_memory=False,
    encoding="utf-8-sig",
)

required_columns = [
    "academic_year",
    "file_name",
    "item_group",
    "item_id",
    "item_desc",
    "record_count",
]

missing = [
    col for col in required_columns
    if col not in inventory.columns
]

if missing:
    raise ValueError(
        f"Required inventory columns missing: {missing}"
    )

print(f"Inventory records: {len(inventory)}")


# ============================================================
# 4. NORMALIZE FIELDS
# ============================================================

for col in required_columns:
    inventory[col] = inventory[col].apply(clean_value)

inventory["file_part"] = inventory["file_name"].apply(
    identify_part
)

inventory["item_group"] = inventory["item_group"].apply(
    normalize_code
)

inventory["item_id"] = inventory["item_id"].apply(
    normalize_code
)


# ============================================================
# 5. BUILD CROSSWALK
# ============================================================

mapping_results = []

for _, row in inventory.iterrows():

    category, label, status, source, note = resolve_mapping(row)

    result = row.to_dict()

    result["feature_category"] = category
    result["canonical_label"] = label
    result["mapping_status"] = status
    result["mapping_source"] = source
    result["mapping_note"] = note

    mapping_results.append(result)


crosswalk = pd.DataFrame(mapping_results)


# ============================================================
# 6. VALIDATION
# ============================================================

if len(crosswalk) != len(inventory):
    raise ValueError(
        "Crosswalk row count does not match inventory."
    )

valid_statuses = {
    "SCHEMA_MAPPED",
    "DCF_EXTENSION",
    "AGE_ID_ONLY",
    "SOURCE_LABEL_ONLY",
    "UNMAPPED",
}

unexpected_statuses = (
    set(crosswalk["mapping_status"].unique())
    - valid_statuses
)

if unexpected_statuses:
    raise ValueError(
        f"Unexpected mapping statuses: {unexpected_statuses}"
    )


# ============================================================
# 7. CREATE UNIQUE CODE DICTIONARY
# ============================================================

dictionary_columns = [
    "file_part",
    "item_group",
    "item_id",
    "item_desc",
    "feature_category",
    "canonical_label",
    "mapping_status",
    "mapping_source",
    "mapping_note",
]

dictionary = (
    crosswalk[dictionary_columns]
    .drop_duplicates()
    .sort_values(
        ["file_part", "item_group", "item_id", "item_desc"],
        na_position="last"
    )
    .reset_index(drop=True)
)


# ============================================================
# 8. CREATE YEAR-WISE MAPPING SUMMARY
# ============================================================

summary = (
    crosswalk.groupby(
        ["academic_year", "mapping_status"],
        dropna=False
    )
    .size()
    .reset_index(name="item_profile_count")
)


# ============================================================
# 9. ISOLATE UNMAPPED ITEMS
# ============================================================

unmapped = crosswalk[
    crosswalk["mapping_status"] == "UNMAPPED"
].copy()


# ============================================================
# 10. SAVE REPORTS
# ============================================================

crosswalk_file = (
    OUTPUT_DIR
    / "enrollment_item_code_crosswalk.csv"
)

dictionary_file = (
    OUTPUT_DIR
    / "enrollment_code_mapping_dictionary.csv"
)

summary_file = (
    OUTPUT_DIR
    / "enrollment_code_mapping_summary.csv"
)

unmapped_file = (
    OUTPUT_DIR
    / "enrollment_unmapped_item_codes.csv"
)

crosswalk.to_csv(
    crosswalk_file,
    index=False,
    encoding="utf-8-sig",
)

dictionary.to_csv(
    dictionary_file,
    index=False,
    encoding="utf-8-sig",
)

summary.to_csv(
    summary_file,
    index=False,
    encoding="utf-8-sig",
)

unmapped.to_csv(
    unmapped_file,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# 11. FINAL RESULT
# ============================================================

print("\n" + "=" * 70)
print("ENROLLMENT CODEBOOK CROSSWALK - FINAL RESULT")
print("=" * 70)

print(f"Input inventory rows: {len(inventory)}")
print(f"Crosswalk rows: {len(crosswalk)}")
print(f"Unique mappings: {len(dictionary)}")

print("\nMAPPING STATUS:")

print(
    crosswalk["mapping_status"]
    .value_counts()
    .to_string()
)

print("\nYEAR-WISE SUMMARY:")

print(
    summary.to_string(index=False)
)

print("\nUNMAPPED ITEMS:")

if unmapped.empty:
    print("No unmapped items found.")
else:
    print(
        unmapped[
            [
                "academic_year",
                "file_name",
                "item_group",
                "item_id",
                "item_desc",
                "record_count",
            ]
        ].to_string(index=False)
    )

print("\nOUTPUT FILES:")

print(crosswalk_file)
print(dictionary_file)
print(summary_file)
print(unmapped_file)

print("\nIMPORTANT:")
print("- Age IDs are not converted into actual age labels.")
print("- Group 5 Item 0 remains UNMAPPED.")
print("- Original source descriptions are preserved.")
print("- No student totals are calculated in this step.")

print("\nENROLLMENT CODEBOOK CROSSWALK COMPLETED")

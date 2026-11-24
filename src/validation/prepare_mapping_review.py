
"""
ShalaScope Maharashtra
Column Mapping Review Preparation

Creates a review template from the draft mapping.
Original mapping files remain unchanged.
"""

from pathlib import Path
import csv
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT / "docs" / "column_mapping"
    / "ShalaScope_Standard_Column_Mapping_Draft.csv"
)

OUTPUT_FILE = (
    ROOT / "docs" / "column_mapping"
    / "ShalaScope_Mapping_Review_Template.csv"
)

SUMMARY_FILE = (
    ROOT / "docs" / "column_mapping"
    / "ShalaScope_Mapping_Review_Summary.csv"
)


def get_review_action(status):
    """Suggests the type of manual review required."""

    status = str(status).strip().lower()

    if status == "direct":
        return "VERIFY_SOURCE_MEANING"

    if status == "alias":
        return "VERIFY_ALIAS_EQUIVALENCE"

    if status == "direct identifier alias":
        return "VERIFY_SCHOOL_ID"

    if status == "derived/direct-new":
        return "VERIFY_NEW_OR_DERIVED_FIELD"

    if status == "review meaning":
        return "CHECK_DEFINITION_AND_UNITS"

    return "MANUAL_REVIEW_REQUIRED"


def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Mapping draft not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("Mapping CSV has no header.")

        required = {
            "category",
            "source_column",
            "standard_column_candidate",
            "mapping_status",
            "years_available",
            "year_count",
            "notes",
        }

        missing = required - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

        rows = list(reader)

    if not rows:
        raise ValueError("Mapping draft contains no records.")

    output_rows = []

    status_counts = Counter()
    category_counts = Counter()

    for row in rows:

        status = row["mapping_status"].strip()

        status_counts[status] += 1
        category_counts[row["category"]] += 1

        output_rows.append({
            **row,
            "review_action": get_review_action(status),
            "review_decision": "PENDING",
            "final_standard_column": "",
            "review_notes": "",
        })

    OUTPUT_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    fields = list(output_rows[0].keys())

    with OUTPUT_FILE.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:

        writer = csv.DictWriter(
            file, fieldnames=fields
        )
        writer.writeheader()
        writer.writerows(output_rows)

    # Create summary report.
    with SUMMARY_FILE.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow(["Mapping Status", "Count"])

        for status, count in sorted(status_counts.items()):
            writer.writerow([status, count])

        writer.writerow([])
        writer.writerow(["Category", "Count"])

        for category, count in sorted(category_counts.items()):
            writer.writerow([category, count])

    print("\nSHALASCOPE MAPPING REVIEW")
    print("=" * 50)
    print(f"Total mapping records: {len(rows)}")

    print("\nStatus-wise counts:")

    for status, count in sorted(status_counts.items()):
        print(f"{status}: {count}")

    print("\nCategory-wise counts:")

    for category, count in sorted(category_counts.items()):
        print(f"{category}: {count}")

    print("\nCreated files:")
    print(OUTPUT_FILE)
    print(SUMMARY_FILE)

    print("\nOriginal mapping draft was not modified.")
    print("MAPPING REVIEW TEMPLATE CREATED SUCCESSFULLY.")


if __name__ == "__main__":
    main()

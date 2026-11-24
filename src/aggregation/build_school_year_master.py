
"""
ShalaScope Maharashtra
School-Year Master Dataset Builder

Years: 2018-19 to 2025-26

Inputs:
- Standardized Profile 1
- Standardized Profile 2
- Standardized Teacher

Merge key:
- School ID

Output:
- One master CSV per academic year.

Features:
1. Uses SQLite for memory-efficient processing.
2. Validates unique School IDs.
3. Validates exact School ID matching.
4. Validates district and district_raw consistency.
5. Preserves all source columns.
6. Prevents duplicate column names.
7. Creates a column manifest.
8. Does not modify original files.
9. Writes final output only after validation passes.

Python standard library only.
"""

from pathlib import Path
import csv
import re
import json
import sqlite3


# ==================================================
# 1. PROJECT PATHS
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

BASE_DIR = ROOT / "data" / "interim" / "standardized"

PROFILE1_DIR = BASE_DIR / "profile1"
PROFILE2_DIR = BASE_DIR / "profile2"
TEACHER_DIR = BASE_DIR / "teacher"

OUTPUT_DIR = ROOT / "data" / "processed" / "school_year"

WORK_DIR = ROOT / "data" / "interim" / "master_build_work"

REPORT_DIR = ROOT / "reports" / "data_audit"

SUMMARY_REPORT = (
    REPORT_DIR / "master_dataset_build_audit.csv"
)

MANIFEST_REPORT = (
    REPORT_DIR / "master_dataset_column_manifest.csv"
)

ISSUES_REPORT = (
    REPORT_DIR / "master_dataset_build_issues.csv"
)

YEARS = [
    "2018-19",
    "2019-20",
    "2020-21",
    "2021-22",
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
]

ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "latin-1",
)

MISSING_VALUES = {
    "",
    "na",
    "n/a",
    "null",
    "none",
    "nan",
}

ID_ALIASES = {
    "pseudocode",
    "psuedocode",
    "schoolid",
    "udiseid",
}

BATCH_SIZE = 1000


# ==================================================
# 2. HELPER FUNCTIONS
# ==================================================

def norm(value):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


def is_missing(value):

    return (
        str(value or "").strip().lower()
        in MISSING_VALUES
    )


def open_csv(path):

    last_error = None

    for encoding in ENCODINGS:

        handle = None

        try:

            handle = path.open(
                "r",
                encoding=encoding,
                newline=""
            )

            sample = handle.read(65536)
            handle.seek(0)

            try:

                dialect = csv.Sniffer().sniff(
                    sample,
                    delimiters=",;\t|"
                )

            except csv.Error:

                dialect = csv.excel

            return handle, dialect

        except UnicodeDecodeError as error:

            last_error = error

            if handle is not None:
                handle.close()

    raise UnicodeError(
        f"Cannot decode CSV: {path}. {last_error}"
    )


def find_id_field(headers):

    normalized = {}

    for header in headers:

        key = norm(header)

        if key in normalized:

            raise ValueError(
                f"Duplicate normalized column: {header}"
            )

        normalized[key] = header

    for alias in ID_ALIASES:

        if alias in normalized:

            return normalized[alias]

    return None


def find_column(headers, target):

    target = norm(target)

    for header in headers:

        if norm(header) == target:
            return header

    return None


# ==================================================
# 3. INPUT FILE PATHS
# ==================================================

def get_input_paths(year):

    return {

        "PROFILE1": (
            PROFILE1_DIR
            / f"maharashtra_profile1_{year}_standardized.csv"
        ),

        "PROFILE2": (
            PROFILE2_DIR
            / f"maharashtra_profile2_{year}_standardized.csv"
        ),

        "TEACHER": (
            TEACHER_DIR
            / f"maharashtra_teacher_{year}_standardized.csv"
        ),

    }


# ==================================================
# 4. LOAD ONE DATASET INTO SQLITE
# ==================================================

def load_dataset(
    connection,
    table_name,
    path,
    dataset_name
):

    if not path.exists():

        raise FileNotFoundError(
            f"{dataset_name} file not found: {path}"
        )

    handle, dialect = open_csv(path)

    total_records = 0
    batch = []

    try:

        reader = csv.reader(
            handle,
            dialect=dialect
        )

        headers = next(reader, [])

        if not headers:

            raise ValueError(
                f"Empty CSV header: {path}"
            )

        id_field = find_id_field(headers)

        district_field = find_column(
            headers,
            "district"
        )

        raw_field = find_column(
            headers,
            "district_raw"
        )

        if not id_field:

            raise ValueError(
                f"School ID column missing in {path.name}"
            )

        if not district_field or not raw_field:

            raise ValueError(
                f"District columns missing in {path.name}"
            )

        connection.execute(
            f"""
            CREATE TABLE {table_name} (
                school_id TEXT PRIMARY KEY,
                district TEXT NOT NULL,
                district_raw TEXT NOT NULL,
                row_json TEXT NOT NULL
            )
            """
        )

        insert_sql = f"""
            INSERT INTO {table_name}
            (
                school_id,
                district,
                district_raw,
                row_json
            )
            VALUES (?, ?, ?, ?)
        """

        for record_number, row in enumerate(reader, start=2):

            if not row or all(
                not str(value).strip()
                for value in row
            ):
                continue

            if len(row) != len(headers):

                raise ValueError(
                    f"{dataset_name}: Malformed row "
                    f"{record_number} in {path.name}. "
                    f"Expected {len(headers)} columns, "
                    f"found {len(row)}."
                )

            row_data = dict(
                zip(headers, row)
            )

            school_id = str(
                row_data[id_field]
            ).strip()

            district = str(
                row_data[district_field]
            ).strip().upper()

            district_raw = str(
                row_data[raw_field]
            ).strip().upper()

            if is_missing(school_id):

                raise ValueError(
                    f"{dataset_name}: Missing School ID "
                    f"at record {record_number}."
                )

            if is_missing(district):

                raise ValueError(
                    f"{dataset_name}: Missing district "
                    f"for School ID {school_id}."
                )

            if is_missing(district_raw):

                raise ValueError(
                    f"{dataset_name}: Missing district_raw "
                    f"for School ID {school_id}."
                )

            row_json = json.dumps(
                row_data,
                ensure_ascii=False
            )

            batch.append((
                school_id,
                district,
                district_raw,
                row_json,
            ))

            total_records += 1

            if len(batch) >= BATCH_SIZE:

                try:

                    connection.executemany(
                        insert_sql,
                        batch
                    )

                except sqlite3.IntegrityError as error:

                    raise ValueError(
                        f"{dataset_name}: Duplicate School ID "
                        f"detected. {error}"
                    )

                batch.clear()

        if batch:

            try:

                connection.executemany(
                    insert_sql,
                    batch
                )

            except sqlite3.IntegrityError as error:

                raise ValueError(
                    f"{dataset_name}: Duplicate School ID "
                    f"detected. {error}"
                )

        connection.commit()

    finally:

        handle.close()

    return {

        "headers": headers,
        "id_field": id_field,
        "records": total_records,
        "district_field": district_field,
        "raw_field": raw_field,

    }


# ==================================================
# 5. DATABASE VALIDATION
# ==================================================

def get_table_stats(connection, table_name):

    row = connection.execute(
        f"""
        SELECT
            COUNT(*),
            COUNT(DISTINCT school_id),
            COUNT(DISTINCT district),
            SUM(
                CASE
                    WHEN TRIM(district) = '' THEN 1
                    ELSE 0
                END
            ),
            SUM(
                CASE
                    WHEN TRIM(district_raw) = '' THEN 1
                    ELSE 0
                END
            )
        FROM {table_name}
        """
    ).fetchone()

    return {

        "records": row[0] or 0,
        "unique_ids": row[1] or 0,
        "unique_districts": row[2] or 0,
        "missing_districts": row[3] or 0,
        "missing_raw_districts": row[4] or 0,

    }


def count_ids_not_in(
    connection,
    left_table,
    right_table
):

    result = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {left_table} AS a
        LEFT JOIN {right_table} AS b
            ON a.school_id = b.school_id
        WHERE b.school_id IS NULL
        """
    ).fetchone()

    return result[0]


def count_district_mismatches(
    connection,
    source_table
):

    result = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {source_table} AS s
        INNER JOIN profile1 AS p
            ON s.school_id = p.school_id
        WHERE
            s.district != p.district
            OR s.district_raw != p.district_raw
        """
    ).fetchone()

    return result[0]


# ==================================================
# 6. CREATE OUTPUT COLUMN PLAN
# ==================================================

def create_column_plan(metadata):

    output_fields = [
        "academic_year",
        "school_id",
        "district",
        "district_raw",
    ]

    used_names = {
        norm(name)
        for name in output_fields
    }

    source_mapping = {}
    manifest = []

    dataset_order = [
        "PROFILE1",
        "PROFILE2",
        "TEACHER",
    ]

    for dataset in dataset_order:

        source_mapping[dataset] = {}

        headers = metadata[dataset]["headers"]

        id_field = metadata[dataset]["id_field"]

        for source_column in headers:

            column_key = norm(source_column)

            # These fields already exist in the master.
            if (
                source_column == id_field
                or column_key in ID_ALIASES
                or column_key in {"district", "districtraw"}
            ):

                continue

            output_column = source_column

            # Avoid duplicate column names.
            if norm(output_column) in used_names:

                output_column = (
                    f"{dataset.lower()}__{source_column}"
                )

            suffix = 2
            original_candidate = output_column

            while norm(output_column) in used_names:

                output_column = (
                    f"{original_candidate}_{suffix}"
                )

                suffix += 1

            used_names.add(
                norm(output_column)
            )

            output_fields.append(
                output_column
            )

            source_mapping[dataset][source_column] = (
                output_column
            )

            manifest.append({

                "source_dataset": dataset,
                "source_column": source_column,
                "master_column": output_column,

            })

    return output_fields, source_mapping, manifest


# ==================================================
# 7. BUILD MASTER CSV
# ==================================================

def build_master_csv(
    connection,
    year,
    metadata,
    output_path
):

    output_fields, source_mapping, manifest = (
        create_column_plan(metadata)
    )

    temp_path = output_path.with_suffix(".tmp")

    query = """
        SELECT
            p1.school_id,
            p1.district,
            p1.district_raw,
            p1.row_json,
            p2.row_json,
            t.row_json

        FROM profile1 AS p1

        INNER JOIN profile2 AS p2
            ON p1.school_id = p2.school_id

        INNER JOIN teacher AS t
            ON p1.school_id = t.school_id

        ORDER BY p1.school_id
    """

    output_records = 0

    cursor = connection.execute(query)

    try:

        with temp_path.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as output_file:

            writer = csv.writer(
                output_file,
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
                doublequote=True,
                lineterminator="\n"
            )

            writer.writerow(output_fields)

            while True:

                rows = cursor.fetchmany(BATCH_SIZE)

                if not rows:
                    break

                for row in rows:

                    (
                        school_id,
                        district,
                        district_raw,
                        profile1_json,
                        profile2_json,
                        teacher_json,
                    ) = row

                    profile_data = {

                        "PROFILE1": json.loads(profile1_json),
                        "PROFILE2": json.loads(profile2_json),
                        "TEACHER": json.loads(teacher_json),

                    }

                    output_values = {

                        "academic_year": year,
                        "school_id": school_id,
                        "district": district,
                        "district_raw": district_raw,

                    }

                    for dataset in (
                        "PROFILE1",
                        "PROFILE2",
                        "TEACHER",
                    ):

                        source_row = profile_data[dataset]

                        for source_column, master_column in (
                            source_mapping[dataset].items()
                        ):

                            output_values[master_column] = (
                                source_row.get(source_column, "")
                            )

                    writer.writerow([
                        output_values.get(field, "")
                        for field in output_fields
                    ])

                    output_records += 1

        expected_records = connection.execute(
            "SELECT COUNT(*) FROM profile1"
        ).fetchone()[0]

        if output_records != expected_records:

            raise ValueError(
                f"Master output count mismatch: "
                f"expected {expected_records}, "
                f"created {output_records}."
            )

        temp_path.replace(output_path)

    except Exception:

        if temp_path.exists():
            temp_path.unlink()

        raise

    return output_records, len(output_fields), manifest


# ==================================================
# 8. SAVE REPORT
# ==================================================

def save_report(path, rows, fields):

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(rows)


# ==================================================
# 9. PROCESS ONE ACADEMIC YEAR
# ==================================================

def process_year(year, manifest_rows):

    print(
        f"\nProcessing academic year: {year}"
    )

    paths = get_input_paths(year)

    for dataset, path in paths.items():

        if not path.exists():

            raise FileNotFoundError(
                f"{dataset} standardized file missing: {path}"
            )

    WORK_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    db_path = WORK_DIR / f"master_{year}.sqlite"

    if db_path.exists():
        db_path.unlink()

    connection = None
    output_path = (
        OUTPUT_DIR
        / f"maharashtra_school_year_master_{year}.csv"
    )

    try:

        connection = sqlite3.connect(db_path)

        connection.execute("PRAGMA journal_mode = OFF")
        connection.execute("PRAGMA synchronous = OFF")
        connection.execute("PRAGMA temp_store = FILE")

        metadata = {}

        # ------------------------------------------
        # LOAD PROFILE 1
        # ------------------------------------------

        metadata["PROFILE1"] = load_dataset(
            connection,
            "profile1",
            paths["PROFILE1"],
            "PROFILE1"
        )

        print(
            f"Profile 1 loaded: "
            f"{metadata['PROFILE1']['records']:,}"
        )

        # ------------------------------------------
        # LOAD PROFILE 2
        # ------------------------------------------

        metadata["PROFILE2"] = load_dataset(
            connection,
            "profile2",
            paths["PROFILE2"],
            "PROFILE2"
        )

        print(
            f"Profile 2 loaded: "
            f"{metadata['PROFILE2']['records']:,}"
        )

        # ------------------------------------------
        # LOAD TEACHER
        # ------------------------------------------

        metadata["TEACHER"] = load_dataset(
            connection,
            "teacher",
            paths["TEACHER"],
            "TEACHER"
        )

        print(
            f"Teacher loaded: "
            f"{metadata['TEACHER']['records']:,}"
        )

        # ------------------------------------------
        # VALIDATE ALL DATASETS
        # ------------------------------------------

        stats = {

            "PROFILE1": get_table_stats(
                connection,
                "profile1"
            ),

            "PROFILE2": get_table_stats(
                connection,
                "profile2"
            ),

            "TEACHER": get_table_stats(
                connection,
                "teacher"
            ),

        }

        p2_not_in_p1 = count_ids_not_in(
            connection,
            "profile2",
            "profile1"
        )

        p1_not_in_p2 = count_ids_not_in(
            connection,
            "profile1",
            "profile2"
        )

        teacher_not_in_p1 = count_ids_not_in(
            connection,
            "teacher",
            "profile1"
        )

        p1_not_in_teacher = count_ids_not_in(
            connection,
            "profile1",
            "teacher"
        )

        p2_not_in_teacher = count_ids_not_in(
            connection,
            "profile2",
            "teacher"
        )

        teacher_not_in_p2 = count_ids_not_in(
            connection,
            "teacher",
            "profile2"
        )

        p2_district_mismatches = count_district_mismatches(
            connection,
            "profile2"
        )

        teacher_district_mismatches = count_district_mismatches(
            connection,
            "teacher"
        )

        id_sets_match = (
            p2_not_in_p1 == 0
            and p1_not_in_p2 == 0
            and teacher_not_in_p1 == 0
            and p1_not_in_teacher == 0
            and p2_not_in_teacher == 0
            and teacher_not_in_p2 == 0
        )

        record_counts_match = (
            stats["PROFILE1"]["records"]
            == stats["PROFILE2"]["records"]
            == stats["TEACHER"]["records"]
        )

        district_counts_pass = all(
            stats[name]["unique_districts"] == 36
            for name in stats
        )

        missing_values_pass = all(

            stats[name]["missing_districts"] == 0
            and stats[name]["missing_raw_districts"] == 0

            for name in stats

        )

        district_mapping_pass = (
            p2_district_mismatches == 0
            and teacher_district_mismatches == 0
        )

        all_id_counts_pass = all(

            stats[name]["records"] == stats[name]["unique_ids"]

            for name in stats

        )

        # ------------------------------------------
        # MERGE ONLY AFTER VALIDATION
        # ------------------------------------------

        validation_pass = all([
            id_sets_match,
            record_counts_match,
            district_counts_pass,
            missing_values_pass,
            district_mapping_pass,
            all_id_counts_pass,
        ])

        if not validation_pass:

            raise ValueError(
                "Pre-merge validation failed. "
                f"ID sets match={id_sets_match}; "
                f"record counts match={record_counts_match}; "
                f"district counts pass={district_counts_pass}; "
                f"missing values pass={missing_values_pass}; "
                f"district mapping pass={district_mapping_pass}; "
                f"unique IDs pass={all_id_counts_pass}."
            )

        # ------------------------------------------
        # BUILD MASTER CSV
        # ------------------------------------------

        output_records, column_count, manifest = build_master_csv(
            connection,
            year,
            metadata,
            output_path
        )

        manifest_rows.extend({

            "academic_year": year,
            "source_dataset": item["source_dataset"],
            "source_column": item["source_column"],
            "master_column": item["master_column"],

        } for item in manifest)

        result = {

            "academic_year": year,

            "profile1_records": stats["PROFILE1"]["records"],
            "profile2_records": stats["PROFILE2"]["records"],
            "teacher_records": stats["TEACHER"]["records"],

            "master_records": output_records,
            "master_columns": column_count,

            "profile1_districts": stats["PROFILE1"]["unique_districts"],
            "profile2_districts": stats["PROFILE2"]["unique_districts"],
            "teacher_districts": stats["TEACHER"]["unique_districts"],

            "id_sets_match": id_sets_match,
            "record_counts_match": record_counts_match,

            "p2_district_mismatches": p2_district_mismatches,
            "teacher_district_mismatches": teacher_district_mismatches,

            "output_file": str(
                output_path.relative_to(ROOT)
            ),

            "status": "PASS",

        }

        print(
            f"School-Year Master Records: {output_records:,}"
        )

        print(
            f"Master Columns: {column_count}"
        )

        print(
            f"District Mismatches: "
            f"{p2_district_mismatches + teacher_district_mismatches}"
        )

        print("ID Sets Match: True")
        print("STATUS: PASS")
        print(f"Output: {result['output_file']}")

        return result

    finally:

        if connection is not None:
            connection.close()

        if db_path.exists():
            db_path.unlink()


# ==================================================
# 10. MAIN PROGRAM
# ==================================================

def main():

    print("\nSHALASCOPE - SCHOOL-YEAR MASTER DATASET BUILDER")
    print("=" * 78)

    if not PROFILE1_DIR.exists():
        raise FileNotFoundError(PROFILE1_DIR)

    if not PROFILE2_DIR.exists():
        raise FileNotFoundError(PROFILE2_DIR)

    if not TEACHER_DIR.exists():
        raise FileNotFoundError(TEACHER_DIR)

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    WORK_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    summaries = []
    manifest_rows = []
    issues = []

    # ------------------------------------------
    # PROCESS ALL EIGHT YEARS
    # ------------------------------------------

    for index, year in enumerate(YEARS, 1):

        print(
            f"\n[{index}/{len(YEARS)}] Academic Year: {year}"
        )

        try:

            result = process_year(
                year,
                manifest_rows
            )

            summaries.append(result)

        except Exception as error:

            print(f"ERROR: {error}")

            summaries.append({

                "academic_year": year,

                "profile1_records": 0,
                "profile2_records": 0,
                "teacher_records": 0,

                "master_records": 0,
                "master_columns": 0,

                "profile1_districts": 0,
                "profile2_districts": 0,
                "teacher_districts": 0,

                "id_sets_match": False,
                "record_counts_match": False,

                "p2_district_mismatches": 0,
                "teacher_district_mismatches": 0,

                "output_file": "",
                "status": "FAILED",

            })

            issues.append({

                "academic_year": year,
                "issue": "MASTER_BUILD_FAILED",
                "details": str(error),

            })

    # ==================================================
    # 11. SAVE SUMMARY REPORT
    # ==================================================

    summary_fields = [

        "academic_year",

        "profile1_records",
        "profile2_records",
        "teacher_records",

        "master_records",
        "master_columns",

        "profile1_districts",
        "profile2_districts",
        "teacher_districts",

        "id_sets_match",
        "record_counts_match",

        "p2_district_mismatches",
        "teacher_district_mismatches",

        "output_file",
        "status",

    ]

    save_report(
        SUMMARY_REPORT,
        summaries,
        summary_fields
    )

    # ==================================================
    # 12. SAVE COLUMN MANIFEST
    # ==================================================

    manifest_fields = [
        "academic_year",
        "source_dataset",
        "source_column",
        "master_column",
    ]

    save_report(
        MANIFEST_REPORT,
        manifest_rows,
        manifest_fields
    )

    # ==================================================
    # 13. SAVE ISSUES
    # ==================================================

    issue_fields = [
        "academic_year",
        "issue",
        "details",
    ]

    save_report(
        ISSUES_REPORT,
        issues,
        issue_fields
    )

    # ==================================================
    # 14. FINAL SUMMARY
    # ==================================================

    passed = sum(
        row["status"] == "PASS"
        for row in summaries
    )

    failed = sum(
        row["status"] == "FAILED"
        for row in summaries
    )

    total_master_records = sum(
        row["master_records"]
        for row in summaries
    )

    print("\n" + "=" * 78)
    print("FINAL MASTER DATASET BUILD SUMMARY")
    print("=" * 78)

    print(f"Academic Years: {len(summaries)}")
    print(f"Master Records: {total_master_records:,}")
    print(f"PASS: {passed}")
    print(f"Failed: {failed}")

    print("\nREPORTS CREATED")
    print(SUMMARY_REPORT)
    print(MANIFEST_REPORT)
    print(ISSUES_REPORT)

    print("\nMASTER DATASET FOLDER")
    print(OUTPUT_DIR)

    print("\nSCHOOL-YEAR MASTER DATASET BUILD COMPLETED")


if __name__ == "__main__":
    main()

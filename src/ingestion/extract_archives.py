
"""
ShalaScope Maharashtra
Automatic UDISE+ ZIP Extraction

Features:
1. Finds all ZIP files year-wise.
2. Checks ZIP integrity using CRC.
3. Prevents unsafe archive paths.
4. Extracts each archive into its own folder.
5. Preserves original ZIP files.
6. Generates an extraction audit CSV.
"""

from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile
import csv
import shutil


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

ZIP_ROOT = ROOT / "data" / "raw" / "udise_zip"
EXTRACT_ROOT = ROOT / "data" / "extracted"

REPORT_DIR = ROOT / "reports" / "data_audit"
MANIFEST = REPORT_DIR / "archive_extraction_manifest.csv"


# --------------------------------------------------
# SAFE ZIP PATH VALIDATION
# --------------------------------------------------

def validate_archive_paths(zip_file: ZipFile, destination: Path):
    """
    Prevents ZIP Slip path traversal.
    """

    base = destination.resolve()

    for info in zip_file.infolist():

        member_name = info.filename.replace("\\", "/")
        member_path = PurePosixPath(member_name)

        if member_path.is_absolute():
            raise ValueError(
                f"Absolute archive path detected: {member_name}"
            )

        if ".." in member_path.parts:
            raise ValueError(
                f"Unsafe archive path detected: {member_name}"
            )

        if member_path.parts and ":" in member_path.parts[0]:
            raise ValueError(
                f"Drive path detected: {member_name}"
            )

        target = destination.joinpath(
            *member_path.parts
        ).resolve()

        try:
            target.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Archive path escapes destination: {member_name}"
            )


# --------------------------------------------------
# EXTRACT ONE ARCHIVE
# --------------------------------------------------

def extract_archive(zip_path: Path, year: str):

    destination = (
        EXTRACT_ROOT / year / zip_path.stem
    )

    temporary = destination.with_name(
        destination.name + "__extracting"
    )

    # Do not overwrite previously extracted data.
    if destination.exists():

        if any(destination.iterdir()):
            return {
                "status": "SKIPPED_ALREADY_EXTRACTED",
                "folder": str(destination.relative_to(ROOT))
            }

        destination.rmdir()

    if temporary.exists():
        shutil.rmtree(temporary)

    temporary.mkdir(parents=True, exist_ok=True)

    try:

        with ZipFile(zip_path, "r") as archive:

            # Verify CRC integrity of every member.
            corrupt_file = archive.testzip()

            if corrupt_file:
                raise BadZipFile(
                    f"Corrupt file inside ZIP: {corrupt_file}"
                )

            validate_archive_paths(archive, temporary)

            # Extract into a temporary directory first.
            archive.extractall(temporary)

            total_files = sum(
                1 for item in temporary.rglob("*")
                if item.is_file()
            )

            csv_files = sum(
                1 for item in temporary.rglob("*")
                if item.is_file()
                and item.suffix.lower() == ".csv"
            )

        destination.parent.mkdir(
            parents=True, exist_ok=True
        )

        # Move completed extraction into final location.
        temporary.rename(destination)

        return {
            "status": "EXTRACTED",
            "folder": str(destination.relative_to(ROOT)),
            "total_files": total_files,
            "csv_files": csv_files
        }

    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


# --------------------------------------------------
# MAIN PROCESS
# --------------------------------------------------

def main():

    if not ZIP_ROOT.exists():
        raise FileNotFoundError(
            f"ZIP folder not found: {ZIP_ROOT}"
        )

    REPORT_DIR.mkdir(
        parents=True, exist_ok=True
    )

    zip_files = sorted(
        ZIP_ROOT.glob("*/*.zip")
    )

    if not zip_files:
        raise FileNotFoundError(
            "No ZIP files found in year folders."
        )

    results = []

    print("\nSHALASCOPE - ZIP EXTRACTION")
    print("=" * 55)

    for index, zip_path in enumerate(zip_files, 1):

        year = zip_path.parent.name

        print(
            f"\n[{index}/{len(zip_files)}] "
            f"{year} | {zip_path.name}"
        )

        try:

            result = extract_archive(
                zip_path, year
            )

            status = result["status"]

            print(f"Status: {status}")

            results.append({
                "academic_year": year,
                "archive_name": zip_path.name,
                "archive_size_mb": round(
                    zip_path.stat().st_size / (1024 * 1024), 2
                ),
                "status": status,
                "extraction_folder": result.get("folder", ""),
                "total_files": result.get("total_files", 0),
                "csv_files": result.get("csv_files", 0),
                "error": ""
            })

        except Exception as error:

            print(f"ERROR: {error}")

            results.append({
                "academic_year": year,
                "archive_name": zip_path.name,
                "archive_size_mb": round(
                    zip_path.stat().st_size / (1024 * 1024), 2
                ),
                "status": "FAILED",
                "extraction_folder": "",
                "total_files": 0,
                "csv_files": 0,
                "error": str(error)
            })

    # Save audit manifest.
    fields = [
        "academic_year",
        "archive_name",
        "archive_size_mb",
        "status",
        "extraction_folder",
        "total_files",
        "csv_files",
        "error"
    ]

    with MANIFEST.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file, fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(results)

    extracted = sum(
        row["status"] == "EXTRACTED"
        for row in results
    )

    skipped = sum(
        row["status"] == "SKIPPED_ALREADY_EXTRACTED"
        for row in results
    )

    failed = sum(
        row["status"] == "FAILED"
        for row in results
    )

    print("\n" + "=" * 55)
    print("EXTRACTION SUMMARY")
    print(f"Total ZIP files : {len(results)}")
    print(f"Extracted       : {extracted}")
    print(f"Already present : {skipped}")
    print(f"Failed          : {failed}")
    print(f"\nAudit report: {MANIFEST}")

    if failed:
        print("\nPlease check failed archives before proceeding.")
    else:
        print("\nExtraction process completed successfully.")


if __name__ == "__main__":
    main()

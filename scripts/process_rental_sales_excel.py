#!/usr/bin/env python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pandas",
#   "geopandas",
#   "openpyxl",
#   "pyarrow"
# ]
# ///
"""
process_rental_sales_excel - Transform rental/sales Excel files to CSV and GeoJSON.

Processes 6 Excel files (2 rental, 4 sales) containing 18 sheets total.
Transforms wide format data to tall format CSV with standardized schema.
Generates matching GeoJSON files with boundary polygons.
"""

import argparse
import json
import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import datetime
from textwrap import dedent
from time import time
import re

# Logging
log = logging.getLogger(__name__)

# Configuration
SCRIPT = Path(__file__)
SCRIPT_NAME = SCRIPT.stem
SCRIPT_DIR = SCRIPT.parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

# Directories
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = PROJECT_ROOT / "tmp" / "claude_cache" / SCRIPT_NAME
OUTPUT_DIR = DATA_DIR / "processed" / "rental_sales"
CSV_DIR = OUTPUT_DIR / "csv"
GEOJSON_DIR = OUTPUT_DIR / "geojson"

# Input files (from discovery)
CONFIG_FILE = SCRIPT_DIR / "rental_sales_config.json"
RENTAL_DIR = DATA_DIR / "originals" / "rental"
SALES_DIR = DATA_DIR / "originals" / "sales"
ALL_INPUTS = [CONFIG_FILE, *RENTAL_DIR.glob("*.xlsx"), *SALES_DIR.glob("*.xlsx")]

# Boundary files
BOUNDARY_DIR = DATA_DIR / "originals_converted" / "boundaries"
LGA_BOUNDARY = BOUNDARY_DIR / "LGA_2024_AUST_GDA2020"
SA2_BOUNDARY = BOUNDARY_DIR / "SA2_2021_AUST_SHP_GDA2020"

# Output files (18 CSV + 18 GeoJSON)
ALL_OUTPUTS = []  # Will be populated based on config

# Cache timeout (5 minutes default)
CACHE_TIMEOUT = 300

# Helper lambdas
_is_cache_valid = lambda time_tuple: all(x > 0 for x in time_tuple)  # noqa: E731
_format_file_list = lambda files, max_show=3: '\\n        '.join(  # noqa: E731
    f"- {p.relative_to(PROJECT_ROOT)}" for p in files[:max_show]
) + (f"\\n        ... and {len(files) - max_show} more files" if len(files) > max_show else "")


def check_cache(cache_dir: Path, all_input_files: list[Path], timeout: int = 300, force: bool = False) -> tuple[int, int]:
    """Check if cache is invalid, 'dirty' or expired.

    Returns tuple of (delta, remaining) where:
    - delta: time difference between cache and inputs (positive = cache newer)
    - remaining: time left before cache expires (positive = not expired)
    """
    if force or not cache_dir.exists():
        return (-1, -1)  # Both negative = forced dirty

    cache_mtime = max([0] + [f.stat().st_mtime for f in cache_dir.rglob('*') if f.is_file()])
    all_inputs_mtime = max([0] + [f.stat().st_mtime for f in all_input_files if f.is_file()])

    delta = int(cache_mtime - all_inputs_mtime)
    remaining = int(timeout - (time() - cache_mtime))

    return (delta, remaining)


def load_config() -> dict:
    """Load the discovery configuration."""
    if not CONFIG_FILE.exists():
        log.error(f"Config file not found: {CONFIG_FILE}")
        raise FileNotFoundError(f"Run discover_rental_sales_data.py first")

    with open(CONFIG_FILE) as f:
        return json.load(f)


def setup_directories():
    """Ensure output directories exist."""
    for dir_path in [CACHE_DIR, CSV_DIR, GEOJSON_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


def process_rental_sheet(file_path: Path, sheet_info: dict) -> pd.DataFrame:
    """Process a rental sheet from wide to tall format.

    Rental data structure (from debugging):
    - Row 0: Title
    - Row 1: Time periods (Mar 2000, Mar 2000, Jun 2000, etc.)
    - Row 2: Count/Median labels
    - Row 3+: Data with first two columns being location info
    """
    sheet_name = sheet_info["sheet_name"]
    log.info(f"  Processing rental sheet: {sheet_name}")

    # Read with multi-level headers (rows 1-2)
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=[1, 2])

    # Clean up the first column name - it contains location data
    first_col = df.columns[0]
    df = df.rename(columns={first_col: "location"})

    # Drop any completely empty rows
    df = df.dropna(how='all')

    # Get location column - handle the case where location might be in second column
    location_data = df.iloc[:, 0].fillna(df.iloc[:, 1])
    location_data = location_data.dropna()

    # Create a clean dataframe with just the location and time-series data
    # Skip the first 2 columns (location info) and take only the median columns
    time_cols = []
    median_cols = []

    for i, col in enumerate(df.columns[2:], 2):  # Start from column 2
        if isinstance(col, tuple) and len(col) == 2:
            time_period, metric = col
            if metric == "Median":
                time_cols.append(time_period)
                median_cols.append(col)

    # Create a dataframe with location and median values only
    result_data = []
    for idx, location in location_data.items():
        if pd.isna(location) or location == "":
            continue

        for time_period, median_col in zip(time_cols, median_cols):
            if idx < len(df):
                value = df.loc[idx, median_col]
                if pd.notna(value) and value != "":
                    # Parse and format time_bucket
                    formatted_time, time_type = parse_time_bucket(str(time_period).strip())

                    result_data.append({
                        "geospatial_id": str(location).strip(),
                        "time_bucket": formatted_time,
                        "time_bucket_type": time_type,
                        "value": value,
                        "value_type": "rent",
                        "dwelling_type": normalize_dwelling_type(sheet_info.get("dwelling_type")),
                        "bedrooms": sheet_info.get("bedrooms"),
                        "geospatial_type": sheet_info.get("geospatial_type")
                    })

    result_df = pd.DataFrame(result_data)

    # Basic cleanup
    if not result_df.empty:
        # Remove any rows where geospatial_id looks like a header
        result_df = result_df[~result_df["geospatial_id"].str.contains("Melbourne|Region", na=False, case=False)]
        result_df = result_df[result_df["geospatial_id"] != ""]

    return result_df


def process_sales_sheet(file_path: Path, sheet_info: dict) -> pd.DataFrame:
    """Process a sales sheet from wide to tall format.

    Sales data structure (from debugging):
    - Row 1: Column headers (Locality, 2013, 2014, etc.)
    - Row 4+: Data starting with suburb names
    - Simpler structure than rental
    """
    sheet_name = sheet_info["sheet_name"]
    log.info(f"  Processing sales sheet: {sheet_name}")

    # Read the sheet, header is on row 1 (0-indexed)
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=1)

    # Drop completely empty rows
    df = df.dropna(how='all')

    # First column is suburb name
    df = df.rename(columns={df.columns[0]: "geospatial_id"})

    # Clean up the data - remove empty rows and header-like rows
    df = df[df["geospatial_id"].notna()]
    df = df[df["geospatial_id"] != ""]

    # Select only year columns (should be numeric column names like 2013, 2014, etc.)
    year_cols = []
    for col in df.columns[1:]:  # Skip the first column (location)
        try:
            # Check if column name is a year (numeric and reasonable range)
            year = int(float(col))
            if 2000 <= year <= 2030:
                year_cols.append(col)
        except (ValueError, TypeError):
            continue

    if not year_cols:
        log.warning(f"No year columns found in {sheet_name}")
        return pd.DataFrame()

    # Melt to tall format
    df_melted = df.melt(
        id_vars=["geospatial_id"],
        value_vars=year_cols,
        var_name="time_bucket",
        value_name="value"
    )

    # Clean up the data
    df_melted = df_melted.dropna(subset=["value"])
    df_melted = df_melted[df_melted["value"] != ""]

    # Parse and format time_bucket for all rows
    time_data = df_melted["time_bucket"].apply(parse_time_bucket)
    df_melted["time_bucket"] = [t[0] for t in time_data]
    df_melted["time_bucket_type"] = [t[1] for t in time_data]

    # Add metadata
    df_melted["dwelling_type"] = normalize_dwelling_type(sheet_info.get("dwelling_type"))
    df_melted["bedrooms"] = sheet_info.get("bedrooms")  # Often None for sales
    df_melted["geospatial_type"] = sheet_info.get("geospatial_type")
    df_melted["value_type"] = "sales"

    # Clean up geospatial_id
    df_melted["geospatial_id"] = df_melted["geospatial_id"].astype(str).str.strip()

    # Select final columns in the right order
    final_columns = ["value", "time_bucket", "time_bucket_type", "value_type", "dwelling_type",
                     "bedrooms", "geospatial_type", "geospatial_id"]

    return df_melted[final_columns]


def normalize_dwelling_type(dwelling_type: str) -> str:
    """Normalize dwelling types - convert Flat to Unit."""
    if not dwelling_type:
        return "All"

    dwelling = str(dwelling_type).strip()
    # Normalize Flat to Unit
    if dwelling.lower() == "flat":
        dwelling = "Unit"

    return dwelling.replace(" ", "_")


def parse_time_bucket(time_str: str) -> tuple[str, str]:
    """Parse time bucket string and return (formatted_time, time_type).

    Examples:
    - 'Sep 2003' -> ('2003-09', 'monthly')
    - 'Mar 2020' -> ('2020-03', 'quarterly')
    - '2013' -> ('2013', 'annually')
    """
    if not time_str or pd.isna(time_str):
        return None, None

    time_str = str(time_str).strip()

    # Month abbreviations mapping
    month_map = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }

    # Try to match "Month Year" pattern (e.g., "Sep 2003")
    month_year_match = re.match(r'^([a-zA-Z]{3})\s+(\d{4})$', time_str)
    if month_year_match:
        month_abbr, year = month_year_match.groups()
        month_num = month_map.get(month_abbr.lower())
        if month_num:
            # Determine if this is quarterly based on month
            quarterly_months = {'mar': '03', 'jun': '06', 'sep': '09', 'dec': '12'}
            time_type = 'quarterly' if month_abbr.lower() in quarterly_months else 'monthly'
            return f"{year}-{month_num}", time_type

    # Try to match year only pattern (e.g., "2013")
    year_match = re.match(r'^(\d{4})$', time_str)
    if year_match:
        return time_str, 'annually'

    # If no pattern matches, return as-is with unknown type
    return time_str, 'unknown'


def determine_time_bucket_type(df: pd.DataFrame) -> str:
    """Determine predominant time bucket type from data."""
    if 'time_bucket_type' in df.columns and not df['time_bucket_type'].isna().all():
        # Use existing time_bucket_type if available
        most_common = df['time_bucket_type'].mode()
        if len(most_common) > 0 and pd.notna(most_common.iloc[0]):
            return str(most_common.iloc[0])

    # Fallback: analyze time_bucket format
    if 'time_bucket' in df.columns:
        sample_buckets = df['time_bucket'].dropna().head(10)
        quarterly_pattern = re.compile(r'^\d{4}-(?:03|06|09|12)$')
        monthly_pattern = re.compile(r'^\d{4}-\d{2}$')
        annual_pattern = re.compile(r'^\d{4}$')

        quarterly_count = sum(1 for bucket in sample_buckets if quarterly_pattern.match(str(bucket)))
        monthly_count = sum(1 for bucket in sample_buckets if monthly_pattern.match(str(bucket)))
        annual_count = sum(1 for bucket in sample_buckets if annual_pattern.match(str(bucket)))

        if quarterly_count > monthly_count and quarterly_count > annual_count:
            return 'quarterly'
        elif monthly_count > annual_count:
            return 'monthly'
        else:
            return 'annually'

    return 'unknown'


def generate_output_filename(sheet_info: dict, file_type: str, time_bucket_type: str) -> str:
    """Generate standardized output filename following new schema.

    Format: <value_type>_<geospatial_type>_<time_bucket_type>_<dwelling_type>_<bedrooms>bedrooms
    """
    value_type = "rent" if file_type == "rental" else "sales"
    dwelling = normalize_dwelling_type(sheet_info.get("dwelling_type"))
    bedrooms = sheet_info.get("bedrooms") or "All"
    geo_type = sheet_info.get("geospatial_type", "UNKNOWN")

    return f"{value_type}_{geo_type}_{time_bucket_type}_{dwelling}_{bedrooms}bedrooms.csv"


def main(dry_run: bool = False, force: bool = False, limit: int = None):
    """Main processing function."""

    # Check cache
    cache_status = check_cache(CACHE_DIR, ALL_INPUTS, CACHE_TIMEOUT, force=force)
    if _is_cache_valid(cache_status):
        log.info("Cache is valid, skipping processing.")
        return

    log.info("Starting rental and sales Excel processing...")
    setup_directories()

    # Load configuration from discovery
    config = load_config()
    file_mappings = config.get("file_mappings", {})

    processed_count = 0
    csv_files_created = []
    manifest = {
        "generated_date": datetime.now().isoformat(),
        "csv_files": []
    }

    # Process each file
    for file_name, file_info in file_mappings.items():
        if limit and processed_count >= limit:
            break

        file_type = file_info["file_type"]
        file_path = DATA_DIR / "originals" / file_type / file_name

        if not file_path.exists():
            log.warning(f"File not found: {file_path}")
            continue

        log.info(f"\\nProcessing {file_type} file: {file_name}")

        # Process each sheet
        for sheet_info in file_info["sheets"]:
            if sheet_info.get("dwelling_type") is None and sheet_info.get("sheet_name") == "All properties":
                log.info(f"  Skipping 'All properties' sheet")
                continue

            try:
                # Process based on file type
                if file_type == "rental":
                    df = process_rental_sheet(file_path, sheet_info)
                else:
                    df = process_sales_sheet(file_path, sheet_info)

                # Determine time bucket type from processed data
                time_bucket_type = determine_time_bucket_type(df)

                # Generate output filename
                output_filename = generate_output_filename(sheet_info, file_type, time_bucket_type)
                output_path = CSV_DIR / output_filename

                # Save CSV (or simulate in dry run)
                if dry_run:
                    log.info(f"    DRY RUN: Would save {len(df)} rows to {output_filename}")
                else:
                    df.to_csv(output_path, index=False)
                    log.info(f"    ✓ Saved {len(df)} rows to {output_filename}")
                    csv_files_created.append(output_path)

                    # Add to manifest
                    manifest["csv_files"].append({
                        "filename": output_filename,
                        "file_path": str(output_path.relative_to(PROJECT_ROOT)),
                        "rows": len(df),
                        "value_type": "rent" if file_type == "rental" else "sales",
                        "dwelling_type": normalize_dwelling_type(sheet_info.get("dwelling_type")),
                        "bedrooms": sheet_info.get("bedrooms"),
                        "geospatial_type": sheet_info.get("geospatial_type", "UNKNOWN"),
                        "time_bucket_type": time_bucket_type,
                        "source_file": file_name,
                        "source_sheet": sheet_info["sheet_name"]
                    })

                    # Cache the result
                    cache_file = CACHE_DIR / output_filename
                    df.to_csv(cache_file, index=False)

                processed_count += 1

            except Exception as e:
                log.error(f"    ✗ Error processing sheet {sheet_info['sheet_name']}: {e}")

    log.info(f"\\nProcessing complete: {processed_count} sheets processed")
    log.info(f"Created {len(csv_files_created)} CSV files")

    # Save manifest file
    if not dry_run:
        manifest_path = CSV_DIR / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        log.info(f"Saved manifest to {manifest_path.relative_to(PROJECT_ROOT)}")

    # TODO: GeoJSON generation will be added in Spec 08
    log.info("Note: GeoJSON generation will be implemented in Spec 08")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent(f"""\
        {SCRIPT_NAME} - Process rental/sales Excel files to CSV format.

        Transforms 6 Excel files (18 sheets) from wide to tall format.
        Part of Specs 02-09 implementation.

        INPUTS:
        {_format_file_list(ALL_INPUTS)}

        OUTPUTS:
        - 18 CSV files in data/processed/rental_sales/csv/
        - 18 GeoJSON files in data/processed/rental_sales/geojson/ (TODO)

        CACHE: tmp/claude_cache/{SCRIPT_NAME}/
        """)
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Show only errors")
    parser.add_argument("-f", "--force", action="store_true", help="Force reprocessing, ignoring cache")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Run without writing outputs")
    parser.add_argument("--cache-check", action="store_true", help="Check cache status only")
    parser.add_argument("-L", "--limit", type=int, help="Process only first N sheets")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.ERROR if args.quiet else logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if args.cache_check:
        delta, remaining = check_cache(CACHE_DIR, ALL_INPUTS, CACHE_TIMEOUT, force=args.force)
        if _is_cache_valid((delta, remaining)):
            log.info(f"Cache is up to date. Delta: {delta}s, Remaining: {remaining}s")
        else:
            log.warning(f"Cache is not up to date. Delta: {delta}s, Remaining: {remaining}s")
    else:
        main(dry_run=args.dry_run, force=args.force, limit=args.limit)
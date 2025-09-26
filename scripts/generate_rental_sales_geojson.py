#!/usr/bin/env python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pandas",
#   "geopandas",
#   "pyarrow"
# ]
# ///
"""
generate_rental_sales_csv - Process rental/sales CSV files with postcode mapping.

Processes rental/sales CSV files by adding postcode information for SUBURB data
and standardizing column ordering and naming conventions across all files.
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
CSV_INPUT_DIR = DATA_DIR / "processed" / "rental_sales" / "csv"
CSV_OUTPUT_DIR = DATA_DIR / "processed" / "rental_sales" / "csv_processed"
CACHE_DIR = PROJECT_ROOT / "tmp" / "claude_cache" / SCRIPT_NAME

# Boundary datasets for postcode mapping (using Victoria-specific data)
BOUNDARY_DIR = DATA_DIR / "originals_converted" / "boundaries_victoria"
SUBURB_BOUNDARY = BOUNDARY_DIR / "SA2_2021_AUST_SHP_GDA2020"
LGA_BOUNDARY = BOUNDARY_DIR / "LGA_2024_AUST_GDA2020"
POSTCODE_BOUNDARY = BOUNDARY_DIR / "POA_2021_AUST_GDA2020_SHP"

# Cache timeout (5 minutes default)
CACHE_TIMEOUT = 300

# Standard column order for all output CSVs
STANDARD_COLUMNS = [
    'value', 'time_bucket', 'time_bucket_type', 'value_type',
    'dwelling_type', 'bedrooms', 'geospatial_type', 'geospatial_id', 'postcode'
]

# Boundary mappings
BOUNDARY_MAPPINGS = {
    'SUBURB': {
        'source': SUBURB_BOUNDARY,
        'id_field': 'SA2_NAME21',
        'geometry_field': 'geometry',
        'file_name': 'SA2_2021_AUST_SHP_GDA2020'
    },
    'LGA': {
        'source': LGA_BOUNDARY,
        'id_field': 'LGA_NAME24',
        'geometry_field': 'geometry',
        'file_name': 'LGA_2024_AUST_GDA2020'
    },
    'POSTCODE': {
        'source': POSTCODE_BOUNDARY,
        'id_field': 'POA_NAME21',
        'geometry_field': 'geometry',
        'file_name': 'POA_2021_AUST_GDA2020'
    }
}

# Helper lambdas
_is_cache_valid = lambda time_tuple: all(x > 0 for x in time_tuple)  # noqa: E731
_format_file_list = lambda files, max_show=3: '\\n        '.join(  # noqa: E731
    f"- {p.relative_to(PROJECT_ROOT)}" for p in files[:max_show]
) + (f"\\n        ... and {len(files) - max_show} more files" if len(files) > max_show else "")


def check_cache(cache_dir: Path, input_files: list[Path], timeout: int = 300, force: bool = False) -> tuple[int, int]:
    """Check if cache is invalid, 'dirty' or expired."""
    if force or not cache_dir.exists():
        return (-1, -1)  # Both negative = forced dirty

    cache_mtime = max([0] + [f.stat().st_mtime for f in cache_dir.rglob('*') if f.is_file()])
    input_mtime = max([0] + [f.stat().st_mtime for f in input_files if f.is_file()])

    delta = int(cache_mtime - input_mtime)
    remaining = int(timeout - (time() - cache_mtime))

    return (delta, remaining)


def setup_directories():
    """Ensure output directories exist."""
    for dir_path in [CACHE_DIR, CSV_OUTPUT_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


def load_postcode_mapping():
    """Load postcode mapping data for spatial joins."""
    log.info("Loading postcode mapping data...")

    # Load SA2 (suburb) boundaries - try different file patterns
    sa2_files_to_try = [
        SUBURB_BOUNDARY / "SA2_2021_AUST_GDA2020.parquet",
        SUBURB_BOUNDARY / "SA2_2021_AUST_SHP_GDA2020.parquet",
        SUBURB_BOUNDARY / "SA2_2021_AUST_GDA2020.geojson",
        SUBURB_BOUNDARY / "SA2_2021_AUST_SHP_GDA2020.geojson",
    ]

    sa2_gdf = None
    for sa2_file in sa2_files_to_try:
        if sa2_file.exists():
            try:
                sa2_gdf = gpd.read_parquet(sa2_file) if sa2_file.suffix == '.parquet' else gpd.read_file(sa2_file)
                log.info(f"Loaded {len(sa2_gdf)} SA2 boundaries from {sa2_file.name}")
                break
            except Exception as e:
                log.warning(f"Failed to load {sa2_file}: {e}")
                continue

    if sa2_gdf is None:
        raise FileNotFoundError(f"No SA2 boundary file found at {SUBURB_BOUNDARY}")

    # Load POA (postcode) boundaries - try different file patterns
    poa_files_to_try = [
        POSTCODE_BOUNDARY / "POA_2021_AUST_GDA2020.parquet",
        POSTCODE_BOUNDARY / "POA_2021_AUST_GDA2020_SHP.parquet",
        POSTCODE_BOUNDARY / "POA_2021_AUST_GDA2020.geojson",
        POSTCODE_BOUNDARY / "POA_2021_AUST_GDA2020_SHP.geojson",
    ]

    poa_gdf = None
    for poa_file in poa_files_to_try:
        if poa_file.exists():
            try:
                poa_gdf = gpd.read_parquet(poa_file) if poa_file.suffix == '.parquet' else gpd.read_file(poa_file)
                log.info(f"Loaded {len(poa_gdf)} postcode boundaries from {poa_file.name}")
                break
            except Exception as e:
                log.warning(f"Failed to load {poa_file}: {e}")
                continue

    if poa_gdf is None:
        raise FileNotFoundError(f"No postcode boundary file found at {POSTCODE_BOUNDARY}")

    # Create spatial join between SA2 and POA to map suburbs to postcodes
    log.info("Creating suburb to postcode mapping...")
    mapping = gpd.sjoin(sa2_gdf, poa_gdf, how='left', predicate='intersects')

    # Create clean mapping dictionary - SA2_NAME21 to POA_NAME21
    suburb_postcode_map = {}
    for _, row in mapping.iterrows():
        suburb_name = str(row['SA2_NAME21']).strip().upper()
        postcode = str(row['POA_NAME21']).strip() if pd.notna(row.get('POA_NAME21')) else None
        if suburb_name and postcode:
            suburb_postcode_map[suburb_name] = postcode

    log.info(f"Created mapping for {len(suburb_postcode_map)} suburbs to postcodes")
    return suburb_postcode_map


def standardize_names(names):
    """Standardize geographic names for matching."""
    if isinstance(names, pd.Series):
        return names.str.upper().str.strip().str.replace(r'[^A-Z0-9\s]', '', regex=True)
    else:
        return str(names).upper().strip()


def add_postcode_column(df: pd.DataFrame, suburb_postcode_map: dict) -> pd.DataFrame:
    """Add postcode column to dataframe based on geospatial_id for SUBURB type."""
    df = df.copy()

    if 'geospatial_type' in df.columns and df['geospatial_type'].iloc[0] == 'SUBURB':
        # Map suburbs to postcodes with enhanced logic
        df['postcode'] = df['geospatial_id'].apply(
            lambda x: map_suburb_to_postcodes(x, suburb_postcode_map)
        )

        # Log mapping success rate
        mapped_count = df['postcode'].notna().sum()
        total_count = len(df)
        success_rate = mapped_count / total_count if total_count > 0 else 0
        log.info(f"  Postcode mapping success: {mapped_count}/{total_count} ({success_rate:.1%})")

        if success_rate < 0.8:
            log.warning(f"  Low postcode mapping success rate ({success_rate:.1%})")
            unmatched = df[df['postcode'].isna()]['geospatial_id'].unique()[:3]
            log.warning(f"  Examples of unmatched suburbs: {list(unmatched)}")
    else:
        # For LGA or other types, set postcode to None
        df['postcode'] = None

    return df


def standardize_column_order(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column order across all CSVs."""
    # Ensure all required columns exist
    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = None if col == 'postcode' else df.get(col, None)

    # Reorder columns
    return df[STANDARD_COLUMNS]


def map_suburb_to_postcodes(suburb_name: str, suburb_postcode_map: dict) -> str:
    """
    Map suburb name to postcodes, handling special cases:
    1. Filter out 'Group Total' (not a suburb)
    2. Handle multi-suburb entries like 'Vermont-Forest Hill-Burwood East'
    3. Return delimited list of postcodes for multi-suburb cases
    """
    if not suburb_name or pd.isna(suburb_name):
        return None

    suburb_name = str(suburb_name).strip()

    # Filter out non-suburb entries
    if suburb_name in ['Group Total', 'Total', '']:
        return None

    # Check if this is a multi-suburb entry (contains hyphens)
    if '-' in suburb_name:
        # Split by hyphens and look up each suburb
        suburb_parts = [part.strip() for part in suburb_name.split('-')]
        postcodes = []

        for part in suburb_parts:
            if part:  # Skip empty parts
                standardized_part = standardize_names(part)
                postcode = suburb_postcode_map.get(standardized_part)
                if postcode and postcode not in postcodes:
                    postcodes.append(postcode)

        # Return delimited list if we found any postcodes
        if postcodes:
            return '|'.join(sorted(postcodes))
        else:
            return None
    else:
        # Single suburb - standard lookup
        standardized_name = standardize_names(suburb_name)
        return suburb_postcode_map.get(standardized_name, None)


def parse_filename_components(filename: str) -> dict:
    """Parse CSV filename to extract components for new naming convention."""
    # Handle different existing naming patterns
    stem = Path(filename).stem

    # Pattern 1: value_type_dwelling_bedrooms_geospatial_type (new format)
    pattern1 = re.match(r'^(rent|sales)_([^_]+)_(\d+|All)bedrooms_([^_]+)$', stem)
    if pattern1:
        return {
            'value_type': pattern1.group(1),
            'dwelling_type': pattern1.group(2),
            'bedrooms': pattern1.group(3),
            'geospatial_type': pattern1.group(4),
            'time_bucket_type': None  # Will be determined from data
        }

    # Pattern 2: dwelling_bedrooms_geospatial_type_value_type (old format)
    pattern2 = re.match(r'^([^_]+)_(\d+|All)bed?(?:rooms?)?_([^_]+)_([^_]+)$', stem)
    if pattern2:
        return {
            'value_type': pattern2.group(4),
            'dwelling_type': pattern2.group(1),
            'bedrooms': pattern2.group(2),
            'geospatial_type': pattern2.group(3),
            'time_bucket_type': None
        }

    # Pattern 3: Other variations, try to extract from data
    log.warning(f"Could not parse filename pattern: {filename}")
    return None


def determine_time_bucket_type(df: pd.DataFrame) -> str:
    """Determine predominant time bucket type from data."""
    if 'time_bucket_type' in df.columns:
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


def generate_output_filename(components: dict, time_bucket_type: str) -> str:
    """Generate new filename following the required convention."""
    # Format: <value_type>_<geospatial_type>_<time_bucket_type>_<dwelling_type>_<bedrooms>bedrooms

    value_type = components['value_type']
    geospatial_type = components['geospatial_type']
    dwelling_type = components['dwelling_type']
    bedrooms = components['bedrooms']

    return f"{value_type}_{geospatial_type}_{time_bucket_type}_{dwelling_type}_{bedrooms}bedrooms.csv"


def process_csv_file(csv_file_path: Path, suburb_postcode_map: dict, dry_run: bool = False):
    """Process a single CSV file with postcode mapping and standardization."""

    csv_name = csv_file_path.stem
    log.info(f"Processing {csv_name}")

    try:
        # Load CSV data
        df = pd.read_csv(csv_file_path)

        if df.empty:
            log.warning(f"  Empty CSV file: {csv_name}")
            return None

        # Parse filename components
        components = parse_filename_components(csv_file_path.name)
        if not components:
            log.error(f"  Could not parse filename: {csv_name}")
            return None

        # Determine time bucket type
        time_bucket_type = determine_time_bucket_type(df)

        # Add postcode column
        df = add_postcode_column(df, suburb_postcode_map)

        # Standardize column order
        df = standardize_column_order(df)

        # Generate output filename
        output_filename = generate_output_filename(components, time_bucket_type)
        output_path = CSV_OUTPUT_DIR / output_filename

        if dry_run:
            log.info(f"    DRY RUN: Would create {output_filename} with {len(df)} rows")
            return None

        # Save processed CSV
        df.to_csv(output_path, index=False)
        log.info(f"    ✓ Created {output_filename} with {len(df)} rows")

        # Cache the result
        cache_file = CACHE_DIR / output_filename
        df.to_csv(cache_file, index=False)

        return output_path

    except Exception as e:
        log.error(f"    ✗ Error processing {csv_name}: {e}")
        return None


def load_manifest() -> dict:
    """Load the manifest.json file created by process_rental_sales_excel.py"""
    manifest_path = CSV_INPUT_DIR / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}. Run process_rental_sales_excel.py first")

    with open(manifest_path) as f:
        return json.load(f)


def process_csv_file_with_metadata(csv_file_path: Path, csv_metadata: dict, suburb_postcode_map: dict, dry_run: bool = False):
    """Process a single CSV file using manifest metadata."""

    csv_name = csv_file_path.stem
    log.info(f"Processing {csv_name}")

    try:
        # Load CSV data
        df = pd.read_csv(csv_file_path)

        if df.empty:
            log.warning(f"  Empty CSV file: {csv_name}")
            return None

        # Use metadata from manifest instead of parsing filename
        components = {
            'value_type': csv_metadata['value_type'],
            'geospatial_type': csv_metadata['geospatial_type'],
            'dwelling_type': csv_metadata['dwelling_type'],
            'bedrooms': csv_metadata['bedrooms'],
            'time_bucket_type': csv_metadata['time_bucket_type']
        }

        # Add postcode column
        df = add_postcode_column(df, suburb_postcode_map)

        # Standardize column order
        df = standardize_column_order(df)

        # Generate output filename
        output_filename = generate_output_filename(components, csv_metadata['time_bucket_type'])
        output_path = CSV_OUTPUT_DIR / output_filename

        if dry_run:
            log.info(f"    DRY RUN: Would create {output_filename} with {len(df)} rows")
            return None

        # Save processed CSV
        df.to_csv(output_path, index=False)
        log.info(f"    ✓ Created {output_filename} with {len(df)} rows")

        # Cache the result
        cache_file = CACHE_DIR / output_filename
        df.to_csv(cache_file, index=False)

        return {
            "output_path": output_path,
            "dataframe": df
        }

    except Exception as e:
        log.error(f"    ✗ Error processing {csv_name}: {e}")
        return None


def main(dry_run: bool = False, force: bool = False, limit: int = None):
    """Main processing function."""

    # Load manifest instead of scanning files
    try:
        manifest = load_manifest()
        csv_files_info = manifest.get("csv_files", [])
    except FileNotFoundError as e:
        log.error(str(e))
        return

    if not csv_files_info:
        log.error("No CSV files found in manifest")
        return

    if limit:
        csv_files_info = csv_files_info[:limit]

    # Check cache based on CSV input files
    csv_input_files = [PROJECT_ROOT / item["file_path"] for item in csv_files_info]
    cache_status = check_cache(CACHE_DIR, csv_input_files, CACHE_TIMEOUT, force=force)
    if _is_cache_valid(cache_status):
        log.info("Cache is valid, skipping processing.")
        return

    log.info(f"Starting CSV processing for {len(csv_files_info)} files...")
    log.info(f"Output format: <value_type>_<geospatial_type>_<time_bucket_type>_<dwelling_type>_<bedrooms>bedrooms")
    setup_directories()

    # Load postcode mapping
    try:
        suburb_postcode_map = load_postcode_mapping()
    except FileNotFoundError as e:
        log.error(f"Failed to load postcode mapping: {e}")
        return

    processed_count = 0
    output_files_created = []
    all_dataframes = []  # For concatenated CSV

    for csv_info in csv_files_info:
        if limit and processed_count >= limit:
            break

        csv_file_path = PROJECT_ROOT / csv_info["file_path"]
        result = process_csv_file_with_metadata(csv_file_path, csv_info, suburb_postcode_map, dry_run=dry_run)
        if result:
            output_files_created.append(result["output_path"])
            if result.get("dataframe") is not None:
                all_dataframes.append(result["dataframe"])

        processed_count += 1

    # Create concatenated CSV
    if not dry_run and all_dataframes:
        concatenated_df = pd.concat(all_dataframes, ignore_index=True)
        concat_path = CSV_OUTPUT_DIR / "all_rental_sales_data.csv"
        concatenated_df.to_csv(concat_path, index=False)
        log.info(f"Created concatenated CSV with {len(concatenated_df)} total rows: {concat_path.name}")

    log.info(f"\\nProcessing complete: {processed_count} files processed")
    log.info(f"Created {len(output_files_created)} processed CSV files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent(f"""\\
        {SCRIPT_NAME} - Process rental/sales CSV files with standardization.

        Processes CSV files by adding postcode mapping for SUBURB data and
        standardizing column ordering and naming conventions.

        INPUTS:
        - CSV files from data/processed/rental_sales/csv/
        - Boundary data from data/originals_converted/boundaries/

        OUTPUTS:
        - Processed CSV files in data/processed/rental_sales/csv_processed/
        - New naming: <value_type>_<geospatial_type>_<time_bucket_type>_<dwelling_type>_<bedrooms>bedrooms

        CACHE: tmp/claude_cache/{SCRIPT_NAME}/
        """)
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Show only errors")
    parser.add_argument("-f", "--force", action="store_true", help="Force reprocessing, ignoring cache")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Run without writing outputs")
    parser.add_argument("--cache-check", action="store_true", help="Check cache status only")
    parser.add_argument("-L", "--limit", type=int, help="Process only first N files")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.ERROR if args.quiet else logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if args.cache_check:
        csv_files = sorted(CSV_INPUT_DIR.glob("*.csv"))
        delta, remaining = check_cache(CACHE_DIR, csv_files, CACHE_TIMEOUT, force=args.force)
        if _is_cache_valid((delta, remaining)):
            log.info(f"Cache is up to date. Delta: {delta}s, Remaining: {remaining}s")
        else:
            log.warning(f"Cache is not up to date. Delta: {delta}s, Remaining: {remaining}s")
    else:
        main(dry_run=args.dry_run, force=args.force, limit=args.limit)
#!/usr/bin/env python3
"""
Export shapefiles from data subdirectories to GeoJSON format.
This script scans the data/ directory for SHP files and converts them to GeoJSON.
"""

# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas>=0.14.0",
#   "requests",
#   "python-dotenv>=1.0.0",
#   "tqdm>=4.66.1",
#   "pyarrow",
# ]
# ///
import argparse
import logging
from pathlib import Path

import geopandas as gpd
from dotenv import load_dotenv
from tqdm import tqdm
from utils import dirty, unzip_archive

# Load environment variables from .env file
load_dotenv()

log = logging.getLogger(__name__)

# Constants
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR.parent / "data/originals"
OUTPUT_DIR = SCRIPT_DIR.parent / "data/originals_converted/"

BOUNDARY_DIR = DATA_DIR / "boundaries"


def find_shapefiles(data_dir: Path) -> list[Path]:
    """
    Find all .shp files in the data directory and its subdirectories.

    Args:
        data_dir: Path to the data directory

    Returns:
        List of paths to shapefiles
    """
    log.info(f"Searching for shapefiles in {data_dir}")

    # Find all .shp files in the data directory and its subdirectories
    shapefiles = list(data_dir.glob("**/*.shp"))

    # Log the results
    if shapefiles:
        for shp in shapefiles:
            log.info(f"Found shapefile: {shp} {shp.stat().st_size / 1024 / 1024:.2f}Mb")
    else:
        log.warning(f"No shapefiles found in {data_dir} or its subdirectories")

    return shapefiles


def export_shapefile_to_geojson(
    shapefile_path: Path,
    output_dir: Path,
    simplify_tolerance: float | None = None,
    filter_columns: list[str] | None = None,
) -> Path:
    """
    Export a shapefile to GeoJSON.

    Args:
        shapefile_path: Path to the shapefile
        output_dir: Directory to save the GeoJSON file
        simplify_tolerance: Tolerance for geometry simplification (in degrees)
        filter_columns: Columns to keep in the output (all if None)

    Returns:
        Path to the exported GeoJSON file
    """
    try:
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate output file path
        relative_shapefile_path = shapefile_path.relative_to(DATA_DIR).parent
        output_file = output_dir / relative_shapefile_path / f"{shapefile_path.stem}.geojson"

        # Guard condition to skip if up to date
        if not dirty(output_file, shapefile_path):
            log.info(
                f"Found shapefile: {shapefile_path} {shapefile_path.stat().st_size / 1024 / 1024:.2f}Mb"
            )
            log.info(
                f"Found existing up-to-date output_file: {output_file} {output_file.stat().st_size / 1024 / 1024:.2f}Mb"
            )
            geoparquet_path = output_file.with_suffix(".parquet")
            log.info(
                f"Found existing up-to-date geoparquet_file: {geoparquet_path} {geoparquet_path.stat().st_size / 1024 / 1024:.2f}Mb"
            )

            return output_file

        log.info(
            f"Reading shapefile: {shapefile_path} {shapefile_path.stat().st_size / 1024 / 1024:.2f}Mb"
        )

        # Read the shapefile with geopandas
        gdf = gpd.read_file(shapefile_path)

        # Log the number of features and CRS
        log.info(f"Read {len(gdf)} features with CRS: {gdf.crs}")

        # Ensure CRS is WGS84 for web compatibility
        if gdf.crs != "EPSG:4326":
            log.info(f"Reprojecting from {gdf.crs} to EPSG:4326 (WGS84)")
            gdf = gdf.to_crs("EPSG:4326")

        # Apply simplification if requested
        if simplify_tolerance is not None and simplify_tolerance > 0:
            log.info(f"Simplifying geometries with tolerance: {simplify_tolerance}")
            original_size = gdf.memory_usage(deep=True).sum()
            gdf["geometry"] = gdf["geometry"].simplify(simplify_tolerance, preserve_topology=True)
            new_size = gdf.memory_usage(deep=True).sum()
            reduction = (original_size - new_size) / original_size * 100
            log.info(f"Simplification reduced size by approximately {reduction:.2f}%")

        # Filter columns if requested
        if filter_columns:
            available_columns = set(gdf.columns)
            requested_columns = set(filter_columns + ["geometry"])  # Always keep geometry
            valid_columns = list(available_columns.intersection(requested_columns))

            if valid_columns:
                log.info(f"Filtering to columns: {valid_columns}")
                gdf = gdf[valid_columns]
            else:
                log.warning("No requested columns found in dataset, keeping all columns")

        # Export to GeoJSON
        log.info(f"Exporting to GeoJSON: {output_file}")
        output_file.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent directory exists
        gdf.to_file(output_file, driver="GeoJSON")
        gdf.to_parquet(output_file.with_suffix(".parquet"), engine="pyarrow", index=False)

        log.info(f"Successfully exported to {output_file}")
        return output_file

    except Exception as e:
        log.error(f"Error exporting shapefile {shapefile_path}: {str(e)}")
        raise


def process_shapefiles(
    data_dir: Path = DATA_DIR,
    output_dir: Path = OUTPUT_DIR,
    simplify_tolerance: float | None = None,
    filter_by_suffix: str | None = None,
) -> list[Path]:
    """
    Process all shapefiles in the data directory and export them to GeoJSON.

    Args:
        data_dir: Path to the data directory
        output_dir: Directory to save the GeoJSON files
        simplify_tolerance: Tolerance for geometry simplification (in degrees)
        filter_by_suffix: Only process files with this suffix

    Returns:
        List of paths to exported GeoJSON files
    """
    # Find all shapefiles
    shapefiles = find_shapefiles(data_dir)

    # Filter by suffix if requested
    if filter_by_suffix:
        shapefiles = [shp for shp in shapefiles if shp.name.endswith(filter_by_suffix)]
        log.info(f"Filtered to {len(shapefiles)} shapefiles ending with '{filter_by_suffix}'")

    if not shapefiles:
        log.warning("No shapefiles to process")
        return []

    exported_files = []

    # Process each shapefile with a progress bar
    for shapefile in tqdm(shapefiles, desc="Exporting shapefiles"):
        try:
            geojson_path = export_shapefile_to_geojson(shapefile, output_dir, simplify_tolerance)
            exported_files.append(geojson_path)
        except Exception as e:
            log.error(f"Failed to export {shapefile}: {e}")

    log.info(f"Successfully exported {len(exported_files)} of {len(shapefiles)} shapefiles")
    return exported_files


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Export shapefiles to GeoJSON format")
    parser.add_argument(
        "--data-dir", default=DATA_DIR, type=Path, help="Data directory containing shapefiles"
    )
    parser.add_argument(
        "--output-dir", default=OUTPUT_DIR, type=Path, help="Output directory for GeoJSON files"
    )
    parser.add_argument(
        "--simplify", type=float, help="Tolerance for geometry simplification (in degrees)"
    )
    parser.add_argument("--filter-suffix", type=str, help="Only process files with this suffix")
    parser.add_argument("--single-file", type=str, help="Process only this specific shapefile")

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    args.output_dir.mkdir(parents=True, exist_ok=True)

    ZIP_FILES = list(BOUNDARY_DIR.glob("*.zip"))
    print(f"Found {len(ZIP_FILES)} zip files in {BOUNDARY_DIR} {ZIP_FILES=}")
    for zip_file in tqdm(ZIP_FILES, desc="Unzipping archives"):
        unzip_archive(zip_file)

    if args.single_file:
        # Process a single file
        single_file_path = Path(args.single_file)
        if not single_file_path.exists():
            log.error(f"Shapefile not found: {args.single_file}")
        else:
            try:
                export_shapefile_to_geojson(single_file_path, args.output_dir, args.simplify)
            except Exception as e:
                log.error(f"Error processing file: {e}")
    else:
        # Process all files
        process_shapefiles(args.data_dir, args.output_dir, args.simplify, args.filter_suffix)

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
from tqdm import tqdm
from utils import dirty, unzip_archive


_file_size = lambda p: f"{p.stat().st_size / 1024 / 1024:.2f}Mb"

log = logging.getLogger(__name__)

# Constants
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR.parent / "data/originals"
OUTPUT_DIR = SCRIPT_DIR.parent / "data/originals_converted/"

BOUNDARY_DIR = DATA_DIR / "boundaries"

ALL_INPUTS = [BOUNDARY_DIR]
ALL_OUTPUTS = [OUTPUT_DIR]

def export_shapefile_to_geojson(
    shapefile_path: Path,
    output_dir: Path,
    simplify_tolerance: float | None = None,
    force: bool = False,
) -> Path:
    """
    Export a shapefile to GeoJSON.

    Args:
        shapefile_path: Path to the shapefile
        output_dir: Directory to save the GeoJSON file
        simplify_tolerance: Tolerance for geometry simplification (in degrees)

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
        if not dirty(output_file, shapefile_path) and not force:
            log.info(
                f"Found shapefile: {relative_shapefile_path} {_file_size(shapefile_path)}"
            )
            log.info(
                f"Found existing up-to-date output_file: {output_file.relative_to(OUTPUT_DIR)} {_file_size(output_file)}"
            )
            geoparquet_path = output_file.with_suffix(".parquet")
            log.info(
                f"Found existing up-to-date geoparquet_file: {geoparquet_path.relative_to(OUTPUT_DIR)} {_file_size(geoparquet_path)}"
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
    force: bool = False,
) -> list[Path]:
    """
    Process all shapefiles in the data directory and export them to GeoJSON.

    Args:
        data_dir: Path to the data directory
        output_dir: Directory to save the GeoJSON files
        simplify_tolerance: Tolerance for geometry simplification (in degrees)

    Returns:
        List of paths to exported GeoJSON files
    """
    # Find all shapefiles
    shapefiles = list(data_dir.glob("**/*.shp"))


    if not shapefiles:
        log.warning("No shapefiles to process")
        return []

    exported_files = []

    # Process each shapefile with a progress bar
    for shapefile in tqdm(shapefiles, desc="Exporting shapefiles"):
        try:
            geojson_path = export_shapefile_to_geojson(shapefile, output_dir, simplify_tolerance, force)
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
    parser.add_argument("--force", action="store_true", help="Force re-exporting all shapefiles")

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # If there are any zip files in the source directory, unzip them first
    ZIP_FILES = list(args.data_dir.glob("*.zip"))
    log.info(f"Found {len(ZIP_FILES)} zip files in {args.data_dir} {ZIP_FILES=}")
    for zip_file in tqdm(ZIP_FILES, desc="Unzipping archives"):
        unzip_archive(zip_file)


    process_shapefiles(args.data_dir, args.output_dir, args.simplify, args.force)

#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas",
#   "pandas",
#   "pyarrow",
#   "pyogrio",
#   "shapely",
#   "tqdm",
#   "requests"
# ]
# ///

"""
Filter Australian boundary data to only include features within a specified state.

This script iterates through all parquet files in the boundaries directory,
loads each one with geopandas, and filters them to keep only the features
that intersect with the specified state polygon. The filtered results are
saved to a new boundaries_{state} directory, preserving the original
directory structure.

Usage:
    uv run scripts/extract_boundaries_state.py [--state STATE] [--dry-run] [--limit N]
    
Options:
    --state STATE State name to filter by (default: Victoria)
    --dry-run     Show what would be processed without actually processing
    --limit N     Process only the first N files (for testing)
    --verbose     Enable detailed logging

Available states:
    Victoria, New South Wales, Queensland, Western Australia, South Australia,
    Tasmania, Northern Territory, Australian Capital Territory
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from utils import dirty

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

# Configure logging

log = logging.getLogger(__name__)

STATE_POLYGONS_FILE = Path("data/originals_converted/state_polygons/australian_states.parquet")
INPUT_DIR = Path("data/originals_converted/boundaries")

class StateBoundaryFilter:
    """Filter boundary data to specified state boundaries."""
    
    def __init__(self, state_name: str = "Victoria", dry_run: bool = False, verbose: bool = False):
        """Initialize the filter with configuration options.
        
        Args:
            state_name: Name of the state to filter by (default: Victoria)
            dry_run: If True, show what would be done without processing
            verbose: If True, enable detailed logging
        """
        self.state_name = state_name
        self.dry_run = dry_run
        self.verbose = verbose
        
        if self.verbose:
            log.setLevel(logging.DEBUG)
        
        
        
        # Create output dir name based on state (lowercase, replace spaces with underscores)
        state_folder = state_name.lower().replace(' ', '_')
        self.output_dir = Path(f"data/originals_converted/boundaries_{state_folder}")
        
        # Will be loaded on first use
        self.state_polygon = None
        self.state_gdf = None
        
    def load_state_polygon(self) -> gpd.GeoDataFrame:
        """Load the specified state polygon from the states file.
        
        Returns:
            GeoDataFrame containing only the specified state polygon
        """
        if self.state_gdf is not None:
            return self.state_gdf
            
        log.info(f"Loading {self.state_name} state polygon...")
        
        if not STATE_POLYGONS_FILE.exists():
            raise FileNotFoundError(f"State polygons file not found: {STATE_POLYGONS_FILE}")
        
        # Load state polygons
        states_gdf = gpd.read_parquet(STATE_POLYGONS_FILE)
        log.debug(f"Loaded {len(states_gdf)} state polygons")
        available_states = sorted(states_gdf['STE_NAME21'].unique())
        log.debug(f"Available states: {available_states}")
        
        # Filter for specified state
        state_gdf = states_gdf[states_gdf['STE_NAME21'] == self.state_name].copy()
        
        if state_gdf.empty:
            raise ValueError(f"{self.state_name} polygon not found in state polygons file. Available states: {', '.join(available_states)}")
        
        log.info(f"{self.state_name} polygon loaded, CRS: {state_gdf.crs}")
        
        # Store both the GeoDataFrame and the geometry for intersection
        self.state_gdf = state_gdf
        self.state_polygon = state_gdf.geometry.iloc[0]
        
        return state_gdf
    
    def find_parquet_files(self) -> list[Path]:
        """Find all parquet files in the boundaries directory.
        
        Returns:
            List of paths to parquet files
        """
        parquet_files = list(INPUT_DIR.rglob("*.parquet"))
        log.info(f"Found {len(parquet_files)} parquet files in {INPUT_DIR}")
        return parquet_files
    
    def process_boundary_file(self, input_file: Path) -> Optional[int]:
        """Process a single boundary file, filtering to specified state.
        
        Args:
            input_file: Path to the input parquet file
            
        Returns:
            Number of features kept after filtering, or None if error
        """
        try:
            # Determine output path (preserve directory structure)
            relative_path = input_file.relative_to(INPUT_DIR)
            output_file = self.output_dir / relative_path
            
            # Create output directory if needed
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            log.info(f"Processing: {relative_path}")
            
            if self.dry_run:
                log.info(f"  [DRY RUN] Would filter to: {output_file}")
                return 0
            
            # Load the boundary data
            log.debug(f"  Loading {input_file}...")
            gdf = gpd.read_parquet(input_file)
            original_count = len(gdf)
            log.debug(f"  Loaded {original_count} features, CRS: {gdf.crs}")
            
            # Skip if empty
            if gdf.empty:
                log.warning(f"  Empty dataset, skipping")
                return 0
            
            # Ensure state polygon is in the same CRS as the data
            state_polygon_reprojected = self.state_gdf.to_crs(gdf.crs)
            
            # Filter to features that intersect with state
            log.debug(f"  Filtering to {self.state_name} boundaries...")
            
            # Use spatial index for efficient intersection
            state_mask = gdf.intersects(state_polygon_reprojected.geometry.iloc[0])
            filtered_gdf = gdf[state_mask].copy()
            
            filtered_count = len(filtered_gdf)
            log.info(f"  Kept {filtered_count}/{original_count} features ({filtered_count/original_count*100:.1f}%)")
            
            # Save filtered data if there are any features
            if filtered_count > 0:
                log.debug(f"  Saving to {output_file}...")
                filtered_gdf.to_parquet(output_file)
                log.info(f"  Saved {filtered_count} features to {output_file}")
            else:
                log.warning(f"  No features in {self.state_name}, skipping file creation")
            
            return filtered_count
            
        except Exception as e:
            log.error(f"  Error processing {input_file}: {e}")
            if self.verbose:
                import traceback
                log.debug(traceback.format_exc())
            return None
    
    def process_all(self, limit: Optional[int] = None):
        """Process all boundary files.
        
        Args:
            limit: If specified, process only the first N files
        """
        # Load state polygon first
        self.load_state_polygon()
        
        # Find all parquet files
        parquet_files = self.find_parquet_files()
        output_files = [self.output_dir / f.relative_to(INPUT_DIR) for f in parquet_files]
        
        if not parquet_files:
            log.warning("No parquet files found to process")
            return

        if not dirty(output_files, parquet_files):
            log.info("All output files are up-to-date. No work to do.")
            return
        
        # Apply limit if specified
        if limit:
            parquet_files = parquet_files[:limit]
            log.info(f"Limited to processing {len(parquet_files)} files")
        
        # Process statistics
        total_files = len(parquet_files)
        successful = 0
        failed = 0
        total_features_kept = 0
        
        # Process each file
        for i, input_file in enumerate(parquet_files, 1):
            log.info(f"\n[{i}/{total_files}] Processing file...")
            result = self.process_boundary_file(input_file)
            
            if result is not None:
                successful += 1
                total_features_kept += result
            else:
                failed += 1
        
        # Summary
        log.info("\n" + "="*60)
        log.info("Processing Complete")
        log.info(f"State: {self.state_name}")
        log.info(f"Output Directory: {self.output_dir}")
        log.info(f"Files processed: {total_files}")
        log.info(f"Successful: {successful}")
        log.info(f"Failed: {failed}")
        log.info(f"Total features kept: {total_features_kept}")
        
        if self.dry_run:
            log.info("[DRY RUN] No files were actually processed")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Filter Australian boundary data to specified state boundaries",
        epilog="""
Available states:
  Victoria                    (default)
  New South Wales
  Queensland
  Western Australia
  South Australia
  Tasmania
  Northern Territory
  Australian Capital Territory
  Other Territories
  Outside Australia

Example usage:
  uv run scripts/extract_boundaries_by_state.py --state "New South Wales" --limit 5
  uv run scripts/extract_boundaries_by_state.py --state Tasmania --dry-run
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--state",
        default="Victoria",
        help="State name to filter by (default: Victoria)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually processing"
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Process only the first N files (for testing)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging"
    )
    
    args = parser.parse_args()
    # Create and run the filter
    filter = StateBoundaryFilter(
        state_name=args.state,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    filter.process_all(limit=args.limit)



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
    )
    main()
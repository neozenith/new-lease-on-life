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
Extract and union state polygons from SA4 boundaries.

This script loads SA4 (Statistical Area Level 4) boundaries for Australia,
groups them by state (STE_NAME21), and creates a single unioned polygon
for each state. The results are saved as both GeoJSON and Parquet files.

Usage:
    uv run scripts/extract_state_polygons.py
"""

import logging
from pathlib import Path

from utils import dirty

import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union

log = logging.getLogger(__name__)


def main():
    """Main function to extract and union state polygons."""
    # Define paths
    input_file = Path("data/originals_converted/boundaries/SA4_2021_AUST_SHP_GDA2020/SA4_2021_AUST_GDA2020.parquet")
    output_dir = Path("data/originals_converted/state_polygons")
    output_geojson = output_dir / "australian_states.geojson"
    output_parquet = output_dir / "australian_states.parquet"

    if not dirty([output_geojson, output_parquet], [input_file]):
        log.info("Output files are up-to-date, skipping processing.")
        return

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"Output directory created/verified: {output_dir}")
    
    # Load the SA4 boundaries
    log.info(f"Loading SA4 boundaries from: {input_file}")
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    gdf = gpd.read_parquet(input_file)
    log.info(f"Loaded {len(gdf)} SA4 polygons")
    log.info(f"CRS: {gdf.crs}")
    log.info(f"Columns: {list(gdf.columns)}")
    
    # Check if STE_NAME21 column exists
    if 'STE_NAME21' not in gdf.columns:
        log.error("Column 'STE_NAME21' not found in the data")
        log.info(f"Available columns: {list(gdf.columns)}")
        raise ValueError("Required column 'STE_NAME21' not found")
    
    # Get unique states
    unique_states = gdf['STE_NAME21'].unique()
    log.info(f"Found {len(unique_states)} unique states/territories: {sorted(unique_states)}")
    
    # Group by state and union the geometries
    log.info("Grouping by state and unioning geometries...")
    state_polygons = []
    
    for state_name in unique_states:
        log.info(f"Processing: {state_name}")
        
        # Filter for this state
        state_gdf = gdf[gdf['STE_NAME21'] == state_name]
        log.info(f"  - {len(state_gdf)} SA4 regions in {state_name}")
        
        # Union all geometries for this state
        unioned_geometry = unary_union(state_gdf.geometry)
        
        # Create a dictionary for this state's data
        state_data = {
            'STE_NAME21': state_name,
            'geometry': unioned_geometry,
            'sa4_count': len(state_gdf),  # Number of SA4 regions that were unioned
        }
        
        # Add aggregate statistics if useful columns exist
        if 'AREASQKM21' in gdf.columns:
            state_data['total_area_sqkm'] = state_gdf['AREASQKM21'].sum()
        
        state_polygons.append(state_data)
    
    # Create new GeoDataFrame with unioned state polygons
    states_gdf = gpd.GeoDataFrame(state_polygons, crs=gdf.crs)
    
    # Sort by state name for consistency
    states_gdf = states_gdf.sort_values('STE_NAME21').reset_index(drop=True)
    
    log.info(f"Created GeoDataFrame with {len(states_gdf)} state/territory polygons")
    
    # Save as GeoJSON
    log.info(f"Saving GeoJSON to: {output_geojson}")
    states_gdf.to_file(output_geojson, driver='GeoJSON')
    
    # Save as Parquet
    log.info(f"Saving Parquet to: {output_parquet}")
    states_gdf.to_parquet(output_parquet)
    
    # Print summary statistics
    log.info("\n" + "="*50)
    log.info("SUMMARY")
    log.info("="*50)
    log.info(f"Input SA4 regions: {len(gdf)}")
    log.info(f"Output state/territory polygons: {len(states_gdf)}")
    log.info(f"States/Territories processed:")
    for idx, row in states_gdf.iterrows():
        area_info = f", Area: {row['total_area_sqkm']:.2f} km²" if 'total_area_sqkm' in states_gdf.columns else ""
        log.info(f"  - {row['STE_NAME21']}: {row['sa4_count']} SA4 regions unioned{area_info}")
    
    log.info("\nOutput files:")
    log.info(f"  - GeoJSON: {output_geojson} ({output_geojson.stat().st_size / 1024:.2f} KB)")
    log.info(f"  - Parquet: {output_parquet} ({output_parquet.stat().st_size / 1024:.2f} KB)")
    log.info("✅ State polygon extraction and union completed successfully!")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
    )
    main()
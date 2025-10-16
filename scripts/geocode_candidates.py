#!/usr/bin/env python3
"""
Geocode real estate candidates and check walkability.

This script:
1. Reads candidate addresses from candidates.yml using ruamel.yaml
2. Geocodes addresses using Google Maps API (preserving existing lat/lon)
3. Updates candidates.yml in-place with lat/lon while preserving formatting
4. Checks PTV walkability against isochrone boundaries
5. Generates all_candidates.geojson with all attributes
"""
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "ruamel.yaml>=0.18.0",
#   "googlemaps>=4.10.0",
#   "python-dotenv>=1.0.0",
#   "geopandas>=0.14.0",
#   "pyarrow",
#   "shapely>=2.0.0",
# ]
# ///

import argparse
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Optional, Tuple

import geopandas as gpd
import googlemaps
from dotenv import load_dotenv
from ruamel.yaml import YAML
from shapely.geometry import Point

# Load environment variables
load_dotenv()

# Setup logging
log = logging.getLogger(__name__)

# Script paths
SCRIPT = Path(__file__)
SCRIPT_NAME = SCRIPT.stem
SCRIPT_DIR = SCRIPT.parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

# Configuration
CANDIDATES_YAML = PROJECT_ROOT / "candidates.yml"
OUTPUT_DIR = PROJECT_ROOT / "data" / "candidate_real_estate"
OUTPUT_ALL_CANDIDATES = OUTPUT_DIR / "all_candidates.geojson"
WEBSITE_OUTPUT_DIR = PROJECT_ROOT / "sites" / "webapp" / "data"
OUTPUT_WEBSITE_ALL_CANDIDATES = WEBSITE_OUTPUT_DIR / "all_candidates.geojson"

# Isochrone files for walkability check
INPUT_ISOCHRONE_FOOT_5MIN = WEBSITE_OUTPUT_DIR / "5.geojson"
INPUT_ISOCHRONE_FOOT_15MIN = WEBSITE_OUTPUT_DIR / "15.geojson"

# Environment variables
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

# Helper lambdas
_format_file_list = lambda files, max_show=5: '\n        '.join(f"- {p.relative_to(PROJECT_ROOT)}" for p in files[:max_show]) + (f"\n        ... and {len(files) - max_show} more files" if len(files) > max_show else "")  # noqa: E731

def check_ptv_walkability(lat: float, lon: float) -> Tuple[bool, bool]:
    """
    Check if a point is within 5 or 15 minutes walkable isochrone.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Tuple of (inside_5_min, inside_15_min)
    """
    point = Point(lon, lat)  # Note: Point takes (lon, lat)

    try:
        # Load isochrone boundaries
        foot_5min_gdf = gpd.read_file(INPUT_ISOCHRONE_FOOT_5MIN)
        foot_15min_gdf = gpd.read_file(INPUT_ISOCHRONE_FOOT_15MIN)

        # Check containment
        inside_5_min = any(foot_5min_gdf.contains(point))
        inside_15_min = any(foot_15min_gdf.contains(point))

        return inside_5_min, inside_15_min

    except Exception as e:
        log.error(f"Error loading isochrone files: {e}")
        return False, False


def get_walkability_colour(inside_5_min: bool, inside_15_min: bool) -> str:
    """
    Determine walkability colour based on isochrone inclusion.

    Args:
        inside_5_min: Whether point is within 5-minute walk
        inside_15_min: Whether point is within 15-minute walk

    Returns:
        Hex colour code
    """
    if inside_5_min:
        return "#A67C00"  # Dark Mustard - Very close (potentially too dense)
    elif inside_15_min:
        return "#00C864"  # Green - Sweet spot (5-15min walk)
    else:
        return "#800000"  # Maroon - Too far to walk


class CandidateGeocoder:
    """Handle geocoding and YAML updates for real estate candidates."""

    def __init__(self, api_key: str):
        """
        Initialize geocoder with Google Maps API.

        Args:
            api_key: Google Maps API key
        """
        self.gmaps = None
        if api_key:
            self.gmaps = googlemaps.Client(key=api_key)
            log.info("Initialized Google Maps client")
        else:
            log.warning("Google Maps API key not provided. Geocoding will be skipped.")

        # Initialize ruamel.yaml with preservation settings
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.map_indent = 4
        self.yaml.sequence_indent = 4
        self.yaml.width = 4096  # Prevent line wrapping

    def load_candidates(self) -> Dict[str, Dict[str, Any]]:
        """
        Load candidates from YAML file.

        Returns:
            Dictionary of address -> attributes
        """
        with open(CANDIDATES_YAML, 'r', encoding='utf-8') as f:
            data = self.yaml.load(f)

        # Convert list format to dict format if needed
        if isinstance(data, list):
            candidates = {}
            for item in data:
                if isinstance(item, dict):
                    # Extract address as key
                    for address, attrs in item.items():
                        if attrs is None:
                            attrs = {}
                        candidates[address] = attrs
            return candidates

        return data or {}

    def save_candidates(self, candidates: Dict[str, Dict[str, Any]]) -> None:
        """
        Save candidates back to YAML file, preserving formatting.

        Args:
            candidates: Dictionary of address -> attributes
        """
        # Convert dict back to list format for YAML
        data = []
        for address, attrs in candidates.items():
            data.append({address: attrs})

        with open(CANDIDATES_YAML, 'w', encoding='utf-8') as f:
            self.yaml.dump(data, f)

        log.info(f"Updated {CANDIDATES_YAML} with geocoded data")

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address using Google Maps API.

        Args:
            address: Street address to geocode

        Returns:
            Tuple of (lat, lon) or None if geocoding fails
        """
        if not self.gmaps:
            return None

        try:
            log.debug(f"Geocoding: {address}")
            geocode_result = self.gmaps.geocode(address)

            if geocode_result and "geometry" in geocode_result[0]:
                location = geocode_result[0]["geometry"]["location"]
                lat, lon = location["lat"], location["lng"]
                log.info(f"Geocoded '{address}' -> ({lat:.6f}, {lon:.6f})")
                return lat, lon
            else:
                log.warning(f"No geocoding result for: {address}")

        except Exception as e:
            log.error(f"Error geocoding address '{address}': {e}")

        return None

    def process_candidates(self, force: bool = False) -> gpd.GeoDataFrame:
        """
        Process all candidates: geocode, check walkability, and create GeoDataFrame.

        Args:
            force: Force re-geocoding even if lat/lon exists

        Returns:
            GeoDataFrame with all candidate data
        """
        candidates = self.load_candidates()
        log.info(f"Loaded {len(candidates)} candidates from {CANDIDATES_YAML}")

        updated = False
        records = []

        for address, attrs in candidates.items():
            if attrs is None:
                attrs = {}
                candidates[address] = attrs

            # Check if geocoding is needed
            lat = attrs.get("lat")
            lon = attrs.get("lon")

            if (lat is None or lon is None or force) and self.gmaps:
                # Geocode the address
                result = self.geocode_address(address)
                if result:
                    lat, lon = result
                    attrs["lat"] = lat
                    attrs["lon"] = lon
                    updated = True

                    # Rate limiting
                    time.sleep(0.5)
            elif lat is not None and lon is not None:
                log.debug(f"Using existing coordinates for '{address}': ({lat}, {lon})")

            # Check walkability if we have coordinates
            if lat is not None and lon is not None:
                inside_5_min, inside_15_min = check_ptv_walkability(lat, lon)
                walkability_colour = get_walkability_colour(inside_5_min, inside_15_min)

                # Create record for GeoDataFrame
                record = {
                    "address": address,
                    "geometry": Point(lon, lat),
                    "ptv_walkable_5min": inside_5_min,
                    "ptv_walkable_15min": inside_15_min,
                    "ptv_walkability_colour": walkability_colour,
                    **attrs  # Include all attributes from YAML
                }
                records.append(record)

                log.info(
                    f"Processed '{address}': "
                    f"5min={inside_5_min}, 15min={inside_15_min}"
                )
            else:
                log.warning(f"No coordinates for '{address}', skipping walkability check")

                # Still include in output without geometry
                record = {
                    "address": address,
                    "geometry": None,
                    "ptv_walkable_5min": False,
                    "ptv_walkable_15min": False,
                    "ptv_walkability_colour": "#808080",  # Gray for unknown
                    **attrs
                }
                records.append(record)

        # Save updated YAML if changes were made
        if updated:
            self.save_candidates(candidates)

        # Create GeoDataFrame
        if records:
            gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
            return gdf
        else:
            return gpd.GeoDataFrame([], crs="EPSG:4326")

    def save_geojson(self, gdf: gpd.GeoDataFrame) -> None:
        """
        Save GeoDataFrame to GeoJSON files.

        Args:
            gdf: GeoDataFrame to save
        """
        # Ensure output directories exist
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        WEBSITE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Filter out records without geometry for GeoJSON
        gdf_with_geom = gdf[gdf.geometry.notna()].copy()

        if not gdf_with_geom.empty:
            # Save to both locations
            gdf_with_geom.to_file(OUTPUT_ALL_CANDIDATES, driver="GeoJSON")
            log.info(f"Saved {len(gdf_with_geom)} features to {OUTPUT_ALL_CANDIDATES}")

            # gdf_with_geom.to_file(OUTPUT_WEBSITE_ALL_CANDIDATES, driver="GeoJSON")
            gdf_with_geom.to_parquet(OUTPUT_WEBSITE_ALL_CANDIDATES.with_suffix(".parquet"), engine="pyarrow", index=False)

            log.info(f"Saved {len(gdf_with_geom)} features to {OUTPUT_WEBSITE_ALL_CANDIDATES}")
        else:
            log.warning("No features with geometry to save")


def main(dry_run: bool = False, force: bool = False):
    """
    Main processing function.

    Args:
        dry_run: Run without saving changes
        force: Force re-geocoding even if coordinates exist
    """
    # Check for API key
    if not GOOGLE_MAPS_API_KEY:
        log.warning("Google Maps API key not found. Set GOOGLE_MAPS_API_KEY in .env file")
        log.warning("Proceeding without geocoding capability...")

    # Initialize geocoder
    geocoder = CandidateGeocoder(GOOGLE_MAPS_API_KEY)

    # Process candidates
    log.info("Starting candidate processing...")
    gdf = geocoder.process_candidates(force=force)

    # Summary statistics
    total = len(gdf)
    geocoded = len(gdf[gdf.geometry.notna()])
    walkable_5min = len(gdf[gdf["ptv_walkable_5min"] == True])
    walkable_15min = len(gdf[gdf["ptv_walkable_15min"] == True])

    log.info(f"\n{'='*50}")
    log.info(f"Processing Summary:")
    log.info(f"  Total candidates: {total}")
    log.info(f"  Successfully geocoded: {geocoded}")
    log.info(f"  Within 5-min walk: {walkable_5min}")
    log.info(f"  Within 15-min walk: {walkable_15min}")
    log.info(f"{'='*50}\n")

    # Save results
    if not dry_run and not gdf.empty:
        geocoder.save_geojson(gdf)
    elif dry_run:
        log.info("DRY RUN: Skipping file saves")


if __name__ == "__main__":
    ALL_INPUTS = [CANDIDATES_YAML, INPUT_ISOCHRONE_FOOT_5MIN, INPUT_ISOCHRONE_FOOT_15MIN]
    ALL_OUTPUTS = [OUTPUT_ALL_CANDIDATES, OUTPUT_WEBSITE_ALL_CANDIDATES]

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent(f"""\
        {SCRIPT_NAME} - Geocode real estate candidates and check walkability

        This script reads candidate addresses from candidates.yml, geocodes them using
        Google Maps API (preserving existing coordinates), checks PTV walkability against
        isochrone boundaries, and generates GeoJSON output with all attributes.

        INPUTS:
        {_format_file_list(ALL_INPUTS)}

        OUTPUTS:
        {_format_file_list(ALL_OUTPUTS)}

        ENVIRONMENT:
            GOOGLE_MAPS_API_KEY - Required for geocoding functionality
        """)
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Show only errors")
    parser.add_argument("-n", "--dry-run", action="store_true",
                       help="Run without saving changes")
    parser.add_argument("-f", "--force", action="store_true",
                       help="Force re-geocoding even if coordinates exist")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.ERROR if args.quiet else logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    main(dry_run=args.dry_run, force=args.force)
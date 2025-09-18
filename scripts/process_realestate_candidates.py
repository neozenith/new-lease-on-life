#!/usr/bin/env python3
"""
Process real estate candidates from a YAML file.

This script:
1. Reads a list of realestate.com.au links from candidates.yml
2. Scrapes each link to extract the property address
3. Uses Google Maps API to calculate commute times to destinations in known_commutes.yml
4. Saves all data to JSON files in data/candidate_real_estate/
"""
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "playwright>=1.40.0",
#   "pyyaml>=6.0.1",
#   "googlemaps>=4.10.0",
#   "python-dotenv>=1.0.0",
#   "geopandas",
#   "pyarrow",
#   "polyline",
#   "requests",
#   "tqdm>=4.66.1",
# ]
# ///

# for each stop calculate the commute time to Southern cross station
# and create a modified stops dataset to visualise the commute isochrones.

import argparse
import asyncio
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import geopandas as gpd
import googlemaps
import polyline
import yaml
from dotenv import load_dotenv
from shapely.geometry import LineString, Point

from utils import save_geodataframe

# Load environment variables from .env file
load_dotenv()

# Setup logging
log = logging.getLogger(__name__)

# Get the path of this script
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent.resolve()

# Constants
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
CANDIDATES_YAML = SCRIPT_DIR.parent / "candidates.yml"
COMMUTES_YAML = SCRIPT_DIR.parent / "known_commutes.yml"

OUTPUT_DIR = SCRIPT_DIR.parent / "data/candidate_real_estate"
OUTPUT_ALL_CANDIDATES = OUTPUT_DIR / "all_candidates.geojson"

WEBSITE_OUTPUT_DIR = SCRIPT_DIR.parent / "static/data/"
OUTPUT_WEBSITE_ALL_CANDIDATES = WEBSITE_OUTPUT_DIR / "all_candidates.geojson"

INPUT_ISOCHRONE_FOOT_5MIN = PROJECT_DIR / "static/data/5.geojson"
INPUT_ISOCHRONE_FOOT_15MIN = PROJECT_DIR / "static/data/15.geojson"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def check_ptv_walkability(lat: float | None, lon: float | None) -> tuple[bool, bool]:
    """Check if a point is within 5 or 15 minutes walkable isochrone."""
    if lat is None or lon is None:
        return False, False

    point = Point(lon, lat)  # Note: Point takes (lon, lat)

    try:
        foot_5min_gdf = gpd.read_file(INPUT_ISOCHRONE_FOOT_5MIN)
        foot_15min_gdf = gpd.read_file(INPUT_ISOCHRONE_FOOT_15MIN)
    except Exception as e:
        log.error(f"Error loading isochrone files: {e}")
        return False, False

    inside_5_min = any(foot_5min_gdf.contains(point))
    inside_15_min = any(foot_15min_gdf.contains(point))

    return inside_5_min, inside_15_min

def get_walkability_colour(inside_5_min: bool, inside_15_min: bool) -> str:
    """Determine walkability colour based on isochrone inclusion."""
    if inside_5_min:
        return "#A67C00"  # Dark Mustard --> A little too close to walk (usually hypoer dense area)
    elif inside_15_min:
        return "#00C864"  # Green --> Between 5-15min walk is the sweet spot
    else:
        return "#800000"  # Maroon --> Too far to walk

class RealEstateProcessor:
    """Process real estate addresses and calculate commute times."""

    def __init__(self, google_maps_api_key: str):
        self.gmaps = None
        if google_maps_api_key:
            self.gmaps = googlemaps.Client(key=google_maps_api_key)
        else:
            log.warning(
                "Google Maps API key not provided. Commute time calculations will be skipped."
            )


    def output_file_for_url(self, url: str) -> Path:
        """
        Generate a filename for the output based on the address.

        Args:
            address: The property address

        Returns:
            A valid filename string
        """
        url_parts = url.replace("https://", "").replace("http://", "").split("/")
        filename = f"{'_'.join(url_parts).replace('.', '_')}.json"

        # Ensure filename is valid
        filename = "".join(c if c.isalnum() or c in ["_", "."] else "_" for c in filename)
        filename = filename[:100] + ".json"  # Limit length

        return Path(OUTPUT_DIR) / filename

    def geocode_address(self, address: str):
        """Geocode an address using Google Maps API. Returns (lat, lon) or (None, None) if not found."""
        if not self.gmaps:
            return None, None
        try:
            geocode_result = self.gmaps.geocode(address)
            if geocode_result and "geometry" in geocode_result[0]:
                location = geocode_result[0]["geometry"]["location"]
                return location["lat"], location["lng"]
        except Exception as e:
            log.error(f"Error geocoding address {address}: {e}")
        return None, None

    def save_geojson_result(self, result: dict[str, Any]) -> gpd.GeoDataFrame:
        """
        Save processing result to a GeoJSON file with Point and LineString features using geopandas.
        Only saves if at least one geometry is present.
        Args:
            result: Processing result dictionary
        Returns:
            Path to the saved file or empty string if not saved
        """
        if result.get("error"):
            log.error(f"Error processing result: {result['error']}")
            return ""

        # Generate a filepath based on the address
        filepath = self.output_file_for_url(result["address"]).with_suffix(".geojson")

        records = []
        # Add property Point feature if lat/lon available or can be geocoded
        lat = result.get("lat")
        lon = result.get("lon")
        if (lat is None or lon is None) and self.gmaps:
            lat, lon = self.geocode_address(result["address"])
            result["lat"] = lat
            result["lon"] = lon

        inside_5_min, inside_15_min = check_ptv_walkability(lat, lon)
        walkability_colour = get_walkability_colour(inside_5_min, inside_15_min)
        result["ptv_walkability_colour"] = walkability_colour
        result["ptv_walkable_5min"] = inside_5_min
        result["ptv_walkable_15min"] = inside_15_min
        if lat is not None and lon is not None:
            records.append(
                {
                    **{k: v for k, v in result.items() if k not in ["lat", "lon"]},
                    "geometry": Point(lon, lat),
                    "feature_type": "property",
                }
            )


        # Only save if there is at least one geometry
        records = [r for r in records if r["geometry"] is not None]
        if not records:
            log.warning(f"No geometry for {result['address']}, not saving GeoJSON.")
            return ""
        gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
        gdf.to_file(filepath, driver="GeoJSON")
        log.info(f"Saved GeoJSON result to {filepath}")
        return gdf


def load_yaml_file(filepath: str) -> Any:
    """Load data from a YAML file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, OSError) as e:
        log.error(f"Error loading YAML file {filepath}: {e}")
        return None


async def main():
    """Main function to process real estate candidates."""
    # Check if Google Maps API key is provided
    if not GOOGLE_MAPS_API_KEY:
        log.warning("Google Maps API key not provided. Set GOOGLE_MAPS_API_KEY in .env file.")

    # Load candidates (now addresses directly)
    candidate_addresses = load_yaml_file(str(CANDIDATES_YAML))
    if not candidate_addresses or not isinstance(candidate_addresses, list):
        log.error(
            f"Invalid or missing candidates in {CANDIDATES_YAML}. Expected a list of addresses."
        )
        return

    log.info(f"Loaded {len(candidate_addresses)} candidate addresses from {CANDIDATES_YAML}")

    # Load commute destinations
    commute_destinations = load_yaml_file(str(COMMUTES_YAML))
    if not commute_destinations or not isinstance(commute_destinations, list):
        log.error(
            f"Invalid or missing destinations in {COMMUTES_YAML}. Expected a list of destinations."
        )
        return

    log.info(f"Loaded {len(commute_destinations)} commute destinations from {COMMUTES_YAML}")

    # Transform commute destinations to expected format
    formatted_destinations = []
    for dest in commute_destinations:
        # Each destination is a dict with a single key like "work"
        for dest_name, dest_details in dest.items():
            formatted_dest = {
                "name": dest_name,
                "address": dest_details.get("address", ""),
                "lat": dest_details.get("lat"),
                "lon": dest_details.get("lon"),
            }
            formatted_destinations.append(formatted_dest)
            log.info(f"Added commute destination: {dest_name} at {formatted_dest['address']}")

    # Initialize processor
    processor = RealEstateProcessor(GOOGLE_MAPS_API_KEY)

    # Process each candidate
    results = []
    all_gdfs = []
    for address in candidate_addresses:
        try:
            file_path = processor.output_file_for_url(address).with_suffix(".geojson")

            if (
                file_path.exists()
                and file_path.stat().st_mtime > Path(CANDIDATES_YAML).stat().st_mtime
            ):
                log.info(f"SKIP {address}, already processed: {file_path}")
                gdf = gpd.read_file(file_path)
                all_gdfs.append(gdf)
                continue

            log.info(f"Processing: {address}")

            # Prepare result
            result = {
                "address": address,
                "lat": None,
                "lon": None,
                "processed_at": datetime.now().isoformat(),
            }

            # Save the result as GeoJSON
            gdf = processor.save_geojson_result(result)
            all_gdfs.append(gdf)
            results.append(result)

            # Add a small delay between API requests
            delay = 1 + (secrets.randbelow(20) / 10)
            log.debug(f"Waiting {delay:.1f} seconds before next request")
            await asyncio.sleep(delay)

        except Exception as e:
            log.error(f"Error processing candidate address {address}: {e}")

    # Combine all GeoDataFrames and save a summary file
    combined_gdf = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs="EPSG:4326")
    save_geodataframe(combined_gdf, OUTPUT_ALL_CANDIDATES)
    save_geodataframe(combined_gdf, OUTPUT_WEBSITE_ALL_CANDIDATES)
    log.info(f"Saved combined GeoDataFrame to {OUTPUT_ALL_CANDIDATES} and {OUTPUT_WEBSITE_ALL_CANDIDATES}")

    # Save summary
    summary = {
        "processed_at": datetime.now().isoformat(),
        "total_candidates": len(candidate_addresses),
        "successful_processing": sum(1 for r in results if "error" not in r),
        "failed_processing": sum(1 for r in results if "error" in r),
    }

    with open(Path(OUTPUT_DIR) / "processing_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    log.info(
        f"Processing completed: {summary['successful_processing']} successful, {summary['failed_processing']} failed"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process real estate candidates from a YAML file. Reads a list of addresses from candidates.yml, "
        "calculates commute times to destinations in known_commutes.yml using Google Maps API, "
        "and saves all data to JSON files in data/candidate_real_estate/."
    )
    args = parser.parse_args()

    # Using asyncio.run (Python 3.12 as per script header)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
    )
    asyncio.run(main())

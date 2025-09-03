#!/usr/bin/env python3
"""
Calculate transit time (minutes) and distance (km) from public transport stops
to Southern Cross Station, and save the results as a GeoJSON file.
"""
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "googlemaps>=4.10.0",
#   "python-dotenv>=1.0.0",
#   "geopandas",
#   "pandas",
#   "pyarrow",
#   "requests",
#   "tqdm",
# ]
# ///

import argparse
import json
import logging
import os
import pathlib
import time
from datetime import datetime, timedelta
from pathlib import Path

import geopandas as gpd
import googlemaps
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
from utils import min_max_normalize, save_geodataframe

# Load environment variables
load_dotenv()

SCRIPT_DIR = Path(__file__).parent.resolve()

HULL_TIER_SIZE = 5  # minutes
CONCAVE_HULL_RATIO = 0.6  # Ratio for concave hull generation
# Constants
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
SOUTHERN_CROSS = "Southern Cross Station, Melbourne, Australia"
TRANSIT_TIME_CACHE = SCRIPT_DIR.parent / "data/transit_time_cache/"
STOPS = SCRIPT_DIR.parent / "data/geojson/ptv/stops_within_union.parquet"

OUTPUT_BASE = SCRIPT_DIR.parent / "data/geojson/ptv/"
OUTPUT_GEOJSON = OUTPUT_BASE / "stops_with_commute_times.geojson"
OUTPUT_PARQUET = OUTPUT_BASE / "stops_with_commute_times.parquet"

OUTPUT_HULL_GEOJSON = OUTPUT_BASE / "ptv_commute_tier_hulls.geojson"

# Setup logging
log = logging.getLogger(__name__)


def get_transit_time(gmaps, origin_lat, origin_lng, destination):
    """Get transit time (minutes) and distance (km) from origin to destination"""
    morning_departure = datetime.now().replace(hour=8, minute=0, second=0) + timedelta(days=1)

    try:
        directions = gmaps.directions(
            (origin_lat, origin_lng), destination, mode="transit", departure_time=morning_departure
        )

        if not directions or not directions[0].get("legs"):
            return None, None

        leg = directions[0]["legs"][0]
        # Convert seconds to minutes
        duration_minutes = leg["duration"]["value"] / 60
        # Convert meters to kilometers
        distance_km = leg["distance"]["value"] / 1000

        time.sleep(0.2)  # Avoid rate limits
        return duration_minutes, distance_km

    except (KeyError, IndexError) as e:
        log.error(f"Error parsing transit data: {e}")
        return None, None


def normalised_stop_name(name):
    """Normalise stop name for use in filenames"""
    return name.lower().replace(" ", "_").replace(",", "").replace("'", "") + "_transit_time.json"


def cache_check(gdf):
    """Check if transit times are already cached for the stops in the GeoDataFrame"""
    expected = 0
    cached = 0
    total_rows = len(gdf)  # Ensure gdf is not empty
    for _, stop in tqdm(gdf.iterrows(), total=total_rows, desc="Checking cache"):
        name = stop["STOP_NAME"]
        output = TRANSIT_TIME_CACHE / normalised_stop_name(name)
        expected += 1
        if output.exists():
            cached += 1

    log.info(f"Cached {cached} / {expected}  {cached / expected * 100.0:.2f}% ")


def create_hulls(gdf):
    gdf_ptv_stops = gdf
    # gdf_ptv_stops = gdf_ptv_stops.to_crs("EPSG:4326")
    # Make sure MODE is a column, not just in the index
    if "MODE" in gdf_ptv_stops.index.names and "MODE" not in gdf_ptv_stops.columns:
        gdf_ptv_stops = gdf_ptv_stops.reset_index()

    PTV_MODES = ["REGIONAL TRAIN", "METRO TRAIN", "METRO TRAM"]
    # gdf_ptv_stops = gdf_ptv_stops[gdf_ptv_stops['MODE'].isin(PTV_MODES)]

    tier_size = HULL_TIER_SIZE
    # tiers = range(tier_size, 60, tier_size)  # Define tiers from 5 to 55 minutes in increments of tier_size
    gdf_ptv_stops["transit_time_minutes_nearest_tier"] = (
        gdf_ptv_stops["transit_time_minutes"] / tier_size
    ).round() * tier_size
    gdf_ptv_stops["transit_time_minutes_nearest_tier_z"] = (
        min_max_normalize(gdf_ptv_stops["transit_time_minutes_nearest_tier"]) * 0.5
        + 0.5  # Normalized to [0.5, 1.0] to be able to be used for opacity or saturation
    )

    # Group stops by MODE and transit_time_minutes_nearest_tier to create hulls
    hull_tiers = []

    # Process each mode
    for mode in PTV_MODES:
        mode_stops = gdf_ptv_stops[gdf_ptv_stops["MODE"] == mode]

        # First, get all unique tiers and sort them since we will accumulate them
        all_tiers = sorted(mode_stops["transit_time_minutes_nearest_tier"].unique())

        # Store hulls for each tier to build cumulative hulls
        tier_hulls = {}

        # For each tier, create a cumulative hull that includes all smaller tiers
        for tier in all_tiers:
            # Get all stops with transit time <= current tier
            cumulative_stops = mode_stops[mode_stops["transit_time_minutes_nearest_tier"] <= tier]

            if len(cumulative_stops) < 3:
                log.debug(
                    f"  Skipping {mode} tier {tier} - not enough points ({len(cumulative_stops)})"
                )
                continue

            log.debug(
                f"  Creating cumulative hull for {mode} tier {tier} with {len(cumulative_stops)} points"
            )

            # Convert the points to a MultiPoint object

            multi_point = gpd.GeoSeries(cumulative_stops["geometry"].union_all())

            # Create a convex hull from all points (the rubber band effect)
            hull = multi_point.concave_hull(
                ratio=CONCAVE_HULL_RATIO,
                allow_holes=False,  # Minimum points to form a hull
            )

            # Store this tier's hull
            tier_hulls[tier] = hull

            # Get the normalized z-value for color mapping (use the current tier's value)
            tier_group = mode_stops[mode_stops["transit_time_minutes_nearest_tier"] == tier]
            tier_z = (
                tier_group["transit_time_minutes_nearest_tier_z"].mean()
                if len(tier_group) > 0
                else 0.5
            )

            # Create a GeoDataFrame for this hull
            hull_gdf = gpd.GeoDataFrame(
                geometry=hull.geometry,
                data={
                    "MODE": [mode],
                    "transit_time_minutes_nearest_tier": [tier],
                    "transit_time_minutes_nearest_tier_z": [tier_z],
                    "point_count": [len(cumulative_stops)],
                },
                crs=gdf_ptv_stops.crs,
            )
            hull_tiers.append(hull_gdf)

    # Combine all hulls into a single GeoDataFrame
    gdf_ptv_tiers = pd.concat(hull_tiers, ignore_index=True)
    # gdf_ptv_tiers = gdf_ptv_tiers[gdf_ptv_tiers['MODE'].isin(["METRO TRAIN", "METRO TRAM"])]

    # Define the tiers we want to keep

    # gdf_ptv_tiers = gdf_ptv_tiers[gdf_ptv_tiers['transit_time_minutes_nearest_tier'].isin(tiers)]

    # Sort by tier in descending order (largest to smallest)
    # This ensures smaller tiers are drawn last and appear on top for hover interactions
    gdf_ptv_tiers = gdf_ptv_tiers.sort_values(
        by=["transit_time_minutes_nearest_tier"], ascending=False
    )

    save_geodataframe(gdf_ptv_tiers, OUTPUT_HULL_GEOJSON)


def main():
    """Process stops and calculate transit times to Southern Cross Station"""
    if not GOOGLE_MAPS_API_KEY:
        log.error("Google Maps API key not provided. Set GOOGLE_MAPS_API_KEY in .env file.")
        return

    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

    # Load stops
    stops_gdf = gpd.read_parquet(STOPS)
    log.info(f"Loaded {len(stops_gdf)} stops")

    cache_check(stops_gdf)

    # List to store stops with transit data
    stops_with_data = []

    # Process each stop
    for i, (_, stop) in enumerate(stops_gdf.iterrows()):
        try:
            name = stop["STOP_NAME"]
            x, y = stop.geometry.x, stop.geometry.y

            output = pathlib.Path(TRANSIT_TIME_CACHE) / normalised_stop_name(name)
            transit_times = {}

            if output.exists():
                transit_times = json.loads(output.read_text())

            else:
                log.info(f"Processing stop {i + 1}/{len(stops_gdf)}: {name}")

                # Get transit details (already in minutes and km)
                duration_minutes, distance_km = get_transit_time(gmaps, y, x, SOUTHERN_CROSS)

                # Skip if no transit option found
                if duration_minutes is None:
                    log.warning(f"No transit option found for {name}")
                    continue

                if duration_minutes is not None:
                    transit_times["transit_time_minutes"] = round(float(duration_minutes), 1)
                if distance_km is not None:
                    transit_times["transit_distance_km"] = round(float(distance_km), 2)

            tier_size = float(HULL_TIER_SIZE)
            # tiers = range(tier_size, 60, tier_size)  # Define tiers from 5 to 55 minutes in increments of tier_size
            transit_times["transit_time_minutes_nearest_tier"] = (
                round(round(float(transit_times["transit_time_minutes"]), 1) / tier_size)
                * tier_size
            )

            # Add stop with transit data - only minutes and kilometers
            stop_record = stop.copy()
            stop_record["transit_time_minutes"] = transit_times.get("transit_time_minutes")
            stop_record["transit_distance_km"] = transit_times.get("transit_distance_km")
            stop_record["transit_time_minutes_nearest_tier"] = transit_times.get(
                "transit_time_minutes_nearest_tier"
            )
            output.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
            output.write_text(json.dumps(transit_times))

            stops_with_data.append(stop_record)

        except (ValueError, KeyError, AttributeError) as e:
            log.error(f"Error processing stop {stop.get('STOP_ID', 'Unknown')}: {e}")

    # Create GeoDataFrame with transit data
    if not stops_with_data:
        log.error("No transit data found for any stops")
        return

    result_gdf = gpd.GeoDataFrame(stops_with_data, crs=stops_gdf.crs)

    # Save results
    result_gdf.to_file(OUTPUT_GEOJSON, driver="GeoJSON")
    result_gdf.to_parquet(OUTPUT_PARQUET)

    create_hulls(result_gdf)

    # Show statistics
    durations = result_gdf["transit_time_minutes"]
    log.info(
        f"Transit time stats (minutes): min={durations.min():.1f}, "
        f"max={durations.max():.1f}, mean={durations.mean():.1f}, "
        f"median={durations.median():.1f}, count={len(durations)}"
    )

    log.info(f"Results saved to {OUTPUT_GEOJSON} and {OUTPUT_PARQUET}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate transit time (minutes) and distance (km) from public transport stops to Southern Cross Station, and save the results as a GeoJSON file."
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
    )

    main()

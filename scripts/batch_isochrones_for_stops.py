# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "requests>=2.31.0",
#   "pyyaml>=6.0.1",
#   "geopandas",
#   "python-dotenv>=1.0.0"
# ]
# ///

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from utils import (
    MAPBOX_PROFILE_MAPPING,
    PTV_TRANSPORT_MODES,
    TRANSPORT_MODES,
    iterate_stop_modes,
    load_stops,
    make_request_with_retry,
)

# Load environment variables from .env file
load_dotenv()

SCRIPT_DIR = Path(__file__).parent.resolve()


GRAPHHOPPER_API_KEY = os.environ.get("GRAPHHOPPER_API_KEY", "")
GRAPHHOPPER_HOST = os.environ.get("GRAPHHOPPER_HOST", "https://graphhopper.com")
ISOCHRONE_URL = f"{GRAPHHOPPER_HOST}/api/1/isochrone"

MAPBOX_LIMIT = 60.0 / 300.0  # 300 requests per minute
MAPBOX_API_TOKEN = os.environ.get("MAPBOX_API_TOKEN", "")
MAPBOX_API_HOST = os.environ.get("MAPBOX_API_HOST", "https://api.mapbox.com")
MAPBOX_ISOCHRONE_URL = f"{MAPBOX_API_HOST}/isochrone/v1/mapbox"

TIME_LIMIT = 900
BUCKETS = 3
MAPBOX_COUNTOUR_TIMES = [5, 10, 15]  # Minutes for Mapbox isochrones


# Function to call GraphHopper Isochrone API
def get_isochrone(lat, lon, mode, time_limit, buckets, api_key, max_retries=10, backoff_factor=5):
    base_url = f"{ISOCHRONE_URL}?point={lat},{lon}"
    params = {
        "time_limit": time_limit,
        "vehicle": mode,
        "buckets": buckets,
        "key": api_key,
    }
    return make_request_with_retry(base_url, params, max_retries, backoff_factor)


def get_isochrone_mapbox(lat, lon, mode, countour_times, api_key, max_retries=10, backoff_factor=5):
    """Call Mapbox Isochrone API.
    https://docs.mapbox.com/api/navigation/isochrone/
    """
    base_url = f"{MAPBOX_ISOCHRONE_URL}/{mode}/{lon},{lat}"
    params = {
        "contours_minutes": countour_times,
        "polygons": "true",
        "access_token": api_key,
    }
    return make_request_with_retry(base_url, params, max_retries, backoff_factor)


def status():
    # Load stops
    gdf = load_stops(filter_modes=PTV_TRANSPORT_MODES)
    print(f"{gdf.columns=}")

    expected_count = {}
    cached_count = {}
    expected_total = 0
    cached_total = 0
    for mode in TRANSPORT_MODES:
        for ptv_mode in PTV_TRANSPORT_MODES:
            expected_count[(mode, ptv_mode)] = 0
            cached_count[(mode, ptv_mode)] = 0

    for _, row, _, _, mode, out_file in iterate_stop_modes(gdf):
        ptv_mode = row.get("MODE", None)
        if ptv_mode is None:
            print(f"❌ Missing PTV_MODE for stop {row.get('STOP_ID', 'unknown')}, skipping.")
            continue

        expected_count[(mode, ptv_mode)] += 1
        if out_file.exists():
            cached_count[(mode, ptv_mode)] += 1

    for mode in TRANSPORT_MODES:
        for ptv_mode in PTV_TRANSPORT_MODES:
            key = (mode, ptv_mode)
            expectations_str = f"expected {expected_count[key]:5d}\tcached {cached_count[key]:5d}\tremaining {expected_count[key] - cached_count[key]:5d}\t"
            cached_percent = (
                cached_count[key] / expected_count[key] * 100.0
                if expected_count[key] > 0
                else 100.0
            )
            cached_percent_str = f"{cached_percent:.2f}%"
            print(
                f"{mode.upper():<16} {ptv_mode.upper():<16}: {expectations_str} {cached_percent_str}"
            )
    expected_total = sum(expected_count.values())
    cached_total = sum(cached_count.values())
    cached_total_percent = cached_total / expected_total * 100.0 if expected_total > 0 else 100.0
    cached_total_percent_str = f"{cached_total_percent:.2f}%"
    t = "TOTAL"
    print(
        f"{t:<33}: expected {expected_total:5d}\tcached {cached_total:5d}\tremaining {expected_total - cached_total:5d}\t {cached_total_percent_str}"
    )


def dry_run(limit):
    """Perform a dry run to check how many isochrones would be scraped.

    Args:
        limit: Maximum number of isochrones to scrape
    """
    # Load stops - no filtering for scraping all stops
    gdf = load_stops(filter_modes=PTV_TRANSPORT_MODES)
    count = 0

    for idx, row, stop_id, stop_name, mode, out_file in iterate_stop_modes(gdf):
        if out_file.exists():
            # print(f"🤷🏻‍♂️ SKIP {mode} {stop_id} ({stop_name}): File exists {out_file}")
            continue

        if count >= limit:
            print(f"Reached limit of {limit} isochrones, stopping.")
            return
        ptv_mode = row.get("MODE", None)
        count += 1
        print(f"DRY RUN: {mode} {stop_id} ({ptv_mode}:{stop_name}) to {out_file}")


def scrape(limit):
    # Load stops - no filtering for scraping all stops
    gdf = load_stops(filter_modes=PTV_TRANSPORT_MODES)
    count = 0

    for idx, row, stop_id, stop_name, mode, out_file in iterate_stop_modes(gdf):
        if out_file.exists():
            # print(f"🤷🏻‍♂️ SKIP {mode} {stop_id} ({stop_name}): File exists {out_file}")
            continue

        try:
            if count >= limit:
                print(f"Reached limit of {limit} isochrones, stopping.")
                return

            # Create output directory if needed
            out_file.parent.mkdir(parents=True, exist_ok=True)

            # Get coordinates
            lat, lon = row.geometry.y, row.geometry.x
            ptv_mode = row.get("MODE", None)

            # Fetch isochrone data
            # result = get_isochrone(lat, lon, mode, TIME_LIMIT, BUCKETS, GRAPHHOPPER_API_KEY)
            result = get_isochrone_mapbox(
                lat,
                lon,
                MAPBOX_PROFILE_MAPPING[mode],
                ",".join(map(str, MAPBOX_COUNTOUR_TIMES)),
                MAPBOX_API_TOKEN,
            )

            # Save result
            out_file.write_text(json.dumps(result, indent=2))
            print(f"✅ Saved {ptv_mode} {mode} {stop_id} ({stop_name}) to {out_file}")

            count += 1
            time.sleep(3)  # Avoid hitting API rate limits

        except requests.HTTPError as e:
            print(f"❌ Failed for stop {stop_id} ({stop_name}), mode {mode}: HTTP error {e}")
        except Exception as e:
            print(f"❌ Failed for stop {stop_id} ({stop_name}), mode {mode}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch process isochrones for public transport stops"
    )
    parser.add_argument("--status", action="store_true", help="Perform only a status check")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without scraping")
    parser.add_argument(
        "--limit", default=170, type=int, help="Specify the number of isochrones to scrape"
    )

    args = parser.parse_args()

    if args.status:
        status()
        sys.exit(0)
    elif args.dry_run:
        dry_run(args.limit)
    else:
        scrape(args.limit)

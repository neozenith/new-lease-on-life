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
import re
import sys
import time
from pathlib import Path

import geopandas as gpd
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GRAPHHOPPER_API_KEY = os.environ.get("GRAPHHOPPER_API_KEY", "")
GRAPHHOPPER_HOST = os.environ.get("GRAPHHOPPER_HOST", "https://graphhopper.com")
ISOCHRONE_URL = f"{GRAPHHOPPER_HOST}/api/1/isochrone"
TRANSPORT_MODES = ["foot", "car", "bike"]
# TRANSPORT_MODES = ["foot"]
TRANSPORT_MODES = ["foot", "bike"]
PTV_TRANSPORT_MODES = ["METRO TRAM", "METRO TRAIN", "REGIONAL TRAIN"]
PTV_TRANSPORT_MODES = ["METRO TRAIN", "REGIONAL TRAIN"]
# PTV_TRANSPORT_MODES = ["METRO TRAM"]
TIME_LIMIT = 900
BUCKETS = 3


STOPS_GEOJSON = "data/geojson/ptv/stops_within_union.geojson"
OUTPUT_BASE = "data/geojson"


# Helper to normalise stop names for filenames
def normalise_name(name):
    return re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()


# Function to call GraphHopper Isochrone API
def get_isochrone(lat, lon, mode, time_limit, buckets, api_key, max_retries=10, backoff_factor=5):
    base_url = f"{ISOCHRONE_URL}?point={lat},{lon}"
    params = {
        "time_limit": time_limit,
        "vehicle": mode,
        "buckets": buckets,
        "key": api_key,
    }
    delay = 1
    for attempt in range(max_retries):
        response = requests.get(base_url, params=params, timeout=30)
        if response.status_code == 429:
            print(response.text)
            print(
                f"Rate limited (HTTP 429) on attempt {attempt + 1}. Retrying in {delay} seconds..."
            )
            time.sleep(delay)
            delay *= backoff_factor
            continue
        response.raise_for_status()
        return response.json()
    raise Exception(f"Failed after {max_retries} retries due to rate limiting.")


def status():
    # Load stops
    gdf = gpd.read_file(STOPS_GEOJSON)
    gdf = gdf[gdf["MODE"].isin(PTV_TRANSPORT_MODES)]
    print(f"{gdf.columns=}")
    stops_count = len(gdf)

    expected_count = 0
    cached_count = 0
    for idx, row in gdf.iterrows():
        stop_id = row.get("STOP_ID", idx)
        stop_name = row.get("STOP_NAME", f"stop_{idx}")
        norm_name = normalise_name(str(stop_name))
        for mode in TRANSPORT_MODES:
            out_dir = Path(OUTPUT_BASE) / mode
            # out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"isochrone_{stop_id}_{norm_name}.geojson"
            expected_count += 1
            if out_file.exists():
                cached_count += 1
    print(
        f"Found {stops_count} stops, expected {expected_count} isochrones, {cached_count} cached files and {expected_count - cached_count} remaining. {cached_count / expected_count * 100.0:.2f}%"
    )


def scrape(limit):
    # Load stops
    gdf = gpd.read_file(STOPS_GEOJSON)
    stops_count = len(gdf)
    count = 0
    for idx, row in gdf.iterrows():
        stop_id = row.get("STOP_ID", idx)
        stop_name = row.get("STOP_NAME", f"stop_{idx}")
        lat, lon = row.geometry.y, row.geometry.x
        norm_name = normalise_name(str(stop_name))
        for mode in TRANSPORT_MODES:
            out_dir = Path(OUTPUT_BASE) / mode
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"isochrone_{stop_id}_{norm_name}.geojson"
            if out_file.exists():
                # print(f"🤷🏻‍♂️ SKIP {mode} {stop_id} ({stop_name}): File exists {out_file}")
                continue
            try:
                if count >= limit:
                    print(f"Reached limit of {limit} isochrones, stopping.")
                    return
                result = get_isochrone(lat, lon, mode, TIME_LIMIT, BUCKETS, GRAPHHOPPER_API_KEY)
                out_file.write_text(json.dumps(result, indent=2))
                print(f"✅ Saved {mode} {stop_id} ({stop_name}) to {out_file}")
                count += 1
                time.sleep(3)  # Avoid hitting API rate limits
            except Exception as e:
                print(f"❌ Failed for stop {stop_id} ({stop_name}), mode {mode}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch process isochrones for public transport stops"
    )
    parser.add_argument("--status", action="store_true", help="Perform only a status check")
    parser.add_argument(
        "--limit", default=170, type=int, help="Specify the number of isochrones to scrape"
    )

    args = parser.parse_args()

    if args.status:
        status()
        sys.exit(0)
    else:
        scrape(args.limit)

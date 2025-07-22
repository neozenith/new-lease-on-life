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

MAPBOX_LIMIT=60.0/300.0 # 300 requests per minute
MAPBOX_API_TOKEN = os.environ.get("MAPBOX_API_TOKEN", "")
MAPBOX_API_HOST = os.environ.get("MAPBOX_API_HOST", "https://api.mapbox.com")
MAPBOX_ISOCHRONE_URL = f"{MAPBOX_API_HOST}/isochrone/v1/mapbox"

TRANSPORT_MODES = ["foot", "bike", "car"]
TRANSPORT_MODES = ["foot", "bike"]
MAPBOX_PROFILE_MAPPING = {
    "foot": "walking",
    "bike": "cycling",
    "car": "driving",
}
PTV_TRANSPORT_MODES = ["INTERSTATE TRAIN", "REGIONAL TRAIN", "METRO TRAIN", "METRO TRAM"]
TIME_LIMIT = 900
BUCKETS = 3
MAPBOX_COUNTOUR_TIMES = [5, 10, 15]  # Minutes for Mapbox isochrones


STOPS_GEOJSON = "data/geojson/ptv/stops_within_union.geojson"
STOPS_GEOJSON = "data/public_transport_stops.geojson"
OUTPUT_BASE = "data/geojson"


# Helper to normalise stop names for filenames
def normalise_name(name):
    return re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()


def make_request_with_retry(url, params, max_retries=10, backoff_factor=5, timeout=30):
    """Make HTTP request with exponential backoff retry for rate limiting.
    
    Args:
        url: The URL to request
        params: Query parameters for the request
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff delay
        timeout: Request timeout in seconds
        
    Returns:
        Response JSON data
        
    Raises:
        Exception: If all retries are exhausted due to rate limiting
        requests.HTTPError: For non-429 HTTP errors
    """
    delay = 1
    for attempt in range(max_retries):
        response = requests.get(url, params=params, timeout=timeout)
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


def load_stops(filter_modes=None):
    """Load stops from GeoJSON file and optionally filter by transport modes.
    
    Args:
        filter_modes: List of transport modes to filter by (e.g., PTV_TRANSPORT_MODES)
                     If None, returns all stops.
    
    Returns:
        GeoDataFrame of stops
    """
    gdf = gpd.read_file(STOPS_GEOJSON)
    gdf = gdf[
        ~gdf["STOP_NAME"].str.contains("Rail Replacement Bus Stop")
    ]
    before = len(gdf)
    gdf = gdf.groupby("STOP_NAME", as_index=False).first() # Consolidate duplicate stops that are effectively the same stop
    after = len(gdf)
    
    # Sort by custom order defined in PTV_TRANSPORT_MODES
    mode_order = {mode: idx for idx, mode in enumerate(PTV_TRANSPORT_MODES)}
    gdf = gdf.sort_values("MODE", key=lambda x: x.map(mode_order))

    print(f"Filtered stops: {before} -> {after} unique stops")
    if filter_modes:
        gdf = gdf[gdf["MODE"].isin(filter_modes)]
    return gdf


def get_isochrone_filepath(stop_id, stop_name, mode):
    """Generate the output filepath for an isochrone.
    
    Args:
        stop_id: The stop ID
        stop_name: The stop name
        mode: The transport mode
        
    Returns:
        Path object for the isochrone file
    """
    norm_name = normalise_name(str(stop_name))
    out_dir = Path(OUTPUT_BASE) / mode
    return out_dir / f"isochrone_{stop_id}_{norm_name}.geojson"


def iterate_stop_modes(gdf: gpd.GeoDataFrame) -> tuple[int, gpd.GeoSeries, str, str, str, Path]:
    """Iterate through all stops and transport modes.
    
    Args:
        gdf: GeoDataFrame of stops
        
    Yields:
        Tuple of (idx, row, stop_id, stop_name, mode, out_file)
    """
    for idx, row in gdf.iterrows():
        stop_id = row.get("STOP_ID", idx)
        stop_name = row.get("STOP_NAME", f"stop_{idx}")
        for mode in TRANSPORT_MODES:
            out_file = get_isochrone_filepath(stop_id, stop_name, mode)
            yield idx, row, stop_id, stop_name, mode, out_file


def status():
    # Load stops
    gdf = load_stops(filter_modes=PTV_TRANSPORT_MODES)
    print(f"{gdf.columns=}")
    

    expected_count = {}
    cached_count = {}
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
                cached_percent = cached_count[key] / expected_count[key] * 100.0 if expected_count[key] > 0 else 100.0
                cached_percent_str = f"{cached_percent:.2f}%"
                print(f"{mode.upper():<16} {ptv_mode.upper():<16}: {expectations_str} {cached_percent_str}")

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
            
            # Fetch isochrone data
            # result = get_isochrone(lat, lon, mode, TIME_LIMIT, BUCKETS, GRAPHHOPPER_API_KEY)
            result = get_isochrone_mapbox(lat, lon, MAPBOX_PROFILE_MAPPING[mode], ",".join(map(str, MAPBOX_COUNTOUR_TIMES)), MAPBOX_API_TOKEN)

            # Save result
            out_file.write_text(json.dumps(result, indent=2))
            print(f"✅ Saved {mode} {stop_id} ({stop_name}) to {out_file}")
            
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

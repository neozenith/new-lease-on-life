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
#   "polyline",
# ]
# ///

# for each stop calculate the commute time to Southern cross station
# and create a modified stops dataset to visualise the commute isochrones.

import asyncio
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import geopandas as gpd
import googlemaps
import polyline
import yaml
from dotenv import load_dotenv
from shapely.geometry import LineString, Point

# Load environment variables from .env file
load_dotenv()

# Setup logging
log = logging.getLogger(__name__)

# Get the path of this script
SCRIPT_DIR = Path(__file__).parent.resolve()

# Constants
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
CANDIDATES_YAML = SCRIPT_DIR.parent / "candidates.yml"
COMMUTES_YAML = SCRIPT_DIR.parent / "known_commutes.yml"
OUTPUT_DIR = SCRIPT_DIR.parent / "data/candidate_real_estate"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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

    def calculate_commute_times(
        self, origin: str, destinations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Calculate commute times from origin to multiple destinations using Google Maps API.

        Args:
            origin: Origin address
            destinations: List of destination dictionaries with name and address
        Returns:
            List of commute results with travel times for different modes
        """
        if not self.gmaps:
            log.warning("Google Maps client not initialized. Skipping commute calculations.")
            return []

        commute_results = []

        for destination in destinations:
            dest_name = destination.get("name", "Unknown")
            dest_address = destination.get("address", "")

            if not dest_address:
                log.warning(f"No address found for destination {dest_name}. Skipping.")
                continue

            log.info(f"Calculating commute from {origin} to {dest_name} ({dest_address})")

            commute_data = {
                "destination_name": dest_name,
                "destination_address": dest_address,
                "modes": {},
            }

            # Calculate for different transport modes
            for mode in ["driving", "transit", "walking", "bicycling"]:
                try:
                    # Calculate for both morning (8 AM) and evening (5 PM) peak times
                    morning_departure = datetime.now().replace(
                        hour=8, minute=0, second=0
                    ) + timedelta(days=1)  # Next day morning
                    evening_departure = datetime.now().replace(
                        hour=17, minute=0, second=0
                    ) + timedelta(days=1)  # Next day evening

                    directions_morning = self.gmaps.directions(
                        origin, dest_address, mode=mode, departure_time=morning_departure
                    )

                    directions_evening = self.gmaps.directions(
                        dest_address, origin, mode=mode, departure_time=evening_departure
                    )

                    # Extract duration from the response
                    morning_duration = (
                        directions_morning[0]["legs"][0]["duration"]["value"]
                        if directions_morning
                        else None
                    )
                    evening_duration = (
                        directions_evening[0]["legs"][0]["duration"]["value"]
                        if directions_evening
                        else None
                    )

                    commute_data["modes"][mode] = {
                        "to_work_seconds": morning_duration,
                        "to_work_text": directions_morning[0]["legs"][0]["duration"]["text"]
                        if directions_morning
                        else None,
                        "from_work_seconds": evening_duration,
                        "from_work_text": directions_evening[0]["legs"][0]["duration"]["text"]
                        if directions_evening
                        else None,
                        "daily_commute_seconds": (morning_duration or 0) + (evening_duration or 0),
                        "weekly_commute_seconds": (
                            (morning_duration or 0) + (evening_duration or 0)
                        )
                        * 5,  # Assuming 5 workdays
                    }

                    # Add a small delay to avoid hitting rate limits
                    time.sleep(0.2)

                except Exception as e:
                    log.error(f"Error calculating {mode} commute: {e}")
                    commute_data["modes"][mode] = {"error": str(e)}

            commute_results.append(commute_data)

        return commute_results

    async def process_candidate(
        self, url: str, commute_destinations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Process a single real estate candidate URL.

        Args:
            url: The realestate.com.au URL
            commute_destinations: List of commute destinations

        Returns:
            Dictionary with property details and commute times
        """
        log.info(f"Processing candidate: {url}")

        # Extract property address
        address = await self.extract_address_from_url(url)

        if not address:
            log.warning(f"Could not extract address for URL: {url}")
            return {
                "url": url,
                "error": "Could not extract address",
                "processed_at": datetime.now().isoformat(),
            }

        log.info(f"Extracted address: {address}")

        # Calculate commute times
        commute_times = self.calculate_commute_times(address, commute_destinations)

        # Prepare result
        result = {
            "url": url,
            "address": address,
            "commute_times": commute_times,
            "processed_at": datetime.now().isoformat(),
        }

        return result

    def save_result(self, result: dict[str, Any]) -> str:
        """
        Save processing result to JSON file.

        Args:
            result: Processing result dictionary

        Returns:
            Path to the saved file
        """
        if result.get("error"):
            log.error(f"Error processing result: {result['error']}")
            return ""

        # Generate a filepath based on the URL
        filepath = self.output_file_for_url(result["url"])

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        log.info(f"Saved result to {filepath}")
        return str(filepath)

    def output_file_for_url(self, url: str) -> Path:
        """
        Generate a filename for the output based on the address.

        Args:
            address: The property address

        Returns:
            A valid filename string
        """
        url_parts = url.replace("https://", "").replace("http://", "").split("/")
        filename = f"{'_'.join(url_parts[1:]).replace('.', '_')}.json"

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

    def save_geojson_result(self, result: dict[str, Any]) -> str:
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
        if lat is not None and lon is not None:
            records.append(
                {
                    **{k: v for k, v in result.items() if k not in ["lat", "lon", "commute_times"]},
                    "geometry": Point(lon, lat),
                    "feature_type": "property",
                }
            )

        # Add commute LineString features if possible, using Google Maps API polyline
        for commute in result.get("commute_times", []):
            dest_lat = commute.get("destination_lat") or commute.get("lat")
            dest_lon = commute.get("destination_lon") or commute.get("lon")
            dest_address = commute.get("destination_address")
            # Geocode destination if needed
            if (dest_lat is None or dest_lon is None) and dest_address and self.gmaps:
                dest_lat, dest_lon = self.geocode_address(dest_address)
            # Use Google Maps Directions API to get polylines for different modes
            if (
                lat is not None
                and lon is not None
                and dest_lat is not None
                and dest_lon is not None
            ):
                # Collect polylines for both driving and transit modes
                for mode in ["driving", "transit"]:
                    try:
                        directions = self.gmaps.directions(
                            (lat, lon), (dest_lat, dest_lon), mode=mode
                        )

                        if directions and "overview_polyline" in directions[0]:
                            poly = directions[0]["overview_polyline"]["points"]
                            coords = polyline.decode(poly)
                            line = LineString([(lng, lat) for lat, lng in coords])
                            records.append(
                                {
                                    **{
                                        k: v
                                        for k, v in commute.items()
                                        if k
                                        not in ["lat", "lon", "destination_lat", "destination_lon"]
                                    },
                                    "geometry": line,
                                    "feature_type": f"commute_{mode}",
                                    "travel_mode": mode,
                                    "distance": directions[0]["legs"][0]["distance"]["text"]
                                    if directions[0]["legs"]
                                    else None,
                                    "duration": directions[0]["legs"][0]["duration"]["text"]
                                    if directions[0]["legs"]
                                    else None,
                                }
                            )

                            # Add each step polyline for more detailed route visualization
                            if directions[0]["legs"]:
                                for i, step in enumerate(directions[0]["legs"][0].get("steps", [])):
                                    if "polyline" in step and "points" in step["polyline"]:
                                        step_coords = polyline.decode(step["polyline"]["points"])
                                        step_line = LineString(
                                            [(lng, lat) for lat, lng in step_coords]
                                        )
                                        records.append(
                                            {
                                                "geometry": step_line,
                                                "feature_type": f"commute_step_{mode}",
                                                "step_index": i,
                                                "travel_mode": mode,
                                                "step_mode": step.get("travel_mode", mode),
                                                "html_instructions": step.get(
                                                    "html_instructions", ""
                                                ),
                                                "distance": step["distance"]["text"]
                                                if "distance" in step
                                                else "",
                                                "duration": step["duration"]["text"]
                                                if "duration" in step
                                                else "",
                                            }
                                        )
                    except Exception as e:
                        log.error(
                            f"Error getting {mode} polyline for {result['address']} to {dest_address}: {e}"
                        )

        # Only save if there is at least one geometry
        records = [r for r in records if r["geometry"] is not None]
        if not records:
            log.warning(f"No geometry for {result['address']}, not saving GeoJSON.")
            return ""
        gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
        gdf.to_file(filepath, driver="GeoJSON")
        log.info(f"Saved GeoJSON result to {filepath}")
        return str(filepath)


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
    candidate_addresses = load_yaml_file(CANDIDATES_YAML)
    if not candidate_addresses or not isinstance(candidate_addresses, list):
        log.error(
            f"Invalid or missing candidates in {CANDIDATES_YAML}. Expected a list of addresses."
        )
        return

    log.info(f"Loaded {len(candidate_addresses)} candidate addresses from {CANDIDATES_YAML}")

    # Load commute destinations
    commute_destinations = load_yaml_file(COMMUTES_YAML)
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
    for address in candidate_addresses:
        try:
            file_path = processor.output_file_for_url(address).with_suffix(".geojson")

            if (
                file_path.exists()
                and file_path.stat().st_mtime > Path(CANDIDATES_YAML).stat().st_mtime
            ):
                log.info(f"SKIP {address}, already processed: {file_path}")
                continue

            log.info(f"Processing: {address}")

            # Calculate commute times for this address
            commute_times = processor.calculate_commute_times(address, formatted_destinations)

            # Try to get lat/lon for the address if available in formatted_destinations
            lat = None
            lon = None
            for dest in formatted_destinations:
                if dest["address"] == address and dest.get("lat") and dest.get("lon"):
                    lat = dest["lat"]
                    lon = dest["lon"]
                    break

            # Prepare result
            result = {
                "address": address,
                "lat": lat,
                "lon": lon,
                "commute_times": commute_times,
                "processed_at": datetime.now().isoformat(),
            }

            # Save the result as GeoJSON
            processor.save_geojson_result(result)

            results.append(result)

            # Add a small delay between API requests
            delay = 1 + (secrets.randbelow(20) / 10)
            log.debug(f"Waiting {delay:.1f} seconds before next request")
            await asyncio.sleep(delay)

        except Exception as e:
            log.error(f"Error processing candidate address {address}: {e}")

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
    # Using asyncio.run (Python 3.12 as per script header)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
    )
    asyncio.run(main())

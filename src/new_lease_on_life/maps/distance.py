# Standard Library
import asyncio
import logging
import os
import sys

from pathlib import Path

# Third Party
import httpx

from ruamel.yaml import YAML

# Our Libraries
from new_lease_on_life.cache import DuckDBCache
from new_lease_on_life.utils import ISO8601_DATE_FORMAT, LOG_FORMAT


log = logging.getLogger(__name__)

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
CACHE_DB_PATH = Path(__file__).parent / "distance_cache.duckdb"
cache = DuckDBCache(CACHE_DB_PATH)

if not API_KEY:
    raise OSError("GOOGLE_MAPS_API_KEY environment variable not set.")


async def get_route_distance_time(origin, destination, travel_mode="DRIVE"):
    # Check cache first
    res = cache.get_route(origin, destination, travel_mode)
    if res:
        return res[0], res[1]
    # Not cached, fetch from API
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
    }
    data = {"origin": {"address": origin}, "destination": {"address": destination}, "travelMode": travel_mode}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
    route = result["routes"][0]
    distance = route["distanceMeters"]
    duration = route["duration"]
    # Store in cache
    cache.set_route(origin, destination, travel_mode, distance, duration)
    return distance, duration


def load_yaml_list(yaml_path: Path) -> list[str]:
    yaml = YAML(typ="safe")
    data = yaml.load(yaml_path.read_text())
    if not isinstance(data, list):
        raise ValueError(f"YAML file {yaml_path} must contain a top-level list.")
    return data


async def process_rental(rental, destinations, travel_modes):
    results = []
    for dest in destinations:
        for mode in travel_modes:
            try:
                distance, duration = await get_route_distance_time(rental, dest, travel_mode=mode)
                results.append(
                    {
                        "origin": rental,
                        "destination": dest,
                        "mode": mode,
                        "distance_km": distance / 1000 if distance else None,
                        "duration": duration,
                    }
                )
                log.info(f"{mode}: {rental} -> {dest}: {distance / 1000:.2f} km, {duration}")
            except Exception as e:
                log.error(f"Error for {mode} {rental} -> {dest}: {e}")
    return results


async def main(candidate_rentals, destinations, travel_modes):
    tasks = [process_rental(rental, destinations, travel_modes) for rental in candidate_rentals]
    all_results = await asyncio.gather(*tasks)
    # Flatten the list of results
    results = [item for sublist in all_results for item in sublist]
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=ISO8601_DATE_FORMAT)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if len(sys.argv) != 3:
        print("Usage: python distance.py <candidate_rentals.yaml> <destinations.yaml>")
        sys.exit(1)
    candidate_rentals = load_yaml_list(Path(sys.argv[1]))
    destinations = load_yaml_list(Path(sys.argv[2]))
    travel_modes = ["DRIVE", "TRANSIT", "WALK", "BICYCLE"]
    asyncio.run(main(candidate_rentals, destinations, travel_modes))

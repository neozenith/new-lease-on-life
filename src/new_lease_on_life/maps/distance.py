# Standard Library
import asyncio
import json
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
CACHE_DB_PATH = Path(__file__).parents[3] / 'distance_cache.duckdb'
cache = DuckDBCache(CACHE_DB_PATH)

if not API_KEY:
    raise OSError("GOOGLE_MAPS_API_KEY environment variable not set.")


async def get_route_distance_time(origin, destination, travel_mode="DRIVE"):
    # Geocode origin and destination if not already in cache
    origin_loc = cache.get_location(origin)
    if not origin_loc or origin_loc["lat"] is None or origin_loc["lng"] is None:
        try:
            origin_lat, origin_lng = await geocode_address(origin)
            cache.set_location_latlng(origin, origin_lat, origin_lng)
            origin_loc = cache.get_location(origin)
        except Exception as e:
            log.error(f"Failed to geocode origin '{origin}': {e}")
            return None
    dest_loc = cache.get_location(destination)
    if not dest_loc or dest_loc["lat"] is None or dest_loc["lng"] is None:
        try:
            dest_lat, dest_lng = await geocode_address(destination)
            cache.set_location_latlng(destination, dest_lat, dest_lng)
            dest_loc = cache.get_location(destination)
        except Exception as e:
            log.error(f"Failed to geocode destination '{destination}': {e}")
            return None
    if not origin_loc or not dest_loc:
        log.error(f"Missing geocoded location for origin '{origin}' or destination '{destination}'")
        return None
    # Check route cache (now uses address text)
    res = cache.get_route(origin, destination, travel_mode)
    if res:
        return res[0], res[1], res[2]
    # Not cached, fetch from API
    url = 'https://routes.googleapis.com/directions/v2:computeRoutes'
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': API_KEY,
        'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline'
    }
    data = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": travel_mode
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
    if not result.get('routes') or not result['routes']:
        log.error(f"No route found for {origin} -> {destination} [{travel_mode}]")
        return None
    route = result['routes'][0]
    distance = route.get('distanceMeters')
    duration = route.get('duration')
    encoded_polyline = route.get('polyline', {}).get('encodedPolyline')
    geojson = polyline_to_geojson(encoded_polyline) if encoded_polyline else None
    # Store in cache (now uses address text)
    cache.set_route(origin, destination, travel_mode, distance, duration, json.dumps(geojson) if geojson else None)
    return distance, duration, geojson


async def geocode_address(address: str) -> tuple[float, float]:


    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": API_KEY}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    if data["status"] == "OK":
        loc = data["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    raise ValueError(f"Could not geocode address: {address}")


def polyline_to_geojson(encoded_polyline: str) -> dict:
    import polyline
    coords = polyline.decode(encoded_polyline)
    return {
        "type": "LineString",
        "coordinates": [[lng, lat] for lat, lng in coords]
    }


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
                route_result = await get_route_distance_time(rental, dest, travel_mode=mode)
                if not route_result:
                    log.error(f"Skipping {mode} {rental} -> {dest}: route or geocode failed.")
                    continue
                distance, duration, geojson = route_result
                results.append({
                    "origin": rental,
                    "destination": dest,
                    "mode": mode,
                    "distance_km": distance/1000 if distance else None,
                    "duration": duration,
                    "geojson": geojson
                })
                log.info(f"{mode}: {rental} -> {dest}: {distance/1000 if distance else 'N/A'} km, {duration}")
            except Exception as e:
                log.error(f"Error for {mode} {rental} -> {dest}: {e}")
    return results


async def main(candidate_rentals, destinations, travel_modes):
    # Geocode all unique addresses first
    addresses = set(candidate_rentals) | set(destinations)
    geocode_tasks = [geocode_address(address) for address in addresses]
    geocode_results = await asyncio.gather(*geocode_tasks, return_exceptions=True)
    for address, result in zip(addresses, geocode_results):
        if isinstance(result, Exception):
            log.error(f"Geocoding failed for {address}: {result}")
        else:
            lat, lng = result
            cache.set_location_latlng(address, lat, lng)
            log.info(f"Geocoded {address}: {lat}, {lng}")
    # Now process all rentals/routes
    rental_tasks = [process_rental(rental, destinations, travel_modes) for rental in candidate_rentals]
    all_results = await asyncio.gather(*rental_tasks)
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

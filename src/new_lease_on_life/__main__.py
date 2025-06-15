# Standard Library
import asyncio
import json
import logging
import os
import sys

# Third Party
import aiohttp
import duckdb

from utils import ISO8601_DATE_FORMAT, LOG_FORMAT, export_env_vars


log = logging.getLogger(__name__)

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
DESTINATIONS = [
    "V2 AI Office, Melbourne VIC",
    "Melbourne Airport, Tullamarine VIC",
    "Melbourne Business School, Carlton VIC",
]
ORIGINS = ["27 Victoria St, Adamstown NSW", "96 Trafford St, Angle Park SA"]
MODES = ["driving", "transit", "walking", "bicycling"]

# Cache connection (DuckDB file-based)
con = duckdb.connect("cache.db")
con.execute("""
CREATE TABLE IF NOT EXISTS distance_cache (
    origin TEXT,
    destination TEXT,
    mode TEXT,
    response TEXT,
    PRIMARY KEY (origin, destination, mode)
)
""")


def generate_key(origin, destination, mode):
    return (origin, destination, mode)


def is_cached(origin, destination, mode):
    result = con.execute(
        """
        SELECT response FROM distance_cache
        WHERE origin = ? AND destination = ? AND mode = ?
    """,
        (origin, destination, mode),
    ).fetchone()
    return json.loads(result[0]) if result else None


def cache_response(origin, destination, mode, response):
    con.execute(
        """
        INSERT OR REPLACE INTO distance_cache (origin, destination, mode, response)
        VALUES (?, ?, ?, ?)
    """,
        (origin, destination, mode, json.dumps(response)),
    )


def encode_params(origin, destination, mode):
    return {
        "origins": origin,
        "destinations": destination,
        "mode": mode,
        "departure_time": "now" if mode in ["driving", "transit"] else None,
        "key": API_KEY,
    }


async def fetch_distance(session, origin, destination, mode, retries=3):
    cached = is_cached(origin, destination, mode)
    if cached:
        return origin, destination, mode, cached

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = encode_params(origin, destination, mode)

    for attempt in range(retries):
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                if data["rows"][0]["elements"][0].get("status") == "OK":
                    cache_response(origin, destination, mode, data)
                    return origin, destination, mode, data
                elif data["rows"][0]["elements"][0].get("status") in ("OVER_QUERY_LIMIT", "UNKNOWN_ERROR"):
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    return origin, destination, mode, data  # Still cache, maybe useful to diagnose
        except TimeoutError:
            if attempt == retries - 1:
                print(f"Timeout for {origin} → {destination} ({mode})")
        except Exception as e:
            print(f"Unexpected error: {e}")
    return origin, destination, mode, {"error": "request_failed"}


async def get_all_distances(origins, destinations, modes):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for origin in origins:
            for destination in destinations:
                for mode in modes:
                    tasks.append(fetch_distance(session, origin, destination, mode))

        results = await asyncio.gather(*tasks)

        # Display results
        for origin, destination, mode, result in results:
            try:
                element = result["rows"][0]["elements"][0]
                if element.get("status") == "OK":
                    distance = element["distance"]["text"]
                    duration = element["duration"]["text"]
                    print(f"{origin} → {destination} [{mode}]: {distance}, {duration}")
                else:
                    print(f"{origin} → {destination} [{mode}]: Error - {element.get('status')}")
            except Exception:
                print(f"{origin} → {destination} [{mode}]: Invalid response or error")


if __name__ == "__main__":
    DEBUG_MODE = False
    if "--debug" in sys.argv:  # Finished with debug flag so it is safe to remove at this point.
        DEBUG_MODE = True
        sys.argv.remove("--debug")

    log_level = logging.DEBUG if DEBUG_MODE else logging.INFO
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt=ISO8601_DATE_FORMAT,
    )
    export_env_vars()
    asyncio.run(get_all_distances(ORIGINS, DESTINATIONS, MODES))

import logging
import re
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import requests

logger = logging.getLogger(__name__)

TRANSPORT_MODES = ["foot", "bike", "car"]

MAPBOX_PROFILE_MAPPING = {
    "foot": "walking",
    "bike": "cycling",
    "car": "driving",
}
PTV_TRANSPORT_MODES = ["INTERSTATE TRAIN", "REGIONAL TRAIN", "METRO TRAIN", "METRO TRAM"]
TIME_LIMIT = 900
BUCKETS = 3
MAPBOX_COUNTOUR_TIMES = [5, 10, 15]  # Minutes for Mapbox isochrones

STOPS_GEOJSON = "data/public_transport_stops.geojson"

OUTPUT_BASE = "data/geojson"


# Helper to normalise stop names for filenames
def normalise_name(name):
    return re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()


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


def load_stops(filter_modes=None):
    """Load stops from GeoJSON file and optionally filter by transport modes.

    Args:
        filter_modes: List of transport modes to filter by (e.g., PTV_TRANSPORT_MODES)
                     If None, returns all stops.

    Returns:
        GeoDataFrame of stops
    """
    gdf = gpd.read_file(STOPS_GEOJSON)
    gdf = gdf[~gdf["STOP_NAME"].str.contains("Rail Replacement Bus Stop")]
    before = len(gdf)
    gdf = gdf.groupby(
        "STOP_NAME", as_index=False
    ).first()  # Consolidate duplicate stops that are effectively the same stop
    after = len(gdf)

    # Sort by custom order defined in PTV_TRANSPORT_MODES
    mode_order = {mode: idx for idx, mode in enumerate(PTV_TRANSPORT_MODES)}
    gdf = gdf.sort_values("MODE", key=lambda x: x.map(mode_order))

    print(f"Filtered stops: {before} -> {after} unique stops")
    if filter_modes:
        gdf = gdf[gdf["MODE"].isin(filter_modes)]
    return gdf


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


def dirty(output_path: list[Path] | Path, input_paths: list[Path] | Path) -> bool:
    """Check if the output_path file(s) are older than any of the input files.

    Args:
        output_path: List of output file paths or a single output file path
        input_paths: List of input file paths or a single input file path

    Returns:
        True if output_path is older than any input, False otherwise
    """

    if isinstance(output_path, Path):
        output_path = [output_path]

    if any(not p.exists() for p in output_path):
        return True  # If any output file doesn't exist, it's considered dirty

    if isinstance(input_paths, Path):
        input_paths = [input_paths]

    min_output_mtime = min(f.stat().st_mtime for f in output_path)
    max_input_mtime = max(f.stat().st_mtime for f in input_paths)

    return (
        min_output_mtime < max_input_mtime
    )  # This means output is dirty if it's older than newest input file


def unzip_archive(zip_path: Path, extract_to: Path | None = None) -> None:
    """
    Unzip a ZIP archive to the specified directory.

    Args:
        zip_path: Path to the ZIP file
        extract_to: Directory to extract files to
    """

    if extract_to is None:
        extract_to = zip_path.parent / zip_path.stem
    logger.info(f"Unzipping {zip_path} to {extract_to}")

    if not dirty([f for f in extract_to.rglob("*") if f.is_file()], zip_path):
        logger.info(f"Skipping extraction, {extract_to} is up to date.")
        return

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

    logger.info(f"Unzipped {zip_path} successfully")


def save_geodataframe(gdf: gpd.GeoDataFrame, output_file: Path) -> Path:
    """
    Save a GeoDataFrame to GeoJSON and Parquet formats.

    Args:
        gdf: The GeoDataFrame to save
        output_file: The base path for the output files (without extension)

    Returns:
        Path to the saved GeoJSON file
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent directory exists
    gdf.to_file(output_file, driver="GeoJSON")
    gdf.to_parquet(output_file.with_suffix(".parquet"), engine="pyarrow", index=False)

    return output_file

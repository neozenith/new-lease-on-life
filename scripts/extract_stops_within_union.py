# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas",
#   "pyarrow",
#   "shapely",
#   "requests",
#   "tqdm"
# ]
# ///

import argparse
import logging
from pathlib import Path

import geopandas as gpd
from utils import dirty, save_geodataframe

log = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent.resolve()

# INPUTS
UNIONED_GEOJSON = (
    SCRIPT_DIR.parent / "data/geojson/ptv/boundaries/unioned_postcodes_with_trams_trains.parquet"
)
STOPS_GEOJSON = SCRIPT_DIR.parent / "data/public_transport_stops.parquet"

# OUTPUTS
OUTPUT_STOPS_GEOJSON = SCRIPT_DIR.parent / "data/geojson/ptv/stops_within_union.geojson"


def extract_stops_within_union():
    if not dirty(OUTPUT_STOPS_GEOJSON, [UNIONED_GEOJSON, STOPS_GEOJSON]):
        log.info(f"{OUTPUT_STOPS_GEOJSON} is up to date. Skipping extraction.")
        return

    # Load the unioned postcode polygon
    unioned_gdf = gpd.read_parquet(UNIONED_GEOJSON)

    # Load the public transport stops
    stops_gdf = gpd.read_file(STOPS_GEOJSON)
    # Ensure CRS matches
    if stops_gdf.crs != unioned_gdf.crs:
        stops_gdf = stops_gdf.to_crs(unioned_gdf.crs)

    # Find stops within the unioned polygon
    # stops_within = [stops_gdf.within(unioned_gdf.union_all())]
    stops_within = stops_gdf

    if "MODE" in stops_within.columns:
        stops_within = stops_within[stops_within["MODE"] != "METRO BUS"]
        stops_within = stops_within[stops_within["MODE"] != "REGIONAL COACH"]
        stops_within = stops_within[stops_within["MODE"] != "REGIONAL BUS"]
        stops_within = stops_within[stops_within["MODE"] != "SKYBUS"]
        # stops_within = stops_within[stops_within["MODE"] != "METRO TRAM"]
        # stops_within = stops_within[stops_within["MODE"] != "REGIONAL TRAIN"]
        # stops_within = stops_within[stops_within["MODE"] != "METRO TRAIN"]
        # stops_within = stops_within[stops_within["MODE"] != "INTERSTATE TRAIN"]
        stops_within = stops_within[
            ~stops_within["STOP_NAME"].str.contains("Rail Replacement Bus Stop")
        ]

    # Group by STOP_NAME and take the first entry in each group
    if "STOP_NAME" in stops_within.columns:
        stops_within = stops_within.groupby("STOP_NAME", as_index=False).first()

    # Save the filtered stops to the output GeoJSON file
    save_geodataframe(stops_within, OUTPUT_STOPS_GEOJSON)

    log.info(f"Unique stop modes: {stops_within['MODE'].unique()}")
    log.info(f"Wrote {len(stops_within)} unique stops to {OUTPUT_STOPS_GEOJSON}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter transport stops within boundary unions (exclude buses)"
    )
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
    )
    extract_stops_within_union()

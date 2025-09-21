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
STOPS_GEOJSON = SCRIPT_DIR.parent / "data/public_transport_stops.geojson"
LINES_GEOJSON = SCRIPT_DIR.parent / "data/public_transport_lines.geojson"

ALL_INPUTS = [
    UNIONED_GEOJSON, 
    STOPS_GEOJSON, 
    LINES_GEOJSON
]

# OUTPUTS
OUTPUT_STOPS_GEOJSON = SCRIPT_DIR.parent / "data/geojson/ptv/stops_within_union.geojson"

OUTPUT_PTV_LINES_WITHIN_UNION = SCRIPT_DIR.parent / "data/geojson/ptv/lines_within_union.geojson"
OUTPUT_PTV_LINES_WITHIN_UNION_METRO_TRAM = SCRIPT_DIR.parent / "data/geojson/ptv/lines_within_union_metro_tram.geojson"
OUTPUT_PTV_LINES_WITHIN_UNION_METRO_TRAIN = SCRIPT_DIR.parent / "data/geojson/ptv/lines_within_union_metro_train.geojson"
OUTPUT_PTV_LINES_WITHIN_UNION_REGIONAL_TRAIN = SCRIPT_DIR.parent / "data/geojson/ptv/lines_within_union_regional_train.geojson"

ALL_OUTPUTS = [
    OUTPUT_STOPS_GEOJSON,
    OUTPUT_PTV_LINES_WITHIN_UNION,
    OUTPUT_PTV_LINES_WITHIN_UNION_METRO_TRAM,
    OUTPUT_PTV_LINES_WITHIN_UNION_METRO_TRAIN,
    OUTPUT_PTV_LINES_WITHIN_UNION_REGIONAL_TRAIN,
]


def extract_stops_within_union():
    if not dirty(ALL_OUTPUTS, ALL_INPUTS):
        log.info(f"{OUTPUT_STOPS_GEOJSON} is up to date. Skipping extraction.")
        return

    # Load the unioned postcode polygon
    unioned_gdf = gpd.read_parquet(UNIONED_GEOJSON)

    # Load the public transport stops
    stops_gdf = gpd.read_parquet(STOPS_GEOJSON) if STOPS_GEOJSON.suffix == ".parquet" else gpd.read_file(STOPS_GEOJSON)
    lines_gdf = gpd.read_parquet(LINES_GEOJSON) if LINES_GEOJSON.suffix == ".parquet" else gpd.read_file(LINES_GEOJSON)

    # Ensure CRS matches
    if stops_gdf.crs != unioned_gdf.crs:
        stops_gdf = stops_gdf.to_crs(unioned_gdf.crs)
    if lines_gdf.crs != unioned_gdf.crs:
        lines_gdf = lines_gdf.to_crs(unioned_gdf.crs)

    # Find stops within the unioned polygon
    stops_within = stops_gdf[stops_gdf.within(unioned_gdf.union_all())]
    # stops_within = stops_gdf

    lines_intersecting = lines_gdf[lines_gdf.intersects(unioned_gdf.union_all())]


    # Subset by PTV MODE
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

    lines_intersecting = lines_intersecting[lines_intersecting["MODE"].isin(["METRO TRAM", "METRO TRAIN"])]
    lines_intersecting = lines_intersecting[
            ~lines_intersecting["SHORT_NAME"].str.contains("Replacement Bus")
        ]

    # Group by STOP_NAME and take the first entry in each group
    if "STOP_NAME" in stops_within.columns:
        stops_within = stops_within.groupby("STOP_NAME", as_index=False).first()

    # Save the filtered stops to the output GeoJSON file
    save_geodataframe(stops_within, OUTPUT_STOPS_GEOJSON)

    log.info(f"Unique stop modes: {stops_within['MODE'].unique()}")
    log.info(f"Wrote {len(stops_within)} unique stops to {OUTPUT_STOPS_GEOJSON}")

    save_geodataframe(lines_intersecting, OUTPUT_PTV_LINES_WITHIN_UNION)
    save_geodataframe(lines_intersecting[lines_intersecting['MODE'] == "METRO TRAM"], OUTPUT_PTV_LINES_WITHIN_UNION_METRO_TRAM)
    save_geodataframe(lines_intersecting[lines_intersecting['MODE'].isin([ "METRO TRAIN"])], OUTPUT_PTV_LINES_WITHIN_UNION_METRO_TRAIN)

    log.info(f"Wrote {len(lines_intersecting)} lines to {OUTPUT_PTV_LINES_WITHIN_UNION}")


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

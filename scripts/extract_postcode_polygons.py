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
import json
import argparse
import logging
import pathlib
from pathlib import Path

import geopandas as gpd
import pandas as pd
from utils import dirty, save_geodataframe

log = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent.resolve()

# INPUTS
POSTCODES_CSV = SCRIPT_DIR.parent / "postcodes.csv"
STOPS_GEOJSON = SCRIPT_DIR.parent / "data/public_transport_stops.parquet"
POSTCODE_POLYGONS = (
    SCRIPT_DIR.parent
    / "data/originals_converted/boundaries/POA_2021_AUST_GDA2020_SHP/POA_2021_AUST_GDA2020.parquet"
)

BOUNDARIES_BASE = SCRIPT_DIR.parent / "data/originals_converted/boundaries"
BOUNDARIES = BOUNDARIES_BASE.rglob("**/*.parquet")

input_to_output_mapping = {
    "postcodes": [POSTCODE_POLYGONS, POSTCODES_CSV],
    "postcodes_with_trams": POSTCODE_POLYGONS,
    "postcodes_with_trams_trains": POSTCODE_POLYGONS,
}
for b in BOUNDARIES:
    output_target = b.stem.lower()
    input_to_output_mapping[output_target] = b


# OUTPUTS
OUTPUT_ROOT = SCRIPT_DIR.parent / "data/geojson/ptv/boundaries/"


def check_output_up_to_date():
    """
    Check if the output files are up to date with respect to the input files.
    """
    files_to_process = {}
    
    for target, input_file in input_to_output_mapping.items():
        selected_output_file = (
            OUTPUT_ROOT / f"selected_{target}.geojson"
        )  # Selects subset of polygons
        unioned_output_file = (
            OUTPUT_ROOT / f"unioned_{target}.geojson"
        )  # Unions the selected polygons
        if dirty([selected_output_file, unioned_output_file], input_file):
            files_to_process[target] = input_file
            log.info(f"{target} needs processing.")

    return files_to_process


def filter_for_target(
    target, gdf_polygons, gdf_stops, code_col=None, code_list=None
) -> gpd.GeoDataFrame:
    """
    Filter the GeoDataFrame of polygons based on the target and code list.
    """
    if target in ["postcodes"]:
        return gdf_polygons[gdf_polygons[code_col].astype(str).isin(code_list)].copy()
    else:
        return gpd.sjoin(gdf_polygons, gdf_stops, how="inner", predicate="intersects")


def extract_postcode_polygons():
    # Load the GeoJSON file
    work_to_do = check_output_up_to_date().items()
    if len(work_to_do) == 0:
        log.info("All outputs are up to date. No work to do.")
        return

    postcode_boundaries = gpd.read_parquet(POSTCODE_POLYGONS)

    # Load postcodes from CSV (expects a column named 'postcode')
    postcodes = pd.read_csv(POSTCODES_CSV)
    postcode_list = postcodes.iloc[:, 1].astype(str).tolist()
    suburbs_by_postcode = postcodes.groupby(postcodes.columns[1])[postcodes.columns[0]].apply(list).to_dict()
    suburbs_by_postcode = {str(k): ', '.join(v) for k, v in suburbs_by_postcode.items()}

    
    log.info(json.dumps(suburbs_by_postcode, indent=2))
    
    postcode_boundaries["suburbs"] = postcode_boundaries["POA_CODE21"].map(suburbs_by_postcode)


    gdf_stops = gpd.read_parquet(STOPS_GEOJSON)
    gdf_stops_trams_trains = gdf_stops[gdf_stops["MODE"].isin(["METRO TRAIN", "METRO TRAM", "REGIONAL TRAIN"])].copy()
    gdf_stops_trams = gdf_stops[gdf_stops["MODE"].isin(["METRO TRAM"])].copy()

    for target, input_file in work_to_do:
        log.info(f"Processing target: {target} with input file: {input_file}")
        if target == "postcodes":
            gdf_polygons = filter_for_target(
                target, postcode_boundaries, gdf_stops, "POA_CODE21", postcode_list
            )
        elif target == "postcodes_with_trams":
            gdf_polygons = filter_for_target(target, postcode_boundaries, gdf_stops_trams)
        elif target == "postcodes_with_trams_trains":
            gdf_polygons = filter_for_target(target, postcode_boundaries, gdf_stops_trams_trains)
        else:
            # For other targets, load the specific boundary file
            log.info(
                f"Loading input file: {input_file} {pathlib.Path(input_file).stat().st_size / 1024 / 1024:.2f} MB"
            )
            gdf_input = gpd.read_parquet(input_file)
            gdf_polygons = filter_for_target(target, gdf_input, gdf_stops_trams_trains)
        
        if target.startswith("postcodes"):
            gdf_polygons["suburbs"] = gdf_polygons["POA_CODE21"].map(suburbs_by_postcode)
            gdf_polygons = gdf_polygons[~gdf_polygons["suburbs"].isna()].copy()
            gdf_polygons = gdf_polygons.drop_duplicates(subset=["POA_CODE21"], keep="first")

        gdf = gdf_polygons.copy()
        unioned_geom = gdf.geometry.union_all()
        unioned_gdf = gpd.GeoDataFrame(geometry=[unioned_geom], crs=gdf.crs)

        selected_output_file = OUTPUT_ROOT / f"selected_{target}.geojson"
        unioned_output_file = OUTPUT_ROOT / f"unioned_{target}.geojson"

        save_geodataframe(gdf, selected_output_file)
        save_geodataframe(unioned_gdf, unioned_output_file)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Filter Australian postcode boundaries by transport stop presence"
    )
    args = parser.parse_args()

    extract_postcode_polygons()
    log.info("Postcode polygons extracted and saved.")

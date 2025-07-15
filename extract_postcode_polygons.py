# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas",
#   "pyarrow",
#   "shapely"
# ]
# ///

import json
import pathlib

import geopandas as gpd
import pandas as pd

# File paths
POSTCODES_CSV = "postcodes.csv"
STOPS_GEOJSON = "data/public_transport_stops.geojson"


POSTCODE_POLYGONS = (
    "data/originals_converted/boundaries/POA_2021_AUST_GDA2020_SHP/POA_2021_AUST_GDA2020.geojson"
)

BOUNDARIES_BASE = pathlib.Path("data/originals_converted/boundaries")
BOUNDARIES = BOUNDARIES_BASE.rglob("**/*.geojson")

OUTPUT_ROOT = pathlib.Path("data/geojson/ptv/boundaries/")

input_to_output_mapping = {
    "postcodes": [POSTCODE_POLYGONS, POSTCODES_CSV],
    "postcodes_with_trams": POSTCODE_POLYGONS,
    "postcodes_with_trams_trains": POSTCODE_POLYGONS,
}
for b in BOUNDARIES:
    output_target = b.stem.lower()
    input_to_output_mapping[output_target] = b


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

        stops_mtime = pathlib.Path(STOPS_GEOJSON).stat().st_mtime
        if isinstance(input_file, list):
            input_file_max_mtime = max(
                pathlib.Path(f).stat().st_mtime for f in input_file
            )
        else:
            input_file_max_mtime = pathlib.Path(input_file).stat().st_mtime

        input_file_max_mtime = max(input_file_max_mtime, stops_mtime)
        
        should_process = False
        if (
            not selected_output_file.exists()
            or selected_output_file.stat().st_mtime < input_file_max_mtime
        ):
            should_process = True
            files_to_process[target] = input_file

        if (
            not unioned_output_file.exists()
            or unioned_output_file.stat().st_mtime < input_file_max_mtime
        ):
            should_process = True
            files_to_process[target] = input_file

        if should_process:
            print(f"{target} needs processing.")

    return files_to_process

def filter_for_target(target, gdf_polygons, gdf_stops, code_col = None, code_list = None) -> gpd.GeoDataFrame:
    """
    Filter the GeoDataFrame of polygons based on the target and code list.
    """
    if target in ["postcodes"]:
        return gdf_polygons[gdf_polygons[code_col].astype(str).isin(code_list)]
    else:
        return gpd.sjoin(gdf_polygons, gdf_stops, how="inner", predicate="intersects")
    


def extract_postcode_polygons():
    # Load the GeoJSON file
    work_to_do = check_output_up_to_date().items()
    if len(work_to_do) == 0:
        print("All outputs are up to date. No work to do.")
        return
    
    postcode_boundaries = gpd.read_file(POSTCODE_POLYGONS)

    # Load postcodes from CSV (expects a column named 'postcode')
    postcodes = pd.read_csv(POSTCODES_CSV)
    postcode_list = postcodes.iloc[:, 1].astype(str).tolist()

    gdf_stops = gpd.read_file(STOPS_GEOJSON)
    gdf_stops_trams_trains = gdf_stops[gdf_stops["MODE"].isin(["METRO TRAIN", "METRO TRAM"])].copy()
    gdf_stops_trams = gdf_stops[gdf_stops["MODE"].isin(["METRO TRAM"])].copy()
    
    for target, input_file in work_to_do:
        print(f"Processing target: {target} with input file: {input_file}")
        if target == "postcodes":
            gdf_polygons = filter_for_target(target, postcode_boundaries, gdf_stops, "POA_CODE21", postcode_list)
        elif target == "postcodes_with_trams":
            gdf_polygons = filter_for_target(target, postcode_boundaries, gdf_stops_trams)
        elif target == "postcodes_with_trams_trains":
            gdf_polygons = filter_for_target(target, postcode_boundaries, gdf_stops_trams_trains)
        else:
            # For other targets, load the specific boundary file
            print(f"Loading input file: {input_file} {pathlib.Path(input_file).stat().st_size / 1024 / 1024:.2f} MB")
            gdf_input = gpd.read_file(input_file)
            gdf_polygons = filter_for_target(target, gdf_input, gdf_stops_trams_trains)

        gdf = gdf_polygons
    
        selected_output_file = OUTPUT_ROOT / f"selected_{target}.geojson"
        unioned_output_file = OUTPUT_ROOT / f"unioned_{target}.geojson"

        selected_output_file.parent.mkdir(parents=True, exist_ok=True)
        unioned_output_file.parent.mkdir(parents=True, exist_ok=True)

        gdf.to_file(selected_output_file, driver="GeoJSON")
        print(f"Saved selected {target} to {selected_output_file} {selected_output_file.stat().st_size / 1024 / 1024:.2f} MB")
        gdf.to_parquet(selected_output_file.with_suffix(".parquet"), engine="pyarrow", index=False)
        print(f"Saved selected {target} to {selected_output_file.with_suffix('.parquet')} {selected_output_file.with_suffix('.parquet').stat().st_size / 1024 / 1024:.2f} MB")

        unioned_geom = gdf.geometry.union_all()
        unioned_gdf = gpd.GeoDataFrame(geometry=[unioned_geom], crs=gdf.crs)

        unioned_gdf.to_file(unioned_output_file, driver="GeoJSON")
        print(f"Saved unioned {target} to {unioned_output_file}  {unioned_output_file.stat().st_size / 1024 / 1024:.2f} MB")
        unioned_gdf.to_parquet(
            unioned_output_file.with_suffix(".parquet"), engine="pyarrow", index=False
        )
        print(f"Saved unioned {target} to {unioned_output_file.with_suffix('.parquet')} {unioned_output_file.with_suffix('.parquet').stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    extract_postcode_polygons()
    print("Postcode polygons extracted and saved.")

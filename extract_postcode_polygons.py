# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas",
#   "pyarrow",
#   "shapely"
# ]
# ///

import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union
import pathlib

# File paths
POSTCODES_CSV = "postcodes.csv"
STOPS_GEOJSON = "data/public_transport_stops.geojson"


GEOJSON_PATH = "data/originals_converted/boundaries/POA_2021_AUST_GDA2020_SHP/POA_2021_AUST_GDA2020.geojson"

BOUNDARIES_BASE = pathlib.Path("data/originals_converted/boundaries")
BOUNDARIES = BOUNDARIES_BASE.rglob("**/*.geojson")

OUTPUT_ROOT = pathlib.Path("data/geojson/ptv/boundaries/")

def extract_postcode_polygons():
    # Load the GeoJSON file
    postcode_boundaries = gpd.read_file(GEOJSON_PATH)

    # Load postcodes from CSV (expects a column named 'postcode')
    postcodes = pd.read_csv(POSTCODES_CSV)
    postcode_list = postcodes.iloc[:, 1].astype(str).tolist()
    print(f"{postcode_list=}")

    gdf_stops = gpd.read_file(STOPS_GEOJSON)
    print(f"Loaded {gdf_stops['MODE'].unique()} modes from {STOPS_GEOJSON}")

    gdf_stops_trams_trains = gdf_stops[gdf_stops["MODE"].isin(["METRO TRAIN", "METRO TRAM"])].copy()
    print(f"Filtered {len(gdf_stops_trams_trains)} stops for {gdf_stops_trams_trains['MODE'].unique()} modes.")
    gdf_stops_trams = gdf_stops[gdf_stops["MODE"].isin(["METRO TRAM"])].copy()
    print(f"Filtered {len(gdf_stops_trams)} stops for {gdf_stops_trams['MODE'].unique()} modes.")


    # The postcode column in the GeoJSON is usually 'POA_CODE21' or similar
    postcode_col = None
    for col in postcode_boundaries.columns:
        if "POA" in col and "CODE" in col:
            postcode_col = col
            break
    if postcode_col is None:
        raise ValueError("Could not find postcode column in GeoJSON file.")
    print(f"Using postcode column: {postcode_col}")



    
    gdf_postcodes_with_trams_trains = gpd.sjoin(postcode_boundaries, gdf_stops_trams_trains, how="inner", predicate="intersects")


    output_target_bases = {
        # "postcodes": gdf_postcodes,
        # "postcodes_with_trams": gdf_postcodes_with_trams,
        "postcodes_with_trams_trains": gdf_postcodes_with_trams_trains
    }

    for b in BOUNDARIES:
        b_gdf = gpd.read_file(b)
        select__b_gdf = gpd.sjoin(b_gdf, gdf_stops_trams_trains, how="inner", predicate="intersects")
        output_target_bases[b.stem.lower()] = select__b_gdf

    for target, gdf in output_target_bases.items():
        selected_output_file = OUTPUT_ROOT / f"selected_{target}.geojson"
        unioned_output_file = OUTPUT_ROOT / f"unioned_{target}.geojson"

        selected_output_file.parent.mkdir(parents=True, exist_ok=True)
        unioned_output_file.parent.mkdir(parents=True, exist_ok=True)

        gdf.to_file(selected_output_file, driver="GeoJSON")
        gdf.to_parquet(selected_output_file.with_suffix('.parquet'), engine='pyarrow', index=False)
        print(f"Saved selected {target} to {selected_output_file}")

        unioned_geom = gdf.geometry.union_all()

        unioned_gdf = gpd.GeoDataFrame(geometry=[unioned_geom], crs=gdf.crs)
        unioned_gdf.to_file(unioned_output_file, driver="GeoJSON")
        unioned_gdf.to_parquet(unioned_output_file.with_suffix('.parquet'), engine='pyarrow', index=False)
        print(f"Saved unioned {target} to {unioned_output_file}")

if __name__ == "__main__":
    extract_postcode_polygons()
    print("Postcode polygons extracted and saved.")
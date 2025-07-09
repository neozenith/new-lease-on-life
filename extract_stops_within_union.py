# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas",
#   "pyarrow",
#   "shapely"
# ]
# ///

import geopandas as gpd
import pathlib

# File paths
UNIONED_GEOJSON = "data/geojson/ptv/boundaries/unioned_postcodes.geojson"
UNIONED_GEOJSON = "data/geojson/ptv/boundaries/unioned_postcodes_with_trams.geojson"
UNIONED_GEOJSON = "data/geojson/ptv/boundaries/unioned_postcodes_with_trams_trains.geojson"

STOPS_GEOJSON = "data/public_transport_stops.geojson"

OUTPUT_STOPS_GEOJSON = "data/geojson/ptv/stops_within_union.geojson"


def extract_stops_within_union():

    # Load the unioned postcode polygon
    unioned_gdf = gpd.read_file(UNIONED_GEOJSON)
    unioned_geom = unioned_gdf.union_all()

    # Load the public transport stops
    stops_gdf = gpd.read_file(STOPS_GEOJSON)

    # Ensure CRS matches
    if stops_gdf.crs != unioned_gdf.crs:
        stops_gdf = stops_gdf.to_crs(unioned_gdf.crs)

    # Find stops within the unioned polygon
    stops_within = stops_gdf[stops_gdf.within(unioned_geom)]


    if "MODE" in stops_within.columns:
        stops_within = stops_within[stops_within["MODE"] != "METRO BUS"]
        stops_within = stops_within[stops_within["MODE"] != "REGIONAL COACH"]
        stops_within = stops_within[stops_within["MODE"] != "REGIONAL BUS"]
        stops_within = stops_within[stops_within["MODE"] != "SKYBUS"]
        # stops_within = stops_within[stops_within["MODE"] != "METRO TRAM"]
        # stops_within = stops_within[stops_within["MODE"] != "REGIONAL TRAIN"]
        # stops_within = stops_within[stops_within["MODE"] != "METRO TRAIN"]
        stops_within = stops_within[stops_within["MODE"] != "INTERSTATE TRAIN"]
        stops_within = stops_within[~stops_within["STOP_NAME"].str.contains("Rail Replacement Bus Stop")]

    # Group by STOP_NAME and take the first entry in each group
    if "STOP_NAME" in stops_within.columns:
        stops_within = stops_within.groupby("STOP_NAME", as_index=False).first()

    # Write the subset to GeoJSON
    pathlib.Path(OUTPUT_STOPS_GEOJSON).parent.mkdir(parents=True, exist_ok=True)
    stops_within.to_file(OUTPUT_STOPS_GEOJSON, driver="GeoJSON")
    stops_within.to_parquet(OUTPUT_STOPS_GEOJSON.replace('.geojson', '.parquet'), engine='pyarrow', index=False)

    print(stops_within["MODE"].unique())
    print(f"Wrote {len(stops_within)} unique stops to {OUTPUT_STOPS_GEOJSON}")

if __name__ == "__main__":
    
    extract_stops_within_union()
    
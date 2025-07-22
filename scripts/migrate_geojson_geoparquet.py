#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas",
#   "pyarrow",
#   "requests",
# ]
# ///

import pathlib

import geopandas as gpd
from pathlib import Path
from utils import dirty, save_geodataframe

SCRIPT_DIR = Path(__file__).parent.resolve()

def convert(geojson_file):
    
    geoparquet_file = str(pathlib.Path(geojson_file).with_suffix(".parquet"))

    geojson_path = pathlib.Path(geojson_file)
    geoparquet_path = pathlib.Path(geoparquet_file)

    if not geojson_path.exists():
        print(f"{geojson_file} does NOT exist. Skipping conversion.")
        return

    if dirty(geoparquet_path, geojson_path):
        gdf = gpd.read_file(geojson_file)
        gdf.to_parquet(geoparquet_file, engine="pyarrow", index=False)
    else:
        print(f"{geoparquet_file} is up to date. Skipping conversion.")
        

    print(f"""
        Converted {geojson_file} {geojson_path.stat().st_size / 1024 / 1024:.2f}Mb 
        to {geoparquet_file} {geoparquet_path.stat().st_size / 1024 / 1024:.2f}Mb 
        compression ratio: {((geoparquet_path.stat().st_size) / geojson_path.stat().st_size) * 100.0:.2f}%
    """)


if __name__ == "__main__":
    convert("data/public_transport_lines.geojson")
    convert("data/public_transport_stops.geojson")

    for f in pathlib.Path("data/isochrones_concatenated/").rglob("*.geojson"):
        convert(str(f))
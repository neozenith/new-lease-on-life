#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas",
#   "pyarrow",
# ]
# ///

import pathlib

import geopandas as gpd


def convert(geojson_file):
    geoparquet_file = str(pathlib.Path(geojson_file).with_suffix(".geoparquet"))

    geojson_path = pathlib.Path(geojson_file)
    geoparquet_path = pathlib.Path(geoparquet_file)

    if (
        not geoparquet_path.exists()
        or geoparquet_path.stat().st_mtime < geojson_path.stat().st_mtime
    ):
        gdf = gpd.read_file(geojson_file)
        gdf.to_parquet(geoparquet_file, engine="pyarrow", index=False)

    print(f"""
        Converted {geojson_file} {geojson_path.stat().st_size / 1024 / 1024:.2f}Mb 
        to {geoparquet_file} {geoparquet_path.stat().st_size / 1024 / 1024:.2f}Mb 
        compression ratio: {((geoparquet_path.stat().st_size) / geojson_path.stat().st_size) * 100.0:.2f}%
    """)


if __name__ == "__main__":
    convert("data/public_transport_lines.geojson")
    convert("data/public_transport_lines_filtered.geojson")
    convert("data/public_transport_stops.geojson")

    for f in pathlib.Path("data/geojson/").glob("*.geojson"):
        convert(str(f))

    for f in pathlib.Path("data/isochrones_concatenated/").rglob("*.geojson"):
        convert(str(f))

    for f in pathlib.Path(".").glob("*.geojson"):
        convert(str(f))

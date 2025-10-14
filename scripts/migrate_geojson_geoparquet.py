#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas",
#   "pyarrow",
#   "requests",
#   "tqdm"
# ]
# ///

import argparse
import logging
import pathlib
from pathlib import Path

import geopandas as gpd
from utils import dirty

SCRIPT_DIR = Path(__file__).parent.resolve()

log = logging.getLogger(__name__)


def convert(geojson_file):
    geoparquet_file = str(pathlib.Path(geojson_file).with_suffix(".parquet"))

    geojson_path = pathlib.Path(geojson_file)
    geoparquet_path = pathlib.Path(geoparquet_file)

    if not geojson_path.exists():
        log.info(f"{geojson_file} does NOT exist. Skipping conversion.")
        return

    if dirty(geoparquet_path, geojson_path):
        gdf = gpd.read_file(geojson_file)
        gdf.to_parquet(geoparquet_file, engine="pyarrow", index=False)
    else:
        log.debug(f"{geoparquet_file} is up to date. Skipping conversion.")

    log.info(f"""
        Converted {geojson_file} {geojson_path.stat().st_size / 1024 / 1024:.2f}Mb 
        to {geoparquet_file} {geoparquet_path.stat().st_size / 1024 / 1024:.2f}Mb 
        compression ratio: {((geoparquet_path.stat().st_size) / geojson_path.stat().st_size) * 100.0:.2f}%
    """)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Convert large GeoJSON files to compressed GeoParquet format"
    )
    args = parser.parse_args()

    convert("data/public_transport_lines.geojson")
    convert("data/public_transport_stops.geojson")


    convert("sites/webapp/data/15.geojson")
    convert("sites/webapp/data/5.geojson")
    convert("sites/webapp/data/all_candidates.geojson")
    convert("sites/webapp/data/lines_within_union_metro_train.geojson")
    convert("sites/webapp/data/lines_within_union_metro_tram.geojson")
    convert("sites/webapp/data/ptv_commute_tier_hulls_metro_train.geojson")
    convert("sites/webapp/data/ptv_commute_tier_hulls_metro_tram.geojson")
    convert("sites/webapp/data/selected_lga_2024_aust_gda2020.geojson")
    convert("sites/webapp/data/selected_postcodes_with_trams_trains.geojson")
    convert("sites/webapp/data/selected_sa2_2021_aust_gda2020.geojson")
    convert("sites/webapp/data/selected_sal_2021_aust_gda2020.geojson")
    convert("sites/webapp/data/stops_with_commute_times_metro_train.geojson")
    convert("sites/webapp/data/stops_with_commute_times_metro_tram.geojson")
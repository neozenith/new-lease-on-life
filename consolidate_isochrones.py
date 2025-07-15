#!/usr/bin/env python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas"
# ]
# ///

import pathlib

import geopandas as gpd
import pandas as pd

ISOCHRONE_FOOT = "data/geojson_fixed/foot/"
ISOCHRONE_BIKE = "data/geojson_fixed/bike/"
ISOCHRONE_CAR = "data/geojson_fixed/car/"
MODES = {"car": ISOCHRONE_CAR, "bike": ISOCHRONE_BIKE, "foot": ISOCHRONE_FOOT}
ISOCHRONE_TIERS = ["15", "10", "5"]
gdf_isochrones: dict[str, dict[str, list[gpd.GeoDataFrame]]] = {
    "foot": {"5": [], "10": [], "15": []},
    "car": {"5": [], "10": [], "15": []},
    "bike": {"5": [], "10": [], "15": []},
}

gdf_isochrones_concatenated: dict[str, dict[str, gpd.GeoDataFrame]] = {
    "foot": {"5": [], "10": [], "15": []},
    "car": {"5": [], "10": [], "15": []},
    "bike": {"5": [], "10": [], "15": []},
}

print(f"Consolidating isochrones from {len(MODES)} modes: {', '.join(MODES.keys())}")
for mode, modality_isochrone_path in MODES.items():
    print(f"Processing isochrones for mode: {mode} from {modality_isochrone_path}")
    for f in pathlib.Path(modality_isochrone_path).rglob("*.geojson"):
        gdf = gpd.read_file(str(f))
        gdf = gdf.to_crs("EPSG:4326")  # Ensure CRS is WGS84 for web compatibility
        gdf["source_file"] = str(f)

        gdf_5 = gdf[gdf["bucket"] == 0]
        gdf_10 = gdf[gdf["bucket"] == 1]
        gdf_15 = gdf[gdf["bucket"] == 2]

        gdf_isochrones[mode]["5"].append(gdf_5)
        gdf_isochrones[mode]["10"].append(gdf_10)
        gdf_isochrones[mode]["15"].append(gdf_15)

for mode in MODES.keys():
    for tier in ISOCHRONE_TIERS:
        print(f"=========={mode} {tier} [{len(gdf_isochrones[mode][tier])}]==========")

        max_input_mtime = max(
            [
                pathlib.Path(g["source_file"].values[0]).stat().st_mtime
                for g in gdf_isochrones[mode][tier]
            ]
        )
        # print(f"Files contributing to {mode} {tier}: {max_input_mtime=}")
        isochrone_concatenated_path = pathlib.Path(
            f"data/isochrones_concatenated/{mode}/{tier}.geojson"
        )
        if isochrone_concatenated_path.exists():
            existing_mtime = isochrone_concatenated_path.stat().st_mtime
            if existing_mtime >= max_input_mtime:
                print(
                    f"SKIP: Output file {isochrone_concatenated_path} is newer than input files. Skipping concatenation."
                )
                continue

        gdf_isochrones_concatenated[mode][tier] = gpd.GeoDataFrame(
            pd.concat(gdf_isochrones[mode][tier], ignore_index=True)
        )

        gdf_isochrones_concatenated[mode][tier]["type"] = mode
        gdf_isochrones_concatenated[mode][tier]["minutes"] = int(tier)

        # merge all overlapping geometries into a single geometries
        gdf_isochrones_concatenated[mode][tier] = gdf_isochrones_concatenated[mode][tier].dissolve(
            by=["type", "minutes"], as_index=False
        )

        isochrone_concatenated_path = pathlib.Path(
            f"data/isochrones_concatenated/{mode}/{tier}.geojson"
        )
        isochrone_concatenated_path.parent.mkdir(parents=True, exist_ok=True)
        gdf_isochrones_concatenated[mode][tier].to_file(
            isochrone_concatenated_path, driver="GeoJSON"
        )

#!/usr/bin/env python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas",
#   "pyarrow",
#   "shapely",
#   "requests",
# ]
# ///

import pathlib
from pathlib import Path
import geopandas as gpd
import pandas as pd
from utils import dirty, save_geodataframe

SCRIPT_DIR = Path(__file__).parent.resolve()


ISOCHRONE_FOOT = SCRIPT_DIR.parent / "data/geojson_fixed/foot/"
ISOCHRONE_BIKE = SCRIPT_DIR.parent / "data/geojson_fixed/bike/"
ISOCHRONE_CAR = SCRIPT_DIR.parent / "data/geojson_fixed/car/"
MODES = {"car": ISOCHRONE_CAR, "bike": ISOCHRONE_BIKE, "foot": ISOCHRONE_FOOT}
ISOCHRONE_TIERS = ["15", "10", "5"]
OUTPUT_DIR = SCRIPT_DIR.parent / "data/isochrones_concatenated"
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
    input_files = list(pathlib.Path(modality_isochrone_path).rglob("*.geojson"))
    print(
        f"Processing isochrones for mode: {mode} from {modality_isochrone_path} {len(input_files)=}"
    )
    # Most recently modified input file
    max_mtime = max(
        f.stat().st_mtime for f in pathlib.Path(modality_isochrone_path).rglob("*.geojson")
    )
    # Least recently updated outputfile
    output_files = list((OUTPUT_DIR / mode).rglob("*.geojson"))
    min_output_mtime = min(f.stat().st_mtime for f in output_files)

    if not dirty(output_files, input_files):
        continue  # Skip if no new files are found

    for f in input_files:
        gdf = gpd.read_file(str(f))
        gdf = gdf.to_crs("EPSG:4326")  # Ensure CRS is WGS84 for web compatibility
        gdf["source_file"] = str(f)
        try:
            ptv_mode = gdf["MODE"].values[0]
            # print(f"Processing {ptv_mode} from {f}")
        except KeyError:
            print(f"Skipping {f} as it does not contain 'MODE' column.")
            continue

        gdf_5 = gdf[gdf["contour_time_minutes"] == 5]
        gdf_10 = gdf[gdf["contour_time_minutes"] == 10]
        gdf_15 = gdf[gdf["contour_time_minutes"] == 15]

        gdf_isochrones[mode]["5"].append(gdf_5)
        gdf_isochrones[mode]["10"].append(gdf_10)
        gdf_isochrones[mode]["15"].append(gdf_15)

for mode in MODES.keys():
    for tier in ISOCHRONE_TIERS:
        print(f"=========={mode} {tier} [{len(gdf_isochrones[mode][tier])}]==========")

        if len(gdf_isochrones[mode][tier]) == 0:
            continue  # Skip if no isochrones found to process for this mode and tier

        input_files = [
            pathlib.Path(g["source_file"].values[0])
            for g in gdf_isochrones[mode][tier]
        ]
        # print(f"Files contributing to {mode} {tier}: {max_input_mtime=}")
        isochrone_concatenated_path = OUTPUT_DIR / mode / f"{tier}.geojson"

        if not dirty(isochrone_concatenated_path, input_files):
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

        save_geodataframe(
            gdf_isochrones_concatenated[mode][tier],
            isochrone_concatenated_path
        )

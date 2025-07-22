#!/usr/bin/env python
"""
isochrone_viewer.py - Minimal Holoviz Panel app with DeckGL map.

Shows a map centered and zoomed to the bounding box:
  Top-left:   -37.713453, 144.895298
  Bottom-right: -37.814206, 144.989262
"""

# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "panel",
#   "pydeck",
#   "geopandas",
#   "pyarrow",
#   "duckdb",
#   "duckdb-extensions",
#   "duckdb-extension-spatial",
#   "python-dotenv>=1.0.0",
#   "shapely",
# ]
# ///
import os
import pathlib
from pathlib import Path

import geopandas as gpd
import panel as pn
import pydeck as pdk

pn.extension("deckgl", template="material", sizing_mode="stretch_width")

from dotenv import load_dotenv

load_dotenv()


def hsv_to_rgb(h: float, s: float, v: float, a: float) -> tuple[float, float, float, float]:
    if s:
        if h == 1.0:
            h = 0.0
        i = int(h * 6.0)
        f = h * 6.0 - i

        w = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))

        if i == 0:
            return (v, t, w, a)
        if i == 1:
            return (q, v, w, a)
        if i == 2:
            return (w, v, t, a)
        if i == 3:
            return (w, q, v, a)
        if i == 4:
            return (t, w, v, a)
        if i == 5:
            return (v, w, q, a)
    else:
        return (v, v, v, a)

    return (0.0, 0.0, 0.0, a)


def rgba_float_to_255(rgba: tuple[float, float, float, float]) -> list[int]:
    """Convert a tuple of floats in range [0.0, 1.0] to a list of ints in range [0, 255]."""
    return [int(255 * c) for c in rgba[:3]] + [int(255 * rgba[3])]


def min_max_normalize(series):
    return (series - series.min()) / (series.max() - series.min())

PTV_LINES = "data/public_transport_lines.geojson"

ISOCHRONE_FOOT = "data/geojson_fixed/foot/"
ISOCHRONE_BIKE = "data/geojson_fixed/bike/"
ISOCHRONE_CAR = "data/geojson_fixed/car/"

SUBURB_OPACITY = 0.1  # Opacity for suburb boundaries
PTV_OPACITY = 0.75  # Opacity for PTV lines and stops
ISOCHRONE_OPACITY = 0.1  # Opacity for isochrones
ISOCHRONE_LINE_OPACITY = 1.0

PTV_MODES = ["METRO TRAM", "METRO TRAIN", "REGIONAL TRAIN", "INTERSTATE TRAIN", "REGIONAL BUS", "REGIONAL COACH", "METRO BUS", "SKYBUS"]
MODES = {"car": ISOCHRONE_CAR, "bike": ISOCHRONE_BIKE, "foot": ISOCHRONE_FOOT}
ALL_MODES = ["METRO TRAM", "bike", "METRO TRAIN", "car", "REGIONAL TRAIN", "foot", "INTERSTATE TRAIN", "REGIONAL BUS", "REGIONAL COACH", "METRO BUS", "SKYBUS"]
ISOCHRONE_TIERS = ["15", "10", "5"]

# Give all modes of transport, either personal or public transport, a unique hue in the HSV color space.
# This allows us to easily distinguish between them on the map.
float_hue_offset = 0.1
HUE_FOR_MODE = {
    mode: (i / len(ALL_MODES) + float_hue_offset) % 1.0 for i, mode in enumerate(ALL_MODES)
}
print(f"HUE_FOR_MODE: {HUE_FOR_MODE}")


def isochrone_colours():
    isochrone_colors = {}
    [f"{mode}-{tier}" for mode in MODES.keys() for tier in ISOCHRONE_TIERS]
    for m, mode in enumerate(MODES.keys()):
        float_hue = HUE_FOR_MODE[mode]
        for t, tier in enumerate(ISOCHRONE_TIERS):
            float_saturation = 0.5 + (0.1 * t)  # Saturation increases with tier
            isochrone_colors[f"{mode}-{tier}"] = rgba_float_to_255(
                hsv_to_rgb(float_hue, float_saturation, 0.8, ISOCHRONE_OPACITY)
            )
    return isochrone_colors


def ptv_colour_mapping():
    return {
        m: rgba_float_to_255(hsv_to_rgb(HUE_FOR_MODE[m], 0.8, 0.8, PTV_OPACITY)) for m in PTV_MODES
    }


def load_ptv_lines_data() -> gpd.GeoDataFrame:
    ptv_colour_lookup = ptv_colour_mapping()
    gdf_ptv_lines = gpd.read_file(PTV_LINES)
    gdf_ptv_lines = gdf_ptv_lines.to_crs("EPSG:4326")

    gdf_ptv_lines = gdf_ptv_lines[~gdf_ptv_lines["SHORT_NAME"].str.contains("Replacement Bus")]

    gdf_ptv_lines["color"] = gdf_ptv_lines.apply(lambda row: ptv_colour_lookup.get(row["MODE"]), axis=1)

    return gdf_ptv_lines

def layer_for(gdf):
    return pdk.Layer(
        "GeoJsonLayer",
        data=gdf,
        get_fill_color=[0, 0, 0, 0],  # Semi-transparent
        get_line_color="color",  # Use the color column
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
    )





def app_for(layers: list[pdk.Layer]) -> pn.Column:
    # Bounding box coordinates
    TOP_LEFT = (-37.713453, 144.895298)  # (lat, lon)
    BOTTOM_RIGHT = (-37.814206, 144.989262)  # (lat, lon)

    # Calculate center
    center_lat = (TOP_LEFT[0] + BOTTOM_RIGHT[0]) / 2
    center_lon = (TOP_LEFT[1] + BOTTOM_RIGHT[1]) / 2

    # DeckGL initial view state
    map_style = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"

    INITIAL_VIEW_STATE = pdk.ViewState(
        bearing=0, latitude=center_lat, longitude=center_lon, maxZoom=15, minZoom=5, pitch=0, zoom=11
    )

    LAYERS = [layer_for(gdf)]
    deck_spec = pdk.Deck(
        initial_view_state=INITIAL_VIEW_STATE,
        layers=LAYERS,
        map_provider="google_maps",  # Use Google Maps as the base map
        map_style=map_style,
        views=[{"@@type": "MapView", "controller": True}],
        api_keys={
            "google_maps": os.environ.get(
                "GOOGLE_MAPS_API_KEY", ""
            ),  # Replace with your Google Maps API key
        },
    )


    app = pn.Column(
        pn.pane.Markdown("# Isochrone Viewer\n\nA basic map view using DeckGL and Panel."),
        pn.pane.DeckGL(deck_spec, height=800),
        sizing_mode="stretch_width",
    )
    return app

if __name__ == "__main__":
    # pn.serve(app, port=5006, show=True, title="Isochrone Viewer")
    gdf = load_ptv_lines_data()
    print(gdf.columns)
    # SHAPE_ID: object unique_count=10914
    # HEADSIGN: object unique_count=719
    # SHORT_NAME: object unique_count=499
    # LONG_NAME: object unique_count=749
    # MODE: object unique_count=8
    # gdf.drop(columns=["SHAPE_ID", "HEADSIGN", "SHORT_NAME", "LONG_NAME"], inplace=True)
    app = app_for(gdf)
    
    try:
        pn.serve(app, port=5006, show=True, title="Isochrone Viewer")
    except Exception as e:
        print(f"Error starting app: {e}")
        
    
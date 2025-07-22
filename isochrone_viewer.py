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


PTV_STOPS = "data/geojson/ptv/stops_with_commute_times.parquet"
PTV_LINES = "data/public_transport_lines.geojson"
PTV_HULLS = "data/geojson/ptv/ptv_commute_tier_hulls.parquet"

POSTCODE_BOUNDARIES = "data/geojson/ptv/boundaries/unioned_postcodes.parquet"
SELECTED_POSTCODES = "data/geojson/ptv/boundaries/selected_postcodes.parquet"


mesh_key = "POA_CODE21"


TRAM_POSTCODE_BOUNDARIES = "data/geojson/ptv/boundaries/unioned_postcodes_with_trams.parquet"
TRAINTRAM_POSTCODE_BOUNDARIES = (
    "data/geojson/ptv/boundaries/unioned_postcodes_with_trams_trains.parquet"
)

ISOCHRONE_FOOT = "data/geojson_fixed/foot/"
ISOCHRONE_BIKE = "data/geojson_fixed/bike/"
ISOCHRONE_CAR = "data/geojson_fixed/car/"

SUBURB_OPACITY = 0.1  # Opacity for suburb boundaries
PTV_OPACITY = 0.75  # Opacity for PTV lines and stops
ISOCHRONE_OPACITY = 0.1  # Opacity for isochrones
ISOCHRONE_LINE_OPACITY = 1.0


PTV_MODES = [
    "METRO TRAM",
    "METRO TRAIN",
    "REGIONAL TRAIN",
    "INTERSTATE TRAIN",
    "REGIONAL BUS",
    "REGIONAL COACH",
    "METRO BUS",
    "SKYBUS",
]
MODES = {"car": ISOCHRONE_CAR, "bike": ISOCHRONE_BIKE, "foot": ISOCHRONE_FOOT}
ALL_MODES = [
    "METRO TRAM",
    "bike",
    "METRO TRAIN",
    "car",
    "REGIONAL TRAIN",
    "foot",
    "INTERSTATE TRAIN",
    "REGIONAL BUS",
    "REGIONAL COACH",
    "METRO BUS",
    "SKYBUS",
]
ISOCHRONE_TIERS = ["15", "10", "5"]

# Give all modes of transport, either personal or public transport, a unique hue in the HSV color space.
# This allows us to easily distinguish between them on the map.
float_hue_offset = 0.1
HUE_FOR_MODE = {
    mode: (float(i) / float(len(ALL_MODES)) + float_hue_offset) % 1.0 for i, mode in enumerate(ALL_MODES)
}
print(f"HUE_FOR_MODE: {HUE_FOR_MODE}")
isochrone_colors = {}
[f"{mode}-{tier}" for mode in MODES.keys() for tier in ISOCHRONE_TIERS]
for m, mode in enumerate(MODES.keys()):
    float_hue = HUE_FOR_MODE[mode]
    for t, tier in enumerate(ISOCHRONE_TIERS):
        float_saturation = 0.2 + (0.1 * t)  # Saturation increases with tier
        isochrone_colors[f"{mode}-{tier}"] = rgba_float_to_255(
            hsv_to_rgb(float_hue, float_saturation, 0.8, ISOCHRONE_OPACITY)
        )

ptv_color_lookup = {
    m: rgba_float_to_255(hsv_to_rgb(HUE_FOR_MODE[m], 0.8, 0.8, PTV_OPACITY)) for m in PTV_MODES
}
print(f"PTV color lookup: {ptv_color_lookup}")


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

LAYERS = []

gdf_postcodes = gpd.read_parquet(SELECTED_POSTCODES)
gdf_postcodes = gdf_postcodes.to_crs("EPSG:4326")


color_lookup = {
    k: [c[0], c[1], c[2], int(255 * SUBURB_OPACITY)]
    for k, c in pdk.data_utils.assign_random_colors(gdf_postcodes[mesh_key]).items()
}
# Assign a color based on attraction_type
gdf_postcodes["color"] = gdf_postcodes.apply(lambda row: color_lookup.get(row[mesh_key]), axis=1)

postcode_boundary_layer = pdk.Layer(
    "GeoJsonLayer",
    data=gdf_postcodes,
    get_fill_color="color",  # Semi-transparent
    get_line_color=[255, 255, 255, 255],  # White lines
    line_width_min_pixels=2,
    pickable=True,
    auto_highlight=True,
)


gdf_outer = gpd.read_parquet(POSTCODE_BOUNDARIES)
gdf_outer = gdf_outer.to_crs("EPSG:4326")

outer_boundary_layer = pdk.Layer(
    "GeoJsonLayer",
    data=gdf_outer,
    get_fill_color=[0, 0, 0, 0],  # transparent
    get_line_color=[0, 255, 0, int(255 * 1.0)],  # Green lines
    line_width_min_pixels=1,
    pickable=False,
    auto_highlight=False,
)

gdf_outer_tram = gpd.read_parquet(TRAM_POSTCODE_BOUNDARIES)
gdf_outer_tram = gdf_outer_tram.to_crs("EPSG:4326")

tram_outer_boundary_layer = pdk.Layer(
    "GeoJsonLayer",
    data=gdf_outer_tram,
    get_fill_color=[0, 0, 0, 0],  # transparent
    get_line_color=[255, 255, 0, int(255 * 1.0)],  # Green lines
    line_width_min_pixels=1,
    pickable=False,
    auto_highlight=False,
)

gdf_outer_traintram = gpd.read_parquet(TRAINTRAM_POSTCODE_BOUNDARIES)
gdf_outer_traintram = gdf_outer_traintram.to_crs("EPSG:4326")

traintram_outer_boundary_layer = pdk.Layer(
    "GeoJsonLayer",
    data=gdf_outer_traintram,
    get_fill_color=[0, 0, 0, 0],  # transparent
    get_line_color=[255, 0, 255, int(255 * 1.0)],  # Green lines
    line_width_min_pixels=1,
    pickable=False,
    auto_highlight=False,
)

gdf_ptv_lines = gpd.read_file(PTV_LINES)
gdf_ptv_lines = gdf_ptv_lines.to_crs("EPSG:4326")

# if len(gdf_ptv_lines["MODE"].unique()) > 3:
# Compact to minimal set
print(gdf_ptv_lines["MODE"].unique())
print(f"Initial PTV lines, total: {len(gdf_ptv_lines)}")
gdf_ptv_lines = gdf_ptv_lines[
    ~gdf_ptv_lines["MODE"].isin(
        [
            "METRO BUS",
            "REGIONAL BUS",
            "REGIONAL COACH",
            "SKYBUS",
            # "REGIONAL TRAIN",
            # "METRO TRAIN",
            # "METRO TRAM",
        ]
    )
]
gdf_ptv_lines = gdf_ptv_lines[~gdf_ptv_lines["SHORT_NAME"].str.contains("Replacement Bus")]
print(f"Filtered PTV lines, remaining: {len(gdf_ptv_lines)}")

# Filter gdf_ptv_lines to include only lines that passthrough gdf_outer
# gdf_ptv_lines_nonintersect = gdf_ptv_lines[~gdf_ptv_lines.intersects(gdf_outer.union_all())]
# gdf_ptv_lines_nonintersect.to_file("data/public_transport_lines_filtered_nonintersect.geojson", driver="GeoJSON")
# gdf_ptv_lines = gdf_ptv_lines[gdf_ptv_lines.intersects(gdf_outer.union_all())]

print(f"Filtered PTV lines that intersect outer boundary, remaining: {len(gdf_ptv_lines)}")
# gdf_ptv_lines.to_file("data/public_transport_lines_filtered.geojson", driver="GeoJSON")
# gdf_ptv_lines.to_parquet("data/public_transport_lines_filtered.geoparquet", engine="pyarrow", index=False)
# gdf_ptv_lines = gpd.read_parquet("data/public_transport_lines_filtered.geoparquet")


gdf_ptv_lines["color"] = gdf_ptv_lines.apply(lambda row: ptv_color_lookup.get(row["MODE"]), axis=1)

ptv_lines_layer = pdk.Layer(
    "GeoJsonLayer",
    data=gdf_ptv_lines,
    get_fill_color=[0, 0, 0, 0],  # Semi-transparent
    get_line_color="color",  # Use the color column
    line_width_min_pixels=1,
    pickable=True,
    auto_highlight=True,
)


gdf_ptv_stops = gpd.read_parquet(PTV_STOPS)
# gdf_ptv_stops = gdf_ptv_stops.to_crs("EPSG:4326")
# Make sure MODE is a column, not just in the index
if "MODE" in gdf_ptv_stops.index.names and "MODE" not in gdf_ptv_stops.columns:
    gdf_ptv_stops = gdf_ptv_stops.reset_index()

def get_stop_colour(row):
    mode = row["MODE"]
    tier = row["transit_time_minutes_nearest_tier"]
    tier = 0 if tier is None else tier

    # Use the specific hue for this mode from HUE_FOR_MODE
    mode_hue = HUE_FOR_MODE[mode]

    # Adjust saturation and value based on transit time
    # Higher transit times (further from city) will have lower saturation and value
    # This creates a visual gradient where closer = more vibrant, further = more faded

    # Map tier to saturation (0.3-0.9 range)
    # Lower tiers (closer to city) have higher saturation
    max_tier = 60  # Assuming 90 minutes is our maximum tier
    saturation = 1.0 - (0.4 * (min(tier, max_tier) / max_tier))

    # Map tier to value (0.5-0.9 range)
    # Lower tiers (closer to city) have higher value (brightness)
    value = 0.9 - (0.4 * (min(tier, max_tier) / max_tier))

    # Create the color with mode-specific hue but time-based saturation and value
    return rgba_float_to_255(
        hsv_to_rgb(
            mode_hue,  # Mode-specific hue
            saturation,  # Time-based saturation
            value,  # Time-based value
            1.0 * saturation,  # link opacity to saturation too
        )
    )

gdf_ptv_stops["color"] = gdf_ptv_stops.apply(get_stop_colour, axis=1)

gdf_ptv_stops = gdf_ptv_stops[
    gdf_ptv_stops["MODE"].isin(["REGIONAL TRAIN", "METRO TRAIN", "METRO TRAM"])
]


# Define a function to get hull colors that respects the hue for each mode
# while varying saturation and value based on transit time
def get_hull_color(row):
    mode = row["MODE"]
    tier = row["transit_time_minutes_nearest_tier"]

    # Use the specific hue for this mode from HUE_FOR_MODE
    mode_hue = HUE_FOR_MODE[mode] + 0.02

    # Adjust saturation and value based on transit time
    # Higher transit times (further from city) will have lower saturation and value
    # This creates a visual gradient where closer = more vibrant, further = more faded

    # Map tier to saturation (0.3-0.9 range)
    # Lower tiers (closer to city) have higher saturation
    max_tier = 60  # Assuming 90 minutes is our maximum tier
    saturation = 1.0 - (0.8 * (min(tier, max_tier) / max_tier))

    # Map tier to value (0.5-0.9 range)
    # Lower tiers (closer to city) have higher value (brightness)
    value = 0.9 - (0.4 * (min(tier, max_tier) / max_tier))

    # Create the color with mode-specific hue but time-based saturation and value
    return rgba_float_to_255(
        hsv_to_rgb(
            mode_hue,  # Mode-specific hue
            saturation,  # Time-based saturation
            value,  # Time-based value
            1.0 * saturation,  # link opacity to saturation too
        )
    )


gdf_ptv_hulls = gpd.read_parquet(PTV_HULLS)


gdf_ptv_hulls = gdf_ptv_hulls[gdf_ptv_hulls["MODE"].isin(["METRO TRAIN", "METRO TRAM"])]
print(f"{gdf_ptv_hulls.columns=}")
print(f"{gdf_ptv_hulls['transit_time_minutes_nearest_tier'].unique()=}")
gdf_ptv_hulls = gdf_ptv_hulls[
    gdf_ptv_hulls["transit_time_minutes_nearest_tier"].isin([15, 30, 45, 60])
]

tier_size = 10  # minutes
tiers = range(
    tier_size, 60, tier_size
)  # Define tiers from 5 to 55 minutes in increments of tier_size

# gdf_ptv_hulls = gdf_ptv_hulls[gdf_ptv_hulls['transit_time_minutes_nearest_tier'].isin(tiers)]
gdf_ptv_hulls["color"] = gdf_ptv_hulls.apply(get_hull_color, axis=1)
# Create a layer for the commute time hull polygons
ptv_commute_hulls_layer = pdk.Layer(
    "GeoJsonLayer",
    data=gdf_ptv_hulls,
    get_fill_color=[0, 0, 0, 0],  # Use the calculated color
    get_line_color="color",  # Light white border
    line_width_min_pixels=5,
    pickable=True,
    auto_highlight=True,
)

# Also keep the original points to show station locations
ptv_stops_layer = pdk.Layer(
    "GeoJsonLayer",
    data=gdf_ptv_stops,
    get_fill_color="color",  # White points
    get_line_color="color",  # Black outline
    line_width_min_pixels=3,
    # get_radius=40,  # Smaller point size
    pickable=True,
    auto_highlight=True,
)


isochrone_layers: dict[str, dict[str, pdk.Layer | None]] = {
    "foot": {"5": None, "10": None, "15": None},
    "car": {"5": None, "10": None, "15": None},
    "bike": {"5": None, "10": None, "15": None},
}
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

visible_isochrone_layers = []
for mode in MODES.keys():
    for tier in ISOCHRONE_TIERS:
        print(f"=========={mode} {tier} ==========")

        isochrone_concatenated_path = pathlib.Path(
            f"data/isochrones_concatenated/{mode}/{tier}.geoparquet"
        )
        gdf_isochrones_concatenated[mode][tier] = gpd.read_parquet(isochrone_concatenated_path)

        if (
            mode == "foot" and (tier in ["15", "5"])
            # or (mode == "car" and tier == "5")
            # or (mode == "bike" and tier == "10")
        ):
            col = isochrone_colors[f"{mode}-{tier}"]
            line_color = [col[0], col[1], col[2], int(255 * ISOCHRONE_LINE_OPACITY)]
            isochrone_layers[mode][tier] = pdk.Layer(
                "GeoJsonLayer",
                data=gdf_isochrones_concatenated[mode][tier],
                get_fill_color=col,  # Use the assigned color
                get_line_color=line_color,  # White lines
                line_width_min_pixels=1,
                pickable=True,
                auto_highlight=True,
            )
            visible_isochrone_layers.append(isochrone_layers[mode][tier])

# LAYERS.append(postcode_boundary_layer)

# LAYERS.append(traintram_outer_boundary_layer)

# LAYERS.append(outer_boundary_layer)

# LAYERS.append(tram_outer_boundary_layer)

LAYERS.extend(visible_isochrone_layers)

# # Add the PTV lines layer to show transit routes
LAYERS.append(ptv_lines_layer)

# Add the commute time hull polygons first (will be below stops)
LAYERS.append(ptv_commute_hulls_layer)

# Add the stops on top for better visibility
LAYERS.append(ptv_stops_layer)


rentals = []

for rental_candidate in pathlib.Path("data/candidate_real_estate/").glob("*.geojson"):
    print(f"Processing rental candidate: {rental_candidate}")
    gdf_rental = gpd.read_file(rental_candidate)
    gdf_rental = gdf_rental.to_crs("EPSG:4326")

    gdf_rental = gdf_rental[gdf_rental["feature_type"] == "property"]
    rentals.append(gdf_rental)

    # Add rental candidates as a layer
    rental_layer = pdk.Layer(
        "GeoJsonLayer",
        data=gdf_rental,
        get_fill_color=[255, 0, 0, 128],  # Semi-transparent red
        get_line_color=[255, 0, 0, 255],  # Red lines
        line_width_min_pixels=12,
        pickable=True,
        auto_highlight=True,
    )
    # LAYERS.append(rental_layer)


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
        bearing=0,
        latitude=center_lat,
        longitude=center_lon,
        maxZoom=15,
        minZoom=5,
        pitch=0,
        zoom=11,
    )

    deck_spec = pdk.Deck(
        initial_view_state=INITIAL_VIEW_STATE,
        layers=layers,
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
    # LAYERS = []
    app = app_for(LAYERS)
    pn.serve(app, port=5006, show=True, title="Isochrone Viewer")

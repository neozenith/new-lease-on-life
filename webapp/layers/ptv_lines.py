
import pydeck as pdk
import geopandas as gpd
from webapp.utils.colours import ptv_colour_mapping
from pathlib import Path
PTV_LINES = Path("data/geojson/ptv/lines/ptv_lines.geojson")

def load_ptv_lines_data() -> gpd.GeoDataFrame:
    ptv_colour_lookup = _ptv_colour_lookup()
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
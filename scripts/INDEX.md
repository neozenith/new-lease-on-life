# Helper Scripts Index

**Quick Reference**: 10 geospatial Python scripts - ⚡ uv run scripts/script.py

## Script Matrix by Category

| Data Pipeline | Geospatial | Boundaries | Analysis | Utils |
|---------------|------------|------------|----------|-------|
| batch_isochrones | export_shapefiles | extract_postcode_polygons | stops_by_transit_time | utils |
| consolidate_isochrones | migrate_geojson_geoparquet | extract_stops_within_union | process_realestate_candidates | |
| fix_geojson | | | | |

## Scripts Reference

### batch_isochrones_for_stops.py

**Purpose**: Fetch isochrone polygons from GraphHopper/Mapbox APIs for transport stops  
**Usage**: `uv run scripts/batch_isochrones_for_stops.py --status|--dry-run|--limit N`  
**Env**: GRAPHHOPPER_API_KEY | MAPBOX_API_TOKEN  
**Output**: data/isochrone_cache/{foot|bike|car}/*.geojson

### consolidate_isochrones.py

**Purpose**: Merge cached isochrones by transport mode & time tier (5,10,15min)  
**Usage**: `uv run scripts/consolidate_isochrones.py`  
**Output**: data/isochrones_concatenated/{foot|bike|car}/{5|10|15}.geojson

### fix_geojson.py

**Purpose**: Standardize GraphHopper/Mapbox isochrone formats to FeatureCollection  
**Usage**: `uv run scripts/fix_geojson.py input.geojson -o output.geojson --validate`  
**Output**: Standard GeoJSON with stop metadata enrichment

### export_shapefiles.py

**Purpose**: Convert ESRI shapefiles → GeoJSON/GeoParquet with CRS reprojection  
**Usage**: `uv run scripts/export_shapefiles.py --simplify 0.001 --single-file path.shp`  
**Output**: data/originals_converted/ with WGS84 projection

### migrate_geojson_geoparquet.py

**Purpose**: Convert large GeoJSON → compressed GeoParquet format  
**Usage**: `uv run scripts/migrate_geojson_geoparquet.py`  
**Output**: .parquet files with compression stats

### extract_postcode_polygons.py

**Purpose**: Filter Australian postcode boundaries by transport stop presence  
**Usage**: `uv run scripts/extract_postcode_polygons.py`  
**Output**: data/geojson/ptv/boundaries/{selected|unioned}_postcodes_*.geojson

### extract_stops_within_union.py

**Purpose**: Filter transport stops within boundary unions (exclude buses)  
**Usage**: `uv run scripts/extract_stops_within_union.py`  
**Output**: data/geojson/ptv/stops_within_union.geojson (445 stops)

### stops_by_transit_time.py

**Purpose**: Calculate transit times to Southern Cross + create time-based hulls  
**Usage**: `uv run scripts/stops_by_transit_time.py`  
**Env**: GOOGLE_MAPS_API_KEY  
**Output**: stops_with_commute_times.{geojson|parquet}, ptv_commute_tier_hulls.geojson

### process_realestate_candidates.py

**Purpose**: Analyze property addresses with multi-modal commute calculations  
**Usage**: `uv run scripts/process_realestate_candidates.py`  
**Env**: GOOGLE_MAPS_API_KEY  
**Output**: data/candidate_real_estate/{address}.json.geojson with routes

### utils.py

**Purpose**: Shared utilities - file ops, caching, API retry, normalization  
**Usage**: Import only - `from utils import load_stops, dirty, save_geodataframe`  
**Functions**: min_max_normalize, normalise_name, make_request_with_retry

## Command Patterns

```sh
# Status & validation
uv run scripts/batch_isochrones_for_stops.py --status
uv run scripts/fix_geojson.py input.geojson --validate

# Directory processing  
uv run scripts/fix_geojson.py data/input -o data/output --recursive
uv run scripts/export_shapefiles.py --data-dir /path --output-dir /out

# Pipeline execution
uv run scripts/{script}.py --help  # All scripts support help
```

## Pipeline Flow

Raw Data → Boundaries → Stops → Isochrones → Analysis

```text
1. export_shapefiles       → Convert raw boundaries
2. extract_postcode_polygons → Filter by transport access  
3. extract_stops_within_union → Extract relevant stops (445)
4. batch_isochrones        → Fetch travel boundaries (API)
5. fix_geojson            → Standardize formats
6. consolidate_isochrones → Merge by mode/tier
7. stops_by_transit_time  → Calculate commute times
8. process_realestate_candidates → Property analysis
```

**Environment**: Python 3.12+ | uv + PEP-723 | API keys in .env

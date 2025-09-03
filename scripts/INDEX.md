# Helper Script Index

**Quick Reference**: 12 scripts - Data Pipeline + Geospatial Analysis | Pipeline: Raw Data → Boundaries → Stops → Isochrones → Analysis

## Script Matrix

| Category | Scripts | Core Purpose |
|----------|---------|-------------|
| **Data Pipeline** | batch_isochrones, consolidate_isochrones, fix_geojson | API fetching, data consolidation, format standardization |
| **Geospatial** | export_shapefiles, migrate_geojson_geoparquet | Format conversion, compression optimization |
| **Boundaries** | extract_postcode_polygons, extract_state_polygons, extract_boundaries_victoria, extract_stops_within_union | Spatial filtering, boundary processing, state union |
| **Analysis** | stops_by_transit_time, process_realestate_candidates | Commute calculation, property analysis |
| **Utils** | utils | Shared functions, API retry, normalization |

## Scripts

### batch_isochrones_for_stops.py

**Purpose**: Fetch isochrone polygons from GraphHopper/Mapbox APIs for transport stops
**Usage**: `uv run scripts/batch_isochrones_for_stops.py --status|--dry-run|--limit N`
**Env**: GRAPHHOPPER_API_KEY, MAPBOX_API_TOKEN
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

### extract_state_polygons.py

**Purpose**: Extract and union state/territory polygons from SA4 boundary data
**Usage**: `uv run scripts/extract_state_polygons.py`
**Output**: data/originals_converted/state_polygons/australian_states.{geojson|parquet}

### extract_boundaries_victoria.py

**Purpose**: Filter Australian boundary data to only include Victoria state features
**Usage**: `uv run scripts/extract_boundaries_victoria.py [--dry-run] [--limit N] [--verbose]`
**Output**: data/originals_converted/boundaries_victoria/**/*.parquet (preserves structure)

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
**Output**: Library functions for other scripts

## Command Patterns

```sh
# Status/dry-run pattern
uv run scripts/{script}.py --status|--dry-run

# File processing pattern  
uv run scripts/fix_geojson.py input -o output --validate

# Directory processing pattern
uv run scripts/export_shapefiles.py --data-dir /path --output-dir /path
```

## Pipeline Flow

Raw Data → Boundaries → Stops → Isochrones → Analysis

1. **export_shapefiles** → Convert raw boundaries (ESRI → GeoJSON/Parquet)
2. **extract_postcode_polygons** → Filter by transport access
3. **extract_stops_within_union** → Extract relevant stops (445 total)
4. **batch_isochrones** → Fetch travel boundaries (API calls)
5. **fix_geojson** → Standardize formats
6. **consolidate_isochrones** → Merge by mode/tier
7. **stops_by_transit_time** → Calculate commute times
8. **process_realestate_candidates** → Property analysis

---
**Scripts**: 12 | **Python**: 3.12+ | **Manager**: uv

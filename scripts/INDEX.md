# Helper Script Index

A comprehensive index of all Python helper scripts in the `scripts/` directory. Each script
is designed to be run independently using `uv run scripts/script_name.py`.

## Data Pipeline Scripts

### batch_isochrones_for_stops.py

**TITLE:** Batch fetch isochrone data from external APIs for public transport stops
**DESCRIPTION:** Fetches isochrone polygons (travel time boundaries) for public transport stops
using GraphHopper or Mapbox APIs. Supports different transport modes (foot, bike, car) and time
buckets. Includes intelligent caching, status monitoring, and rate limiting to avoid API quotas.

**SOURCE:** scripts/batch_isochrones_for_stops.py

**LANGUAGE:** python
**USAGE:**
    Core operations: status check, dry run, or actual scraping with configurable limits.

```sh
# Check current status of cached isochrones
uv run scripts/batch_isochrones_for_stops.py --status

# Perform dry run to see what would be processed
uv run scripts/batch_isochrones_for_stops.py --dry-run --limit 50

# Scrape isochrones with limit (default: 170)
uv run scripts/batch_isochrones_for_stops.py --limit 100
```

**OUTPUT:**

```sh
# Status output shows cached vs expected files by transport mode
FOOT             METRO TRAIN     : expected   450  cached   380  remaining    70   84.44%
BIKE             METRO TRAM      : expected   180  cached   180  remaining     0  100.00%

# Scraping output shows progress
✅ Saved METRO TRAIN foot 10001 (Flinders Street Station) to
   data/isochrone_cache/foot/isochrone_10001_flinders_street_station.geojson
```

**DEPENDENCIES:** requests, pyyaml, geopandas, python-dotenv, tqdm
**ENVIRONMENT:** Requires GRAPHHOPPER_API_KEY or MAPBOX_API_TOKEN

----------------------------------------

### consolidate_isochrones.py

**TITLE:** Consolidate and merge isochrone polygons by transport mode and time tier
**DESCRIPTION:** Processes cached isochrone GeoJSON files and creates consolidated datasets.
Groups isochrones by transport mode (foot, bike, car) and time tiers (5, 10, 15 minutes), then
dissolves overlapping geometries into unified coverage areas for visualization.

**SOURCE:** scripts/consolidate_isochrones.py

**LANGUAGE:** python
**USAGE:**
    Automatically processes all cached isochrones and creates merged datasets.

```sh
uv run scripts/consolidate_isochrones.py
```

**OUTPUT:**
    Creates merged GeoJSON files organized by mode and time tier.

```sh
# Processing output
Processing isochrones for mode: foot from data/geojson_fixed/foot/ input_files=1250
==========foot 5 [415]==========
==========foot 10 [415]==========
==========foot 15 [415]==========

# Generated files
data/isochrones_concatenated/foot/5.geojson
data/isochrones_concatenated/foot/10.geojson
data/isochrones_concatenated/foot/15.geojson
```

**DEPENDENCIES:** geopandas, pyarrow, shapely, requests, tqdm

----------------------------------------

### fix_geojson.py

**TITLE:** Convert and standardize non-standard GeoJSON isochrone files
**DESCRIPTION:** Fixes GeoJSON files from different isochrone APIs by converting them to standard
FeatureCollection format. Handles both GraphHopper's "polygons" array format and Mapbox's standard
format. Enriches features with transport stop metadata and standardizes property names.

**SOURCE:** scripts/fix_geojson.py

**LANGUAGE:** python
**USAGE:**
    Can process single files or entire directories recursively with validation.

```sh
# Process single file
uv run scripts/fix_geojson.py input_file.geojson -o output_file.geojson --validate

# Process entire directory
uv run scripts/fix_geojson.py data/isochrone_cache -o data/geojson_fixed --recursive --validate
```

**OUTPUT:**
    Standardized GeoJSON files with proper FeatureCollection structure.

```sh
Successfully converted data/isochrone_cache/foot/isochrone_10001_flinders_street.geojson
    to standard GeoJSON format
Processed 1250/1250 files successfully. (850 files were cached).
```

**DEPENDENCIES:** geopandas, pyarrow, shapely, requests, tqdm

----------------------------------------

## Geospatial Conversion Scripts

### export_shapefiles.py

**TITLE:** Convert shapefiles to GeoJSON and GeoParquet formats
**DESCRIPTION:** Scans data directories for ESRI Shapefiles and converts them to web-compatible
GeoJSON format and efficient GeoParquet format. Supports geometry simplification, column filtering,
CRS reprojection to WGS84, and automatic ZIP archive extraction.

**SOURCE:** scripts/export_shapefiles.py

**LANGUAGE:** python
**USAGE:**
    Processes shapefiles with optional simplification and filtering.

```sh
# Convert all shapefiles in data/originals
uv run scripts/export_shapefiles.py

# Convert with geometry simplification
uv run scripts/export_shapefiles.py --simplify 0.001

# Process single file
uv run scripts/export_shapefiles.py --single-file data/boundaries/postcodes.shp
```

**OUTPUT:**
    GeoJSON and GeoParquet files in data/originals_converted/ directory.

```sh
Found shapefile: data/originals/boundaries/POA_2021_AUST_GDA2020.shp 125.67Mb
Read 2668 features with CRS: EPSG:3577
Reprojecting from EPSG:3577 to EPSG:4326 (WGS84)
Successfully exported to data/originals_converted/boundaries/POA_2021_AUST_GDA2020.geojson
```

**DEPENDENCIES:** geopandas, requests, python-dotenv, tqdm, pyarrow

----------------------------------------

### migrate_geojson_geoparquet.py

**TITLE:** Convert GeoJSON files to efficient GeoParquet format
**DESCRIPTION:** Simple utility to convert GeoJSON files to compressed GeoParquet format for better
storage efficiency and faster loading. Shows compression ratios and handles file timestamp checking
to avoid unnecessary conversions.

**SOURCE:** scripts/migrate_geojson_geoparquet.py

**LANGUAGE:** python
**USAGE:**
    Automatically converts specific large GeoJSON files to Parquet.

```sh
uv run scripts/migrate_geojson_geoparquet.py
```

**OUTPUT:**
    Compressed Parquet files with size comparison.

```sh
Converted data/public_transport_lines.geojson 45.23Mb 
to data/public_transport_lines.parquet 12.87Mb 
compression ratio: 28.46%
```

**DEPENDENCIES:** geopandas, pyarrow, requests, tqdm

----------------------------------------

## Boundary Processing Scripts

### extract_postcode_polygons.py

**TITLE:** Extract and filter Australian postcode boundary polygons
**DESCRIPTION:** Processes Australian Bureau of Statistics postcode boundaries and filters them
based on transport stops. Creates both selected individual polygons and unioned coverage areas for
postcodes containing metro trains and trams.

**SOURCE:** scripts/extract_postcode_polygons.py

**LANGUAGE:** python
**USAGE:**
    Automatically processes boundary files and creates filtered outputs.

```sh
uv run scripts/extract_postcode_polygons.py
```

**OUTPUT:**
    Selected and unioned boundary files for different transport-accessible areas.

```sh
Processing target: postcodes_with_trams_trains with input file:
    data/originals_converted/boundaries/POA_2021_AUST_GDA2020.parquet
Loading input file: POA_2021_AUST_GDA2020.parquet 125.67 MB

# Generated files
data/geojson/ptv/boundaries/selected_postcodes_with_trams_trains.geojson
data/geojson/ptv/boundaries/unioned_postcodes_with_trams_trains.geojson
```

**DEPENDENCIES:** geopandas, pyarrow, shapely, requests, tqdm

----------------------------------------

### extract_stops_within_union.py

**TITLE:** Filter transport stops within unified boundary polygons
**DESCRIPTION:** Extracts public transport stops that fall within unioned postcode boundaries.
Filters out bus stops and duplicates, focusing on rail and tram infrastructure for isochrone
analysis.

**SOURCE:** scripts/extract_stops_within_union.py

**LANGUAGE:** python
**USAGE:**
    Processes stops against boundary unions automatically.

```sh
uv run scripts/extract_stops_within_union.py
```

**OUTPUT:**
    Filtered GeoJSON file containing relevant transport stops.

```sh
Unique stop modes: ['METRO TRAIN' 'METRO TRAM' 'REGIONAL TRAIN' 'INTERSTATE TRAIN']
Wrote 445 unique stops to data/geojson/ptv/stops_within_union.geojson
```

**DEPENDENCIES:** geopandas, pyarrow, shapely, requests, tqdm

----------------------------------------

## Transit Analysis Scripts

### stops_by_transit_time.py

**TITLE:** Calculate transit times from stops to Southern Cross Station
**DESCRIPTION:** Uses Google Maps API to calculate public transport commute times from each
transport stop to Southern Cross Station. Creates time-based hulls for visualization and caches
results for performance. Generates both point data and concave hull polygons for different time
tiers.

**SOURCE:** scripts/stops_by_transit_time.py

**LANGUAGE:** python
**USAGE:**
    Calculates transit times and creates visualization hulls.

```sh
uv run scripts/stops_by_transit_time.py
```

**OUTPUT:**
    GeoJSON files with transit times and visualization hulls.

```sh
Processing stop 127/445: Flinders Street Station
Transit time stats (minutes): min=5.0, max=87.3, mean=34.2, median=31.5, count=445
Results saved to data/geojson/ptv/stops_with_commute_times.geojson and
    data/geojson/ptv/stops_with_commute_times.parquet

# Creates concave hulls for time visualization
data/geojson/ptv/ptv_commute_tier_hulls.geojson
```

**DEPENDENCIES:** googlemaps, python-dotenv, geopandas, pandas, pyarrow, requests, tqdm
**ENVIRONMENT:** Requires GOOGLE_MAPS_API_KEY

----------------------------------------

## Real Estate Analysis Scripts

### process_realestate_candidates.py

**TITLE:** Analyze real estate properties with commute time calculations
**DESCRIPTION:** Processes candidate property addresses and calculates comprehensive commute times
to work destinations using Google Maps API. Supports multiple transport modes (driving, transit,
walking, cycling) and time periods (morning/evening). Generates detailed GeoJSON outputs with route
polylines for visualization.

**SOURCE:** scripts/process_realestate_candidates.py

**LANGUAGE:** python
**USAGE:**
    Processes property addresses from YAML file with commute calculations.

```sh
uv run scripts/process_realestate_candidates.py
```

**OUTPUT:**
    Individual GeoJSON files per property with commute data and route visualization.

```sh
Processing: 12 Eleanor Street, Footscray, Vic 3011
Calculating commute from 12 Eleanor Street, Footscray, Vic 3011 to work
    (Southern Cross Station, Melbourne)
Saved GeoJSON result to
    data/candidate_real_estate/12_Eleanor_Street__Footscray__Vic_3011.json.geojson

Processing completed: 7 successful, 0 failed
```

**DEPENDENCIES:** playwright, pyyaml, googlemaps, python-dotenv, geopandas, polyline
**ENVIRONMENT:** Requires GOOGLE_MAPS_API_KEY

----------------------------------------

## Utility Modules

### utils.py

**TITLE:** Shared utility functions for geospatial data processing
**DESCRIPTION:** Common utility functions used across multiple scripts including file handling,
data normalization, API retry logic, and GeoDataFrame operations. Provides standardized functions
for loading stops, generating file paths, caching validation, and saving outputs.

**SOURCE:** scripts/utils.py

**LANGUAGE:** python
**USAGE:**
    Imported by other scripts - not run directly.

```sh
# Used as import in other scripts
from utils import load_stops, dirty, save_geodataframe, make_request_with_retry
```

**FUNCTIONS:**

- `min_max_normalize()` - Normalize series to 0-1 range
- `normalise_name()` - Clean names for filenames
- `load_stops()` - Load and filter transport stops
- `dirty()` - Check if files need updating
- `make_request_with_retry()` - HTTP requests with backoff
- `save_geodataframe()` - Save to GeoJSON and Parquet

**DEPENDENCIES:** geopandas, requests, python-dotenv, tqdm, pyarrow

----------------------------------------

## Script Execution Guidelines

### Common Usage Patterns

All scripts follow these conventions:

1. **Independent Execution:** Each script runs standalone with `uv run scripts/script_name.py`
2. **Dependency Management:** Uses PEP-723 inline metadata for dependencies
3. **Environment Variables:** Configured via `.env` file (see `env.example`)
4. **Caching:** Intelligent file timestamp checking to avoid redundant processing
5. **Logging:** Structured logging instead of print statements
6. **Error Handling:** Graceful handling of API limits and missing data

### Processing Pipeline

The typical data processing flow:

1. `export_shapefiles.py` - Convert raw boundary data
2. `extract_postcode_polygons.py` - Filter relevant boundaries  
3. `extract_stops_within_union.py` - Extract relevant transport stops
4. `batch_isochrones_for_stops.py` - Fetch isochrone data
5. `fix_geojson.py` - Standardize isochrone formats
6. `consolidate_isochrones.py` - Merge isochrone datasets
7. `stops_by_transit_time.py` - Calculate transit times
8. `process_realestate_candidates.py` - Analyze properties

### Data Quality

- **Incremental Processing:** Scripts check file timestamps to avoid redundant work
- **Error Recovery:** API failures are logged and processing continues
- **Data Validation:** GeoJSON validation and CRS standardization
- **Compression:** Automatic GeoParquet generation for efficiency

### API Requirements

Several scripts require external API keys:
- **GraphHopper/Mapbox:** For isochrone calculations
- **Google Maps:** For transit times and property geocoding

Configure these in your `.env` file following the pattern in `env.example`.
